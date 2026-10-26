"""Streamlit front end for the AI and SaaS contract clause checker.

Run locally:  streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

from clausecheck import Rules, analyse, read_bytes, to_csv, to_markdown  # noqa: E402
from clausecheck.report import VALUE_LABELS, format_value  # noqa: E402

REPO_URL = "https://github.com/gifmaster/contract-clause-checker"
SAMPLES = {
    "Risky AI vendor terms (English)": "01_brightloop_ai_terms_EN.txt",
    "Balanced AI SaaS agreement (English)": "02_nordlys_analytics_saas_EN.txt",
    "Abonnementsaftale (Danish)": "03_klarsprog_abonnementsaftale_DA.txt",
}
SEV = {"high": ("🔴", "High"), "medium": ("🟠", "Medium"), "low": ("🟡", "Low")}

st.set_page_config(page_title="AI Contract Clause Checker", page_icon="📄", layout="wide")


@st.cache_resource
def rules() -> Rules:
    return Rules.builtin()


R = rules()

with st.sidebar:
    st.header("Contract")
    source = st.radio("Source", ["Sample contract", "Upload your own"], key="source")
    text, name = "", ""
    if source == "Sample contract":
        choice = st.selectbox("Sample", list(SAMPLES), key="sample")
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
    st.markdown(
        f"**How it works.** The contract is split into clauses, each clause is matched against "
        f"[readable rules]({REPO_URL}/tree/main/src/clausecheck/rules), and risk checks run on the text. "
        "Every finding shows the sentence behind it. No AI guesses the answer."
    )
    st.caption("English and Danish contracts. Screening aid, not legal advice.")

st.title("AI Contract Clause Checker")
st.caption("Finds the key clauses in AI and SaaS vendor contracts and flags the terms worth a second look.")

if not text.strip():
    st.info("Choose a sample contract or upload one to start.")
    st.stop()

result = analyse(text, R)
n = {s: sum(f.severity == s for f in result.findings) for s in SEV}

c1, c2, c3, c4 = st.columns(4)
c1.metric("High", n["high"])
c2.metric("Medium", n["medium"])
c3.metric("Low", n["low"])
c4.metric("Clauses found", f"{len(result.clauses)} of {len(R.labels)}")

left, right = st.columns([3, 2], gap="large")

with left:
    st.subheader("Findings")
    if not result.findings:
        st.success("No issues flagged by the checks. Still read the contract: the checks cover common risks, not everything.")
    for f in result.findings:
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

st.subheader("The contract, clause by clause")
for s in result.segments:
    tag = R.labels.get(s.clause, "Not classified") if s.clause else "Not classified"
    with st.expander(f"{s.heading or '(preamble)'}  ·  {tag}"):
        st.text(s.text or "(no text)")
