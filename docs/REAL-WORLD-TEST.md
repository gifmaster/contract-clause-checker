# Real-world test: public contracts the author did not write

An expert review of the tool made one point above all: the accuracy figures were measured on contracts the author wrote, with an answer key
the author wrote and rules the author wrote. That proves the code works. It does not show that the tool copes with real contracts.
So this page tests it on real, publicly published ones.

## Method

1. Pick real contracts that are free to reuse (Common Paper, Bonterms and GitHub, all CC BY 4.0 or CC0). Sources and licences are in [`samples/real/NOTICE.md`](../samples/real/NOTICE.md).
2. Read each one and write the answer key by hand ([`tests/real_world_truth.yaml`](../tests/real_world_truth.yaml)) **before changing any rule**.
3. Run the unmodified tool once. Commit the numbers. This is the first run.
4. Fix the rules in general terms, and run again.
5. Add documents the rules have never seen, label them first, run them once, and only then fix what they show.

Everything here is reproducible: `python scripts/real_world_report.py`. The same answer key runs in CI.

## First run, unmodified tool

Six real contracts and one synthetic hard case written by the author. Core checks: **precision 0.21, recall 0.43**.

| Document | Missed | Wrongly flagged | Clauses found | Other |
|---|---|---|---|---|
| Common Paper Cloud Service Agreement | - | no liability cap, transfer without safeguards, no governing law | 6/7 | Did not see that the DPA is a separate document |
| Bonterms Cloud Terms | automatic renewal | no liability clause, no governing law clause, no confidentiality clause | **1/8** | Did not see the DPA reference |
| GitHub Corporate Terms | unilateral changes, vendor may end at any time | no liability clause, no DPA, transfer, no governing law, no confidentiality | **1/5** | Did not see the DPA reference |
| Common Paper AI Addendum | AI training or improvement | - | n/a | |
| Common Paper DPA | - | five contract-only checks | n/a | **Not recognised as a DPA**; one wrong GDPR flag |
| Bonterms DPA | - | four contract-only checks | n/a | **Not recognised as a DPA**; two wrong GDPR flags |
| Synthetic US-style MSA | automatic renewal, very short cap, transfer, vendor may end | no termination clause, no liability cap | 5/5 | Did not see the DPA reference |

Clause detection: 13 of 25. GDPR pack on the two real DPAs: precision 0.50, recall 1.00.

## What was wrong

Seven general problems, none specific to one document:

1. **Headings.** US-style contracts run the heading into the first sentence (`**5. Data**. Text follows`), or use Markdown or letter headings (`## N. Limitations of Liability`). The tool saw one clause in a document that has twenty.
2. **Negation.** `will not sell Customer Data, but may use it to train its models` was ignored, because the word "not" cancelled the whole sentence.
3. **Wording of a cap.** `will not be more than`, `total cumulative liability` and `entire liability` were not recognised as caps. A cap of one month of fees was not flagged at all.
4. **Data transfers.** A country name alone triggered "data may leave the EU": export control clauses, a list of sanctioned parties "maintained by the U.S.", the definition of "the Americas".
5. **DPA by other names.** `Data Protection Addendum`, `incorporated by reference`, `if the parties have a DPA`, `must enter into a data processing agreement`.
6. **Renewal and changes.** `renews automatically`, `will renew for successive periods unless`, `reserves the right, at its sole discretion, to amend`.
7. **Documents that are not contracts.** A real DPA that mentions its own annexes was read as "points to a DPA elsewhere", so it was not recognised as a DPA and was held to contract checks it should not face.

## After the general fixes

On the documents the rules were tuned on: core checks **precision 1.00, recall 0.93**, clause detection **25 of 25**, GDPR pack on both real DPAs **1.00 / 1.00**.
These numbers are not independent: the fixes were made on these documents. The first-run numbers above are the evidence.

## Held-out documents

Two further real contracts, labelled before the first run: Common Paper Professional Services Agreement (a clean contract where nothing should fire) and the GitHub Terms of Service (AI training licence, unilateral changes, exclusion-only liability, US law).

| Run | Core checks (precision / recall) | Clauses found |
|---|---|---|
| **First run** | **0.83 / 0.83** | 11 of 11 |
| After three more fixes (no longer independent) | 1.00 / 1.00 | 11 of 11 |

The first run had three errors: US law was not recognised when written "federal laws of the United States of America"; "access certain GitHub services pursuant to U.S. law" was read as a data transfer; and "If the parties have a DPA" was not read as a pointer to a DPA. All three were fixed in general terms.

## What is still wrong

- **Known miss.** The Common Paper AI Addendum lets the vendor use inputs and outputs to improve its AI system, "provided that such usage does not constitute Training". A rule that reads a negation anywhere in the clause cannot tell that from "provided it is not used to train", and the tool prefers silence to flagging every restriction. A reviewer reading only the tool's output would miss it.
- **Small sample.** Eight real documents and one synthetic. The 1.00 figures say little about how it will do on the next ten.
- **Templates are not negotiated contracts.** These are clean, well-structured, English-language templates. Real contracts are messier: scanned PDFs, tracked changes, schedules, Danish and mixed-language text.
- **One reader's labels.** The answer key is one person's reading of each contract and can be argued with. Where a label was a judgement call it says so in the key.
- **Wording, not adequacy.** The tool checks that wording exists. It does not judge whether a 72-hour breach notice or a cap of twelve months of fees suits you.
- **Cover pages.** Terms that sit in a cover page, order form or annex are invisible, so they show as missing.

## Changes to the tool

Cleaning of web markup; run-in, Markdown and letter headings; sub-clauses belong to their parent clause; "Term and Termination" counts as both; negation cancels only its own part of a sentence; broader wording for caps, renewal, changes and DPA references; a new check for very small liability caps; tighter data-transfer triggers; governing law is flagged only when it is read as a recognised non-EU jurisdiction; documents covering most of the twelve Art. 28 terms are treated as DPAs; a visible "what this tool does not catch" box in the app.
