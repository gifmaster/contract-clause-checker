"""Unit tests for the GDPR pack (Regulation (EU) 2016/679, Art. 28)."""

import pytest

from clausecheck import Rules, analyse, processes_personal_data, to_markdown

RULES = Rules.builtin()
ALL = {k["id"] for k in RULES.gdpr}


def gdpr_ids(text):
    return {f.id for f in analyse(text, RULES, gdpr=True).findings if f.pack == "gdpr"}


def test_pack_is_off_by_default():
    assert not any(f.pack == "gdpr" for f in analyse("1. Fees\nPay on time.", RULES).findings)
    assert analyse("1. Fees\nPay on time.", RULES).gdpr_checklist(RULES) == []


def test_twelve_terms_all_from_article_28():
    assert len(RULES.gdpr) == 12
    for k in RULES.gdpr:
        assert k["ref"].startswith("GDPR Art. 28"), k["id"]
        assert k["looked_for"] and k["why"], k["id"]
    assert gdpr_ids("1. Fees\nThe fees are in the order.") == ALL


@pytest.mark.parametrize("check, sentence", [
    ("gdpr_instructions", "The Processor processes personal data only on documented instructions from the Controller."),
    ("gdpr_instructions", "Databehandleren må kun behandle personoplysninger efter dokumenteret instruks."),
    ("gdpr_staff_confidentiality", "Persons authorised to process the data are bound by confidentiality."),
    ("gdpr_staff_confidentiality", "Medarbejdere med adgang til oplysningerne er underlagt tavshedspligt."),
    ("gdpr_subprocessor_approval", "New sub-processors require the Controller's prior written approval."),
    ("gdpr_subprocessor_approval", "Brug af nye underleverandører kræver Kundens forudgående skriftlige godkendelse."),
    ("gdpr_subprocessor_flowdown", "Each sub-processor is bound by the same data protection obligations."),
    ("gdpr_breach_notification", "The Processor notifies the Controller of any personal data breach within 24 hours."),
    ("gdpr_breach_notification", "Databehandleren underretter straks om et brud på persondatasikkerheden."),
    ("gdpr_deletion_return", "On termination the Processor deletes all personal data."),
    ("gdpr_deletion_return", "Ved ophør sletter Databehandleren alle personoplysninger."),
    ("gdpr_controller_assistance", "The Processor assists with data protection impact assessments."),
    ("gdpr_audit", "The Controller may audit the Processor once a year."),
    ("gdpr_unlawful_instruction", "The Processor informs the Controller if an instruction infringes the GDPR."),
])
def test_wording_counts_as_covered(check, sentence):
    assert check not in gdpr_ids("1. Terms\n" + sentence)


@pytest.mark.parametrize("check, sentence", [
    ("gdpr_deletion_return", "The Processor will not delete personal data after termination."),
    ("gdpr_audit", "The Controller may not audit the Processor."),
    ("gdpr_breach_notification", "The Processor has no obligation to report a personal data breach."),
    ("gdpr_staff_confidentiality", "Each party shall keep the other party's confidential information confidential."),
])
def test_negated_or_unrelated_wording_does_not_count(check, sentence):
    assert check in gdpr_ids("1. Terms\n" + sentence)


def test_breach_mentioned_without_a_duty_to_notify_is_flagged():
    """From the held-out DPA: 'breaches are handled as set out in Annex II' says nothing about telling you."""
    assert "gdpr_breach_notification" in gdpr_ids("3. Security\nPersonal data breaches are handled as set out in Annex II.")


def test_contract_pointing_to_a_separate_dpa():
    text = "6. Data Protection\nThe Supplier processes personal data under the data processing agreement in Appendix 3."
    result = analyse(text, RULES, gdpr=True)
    assert result.dpa_elsewhere and not result.is_dpa
    assert "separate document" in to_markdown(result, RULES, "T")


def test_dpa_that_mentions_the_main_agreement_is_still_a_dpa():
    """A full DPA covers most terms itself, so a mention of 'the Agreement' does not send the user elsewhere."""
    terms = ("Types of personal data and categories of data subjects are listed in Annex 1. "
             "The Processor acts only on documented instructions. Persons authorised to process the data are bound by confidentiality. "
             "The Processor implements technical and organisational measures. Sub-processors require prior written approval. "
             "The Processor notifies the Controller of any personal data breach. The Controller may audit the Processor.")
    result = analyse("1. Terms\n" + terms, RULES, gdpr=True)
    assert result.is_dpa and not result.dpa_elsewhere


def test_dpa_hides_contract_only_checks_but_keeps_data_checks():
    dpa = ("1. Terms\nTypes of personal data and categories of data subjects are listed in Annex 1. "
           "The Processor acts only on documented instructions. Persons authorised to process the data are bound by confidentiality. "
           "The Processor implements technical and organisational measures. Sub-processors require prior written approval. "
           "The Processor notifies the Controller of any personal data breach. The Controller may audit the Processor. "
           "The Processor may use the personal data to train its models.")
    ids = {f.id for f in analyse(dpa, RULES, gdpr=True).findings if f.pack == "core"}
    assert ids == {"ai_training_on_data"}


def test_personal_data_switches_the_pack_on_in_the_app():
    assert processes_personal_data("The Supplier processes personal data for the Customer.", RULES)
    assert processes_personal_data("Leverandøren behandler personoplysninger.", RULES)
    assert not processes_personal_data("The Supplier hosts marketing images.", RULES)


def test_report_has_gdpr_checklist():
    text = "1. Deletion\nOn termination the Processor deletes all personal data."
    md = to_markdown(analyse(text, RULES, gdpr=True), RULES, "T")
    assert "## GDPR data processing terms" in md
    assert "Covered in this document: **1 of 12**" in md
    assert "GDPR data processing terms" not in to_markdown(analyse(text, RULES), RULES, "T")
