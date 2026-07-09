"""
tests/test_app.py

Smoke tests for app.py using Streamlit's AppTest framework — verifies the
app loads without exceptions, all five tabs render, and the Investigate
tab's NotImplementedError handling shows the expected message rather than
crashing, since the agent layer isn't built yet.
"""

import pytest
from streamlit.testing.v1 import AppTest


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Run the app against an isolated DuckDB file, same pattern as the other tests."""
    from utils import storage

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.duckdb")
    at = AppTest.from_file("app.py")
    at.run(timeout=15)
    return at


def test_app_loads_without_exceptions(app):
    assert not app.exception


def test_all_five_tabs_render(app):
    assert len(app.tabs) == 5


def test_investigate_tab_shows_not_implemented_message(app):
    # tabs order: Source code, Logs, Documents, Investigate, Ingested artifacts
    investigate_tab = app.tabs[3]

    investigate_tab.text_area(key="investigate_question").input(
        "Why does the XR400 reboot after standby?"
    )
    investigate_tab.button(key="investigate_btn").click()
    app.run(timeout=15)

    assert not app.exception
    info_messages = [i.value for i in app.tabs[3].info]
    assert any("not yet built" in msg for msg in info_messages)


def test_investigate_tab_lists_the_six_agent_tools(app):
    from agent.tools import TOOL_DEFINITIONS

    investigate_tab = app.tabs[3]
    markdown_text = " ".join(m.value for m in investigate_tab.markdown)
    for tool in TOOL_DEFINITIONS:
        assert tool["name"] in markdown_text
