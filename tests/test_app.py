"""Smoke tests for the Streamlit app."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).parents[1] / "app.py")


def text_of(at):
    parts = [m.value for m in at.markdown] + [e.label for e in at.expander] + [h.value for h in at.subheader]
    parts += [str(m.value) for m in at.metric]
    for kind in ("success", "info", "warning", "error"):
        parts += [e.value for e in getattr(at, kind)]
    return "\n".join(parts)


def test_risky_sample_shows_high_findings():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    t = text_of(at)
    assert "train or improve its models" in t
    assert "Governing law outside the EU" in t


def test_balanced_sample_is_clean():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.selectbox(key="sample").set_value("Balanced AI SaaS agreement (English)").run()
    assert not at.exception
    assert "No issues flagged" in text_of(at)


def test_danish_sample_runs():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.selectbox(key="sample").set_value("Abonnementsaftale (Danish)").run()
    assert not at.exception
    assert "Automatic renewal" in text_of(at)


def test_dora_sample_shows_checklist():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.selectbox(key="sample").set_value("DORA contract for an insurer (English)").run()
    assert not at.exception
    assert at.radio(key="dora").value.startswith("Yes, supporting")
    t = text_of(at)
    assert "DORA key contractual provisions" in t and "16 of 18" in t
    assert "threat-led penetration testing" in t


def test_dora_switch_on_risky_sample():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.radio(key="dora").set_value("Yes, an ICT service").run()
    assert not at.exception
    assert "2 of 12" in text_of(at)
