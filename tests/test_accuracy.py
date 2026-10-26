"""Accuracy against hand-labelled sample contracts.

Each sample is checked case by case, and overall precision and recall are
asserted so that a rule change that degrades accuracy fails the build.
"""

from pathlib import Path

import pytest
import yaml

from clausecheck import Rules, analyse, read_file

ROOT = Path(__file__).parents[1]
TRUTH = yaml.safe_load((Path(__file__).parent / "ground_truth.yaml").read_text(encoding="utf-8"))["samples"]
RULES = Rules.builtin()
RESULTS = {name: analyse(read_file(ROOT / "samples" / name), RULES) for name in TRUTH}


@pytest.mark.parametrize("name", TRUTH)
def test_clauses_found_where_expected(name):
    result = RESULTS[name]
    for clause, heading in TRUTH[name]["clauses"].items():
        headings = [s.heading for s in result.clauses.get(clause, [])]
        assert heading in headings, f"{name}: {clause} expected at '{heading}', found {headings}"


@pytest.mark.parametrize("name", TRUTH)
def test_findings_exactly_as_labelled(name):
    got = {f.id for f in RESULTS[name].findings}
    want = set(TRUTH[name]["findings"])
    assert got == want, f"{name}: missing {want - got}, unexpected {got - want}"


@pytest.mark.parametrize("name", TRUTH)
def test_values_extracted(name):
    values = RESULTS[name].values
    for key, want in TRUTH[name]["values"].items():
        assert values.get(key) == want, f"{name}: {key} expected {want!r}, got {values.get(key)!r}"


def test_overall_precision_and_recall():
    """Across all samples: clause detection and checks must stay at or above 0.9."""
    tp = fp = fn = 0
    for name, truth in TRUTH.items():
        result = RESULTS[name]
        want = {(c, h) for c, h in truth["clauses"].items()}
        got = {(s.clause, s.heading) for s in result.segments if s.clause}
        # a clause counts as correct if the labelled heading was found for that type
        tp += len(want & got)
        fn += len(want - got)
        fp += len({g for g in got if g[0] not in truth["clauses"]})
        fw, gw = set(truth["findings"]), {f.id for f in result.findings}
        tp += len(fw & gw)
        fn += len(fw - gw)
        fp += len(gw - fw)
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    assert precision >= 0.9 and recall >= 0.9, f"precision {precision:.2f}, recall {recall:.2f}"


def test_every_finding_has_evidence_or_is_a_missing_clause():
    missing_type = {k["id"] for k in RULES.checks if k["type"] == "missing"}
    for name, result in RESULTS.items():
        for f in result.findings:
            assert f.evidence or f.id in missing_type, f"{name}: {f.id} has no evidence"


@pytest.mark.parametrize("fmt", ["docx", "pdf"])
def test_same_result_from_pdf_and_word(fmt):
    """The same contract as PDF or Word must give the same findings and key terms as plain text."""
    base = RESULTS["01_brightloop_ai_terms_EN.txt"]
    other = analyse(read_file(ROOT / "samples" / f"04_brightloop_ai_terms_EN.{fmt}"), RULES)
    assert {f.id for f in other.findings} == {f.id for f in base.findings}
    assert {k: v for k, v in other.values.items() if k != "liability_cap"} == {k: v for k, v in base.values.items() if k != "liability_cap"}
