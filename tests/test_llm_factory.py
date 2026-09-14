import pytest

from llm.deepseek_client import DeepSeekClient
from llm.factory import create_llm_client


def test_factory_builds_deepseek_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "test-model")

    client = create_llm_client("deepseek", max_output_tokens=123)

    assert isinstance(client, DeepSeekClient)
    assert client.model == "test-model"
    assert client.max_output_tokens == 123
    assert client.base_url == "https://api.deepseek.com"


def test_factory_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        create_llm_client("unknown")
