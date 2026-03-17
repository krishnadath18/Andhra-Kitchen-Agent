"""
Unit tests for the current Streamlit app structure.

These tests validate the auth-gated UI introduced with Cognito-backed sessions.
"""

import os
import sys
from unittest.mock import patch

import pytest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class FakeSessionState(dict):
    """Minimal session_state stand-in supporting dict and attribute access."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


def test_app_imports_successfully():
    """Test that app.py can be imported without errors."""
    try:
        import app  # noqa: F401
    except ImportError as exc:
        pytest.fail(f"Failed to import app.py: {exc}")


def test_ui_text_structure():
    """Test that UI_TEXT contains the required keys for both languages."""
    import app

    required_keys = [
        'title',
        'subtitle',
        'language_label',
        'chat_placeholder',
        'send_button',
        'voice_button',
        'upload_button',
        'welcome_message',
        'loading',
        'error_prefix',
    ]

    assert 'en' in app.UI_TEXT
    assert 'te' in app.UI_TEXT

    for lang in ['en', 'te']:
        for key in required_keys:
            assert key in app.UI_TEXT[lang], f"Missing key '{key}' in language '{lang}'"


def test_session_state_initialization_defaults():
    """Test that initialize_session_state populates the current auth-aware defaults."""
    import app

    fake_state = FakeSessionState()
    with patch.object(app.st, 'session_state', fake_state), \
         patch.object(app, 'api_client', None):
        app.initialize_session_state()

    required_keys = [
        'conversation_history',
        'session_id',
        'language',
        'selected_recipe',
        'shopping_list',
        'is_authenticated',
        'id_token',
        'access_token',
        'refresh_token',
        'token_expires_at',
        'user_sub',
        'user_email',
        'auth_error',
    ]

    for key in required_keys:
        assert key in fake_state, f"Missing session state key: {key}"


def test_translation_helper_uses_current_language():
    """Test that the translation helper returns the correct string for each language."""
    import app

    with patch.object(app.st, 'session_state', {'language': 'en'}):
        assert app.t('title') == app.UI_TEXT['en']['title']

    with patch.object(app.st, 'session_state', {'language': 'te'}):
        assert app.t('title') == app.UI_TEXT['te']['title']


def test_page_title_matches_current_config():
    """Test that page config uses the current single-language title."""
    with open('app.py', 'r', encoding='utf-8') as file:
        content = file.read()

    assert 'page_title="Andhra Kitchen Agent"' in content


def test_css_includes_mobile_and_font_rules():
    """Test that the current design system includes mobile styling and Telugu font support."""
    with open('app.py', 'r', encoding='utf-8') as file:
        content = file.read()

    assert "@media (max-width: 768px)" in content
    assert "Noto Sans Telugu" in content
    assert "Plus Jakarta Sans" in content


def test_current_render_functions_exist():
    """Test that the app exposes the current top-level render functions."""
    import app

    required_functions = [
        'render_login_screen',
        'render_navbar',
        'render_tabs',
        'render_chat_tab',
        'render_upload_tab',
        'render_recipes_tab',
        'render_shopping_tab',
        'render_reminders_tab',
        'main',
    ]

    for func_name in required_functions:
        assert hasattr(app, func_name), f"Missing function: {func_name}"
        assert callable(getattr(app, func_name)), f"'{func_name}' is not callable"


def test_auth_helpers_exist():
    """Test that the Cognito/session helper functions exist."""
    import app

    # SECURITY FIX: decode_token_claims was removed as it was insecure
    # (disabled signature verification). Token validation now happens server-side only.
    required_functions = [
        'set_auth_state',
        'clear_auth_state',
        'refresh_auth_tokens',
        'get_current_bearer_token',
    ]

    for func_name in required_functions:
        assert hasattr(app, func_name), f"Missing function: {func_name}"
        assert callable(getattr(app, func_name)), f"'{func_name}' is not callable"
    
    # Verify the insecure function is NOT present
    assert not hasattr(app, 'decode_token_claims'), \
        "decode_token_claims should be removed (was insecure - disabled signature verification)"

