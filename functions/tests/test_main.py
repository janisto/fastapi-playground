"""
Tests for the dad-joke Firebase Function.
"""

import asyncio
from collections.abc import Coroutine
from types import SimpleNamespace
from typing import Any

import main
import pytest
from firebase_functions import https_fn
from genkit import GenkitError
from genkit.plugin_api import ActionKind
from genkit_google_genai import VertexAI
from pydantic import ValidationError
from werkzeug.test import EnvironBuilder


def make_request(method: str = "GET", *, topic: str | None = None) -> https_fn.Request:
    """
    Build a Firebase-compatible HTTP request.
    """
    query_string = {"topic": topic} if topic is not None else None
    return https_fn.Request(EnvironBuilder(method=method, path="/", query_string=query_string).get_environ())


def close_coroutine(coro: Coroutine[object, object, object]) -> None:
    """
    Close a generated coroutine that a synchronous test replaces.
    """
    coro.close()


def test_function_manifest_requires_authenticated_invocation() -> None:
    """
    Verify deployment does not expose the model-backed endpoint publicly.
    """
    assert main.dad_joke.__firebase_endpoint__.httpsTrigger == {"invoker": ["private"]}


def test_vertex_model_uses_global_auto_updating_pro_alias() -> None:
    """
    Verify the Function follows the supported Pro alias through the global endpoint.
    """
    assert main.GEMINI_MODEL == "vertexai/gemini-pro-latest"
    assert main.VERTEX_AI_LOCATION == "global"


def test_installed_vertex_plugin_resolves_model_alias_without_discovery() -> None:
    """
    Verify the pinned Genkit plugin accepts the configured alias on demand.
    """
    plugin = VertexAI(location=main.VERTEX_AI_LOCATION)

    action = asyncio.run(plugin.resolve(ActionKind.MODEL, main.GEMINI_MODEL))

    assert action is not None


@pytest.mark.parametrize(
    "payload",
    [
        {"setup": "", "punchline": "Valid punchline"},
        {"setup": "   ", "punchline": "Valid punchline"},
        {"setup": "Valid setup", "punchline": ""},
        {"setup": "x" * (main.MAX_JOKE_LINE_LENGTH + 1), "punchline": "Valid punchline"},
        {"setup": "Valid setup", "punchline": "Valid punchline", "unexpected": "value"},
    ],
)
def test_generated_joke_schema_rejects_invalid_model_output(payload: dict[str, str]) -> None:
    """
    Verify the model contract rejects blank, oversized, and additional content.
    """
    with pytest.raises(ValidationError):
        main.GeneratedJoke.model_validate(payload)


def test_generated_joke_schema_strips_surrounding_whitespace() -> None:
    """
    Verify valid generated lines are normalized before reaching the API response.
    """
    joke = main.GeneratedJoke(setup="  Valid setup  ", punchline="  Valid punchline  ")

    assert joke.setup == "Valid setup"
    assert joke.punchline == "Valid punchline"


def test_generation_rejects_non_model_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify Genkit output must be the configured Pydantic model, not merely parsed JSON.
    """

    async def generate_unvalidated_output(**_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(output={"setup": "Valid setup", "punchline": "Valid punchline"})

    monkeypatch.setattr(main.genkit, "generate", generate_unvalidated_output)

    with pytest.raises(GenkitError) as exc_info:
        asyncio.run(main.generate_dad_joke())

    assert isinstance(exc_info.value.__cause__, main.InvalidGeneratedJokeError)


def test_non_get_method_is_rejected_before_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify unsupported methods cannot consume model quota.
    """
    run_async = pytest.fail
    monkeypatch.setattr(main, "run_async", run_async)

    response = main._handle_dad_joke(make_request("POST"))

    assert response.status_code == 405
    assert response.headers["Allow"] == "GET"
    assert response.get_json() == {"error": "METHOD_NOT_ALLOWED", "message": "Use GET"}


