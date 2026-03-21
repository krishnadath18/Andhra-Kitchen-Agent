"""
Authentication helpers for Cognito-backed API requests.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Optional

import jwt
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError

from config.env import Config


class AuthenticationError(Exception):
    """Raised when a request cannot be authenticated."""


@dataclass(frozen=True)
class AuthContext:
    """Authenticated user context derived from Cognito claims."""

    sub: str
    email: Optional[str]
    claims: Dict[str, Any]


def require_authenticated_user(event: Dict[str, Any]) -> AuthContext:
    """
    Resolve the authenticated user from API Gateway claims or a bearer token.
    In mock auth mode, returns a mock user context.
    """
    # Mock authentication bypass for local development
    if Config.USE_MOCK_AUTH:
        return AuthContext(
            sub="mock_user_sub_12345",
            email="mock@example.com",
            claims={
                "sub": "mock_user_sub_12345",
                "email": "mock@example.com",
                "cognito:username": "mockuser"
            }
        )
    
    claims = _extract_event_claims(event)
    if claims is None:
        token = _extract_bearer_token(event)
        claims = _validate_bearer_token(token)

    sub = claims.get("sub")
    if not sub:
        raise AuthenticationError("Authenticated token is missing the Cognito subject claim")

    return AuthContext(
        sub=sub,
        email=claims.get("email"),
        claims=claims,
    )


def _extract_event_claims(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    request_context = event.get("requestContext") or {}
    authorizer = request_context.get("authorizer") or {}

    claims = authorizer.get("claims")
    if isinstance(claims, dict) and claims.get("sub"):
        return claims

    jwt_context = authorizer.get("jwt") or {}
    claims = jwt_context.get("claims")
    if isinstance(claims, dict) and claims.get("sub"):
        return claims

    return None


def _extract_bearer_token(event: Dict[str, Any]) -> str:
    headers = event.get("headers") or {}
    authorization = None
    for key, value in headers.items():
        if key.lower() == "authorization":
            authorization = value
            break

    if not authorization:
        raise AuthenticationError("Missing Authorization header")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthenticationError("Authorization header must use Bearer token format")

    return token


def _validate_bearer_token(token: str) -> Dict[str, Any]:
    cognito_region = os.getenv("COGNITO_REGION") or Config.COGNITO_REGION
    user_pool_id = os.getenv("COGNITO_USER_POOL_ID") or Config.COGNITO_USER_POOL_ID
    app_client_id = os.getenv("COGNITO_APP_CLIENT_ID") or Config.COGNITO_APP_CLIENT_ID

    if not user_pool_id or not app_client_id:
        raise AuthenticationError(
            "Cognito is not configured for local token validation. "
            "Set COGNITO_USER_POOL_ID and COGNITO_APP_CLIENT_ID."
        )

    issuer = (
        f"https://cognito-idp.{cognito_region}.amazonaws.com/"
        f"{user_pool_id}"
    )

    try:
        signing_key = _get_jwk_client(cognito_region, user_pool_id).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=app_client_id,
            issuer=issuer,
        )
    except InvalidTokenError as exc:
        raise AuthenticationError(f"Invalid bearer token: {exc}") from exc
    except Exception as exc:  # pragma: no cover - network errors are surfaced generically
        raise AuthenticationError(f"Failed to validate bearer token: {exc}") from exc

    token_use = claims.get("token_use")
    if token_use != "id":
        raise AuthenticationError("Bearer token must be a Cognito ID token")

    return claims


@lru_cache(maxsize=4)
def _get_jwk_client(cognito_region: str, user_pool_id: str) -> PyJWKClient:
    jwks_url = (
        f"https://cognito-idp.{cognito_region}.amazonaws.com/"
        f"{user_pool_id}/.well-known/jwks.json"
    )
    return PyJWKClient(jwks_url)
