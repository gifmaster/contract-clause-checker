"""Score the checker against the real-world answer key (tests/real_world_truth.yaml).

Used by tests/test_real_world.py and by scripts/real_world_report.py, so the table in the docs is produced by the same code that CI runs.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from clausecheck import Rules, analyse, read_file

ROOT = Path(__file__).parents[1]
TRUTH = yaml.safe_load((Path(__file__).parent / "real_world_truth.yaml").read_text(encoding="utf-8"))["docs"]


def evaluate(name: str, rules: Rules | None = None) -> dict:
    rules = rules or Rules.builtin()
    truth = TRUTH[name]
    result = analyse(read_file(ROOT / "samples" / name), rules, gdpr=True)
    core_ids = {k["id"] for k in rules.checks}
    want = set(truth["findings"])
    scored = set(truth["scope"]) if truth.get("scope") else (core_ids | want)
    scored -= set(truth.get("ignore", []))
    got = {f.id for f in result.findings if f.pack == "core"} & scored
    want &= scored
    found = {s.clause for s in result.segments if s.clause}
    out = {
        "name": name,
        "kind": truth["kind"],
        "tp": sorted(got & want),
        "fp": sorted(got - want),
        "fn": sorted(want - got),
        "clauses_missed": sorted(set(truth.get("clauses", [])) - found),
        "clauses_expected": len(truth.get("clauses", [])),
        "dpa_elsewhere": (result.dpa_elsewhere, truth.get("dpa_elsewhere")),
        "is_dpa": (result.is_dpa, truth.get("is_dpa")),
    }
    if truth["kind"] == "dpa":
        g_got = {f.id for f in result.findings if f.pack == "gdpr"}
        g_want = set(truth["gdpr"])
        out.update(g_tp=sorted(g_got & g_want), g_fp=sorted(g_got - g_want), g_fn=sorted(g_want - g_got))
    return out


def totals(rows: list[dict]) -> dict:
    tp = sum(len(r["tp"]) for r in rows)
    fp = sum(len(r["fp"]) for r in rows)
    fn = sum(len(r["fn"]) for r in rows)
    gtp = sum(len(r.get("g_tp", [])) for r in rows)
    gfp = sum(len(r.get("g_fp", [])) for r in rows)
    gfn = sum(len(r.get("g_fn", [])) for r in rows)
    ce = sum(r["clauses_expected"] for r in rows)
    cm = sum(len(r["clauses_missed"]) for r in rows)
    ratio = lambda a, b: (a / b) if b else 1.0
    return {
        "checks_precision": ratio(tp, tp + fp), "checks_recall": ratio(tp, tp + fn),
        "gdpr_precision": ratio(gtp, gtp + gfp), "gdpr_recall": ratio(gtp, gtp + gfn),
        "clause_recall": ratio(ce - cm, ce), "clauses_found": ce - cm, "clauses_expected": ce,
        "tp": tp, "fp": fp, "fn": fn, "g_tp": gtp, "g_fp": gfp, "g_fn": gfn,
    }
