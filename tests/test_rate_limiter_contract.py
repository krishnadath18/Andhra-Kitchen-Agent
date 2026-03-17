from unittest.mock import MagicMock, patch

from src.api_handler import enforce_rate_limit, handle_chat
from src.rate_limiter import RateLimiter


def test_rate_limiter_returns_structured_result_when_table_missing(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    limiter = RateLimiter("missing-table")
    limiter.table = None

    result = limiter.check_rate_limit("sess_123", "/chat")

    assert result.allowed is True
    assert result.requests_limit == 50
    assert hasattr(result, "remaining")
    assert hasattr(result, "reset_time")


@patch("src.api_handler.check_rate_limit")
@patch("src.api_handler.agentcore_orchestrator")
@patch("src.api_handler.kitchen_agent")
def test_handle_chat_checks_rate_limit_once(mock_kitchen_agent, mock_orchestrator, mock_check_rate_limit):
    mock_check_rate_limit.return_value = RateLimiter.RateLimitResult(
        allowed=True,
        retry_after_seconds=None,
        requests_limit=50,
        remaining=49,
        reset_time="2026-03-16T10:00:00Z",
    )
    mock_kitchen_agent.get_session.return_value = {"session_id": "sess_test123"}
    mock_kitchen_agent.update_session_data.return_value = True
    mock_orchestrator.invoke_agent.return_value = {
        "final_response": "hi",
        "workflow_id": "wf_123",
        "status": "completed",
        "execution_time_ms": 10,
        "subtask_results": {},
    }

    response = handle_chat(
        {
            "httpMethod": "POST",
            "path": "/chat",
            "headers": {"Content-Type": "application/json"},
            "body": '{"session_id":"sess_test123","message":"hello","language":"en"}',
        }
    )

    assert response["statusCode"] == 200
    mock_check_rate_limit.assert_called_once_with("sess_test123", "/chat")


@patch("src.api_handler.check_rate_limit")
def test_enforce_rate_limit_returns_consistent_headers(mock_check_rate_limit):
    mock_check_rate_limit.return_value = RateLimiter.RateLimitResult(
        allowed=False,
        retry_after_seconds=42,
        requests_limit=50,
        remaining=0,
        reset_time="2026-03-16T10:00:00Z",
    )

    response = enforce_rate_limit("sess_123", "/chat")

    assert response["statusCode"] == 429
    assert response["headers"]["Retry-After"] == "42"
    assert response["headers"]["X-RateLimit-Limit"] == "50"
    assert response["headers"]["X-RateLimit-Remaining"] == "0"
    assert response["headers"]["X-RateLimit-Reset"] == "2026-03-16T10:00:00Z"


def test_rate_limiter_fails_closed_in_prod(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "prod")
    limiter = RateLimiter("prod-table")
    limiter.table = MagicMock()
    limiter.table.get_item.side_effect = RuntimeError("boom")

    result = limiter.check_rate_limit("sess_123", "/chat")

    assert result.allowed is False
    assert result.retry_after_seconds == 60
    assert result.http_status == 503


@patch("src.api_handler.rate_limiter")
def test_create_response_adds_rate_limit_headers_on_success(mock_rate_limiter):
    from src.api_handler import create_response

    mock_rate_limiter.get_rate_limit_info.return_value = {
        "enabled": True,
        "limit": 50,
        "remaining": 49,
        "resets_in_seconds": 120,
    }

    response = create_response(
        status_code=200,
        body={"ok": True},
        rate_limit_session_id="sess_123",
        rate_limit_endpoint="/chat",
    )

    assert response["headers"]["X-RateLimit-Limit"] == "50"
    assert response["headers"]["X-RateLimit-Remaining"] == "49"
    assert "X-RateLimit-Reset" in response["headers"]
