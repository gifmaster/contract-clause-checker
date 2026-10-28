"""Regression tests for the problems an expert review found: each case is a phrasing real contracts use."""

import pytest

from clausecheck import analyse
from clausecheck.engine import normalize, segment

CONTRACT = """MASTER AGREEMENT

1. Use of Data
{data}

2. Term and Termination
{term}

3. Liability
{liab}

4. Governing Law
This Agreement is governed by the laws of Denmark.
"""


def ids(data="", term="", liab="", extra="", **kw):
    text = CONTRACT.format(data=data, term=term, liab=liab) + extra
    return {f.id for f in analyse(text, **kw).findings if f.pack == "core"}


# --- negation belongs to its own part of the sentence ------------------------------------------------

@pytest.mark.parametrize("sentence", [
    "Provider will not sell Customer Data, but Provider may use Customer Data to improve and train its machine learning models.",
    "Provider does not claim ownership; however, Provider may use Customer Data to train its models.",
])
def test_training_is_found_despite_a_negation_elsewhere_in_the_sentence(sentence):
    assert "ai_training_on_data" in ids(data=sentence)


@pytest.mark.parametrize("sentence", [
    "Provider shall not use Customer Data to train its models.",
    "Provider has no right to use Customer Data to train any model.",
    "Provider may use Customer Data only to provide the Services and not to train any model.",
    "Provider may use Customer Data to train its models only with Customer's prior written consent.",
    "Leverandøren må ikke anvende kundens data til at træne modeller.",
])
def test_training_is_not_flagged_when_it_is_forbidden_or_limited(sentence):
    assert "ai_training_on_data" not in ids(data=sentence)


# --- automatic renewal ----------------------------------------------------------------------------------

@pytest.mark.parametrize("sentence", [
    "This Agreement renews automatically for successive twelve-month periods unless either party gives notice.",
    "Each Subscription Term will renew for successive periods unless a party gives notice of non-renewal.",
    "The agreement continues with automatic renewal for one year at a time.",
])
def test_automatic_renewal_variants(sentence):
    assert "auto_renewal" in ids(term=sentence)


def test_no_automatic_renewal_is_not_flagged():
    assert "auto_renewal" not in ids(term="This Agreement will not automatically renew.")


# --- liability caps ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("sentence", [
    "Each party's total cumulative liability will not be more than the General Cap Amount.",
    "In no event shall Provider's aggregate liability exceed the fees paid in the preceding twelve months.",
])
def test_a_cap_in_other_words_is_still_a_cap(sentence):
    assert "no_liability_cap" not in ids(liab=sentence)


def test_exclusion_only_liability_clause_has_no_cap():
    assert "no_liability_cap" in ids(liab="We will not be liable for any indirect or consequential damages.")


def test_very_short_cap_is_flagged_and_a_normal_one_is_not():
    short = "In no event shall Provider's aggregate liability exceed the fees paid in the one month preceding the claim."
    normal = "In no event shall Provider's aggregate liability exceed the fees paid in the twelve months preceding the claim."
    assert "short_liability_cap" in ids(liab=short)
    assert "short_liability_cap" not in ids(liab=normal)


# --- data transfers ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("sentence", [
    "Customer may not remove or export the Service from the United States in violation of export laws.",
    "Provider will not deal with any party on a list maintained by the U.S. Department of the Treasury.",
    "GitHub may allow persons in sanctioned countries to access certain services pursuant to U.S. law.",
])
def test_a_country_name_alone_is_not_a_data_transfer(sentence):
    assert "transfer_without_safeguards" not in ids(extra="\n5. Personal data\nThe Provider processes personal data. " + sentence + "\n", )


@pytest.mark.parametrize("sentence", [
    "Customer Data may be transferred to and processed in the United States.",
    "Provider and its Subprocessors may process Customer Data in any country in which they maintain facilities.",
])
def test_real_transfers_are_still_found(sentence):
    assert "transfer_without_safeguards" in ids(data=sentence)


def test_transfer_with_standard_contractual_clauses_is_not_flagged():
    assert "transfer_without_safeguards" not in ids(
        data="Customer Data may be processed in the United States under the Standard Contractual Clauses.")


# --- data processing agreements by other names ----------------------------------------------------------------

@pytest.mark.parametrize("sentence", [
    "The Data Processing Addendum available at example.com/legal/dpa is incorporated by reference.",
    "The GitHub Data Protection Agreement provides notice of Provider's processing of personal data.",
    "The parties will adhere to the Data Protection Addendum identified on the Cover Page.",
    "Before submitting personal data the Customer must enter into a data processing agreement with Provider.",
    "If the parties have a DPA, each party will comply with its obligations in the DPA.",
])
def test_reference_to_a_dpa_is_recognised(sentence):
    text = CONTRACT.format(data="Provider processes personal data. " + sentence, term="", liab="")
    r = analyse(text, gdpr=True)
    assert r.dpa_elsewhere
    assert "no_dpa" not in {f.id for f in r.findings}


# --- governing law -------------------------------------------------------------------------------------------

def test_governing_law_is_flagged_only_when_it_is_read():
    law = lambda s: "non_eu_law" in {f.id for f in analyse(f"1. Governing Law\n{s}\n").findings}
    assert law("This Agreement is governed by the federal laws of the United States of America and the laws of the State of California.")
    assert law("This Agreement is governed by the laws of California.")
    assert not law("This Agreement is governed by the laws of the Governing Member State.")  # a variable, not a country
    assert not law("This Agreement is governed by the laws of Denmark.")


# --- how documents are read ---------------------------------------------------------------------------------

def test_web_markup_is_removed():
    out = normalize('<span class="x">Fees</span> are in **USD**, see [the policy](https://e.com/p) and _Service Disclaimer._ here.')
    assert "<" not in out and "**" not in out and "](" not in out and "_Service" not in out
    assert "the policy" in out and "USD" in out


def test_run_in_headings_start_a_clause():
    text = ("**1. The Agreement**. These terms apply to the service you buy.\n\n"
            "**16. Limitations of Liability**. Each party's entire liability will not exceed the General Cap.\n\n"
            "**22.2.** Governing Law and Courts. The Governing Law governs this Agreement.\n")
    heads = [s.heading for s in segment(normalize(text))]
    assert "16. Limitations of Liability" in heads
    assert any(h.startswith("22.2") and "Governing Law" in h for h in heads)


def test_an_ordinary_numbered_sentence_is_not_a_heading():
    text = "1. The Customer pays the fee. Payment is due in thirty days.\n"
    assert [s.heading for s in segment(normalize(text))] == [""]


def test_markdown_headings_are_headings():
    text = "# Agreement\n\n## N. Limitations of Liability\n\nOur total liability will not exceed the fees paid.\n"
    assert any(s.heading == "N. Limitations of Liability" for s in segment(normalize(text)))


def test_term_and_termination_counts_as_both():
    r = analyse("1. Services\nWe provide the service.\n\n2. Term and Termination\nThis Agreement lasts one year. Either party may terminate on 30 days notice.\n")
    assert "missing_termination" not in {f.id for f in r.findings}
    assert r.found("term") and r.found("termination")


def test_sub_clause_belongs_to_its_parent_clause():
    text = ("16. Limitations of Liability.\n"
            "16.1. General Cap. Each party's entire liability will not exceed the General Cap.\n"
            "16.2. Exceptions. The cap does not apply to fraud.\n")
    r = analyse(text)
    assert "no_liability_cap" not in {f.id for f in r.findings}
