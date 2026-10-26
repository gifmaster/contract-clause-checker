# Method, accuracy and limitations

## How it works

1. **Read.** PDF, Word or text is turned into plain text.
2. **Split into clauses.** A new clause starts at a heading: numbered (`4. Fees`, `4.2`), `Section 5` style, or a line in capitals. Numbered lines that read like full sentences are treated as sub-clauses, not headings. Everything before the first numbered heading is treated as title and preamble.
3. **Classify.** Each clause is scored against the clause types in [`rules/clauses.yaml`](../src/clausecheck/rules/clauses.yaml): a heading match counts 3 points, each matching body pattern 1 point. The highest score wins if it reaches 3.
4. **Extract key terms.** Governing law, initial term, notice periods, automatic renewal, liability cap and availability, from the clauses where they belong.
5. **Check.** The rules in [`rules/checks.yaml`](../src/clausecheck/rules/checks.yaml) run on the text. Checks work on whole sentences, so negations (`shall not use Customer Data to train`) and consent conditions (`only with prior written consent`) are recognised. Every finding carries the sentence that triggered it.

All patterns cover English and Danish.

## Accuracy

Measured on hand-labelled fictional contracts in [`tests/ground_truth.yaml`](../tests/ground_truth.yaml): which clause should be found where, which checks should fire, and which values should be extracted. The test suite fails if overall precision or recall drops below 0.90.

| Set | When | Clause detection | Checks (precision / recall) |
|---|---|---|---|
| 3 development samples (2 EN, 1 DA) | Final rules | 26 of 26 | 1.00 / 1.00 |
| **Held-out contract**, different style, rules not changed | First run | **0 of 6** | **0.50 / 1.00** |
| Same held-out contract | After two general fixes | 6 of 6 | 1.00 / 1.00 |

**What the held-out test showed.** The checks themselves held up on a contract they had never seen: every real issue was flagged. But headings in the style `SECTION 1. THE SERVICE` were not recognised, so the whole contract was read as one block and four clauses were reported missing when they were not. Two general fixes followed: support for `SECTION`/`CLAUSE`-style headings in capitals, and plain-English heading words (*Charges*, *Ending the contract*, *Law*, *Your content*). After that the held-out contract became part of the regression set, so it no longer counts as unseen.

**What this means.** The numbers above come from a small set of fictional contracts, partly used to build the rules. Real contracts are messier. Expect missed clauses on unusual layouts and occasional false flags. That is why every finding shows its evidence, and why the tool is built for a human reviewer, not instead of one. The next held-out contracts should be real ones, anonymised.

## Same result from any format

The risky sample is also stored as Word and PDF. A test checks that all three formats give identical findings and key terms. PDF extraction breaks lines mid-sentence, so single line breaks are not treated as sentence ends.

## Known limitations

- Headings are needed to split clauses. Contracts written as one long block of text will be classified poorly.
- Tables, footnotes and appendices referenced by name (e.g. "the DPA in Appendix 3") are not read; the reference itself counts.
- The checks look at the customer's side of an AI or SaaS vendor contract. They are not a general contract review.
- Pattern-based negation handles common phrasing, not every legal construction.
- No legal advice. A qualified person should read the full contract.

## Related obligations

| Check | Why it matters | Source |
|---|---|---|
| Vendor may train on your data | Confidentiality, purpose limitation, controller role | GDPR Art. 5(1)(b), 28 |
| No data processing agreement | Written terms are required when a vendor processes personal data for you | GDPR Art. 28 |
| Transfers without safeguards | Transfers outside the EU/EEA need a legal basis | GDPR Chapter V |
| No AI Act terms | Deployers must follow the provider's instructions and ensure human oversight | EU AI Act Art. 13, 26 |
| Vendor may end at any time | Exit and continuity risk; for financial entities also an ICT third-party question | DORA Art. 28 |
