"""Offline deterministic static security scanning over documents and chunks."""

import base64
import codecs
import html
import math
import re
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from time import monotonic
from typing import Any

from ragscanner.domain import (
    Chunk,
    DetectionType,
    Document,
    EvaluationClassification,
    Finding,
    SourceLocation,
    finding_fingerprint,
)
from ragscanner.domain.helpers import REDACTED, mask_secret_like_values
from ragscanner.normalization import NormalizationAnnotation, NormalizationResult
from ragscanner.parsers import ParserWarning
from ragscanner.security.static_models import (
    MatcherType,
    StaticMatcher,
    StaticRule,
    StaticScanConfig,
    StaticScanResult,
    StaticScanStatistics,
    StaticScanWarning,
    StaticScope,
)
from ragscanner.security.static_rules import StaticRuleLibrary, validate_safe_regex

_BENIGN = re.compile(
    r"(?i)\b(?:security\s+(?:article|guide|training)|documentation|example|for educational purposes|"
    r"do not follow|harmless|quoted attack|canary|no-op|simulate|örnek|dokümantasyon|eğitim|uygulamayın|çalıştırmayın)\b"
)
_DOCUMENTATION_CONTEXT = re.compile(
    r"(?i)\b(?:documentation|troubleshooting|syntax|security article|guide|dokümantasyon|örnek)\b"
)
_AGENT_CONTEXT = re.compile(
    r"(?i)\b(?:assistant|agent|model|chatbot|llm|ai|you must|you should|call the|invoke the|"
    r"asistan|ajan|model|yapay zek[âa]|çağır|çalıştır|uygula|talimat)\b"
)
_PLACEHOLDER = re.compile(
    r"(?i)(?:example|placeholder|dummy|sample|test|fake|your[_-]?|xxx+|<[^>]+>|\{\{[^}]+\}\})"
)
_BASE64 = re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{30,}={0,2}(?![A-Za-z0-9+/=])")
_UNICODE_ESCAPE = re.compile(r"(?:\\u[0-9a-fA-F]{4}){3,}(?:[ \t]+[A-Za-z ]{1,160})?")
_HEX = re.compile(r"(?i)(?:[0-9a-f]{2}[\s:]*){16,}")
_URL = re.compile(r"(?i)\b(?:https?|ftp|file|javascript|data)://[^\s<>\"']+")
_EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_PHONE = re.compile(
    r"(?<!\d)(?:\+?90[\s.-]?)?(?:\(?0?5\d{2}\)?[\s.-]?)\d{3}[\s.-]?\d{2}[\s.-]?\d{2}(?!\d)"
)
_TC = re.compile(r"(?<!\d)[1-9]\d{10}(?!\d)")
_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
_IP = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")
_PRIVATE_KEY = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]{0,8192}?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
)
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{16,}")
_ASSIGNMENT_SECRET = re.compile(
    r"(?i)\b(?:api[_-]?key|access[_-]?token|secret|password|webhook[_-]?secret)\s*[:=]\s*['\"]?([^\s,'\"]{8,})"
)
_CONNECTION = re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s]+")
_CLOUD_KEY = re.compile(r"\bAKIA[0-9A-Z]{16}\b")


@dataclass(frozen=True, slots=True)
class _Target:
    scope: StaticScope
    text: str
    source: SourceLocation
    document_id: str
    chunk_id: str | None = None
    normalized_offset: int = 0
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class _Match:
    start: int
    end: int
    value: str
    matcher_type: MatcherType
    decoded: bool = False
    metadata: dict[str, Any] | None = None


