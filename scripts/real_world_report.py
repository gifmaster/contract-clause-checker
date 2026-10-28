"""Print the real-world accuracy table. Run from the repository root: python scripts/real_world_report.py"""

import sys
from pathlib import Path

root = Path(__file__).parents[1]
sys.path[:0] = [str(root / "src"), str(root / "tests")]

from real_world_eval import TRUTH, evaluate, totals  # noqa: E402

rows = [evaluate(n) for n in TRUTH]
print("| Document | Kind | Missed (FN) | Wrongly flagged (FP) | Clauses found | Other |")
print("|---|---|---|---|---|---|")
for r in rows:
    other = []
    if r["dpa_elsewhere"][1] is not None and r["dpa_elsewhere"][0] != r["dpa_elsewhere"][1]:
        other.append(f"DPA elsewhere: got {r['dpa_elsewhere'][0]}, want {r['dpa_elsewhere'][1]}")
    if r["is_dpa"][1] is not None and r["is_dpa"][0] != r["is_dpa"][1]:
        other.append(f"Recognised as DPA: got {r['is_dpa'][0]}, want {r['is_dpa'][1]}")
    if r["kind"] == "dpa":
        other.append(f"GDPR pack FN {r['g_fn'] or '-'} FP {r['g_fp'] or '-'}")
    found = r["clauses_expected"] - len(r["clauses_missed"])
    print(f"| {Path(r['name']).name} | {r['kind']} | {', '.join(r['fn']) or '-'} | {', '.join(r['fp']) or '-'} "
          f"| {found}/{r['clauses_expected']} | {'; '.join(other) or '-'} |")
t = totals(rows)
print()
print(f"Core checks: precision {t['checks_precision']:.2f} ({t['tp']} right, {t['fp']} wrongly flagged), recall {t['checks_recall']:.2f} ({t['fn']} missed)")
print(f"GDPR pack on the two real DPAs: precision {t['gdpr_precision']:.2f}, recall {t['gdpr_recall']:.2f} (FP {t['g_fp']}, FN {t['g_fn']})")
print(f"Clause detection: {t['clauses_found']} of {t['clauses_expected']}")
