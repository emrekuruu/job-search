import pytest

from job_search import providers
from job_search.config import settings


def test_unknown_backend_raises():
    with pytest.raises(ValueError, match="unknown backend"):
        providers.get_model("gpt5")


def test_missing_credential_raises(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", None)
    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        providers.get_model("deepseek")


def test_agents_import():
    from job_search.agents import eval_agent, query_agent

    assert query_agent is not None
    assert eval_agent is not None
