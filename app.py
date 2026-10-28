"""Streamlit front end for the AI and SaaS contract clause checker.

Run locally:  streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

from clausecheck import Rules, analyse, processes_personal_data, read_bytes, to_csv, to_markdown  # noqa: E402
from clausecheck.report import VALUE_LABELS, format_value  # noqa: E402

REPO_URL = "https://github.com/gifmaster/contract-clause-checker"
SAMPLES = {
    "Risky AI vendor terms (English)": "01_brightloop_ai_terms_EN.txt",
    "Balanced AI SaaS agreement (English)": "02_nordlys_analytics_saas_EN.txt",
    "Abonnementsaftale (Danish)": "03_klarsprog_abonnementsaftale_DA.txt",
    "DORA contract for an insurer (English)": "06_havbro_claims_ai_DORA_EN.txt",
    "NIS2 contract for a water utility (English)": "11_vandvagt_ai_monitoring_NIS2_EN.txt",
    "Data processing agreement (English)": "08_nordlys_dpa_EN.txt",
    "Databehandleraftale (Danish)": "09_klarsprog_databehandleraftale_DA.txt",
}
DORA_OPTIONS = {
    "No": None,
    "Yes, an ICT service": "all",
    "Yes, supporting a critical or important function": "critical",
}
SEV = {"high": ("🔴", "High"), "medium": ("🟠", "Medium"), "low": ("🟡", "Low")}

st.set_page_config(page_title="AI Contract Clause Checker", page_icon="📄", layout="wide")


@st.cache_resource
def rules() -> Rules:
    return Rules.builtin()


R = rules()


def sample_changed() -> None:
    """Switch the DORA and NIS2 options on for their own samples, and off for the others."""
    st.session_state.dora = list(DORA_OPTIONS)[2 if st.session_state.sample.startswith("DORA") else 0]
    st.session_state.nis2 = st.session_state.sample.startswith("NIS2")


with st.sidebar:
    st.header("Contract")
    source = st.radio("Source", ["Sample contract", "Upload your own"], key="source")
    text, name = "", ""
    if source == "Sample contract":
        choice = st.selectbox("Sample", list(SAMPLES), key="sample", on_change=sample_changed)
        name = choice
        text = (ROOT / "samples" / SAMPLES[choice]).read_text(encoding="utf-8")
        st.caption("Fictional contracts written for this demo.")
    else:
        up = st.file_uploader("PDF, Word or text file", type=["pdf", "docx", "txt"])
        st.caption("Processed in memory and not stored. For confidential contracts, run the tool locally.")
        if up:
            try:
                text, name = read_bytes(up.getvalue(), up.name), up.name
            except Exception as exc:  # show a friendly message for unreadable files
                st.error(f"Could not read the file: {exc}")
    st.divider()
    dora_choice = st.radio(
        "Is the customer a financial entity under DORA?", list(DORA_OPTIONS), key="dora",
        help="Banks, insurers, pension funds, investment firms, payment and e-money institutions and others in DORA Art. 2. "
             "Every AI tool they buy is an ICT service, so its contract must contain the terms in DORA Art. 30.",
    )
    dora = DORA_OPTIONS[dora_choice]
    nis2 = st.toggle(
        "Is the customer covered by NIS2?", key="nis2",
        help="Essential and important entities under NIS2 (in Denmark the NIS2 Act), such as energy, water, transport, "
             "health and digital infrastructure. Checks the supply chain terms in point 5.1.4 of the Annex to "
             "Implementing Regulation (EU) 2024/2690.",
    )
    gdpr = st.toggle(
        "Check the data processing terms (GDPR Art. 28)", value=processes_personal_data(text, R) if text else False,
        key=f"gdpr_{name}",
        help="Switched on when the document mentions personal data. Checks the 12 terms a data processing agreement "
             "must contain. Works best on the data processing agreement itself.",
    )
    st.divider()
    st.markdown(
        f"**How it works.** The contract is split into clauses, each clause is matched against "
        f"[readable rules]({REPO_URL}/tree/main/src/clausecheck/rules), and risk checks run on the text. "
        "Every finding shows the sentence behind it. No AI guesses the answer."
    )
    st.caption("English and Danish contracts. Screening aid, not legal advice.")

st.title("AI Contract Clause Checker")
st.caption("Finds the key clauses in AI and SaaS vendor contracts and flags the terms worth a second look.")
with st.expander("What this tool does not catch"):
    st.markdown(
        "- **Whether a clause is good enough.** It checks that wording exists, not that it is adequate. A cap of one month of fees and a cap of "
        "twelve months both count as *a cap*, so the tool adds a separate flag for very small caps.\n"
        "- **Anything outside the text you give it.** Cover pages, order forms, annexes and website policies are invisible. A term that sits there "
        "will show as missing.\n"
        "- **Unusual drafting.** It reads sentences with rules, not legal meaning. Long cross-references, double negatives and unusual wording can "
        "slip through or be flagged wrongly.\n"
        "- **Your situation.** It does not know your sector, your risk appetite or whether a term is enforceable.\n"
        "- **How accurate it is.** Measured on public contracts the author did not write: see "
        "[the real-world test](https://github.com/gifmaster/contract-clause-checker/blob/main/docs/REAL-WORLD-TEST.md), including what it got wrong.\n\n"
        "A screening aid for the person reviewing the contract. Not legal advice."
    )

if not text.strip():
    st.info("Choose a sample contract or upload one to start.")
    st.stop()

result = analyse(text, R, dora=dora, gdpr=gdpr, nis2=nis2)
core = [f for f in result.findings if f.pack == "core"]
dora_findings = [f for f in result.findings if f.pack == "dora"]
n = {s: sum(f.severity == s for f in core) for s in SEV}

c1, c2, c3, c4 = st.columns(4)
c1.metric("High", n["high"])
c2.metric("Medium", n["medium"])
c3.metric("Low", n["low"])
c4.metric("Clauses found", f"{len(result.clauses)} of {len(R.labels)}")

left, right = st.columns([3, 2], gap="large")

with left:
    st.subheader("Findings")
    if result.is_dpa:
        st.info("This looks like a data processing agreement on its own. Only the contract checks that matter for a DPA "
                "are shown here. Check liability, termination and governing law in the main agreement.")
    if not core:
        st.success("No issues flagged by the checks. Still read the contract: the checks cover common risks, not everything.")
    for f in core:
        icon, label = SEV[f.severity]
        with st.expander(f"{icon} **{label}** · {f.title}", expanded=f.severity == "high"):
            st.markdown(f"{f.why}  \n`{f.ref}`")
            for e in f.evidence:
                st.markdown(f"> {e}")
            st.caption(f"Rule: `{f.id}`")

with right:
    st.subheader("Key terms")
    rows = [(label, format_value(k, result.values[k])) for k, label in VALUE_LABELS.items() if k in result.values]
    if rows:
        st.table({"Term": [r[0] for r in rows], "Value": [r[1] for r in rows]})
    st.subheader("Clauses")
    st.table({
        "Clause": list(R.labels.values()),
        "Found": ["✅" if result.found(c) else "No" for c in R.labels],
        "Where": ["; ".join(s.heading for s in result.clauses.get(c, [])) for c in R.labels],
    })
    st.download_button("Download review (Markdown)", to_markdown(result, R, name),
                       file_name="contract-review.md", mime="text/markdown", width="stretch")
    st.download_button("Download clause table (CSV)", to_csv(result, R),
                       file_name="contract-clauses.csv", mime="text/csv", width="stretch")

if gdpr:
    st.divider()
    gdpr_list = result.gdpr_checklist(R)
    covered = sum(ok for _, ok in gdpr_list)
    st.subheader("GDPR data processing terms")
    st.caption("Regulation (EU) 2016/679, Art. 28(2) to (4): what a data processing agreement must contain.")
    if result.dpa_elsewhere:
        st.info("**The data processing agreement is a separate document.** This contract points to it, so most of these "
                "terms are expected there. Upload the data processing agreement to check it. The list below is for this "
                "document only.")
    m1, m2 = st.columns([1, 3])
    m1.metric("Terms covered", f"{covered} of {len(gdpr_list)}")
    m2.progress(covered / len(gdpr_list))
    st.table({
        "": ["✅" if ok else "❌" for _, ok in gdpr_list],
        "Term": [k["looked_for"][0].upper() + k["looked_for"][1:] for k, _ in gdpr_list],
        "Reference": [k["ref"] for k, _ in gdpr_list],
    })
    if not result.dpa_elsewhere:
        for f in [f for f in result.findings if f.pack == "gdpr"]:
            icon, label = SEV[f.severity]
            with st.expander(f"{icon} **{label}** · {f.title}"):
                st.markdown(f"{f.why}  \n`{f.ref}`")
                st.caption(f"Looked for: {f.looked_for}. Rule: `{f.id}`")
    st.caption("✅ means wording for the term was found, not that it is good enough. Check how fast breaches are "
               "reported and how long deletion takes.")

if nis2:
    st.divider()
    nis2_list = result.nis2_checklist(R)
    covered = sum(ok for _, ok in nis2_list)
    st.subheader("NIS2 supply chain terms")
    st.caption("NIS2 Art. 21(2)(d) and point 5.1.4 of the Annex to Implementing Regulation (EU) 2024/2690. Binding for "
               "digital infrastructure and ICT service providers; for other NIS2 entities the most concrete reading of "
               "Art. 21(2)(d), to apply where your supply chain risk assessment calls for it.")
    m1, m2 = st.columns([1, 3])
    m1.metric("Terms covered", f"{covered} of {len(nis2_list)}")
    m2.progress(covered / len(nis2_list))
    st.table({
        "": ["✅" if ok else "❌" for _, ok in nis2_list],
        "Term": [k["looked_for"][0].upper() + k["looked_for"][1:] for k, _ in nis2_list],
        "Reference": [k["ref"] for k, _ in nis2_list],
    })
    for f in [f for f in result.findings if f.pack == "nis2"]:
        icon, label = SEV[f.severity]
        with st.expander(f"{icon} **{label}** · {f.title}"):
            st.markdown(f"{f.why}  \n`{f.ref}`")
            st.caption(f"Looked for: {f.looked_for}. Rule: `{f.id}`")
    st.caption("❌ means the wording was not found in the main contract text. Check appendices before concluding that a term is missing.")

if dora:
    st.divider()
    checklist = result.dora_checklist(R)
    covered = sum(ok for _, ok in checklist)
    st.subheader("DORA key contractual provisions")
    st.caption("Regulation (EU) 2022/2554, Art. 30(2) for all ICT services"
               + (", plus Art. 30(3) for services supporting critical or important functions." if dora == "critical" else "."))
    m1, m2 = st.columns([1, 3])
    m1.metric("Provisions covered", f"{covered} of {len(checklist)}")
    m2.progress(covered / len(checklist))
    st.table({
        "": ["✅" if ok else "❌" for _, ok in checklist],
        "Provision": [k["looked_for"][0].upper() + k["looked_for"][1:] for k, _ in checklist],
        "Reference": [k["ref"] for k, _ in checklist],
    })
    for f in dora_findings:
        icon, label = SEV[f.severity]
        with st.expander(f"{icon} **{label}** · {f.title}"):
            st.markdown(f"{f.why}  \n`{f.ref}`")
            st.caption(f"Looked for: {f.looked_for}. Rule: `{f.id}`")
    st.caption("❌ means the wording was not found in the main contract text. Check appendices and referenced documents "
               "before concluding that a term is missing.")

st.subheader("The contract, clause by clause")
for s in result.segments:
    tag = R.labels.get(s.clause, "Not classified") if s.clause else "Not classified"
    with st.expander(f"{s.heading or '(preamble)'}  ·  {tag}"):
        st.text(s.text or "(no text)")
