"""The checker on real, publicly published contracts (see samples/real/NOTICE.md and tests/real_world_truth.yaml)."""

import pytest

from real_world_eval import TRUTH, evaluate, totals


@pytest.mark.parametrize("name", list(TRUTH))
def test_document_exactly_as_labelled(name):
    r = evaluate(name)
    assert r["fn"] == sorted(TRUTH[name].get("known_misses", [])), f"{name}: missed {r['fn']}"
    assert not r["fp"], f"{name}: wrongly flagged {r['fp']}"
    assert not r["clauses_missed"], f"{name}: clauses not found {r['clauses_missed']}"
    for key in ("dpa_elsewhere", "is_dpa"):
        got, want = r[key]
        if want is not None:
            assert got == want, f"{name}: {key} is {got}, expected {want}"
    if r["kind"] == "dpa":
        assert not r["g_fn"] and not r["g_fp"], f"{name}: GDPR pack missed {r['g_fn']}, wrongly flagged {r['g_fp']}"


def test_overall_numbers():
    t = totals([evaluate(n) for n in TRUTH])
    assert t["checks_precision"] == 1.0
    assert t["checks_recall"] >= 0.95  # one documented miss (the AI addendum)
    assert t["clause_recall"] == 1.0
