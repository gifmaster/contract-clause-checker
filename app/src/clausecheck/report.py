"""Reports: a Markdown review summary and a CSV clause table."""

from __future__ import annotations

import csv
import io
from datetime import date

from .engine import Result, Rules

SEV_LABEL = {"high": "High", "medium": "Medium", "low": "Low"}
VALUE_LABELS = {
    "governing_law": "Governing law",
    "initial_term": "Initial term",
    "auto_renewal": "Automatic renewal",
    "notice_periods": "Notice periods mentioned",
    "liability_cap": "Liability cap",
    "uptime": "Availability (SLA)",
}


def format_value(key: str, value) -> str:
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, list):
        return ", ".join(value)
    return str(value)


def to_markdown(result: Result, rules: Rules, name: str = "", today: date | None = None) -> str:
    today = today or date.today()
    core = [f for f in result.findings if f.pack == "core"]
    high = sum(f.severity == "high" for f in core)
    lines = [
        f"# Contract review: {name or 'Uploaded contract'}",
        "",
        f"- **Date:** {today.isoformat()}",
        f"- **Language detected:** {'Danish' if result.language == 'da' else 'English'}",
        f"- **Findings:** {len(core)} ({high} high)",
        "",
        "## Key terms",
        "",
    ]
    for k, label in VALUE_LABELS.items():
        if k in result.values:
            lines.append(f"- **{label}:** {format_value(k, result.values[k])}")
    lines += ["", "## Findings", ""]
    if result.is_dpa:
        lines += ["*This document is a data processing agreement on its own, so only the contract checks that matter for a DPA "
                  "are shown. Liability, termination and governing law belong in the main agreement.*", ""]
    if not core:
        lines.append("No issues flagged by the checks.")
    for f in core:
        lines += [f"### [{SEV_LABEL[f.severity]}] {f.title}", "", f"{f.why} *({f.ref})*", ""]
        for e in f.evidence:
            lines.append(f"> {e}")
            lines.append("")
    gdpr = result.gdpr_checklist(rules)
    if gdpr:
        covered = sum(ok for _, ok in gdpr)
        lines += ["## GDPR data processing terms", "",
                  f"Checked against GDPR Art. 28(2) to (4). Covered in this document: **{covered} of {len(gdpr)}**.", ""]
        if result.dpa_elsewhere:
            lines += ["> **The data processing agreement is a separate document.** This contract points to it, so these terms "
                      "are expected there. Run the check on the data processing agreement itself.", ""]
        lines += ["| | Term | Reference | Severity if missing |", "|---|---|---|---|"]
        for k, ok in gdpr:
            lines.append(f"| {'Covered' if ok else '**Not found**'} | {k['looked_for'][0].upper() + k['looked_for'][1:]} | {k['ref']} | {SEV_LABEL[k['severity']]} |")
        lines += ["", "*Covered means wording for the term was found. It does not mean the wording is good enough, "
                  "for example how fast breaches are reported.*", ""]
    nis2 = result.nis2_checklist(rules)
    if nis2:
        covered = sum(ok for _, ok in nis2)
        lines += ["## NIS2 supply chain terms", "",
                  f"Checked against NIS2 Art. 21(2)(d) and point 5.1.4 of the Annex to Implementing Regulation (EU) 2024/2690. "
                  f"Covered in the main text: **{covered} of {len(nis2)}**.", "",
                  "| | Term | Reference | Severity if missing |", "|---|---|---|---|"]
        for k, ok in nis2:
            lines.append(f"| {'Covered' if ok else '**Not found**'} | {k['looked_for'][0].upper() + k['looked_for'][1:]} | {k['ref']} | {SEV_LABEL[k['severity']]} |")
        lines += ["", "*The list in Implementing Regulation (EU) 2024/2690 is binding for digital infrastructure and ICT service "
                  "providers such as cloud, data centres and managed service providers. For other NIS2 entities it is the most "
                  "concrete reading of Art. 21(2)(d), to apply where your supply chain risk assessment calls for it. "
                  "Check appendices before concluding that a term is missing.*", ""]
    checklist = result.dora_checklist(rules)
    if checklist:
        covered = sum(ok for _, ok in checklist)
        scope = "all ICT services, Art. 30(2)" if result.dora == "all" else "ICT services supporting critical or important functions, Art. 30(2) and (3)"
        lines += ["## DORA key contractual provisions", "",
                  f"Checked as: {scope}. Covered in the main text: **{covered} of {len(checklist)}**.", "",
                  "| | Provision | Reference | Severity if missing |", "|---|---|---|---|"]
        for k, ok in checklist:
            lines.append(f"| {'Covered' if ok else '**Not found**'} | {k['looked_for'][0].upper() + k['looked_for'][1:]} | {k['ref']} | {SEV_LABEL[k['severity']]} |")
        lines += ["", "*Not found means the wording was not found in the main contract text. Check appendices and referenced documents before concluding that a term is missing.*", ""]
    lines += ["## Clauses found", "", "| Clause | Found | Where |", "|---|---|---|"]
    for cid, label in rules.labels.items():
        segs = result.clauses.get(cid, [])
        lines.append(f"| {label} | {'Yes' if segs else 'No'} | {'; '.join(s.heading for s in segs) if segs else ''} |")
    lines += ["", "---", "", "*Automated screening to support contract review. Not legal advice. A qualified person should review the full contract.*", ""]
    return "\n".join(lines)


def to_csv(result: Result, rules: Rules) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["clause_type", "label", "heading", "text"])
    for s in result.segments:
        if s.clause:
            w.writerow([s.clause, rules.labels[s.clause], s.heading, " ".join(s.text.split())])
    return "﻿" + out.getvalue()
