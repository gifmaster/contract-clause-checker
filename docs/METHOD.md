# Method, accuracy and limitations

## How it works

1. **Read.** PDF, Word or text is turned into plain text.
2. **Split into clauses.** A new clause starts at a heading: numbered (`4. Fees`), `Section 5` style, or a line in capitals. Numbered sub-clauses (`4.2 ...`) that end like a sentence are treated as text, not headings, even when they are short. Everything before the first numbered heading is treated as title and preamble.
3. **Classify.** Each clause is scored against the clause types in [`rules/clauses.yaml`](../src/clausecheck/rules/clauses.yaml): a heading match counts 3 points, each matching body pattern 1 point. The highest score wins if it reaches 3.
4. **Extract key terms.** Governing law, initial term, notice periods, automatic renewal, liability cap and availability, from the clauses where they belong.
5. **Check.** The rules in [`rules/checks.yaml`](../src/clausecheck/rules/checks.yaml) run on the text. Checks work on whole sentences, so negations (`shall not use Customer Data to train`) and consent conditions (`only with prior written consent`) are recognised. Every finding carries the sentence that triggered it.

All patterns cover English and Danish.

## GDPR pack

When a vendor processes personal data on your behalf, GDPR Art. 28 requires a contract with specific terms. The pack in [`rules/gdpr.yaml`](../src/clausecheck/rules/gdpr.yaml) checks for each of them.

| Term | Article | Severity if missing |
|---|---|---|
| Description of the processing (subject matter, duration, nature, purpose, data types, data subjects) | 28(3) | Medium |
| Processing only on documented instructions | 28(3)(a) | High |
| Confidentiality for the people who handle the data | 28(3)(b) | Medium |
| Security measures | 28(3)(c), 32 | Medium |
| Prior approval of sub-processors, notice of changes | 28(2), 28(3)(d) | High |
| Same obligations passed on to sub-processors | 28(4) | Medium |
| Help with data subject requests | 28(3)(e) | Medium |
| Breach notification to you | 28(3)(f), 33(2) | High |
| Help with impact assessments and prior consultation | 28(3)(f) | Medium |
| Deletion or return at the end | 28(3)(g) | High |
| Information and audits | 28(3)(h) | Medium |
| Warning about unlawful instructions | 28(3), last subparagraph | Low |

**Where the DPA lives.** Most vendor contracts keep the DPA in an appendix. The tool recognises a contract that points to a separate DPA and covers fewer than six of the twelve terms itself, and asks for the DPA instead of reporting the gaps as real. The reverse also holds: a document that covers six or more terms is treated as a DPA in its own right, so contract-only checks such as liability, termination and governing law are not shown for it. Two contract checks stay on because they matter in a DPA too: training on your data and transfers outside the EU (marked `in_dpa` in `checks.yaml`).

**Accuracy.** The answer key for all nine documents was written by hand before the rules. On the 8 development documents (the six contracts plus an English and a Danish DPA, each with planted gaps) the pack matched the key exactly: 65 of 65 decisions. The held-out DPA, written in the style of the Commission's standard clauses before the rules and run once, also matched on the first run, including a trap where breaches are mentioned without any duty to report them. The same author wrote the rules and the held-out DPA, so treat this as a check of known drafting styles. The next real test is anonymised DPAs from vendors.

Building the pack also exposed a gap in the core training check: *"may use the personal data to train its models"* was not caught, because the rule only knew wording like *customer data* and *content*. Personal data (and *personoplysninger*) was added; no sample changed result.

## NIS2 pack

NIS2 (Directive (EU) 2022/2555) Art. 21(2)(d) requires essential and important entities to manage supply chain security, including the security aspects of their relationships with direct suppliers. In Denmark it is implemented by the NIS2 Act. The directive does not list contract terms; point 5.1.4 of the Annex to Commission Implementing Regulation (EU) 2024/2690 does, and the pack in [`rules/nis2.yaml`](../src/clausecheck/rules/nis2.yaml) checks one term per point.

| Term | Point of 5.1.4 | Severity if missing |
|---|---|---|
| Cybersecurity requirements for the supplier | (a) | High |
| Security skills and training of supplier staff | (b) | Low |
| Background checks on supplier staff | (c) | Low |
| Incident notification without undue delay | (d) | High |
| Right to audit, or audit reports | (e) | Medium |
| Handling of vulnerabilities | (f) | High |
| Subcontracting conditions | (g) | Medium |
| Return and disposal of information at the end | (h) | Medium |

**How binding it is.** Implementing Regulation (EU) 2024/2690 is binding for digital infrastructure and ICT service providers: DNS, TLD registries, cloud, data centres, CDNs, managed (security) service providers, online marketplaces, search engines, social networks and trust service providers. For other NIS2 entities, such as a water or heating utility, it is the most concrete reading of Art. 21(2)(d) available, not a binding list. The regulation itself asks for these terms "where appropriate", based on the entity's own supply chain risk assessment. The report and the app say this next to the checklist.

**Accuracy.** As for the GDPR pack, the answer key was written by hand before the rules. On 7 development contracts (the six existing ones plus a water utility contract with two planted gaps) the pack matched exactly: 38 of 38. The held-out Danish contract in `§` style, written before the rules and run once, also scored 1.00 on the first run, including a trap where the vendor may *update the platform at its own choice*, which is not vulnerability handling.

