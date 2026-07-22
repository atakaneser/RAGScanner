"""Deterministic, non-rendering normalization with bounded source mappings."""

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Literal

from ragscanner.domain import Document, SourceLocation
from ragscanner.domain.helpers import document_content_hash
from ragscanner.normalization.models import (
    AnnotationType,
    NormalizationAnnotation,
    NormalizationConfig,
    NormalizationError,
    NormalizationErrorCategory,
    NormalizationResult,
    NormalizationSegment,
    NormalizationStatistics,
    NormalizationWarning,
    UnicodeForm,
)

_BIDI = {
    "\u061c": "ALM",
    "\u200e": "LRM",
    "\u200f": "RLM",
    "\u202a": "LRE",
    "\u202b": "RLE",
    "\u202c": "PDF",
    "\u202d": "LRO",
    "\u202e": "RLO",
    "\u2066": "LRI",
    "\u2067": "RLI",
    "\u2068": "FSI",
    "\u2069": "PDI",
}
_ZERO_WIDTH = {"\u200b": "ZWSP", "\u200c": "ZWNJ", "\u200d": "ZWJ", "\u2060": "WJ"}
_LIST = re.compile(r"^\s*(?:[-+*•]|\d{1,4}[.)])\s+")
_HEADING = re.compile(r"^\s*#{1,6}\s+")
_PAGE_NUMBER = re.compile(
    r"^\s*(?:page|sayfa)?\s*[-–—]?\s*\d{1,6}\s*(?:/\s*\d{1,6})?\s*[-–—]?\s*$", re.I
)
_URL_OR_PATH = re.compile(r"(?:https?://|www\.|[/\\][\w.-]+|[A-Za-z]:\\)")
_CODEISH = re.compile(r"[{}();=]|^(?:def|class|function|const|let|var|import|from)\b")
_HYPHEN_JOIN = re.compile(r"^(.{0,200}?)([A-Za-zÇĞİÖŞÜçğıöşü]{3,})-$")


@dataclass(frozen=True, slots=True)
class _Unit:
    value: str
    original_start: int
    original_end: int
    transformations: tuple[str, ...] = ()
    approximate: bool = False


