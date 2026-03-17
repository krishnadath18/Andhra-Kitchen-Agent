import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from src.api_handler import handle_get_reminders, handle_get_session


pytestmark = pytest.mark.auth_real


def _authorized_event(path: str, sub: str = "user-123"):
    return {
        "httpMethod": "GET",
        "path": path,
        "headers": {},
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": sub,
                    "email": "user@example.com",
                }
            }
        },
    }


@patch("src.api_handler.kitchen_agent")
def test_handle_get_session_requires_auth(mock_agent):
    response = handle_get_session({"httpMethod": "GET", "path": "/session/sess_123", "headers": {}})

    assert response["statusCode"] == 401
    body = json.loads(response["body"])
    assert body["error"] == "unauthorized"


@patch("src.api_handler.kitchen_agent")
def test_handle_get_session_rejects_legacy_session(mock_agent):
    mock_agent.get_session.return_value = {
        "session_id": "sess_123",
        "user_language": "en",
        "expiry_timestamp": int((datetime.now(timezone.utc) + timedelta(days=1)).timestamp()),
    }

    response = handle_get_session(_authorized_event("/session/sess_123"))

    assert response["statusCode"] == 401
    body = json.loads(response["body"])
    assert body["error"] == "legacy_session_invalid"


@patch("src.api_handler.kitchen_agent")
def test_handle_get_session_rejects_other_users_session(mock_agent):
    mock_agent.get_session.return_value = {
        "session_id": "sess_123",
        "owner_sub": "other-user",
        "user_language": "en",
        "expiry_timestamp": int((datetime.now(timezone.utc) + timedelta(days=1)).timestamp()),
    }

    response = handle_get_session(_authorized_event("/session/sess_123"))

    assert response["statusCode"] == 403
    body = json.loads(response["body"])
    assert body["error"] == "forbidden"


@patch("src.api_handler.kitchen_agent")
def test_handle_get_reminders_rejects_other_users_session(mock_agent):
    mock_agent.get_session.return_value = {
        "session_id": "sess_123",
        "owner_sub": "other-user",
        "user_language": "en",
        "expiry_timestamp": int((datetime.now(timezone.utc) + timedelta(days=1)).timestamp()),
    }

    response = handle_get_reminders(_authorized_event("/reminders/sess_123"))

    assert response["statusCode"] == 403
    body = json.loads(response["body"])
    assert body["error"] == "forbidden"
