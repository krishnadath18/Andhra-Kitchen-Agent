"""
Simple Cognito authentication client for the Streamlit frontend.
Supports mock authentication for local development.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import boto3

from config.env import Config


class AuthClientError(Exception):
    """Raised when Cognito authentication fails."""


class MockAuthClient:
    """Mock authentication client for local development."""
    
    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """Mock sign-in that accepts any credentials."""
        # Accept any email/password for local testing
        token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        return {
            'id_token': 'mock_id_token_' + email,
            'access_token': 'mock_access_token_' + email,
            'refresh_token': 'mock_refresh_token_' + email,
            'token_expires_at': token_expires_at.isoformat(),
        }
    
    def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        """Mock token refresh."""
        token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        return {
            'id_token': 'mock_id_token_refreshed',
            'access_token': 'mock_access_token_refreshed',
            'refresh_token': refresh_token,
            'token_expires_at': token_expires_at.isoformat(),
        }
    
    def logout(self, access_token: str) -> None:
        """Mock logout (no-op)."""
        pass


class AuthClient:
    """Authenticate first-party users against Cognito User Pools."""

    def __init__(self):
        self.client = boto3.client('cognito-idp', region_name=Config.COGNITO_REGION)

    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate with USER_PASSWORD_AUTH and return token payload."""
        try:
            response = self.client.initiate_auth(
                ClientId=Config.COGNITO_APP_CLIENT_ID,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': email,
                    'PASSWORD': password,
                }
            )
        except Exception as exc:
            raise AuthClientError(f"Sign-in failed: {exc}") from exc

        return self._normalize_auth_result(response)

    def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh Cognito tokens using a refresh token."""
        try:
            response = self.client.initiate_auth(
                ClientId=Config.COGNITO_APP_CLIENT_ID,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={
                    'REFRESH_TOKEN': refresh_token,
                }
            )
        except Exception as exc:
            raise AuthClientError(f"Token refresh failed: {exc}") from exc

        return self._normalize_auth_result(response, existing_refresh_token=refresh_token)

    def logout(self, access_token: str) -> None:
        """Invalidate the current Cognito session."""
        try:
            self.client.global_sign_out(AccessToken=access_token)
        except Exception as exc:
            raise AuthClientError(f"Logout failed: {exc}") from exc

    @staticmethod
    def _normalize_auth_result(
        response: Dict[str, Any],
        existing_refresh_token: Optional[str] = None
    ) -> Dict[str, Any]:
        auth_result = response.get('AuthenticationResult') or {}
        expires_in = int(auth_result.get('ExpiresIn', 3600))
        token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        return {
            'id_token': auth_result.get('IdToken'),
            'access_token': auth_result.get('AccessToken'),
            'refresh_token': auth_result.get('RefreshToken') or existing_refresh_token,
            'token_expires_at': token_expires_at.isoformat(),
        }


# Use mock auth client if configured, otherwise use real Cognito
if Config.USE_MOCK_AUTH:
    auth_client = MockAuthClient()
else:
    auth_client = AuthClient()
