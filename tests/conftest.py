from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from src.auth_utils import AuthContext


@pytest.fixture(autouse=True)
def security_test_env(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGIN", "http://localhost:8501")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("COGNITO_REGION", "ap-south-1")
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "ap-south-1_testpool")
    monkeypatch.setenv("COGNITO_APP_CLIENT_ID", "test-client-id")


@pytest.fixture(autouse=True)
def default_auth_context(monkeypatch, request):
    if request.node.get_closest_marker("auth_real"):
        return

    auth_context = AuthContext(
        sub="user-123",
        email="user@example.com",
        claims={"sub": "user-123", "email": "user@example.com"},
    )
    monkeypatch.setattr("src.api_handler.get_auth_context", lambda event: (auth_context, None))

    def _load_owned_session(raw_session_id, auth_ctx):
        from src.api_handler import create_response, kitchen_agent, validate_session_id

        try:
            session_id = validate_session_id(raw_session_id)
        except ValueError as exc:
            return None, None, create_response(
                status_code=400,
                body={'error': 'invalid_request', 'message': f'Invalid session_id: {exc}'}
            )

        get_session = kitchen_agent.get_session
        if isinstance(get_session, Mock):
            session_data = get_session(session_id)
            if isinstance(session_data, Mock):
                session_data = {
                    'session_id': session_id,
                }
        else:
            session_data = {
                'session_id': session_id,
                'owner_sub': auth_ctx.sub,
                'expiry_timestamp': int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
            }
        if not session_data:
            return None, None, create_response(
                status_code=404,
                body={'error': 'session_not_found', 'message': f'Session not found: {session_id}. Please create a new session.'}
            )

        if 'owner_sub' not in session_data:
            session_data['owner_sub'] = auth_ctx.sub

        if session_data.get('owner_sub') != auth_ctx.sub:
            return None, None, create_response(
                status_code=403,
                body={'error': 'forbidden', 'message': 'You do not have access to this session.'}
            )

        session_data.setdefault(
            'expiry_timestamp',
            int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
        )

        is_valid = kitchen_agent.is_session_valid(session_data)
        if not is_valid:
            return None, None, create_response(
                status_code=401,
                body={'error': 'session_expired', 'message': 'Session has expired. Please create a new session.'}
            )

        return session_id, session_data, None

    monkeypatch.setattr("src.api_handler.load_owned_session", _load_owned_session)
