from pathlib import Path

import pytest
from ragscanner.quality.calibration import (
    CalibrationCase,
    evaluate_calibration_cases,
    run_security_calibration,
)

FIXTURE_MANIFEST = (
    Path(__file__).parents[1] / "fixtures" / "calibration" / "security" / "manifest.json"
)


def test_evaluator_reports_false_positives_negatives_and_intervals() -> None:
    positive = CalibrationCase(
        id="positive",
        path="positive.txt",
        language="en",
        format="text",
        expected_rule_ids={"RULE-1"},
    )
    negative = CalibrationCase(
        id="negative",
        path="negative.txt",
        language="tr",
        format="text",
    )
    report = evaluate_calibration_cases(
        corpus_name="unit",
        results=[(positive, set()), (negative, {"RULE-1"})],
    )

    assert report.aggregate.precision == 0
    assert report.aggregate.recall == 0
    assert report.aggregate.counts.false_positive == 1
    assert report.aggregate.counts.false_negative == 1
    assert report.aggregate.precision_interval_95 is not None
    assert report.by_language["en"].counts.false_negative == 1
    assert report.by_language["tr"].counts.false_positive == 1


def test_six_language_security_fixture_is_reproducible() -> None:
    report = run_security_calibration(FIXTURE_MANIFEST)

    assert report.cases == 12
    assert report.aggregate.precision == 1
    assert report.aggregate.recall == 1
    assert report.aggregate.f1 == 1
    assert set(report.by_language) == {"de", "en", "fr", "it", "tr", "zh-CN"}
    assert not any(
        case.false_positive_rule_ids or case.false_negative_rule_ids for case in report.case_results
    )


def test_calibration_rejects_paths_outside_the_corpus(tmp_path: Path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("safe", encoding="utf-8")
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    manifest = corpus / "manifest.json"
    manifest.write_text(
        '{"corpus_name":"bad","cases":[{"id":"escape","path":"../outside.txt",'
        '"language":"en","format":"text","expected_rule_ids":[]}]}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="escapes"):
        run_security_calibration(manifest)