class StaticSecurityScanner:
    name = "static_security_scanner"
    version = "1.0.0"

    def __init__(
        self,
        library: StaticRuleLibrary,
        config: StaticScanConfig | None = None,
        monotonic_clock: Callable[[], float] | None = None,
    ) -> None:
        self.library = library
        self.config = config or StaticScanConfig()
        self._monotonic = monotonic_clock or monotonic

    def scan(
        self,
        document: Document,
        *,
        normalized: NormalizationResult | None = None,
        chunks: list[Chunk] | None = None,
        parser_warnings: list[ParserWarning] | None = None,
        normalization_annotations: list[NormalizationAnnotation] | None = None,
    ) -> StaticScanResult:
        started = self._monotonic()
        rules, skipped = self.library.select(self.config.selection)
        if len(rules) > self.config.maximum_total_rules:
            omitted = rules[self.config.maximum_total_rules :]
            rules = rules[: self.config.maximum_total_rules]
            skipped.extend(rule.id for rule in omitted)
        warnings: list[StaticScanWarning] = []
        findings: list[Finding] = []
        evaluated: list[str] = []
        matches_evaluated = 0
        decoded_count = 0
        metadata_count = 0
        annotations = normalization_annotations or (normalized.annotations if normalized else [])
        targets, metadata_count = self._targets(
            document, normalized, chunks or [], parser_warnings or [], annotations, warnings
        )
        for rule in rules:
            if self._timed_out(started):
                warnings.append(
                    StaticScanWarning(
                        code="scan_time_limit_reached",
                        message="Static scan stopped at the configured cooperative time limit.",
                    )
                )
                skipped.extend(candidate.id for candidate in rules if candidate.id not in evaluated)
                break
            evaluated.append(rule.id)
            rule_matches = 0
            for target in targets:
                if target.scope not in rule.scope:
                    continue
                if (
                    chunks
                    and StaticScope.CHUNK in rule.scope
                    and target.scope
                    in {
                        StaticScope.RAW_DOCUMENT,
                        StaticScope.NORMALIZED_DOCUMENT,
                    }
                ):
                    continue
                for matcher in rule.matchers:
                    for match in self._match(matcher, target, warnings):
                        matches_evaluated += 1
                        decoded_count += int(match.decoded)
                        if not self._context_allows(rule, target, match):
                            continue
                        finding = self._finding(document, normalized, rule, target, match)
                        findings.append(finding)
                        rule_matches += 1
                        if len(findings) >= self.config.maximum_findings_per_document:
                            warnings.append(
                                StaticScanWarning(
                                    code="maximum_findings_reached",
                                    message="Finding output reached the configured document limit.",
                                )
                            )
                            return self._result(
                                document,
                                findings,
                                evaluated,
                                skipped,
                                warnings,
                                matches_evaluated,
                                len(chunks or []),
                                metadata_count,
                                decoded_count,
                            )
                        if rule_matches >= self.config.maximum_matches_per_rule:
                            warnings.append(
                                StaticScanWarning(
                                    code="maximum_matches_per_rule_reached",
                                    message="Rule match output reached its configured limit.",
                                    rule_id=rule.id,
                                )
                            )
                            break
                    if rule_matches >= self.config.maximum_matches_per_rule:
                        break
                if rule_matches >= self.config.maximum_matches_per_rule:
                    break
        return self._result(
            document,
            findings,
            evaluated,
            skipped,
            warnings,
            matches_evaluated,
            len(chunks or []),
            metadata_count,
            decoded_count,
        )

    def _targets(
        self,
        document: Document,
        normalized: NormalizationResult | None,
        chunks: list[Chunk],
        parser_warnings: list[ParserWarning],
        annotations: list[NormalizationAnnotation],
        warnings: list[StaticScanWarning],
    ) -> tuple[list[_Target], int]:
        targets = [
            _Target(StaticScope.RAW_DOCUMENT, document.content, document.source, document.id),
            _Target(
                StaticScope.NORMALIZED_DOCUMENT,
                normalized.normalized_content if normalized else document.normalized_content,
                document.source,
                document.id,
            ),
        ]
        if document.title:
            targets.append(_Target(StaticScope.TITLE, document.title, document.source, document.id))
        for chunk in sorted(chunks, key=lambda item: item.index):
            targets.append(
                _Target(
                    StaticScope.CHUNK,
                    chunk.normalized_content,
                    chunk.source,
                    document.id,
                    chunk.id,
                    int(chunk.metadata.get("normalized_start", 0)),
                    chunk.metadata,
                )
            )
            for heading in chunk.headings:
                targets.append(
                    _Target(StaticScope.HEADING, heading, chunk.source, document.id, chunk.id)
                )
        flattened = list(self._flatten_metadata(document.metadata, "document"))
        flattened.extend(self._flatten_metadata(document.source.metadata, "source"))
        for chunk in chunks:
            flattened.extend(self._flatten_metadata(chunk.metadata, f"chunk:{chunk.id}"))
        if len(flattened) > self.config.maximum_metadata_fields_scanned:
            warnings.append(
                StaticScanWarning(
                    code="metadata_field_limit_reached",
                    message="Metadata scanning was bounded by configuration.",
                    metadata={
                        "detected": len(flattened),
                        "limit": self.config.maximum_metadata_fields_scanned,
                    },
                )
            )
            flattened = flattened[: self.config.maximum_metadata_fields_scanned]
        targets.extend(
            _Target(
                StaticScope.METADATA,
                value,
                document.source,
                document.id,
                metadata={"field": field},
            )
            for field, value in flattened
        )
        targets.extend(
            _Target(
                StaticScope.PARSER_WARNING,
                warning.code,
                document.source.model_copy(update={"page_number": warning.page_number}),
                document.id,
                metadata={"warning_code": warning.code},
            )
            for warning in parser_warnings
        )
        targets.extend(
            _Target(
                StaticScope.NORMALIZATION_ANNOTATION,
                annotation.annotation_type.value,
                self._annotation_source(document, normalized, annotation),
                document.id,
                normalized_offset=annotation.normalized_start,
                metadata={"annotation_type": annotation.annotation_type.value},
            )
            for annotation in annotations
        )
        normalized_text = (
            normalized.normalized_content if normalized else document.normalized_content
        )
        structural_scope = {
            "heading_region": StaticScope.HEADING,
            "table_region": StaticScope.TABLE_CELL,
            "code_region": StaticScope.CODE_BLOCK,
        }
        for annotation in annotations:
            scope = structural_scope.get(annotation.annotation_type.value)
            if scope is None:
                continue
            targets.append(
                _Target(
                    scope,
                    normalized_text[annotation.normalized_start : annotation.normalized_end],
                    self._annotation_source(document, normalized, annotation),
                    document.id,
                    normalized_offset=annotation.normalized_start,
                    metadata={"annotation_type": annotation.annotation_type.value},
                )
            )
        targets.extend(
            _Target(
                StaticScope.URL,
                found.group(0),
                document.source,
                document.id,
                normalized_offset=found.start(),
            )
            for found in _URL.finditer(normalized_text)
        )
        return targets, len(flattened)

    def _match(
        self,
        matcher: StaticMatcher,
        target: _Target,
        warnings: list[StaticScanWarning],
    ) -> Iterable[_Match]:
        text = target.text
        if matcher.type is MatcherType.EXACT:
            if text in matcher.patterns:
                yield _Match(0, len(text), text, matcher.type)
        elif matcher.type is MatcherType.SUBSTRING_CI:
            folded = text.casefold()
            for pattern in matcher.patterns:
                cursor = 0
                needle = pattern.casefold()
                while (start := folded.find(needle, cursor)) >= 0:
                    yield _Match(
                        start,
                        start + len(pattern),
                        text[start : start + len(pattern)],
                        matcher.type,
                    )
                    cursor = start + max(1, len(pattern))
        elif matcher.type in {MatcherType.REGEX, MatcherType.TOKEN_SEQUENCE}:
            bounded = text[: self.config.maximum_regex_input_size]
            if len(text) > len(bounded):
                warnings.append(
                    StaticScanWarning(
                        code="regex_input_bounded",
                        message="Rule input was bounded before regular-expression matching.",
                    )
                )
            for pattern in matcher.patterns:
                expression = (
                    validate_safe_regex(pattern)
                    if matcher.type is MatcherType.REGEX
                    else re.compile(
                        r"\b" + r"\s+".join(re.escape(token) for token in pattern.split()) + r"\b",
                        re.IGNORECASE,
                    )
                )
                for found in expression.finditer(bounded):
                    yield _Match(found.start(), found.end(), found.group(0), matcher.type)
        elif matcher.type is MatcherType.ANNOTATION_TYPE:
            if (
                target.scope is StaticScope.NORMALIZATION_ANNOTATION
                and target.text in matcher.patterns
            ):
                yield _Match(0, len(text), text, matcher.type)
        elif matcher.type is MatcherType.WARNING_CODE:
            if target.scope is StaticScope.PARSER_WARNING and target.text in matcher.patterns:
                yield _Match(0, len(text), text, matcher.type)
        elif matcher.type is MatcherType.METADATA_FIELD:
            field = (
                "title"
                if target.scope is StaticScope.TITLE
                else str((target.metadata or {}).get("field", ""))
            )
            if target.scope in {StaticScope.METADATA, StaticScope.TITLE} and (
                not matcher.metadata_fields or field in matcher.metadata_fields
            ):
                for pattern in matcher.patterns:
                    if (start := text.casefold().find(pattern.casefold())) >= 0:
                        yield _Match(
                            start,
                            start + len(pattern),
                            text[start : start + len(pattern)],
                            matcher.type,
                        )
        elif matcher.type is MatcherType.DECODED_CONTENT:
            yield from self._decoded_matches(text, matcher)
        elif matcher.type is MatcherType.ENTROPY_HEURISTIC:
            if len(text) >= matcher.minimum_length and self._entropy(text) >= float(
                matcher.metadata.get("minimum_entropy", 4.5)
            ):
                yield _Match(0, min(len(text), 256), text[:256], matcher.type)
        elif matcher.type is MatcherType.URL_PROPERTY:
            yield from self._url_matches(text)
        elif matcher.type is MatcherType.SECRET_PATTERN:
            yield from self._secret_matches(text)
        elif matcher.type is MatcherType.PII_PATTERN:
            yield from self._pii_matches(text)

    def _decoded_matches(self, text: str, matcher: StaticMatcher) -> Iterable[_Match]:
        if self.config.maximum_decoding_depth == 0:
            return
        indicators = tuple(pattern.casefold() for pattern in matcher.patterns)
        candidates: list[tuple[int, int, str, str]] = []
        if not text.casefold().startswith("data:image/"):
            candidates.extend(
                (match.start(), match.end(), match.group(0), "base64")
                for match in _BASE64.finditer(text)
            )
        candidates.extend(
            (match.start(), match.end(), match.group(0), "unicode_escape")
            for match in _UNICODE_ESCAPE.finditer(text)
        )
        candidates.extend(
            (match.start(), match.end(), match.group(0), "hex") for match in _HEX.finditer(text)
        )
        for start, end, raw, encoding in candidates:
            if len(raw) > self.config.maximum_decoded_payload_size * 4:
                continue
            decoded = self._decode(raw, encoding)
            if decoded is None or len(decoded) > self.config.maximum_decoded_payload_size:
                continue
            inspected = decoded
            depth = 1
            while (
                depth < self.config.maximum_decoding_depth
                and not any(indicator in inspected.casefold() for indicator in indicators)
                and (nested := _BASE64.fullmatch(inspected.strip())) is not None
            ):
                candidate = self._decode(nested.group(0), "base64")
                if candidate is None or len(candidate) > self.config.maximum_decoded_payload_size:
                    break
                inspected = candidate
                depth += 1
            if any(indicator in inspected.casefold() for indicator in indicators):
                yield _Match(start, end, raw, matcher.type, True, {"encoding": encoding})
        for match in re.finditer(r"(?:[A-Za-z]{4,}\s+){2,}[A-Za-z]{4,}|[A-Za-z]{24,}", text):
            decoded = codecs.decode(match.group(0), "rot_13")
            if any(indicator in decoded.casefold() for indicator in indicators):
                yield _Match(
                    match.start(),
                    match.end(),
                    match.group(0),
                    matcher.type,
                    True,
                    {"encoding": "rot13"},
                )

    @staticmethod
    def _decode(raw: str, encoding: str) -> str | None:
        try:
            if encoding == "base64":
                return base64.b64decode(raw, validate=True).decode("utf-8")
            if encoding == "unicode_escape":
                return bytes(raw, "ascii").decode("unicode_escape")
            if encoding == "hex":
                return bytes.fromhex(re.sub(r"[\s:]", "", raw)).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return None
        return None

    @staticmethod
    def _url_matches(text: str) -> Iterable[_Match]:
        for found in _URL.finditer(text):
            value = found.group(0)
            lowered = value.casefold()
            authority = value.split("://", 1)[1].split("/", 1)[0] if "://" in value else ""
            host = authority.rsplit("@", 1)[-1].split(":", 1)[0]
            reasons: list[str] = []
            if "@" in authority:
                reasons.append("userinfo_credentials")
            if lowered.startswith(("file:", "javascript:", "data:")):
                reasons.append("suspicious_scheme")
            if host in {"localhost", "127.0.0.1", "169.254.169.254", "metadata.google.internal"}:
                reasons.append("local_or_metadata_service")
            if _IP.fullmatch(host):
                reasons.append("ip_address_host")
            if re.search(r"(?i)(?:bit\.ly|tinyurl\.com|t\.co|goo\.gl)$", host):
                reasons.append("url_shortener")
            if lowered.startswith("http://") and _AGENT_CONTEXT.search(
                text[max(0, found.start() - 100) : found.end() + 100]
            ):
                reasons.append("http_in_instruction_context")
            if reasons:
                yield _Match(
                    found.start(),
                    found.end(),
                    value,
                    MatcherType.URL_PROPERTY,
                    metadata={"reasons": reasons},
                )

    @staticmethod
    def _secret_matches(text: str) -> Iterable[_Match]:
        patterns = (_PRIVATE_KEY, _BEARER, _ASSIGNMENT_SECRET, _CONNECTION, _CLOUD_KEY)
        for pattern in patterns:
            for found in pattern.finditer(text):
                if _PLACEHOLDER.search(found.group(0)):
                    continue
                yield _Match(found.start(), found.end(), found.group(0), MatcherType.SECRET_PATTERN)

    @staticmethod
    def _pii_matches(text: str) -> Iterable[_Match]:
        for pattern, kind in (
            (_EMAIL, "email"),
            (_PHONE, "phone"),
            (_TC, "turkish_identity"),
            (_CARD, "payment_card"),
            (_IP, "ip_address"),
        ):
            for found in pattern.finditer(text):
                value = found.group(0)
                if kind == "turkish_identity" and not StaticSecurityScanner._valid_tc(value):
                    continue
                if kind == "payment_card" and not StaticSecurityScanner._luhn(value):
                    continue
                if kind == "ip_address" and not all(
                    0 <= int(part) <= 255 for part in value.split(".")
                ):
                    continue
                yield _Match(
                    found.start(),
                    found.end(),
                    value,
                    MatcherType.PII_PATTERN,
                    metadata={"pii_type": kind},
                )

    def _context_allows(self, rule: StaticRule, target: _Target, match: _Match) -> bool:
        window = target.text[max(0, match.start - 200) : min(len(target.text), match.end + 200)]
        if any(exclusion.casefold() in window.casefold() for exclusion in rule.exclusions):
            return False
        if "agent_instruction" in rule.context_requirements and not _AGENT_CONTEXT.search(window):
            return False
        if "agent_instruction" in rule.context_requirements and _DOCUMENTATION_CONTEXT.search(
            window
        ):
            return False
        if "not_placeholder" in rule.context_requirements and _PLACEHOLDER.search(match.value):
            return False
        return True

    def _finding(
        self,
        document: Document,
        normalized: NormalizationResult | None,
        rule: StaticRule,
        target: _Target,
        match: _Match,
    ) -> Finding:
        window_start = max(
            0, match.start - min(rule.evidence_window, self.config.maximum_evidence_size) // 2
        )
        window_end = min(
            len(target.text),
            match.end + min(rule.evidence_window, self.config.maximum_evidence_size) // 2,
        )
        raw_evidence = target.text[window_start:window_end]
        secret = match.matcher_type is MatcherType.SECRET_PATTERN
        evidence = self._safe_evidence(raw_evidence, secret)
        benign = bool(_BENIGN.search(raw_evidence)) or target.scope is StaticScope.CODE_BLOCK
        confidence = max(0.1, rule.default_confidence - (0.35 if benign else 0.0))
        if match.matcher_type in {
            MatcherType.PII_PATTERN,
            MatcherType.URL_PROPERTY,
            MatcherType.DECODED_CONTENT,
        }:
            confidence = min(confidence, 0.78)
        classification = self._classification(rule, confidence, benign)
        absolute_start = target.normalized_offset + match.start
        absolute_end = target.normalized_offset + match.end
        source = self._source_for_range(
            document, normalized, target.source, absolute_start, absolute_end
        )
        fingerprint = finding_fingerprint(
            rule_id=rule.id,
            rule_version=rule.version,
            source_id=source.source_id,
            document_id=document.id,
            chunk_id=target.chunk_id,
            target_id=None,
            test_case_id=None,
            evidence=f"{evidence}|location:{target.scope.value}:{absolute_start}:{absolute_end}",
        )
        metadata = {
            "scope": target.scope.value,
            "matcher_type": match.matcher_type.value,
            "normalized_start": (
                absolute_start if target.scope is not StaticScope.RAW_DOCUMENT else None
            ),
            "normalized_end": (
                absolute_end if target.scope is not StaticScope.RAW_DOCUMENT else None
            ),
            "original_start": (
                absolute_start if target.scope is StaticScope.RAW_DOCUMENT else None
            ),
            "original_end": absolute_end if target.scope is StaticScope.RAW_DOCUMENT else None,
            "manual_review": classification is EvaluationClassification.AMBIGUOUS,
            "benign_context_detected": benign,
            "decoded_for_inspection": match.decoded,
            "decoded_content_executed": False,
            "url_fetched": False,
            "match_metadata": self._safe_metadata(match.metadata or {}),
        }
        return Finding(
            id=fingerprint,
            fingerprint=fingerprint,
            category=rule.category,
            scanner=self.name,
            rule_id=rule.id,
            rule_version=rule.version,
            title=rule.name,
            description=rule.description,
            severity=rule.severity,
            confidence=confidence,
            detection_type=rule.detection_type,
            classification=classification,
            source=source,
            document_id=document.id,
            chunk_id=target.chunk_id,
            evidence=evidence,
            impact=str(rule.metadata.get("impact", rule.description)),
            recommendation=rule.remediation,
            references=rule.references,
            first_seen=document.ingested_at,
            last_seen=document.ingested_at,
            metadata=metadata,
        )

    def _safe_evidence(self, value: str, secret: bool) -> str:
        if secret:
            value = _PRIVATE_KEY.sub("[REDACTED PRIVATE KEY]", value)
            value = _CONNECTION.sub("[REDACTED CONNECTION STRING]", value)
            value = _BEARER.sub("Bearer [REDACTED]", value)
            value = _ASSIGNMENT_SECRET.sub(
                lambda found: found.group(0).split(found.group(1))[0] + REDACTED, value
            )
            value = _CLOUD_KEY.sub("[REDACTED CLOUD KEY]", value)
        value = mask_secret_like_values(value)
        bounded = value[: self.config.maximum_evidence_size]
        return html.escape(bounded, quote=True)

    @staticmethod
    def _safe_metadata(value: dict[str, Any]) -> dict[str, Any]:
        return {
            str(key)[:64]: mask_secret_like_values(str(item))[:256] for key, item in value.items()
        }

    @staticmethod
    def _classification(
        rule: StaticRule, confidence: float, benign: bool
    ) -> EvaluationClassification:
        if benign or confidence < 0.55:
            return EvaluationClassification.AMBIGUOUS
        if (
            rule.detection_type is DetectionType.DETERMINISTIC
            and confidence >= 0.9
            and rule.category
            in {
                "secret_exposure",
                "hidden_content",
            }
        ):
            return EvaluationClassification.CONFIRMED
        return EvaluationClassification.PROBABLE

    @staticmethod
    def _source_for_range(
        document: Document,
        normalized: NormalizationResult | None,
        fallback: SourceLocation,
        start: int,
        end: int,
    ) -> SourceLocation:
        if normalized is None:
            return fallback
        segments = [
            segment
            for segment in normalized.segments
            if start < segment.normalized_end and segment.normalized_start < end
        ]
        if not segments:
            return fallback
        values = fallback.model_dump()
        pages = [
            segment.source_location.page_number
            for segment in segments
            if segment.source_location.page_number
        ]
        lines_start = [
            segment.source_location.line_start
            for segment in segments
            if segment.source_location.line_start
        ]
        lines_end = [
            segment.source_location.line_end
            for segment in segments
            if segment.source_location.line_end
        ]
        values["page_number"] = min(pages) if pages else fallback.page_number
        values["line_start"] = min(lines_start) if lines_start else fallback.line_start
        values["line_end"] = max(lines_end) if lines_end else fallback.line_end
        return SourceLocation.model_validate(values)

    @staticmethod
    def _annotation_source(
        document: Document,
        normalized: NormalizationResult | None,
        annotation: NormalizationAnnotation,
    ) -> SourceLocation:
        return StaticSecurityScanner._source_for_range(
            document,
            normalized,
            document.source,
            annotation.normalized_start,
            annotation.normalized_end,
        )

    @staticmethod
    def _flatten_metadata(
        value: Any,
        prefix: str,
        depth: int = 0,
        seen: set[int] | None = None,
    ) -> Iterable[tuple[str, str]]:
        seen = seen or set()
        if depth > 8:
            yield prefix, "[metadata-depth-limit]"
            return
        if isinstance(value, dict | list):
            identity = id(value)
            if identity in seen:
                yield prefix, "[metadata-cycle]"
                return
            seen.add(identity)
        if isinstance(value, dict):
            for key in sorted(value, key=lambda item: str(type(item)) + repr(item)[:128])[:1_000]:
                safe_key = key if isinstance(key, str | int | float | bool) else type(key).__name__
                yield from StaticSecurityScanner._flatten_metadata(
                    value[key], f"{prefix}.{safe_key}", depth + 1, seen
                )
        elif isinstance(value, list):
            for index, item in enumerate(value[:1_000]):
                yield from StaticSecurityScanner._flatten_metadata(
                    item, f"{prefix}[{index}]", depth + 1, seen
                )
        elif isinstance(value, bytes):
            yield prefix, value[:4_096].decode("utf-8", errors="replace")
        elif isinstance(value, str | int | float | bool):
            yield prefix, str(value)[:4_096]
        elif value is not None:
            yield prefix, f"[unsupported-metadata-type:{type(value).__name__}]"

    @staticmethod
    def _entropy(value: str) -> float:
        if not value:
            return 0.0
        counts = Counter(value)
        return -sum(
            (count / len(value)) * math.log2(count / len(value)) for count in counts.values()
        )

    @staticmethod
    def _valid_tc(value: str) -> bool:
        digits = [int(character) for character in value]
        return (
            len(digits) == 11
            and digits[0] != 0
            and ((sum(digits[0:9:2]) * 7 - sum(digits[1:8:2])) % 10) == digits[9]
            and sum(digits[:10]) % 10 == digits[10]
        )

    @staticmethod
    def _luhn(value: str) -> bool:
        digits = [int(character) for character in value if character.isdigit()]
        if not 13 <= len(digits) <= 19:
            return False
        total = 0
        parity = len(digits) % 2
        for index, digit in enumerate(digits):
            if index % 2 == parity:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        return total % 10 == 0

    def _timed_out(self, started: float) -> bool:
        return self._monotonic() - started >= self.config.maximum_scan_seconds

    def _result(
        self,
        document: Document,
        findings: list[Finding],
        evaluated: list[str],
        skipped: list[str],
        warnings: list[StaticScanWarning],
        matches: int,
        chunks: int,
        metadata_fields: int,
        decoded: int,
    ) -> StaticScanResult:
        ordered = sorted(
            findings, key=lambda item: (item.rule_id, item.chunk_id or "", item.fingerprint)
        )
        return StaticScanResult(
            document_id=document.id,
            findings=ordered,
            rules_evaluated=sorted(set(evaluated)),
            rules_skipped=sorted(set(skipped)),
            warnings=warnings,
            statistics=StaticScanStatistics(
                rules_evaluated=len(set(evaluated)),
                rules_skipped=len(set(skipped)),
                matches_evaluated=matches,
                findings_created=len(ordered),
                chunks_scanned=chunks,
                metadata_fields_scanned=metadata_fields,
                decoded_payloads_inspected=decoded,
            ),
            scanner_name=self.name,
            scanner_version=self.version,
            rule_pack_versions=self.library.pack_versions,
            metadata={
                "offline": True,
                "content_executed": False,
                "network_used": False,
                "subprocess_used": False,
            },
        )
