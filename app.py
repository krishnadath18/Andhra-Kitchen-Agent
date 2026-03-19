"""
Andhra Kitchen Agent - Streamlit Frontend Application
Multilingual (English/Telugu) kitchen assistant UI.
Requirements: 15.1, 15.9, 21.1

REFACTORED: Modular architecture with separated concerns.
"""

import streamlit as st
import sys
import os
import logging

from config.env import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# ============================================================================
# SECURITY: HTTPS ENFORCEMENT
# ============================================================================

def check_https_security():
    """
    WARNING: In production this app must be served over HTTPS only.
    HTTP exposes session tokens and user data to interception.
    """
    if 'https_checked' in st.session_state:
        return

    st.session_state.https_checked = True
    is_production = os.getenv('ENVIRONMENT', Config.ENVIRONMENT) == 'prod'
    is_localhost = os.getenv('STREAMLIT_SERVER_ADDRESS', 'localhost') in ['localhost', '127.0.0.1']
    forwarded_proto = (
        os.getenv('HTTP_X_FORWARDED_PROTO')
        or os.getenv('X_FORWARDED_PROTO')
        or os.getenv('FORWARDED_PROTO')
        or ''
    ).lower()
    forwarded_ssl = (
        os.getenv('HTTP_X_FORWARDED_SSL')
        or os.getenv('X_FORWARDED_SSL')
        or ''
    ).lower()
    https_enabled = os.getenv('STREAMLIT_SERVER_ENABLE_HTTPS', 'false').lower() == 'true'
    is_https = https_enabled or forwarded_proto == 'https' or forwarded_ssl in {'on', '1', 'true'}

    if is_production and not is_localhost:
        if Config.REQUIRE_HTTPS and not is_https:
            logger.critical("SECURITY: Refusing insecure HTTP access in production")
            st.error("Secure HTTPS access is required in production. Please use the HTTPS endpoint.")
            st.stop()

        enable_xsrf = os.getenv('STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION', 'true').lower() == 'true'
        if not enable_xsrf:
            st.error("Security warning: XSRF protection is disabled.")
            logger.error("SECURITY: XSRF protection disabled in production")


check_https_security()

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Andhra Kitchen Agent",
    page_icon="🍛",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================================
# IMPORT UI MODULES
# ============================================================================

from ui.styles import get_global_styles
from ui.state import initialize_session_state
from ui.components import (
    render_login_screen,
    render_navbar,
    render_chat_tab,
    render_upload_tab,
    render_recipes_tab,
    render_shopping_tab,
    render_reminders_tab,
)

# ============================================================================
# APPLY STYLES
# ============================================================================

st.markdown(get_global_styles(), unsafe_allow_html=True)

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application entry point."""
    initialize_session_state()
    
    # Authentication gate
    if not st.session_state.is_authenticated:
        render_login_screen()
        return

    # Render navigation
    render_navbar()
    
    # Tab navigation
    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
    tabs = [
        ('chat', '💬 Chat'),
        ('upload', '📷 Scan'),
        ('recipes', '📖 Recipes'),
        ('shopping', '🛒 Shopping'),
        ('reminders', '⏰ Reminders'),
    ]
    
    cols = st.columns(len(tabs))
    for col, (key, label) in zip(cols, tabs):
        with col:
            if st.button(label, key=f"tab_{key}", use_container_width=True):
                st.session_state.active_tab = key
                st.rerun()
    
    st.markdown('<div style="height:1.5rem"></div>', unsafe_allow_html=True)

    # Reminder notification
    active_reminders = [r for r in st.session_state.reminders if r.get('status') in ('pending', 'delivered')]
    if active_reminders and st.session_state.active_tab != 'reminders':
        st.info(f"⏰ You have {len(active_reminders)} active reminder(s).")

    # Route to active tab
    tab = st.session_state.active_tab
    if tab == 'chat':
        render_chat_tab()
    elif tab == 'upload':
        render_upload_tab()
    elif tab == 'recipes':
        render_recipes_tab()
    elif tab == 'shopping':
        render_shopping_tab()
    elif tab == 'reminders':
        render_reminders_tab()


if __name__ == "__main__":
    main()
