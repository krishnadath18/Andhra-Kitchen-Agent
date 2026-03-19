"""
Event Handlers and API Integration for Andhra Kitchen Agent
Handles user interactions, API calls, and data processing.
"""

import streamlit as st
from typing import Dict, Any
from datetime import datetime
import html
import logging

from config.env import Config
from ui.translations import t

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


def _escape_html(text: str) -> str:
    """
    Escape HTML special characters to prevent XSS attacks.
    
    SECURITY: All user-provided content MUST be escaped before rendering
    with unsafe_allow_html=True.
    """
    if not text:
        return ""
    return html.escape(str(text))


def display_error(error_type: str):
    """Display a localized error message."""
    st.error(f"{t('error_prefix')}{t(f'error_{error_type}')}")


def check_password_strength(password: str) -> Dict[str, Any]:
    """Return password-strength details for the login UI."""
    min_length = Config.PASSWORD_MIN_LENGTH
    requirements = {
        'min_length': len(password) >= min_length,
        'uppercase': any(char.isupper() for char in password),
        'lowercase': any(char.islower() for char in password),
        'number': any(char.isdigit() for char in password),
        'special': any(not char.isalnum() for char in password),
    }

    score = sum(requirements.values())
    if score <= 2:
        strength = 'Weak'
        color = '#8A3A3A'
    elif score == 3:
        strength = 'Fair'
        color = '#A87A1A'
    elif score == 4:
        strength = 'Good'
        color = '#3A8A3A'
    else:
        strength = 'Strong'
        color = '#2AA198'

    feedback = []
    if not requirements['min_length']:
        feedback.append(f"Use at least {min_length} characters.")
    if not requirements['uppercase']:
        feedback.append("Add an uppercase letter.")
    if not requirements['lowercase']:
        feedback.append("Add a lowercase letter.")
    if not requirements['number']:
        feedback.append("Add a number.")
    if Config.PASSWORD_REQUIRE_SPECIAL and not requirements['special']:
        feedback.append("Add a special character.")

    return {
        'requirements': requirements,
        'score': score,
        'strength': strength,
        'color': color,
        'feedback': feedback or ["Password meets the recommended complexity."],
    }


def send_message(message: str):
    """
    Send a chat message and append both sides to history.
    
    SECURITY: Input validation and sanitization.
    """
    # Input validation - prevent excessively long messages
    MAX_MESSAGE_LENGTH = 2000
    if len(message) > MAX_MESSAGE_LENGTH:
        st.error(f"Message too long. Maximum {MAX_MESSAGE_LENGTH} characters.")
        return
    
    # Sanitize message for storage (strip leading/trailing whitespace)
    message = message.strip()
    if not message:
        return
    
    st.session_state.conversation_history.append({
        'role': 'user', 'content': message,
        'timestamp': datetime.now().strftime('%H:%M'),
    })
    if api_client and st.session_state.session_id:
        try:
            resp = api_client.send_chat_message(
                session_id=st.session_state.session_id,
                message=message,
                language=st.session_state.language,
            )
            st.session_state.conversation_history.append({
                'role': 'assistant',
                'content': resp.get('response', 'No response'),
                'timestamp': datetime.now().strftime('%H:%M'),
            })
        except APIError:
            display_error('api')
        except NetworkError:
            display_error('network')
    else:
        st.session_state.conversation_history.append({
            'role': 'assistant',
            'content': 'Backend not connected. Configure API_BASE_URL.',
            'timestamp': datetime.now().strftime('%H:%M'),
        })
