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

![Screenshot](docs/screenshot.png)

**[Try it live](https://contract-clause-checker.streamlit.app)** with three fictional sample contracts.

## Why rules, not an LLM

Same reason as the [EU AI Act Risk Check](https://github.com/gifmaster/ai-act-risk-check): a review tool should be able to show its work.

- Clause types and checks live in two readable YAML files: [`clauses.yaml`](src/clausecheck/rules/clauses.yaml) and [`checks.yaml`](src/clausecheck/rules/checks.yaml)
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

The held-out test found a real weakness (a heading style the rules did not know). It was fixed in general terms and is now a regression test. Small fictional test set, so treat the numbers as a floor for known patterns, not a promise for every contract. Details in [docs/METHOD.md](docs/METHOD.md).

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
from clausecheck import analyse, read_file

result = analyse(read_file("contract.pdf"))
for f in result.findings:
    print(f.severity, f.title, f.evidence[:1])
print(result.values)   # governing law, notice periods, liability cap, ...
```

## Tests

```bash
pip install pytest
pytest
```

38 tests: segmentation, negation and consent handling, rule validation, accuracy against labelled contracts, identical results from PDF, Word and text, and app smoke tests.

## Part of a toolkit

| | |
|---|---|
| [EU AI Act Risk Check](https://github.com/gifmaster/ai-act-risk-check) | Classify an AI system under the EU AI Act |
| [Practical AI Governance Framework](https://github.com/gifmaster/ai-governance-framework) | Policy, roles, lifecycle and templates |
| This tool | Review the vendor contract before you buy |

## Limitations

A screening aid for contract review, not legal advice. It needs headings to split clauses, does not read appendices, and covers the customer's side of AI and SaaS contracts. See [docs/METHOD.md](docs/METHOD.md).

## About

Built by **Alexander Senderovitz**, AI governance and digital transformation, Copenhagen.
[senderovitz.eu](https://senderovitz.eu) · [alexander@senderovitz.eu](mailto:alexander@senderovitz.eu)

MIT License.
