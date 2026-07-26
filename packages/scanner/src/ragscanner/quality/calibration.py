"""Labelled-corpus calibration for deterministic static security rules."""

import asyncio
import math
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CalibrationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=160)
    path: str = Field(min_length=1, max_length=4_096)
    language: str = Field(min_length=1, max_length=32)
    format: str = Field(min_length=1, max_length=80)
    expected_rule_ids: set[str] = Field(default_factory=set)


class CalibrationManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0.0"
    corpus_name: str = Field(min_length=1, max_length=240)
    root: str = "."
    cases: list[CalibrationCase] = Field(min_length=1, max_length=10_000)

    @model_validator(mode="after")
    def validate_case_ids(self) -> "CalibrationManifest":
        identifiers = [case.id for case in self.cases]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("calibration case IDs must be unique")
        return self


class ClassificationCounts(BaseModel):
    true_positive: int = Field(ge=0)
    false_positive: int = Field(ge=0)
    false_negative: int = Field(ge=0)
    true_negative: int = Field(ge=0)


class CalibrationMetrics(BaseModel):
    counts: ClassificationCounts
    precision: float | None = Field(default=None, ge=0, le=1)
    precision_interval_95: tuple[float, float] | None = None
    recall: float | None = Field(default=None, ge=0, le=1)
    recall_interval_95: tuple[float, float] | None = None
    f1: float | None = Field(default=None, ge=0, le=1)
    false_positive_rate: float | None = Field(default=None, ge=0, le=1)


class CalibrationCaseResult(BaseModel):
    id: str
    language: str
    format: str
    expected_rule_ids: list[str]
    predicted_rule_ids: list[str]
    false_positive_rule_ids: list[str]
    false_negative_rule_ids: list[str]


class CalibrationReport(BaseModel):
    schema_version: str = "1.0.0"
    corpus_name: str
    scanner: str = "static_security_scanner"
    scanner_version: str | None = None
    rule_pack_versions: list[str] = Field(default_factory=list)
    cases: int = Field(ge=1)
    aggregate: CalibrationMetrics
    by_rule: dict[str, CalibrationMetrics]
    by_language: dict[str, CalibrationMetrics]
    by_format: dict[str, CalibrationMetrics]
    case_results: list[CalibrationCaseResult]
    limitations: list[str]


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _wilson(successes: int, total: int) -> tuple[float, float] | None:
    if not total:
        return None
    z = 1.959963984540054
    proportion = successes / total
    denominator = 1 + z * z / total
    centre = (proportion + z * z / (2 * total)) / denominator
    margin = (
        z
        * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total))
        / denominator
    )
    return max(0.0, centre - margin), min(1.0, centre + margin)


def _metrics(counts: ClassificationCounts) -> CalibrationMetrics:
    precision = _ratio(counts.true_positive, counts.true_positive + counts.false_positive)
    recall = _ratio(counts.true_positive, counts.true_positive + counts.false_negative)
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    return CalibrationMetrics(
        counts=counts,
        precision=precision,
        precision_interval_95=_wilson(
            counts.true_positive, counts.true_positive + counts.false_positive
        ),
        recall=recall,
        recall_interval_95=_wilson(
            counts.true_positive, counts.true_positive + counts.false_negative
        ),
        f1=f1,
        false_positive_rate=_ratio(
            counts.false_positive, counts.false_positive + counts.true_negative
        ),
    )


def _count(rows: list[tuple[set[str], set[str]]], rule_ids: set[str]) -> ClassificationCounts:
    tp = fp = fn = tn = 0
    for expected, predicted in rows:
        for rule_id in rule_ids:
            wanted = rule_id in expected
            found = rule_id in predicted
            if wanted and found:
                tp += 1
            elif found:
                fp += 1
            elif wanted:
                fn += 1
            else:
                tn += 1
    return ClassificationCounts(
        true_positive=tp,
        false_positive=fp,
        false_negative=fn,
        true_negative=tn,
    )


