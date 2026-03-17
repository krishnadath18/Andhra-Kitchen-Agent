import pytest
from jwt.exceptions import InvalidTokenError

from src.auth_utils import AuthenticationError, require_authenticated_user


def test_require_authenticated_user_uses_gateway_claims():
    event = {
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "user-123",
                    "email": "user@example.com",
                }
            }
        }
    }

    auth_context = require_authenticated_user(event)

    assert auth_context.sub == "user-123"
    assert auth_context.email == "user@example.com"


def test_require_authenticated_user_requires_authorization_header():
    with pytest.raises(AuthenticationError, match="Missing Authorization header"):
        require_authenticated_user({"headers": {}})


def test_require_authenticated_user_rejects_invalid_authorization_scheme():
    event = {"headers": {"Authorization": "Token abc"}}

    with pytest.raises(AuthenticationError, match="Bearer token format"):
        require_authenticated_user(event)


def test_require_authenticated_user_validates_bearer_token(monkeypatch):
    class FakeSigningKey:
        key = "public-key"

    class FakeJWKClient:
        def get_signing_key_from_jwt(self, token):
            assert token == "good-token"
            return FakeSigningKey()

    monkeypatch.setattr("src.auth_utils._get_jwk_client", lambda *args: FakeJWKClient())
    monkeypatch.setattr(
        "src.auth_utils.jwt.decode",
        lambda *args, **kwargs: {
            "sub": "user-123",
            "email": "user@example.com",
            "token_use": "id",
        }
    )

    auth_context = require_authenticated_user(
        {"headers": {"Authorization": "Bearer good-token"}}
    )

    assert auth_context.sub == "user-123"


def test_require_authenticated_user_rejects_expired_token(monkeypatch):
    class FakeJWKClient:
        def get_signing_key_from_jwt(self, token):
            return type("Key", (), {"key": "public-key"})()

    monkeypatch.setattr("src.auth_utils._get_jwk_client", lambda *args: FakeJWKClient())

    def _raise(*args, **kwargs):
        raise InvalidTokenError("Signature has expired")

    monkeypatch.setattr("src.auth_utils.jwt.decode", _raise)

    with pytest.raises(AuthenticationError, match="Invalid bearer token"):
        require_authenticated_user({"headers": {"Authorization": "Bearer expired-token"}})


def test_require_authenticated_user_requires_id_token(monkeypatch):
    class FakeJWKClient:
        def get_signing_key_from_jwt(self, token):
            return type("Key", (), {"key": "public-key"})()

    monkeypatch.setattr("src.auth_utils._get_jwk_client", lambda *args: FakeJWKClient())
    monkeypatch.setattr(
        "src.auth_utils.jwt.decode",
        lambda *args, **kwargs: {"sub": "user-123", "token_use": "access"}
    )

    with pytest.raises(AuthenticationError, match="ID token"):
        require_authenticated_user({"headers": {"Authorization": "Bearer access-token"}})
