"""
Simple Cognito authentication client for the Streamlit frontend.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import boto3

from config.env import Config


class AuthClientError(Exception):
    """Raised when Cognito authentication fails."""


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


auth_client = AuthClient()