def evaluate_calibration_cases(
    *,
    corpus_name: str,
    results: list[tuple[CalibrationCase, set[str]]],
    scanner_version: str | None = None,
    rule_pack_versions: list[str] | None = None,
) -> CalibrationReport:
    universe = {
        rule_id for case, predicted in results for rule_id in case.expected_rule_ids | predicted
    }
    rows = [(case.expected_rule_ids, predicted) for case, predicted in results]
    aggregate = _metrics(_count(rows, universe))
    by_rule = {rule_id: _metrics(_count(rows, {rule_id})) for rule_id in sorted(universe)}

    def grouped(attribute: str) -> dict[str, CalibrationMetrics]:
        values = sorted({str(getattr(case, attribute)) for case, _predicted in results})
        output: dict[str, CalibrationMetrics] = {}
        for value in values:
            selected = [
                (case.expected_rule_ids, predicted)
                for case, predicted in results
                if str(getattr(case, attribute)) == value
            ]
            output[value] = _metrics(_count(selected, universe))
        return output

    case_results = [
        CalibrationCaseResult(
            id=case.id,
            language=case.language,
            format=case.format,
            expected_rule_ids=sorted(case.expected_rule_ids),
            predicted_rule_ids=sorted(predicted),
            false_positive_rule_ids=sorted(predicted - case.expected_rule_ids),
            false_negative_rule_ids=sorted(case.expected_rule_ids - predicted),
        )
        for case, predicted in results
    ]
    return CalibrationReport(
        corpus_name=corpus_name,
        scanner_version=scanner_version,
        rule_pack_versions=rule_pack_versions or [],
        cases=len(results),
        aggregate=aggregate,
        by_rule=by_rule,
        by_language=grouped("language"),
        by_format=grouped("format"),
        case_results=case_results,
        limitations=[
            "Metrics describe only the labelled corpus and enabled deterministic rules.",
            "Confidence intervals quantify sampling uncertainty, not coverage of unseen attacks.",
            "Language and format slices require enough positive and negative cases to be meaningful.",
        ],
    )


def run_security_calibration(manifest_path: Path) -> CalibrationReport:
    """Run isolated local scans for each labelled case without persisting source content."""

    from ragscanner.pipeline import StaticPipelineConfig, StaticScanPipeline

    manifest_path = manifest_path.expanduser().resolve(strict=True)
    manifest = CalibrationManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    corpus_root = (manifest_path.parent / manifest.root).resolve(strict=True)
    if not corpus_root.is_dir():
        raise ValueError("calibration root must be a directory")
    resolved: list[tuple[CalibrationCase, Path]] = []
    for case in manifest.cases:
        candidate = (corpus_root / case.path).resolve(strict=True)
        try:
            candidate.relative_to(corpus_root)
        except ValueError as error:
            raise ValueError("calibration case path escapes the corpus root") from error
        if not candidate.is_file():
            raise ValueError("calibration cases must reference files")
        resolved.append((case, candidate))

    outputs: list[tuple[CalibrationCase, set[str]]] = []
    scanner_version: str | None = None
    pack_versions: set[str] = set()
    for case, candidate in resolved:
        result = asyncio.run(
            StaticScanPipeline(
                StaticPipelineConfig(
                    source_path=candidate,
                    exact_duplicates_enabled=False,
                    near_duplicates_enabled=False,
                    chunk_quality_enabled=False,
                )
            ).run()
        )
        outputs.append(
            (
                case,
                {
                    finding.rule_id
                    for finding in result.findings
                    if finding.scanner == "static_security_scanner"
                },
            )
        )
        scanner_version = result.scan.scanner_version
        if result.scan.rule_pack_version:
            pack_versions.update(result.scan.rule_pack_version.split(","))
    return evaluate_calibration_cases(
        corpus_name=manifest.corpus_name,
        results=outputs,
        scanner_version=scanner_version,
        rule_pack_versions=sorted(pack_versions),
    )
