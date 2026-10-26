"""Contract clause checker: segment, classify, extract key values, run risk checks.

All knowledge about clause types and risks lives in YAML files in ``rules/``.
The code only applies them, so every result can be traced to a rule.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

RULES_DIR = Path(__file__).parent / "rules"
FLAGS = re.IGNORECASE

# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #


@dataclass
class Segment:
    index: int
    heading: str
    text: str
    clause: str | None = None
    score: int = 0

    @property
    def full(self) -> str:
        return f"{self.heading}\n{self.text}".strip()


@dataclass
class Finding:
    id: str
    severity: str
    title: str
    why: str
    ref: str
    evidence: list[str] = field(default_factory=list)
    pack: str = "core"
    looked_for: str = ""


@dataclass
class Result:
    segments: list[Segment]
    clauses: dict[str, list[Segment]]
    values: dict[str, Any]
    findings: list[Finding]
    language: str
    dora: str | None = None

    def dora_checklist(self, rules: "Rules") -> list[tuple[dict, bool]]:
        """Each DORA check that ran, with True when the contract covers it."""
        if not self.dora:
            return []
        fired = {f.id for f in self.findings}
        return [(k, k["id"] not in fired) for k in rules.dora if k["level"] in DORA_LEVELS[self.dora]]

    def found(self, clause_id: str) -> bool:
        return bool(self.clauses.get(clause_id))


SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
DORA_LEVELS = {"all": ("all",), "critical": ("all", "critical")}  # which check levels run for each choice

# --------------------------------------------------------------------------- #
# Rules
# --------------------------------------------------------------------------- #


class Rules:
    def __init__(self, clauses: dict, checks: dict, dora: dict | None = None):
        self.min_score = clauses.get("min_score", 3)
        self.clauses = clauses["clauses"]
        self.labels = {c["id"]: c["label"] for c in self.clauses}
        self.checks = checks["checks"]
        for k in self.checks:
            k.setdefault("pack", "core")
        self.dora = (dora or {}).get("checks", [])
        for k in self.dora:
            k["pack"] = "dora"
        self._compile()
        self._validate()

    @classmethod
    def builtin(cls) -> "Rules":
        load = lambda n: yaml.safe_load((RULES_DIR / n).read_text(encoding="utf-8"))  # noqa: E731
        return cls(load("clauses.yaml"), load("checks.yaml"), load("dora.yaml"))

    @property
    def all_checks(self) -> list[dict]:
        return self.checks + self.dora

    def _compile(self) -> None:
        for c in self.clauses:
            c["_heading"] = [re.compile(p, FLAGS) for p in c.get("heading", [])]
            c["_body"] = [re.compile(p, FLAGS) for p in c.get("body", [])]
        for k in self.all_checks:
            for key in ("pattern", "unless", "without", "if_any", "then_any"):
                if key in k:
                    k["_" + key] = [re.compile(p, FLAGS) for p in k[key]]

    def _validate(self) -> None:
        ids = set(self.labels)
        seen = set()
        for k in self.all_checks:
            if k.get("pack") == "dora":
                if k.get("level") not in DORA_LEVELS:
                    raise ValueError(f"DORA check {k['id']} needs level 'all' or 'critical'")
                if not k.get("looked_for"):
                    raise ValueError(f"DORA check {k['id']} is missing 'looked_for'")
            if k["id"] in seen:
                raise ValueError(f"Duplicate check id {k['id']}")
            seen.add(k["id"])
            if k["severity"] not in SEVERITY_ORDER:
                raise ValueError(f"Check {k['id']} has unknown severity {k['severity']}")
            for f in ("title", "why", "ref"):
                if not k.get(f):
                    raise ValueError(f"Check {k['id']} is missing '{f}'")
            clause = k.get("clause") or (k.get("scope") if k.get("scope") != "all" else None)
            if clause and clause not in ids:
                raise ValueError(f"Check {k['id']} refers to unknown clause {clause}")


# --------------------------------------------------------------------------- #
# Segmentation
# --------------------------------------------------------------------------- #

HEADING_RE = re.compile(
    r"""^\s*(
        (?:\d{1,2}(?:\.\d{1,2}){0,2}\.?)\s+[A-ZÆØÅ][^\n]{0,90}          # 1. Term / 4.2 Fees
      | (?:[Ss]ection|SECTION|[Cc]lause|CLAUSE|[Aa]rticle|ARTICLE|[Pp]unkt|PUNKT|§)\s*\d{1,2}\.?[^\n]{0,90}  # Section 5 ...
      | [A-ZÆØÅ][A-ZÆØÅ0-9 &,/.\-]{3,60}                               # ALL CAPS HEADING
    )\s*$""",
    re.VERBOSE,
)
NUMBER_ONLY_SUBCLAUSE = re.compile(r"^\s*\d{1,2}\.\d{1,2}\.?\s+")


def _is_heading(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 95:
        return False
    if not HEADING_RE.match(line):
        return False
    # A numbered sub-clause (4.2) that ends like a sentence is text, not a heading, even when it is short:
    # "6.2 The Supplier cooperates fully with the authority."
    if NUMBER_ONLY_SUBCLAUSE.match(line) and line.rstrip().endswith((".", ";")) and len(line.split()) > 4:
        return False
    if NUMBER_ONLY_SUBCLAUSE.match(line) and line.rstrip().endswith(":") and len(line.split()) > 8:
        return False
    return True


def segment(text: str) -> list[Segment]:
    segments: list[Segment] = []
    heading, buf = "", []
    for raw in text.splitlines():
        line = raw.rstrip()
        if _is_heading(line):
            if heading or any(b.strip() for b in buf):
                segments.append(Segment(len(segments), heading, "\n".join(buf).strip()))
            heading, buf = line.strip(), []
        else:
            buf.append(line)
    if heading or any(b.strip() for b in buf):
        segments.append(Segment(len(segments), heading, "\n".join(buf).strip()))
    return [s for s in segments if s.full]


NUMBERED = re.compile(r"^\s*(\d{1,2}(\.\d{1,2})*\.?\s|(section|clause|article|punkt|§)\s*\d)", FLAGS)


def classify(segments: list[Segment], rules: Rules) -> None:
    started = not any(NUMBERED.match(s.heading) for s in segments)
    for s in segments:
        if not started and NUMBERED.match(s.heading):
            started = True
        if not started:
            continue  # title and preamble
        best, best_score = None, 0
        for c in rules.clauses:
            score = 3 * sum(bool(p.search(s.heading)) for p in c["_heading"]) if s.heading else 0
            score += sum(bool(p.search(s.text)) for p in c["_body"])
            if score > best_score:
                best, best_score = c["id"], score
        if best_score >= rules.min_score:
            s.clause, s.score = best, best_score


# --------------------------------------------------------------------------- #
# Value extraction
# --------------------------------------------------------------------------- #

NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "ten": 10, "twelve": 12,
             "fourteen": 14, "fifteen": 15, "thirty": 30, "sixty": 60, "ninety": 90,
             "en": 1, "et": 1, "to": 2, "tre": 3, "fire": 4, "seks": 6, "tolv": 12, "tredive": 30}
DURATION = re.compile(
    r"\b(?:(\d{1,3})|(" + "|".join(NUM_WORDS) + r"))\s*(?:\((\d{1,3})\)\s*)?(?:calendar\s+|business\s+|working\s+)?"
    r"(days?|months?|years?|dage|dages|måneder|måneders|år|uger?|weeks?)\b",
    FLAGS,
)
UNIT = {"day": "days", "dage": "days", "dages": "days", "month": "months", "måneder": "months", "måneders": "months",
        "year": "years", "år": "years", "week": "weeks", "uge": "weeks", "uger": "weeks"}
EU_NAMES = {"denmark": "Denmark", "danish": "Denmark", "dansk": "Denmark", "sweden": "Sweden", "svensk": "Sweden",
            "norway": "Norway", "norsk": "Norway", "germany": "Germany", "tysk": "Germany", "ireland": "Ireland",
            "netherlands": "Netherlands", "finland": "Finland", "france": "France", "belgium": "Belgium",
            "england and wales": "England and Wales", "engelsk": "England and Wales", "england": "England and Wales",
            "delaware": "USA (Delaware)", "california": "USA (California)", "new york": "USA (New York)",
            "united states": "USA", "switzerland": "Switzerland", "schweizisk": "Switzerland"}
LAW_RE = re.compile(r"(?:laws?\s+of\s+(?:the\s+)?(?:[Ss]tate\s+of\s+)?([A-Z][A-Za-z ]{2,30}?)(?=[,.;)]|\s+(?:and|without|excluding|applicable))"
                    r"|\b(dansk|svensk|norsk|tysk|engelsk|schweizisk)\s+ret\b)", re.UNICODE)
CAP_RE = re.compile(r"[^.]*(?:shall not exceed|will not exceed|not exceed|limited to|capped at|maximum (?:aggregate )?liability|overstige|begrænset til)[^.]*\.", FLAGS)
NOTICE_WORD = re.compile(r"notice|varsel", FLAGS)
UPTIME_RE = re.compile(r"(\d{2}[.,]\d{1,3})\s?%")


def _durations(sentence: str) -> list[str]:
    out = []
    for m in DURATION.finditer(sentence):
        n = int(m.group(3) or m.group(1) or NUM_WORDS.get(m.group(2).lower(), 0))
        unit = m.group(4).lower()
        unit = UNIT.get(unit.rstrip("s") if unit.endswith("s") and unit.rstrip("s") in UNIT else unit, unit)
        unit = "days" if unit.startswith("day") else "months" if unit.startswith("month") else "years" if unit.startswith("year") else "weeks" if unit.startswith("week") else unit
        if n:
            out.append(f"{n} {unit}")
    return out


def extract_values(text: str, clauses: dict[str, list[Segment]]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    text = " ".join(text.split())
    law_text = " ".join(s.full for s in clauses.get("governing_law", [])) or text
    m = LAW_RE.search(law_text)
    if m:
        raw = (m.group(1) or m.group(2) or "").strip().lower()
        values["governing_law"] = EU_NAMES.get(raw, raw.title())

    liab = " ".join(s.full for s in clauses.get("liability", []))
    cap = CAP_RE.search(liab)
    if cap:
        values["liability_cap"] = re.sub(r"^[\d.\s]+", "", " ".join(cap.group(0).split()))

    notice_src = " ".join(s.full for s in clauses.get("termination", []) + clauses.get("term", []))
    notices = []
    for m in DURATION.finditer(notice_src):
        after = notice_src[m.end(): m.end() + 25]
        before = notice_src[max(0, m.start() - 40): m.start()]
        if NOTICE_WORD.search(after) or re.search(r"(notice|varsel)[^.]{0,30}(at least|of|with|på|med)\s*$", before, FLAGS):
            notices += _durations(m.group(0))
    if notices:
        values["notice_periods"] = sorted(set(notices), key=notices.index)

    term_src = " ".join(s.full for s in clauses.get("term", []))
    init = re.search(r"[^.]*(?:initial term|initial period|løbetid|aftaleperiode|uopsigelig)[^.]*\.", term_src, FLAGS)
    if init and _durations(init.group(0)):
        values["initial_term"] = _durations(init.group(0))[0]

    values["auto_renewal"] = bool(re.search(r"automatically renew|auto-?renew|renew(?:ed)? automatically|fornyes automatisk|forlænges automatisk|automatisk forlæng", text, FLAGS)) \
        and not re.search(r"not (be )?automatically renew|ikke automatisk", text, FLAGS)

    up = UPTIME_RE.search(" ".join(s.full for s in clauses.get("service_levels", [])))
    if up:
        values["uptime"] = up.group(1).replace(",", ".") + "%"
    return values


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #

SENTENCE_RE = re.compile(r"(?<=[.!?;])\s+|\n{2,}")


def _sentences(text: str) -> list[str]:
    """Split into sentences. Single line breaks (common in PDFs) do not end a sentence."""
    return [" ".join(s.split()) for s in SENTENCE_RE.split(text) if s and s.strip()]


def _scope_sentences(result: Result, scope: str) -> list[str]:
    segs = result.segments if scope == "all" else result.clauses.get(scope, [])
    out = []
    for s in segs:
        out += _sentences(s.full if scope == "all" else s.text)
    return out


def _scope_text(result: Result, scope: str, text: str) -> str:
    if scope == "all":
        return text
    return "\n".join(s.full for s in result.clauses.get(scope, []))


def _short(s: str, n: int = 260) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def run_checks(result: Result, text: str, rules: Rules, dora: str | None = None) -> list[Finding]:
    """Run the core checks, plus the DORA pack when ``dora`` is "all" or "critical"."""
    if dora not in (None, *DORA_LEVELS):
        raise ValueError(f"dora must be None, 'all' or 'critical', not {dora!r}")
    checks = rules.checks + ([k for k in rules.dora if k["level"] in DORA_LEVELS[dora]] if dora else [])
    findings = []
    for k in checks:
        t, evidence, fire = k["type"], [], False
        if t == "missing":
            fire = not result.found(k["clause"])
        elif t == "match":
            for sent in _scope_sentences(result, k.get("scope", "all")):
                if any(p.search(sent) for p in k["_pattern"]) and not any(u.search(sent) for u in k.get("_unless", [])):
                    evidence.append(_short(sent))
            fire = bool(evidence)
        elif t == "present_without":
            body = _scope_text(result, k["clause"], text)
            fire = bool(body) and not any(p.search(body) for p in k["_without"])
            if fire:
                evidence = [_short(s.full) for s in result.clauses[k["clause"]]][:2]
        elif t == "requires":
            trig = [sent for sent in _scope_sentences(result, "all") if any(p.search(sent) for p in k["_if_any"])]
            trig = [t for t in trig if len(t.split()) >= 6] or trig
            fire = bool(trig) and not any(p.search(text) for p in k["_then_any"])
            if fire:
                evidence = [_short(s) for s in trig[:2]]
        elif t == "absent":
            fire = not any(
                any(p.search(sent) for p in k["_pattern"]) and not any(u.search(sent) for u in k.get("_unless", []))
                for sent in _scope_sentences(result, "all")
            )
        elif t == "value_not_in":
            v = result.values.get(k["value"])
            fire = bool(v) and v not in k["allowed"]
            if fire:
                evidence = [f"Extracted {k['value'].replace('_', ' ')}: {v}"]
        else:
            raise ValueError(f"Unknown check type {t}")
        if fire:
            findings.append(Finding(k["id"], k["severity"], k["title"], k["why"], k["ref"], evidence[:3],
                                    k["pack"], k.get("looked_for", "")))
    findings.sort(key=lambda f: (f.pack != "core", SEVERITY_ORDER[f.severity]))
    return findings


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

DA_WORDS = re.compile(r"\b(og|ikke|skal|aftale|leverandøren|kunden|af|til|eller|denne)\b", FLAGS)
EN_WORDS = re.compile(r"\b(and|not|shall|agreement|the|of|to|or|this|customer)\b", FLAGS)


def analyse(text: str, rules: Rules | None = None, dora: str | None = None) -> Result:
    """Analyse a contract.

    dora: None (default) runs the core checks only. "all" adds the DORA Art. 30(2) checks for any
    ICT service used by a financial entity, "critical" adds Art. 30(3) for critical or important functions.
    """
    rules = rules or Rules.builtin()
    segs = segment(text)
    classify(segs, rules)
    clauses: dict[str, list[Segment]] = {}
    for s in segs:
        if s.clause:
            clauses.setdefault(s.clause, []).append(s)
    lang = "da" if len(DA_WORDS.findall(text)) > len(EN_WORDS.findall(text)) else "en"
    result = Result(segs, clauses, extract_values(text, clauses), [], lang, dora)
    result.findings = run_checks(result, text, rules, dora)
    return result