class DocumentNormalizer:
    """Normalize parser output without mutating the input Document."""

    name = "document_normalizer"
    version = "1.1.0"

    def __init__(self, config: NormalizationConfig | None = None) -> None:
        self.config = config or NormalizationConfig()

    def normalize(self, document: Document) -> NormalizationResult:
        if not document.hash_matches_content():
            raise NormalizationError(
                NormalizationErrorCategory.INVALID_INPUT,
                "document content hash does not match original content",
            )
        statistics = NormalizationStatistics(
            original_characters=len(document.content), normalized_characters=0
        )
        warnings: list[NormalizationWarning] = []
        annotations: list[NormalizationAnnotation] = []
        units = self._initial_units(document.content, statistics)
        units = self._unicode(units, statistics)
        units = self._controls(units, statistics, warnings, annotations)
        units, protected = self._whitespace(units, document, statistics, annotations)
        units = self._repair_lines(units, document, protected, statistics)
        if len(units) > self.config.maximum_normalized_output_size:
            raise NormalizationError(
                NormalizationErrorCategory.OUTPUT_LIMIT_EXCEEDED,
                "normalized output exceeds configured limit",
            )
        self._structural_annotations(document, units, annotations)
        if self.config.detect_boilerplate:
            self._boilerplate(document, units, annotations, statistics)
        for annotation in annotations:
            if annotation.original_start is not None and annotation.original_end is not None:
                annotation.normalized_start, annotation.normalized_end = self._normalized_range(
                    units, annotation.original_start, annotation.original_end
                )
        annotations = self._bound_annotations(annotations, warnings)
        segments = self._segments(document, units, warnings)
        content = "".join(unit.value for unit in units)
        statistics.normalized_characters = len(content)
        statistics.segments = len(segments)
        statistics.annotations = len(annotations)
        return NormalizationResult(
            document_id=document.id,
            original_hash=document.content_hash,
            normalized_content=content,
            normalized_hash=document_content_hash(content),
            segments=segments,
            warnings=warnings,
            annotations=annotations,
            statistics=statistics,
            normalizer_name=self.name,
            normalizer_version=self.version,
            metadata={
                "unicode_form": self.config.unicode_form.value,
                "normalization_is_sanitization": False,
                "original_content_modified": False,
                "boilerplate_removed": False,
                "page_boundaries_preserved": self.config.preserve_page_boundaries,
                "config": self.config.model_dump(mode="json"),
            },
        )

    def _initial_units(self, content: str, statistics: NormalizationStatistics) -> list[_Unit]:
        result: list[_Unit] = []
        index = 0
        while index < len(content):
            if self.config.normalize_newlines and content.startswith("\r\n", index):
                result.append(_Unit("\n", index, index + 2, ("newline_normalization",), True))
                statistics.newline_changes += 1
                index += 2
            elif self.config.normalize_newlines and content[index] == "\r":
                result.append(_Unit("\n", index, index + 1, ("newline_normalization",)))
                statistics.newline_changes += 1
                index += 1
            else:
                result.append(_Unit(content[index], index, index + 1))
                index += 1
        return result

    def _unicode(self, units: list[_Unit], statistics: NormalizationStatistics) -> list[_Unit]:
        if self.config.unicode_form is UnicodeForm.NONE:
            return units
        result: list[_Unit] = []
        index = 0
        while index < len(units):
            end = index + 1
            while end < len(units) and unicodedata.combining(units[end].value):
                end += 1
            group = units[index:end]
            raw = "".join(unit.value for unit in group)
            form: Literal["NFC", "NFKC"] = (
                "NFC" if self.config.unicode_form is UnicodeForm.NFC else "NFKC"
            )
            normalized = unicodedata.normalize(form, raw)
            if normalized == raw:
                result.extend(group)
            else:
                statistics.unicode_changes += 1
                transformations = self._merge_transformations(group, "unicode_normalization")
                start, finish = group[0].original_start, group[-1].original_end
                result.extend(
                    _Unit(character, start, finish, transformations, True)
                    for character in normalized
                )
            index = end
        return result

    def _controls(
        self,
        units: list[_Unit],
        statistics: NormalizationStatistics,
        warnings: list[NormalizationWarning],
        annotations: list[NormalizationAnnotation],
    ) -> list[_Unit]:
        result: list[_Unit] = []
        for unit in units:
            name: str | None = None
            annotation_type = AnnotationType.INVISIBLE_UNICODE
            if unit.value == "\x00":
                name = "NUL"
            elif unit.value in _BIDI:
                name = f"BIDI:{_BIDI[unit.value]}"
                annotation_type = AnnotationType.BIDI_CONTROL
            elif unit.value in _ZERO_WIDTH:
                name = _ZERO_WIDTH[unit.value]
            elif unit.value == "\ufffd":
                name = "REPLACEMENT"
                annotation_type = AnnotationType.REPLACEMENT_CHARACTER
            elif unit.value == "\u00ad":
                name = "SOFT_HYPHEN"
                statistics.soft_hyphens_marked += 1
            elif unicodedata.category(unit.value) == "Cc" and unit.value not in "\n\t":
                name = f"CONTROL:U+{ord(unit.value):04X}"
            if name is None:
                result.append(unit)
                continue
            preserve_emoji_joiner = unit.value == "\u200d"
            marker = (
                unit.value
                if preserve_emoji_joiner or not self.config.visible_control_markers
                else f"<{name}>"
            )
            output_start = sum(len(item.value) for item in result)
            transformed = _Unit(
                marker,
                unit.original_start,
                unit.original_end,
                self._merge_transformations([unit], "visible_control_marker"),
                marker != unit.value or unit.approximate,
            )
            result.append(transformed)
            statistics.control_markers += 1
            warnings.append(
                NormalizationWarning(
                    code="security_sensitive_control",
                    message="An invisible or non-printing character was represented explicitly.",
                    original_start=unit.original_start,
                    original_end=unit.original_end,
                    metadata={"marker": name},
                )
            )
            if self.config.annotate_invisible_unicode:
                annotations.append(
                    NormalizationAnnotation(
                        annotation_type=annotation_type,
                        normalized_start=output_start,
                        normalized_end=output_start + len(marker),
                        original_start=unit.original_start,
                        original_end=unit.original_end,
                        normalized_text=marker,
                        candidate_type=name,
                    )
                )
        return result

    def _whitespace(
        self,
        units: list[_Unit],
        document: Document,
        statistics: NormalizationStatistics,
        annotations: list[NormalizationAnnotation],
    ) -> tuple[list[_Unit], set[int]]:
        lines = self._split_lines(units)
        markdown = document.mime_type == "text/markdown"
        fenced = False
        protected: set[int] = set()
        blank_run = 0
        result: list[_Unit] = []
        for index, (line, newline) in enumerate(lines):
            text = "".join(unit.value for unit in line)
            stripped = text.lstrip()
            fence_line = markdown and (stripped.startswith("```") or stripped.startswith("~~~"))
            is_table = self._table_like(text)
            is_indented_code = markdown and (text.startswith("    ") or text.startswith("\t"))
            is_ascii = self._ascii_diagram(text)
            preserve = fenced or fence_line or is_indented_code or is_table or is_ascii
            if preserve:
                protected.add(index)
                self._annotation_for_units(
                    annotations,
                    AnnotationType.TABLE_REGION if is_table else AnnotationType.CODE_REGION,
                    line,
                    units,
                    metadata={"preformatted": True},
                )
            transformed = line if preserve else self._normalize_line(line, statistics)
            empty = not "".join(unit.value for unit in transformed).strip()
            if empty:
                blank_run += 1
                if blank_run > self.config.maximum_consecutive_blank_lines:
                    statistics.blank_lines_removed += 1
                    continue
            else:
                blank_run = 0
            result.extend(transformed)
            result.extend(newline)
            if fence_line:
                fenced = not fenced
        return result, protected

    def _normalize_line(
        self, line: list[_Unit], statistics: NormalizationStatistics
    ) -> list[_Unit]:
        working = list(line)
        if self.config.trim_lines:
            while working and working[-1].value in {" ", "\t"}:
                working.pop()
                statistics.whitespace_changes += 1
        if not self.config.normalize_horizontal_whitespace:
            return working
        result: list[_Unit] = []
        index = 0
        while index < len(working):
            if working[index].value not in {" ", "\t"}:
                result.append(working[index])
                index += 1
                continue
            end = index + 1
            while end < len(working) and working[end].value in {" ", "\t"}:
                end += 1
            group = working[index:end]
            result.append(
                _Unit(
                    " ",
                    group[0].original_start,
                    group[-1].original_end,
                    self._merge_transformations(group, "horizontal_whitespace"),
                    len(group) != 1 or group[0].value != " ",
                )
            )
            if len(group) != 1 or group[0].value != " ":
                statistics.whitespace_changes += 1
            index = end
        return result

    def _repair_lines(
        self,
        units: list[_Unit],
        document: Document,
        protected: set[int],
        statistics: NormalizationStatistics,
    ) -> list[_Unit]:
        if document.mime_type != "application/pdf":
            return units
        lines = self._split_lines(units)
        result: list[_Unit] = []
        index = 0
        while index < len(lines):
            line, newline = lines[index]
            if index + 1 >= len(lines) or index in protected or index + 1 in protected:
                result.extend(line + newline)
                index += 1
                continue
            next_line, next_newline = lines[index + 1]
            left = "".join(unit.value for unit in line)
            right = "".join(unit.value for unit in next_line)
            if self._is_page_marker(left) or self._is_page_marker(right):
                result.extend(line + newline)
                index += 1
                continue
            replacement: list[_Unit] | None = None
            if self.config.repair_hyphenated_line_breaks:
                replacement = self._hyphen_join(line, newline, next_line, left, right)
                if replacement is not None:
                    statistics.hyphenated_line_repairs += 1
            if (
                replacement is None
                and self.config.repair_pdf_wraps
                and self._likely_wrap(left, right)
            ):
                replacement = self._space_join(line, newline, next_line, "pdf_line_wrap_repair")
                statistics.pdf_wrap_repairs += 1
            if replacement is None:
                result.extend(line + newline)
                index += 1
            else:
                result.extend(replacement + next_newline)
                index += 2
        return result

    def _hyphen_join(
        self,
        line: list[_Unit],
        newline: list[_Unit],
        next_line: list[_Unit],
        left: str,
        right: str,
    ) -> list[_Unit] | None:
        match = _HYPHEN_JOIN.fullmatch(left.rstrip())
        next_match = re.match(r"^([a-zçğıöşü]{3,})(?:\b|$)", right)
        if not match or not next_match or _URL_OR_PATH.search(left) or _CODEISH.search(left):
            return None
        if _LIST.match(left) or _LIST.match(right):
            return None
        trimmed = list(line)
        while trimmed and trimmed[-1].value == " ":
            trimmed.pop()
        if not trimmed or trimmed[-1].value != "-":
            return None
        removed = trimmed.pop()
        bridge = newline or [removed]
        marker = _Unit(
            "",
            removed.original_start,
            bridge[-1].original_end,
            self._merge_transformations([removed, *newline], "hyphenated_line_break_repair"),
            True,
        )
        return [*trimmed, marker, *next_line]

    def _space_join(
        self, line: list[_Unit], newline: list[_Unit], next_line: list[_Unit], transform: str
    ) -> list[_Unit]:
        bridge = newline or ([line[-1]] if line else next_line[:1])
        space = _Unit(
            " ",
            bridge[0].original_start,
            bridge[-1].original_end,
            self._merge_transformations(bridge, transform),
            True,
        )
        return [*line, space, *next_line]

    @staticmethod
    def _likely_wrap(left: str, right: str) -> bool:
        left = left.rstrip()
        right = right.lstrip()
        if not left or not right or len(left) < 20:
            return False
        if left[-1] in ".!?:;" or not right[0].islower():
            return False
        if (
            _LIST.match(left)
            or _LIST.match(right)
            or DocumentNormalizer._looks_heading(left)
            or DocumentNormalizer._looks_heading(right)
        ):
            return False
        if DocumentNormalizer._table_like(left) or DocumentNormalizer._table_like(right):
            return False
        return not (_URL_OR_PATH.search(left) or _CODEISH.search(left))

    @staticmethod
    def _looks_heading(value: str) -> bool:
        stripped = value.strip()
        if "RAGSCANNER_PAGE_BOUNDARY" in stripped or "RAGSCANNER_DOCX_BLOCK_BOUNDARY" in stripped:
            return False
        letters = "".join(character for character in stripped if character.isalpha())
        has_case = any(character.lower() != character.upper() for character in letters)
        return bool(_HEADING.match(value)) or (
            0 < len(stripped) <= 80 and bool(letters) and has_case and letters == letters.upper()
        )

    def _boilerplate(
        self,
        document: Document,
        units: list[_Unit],
        annotations: list[NormalizationAnnotation],
        statistics: NormalizationStatistics,
    ) -> None:
        pages = document.metadata.get("pages")
        if not isinstance(pages, list) or len(pages) < 2:
            return
        candidates: defaultdict[tuple[str, str], list[tuple[int, int, int]]] = defaultdict(list)
        for page in pages:
            if not isinstance(page, dict):
                continue
            page_number = page.get("page_number")
            start, end = page.get("start_offset"), page.get("end_offset")
            if (
                not isinstance(page_number, int)
                or not isinstance(start, int)
                or not isinstance(end, int)
            ):
                continue
            raw_lines = document.content[start:end].splitlines()
            visible = [
                (line_index, value.strip())
                for line_index, value in enumerate(raw_lines)
                if value.strip()
            ]
            if not visible:
                continue
            positions = [("header", visible[0]), ("footer", visible[-1])]
            page_cursor = start
            offsets: list[int] = []
            for raw in raw_lines:
                offsets.append(page_cursor)
                page_cursor += len(raw) + 1
            for kind, (line_index, value) in positions:
                normalized = " ".join(value.casefold().split())
                if len(normalized) <= 200:
                    candidates[(kind, normalized)].append(
                        (
                            page_number,
                            offsets[line_index],
                            offsets[line_index] + len(raw_lines[line_index]),
                        )
                    )
            for line_index, value in visible:
                if _PAGE_NUMBER.fullmatch(value):
                    candidates[("page_number", "<page-number>")].append(
                        (
                            page_number,
                            offsets[line_index],
                            offsets[line_index] + len(raw_lines[line_index]),
                        )
                    )
        for (kind, text), occurrences in sorted(candidates.items()):
            if kind != "page_number" and len(occurrences) < 2:
                continue
            original_start, original_end = occurrences[0][1], occurrences[0][2]
            normalized_start, normalized_end = self._normalized_range(
                units, original_start, original_end
            )
            annotation_type = {
                "header": AnnotationType.HEADER_CANDIDATE,
                "footer": AnnotationType.FOOTER_CANDIDATE,
                "page_number": AnnotationType.PAGE_NUMBER_CANDIDATE,
            }[kind]
            annotations.append(
                NormalizationAnnotation(
                    annotation_type=annotation_type,
                    normalized_start=normalized_start,
                    normalized_end=normalized_end,
                    original_start=original_start,
                    original_end=original_end,
                    normalized_text=text,
                    occurrence_count=len(occurrences),
                    pages=sorted({item[0] for item in occurrences}),
                    confidence=0.95 if len(occurrences) >= 3 else 0.8,
                    candidate_type=kind,
                    metadata={"removed": False},
                )
            )
            statistics.boilerplate_candidates += 1

    def _structural_annotations(
        self, document: Document, units: list[_Unit], annotations: list[NormalizationAnnotation]
    ) -> None:
        for line_number, value in enumerate(document.content.splitlines(), start=1):
            annotation_type: AnnotationType | None = None
            if _LIST.match(value):
                annotation_type = AnnotationType.LIST_REGION
            elif self._table_like(value):
                annotation_type = AnnotationType.TABLE_REGION
            elif self._looks_heading(value):
                annotation_type = AnnotationType.HEADING_REGION
            if annotation_type is not None:
                self._annotate_line(
                    document,
                    units,
                    annotations,
                    line_number,
                    annotation_type,
                    {"detected_from_text": True},
                )
        headings = document.metadata.get("headings")
        if isinstance(headings, list):
            for heading in headings:
                if isinstance(heading, dict) and isinstance(heading.get("line"), int):
                    self._annotate_line(
                        document,
                        units,
                        annotations,
                        heading["line"],
                        AnnotationType.HEADING_REGION,
                        {"level": heading.get("level")},
                    )
        blocks = document.metadata.get("blocks")
        if isinstance(blocks, list):
            mapping = {
                "heading": AnnotationType.HEADING_REGION,
                "list_item": AnnotationType.LIST_REGION,
                "table_cell": AnnotationType.TABLE_REGION,
                "page_break": AnnotationType.PAGE_BOUNDARY,
                "section_break": AnnotationType.SECTION_BOUNDARY,
                "header": AnnotationType.HEADER_REGION,
                "footer": AnnotationType.FOOTER_REGION,
            }
            for block in blocks:
                if not isinstance(block, dict) or block.get("block_type") not in mapping:
                    continue
                start, end = block.get("start_offset"), block.get("end_offset")
                if not isinstance(start, int) or not isinstance(end, int):
                    continue
                normalized_start, normalized_end = self._normalized_range(units, start, end)
                annotations.append(
                    NormalizationAnnotation(
                        annotation_type=mapping[block["block_type"]],
                        normalized_start=normalized_start,
                        normalized_end=normalized_end,
                        original_start=start,
                        original_end=end,
                        metadata={
                            "block_index": block.get("block_index"),
                            "section_index": block.get("section_index"),
                            "region": block.get("region"),
                        },
                    )
                )

    def _segments(
        self, document: Document, units: list[_Unit], warnings: list[NormalizationWarning]
    ) -> list[NormalizationSegment]:
        segments: list[NormalizationSegment] = []
        output_offset = 0
        for unit in units:
            start = output_offset
            output_offset += len(unit.value)
            location, metadata = self._source_location(
                document, unit.original_start, unit.original_end
            )
            candidate = NormalizationSegment(
                normalized_start=start,
                normalized_end=output_offset,
                original_start=unit.original_start,
                original_end=unit.original_end,
                source_location=location,
                transformation_types=list(unit.transformations),
                approximate=unit.approximate,
                metadata=metadata,
            )
            if segments and self._mergeable(segments[-1], candidate):
                segments[-1].normalized_end = candidate.normalized_end
                segments[-1].original_end = candidate.original_end
            else:
                segments.append(candidate)
        limit = self.config.maximum_normalization_segments
        if len(segments) <= limit:
            return segments
        warnings.append(
            NormalizationWarning(
                code="segment_limit_coalesced",
                message="Source mappings were coalesced to the configured segment limit.",
                metadata={"original_segment_count": len(segments), "limit": limit},
            )
        )
        while len(segments) > limit:
            merged: list[NormalizationSegment] = []
            for index in range(0, len(segments), 2):
                left = segments[index]
                if index + 1 >= len(segments):
                    merged.append(left)
                    continue
                right = segments[index + 1]
                merged.append(
                    NormalizationSegment(
                        normalized_start=left.normalized_start,
                        normalized_end=right.normalized_end,
                        original_start=min(left.original_start, right.original_start),
                        original_end=max(left.original_end, right.original_end),
                        source_location=left.source_location,
                        transformation_types=sorted(
                            set(left.transformation_types + right.transformation_types)
                        ),
                        approximate=True,
                        metadata={"coalesced": True},
                    )
                )
            segments = merged
        return segments

    def _source_location(
        self, document: Document, start: int, end: int
    ) -> tuple[SourceLocation, dict[str, Any]]:
        values = document.source.model_dump()
        values["line_start"] = document.content.count("\n", 0, start) + 1
        values["line_end"] = document.content.count("\n", 0, max(start, end - 1)) + 1
        metadata: dict[str, Any] = {}
        pages = document.metadata.get("pages")
        if isinstance(pages, list):
            for page in pages:
                if (
                    isinstance(page, dict)
                    and isinstance(page.get("start_offset"), int)
                    and isinstance(page.get("end_offset"), int)
                ):
                    if page["start_offset"] <= start <= page["end_offset"]:
                        values["page_number"] = page.get("page_number")
                        metadata["page_approximate"] = end > page["end_offset"]
                        break
        blocks = document.metadata.get("blocks")
        if isinstance(blocks, list):
            for block in blocks:
                if (
                    isinstance(block, dict)
                    and isinstance(block.get("start_offset"), int)
                    and isinstance(block.get("end_offset"), int)
                ):
                    if block["start_offset"] <= start <= block["end_offset"]:
                        metadata["parser_block"] = block.get("block_index")
                        metadata["block_type"] = block.get("block_type")
                        section = block.get("section_index")
                        values["section"] = (
                            str(section) if section is not None else values.get("section")
                        )
                        break
        return SourceLocation.model_validate(values), metadata

    def _bound_annotations(
        self,
        annotations: list[NormalizationAnnotation],
        warnings: list[NormalizationWarning],
    ) -> list[NormalizationAnnotation]:
        annotations.sort(
            key=lambda item: (
                item.normalized_start,
                item.normalized_end,
                item.annotation_type.value,
                item.candidate_type or "",
            )
        )
        if len(annotations) <= self.config.maximum_annotations:
            return annotations
        warnings.append(
            NormalizationWarning(
                code="annotation_limit_reached",
                message="Normalization annotations were bounded by configuration.",
                metadata={"detected": len(annotations), "limit": self.config.maximum_annotations},
            )
        )
        return annotations[: self.config.maximum_annotations]

    @staticmethod
    def _split_lines(units: list[_Unit]) -> list[tuple[list[_Unit], list[_Unit]]]:
        lines: list[tuple[list[_Unit], list[_Unit]]] = []
        current: list[_Unit] = []
        for unit in units:
            if unit.value == "\n":
                lines.append((current, [unit]))
                current = []
            else:
                current.append(unit)
        lines.append((current, []))
        return lines

    @staticmethod
    def _table_like(value: str) -> bool:
        stripped = value.strip()
        return stripped.count("|") >= 2 or bool(re.search(r"\S\s{2,}\S\s{2,}\S", value))

    @staticmethod
    def _ascii_diagram(value: str) -> bool:
        stripped = value.strip()
        if len(stripped) < 3:
            return False
        symbols = sum(character in "+-|><=_/\\[]()" for character in stripped)
        return symbols / len(stripped) >= 0.4

    @staticmethod
    def _is_page_marker(value: str) -> bool:
        return "<<<RAGSCANNER_PAGE_BOUNDARY:" in value

    @staticmethod
    def _merge_transformations(units: list[_Unit], added: str) -> tuple[str, ...]:
        return tuple(sorted({added, *(item for unit in units for item in unit.transformations)}))

    @staticmethod
    def _mergeable(left: NormalizationSegment, right: NormalizationSegment) -> bool:
        return (
            left.normalized_end == right.normalized_start
            and left.original_end == right.original_start
            and left.source_location == right.source_location
            and left.transformation_types == right.transformation_types
            and left.approximate == right.approximate
            and left.metadata == right.metadata
        )

    @staticmethod
    def _normalized_range(
        units: list[_Unit], original_start: int, original_end: int
    ) -> tuple[int, int]:
        cursor = 0
        starts: list[int] = []
        ends: list[int] = []
        for unit in units:
            next_cursor = cursor + len(unit.value)
            if unit.original_end > original_start and unit.original_start < original_end:
                starts.append(cursor)
                ends.append(next_cursor)
            cursor = next_cursor
        return (min(starts), max(ends)) if starts else (cursor, cursor)

    def _annotation_for_units(
        self,
        annotations: list[NormalizationAnnotation],
        annotation_type: AnnotationType,
        selected: list[_Unit],
        all_units: list[_Unit],
        metadata: dict[str, Any],
    ) -> None:
        if not selected:
            return
        original_start, original_end = selected[0].original_start, selected[-1].original_end
        start, end = self._normalized_range(all_units, original_start, original_end)
        annotations.append(
            NormalizationAnnotation(
                annotation_type=annotation_type,
                normalized_start=start,
                normalized_end=end,
                original_start=original_start,
                original_end=original_end,
                metadata=metadata,
            )
        )

    def _annotate_line(
        self,
        document: Document,
        units: list[_Unit],
        annotations: list[NormalizationAnnotation],
        line_number: int,
        annotation_type: AnnotationType,
        metadata: dict[str, Any],
    ) -> None:
        starts = [0]
        starts.extend(index + 1 for index, value in enumerate(document.content) if value == "\n")
        if line_number < 1 or line_number > len(starts):
            return
        start = starts[line_number - 1]
        end = document.content.find("\n", start)
        end = len(document.content) if end < 0 else end
        normalized_start, normalized_end = self._normalized_range(units, start, end)
        annotations.append(
            NormalizationAnnotation(
                annotation_type=annotation_type,
                normalized_start=normalized_start,
                normalized_end=normalized_end,
                original_start=start,
                original_end=end,
                metadata=metadata,
            )
        )
