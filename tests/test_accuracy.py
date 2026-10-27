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
RESULTS = {name: analyse(read_file(ROOT / "samples" / name), RULES, dora="critical", gdpr=True, nis2=True) for name in TRUTH}
# Samples written for one pack are scored on that pack only: DPAs on GDPR, NIS2 contracts on NIS2.
CONTRACTS = [n for n, t in TRUTH.items() if not t.get("kind")]
GDPR_SAMPLES = [n for n, t in TRUTH.items() if t.get("kind") in (None, "dpa")]
NIS2_SAMPLES = [n for n, t in TRUTH.items() if "nis2" in t]


def core(result):
    return {f.id for f in result.findings if f.pack == "core"}


def dora(result):
    return {f.id for f in result.findings if f.pack == "dora"}


def gdpr(result):
    return {f.id for f in result.findings if f.pack == "gdpr"}


def nis2(result):
    return {f.id for f in result.findings if f.pack == "nis2"}


@pytest.mark.parametrize("name", CONTRACTS)
def test_clauses_found_where_expected(name):
    result = RESULTS[name]
    for clause, heading in TRUTH[name]["clauses"].items():
        headings = [s.heading for s in result.clauses.get(clause, [])]
        assert heading in headings, f"{name}: {clause} expected at '{heading}', found {headings}"


@pytest.mark.parametrize("name", CONTRACTS)
def test_findings_exactly_as_labelled(name):
    got = core(RESULTS[name])
    want = set(TRUTH[name]["findings"])
    assert got == want, f"{name}: missing {want - got}, unexpected {got - want}"


@pytest.mark.parametrize("name", CONTRACTS)
def test_dora_findings_exactly_as_labelled(name):
    got = dora(RESULTS[name])
    want = set(TRUTH[name]["dora"])
    assert got == want, f"{name}: missing {want - got}, unexpected {got - want}"


@pytest.mark.parametrize("name", CONTRACTS)
def test_values_extracted(name):
    values = RESULTS[name].values
    for key, want in TRUTH[name]["values"].items():
        assert values.get(key) == want, f"{name}: {key} expected {want!r}, got {values.get(key)!r}"


@pytest.mark.parametrize("name", NIS2_SAMPLES)
def test_nis2_findings_exactly_as_labelled(name):
    got = nis2(RESULTS[name])
    want = set(TRUTH[name]["nis2"])
    assert got == want, f"{name}: missing {want - got}, unexpected {got - want}"


@pytest.mark.parametrize("name", GDPR_SAMPLES)
def test_gdpr_findings_exactly_as_labelled(name):
    got = gdpr(RESULTS[name])
    want = set(TRUTH[name]["gdpr"])
    assert got == want, f"{name}: missing {want - got}, unexpected {got - want}"


@pytest.mark.parametrize("name", GDPR_SAMPLES)
def test_separate_dpa_is_recognised(name):
    assert RESULTS[name].dpa_elsewhere == TRUTH[name]["dpa_elsewhere"], name


def test_overall_precision_and_recall():
    """Across all samples: clause detection and checks must stay at or above 0.9."""
    tp = fp = fn = 0
    for name, truth in TRUTH.items():
        result = RESULTS[name]
        if truth.get("kind"):
            pack = {"dpa": ("gdpr", gdpr), "nis2": ("nis2", nis2)}[truth["kind"]]
            fw, gw = set(truth[pack[0]]), pack[1](result)
            tp, fn, fp = tp + len(fw & gw), fn + len(fw - gw), fp + len(gw - fw)
            continue
        want = {(c, h) for c, h in truth["clauses"].items()}
        got = {(s.clause, s.heading) for s in result.segments if s.clause}
        # a clause counts as correct if the labelled heading was found for that type
        tp += len(want & got)
        fn += len(want - got)
        fp += len({g for g in got if g[0] not in truth["clauses"]})
        fw = set(truth["findings"]) | set(truth["dora"]) | set(truth["gdpr"]) | set(truth["nis2"])
        gw = {f.id for f in result.findings}
        tp += len(fw & gw)
        fn += len(fw - gw)
        fp += len(gw - fw)
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    assert precision >= 0.9 and recall >= 0.9, f"precision {precision:.2f}, recall {recall:.2f}"


def test_every_finding_has_evidence_or_is_a_missing_clause():
    missing_type = {k["id"] for k in RULES.all_checks if k["type"] in ("missing", "absent")}
    for name, result in RESULTS.items():
        for f in result.findings:
            assert f.evidence or f.id in missing_type, f"{name}: {f.id} has no evidence"


@pytest.mark.parametrize("fmt", ["docx", "pdf"])
def test_same_result_from_pdf_and_word(fmt):
    """The same contract as PDF or Word must give the same findings and key terms as plain text."""
    base = RESULTS["01_brightloop_ai_terms_EN.txt"]
    other = analyse(read_file(ROOT / "samples" / f"04_brightloop_ai_terms_EN.{fmt}"), RULES, dora="critical", gdpr=True, nis2=True)
    assert {f.id for f in other.findings} == {f.id for f in base.findings}
    assert {k: v for k, v in other.values.items() if k != "liability_cap"} == {k: v for k, v in base.values.items() if k != "liability_cap"}
