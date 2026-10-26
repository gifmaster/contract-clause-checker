"""Unit tests for the DORA pack (Regulation (EU) 2022/2554, Art. 30)."""

import pytest

from clausecheck import Rules, analyse, to_markdown
from clausecheck.engine import segment

RULES = Rules.builtin()


def dora_ids(text, level="critical"):
    return {f.id for f in analyse(text, RULES, dora=level).findings if f.pack == "dora"}


def test_pack_is_off_by_default():
    assert not any(f.pack == "dora" for f in analyse("1. Fees\nPay on time.", RULES).findings)


def test_levels_follow_article_30():
    lvl2 = {k["id"] for k in RULES.dora if k["level"] == "all"}
    lvl3 = {k["id"] for k in RULES.dora if k["level"] == "critical"}
    assert len(lvl2) == 12 and len(lvl3) == 6
    empty = "1. Fees\nThe fees are in the order."
    assert dora_ids(empty, "all") == lvl2
    assert dora_ids(empty, "critical") == lvl2 | lvl3


def test_every_dora_check_cites_dora():
    for k in RULES.dora:
        assert k["ref"].startswith("DORA Art. "), k["id"]
        want = "30(3)" if k["level"] == "critical" else "30(2)"
        assert want in k["ref"] or k["id"] == "dora_regulatory_termination", k["id"]


def test_unknown_level_is_rejected():
    with pytest.raises(ValueError, match="dora must be"):
        analyse("text", RULES, dora="yes")


@pytest.mark.parametrize("check, sentence", [
    ("dora_audit_rights", "The Customer and its competent authority have the right to audit the Supplier."),
    ("dora_audit_rights", "Kunden og Finanstilsynet har ret til at foretage revision hos Leverandøren."),
    ("dora_exit_strategy", "A transition period of twelve months applies when the Agreement ends."),
    ("dora_data_return", "On termination the Supplier will return all Customer Data in CSV format."),
    ("dora_data_return", "Leverandøren stiller alle Kundens data til rådighed for Kunden ved ophør."),
    ("dora_incident_assistance", "The Supplier will assist the Customer with any incident at no additional cost."),
    ("dora_location_change_notice", "Leverandøren giver tre måneders varsel, før placeringen af data ændres."),
    ("dora_authority_cooperation", "The Supplier will cooperate fully with Finanstilsynet."),
])
def test_wording_counts_as_covered(check, sentence):
    assert check not in dora_ids("1. Terms\n" + sentence)


@pytest.mark.parametrize("check, sentence", [
    ("dora_audit_rights", "The Customer may not audit the Supplier."),
    ("dora_data_return", "The Supplier will not return Customer Data after termination."),
    ("dora_incident_assistance", "The Supplier has no obligation to assist with incidents."),
])
def test_negated_wording_does_not_count(check, sentence):
    assert check in dora_ids("1. Terms\n" + sentence)


def test_short_numbered_subclause_is_text_not_heading():
    """Found by the held-out Danish contract: short sub-clauses were read as headings and never checked."""
    segs = segment("6. Kontrol\n6.1 Kunden har ret til revision.\n6.2 Leverandøren samarbejder med Finanstilsynet.\n")
    assert [s.heading for s in segs] == ["6. Kontrol"]


def test_report_has_dora_checklist():
    text = "1. Exit\nThe Supplier maintains an exit plan and a transition period of six months."
    md = to_markdown(analyse(text, RULES, dora="critical"), RULES, "T")
    assert "## DORA key contractual provisions" in md
    assert "Covered in the main text: **1 of 18**" in md
    assert "| Covered | An exit strategy" in md
    assert "Check appendices" in md
    assert "DORA" not in to_markdown(analyse(text, RULES), RULES, "T")
