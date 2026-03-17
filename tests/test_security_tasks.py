import importlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest


class FakeSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


def _reload_env_module():
    import config.env as env_module
    return importlib.reload(env_module)


@pytest.fixture
def restore_safe_env(monkeypatch):
    yield
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("ALLOWED_ORIGIN", "http://localhost:8501")
    _reload_env_module()


def test_config_rejects_wildcard_cors_in_prod(monkeypatch, restore_safe_env):
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setenv("ALLOWED_ORIGIN", "*")
    with pytest.raises(ValueError, match="ALLOWED_ORIGIN='\\*'"):
        _reload_env_module()


def test_config_rejects_non_https_cors_in_prod(monkeypatch, restore_safe_env):
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setenv("ALLOWED_ORIGIN", "http://example.com")
    with pytest.raises(ValueError, match="valid HTTPS URL"):
        _reload_env_module()


def test_config_accepts_specific_https_origin_in_prod(monkeypatch, restore_safe_env):
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setenv("ALLOWED_ORIGIN", "https://example.com")
    reloaded = _reload_env_module()
    assert reloaded.Config.validate_cors_config() is True


def test_validate_session_id_rejects_reserved_and_traversal(monkeypatch):
    from src.security_utils import validate_session_id

    monkeypatch.setenv("SESSION_ID_STRICT_VALIDATION", "true")

    with pytest.raises(ValueError, match="reserved keywords"):
        validate_session_id("admin")

    with pytest.raises(ValueError, match="path traversal"):
        validate_session_id("user123..data")


def test_sanitize_user_input_blocks_malicious_patterns(monkeypatch):
    from src.security_utils import sanitize_user_input

    monkeypatch.setenv("INPUT_VALIDATION_STRICT", "true")

    with pytest.raises(ValueError, match="sql injection"):
        sanitize_user_input("hello'; DROP TABLE users;--")

    with pytest.raises(ValueError, match="xss"):
        sanitize_user_input("<script>alert(1)</script>")

    with pytest.raises(ValueError, match="command injection"):
        sanitize_user_input("nice ;cat /etc/passwd")


def test_sanitize_user_input_preserves_valid_content(monkeypatch):
    from src.security_utils import sanitize_user_input

    monkeypatch.setenv("INPUT_VALIDATION_STRICT", "true")

    cleaned = sanitize_user_input("  Make   tomato rice\ttonight  ")
    assert cleaned == "Make tomato rice tonight"


def test_sanitize_for_logging_redacts_nested_sensitive_fields():
    from src.security_utils import sanitize_for_logging

    sanitized = sanitize_for_logging(
        {
            "email": "user@example.com",
            "nested": {
                "refresh_token": "secret-token",
                "items": [{"phone": "1234567890"}],
            },
            "items": [{"preferences": {"spice": "high"}}],
        }
    )

    assert sanitized["email"] == "[REDACTED]"
    assert sanitized["nested"]["refresh_token"] == "[REDACTED]"
    assert sanitized["nested"]["items"][0]["phone"] == "[REDACTED]"
    assert sanitized["items"][0]["preferences"] == "[REDACTED]"


def test_security_headers_use_strict_csp(monkeypatch):
    from src.security_utils import create_secure_response_headers

    monkeypatch.setenv("CSP_STRICT_MODE", "true")
    monkeypatch.setenv("CSP_ALLOW_INLINE_STYLES", "true")
    headers = create_secure_response_headers("https://example.com")

    csp = headers["Content-Security-Policy"]
    assert "script-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "style-src 'self' 'unsafe-inline'" in csp
    assert "frame-ancestors 'none'" in csp


def test_handle_chat_rejects_oversized_request():
    from src.api_handler import handle_chat

    oversized_message = "a" * (1024 * 1024)
    event = {
        "httpMethod": "POST",
        "path": "/chat",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"session_id": "sess_test123", "message": oversized_message}),
    }

    response = handle_chat(event)

    assert response["statusCode"] == 413


def test_password_strength_helper_reports_missing_requirements():
    import app

    result = app.check_password_strength("password")

    assert result["strength"] in {"Weak", "Fair"}
    assert any("uppercase" in message.lower() for message in result["feedback"])
    assert any("number" in message.lower() for message in result["feedback"])


def test_https_security_stops_insecure_prod_requests(monkeypatch):
    import app

    fake_state = FakeSessionState()
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setenv("STREAMLIT_SERVER_ADDRESS", "app.example.com")
    monkeypatch.delenv("HTTP_X_FORWARDED_PROTO", raising=False)
    monkeypatch.delenv("X_FORWARDED_PROTO", raising=False)
    monkeypatch.setenv("STREAMLIT_SERVER_ENABLE_HTTPS", "false")

    with patch.object(app.st, "session_state", fake_state), \
         patch.object(app.Config, "REQUIRE_HTTPS", True), \
         patch.object(app.st, "error") as mock_error, \
         patch.object(app.st, "stop", side_effect=RuntimeError("stopped")) as mock_stop:
        with pytest.raises(RuntimeError, match="stopped"):
            app.check_https_security()

    mock_error.assert_called_once()
    mock_stop.assert_called_once()


def test_fixed_api_template_covers_full_authenticated_surface():
    template = Path("infrastructure/cloudformation/api-gateway-fixed.yaml").read_text(encoding="utf-8")

    for path_part in (
        "PathPart: chat",
        "PathPart: session",
        "PathPart: upload-image",
        "PathPart: analyze-image",
        "PathPart: generate-recipes",
        "PathPart: generate-shopping-list",
        "PathPart: reminders",
        "PathPart: dismiss",
        "PathPart: snooze",
    ):
        assert path_part in template

    assert "AlarmNotificationTopicArn" in template
    assert "ApplicationLogGroupName" in template
    assert "Type: AWS::ApiGateway::GatewayResponse" in template
    assert "Type: AWS::Logs::MetricFilter" in template