**The lucky result.** A unit test written afterwards showed that one of those held-out results was luck. The rule did not understand the Danish compound *sikkerhedshændelse* (security incident) at all. It only matched because the section heading *Hændelser* happened to sit next to *uden unødig forsinkelse*. With a different heading the clause would have been missed. Fix, in general terms: Danish incident and vulnerability words are now matched by their last part (*-hændelse*, *-brud*, *-sårbarhed*), and a test checks the held-out clause without the heading.

## DORA pack

For financial entities under DORA (Regulation (EU) 2022/2554), an optional pack in [`rules/dora.yaml`](../src/clausecheck/rules/dora.yaml) checks the key contractual provisions of Article 30. Every AI tool a bank, insurer or pension fund buys is an ICT service, so its contract must contain them.

| Level | Articles | Checks |
|---|---|---|
| Any ICT service | Art. 30(2)(a) to (i), with termination grounds from Art. 28(7) | 12 |
| ICT service supporting a critical or important function | Art. 30(2) plus Art. 30(3)(a) to (f) | 18 |

The DORA checks are of type `absent`: they look for wording that covers the provision anywhere in the contract, and a provision counts as covered only if the sentence is not negated (*"may not audit"*). The report shows a checklist of all provisions, covered or not found. *Not found* means not found in the main text. DORA contracts often put service levels, audit procedures and exit plans in appendices, which the tool does not read, so a gap is a question to ask, not a conclusion.

The pack checks that a provision is there, not that it is good enough. A six-month transition period and a six-week one both count as an exit term.

## Accuracy

Measured on hand-labelled fictional contracts in [`tests/ground_truth.yaml`](../tests/ground_truth.yaml): which clause should be found where, which checks should fire, and which values should be extracted. The test suite fails if overall precision or recall drops below 0.90.

| Set | When | Clause detection | Checks (precision / recall) |
|---|---|---|---|
| 3 development samples (2 EN, 1 DA) | Final rules | 26 of 26 | 1.00 / 1.00 |
| **Held-out contract**, different style, rules not changed | First run | **0 of 6** | **0.50 / 1.00** |
| Same held-out contract | After two general fixes | 6 of 6 | 1.00 / 1.00 |

DORA pack, at the level for critical or important functions (18 checks per contract):

| Set | When | Clause detection | DORA checks (precision / recall) |
|---|---|---|---|
| 5 development samples, incl. one written to meet DORA | Final rules | 41 of 41 | 1.00 / 1.00 |
| **Held-out Danish DORA contract**, rules not changed | First run | **7 of 8** | **0.57 / 1.00** |
| Same held-out contract | After three general fixes | 8 of 8 | 1.00 / 1.00 |

**What the held-out test showed.** The checks themselves held up on a contract they had never seen: every real issue was flagged. But headings in the style `SECTION 1. THE SERVICE` were not recognised, so the whole contract was read as one block and four clauses were reported missing when they were not. Two general fixes followed: support for `SECTION`/`CLAUSE`-style headings in capitals, and plain-English heading words (*Charges*, *Ending the contract*, *Law*, *Your content*). After that the held-out contract became part of the regression set, so it no longer counts as unseen.

**What the DORA held-out test showed.** All four real gaps were found, but three provisions that were there were reported missing. The causes were general, not specific to that contract:

1. Short numbered sub-clauses such as `6.2 Leverandøren samarbejder fuldt ud med Finanstilsynet.` were read as headings, and headings were not checked. This affected every check, not only DORA. Fixed in the segmenter.
2. Danish phrasing the patterns did not know: data is *stillet til rådighed* (made available) rather than returned, and the notice word came before the location word (*varsel, før placeringen af data ændres*).
3. A clause headed only `Data` was not recognised as data protection.

The contract is now part of the regression set.

**What this means.** The numbers above come from a small set of fictional contracts, partly used to build the rules. Real contracts are messier. Expect missed clauses on unusual layouts and occasional false flags. That is why every finding shows its evidence, and why the tool is built for a human reviewer, not instead of one. The next held-out contracts should be real ones, anonymised.

## Same result from any format

The risky sample is also stored as Word and PDF. A test checks that all three formats give identical findings and key terms. PDF extraction breaks lines mid-sentence, so single line breaks are not treated as sentence ends.

## Known limitations

- Tested on real public contracts as well as the author's own samples. The tool did much worse on the real ones at first; see [REAL-WORLD-TEST.md](REAL-WORLD-TEST.md).
- A permission to use data to *improve* a service, in a sentence that also contains a negation, can be missed (documented known miss).
- Terms in a cover page, order form or annex are not visible.

- Headings are needed to split clauses. Contracts written as one long block of text will be classified poorly.
- Tables, footnotes and appendices referenced by name (e.g. "the DPA in Appendix 3") are not read; the reference itself counts.
- The checks look at the customer's side of an AI or SaaS vendor contract. They are not a general contract review.
- Pattern-based negation handles common phrasing, not every legal construction.
- No legal advice. A qualified person should read the full contract.

## Related obligations

| Check | Why it matters | Source |
|---|---|---|
| Vendor may train on your data | Confidentiality, purpose limitation, controller role | GDPR Art. 5(1)(b), 28 |
| No data processing agreement | Written terms are required when a vendor processes personal data for you. The GDPR pack checks those terms | GDPR Art. 28 |
| Transfers without safeguards | Transfers outside the EU/EEA need a legal basis | GDPR Chapter V |
| No AI Act terms | Deployers must follow the provider's instructions and ensure human oversight | EU AI Act Art. 13, 26 |
| Vendor may end at any time | Exit and continuity risk; for financial entities also an ICT third-party question | DORA Art. 28 |