def test_invalid_topic_returns_actionable_400(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify invalid input is rejected without invoking the model.
    """
    warning_log: dict[str, object] = {}

    def capture_warning(message: str, **context: object) -> None:
        warning_log["message"] = message
        warning_log.update(context)

    monkeypatch.setattr(main, "run_async", pytest.fail)
    monkeypatch.setattr(main.logger, "warn", capture_warning)

    response = main._handle_dad_joke(make_request(topic="not-a-topic"))

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "INVALID_ARGUMENT"
    assert "work" in body["message"]
    assert "not-a-topic" not in str(warning_log)
    assert warning_log == {"message": "Invalid topic requested"}


def test_valid_topic_returns_generated_joke(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify validated topics reach generation and serialize the public contract.
    """

    def fake_run_async(coro: Coroutine[object, object, Any]) -> main.DadJoke:
        close_coroutine(coro)
        return main.DadJoke(
            setup="Why did the developer use dark mode?",
            punchline="Because light attracts bugs.",
            topic=main.JokeTopic.TECH,
            style=main.JokeStyle.PUN,
        )

    info_log: dict[str, object] = {}

    def capture_info(message: str, **context: object) -> None:
        info_log["message"] = message
        info_log.update(context)

    monkeypatch.setattr(main, "run_async", fake_run_async)
    monkeypatch.setattr(main.logger, "info", capture_info)

    response = main._handle_dad_joke(make_request(topic="TECH"))

    assert response.status_code == 200
    assert response.get_json() == {
        "setup": "Why did the developer use dark mode?",
        "punchline": "Because light attracts bugs.",
        "topic": "tech",
        "style": "pun",
    }
    assert info_log == {"message": "Generated dad joke", "topic_provided": True}


def test_unexpected_generation_failure_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify internal exception details are not returned to clients.
    """

    def fail_generation(coro: Coroutine[object, object, Any]) -> main.DadJoke:
        close_coroutine(coro)
        raise RuntimeError("credential secret must not escape")

    error_log: dict[str, object] = {}

    def capture_error(_message: str, **context: object) -> None:
        error_log.update(context)

    monkeypatch.setattr(main, "run_async", fail_generation)
    monkeypatch.setattr(main.logger, "error", capture_error)

    response = main._handle_dad_joke(make_request())

    assert response.status_code == 500
    body = response.get_json()
    assert body == {"error": "INTERNAL", "message": "An unexpected error occurred"}
    assert "secret" not in response.get_data(as_text=True)
    assert error_log == {"exception_type": "RuntimeError"}


def test_unexpected_value_error_is_not_misreported_as_invalid_topic(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify downstream ValueError failures remain sanitized server errors.
    """

    def fail_generation(coro: Coroutine[object, object, Any]) -> main.DadJoke:
        close_coroutine(coro)
        raise ValueError("generated value secret must not escape")

    monkeypatch.setattr(main, "run_async", fail_generation)

    response = main._handle_dad_joke(make_request(topic="tech"))

    assert response.status_code == 500
    assert response.get_json() == {"error": "INTERNAL", "message": "An unexpected error occurred"}
    assert "secret" not in response.get_data(as_text=True)


def test_invalid_generated_output_returns_retryable_sanitized_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify model schema failures are dependency failures rather than invalid topic errors.
    """

    def fail_generation(coro: Coroutine[object, object, Any]) -> main.DadJoke:
        close_coroutine(coro)
        return main.GeneratedJoke.model_validate({"setup": " ", "punchline": "must not escape"})

    error_log: dict[str, object] = {}

    def capture_error(_message: str, **context: object) -> None:
        error_log.update(context)

    monkeypatch.setattr(main, "run_async", fail_generation)
    monkeypatch.setattr(main.logger, "error", capture_error)

    response = main._handle_dad_joke(make_request(topic="tech"))

    assert response.status_code == 503
    assert response.get_json() == {"error": "INVALID_MODEL_OUTPUT", "message": "Failed to generate joke"}
    assert "must not escape" not in response.get_data(as_text=True)
    assert error_log == {
        "generation_status": "INVALID_MODEL_OUTPUT",
        "exception_type": "ValidationError",
    }


def test_wrapped_invalid_generated_output_keeps_stable_error_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify Genkit flow wrapping does not hide the invalid-output classification.
    """

    def fail_generation(coro: Coroutine[object, object, Any]) -> main.DadJoke:
        close_coroutine(coro)
        try:
            raise main.InvalidGeneratedJokeError
        except main.InvalidGeneratedJokeError as error:
            raise GenkitError(message="wrapped invalid output", status="INTERNAL") from error

    monkeypatch.setattr(main, "run_async", fail_generation)

    response = main._handle_dad_joke(make_request())

    assert response.status_code == 503
    assert response.get_json() == {"error": "INVALID_MODEL_OUTPUT", "message": "Failed to generate joke"}


def test_genkit_failure_returns_retryable_sanitized_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify model dependency failures expose a stable status without provider details.
    """

    def fail_generation(coro: Coroutine[object, object, Any]) -> main.DadJoke:
        close_coroutine(coro)
        raise GenkitError(message="provider credential secret", status="UNAVAILABLE")

    error_log: dict[str, object] = {}

    def capture_error(_message: str, **context: object) -> None:
        error_log.update(context)

    monkeypatch.setattr(main, "run_async", fail_generation)
    monkeypatch.setattr(main.logger, "error", capture_error)

    response = main._handle_dad_joke(make_request())

    assert response.status_code == 503
    assert response.get_json() == {"error": "UNAVAILABLE", "message": "Failed to generate joke"}
    assert "secret" not in response.get_data(as_text=True)
    assert error_log == {"generation_status": "UNAVAILABLE", "exception_type": "GenkitError"}
