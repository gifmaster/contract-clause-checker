"""Unit tests for the NIS2 supply chain pack (Art. 21(2)(d), Impl. Reg. (EU) 2024/2690 Annex 5.1.4)."""

import pytest

from clausecheck import Rules, analyse, to_markdown

RULES = Rules.builtin()
ALL = {k["id"] for k in RULES.nis2}


def nis2_ids(text):
    return {f.id for f in analyse(text, RULES, nis2=True).findings if f.pack == "nis2"}


def test_pack_is_off_by_default():
    assert not any(f.pack == "nis2" for f in analyse("1. Fees\nPay on time.", RULES).findings)
    assert analyse("1. Fees\nPay on time.", RULES).nis2_checklist(RULES) == []


def test_eight_terms_one_per_point_of_5_1_4():
    assert len(RULES.nis2) == 8
    points = sorted(k["ref"].split("5.1.4")[1] for k in RULES.nis2)
    assert points == [f"({c})" for c in "abcdefgh"]
    for k in RULES.nis2:
        assert k["ref"].startswith("NIS2 Art. 21(2)(d)"), k["id"]
    assert nis2_ids("1. Fees\nThe fees are in the order.") == ALL


@pytest.mark.parametrize("check, sentence", [
    ("nis2_security_requirements", "The Supplier is certified to ISO/IEC 27001."),
    ("nis2_security_requirements", "Leverandøren overholder Kundens sikkerhedskrav i bilag 2."),
    ("nis2_staff_training", "All staff with access complete security awareness training every year."),
    ("nis2_staff_training", "Medarbejdere med adgang gennemgår et kursus i informationssikkerhed."),
    ("nis2_background_checks", "The Supplier carries out background checks on all administrators."),
    ("nis2_background_checks", "Leverandøren indhenter straffeattest for alle medarbejdere."),
    ("nis2_incident_notification", "The Supplier will notify the Customer of any incident within 4 hours."),
    ("nis2_incident_notification", "Leverandøren underretter Kunden om enhver sikkerhedshændelse."),
    ("nis2_audit", "The Supplier provides an annual ISAE 3402 type 2 report."),
    ("nis2_vulnerability_handling", "Critical security patches are applied within 72 hours."),
    ("nis2_vulnerability_handling", "Leverandøren retter kritiske sårbarheder inden for 3 dage."),
    ("nis2_subcontracting", "Subcontractors require the Customer's prior written approval."),
    ("nis2_exit", "At the end of the Agreement the Supplier returns and then deletes all Customer data."),
])
def test_wording_counts_as_covered(check, sentence):
    assert check not in nis2_ids("1. Terms\n" + sentence)


@pytest.mark.parametrize("check, sentence", [
    ("nis2_vulnerability_handling", "Leverandøren kan efter eget valg opdatere og videreudvikle platformen."),
    ("nis2_vulnerability_handling", "The Supplier may update the platform at its discretion."),
    ("nis2_incident_notification", "The Supplier has no obligation to report incidents."),
    ("nis2_audit", "The Customer may not audit the Supplier."),
])
def test_updates_and_negations_do_not_count(check, sentence):
    """From the held-out contract: a right to update the product is not a duty to handle vulnerabilities."""
    assert check in nis2_ids("1. Terms\n" + sentence)


def test_report_has_nis2_checklist_and_states_the_scope():
    text = "1. Security\nThe Supplier is certified to ISO/IEC 27001."
    md = to_markdown(analyse(text, RULES, nis2=True), RULES, "T")
    assert "## NIS2 supply chain terms" in md
    assert "Covered in the main text: **1 of 8**" in md
    assert "binding for digital infrastructure" in md
    assert "NIS2 supply chain terms" not in to_markdown(analyse(text, RULES), RULES, "T")


def test_held_out_incident_clause_without_its_lucky_heading():
    """The held-out contract only passed because of its heading. The clause itself must count on its own."""
    clause = ("§ 3 Underretning\nLeverandøren underretter Kunden uden unødig forsinkelse og senest 12 timer efter, at "
              "Leverandøren er blevet bekendt med en sikkerhedshændelse, der kan påvirke Kundens net- og informationssystemer.")
    assert "nis2_incident_notification" not in nis2_ids(clause)
