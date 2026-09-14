import os

from configs.environment import load_project_env


def test_load_project_env_reads_file(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("TEST_BROWSER_AGENT_VALUE=from-file\n", encoding="utf-8")
    monkeypatch.delenv("TEST_BROWSER_AGENT_VALUE", raising=False)

    assert load_project_env(env_file)
    assert os.environ["TEST_BROWSER_AGENT_VALUE"] == "from-file"


def test_load_project_env_preserves_existing_value(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("TEST_BROWSER_AGENT_VALUE=from-file\n", encoding="utf-8")
    monkeypatch.setenv("TEST_BROWSER_AGENT_VALUE", "from-process")

    load_project_env(env_file)

    assert os.environ["TEST_BROWSER_AGENT_VALUE"] == "from-process"
