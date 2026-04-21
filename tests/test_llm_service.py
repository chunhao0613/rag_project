import pytest

from services import llm_service as ls


def test_extract_retry_seconds_from_error_text():
    assert ls._extract_retry_seconds("please retry in 12.7s") == 12
    assert ls._extract_retry_seconds("retry_delay { seconds: 9 }") == 9
    assert ls._extract_retry_seconds("no retry hint") is None


def test_run_llm_routes_google_provider(monkeypatch):
    class Response:
        content = "google-answer"

    monkeypatch.setattr(
        ls,
        "_invoke_google_with_model_fallback",
        lambda messages, preferred_model=None: Response(),
    )

    result = ls._run_llm("google", "gemini-2.0-flash-lite", "prompt", ["m1"])

    assert result == "google-answer"


def test_run_llm_routes_huggingface_provider(monkeypatch):
    monkeypatch.setattr(ls, "_hf_chat", lambda prompt_text, model: "hf-answer")

    result = ls._run_llm("huggingface", "mistral", "prompt", [])

    assert result == "hf-answer"


def test_run_llm_rejects_unsupported_provider():
    with pytest.raises(RuntimeError, match="Unsupported llm provider"):
        ls._run_llm("unsupported", "model", "prompt", [])
