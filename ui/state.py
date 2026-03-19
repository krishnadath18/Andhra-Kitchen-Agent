"""
Session State Management for Andhra Kitchen Agent
Handles authentication state, session initialization, and token management.
"""

import streamlit as st
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

# Import clients (with fallback for development)
try:
    from src.api_client import api_client, APIError, NetworkError
    from src.auth_client import auth_client, AuthClientError
except ImportError:
    api_client = None
    APIError = Exception
    NetworkError = Exception
    auth_client = None
    AuthClientError = Exception


def initialize_session_state():
    """Initialize all session state variables with defaults."""
    defaults = {
        'conversation_history': [],
        'session_id': None,
        'language': 'en',
        'selected_recipe': None,
        'shopping_list': None,
        'is_recording': False,
        'voice_transcript': '',
        'uploaded_image': None,
        'detected_ingredients': None,
        'recipes': None,
        'reminders': [],
        'purchased_items': set(),
        'active_tab': 'chat',
        'show_upload': False,
        'is_authenticated': False,
        'id_token': None,
        'access_token': None,
        'refresh_token': None,
        'token_expires_at': None,
        'user_sub': None,
        'user_email': None,
        'auth_error': None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if api_client:
        api_client.set_token_provider(get_current_bearer_token)

    if st.session_state.is_authenticated and st.session_state.session_id is None and api_client:
        try:
            r = api_client.create_session(language='en')
            st.session_state.session_id = r.get('session_id')
        except (APIError, NetworkError) as e:
            logger.error(f"Failed to create session: {e}")


def set_auth_state(auth_result: Dict[str, Any]):
    """
    Persist Cognito tokens in Streamlit state.
    
    WARNING: Tokens are stored in session state (memory only).
    Never log tokens or expose them in error messages.
    """
    st.session_state.id_token = auth_result.get('id_token')
    st.session_state.access_token = auth_result.get('access_token')
    st.session_state.refresh_token = auth_result.get('refresh_token')
    st.session_state.token_expires_at = auth_result.get('token_expires_at')
    st.session_state.is_authenticated = True
    st.session_state.session_id = None
    st.session_state.auth_error = None
    # Note: User claims (sub, email) will be retrieved from backend API
    # after token validation, not decoded client-side


def clear_auth_state():
    """Clear current Cognito and backend session state."""
    st.session_state.is_authenticated = False
    st.session_state.id_token = None
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.token_expires_at = None
    st.session_state.user_sub = None
    st.session_state.user_email = None
    st.session_state.session_id = None
    st.session_state.conversation_history = []
    st.session_state.detected_ingredients = None
    st.session_state.recipes = None
    st.session_state.shopping_list = None
    st.session_state.reminders = []


def refresh_auth_tokens():
    """Refresh Cognito tokens when the current ID token is nearing expiry."""
    refresh_token = st.session_state.get('refresh_token')
    if not refresh_token or not auth_client:
        return
    auth_result = auth_client.refresh_tokens(refresh_token)
    set_auth_state(auth_result)


def get_current_bearer_token() -> Optional[str]:
    """Return a valid bearer token, refreshing it if needed."""
    if not st.session_state.get('is_authenticated'):
        return None

    expires_at = st.session_state.get('token_expires_at')
    if expires_at:
        expiry_dt = datetime.fromisoformat(expires_at)
        if expiry_dt.tzinfo is None:
            expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) + timedelta(minutes=5) >= expiry_dt:
            try:
                refresh_auth_tokens()
            except AuthClientError as exc:
                logger.error(f"Token refresh failed: {exc}")
                clear_auth_state()
                return None

    return st.session_state.get('id_token')
