"""Strict Firebase bearer parsing and failure classification tests."""

import asyncio
import logging
from unittest.mock import Mock

import pytest
from firebase_admin.auth import (
    CertificateFetchError,
    ExpiredIdTokenError,
    InvalidIdTokenError,
    RevokedIdTokenError,
    UserDisabledError,
)
from starlette.requests import Request

from app.auth.firebase import verify_firebase_token
from app.core.problems import PortableProblem


def _request(headers: list[tuple[bytes, bytes]]) -> Request:
    return Request({"type": "http", "method": "GET", "path": "/v1/profile", "headers": headers})


@pytest.mark.parametrize(
    "headers",
    [
        [],
        [(b"authorization", b"Basic abc")],
        [(b"authorization", b"Bearer\tabc")],
        [(b"authorization", b"Bearer abc,def")],
        [(b"authorization", b"Bearer abc"), (b"authorization", b"Bearer def")],
        [(b"authorization", b"Bearer abc def")],
    ],
)
async def test_malformed_credentials_are_401_without_verifier_call(
    headers: list[tuple[bytes, bytes]], monkeypatch: pytest.MonkeyPatch
) -> None:
    verifier = Mock()
    monkeypatch.setattr("app.auth.firebase.auth.verify_id_token", verifier)
    with pytest.raises(PortableProblem) as captured:
        await verify_firebase_token(_request(headers))
    assert captured.value.code == "unauthorized"
    assert captured.value.headers == {"WWW-Authenticate": "Bearer"}
    verifier.assert_not_called()


async def test_valid_token68_is_verified_with_revocation_and_uses_sub(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = Mock(return_value={"sub": "principal-123"})
    app = object()
    monkeypatch.setattr("app.auth.firebase.get_firebase_app", lambda: app)
    monkeypatch.setattr("app.auth.firebase.auth.verify_id_token", verifier)
    user = await verify_firebase_token(_request([(b"authorization", b"bEaReR   abc_DEF-123==")]))
    assert user.uid == "principal-123"
    verifier.assert_called_once_with("abc_DEF-123==", app=app, check_revoked=True)


@pytest.mark.parametrize(
    ("case", "error"),
    [
        ("expired", ExpiredIdTokenError("credential-secret", RuntimeError("cause-secret"))),
        ("revoked", RevokedIdTokenError("credential-secret")),
        ("disabled", UserDisabledError("credential-secret")),
        ("wrong audience", InvalidIdTokenError("credential-secret")),
        ("wrong issuer", InvalidIdTokenError("credential-secret")),
        ("none algorithm", InvalidIdTokenError("credential-secret")),
        ("HS algorithm", InvalidIdTokenError("credential-secret")),
        ("known-key bad signature", InvalidIdTokenError("credential-secret")),
    ],
)
async def test_credential_rejections_are_401_without_sensitive_logs(
    case: str,
    error: Exception,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    del case
    monkeypatch.setattr("app.auth.firebase.get_firebase_app", Mock())
    monkeypatch.setattr("app.auth.firebase.auth.verify_id_token", Mock(side_effect=error))
    with caplog.at_level(logging.WARNING, logger="app.auth.firebase"), pytest.raises(PortableProblem) as captured:
        await verify_firebase_token(_request([(b"authorization", b"Bearer caller-credential-secret")]))
    assert captured.value.code == "unauthorized"
    assert captured.value.headers == {"WWW-Authenticate": "Bearer"}
    assert "caller-credential-secret" not in caplog.text
    assert "credential-secret" not in caplog.text
    assert "cause-secret" not in caplog.text


@pytest.mark.parametrize("principal", [None, "", 42, "x" * 129, "principal-\ud800"])
async def test_invalid_verified_subject_is_401(
    principal: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.auth.firebase.get_firebase_app", Mock())
    monkeypatch.setattr("app.auth.firebase.auth.verify_id_token", Mock(return_value={"sub": principal}))
    with pytest.raises(PortableProblem) as captured:
        await verify_firebase_token(_request([(b"authorization", b"Bearer abc")]))
    assert captured.value.code == "unauthorized"
    assert captured.value.headers == {"WWW-Authenticate": "Bearer"}


@pytest.mark.parametrize(
    "failure",
    [CertificateFetchError("provider-secret", RuntimeError("cause-secret")), RuntimeError("provider-secret")],
)
async def test_verifier_dependency_failures_are_safe_503(
    failure: Exception,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr("app.auth.firebase.get_firebase_app", Mock())
    monkeypatch.setattr("app.auth.firebase.auth.verify_id_token", Mock(side_effect=failure))
    with caplog.at_level(logging.ERROR, logger="app.auth.firebase"), pytest.raises(PortableProblem) as captured:
        await verify_firebase_token(_request([(b"authorization", b"Bearer caller-secret")]))
    assert captured.value.code == "dependency_unavailable"
    assert captured.value.headers == {"Retry-After": "30"}
    assert "caller-secret" not in caplog.text
    assert "provider-secret" not in caplog.text
    assert "cause-secret" not in caplog.text


async def test_cancellation_is_not_reclassified_as_dependency_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.auth.firebase.get_firebase_app", Mock())
    monkeypatch.setattr("app.auth.firebase.auth.verify_id_token", Mock(side_effect=asyncio.CancelledError))
    with pytest.raises(asyncio.CancelledError):
        await verify_firebase_token(_request([(b"authorization", b"Bearer abc")]))
