"""
tests/test_app.py

Smoke tests for app.py using Streamlit's AppTest framework — verifies the
app loads without exceptions, all six tabs render, the component tagging +
cache-skip flow works end to end (not mocked — a real second ingestion is
run and checked to skip), and the Investigate tab's NotImplementedError
handling shows the expected message rather than crashing.
"""

import pytest
from streamlit.testing.v1 import AppTest

# Tab order: Source code, Logs, Documents, Components, Investigate, Ingested artifacts
SOURCE_CODE_TAB, LOGS_TAB, DOCS_TAB, COMPONENTS_TAB, INVESTIGATE_TAB, BROWSE_TAB = range(6)


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Run the app against an isolated DuckDB file, same pattern as the other tests."""
    from utils import storage

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.duckdb")
    at = AppTest.from_file("app.py")
    at.run(timeout=15)
    return at


@pytest.fixture
def code_folder(tmp_path):
    """A small local folder with one recognized source file, for ingestion tests."""
    folder = tmp_path / "src"
    folder.mkdir()
    (folder / "lock.c").write_text("int tuner_lock_retry(int freq) { return 0; }\n")
    return str(folder)


def test_app_loads_without_exceptions(app):
    assert not app.exception


def test_all_six_tabs_render(app):
    assert len(app.tabs) == 6


def test_investigate_tab_shows_not_implemented_message(app):
    investigate_tab = app.tabs[INVESTIGATE_TAB]

    investigate_tab.text_area(key="investigate_question").input(
        "Why does the XR400 reboot after standby?"
    )
    investigate_tab.button(key="investigate_btn").click()
    app.run(timeout=15)

    assert not app.exception
    info_messages = [i.value for i in app.tabs[INVESTIGATE_TAB].info]
    assert any("not yet built" in msg for msg in info_messages)


def test_investigate_tab_lists_the_six_agent_tools(app):
    from agent.tools import TOOL_DEFINITIONS

    investigate_tab = app.tabs[INVESTIGATE_TAB]
    markdown_text = " ".join(m.value for m in investigate_tab.markdown)
    for tool in TOOL_DEFINITIONS:
        assert tool["name"] in markdown_text


def test_components_tab_shows_empty_state_before_any_tagging(app):
    components_tab = app.tabs[COMPONENTS_TAB]
    info_messages = [i.value for i in components_tab.info]
    assert any("No components tagged yet" in msg for msg in info_messages)


def test_ingesting_code_with_a_component_tags_it_and_shows_in_component_map(app, code_folder):
    code_tab = app.tabs[SOURCE_CODE_TAB]
    code_tab.text_input(key="code_components_input").input("Tuner")
    code_tab.text_input(key="code_folder").input(code_folder)
    code_tab.button(key="code_folder_btn").click()
    app.run(timeout=15)

    assert not app.exception
    success_messages = [s.value for s in app.tabs[SOURCE_CODE_TAB].success]
    assert any("Registered 1 source files" in msg for msg in success_messages)

    # The Components tab should now show Tuner as a known component with 1 code file.
    components_tab = app.tabs[COMPONENTS_TAB]
    select = components_tab.selectbox(key="component_lookup_select")
    assert "Tuner" in select.options


def test_second_ingestion_of_same_component_hits_cache_and_skips(app, code_folder, tmp_path):
    code_tab = app.tabs[SOURCE_CODE_TAB]

    # First ingestion — real, should succeed and register the file.
    code_tab.text_input(key="code_components_input").input("Tuner")
    code_tab.text_input(key="code_folder").input(code_folder)
    code_tab.button(key="code_folder_btn").click()
    app.run(timeout=15)
    assert not app.exception

    # Second ingestion against the SAME component, different folder — should
    # hit the cache and skip, per the requested behavior, rather than
    # re-scanning the new folder.
    other_folder = tmp_path / "other_src"
    other_folder.mkdir()
    (other_folder / "other.c").write_text("int unrelated(void) { return 1; }\n")

    code_tab2 = app.tabs[SOURCE_CODE_TAB]
    code_tab2.text_input(key="code_components_input").input("Tuner")
    code_tab2.text_input(key="code_folder").input(str(other_folder))
    code_tab2.button(key="code_folder_btn").click()
    app.run(timeout=15)

    assert not app.exception
    info_messages = [i.value for i in app.tabs[SOURCE_CODE_TAB].info]
    assert any("Cache hit" in msg for msg in info_messages)

    # The cache-hit path must NOT have registered other.c — only the original
    # lock.c should be tagged under Tuner.
    from utils.storage import get_artifacts_by_component

    tuner_code = get_artifacts_by_component("Tuner", "code")
    assert len(tuner_code) == 1
    assert tuner_code.iloc[0]["display_name"] == "lock.c"


def test_force_refresh_bypasses_cache(app, code_folder, tmp_path):
    code_tab = app.tabs[SOURCE_CODE_TAB]
    code_tab.text_input(key="code_components_input").input("Tuner")
    code_tab.text_input(key="code_folder").input(code_folder)
    code_tab.button(key="code_folder_btn").click()
    app.run(timeout=15)
    assert not app.exception

    other_folder = tmp_path / "other_src"
    other_folder.mkdir()
    (other_folder / "other.c").write_text("int unrelated(void) { return 1; }\n")

    code_tab2 = app.tabs[SOURCE_CODE_TAB]
    code_tab2.text_input(key="code_components_input").input("Tuner")
    code_tab2.checkbox(key="code_force_refresh").set_value(True)
    code_tab2.text_input(key="code_folder").input(str(other_folder))
    code_tab2.button(key="code_folder_btn").click()
    app.run(timeout=15)

    assert not app.exception
    success_messages = [s.value for s in app.tabs[SOURCE_CODE_TAB].success]
    assert any("Registered 1 source files" in msg for msg in success_messages)

    from utils.storage import get_artifacts_by_component

    tuner_code = get_artifacts_by_component("Tuner", "code")
    assert len(tuner_code) == 2  # both lock.c and other.c now tagged Tuner
