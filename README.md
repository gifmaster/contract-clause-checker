# AI Contract Clause Checker

[![tests](https://github.com/gifmaster/contract-clause-checker/actions/workflows/tests.yml/badge.svg)](https://github.com/gifmaster/contract-clause-checker/actions/workflows/tests.yml)
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://contract-clause-checker.streamlit.app)

**Find the key clauses in an AI or SaaS vendor contract, and the terms worth a second look.**

Upload a contract (PDF, Word or text, English or Danish). The tool splits it into clauses, pulls out the key terms, and flags risks from the customer's side, such as:

- the vendor may **train its models on your data**
- personal data is processed but **no data processing agreement** is referenced
- data may leave the EU **without safeguards**
- an AI service with **no terms supporting your EU AI Act duties**
- **automatic renewal**, **one-sided changes**, a vendor that can **end the service at any time**, **non-EU governing law**

Every finding shows the exact sentence it is based on and the rule that produced it.

**For banks, insurers and pension funds:** switch on the **DORA pack** to check the contract against the key contractual provisions in DORA Art. 30. Every AI tool a financial entity buys is an ICT service, so its contract must contain them. You get a checklist of all 12 provisions for any ICT service, or 18 for services supporting a critical or important function.

![DORA checklist](docs/screenshot-dora.png)

![Screenshot](docs/screenshot.png)

**[Try it live](https://contract-clause-checker.streamlit.app)** with four fictional sample contracts, including one for an insurer under DORA.

## Why rules, not an LLM

Same reason as the [EU AI Act Risk Check](https://github.com/gifmaster/ai-act-risk-check): a review tool should be able to show its work.

- Clause types and checks live in readable YAML files: [`clauses.yaml`](src/clausecheck/rules/clauses.yaml), [`checks.yaml`](src/clausecheck/rules/checks.yaml) and the DORA pack [`dora.yaml`](src/clausecheck/rules/dora.yaml)
- Every finding cites the sentence behind it
- Negations are handled: *"shall not use Customer Data to train"* is not flagged, *"may use Customer Data to train"* is
- Accuracy is measured against hand-labelled contracts and enforced in CI

A check looks like this:

```yaml
- id: no_dpa
  severity: high
  title: Personal data is processed, but no data processing agreement is referenced
  type: requires
  if_any: ['personal data', 'personoplysninger', ...]
  then_any: ['data processing (agreement|addendum)', 'article 28', 'databehandleraftale', ...]
  ref: GDPR Art. 28
```

## Accuracy, honestly

| Set | Clause detection | Checks (precision / recall) |
|---|---|---|
| Development samples (EN and DA) | 26 of 26 | 1.00 / 1.00 |
| Held-out contract, **first run** | 0 of 6 | 0.50 / 1.00 |
| Held-out contract, after two general fixes | 6 of 6 | 1.00 / 1.00 |
| DORA pack, development samples | 41 of 41 | 1.00 / 1.00 |
| Held-out Danish DORA contract, **first run** | 7 of 8 | 0.57 / 1.00 |
| Held-out Danish DORA contract, after three general fixes | 8 of 8 | 1.00 / 1.00 |

Each held-out test found real weaknesses: a heading style the rules did not know, and short numbered sub-clauses that were read as headings and never checked. They were fixed in general terms and are now regression tests. Small fictional test set, so treat the numbers as a floor for known patterns, not a promise for every contract. Details in [docs/METHOD.md](docs/METHOD.md).

## Run it locally

Recommended for real contracts, so they never leave your machine.

```bash
git clone https://github.com/gifmaster/contract-clause-checker.git
cd contract-clause-checker
pip install -r requirements.txt
streamlit run app.py
```

From Python:

```python
from clausecheck import Rules, analyse, read_file

result = analyse(read_file("contract.pdf"))
for f in result.findings:
    print(f.severity, f.title, f.evidence[:1])
print(result.values)   # governing law, notice periods, liability cap, ...

# DORA: "all" for any ICT service (Art. 30(2)), "critical" adds Art. 30(3)
result = analyse(read_file("contract.pdf"), dora="critical")
for check, covered in result.dora_checklist(Rules.builtin()):
    print("covered" if covered else "NOT FOUND", check["ref"], check["looked_for"])
```

## Tests

```bash
pip install pytest
pytest
```

69 tests: segmentation, negation and consent handling, rule validation, the DORA pack, accuracy against labelled contracts, identical results from PDF, Word and text, and app smoke tests.

## Part of a toolkit

| | |
|---|---|
| [EU AI Act Risk Check](https://github.com/gifmaster/ai-act-risk-check) | Classify an AI system under the EU AI Act |
| [Practical AI Governance Framework](https://github.com/gifmaster/ai-governance-framework) | Policy, roles, lifecycle and templates |
| This tool | Review the vendor contract before you buy |
| [AI Use Case Register](https://github.com/gifmaster/ai-use-case-register) | Keep track of every AI use case |
| [Regulation Navigator](https://github.com/gifmaster/regulation-navigator) | See which of the AI Act, GDPR, NIS2 and DORA apply, and where they overlap |

## Limitations

A screening aid for contract review, not legal advice. It needs headings to split clauses, does not read appendices, and covers the customer's side of AI and SaaS contracts. The DORA pack checks that a provision is there, not that it is good enough. See [docs/METHOD.md](docs/METHOD.md).

## About

Built by **Alexander Senderovitz**, AI governance and digital transformation, Copenhagen.
[senderovitz.eu](https://senderovitz.eu) · [alexander@senderovitz.eu](mailto:alexander@senderovitz.eu)

MIT License.
