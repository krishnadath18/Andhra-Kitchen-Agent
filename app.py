"""
Andhra Kitchen Agent - Streamlit Frontend Application
Multilingual (English/Telugu) kitchen assistant UI.
Requirements: 15.1, 15.9, 21.1
"""

import streamlit as st
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import sys
import os
import logging
import html

from config.env import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.api_client import api_client, APIError, NetworkError
    from src.auth_client import auth_client, AuthClientError
except ImportError:
    api_client = None
    APIError = Exception
    NetworkError = Exception
    auth_client = None
    AuthClientError = Exception

# ============================================================================
# SECURITY: HTTPS ENFORCEMENT
# ============================================================================

def check_https_security():
    """
    WARNING: In production this app must be served over HTTPS only.
    HTTP exposes session tokens and user data to interception.
    """
    if 'https_checked' not in st.session_state:
        st.session_state.https_checked = True
        is_production = os.getenv('ENVIRONMENT', 'dev') == 'prod'
        is_localhost = os.getenv('STREAMLIT_SERVER_ADDRESS', 'localhost') in ['localhost', '127.0.0.1']
        if is_production and not is_localhost:
            enable_xsrf = os.getenv('STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION', 'true').lower() == 'true'
            if not enable_xsrf:
                # WARNING: XSRF protection disabled — re-enable via STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true
                st.error("⚠️ SECURITY WARNING: XSRF protection is disabled.")
                logger.error("SECURITY: XSRF protection disabled in production")
            st.warning("🔒 Ensure you are accessing this app via HTTPS.")
            logger.warning("SECURITY: Production app should use HTTPS")

def _secure_check_https_security():
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


check_https_security = _secure_check_https_security
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
# DESIGN SYSTEM & CSS
# ============================================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Telugu:wght@400;600&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

/* ── Reset & base ── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', 'Noto Sans Telugu', sans-serif;
    background: #0C0B09;
    color: #EDE8DF;
}
.main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
}
/* hide default streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stSidebar"] { display: none; }

/* ── Top navbar ── */
.navbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 2rem;
    height: 60px;
    background: #111009;
    border-bottom: 1px solid #2A2015;
    position: sticky;
    top: 0;
    z-index: 100;
}
.navbar-brand {
    display: flex;
    align-items: center;
    gap: 0.6rem;
}
.navbar-brand .brand-icon { font-size: 1.6rem; }
.navbar-brand .brand-name {
    font-size: 1.1rem;
    font-weight: 700;
    color: #F0C040;
    letter-spacing: -0.3px;
}
.navbar-brand .brand-sub {
    font-size: 0.72rem;
    color: #7A6535;
    margin-left: 0.3rem;
    font-weight: 400;
}
.navbar-status {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.75rem;
    color: #5A4A28;
}
.status-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #3A8A3A;
    box-shadow: 0 0 6px #3A8A3A;
}

/* ── Tab navigation ── */
.tab-nav {
    display: flex;
    gap: 0;
    background: #111009;
    border-bottom: 1px solid #2A2015;
    padding: 0 2rem;
    overflow-x: auto;
}
.tab-nav::-webkit-scrollbar { display: none; }
.tab-btn {
    padding: 0.75rem 1.4rem;
    font-size: 0.85rem;
    font-weight: 500;
    color: #6A5830;
    border: none;
    background: transparent;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    white-space: nowrap;
    transition: color 0.15s, border-color 0.15s;
    font-family: inherit;
}
.tab-btn:hover { color: #C4956A; }
.tab-btn.active {
    color: #F0C040;
    border-bottom-color: #F0C040;
}

/* ── Page wrapper ── */
.page-content {
    padding: 1.5rem 2rem 4rem 2rem;
    max-width: 1000px;
    margin: 0 auto;
}

/* ── Chat layout ── */
.chat-area {
    display: flex;
    flex-direction: column;
    gap: 0;
}
.chat-messages {
    min-height: 420px;
    max-height: 520px;
    overflow-y: auto;
    padding: 1.25rem;
    background: #0F0D0A;
    border: 1px solid #1E1A10;
    border-radius: 16px 16px 0 0;
    scroll-behavior: smooth;
}
.chat-messages::-webkit-scrollbar { width: 4px; }
.chat-messages::-webkit-scrollbar-thumb { background: #2A2015; border-radius: 2px; }

/* ── Message bubbles ── */
.msg-row {
    display: flex;
    margin-bottom: 1rem;
    gap: 0.6rem;
    animation: popIn 0.2s ease;
}
@keyframes popIn {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}
.msg-row.user { flex-direction: row-reverse; }
.msg-avatar-circle {
    width: 32px; height: 32px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.9rem;
    flex-shrink: 0;
    margin-top: 2px;
}
.msg-row.user .msg-avatar-circle { background: #1A2E45; }
.msg-row.assistant .msg-avatar-circle { background: #2A1A08; }
.msg-bubble {
    max-width: 72%;
    padding: 0.7rem 1rem;
    border-radius: 14px;
    font-size: 0.92rem;
    line-height: 1.6;
}
.msg-row.user .msg-bubble {
    background: #1A2840;
    border: 1px solid #1E3A5F;
    border-top-right-radius: 4px;
    color: #C8DCF0;
}
.msg-row.assistant .msg-bubble {
    background: #1E1508;
    border: 1px solid #3A2510;
    border-top-left-radius: 4px;
    color: #EDE0C8;
}
.msg-time {
    font-size: 0.65rem;
    color: #3A3020;
    margin-top: 0.25rem;
    text-align: right;
}
.msg-row.assistant .msg-time { text-align: left; }

/* ── Welcome state ── */
.welcome-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    min-height: 380px;
    text-align: center;
    gap: 0.75rem;
}
.welcome-state .w-icon { font-size: 3.5rem; }
.welcome-state h2 {
    font-size: 1.3rem;
    font-weight: 600;
    color: #F0C040;
    margin: 0;
}
.welcome-state p { color: #7A6535; font-size: 0.88rem; max-width: 380px; line-height: 1.6; margin: 0; }
.quick-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    justify-content: center;
    margin-top: 0.5rem;
}
.chip {
    background: #1A1508;
    border: 1px solid #3A2510;
    color: #C4956A;
    border-radius: 20px;
    padding: 0.35rem 0.85rem;
    font-size: 0.78rem;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
}
.chip:hover { background: #2A1E0A; border-color: #E8890C; color: #F0C040; }

/* ── Chat input bar ── */
.chat-input-bar {
    background: #141208;
    border: 1px solid #2A2015;
    border-top: none;
    border-radius: 0 0 16px 16px;
    padding: 0.75rem 1rem;
    display: flex;
    gap: 0.5rem;
    align-items: center;
}

/* ── Streamlit input overrides ── */
.stTextInput > div > div > input {
    background: #0F0D0A !important;
    border: 1px solid #2A2015 !important;
    border-radius: 10px !important;
    color: #EDE8DF !important;
    font-size: 0.92rem !important;
    padding: 0.6rem 1rem !important;
    font-family: inherit !important;
}
.stTextInput > div > div > input:focus {
    border-color: #E8890C !important;
    box-shadow: 0 0 0 2px rgba(232,137,12,0.15) !important;
}
.stTextInput > div > div > input::placeholder { color: #3A3020 !important; }

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #E8890C, #C96E08) !important;
    color: #0C0B09 !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 0.55rem 1.1rem !important;
    font-family: inherit !important;
    transition: opacity 0.15s, transform 0.15s !important;
    box-shadow: 0 2px 8px rgba(232,137,12,0.2) !important;
}
.stButton > button:hover {
    opacity: 0.9 !important;
    transform: translateY(-1px) !important;
}
/* ghost variant — secondary buttons */
button[data-ghost="true"],
.stButton > button.ghost {
    background: transparent !important;
    border: 1px solid #2A2015 !important;
    color: #7A6535 !important;
    box-shadow: none !important;
}

/* ── Form submit button ── */
[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #E8890C, #C96E08) !important;
    color: #0C0B09 !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    padding: 0.6rem 1.4rem !important;
    font-family: inherit !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
    background: #141208 !important;
    border: 1px solid #2A2015 !important;
    border-radius: 10px !important;
    color: #EDE8DF !important;
    font-family: inherit !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: #141208 !important;
    border: 1px solid #1E1A10 !important;
    border-radius: 12px !important;
    padding: 0.8rem 1rem !important;
}
[data-testid="stMetricLabel"] { color: #5A4A28 !important; font-size: 0.72rem !important; text-transform: uppercase; letter-spacing: 0.5px; }
[data-testid="stMetricValue"] { color: #F0C040 !important; font-size: 1.25rem !important; font-weight: 600 !important; }

/* ── Cards ── */
.card {
    background: #141208;
    border: 1px solid #1E1A10;
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s;
}
.card:hover { border-color: #3A2510; }
.card.selected { border-color: #F0C040; box-shadow: 0 0 0 1px rgba(240,192,64,0.15); }
.card-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #EDE8DF;
    margin: 0 0 0.3rem 0;
}
.card-meta {
    font-size: 0.78rem;
    color: #5A4A28;
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    margin-bottom: 0.75rem;
}
.card-meta span { display: flex; align-items: center; gap: 0.3rem; }
.tag {
    display: inline-block;
    background: #1E1508;
    border: 1px solid #3A2510;
    color: #C4956A;
    border-radius: 20px;
    padding: 0.18rem 0.65rem;
    font-size: 0.72rem;
    font-weight: 500;
    margin: 0.15rem 0.2rem 0.15rem 0;
}

/* ── Section title ── */
.section-title {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #5A4A28;
    margin: 1.5rem 0 0.75rem 0;
}
.page-title {
    font-size: 1.4rem;
    font-weight: 700;
    color: #F0C040;
    margin: 0 0 0.25rem 0;
}
.page-subtitle { font-size: 0.85rem; color: #5A4A28; margin: 0 0 1.5rem 0; }

/* ── Ingredient row ── */
.ing-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.6rem 0;
    border-bottom: 1px solid #1A1508;
}
.ing-name { font-size: 0.9rem; color: #EDE8DF; font-weight: 500; }
.ing-qty { font-size: 0.82rem; color: #7A6535; }
.conf-badge {
    font-size: 0.68rem;
    padding: 0.15rem 0.5rem;
    border-radius: 10px;
    font-weight: 600;
}
.conf-high { background: #0D2010; color: #4CAF50; border: 1px solid #1A4020; }
.conf-med  { background: #201808; color: #E8890C; border: 1px solid #3A2510; }
.conf-low  { background: #200808; color: #E84040; border: 1px solid #3A1010; }

/* ── Shopping row ── */
.shop-row {
    display: flex;
    align-items: center;
    padding: 0.55rem 0;
    border-bottom: 1px solid #1A1508;
    gap: 0.75rem;
}
.shop-name { flex: 1; font-size: 0.88rem; color: #EDE8DF; }
.shop-name.done { text-decoration: line-through; color: #3A3020; }
.shop-qty { font-size: 0.8rem; color: #5A4A28; min-width: 70px; }
.shop-price { font-size: 0.85rem; color: #F0C040; font-weight: 500; min-width: 60px; text-align: right; }

/* ── Reminder card ── */
.reminder-item {
    background: #141208;
    border: 1px solid #2A2015;
    border-left: 3px solid #F0C040;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
}
.reminder-text { font-size: 0.92rem; color: #EDE8DF; }
.reminder-reason { font-size: 0.78rem; color: #5A4A28; margin-top: 0.3rem; }

/* ── Upload zone ── */
[data-testid="stFileUploader"] {
    background: #0F0D0A !important;
    border: 2px dashed #2A2015 !important;
    border-radius: 14px !important;
}
[data-testid="stFileUploader"]:hover { border-color: #E8890C !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #141208 !important;
    border: 1px solid #1E1A10 !important;
    border-radius: 12px !important;
}

/* ── Spinner ── */
.stSpinner > div { border-top-color: #E8890C !important; }

/* ── Divider ── */
hr { border: none !important; border-top: 1px solid #1E1A10 !important; margin: 1rem 0 !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #0C0B09; }
::-webkit-scrollbar-thumb { background: #2A2015; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #E8890C; }

/* ── Mobile ── */
@media (max-width: 768px) {
    .page-content { padding: 1rem 1rem 4rem 1rem; }
    .navbar { padding: 0 1rem; }
    .tab-nav { padding: 0 1rem; }
    .msg-bubble { max-width: 88%; }
    .chat-messages { min-height: 320px; max-height: 400px; }
}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE
# ============================================================================

def initialize_session_state():
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


# WARNING: Never decode JWT tokens client-side without signature verification.
# Token validation MUST happen server-side. The backend API validates tokens
# using JWKS in src/auth_utils.py. Client-side token decoding is removed to
# prevent security vulnerabilities.
# 
# REMOVED INSECURE FUNCTION:
# def decode_token_claims(id_token: str) -> Dict[str, Any]:
#     return jwt.decode(id_token, options={"verify_signature": False})
#
# This was a critical vulnerability allowing token forgery.


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

# ============================================================================
# TRANSLATIONS
# ============================================================================

UI_TEXT = {
    'en': {
        'title': 'Andhra Kitchen Agent', 'subtitle': 'Your AI-powered kitchen assistant',
        'language_label': 'Language',
        'chat_placeholder': 'Ask about recipes, ingredients, shopping…',
        'send_button': 'Send', 'voice_button': '🎤 Voice', 'upload_button': '📷 Photo',
        'welcome_message': 'Namaste! Ask me anything about Andhra cuisine.',
        'loading': 'Thinking…',
        'error_prefix': 'Error: ', 'retry_button': 'Retry',
        'error_network': 'Network error. Check your connection.',
        'error_api': 'Service unavailable. Try again shortly.',
        'error_upload': 'Upload failed. Please retry.',
        'error_analysis': 'Image analysis failed. Ensure image is clear.',
        'error_recipe': 'Recipe generation failed. Please retry.',
        'error_shopping': 'Shopping list generation failed. Please retry.',
        'voice_listening': 'Listening…', 'voice_stop': '⏹ Stop',
        'voice_permission_denied': 'Microphone access denied.',
        'voice_not_supported': 'Voice not supported in this browser.',
        'upload_image_title': 'Upload Kitchen Photo',
        'upload_formats': 'JPEG, PNG, HEIC · Max 10 MB',
        'upload_success': 'Image uploaded!', 'upload_analyzing': 'Analysing…',
        'ingredients_detected': 'Detected Ingredients',
        'confidence_high': 'High', 'confidence_medium': 'Medium', 'confidence_low': 'Low',
        'confirm_ingredient': 'Confirm', 'remove_ingredient': 'Remove',
        'recipe_title': 'Recipes', 'recipe_prep_time': 'Prep', 'recipe_servings': 'Serves',
        'recipe_cost': 'Cost/serving', 'recipe_ingredients': 'Ingredients',
        'recipe_steps': 'Steps', 'recipe_nutrition': 'Nutrition',
        'recipe_calories': 'Cal', 'recipe_protein': 'Protein',
        'recipe_carbs': 'Carbs', 'recipe_fat': 'Fat', 'recipe_fiber': 'Fiber',
        'recipe_select': 'Select', 'recipe_selected': '✓ Selected',
        'generate_shopping_list': 'Generate Shopping List',
        'shopping_list_title': 'Shopping List', 'shopping_total': 'Total',
        'reminder_title': 'Reminders', 'reminder_dismiss': 'Dismiss',
        'reminder_snooze': 'Snooze', 'reminder_snooze_1h': '1 hr',
        'reminder_snooze_3h': '3 hrs', 'reminder_snooze_24h': '24 hrs',
    },
    'te': {
        'title': 'అంధ్ర వంటగది సహాయకుడు', 'subtitle': 'మీ AI-ఆధారిత వంటగది సహాయకుడు',
        'language_label': 'భాష',
        'chat_placeholder': 'వంటకాలు, పదార్థాల గురించి అడగండి…',
        'send_button': 'పంపండి', 'voice_button': '🎤 వాయిస్', 'upload_button': '📷 ఫోటో',
        'welcome_message': 'నమస్కారం! ఆంధ్ర వంటకాల గురించి అడగండి.',
        'loading': 'ఆలోచిస్తోంది…',
        'error_prefix': 'లోపం: ', 'retry_button': 'మళ్లీ ప్రయత్నించండి',
        'error_network': 'నెట్‌వర్క్ లోపం.', 'error_api': 'సేవ అందుబాటులో లేదు.',
        'error_upload': 'అప్‌లోడ్ విఫలమైంది.', 'error_analysis': 'విశ్లేషణ విఫలమైంది.',
        'error_recipe': 'వంటకాలు రూపొందించడం విఫలమైంది.',
        'error_shopping': 'షాపింగ్ జాబితా విఫలమైంది.',
        'voice_listening': 'వింటోంది…', 'voice_stop': '⏹ ఆపండి',
        'voice_permission_denied': 'మైక్రోఫోన్ అనుమతి తిరస్కరించబడింది.',
        'voice_not_supported': 'వాయిస్ మద్దతు లేదు.',
        'upload_image_title': 'వంటగది ఫోటో అప్‌లోడ్ చేయండి',
        'upload_formats': 'JPEG, PNG, HEIC · గరిష్టంగా 10 MB',
        'upload_success': 'చిత్రం అప్‌లోడ్ అయింది!', 'upload_analyzing': 'విశ్లేషిస్తోంది…',
        'ingredients_detected': 'గుర్తించబడిన పదార్థాలు',
        'confidence_high': 'అధికం', 'confidence_medium': 'మధ్యస్థం', 'confidence_low': 'తక్కువ',
        'confirm_ingredient': 'నిర్ధారించండి', 'remove_ingredient': 'తొలగించండి',
        'recipe_title': 'వంటకాలు', 'recipe_prep_time': 'సమయం', 'recipe_servings': 'సర్వింగ్‌లు',
        'recipe_cost': 'ఖర్చు', 'recipe_ingredients': 'పదార్థాలు',
        'recipe_steps': 'దశలు', 'recipe_nutrition': 'పోషకాలు',
        'recipe_calories': 'కేలరీలు', 'recipe_protein': 'ప్రోటీన్',
        'recipe_carbs': 'కార్బ్స్', 'recipe_fat': 'కొవ్వు', 'recipe_fiber': 'ఫైబర్',
        'recipe_select': 'ఎంచుకోండి', 'recipe_selected': '✓ ఎంచుకోబడింది',
        'generate_shopping_list': 'షాపింగ్ జాబితా రూపొందించండి',
        'shopping_list_title': 'షాపింగ్ జాబితా', 'shopping_total': 'మొత్తం',
        'reminder_title': 'రిమైండర్లు', 'reminder_dismiss': 'తీసివేయండి',
        'reminder_snooze': 'స్నూజ్', 'reminder_snooze_1h': '1 గంట',
        'reminder_snooze_3h': '3 గంటలు', 'reminder_snooze_24h': '24 గంటలు',
    }
}

def t(key: str) -> str:
    return UI_TEXT[st.session_state.get('language', 'en')].get(key, key)

# ============================================================================
# SHARED HELPERS
# ============================================================================

def display_error(error_type: str):
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


def render_login_screen():
    """Render the Cognito sign-in form."""
    st.markdown(
        """
        <div style="max-width:420px;margin:6rem auto 0 auto;padding:2rem;background:#141208;border:1px solid #2A2015;border-radius:16px;">
            <div style="font-size:2rem;margin-bottom:0.75rem;">🔐</div>
            <div style="font-size:1.4rem;font-weight:700;color:#F0C040;margin-bottom:0.35rem;">Sign In</div>
            <div style="font-size:0.9rem;color:#7A6535;margin-bottom:1.5rem;">Authenticate with Cognito to access your kitchen session.</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if Config.SHOW_PASSWORD_STRENGTH:
            password_strength = check_password_strength(password)
            st.markdown(
                f"<div style='font-size:0.85rem;color:{password_strength['color']};"
                f"margin:0.35rem 0;'>Password strength: {password_strength['strength']}</div>",
                unsafe_allow_html=True
            )
            progress = min(password_strength['score'] / 5, 1.0)
            st.progress(progress)
            requirements = password_strength['requirements']
            requirement_lines = [
                f"{'✓' if requirements['min_length'] else '✗'} At least {Config.PASSWORD_MIN_LENGTH} characters",
                f"{'✓' if requirements['uppercase'] else '✗'} One uppercase letter",
                f"{'✓' if requirements['lowercase'] else '✗'} One lowercase letter",
                f"{'✓' if requirements['number'] else '✗'} One number",
            ]
            if Config.PASSWORD_REQUIRE_SPECIAL:
                requirement_lines.append(
                    f"{'✓' if requirements['special'] else '✗'} One special character"
                )
            for line in requirement_lines:
                st.caption(line)
            for feedback_line in password_strength['feedback']:
                st.caption(feedback_line)
        submitted = st.form_submit_button("Sign In", use_container_width=True)

    if st.session_state.get('auth_error'):
        st.error(st.session_state.auth_error)

    if submitted:
        if not email or not password:
            st.session_state.auth_error = "Email and password are required."
            st.rerun()

        try:
            auth_result = auth_client.sign_in(email=email, password=password)
            set_auth_state(auth_result)
            st.rerun()
        except AuthClientError as exc:
            logger.error(f"Authentication failed: {exc}")
            st.session_state.auth_error = str(exc)
            st.rerun()

def _send_message(message: str):
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


def _escape_html(text: str) -> str:
    """
    Escape HTML special characters to prevent XSS attacks.
    
    SECURITY: All user-provided content MUST be escaped before rendering
    with unsafe_allow_html=True.
    """
    if not text:
        return ""
    return html.escape(str(text))

# ============================================================================
# NAVBAR
# ============================================================================

def render_navbar():
    connected = st.session_state.is_authenticated and st.session_state.session_id is not None
    dot = '<span class="status-dot"></span>' if connected else '<span class="status-dot" style="background:#8A3A3A;box-shadow:0 0 6px #8A3A3A;"></span>'
    status_text = st.session_state.user_email if connected and st.session_state.user_email else ("Connected" if connected else "Offline")
    
    # SECURITY: Escape status text to prevent XSS (user_email comes from session state)
    status_text_safe = _escape_html(status_text)

    lang_options = {'🇬🇧 EN': 'en', '🇮🇳 TE': 'te'}
    col_brand, col_lang, col_status, col_logout = st.columns([4, 1, 1, 1])
    with col_brand:
        st.markdown(f"""
        <div class="navbar">
            <div class="navbar-brand">
                <span class="brand-icon">🍛</span>
                <span class="brand-name">{t('title')}</span>
                <span class="brand-sub">అంధ్ర వంటగది</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_lang:
        sel = st.selectbox(
            "lang", list(lang_options.keys()),
            index=list(lang_options.values()).index(st.session_state.language),
            label_visibility='collapsed', key='lang_sel'
        )
        new_lang = lang_options[sel]
        if new_lang != st.session_state.language:
            st.session_state.language = new_lang
            st.rerun()
    with col_status:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:0.4rem;height:38px;font-size:0.75rem;color:#5A4A28;">
            {dot} {status_text_safe}
        </div>
        """, unsafe_allow_html=True)
    with col_logout:
        if st.session_state.is_authenticated:
            if st.button("Logout", use_container_width=True, key='logout_btn'):
                try:
                    if auth_client and st.session_state.get('access_token'):
                        auth_client.logout(st.session_state.access_token)
                except AuthClientError as exc:
                    logger.error(f"Logout failed: {exc}")
                clear_auth_state()
                st.rerun()

# ============================================================================
# TAB NAVIGATION
# ============================================================================

def render_tabs():
    tabs = [
        ('chat',     '💬', 'Chat'),
        ('recipes',  '📖', 'Recipes'),
        ('shopping', '🛒', 'Shopping'),
        ('reminders','⏰', 'Reminders'),
        ('upload',   '📷', 'Scan'),
    ]
    cols = st.columns(len(tabs))
    for col, (key, icon, label) in zip(cols, tabs):
        with col:
            active = st.session_state.active_tab == key
            style = "background:#1A1508;border:1px solid #3A2510;color:#F0C040;" if active else "background:transparent;border:1px solid #1E1A10;color:#5A4A28;"
            if st.button(
                f"{icon} {label}",
                key=f"tab_{key}",
                use_container_width=True,
            ):
                st.session_state.active_tab = key
                st.rerun()

# ============================================================================
# CHAT TAB
# ============================================================================

def render_chat_tab():
    history = st.session_state.conversation_history

    # ── Message area ──
    if not history:
        st.markdown("""
        <div class="chat-messages">
            <div class="welcome-state">
                <div class="w-icon">🍛</div>
                <h2>Namaste!</h2>
                <p>Ask me about Andhra recipes, identify ingredients from a photo, or plan your shopping.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Quick-start chips rendered as real buttons
        st.markdown('<div class="section-title">Try asking</div>', unsafe_allow_html=True)
        chips = [
            "What can I cook with tomatoes and rice?",
            "Give me a Pesarattu recipe",
            "How do I make Gongura chutney?",
            "What spices are in Andhra biryani?",
        ]
        c1, c2 = st.columns(2)
        for i, chip in enumerate(chips):
            with (c1 if i % 2 == 0 else c2):
                if st.button(chip, key=f"chip_{i}", use_container_width=True):
                    with st.spinner(t('loading')):
                        _send_message(chip)
                    st.rerun()
    else:
        msgs_html = ""
        for msg in history:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            ts = msg.get('timestamp', '')
            avatar = '👤' if role == 'user' else '🍛'
            # SECURITY: Escape all user content to prevent XSS
            content_safe = _escape_html(content)
            ts_safe = _escape_html(ts)
            msgs_html += f"""
            <div class="msg-row {role}">
                <div class="msg-avatar-circle">{avatar}</div>
                <div>
                    <div class="msg-bubble">{content_safe}</div>
                    <div class="msg-time">{ts_safe}</div>
                </div>
            </div>"""
        st.markdown(f'<div class="chat-messages">{msgs_html}</div>', unsafe_allow_html=True)

    # ── Input bar ──
    st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
    with st.form(key='chat_form', clear_on_submit=True):
        c1, c2 = st.columns([8, 1])
        with c1:
            user_input = st.text_input(
                "msg", placeholder=t('chat_placeholder'),
                label_visibility='collapsed', key='chat_field'
            )
        with c2:
            submitted = st.form_submit_button("➤", use_container_width=True)

    if submitted and user_input:
        with st.spinner(t('loading')):
            _send_message(user_input)
        st.rerun()

    # ── Action row ──
    a1, a2, a3 = st.columns(3)
    with a1:
        if st.button(t('voice_button'), use_container_width=True, key='voice_btn'):
            st.session_state.is_recording = not st.session_state.is_recording
            st.rerun()
    with a2:
        if st.button(t('upload_button'), use_container_width=True, key='scan_shortcut'):
            st.session_state.active_tab = 'upload'
            st.rerun()
    with a3:
        if st.button("🗑 Clear", use_container_width=True, key='clear_chat'):
            st.session_state.conversation_history = []
            st.rerun()

    # Voice recording indicator
    if st.session_state.is_recording:
        st.info(t('voice_listening'))
        lang_code = 'en-IN' if st.session_state.language == 'en' else 'te-IN'
        st.components.v1.html(f"""
        <script>
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) {{
            window.parent.postMessage({{type:'voice_error',message:'not_supported'}},'*');
        }} else {{
            const r = new SR();
            r.lang = '{lang_code}'; r.continuous = false; r.interimResults = false;
            r.onresult = e => window.parent.postMessage({{type:'voice_transcript',text:e.results[0][0].transcript}},'*');
            r.onerror = e => window.parent.postMessage({{type:'voice_error',message:e.error}},'*');
            r.onend = () => window.parent.postMessage({{type:'voice_stopped'}},'*');
            try {{ r.start(); }} catch(e) {{}}
        }}
        </script>""", height=0)

    # Handle voice transcript
    if st.session_state.voice_transcript:
        with st.spinner(t('loading')):
            _send_message(st.session_state.voice_transcript)
        st.session_state.voice_transcript = ''
        st.session_state.is_recording = False
        st.rerun()

# ============================================================================
# SCAN / UPLOAD TAB
# ============================================================================

def render_upload_tab():
    st.markdown('<div class="page-title">📷 Scan Ingredients</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-subtitle">{t("upload_formats")}</div>', unsafe_allow_html=True)

    # WARNING: File type and size are validated below to prevent malicious uploads.
    # Never skip these checks — accepting arbitrary files is a security risk.
    uploaded_file = st.file_uploader(
        "Upload", type=['jpg', 'jpeg', 'png', 'heic'],
        accept_multiple_files=False,
        label_visibility='collapsed', key='image_uploader'
    )

    if uploaded_file:
        if uploaded_file.size / (1024 * 1024) > 10:
            st.error("File exceeds 10 MB limit.")
            return

        col_img, col_action = st.columns([2, 1])
        with col_img:
            st.image(uploaded_file, use_column_width=True)
        with col_action:
            st.markdown('<div class="section-title">Actions</div>', unsafe_allow_html=True)
            if st.button("🔍 Analyse Ingredients", use_container_width=True, key='analyse_btn'):
                with st.spinner(t('upload_analyzing')):
                    if api_client and st.session_state.session_id:
                        try:
                            up = api_client.upload_image(uploaded_file, session_id=st.session_state.session_id)
                            result = api_client.analyze_image(
                                session_id=st.session_state.session_id,
                                image_id=up.get('image_id'),
                                language=st.session_state.language,
                            )
                            st.session_state.detected_ingredients = result
                            st.success(t('upload_success'))
                        except APIError:
                            display_error('analysis')
                        except NetworkError:
                            display_error('network')
                    else:
                        # Dev fallback — mock data
                        st.session_state.detected_ingredients = {
                            'ingredients': [
                                {'ingredient_name': 'Tomato',  'quantity': 5, 'unit': 'pcs',  'confidence_score': 0.95},
                                {'ingredient_name': 'Onion',   'quantity': 3, 'unit': 'pcs',  'confidence_score': 0.65},
                                {'ingredient_name': 'Rice',    'quantity': 1, 'unit': 'kg',   'confidence_score': 0.88},
                            ]
                        }
                        st.warning("Mock data — backend not connected")
                st.rerun()

    # ── Detected ingredients ──
    if st.session_state.detected_ingredients:
        ingredients = st.session_state.detected_ingredients.get('ingredients', [])
        st.markdown(f'<div class="section-title">{t("ingredients_detected")} ({len(ingredients)})</div>', unsafe_allow_html=True)

        with st.container():
            for idx, ing in enumerate(ingredients):
                name  = ing.get('ingredient_name', '')
                qty   = ing.get('quantity', 0)
                unit  = ing.get('unit', '')
                conf  = ing.get('confidence_score', 0)

                # SECURITY: Escape user-provided ingredient data
                name_safe = _escape_html(name)
                unit_safe = _escape_html(unit)

                if conf >= 0.7:
                    badge = f'<span class="conf-badge conf-high">{t("confidence_high")}</span>'
                elif conf >= 0.5:
                    badge = f'<span class="conf-badge conf-med">{t("confidence_medium")}</span>'
                else:
                    badge = f'<span class="conf-badge conf-low">{t("confidence_low")}</span>'

                c1, c2, c3 = st.columns([4, 1, 1])
                with c1:
                    st.markdown(
                        f'<div class="ing-row"><span class="ing-name">{name_safe}</span>'
                        f'<span class="ing-qty">{qty} {unit_safe}</span>{badge}</div>',
                        unsafe_allow_html=True
                    )
                with c2:
                    if 0.5 <= conf < 0.7:
                        if st.button(t('confirm_ingredient'), key=f'conf_{idx}', use_container_width=True):
                            st.session_state.detected_ingredients['ingredients'][idx]['confidence_score'] = 0.95
                            st.rerun()
                with c3:
                    if st.button(t('remove_ingredient'), key=f'rem_{idx}', use_container_width=True):
                        st.session_state.detected_ingredients['ingredients'].pop(idx)
                        st.rerun()

        st.markdown("---")
        if st.button("🍳 Generate Recipes from these ingredients", use_container_width=True, key='gen_recipes_scan'):
            with st.spinner("Generating recipes…"):
                if api_client and st.session_state.session_id:
                    try:
                        resp = api_client.generate_recipes(
                            session_id=st.session_state.session_id,
                            inventory=st.session_state.detected_ingredients,
                            language=st.session_state.language,
                            count=3,
                        )
                        st.session_state.recipes = resp.get('recipes', [])
                        st.session_state.active_tab = 'recipes'
                    except (APIError, NetworkError):
                        display_error('recipe')
                else:
                    st.warning("Backend not connected")
            st.rerun()

# ============================================================================
# RECIPES TAB
# ============================================================================

def render_recipes_tab():
    st.markdown(f'<div class="page-title">📖 {t("recipe_title")}</div>', unsafe_allow_html=True)

    if not st.session_state.recipes:
        st.markdown("""
        <div class="card" style="text-align:center;padding:2.5rem;">
            <div style="font-size:2.5rem;margin-bottom:0.75rem;">🍳</div>
            <div style="color:#5A4A28;font-size:0.9rem;">
                No recipes yet. Upload a photo or ask in chat to generate recipes.
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("💬 Go to Chat", key='goto_chat_r'):
            st.session_state.active_tab = 'chat'
            st.rerun()
        return

    for idx, recipe in enumerate(st.session_state.recipes):
        recipe_id      = recipe.get('recipe_id', f'recipe_{idx}')
        name           = recipe.get('name', 'Unknown Recipe')
        prep_time      = recipe.get('prep_time', 'N/A')
        servings       = recipe.get('servings', 1)
        ingredients    = recipe.get('ingredients', [])
        steps          = recipe.get('steps', [])
        nutrition      = recipe.get('nutrition', {})
        cost           = recipe.get('cost_per_serving', 0)
        is_selected    = (
            st.session_state.selected_recipe and
            st.session_state.selected_recipe.get('recipe_id') == recipe_id
        )
        card_class = "card selected" if is_selected else "card"

        # SECURITY: Escape all recipe data to prevent XSS
        name_safe = _escape_html(name)
        prep_time_safe = _escape_html(prep_time)

        with st.container():
            st.markdown(f'<div class="{card_class}"></div>', unsafe_allow_html=True)

            h1, h2 = st.columns([5, 1])
            with h1:
                st.markdown(f'<div class="card-title">{name_safe}</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="card-meta">'
                    f'<span>⏱ {prep_time_safe}</span>'
                    f'<span>👥 {servings}</span>'
                    f'<span>₹ {cost:.0f}/serving</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            with h2:
                btn_label = t('recipe_selected') if is_selected else t('recipe_select')
                if st.button(btn_label, key=f'sel_{idx}', use_container_width=True):
                    st.session_state.selected_recipe = None if is_selected else recipe
                    st.rerun()

            # Expandable details
            with st.expander("View details"):
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric(t('recipe_calories'), f"{nutrition.get('calories',0)}")
                m2.metric(t('recipe_protein'),  f"{nutrition.get('protein',0)}g")
                m3.metric(t('recipe_carbs'),    f"{nutrition.get('carbohydrates',0)}g")
                m4.metric(t('recipe_fat'),      f"{nutrition.get('fat',0)}g")
                m5.metric(t('recipe_fiber'),    f"{nutrition.get('fiber',0)}g")

                st.markdown(f'<div class="section-title">{t("recipe_ingredients")}</div>', unsafe_allow_html=True)
                for ing in ingredients:
                    # SECURITY: Escape ingredient data
                    ing_name_safe = _escape_html(ing.get('name',''))
                    ing_qty_safe = _escape_html(str(ing.get('quantity','')))
                    ing_unit_safe = _escape_html(ing.get('unit',''))
                    st.markdown(
                        f"<span class='tag'>{ing_name_safe} · {ing_qty_safe} {ing_unit_safe}</span>",
                        unsafe_allow_html=True
                    )

                st.markdown(f'<div class="section-title">{t("recipe_steps")}</div>', unsafe_allow_html=True)
                for i, step in enumerate(steps, 1):
                    # SECURITY: Escape step content
                    step_safe = _escape_html(step)
                    st.markdown(
                        f'<div style="padding:0.4rem 0;border-bottom:1px solid #1A1508;font-size:0.88rem;color:#C8B890;">'
                        f'<span style="color:#E8890C;font-weight:600;margin-right:0.5rem;">{i}.</span>{step_safe}</div>',
                        unsafe_allow_html=True
                    )

    # Generate shopping list CTA
    if st.session_state.selected_recipe:
        st.markdown("---")
        if st.button(f"🛒 {t('generate_shopping_list')}", use_container_width=True, key='gen_shop'):
            with st.spinner("Generating shopping list…"):
                if api_client and st.session_state.session_id:
                    try:
                        resp = api_client.generate_shopping_list(
                            session_id=st.session_state.session_id,
                            recipe_id=st.session_state.selected_recipe.get('recipe_id'),
                            current_inventory=st.session_state.detected_ingredients or {},
                            language=st.session_state.language,
                        )
                        st.session_state.shopping_list = resp.get('shopping_list')
                        reminders = resp.get('reminders', [])
                        if reminders:
                            st.session_state.reminders.extend(reminders)
                        st.session_state.active_tab = 'shopping'
                    except (APIError, NetworkError):
                        display_error('shopping')
                else:
                    st.warning("Backend not connected")
            st.rerun()

# ============================================================================
# SHOPPING TAB
# ============================================================================

def render_shopping_tab():
    st.markdown(f'<div class="page-title">🛒 {t("shopping_list_title")}</div>', unsafe_allow_html=True)

    if not st.session_state.shopping_list:
        st.markdown("""
        <div class="card" style="text-align:center;padding:2.5rem;">
            <div style="font-size:2.5rem;margin-bottom:0.75rem;">🛒</div>
            <div style="color:#5A4A28;font-size:0.9rem;">
                No shopping list yet. Select a recipe and generate one.
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("📖 Go to Recipes", key='goto_recipes_s'):
            st.session_state.active_tab = 'recipes'
            st.rerun()
        return

    shopping_list = st.session_state.shopping_list
    items         = shopping_list.get('items', [])
    total_cost    = shopping_list.get('total_cost', 0)

    # Group by section
    sections: dict = {}
    for item in items:
        sec = item.get('market_section', 'Other')
        sections.setdefault(sec, []).append(item)

    remaining = 0.0
    for section, sec_items in sections.items():
        st.markdown(f'<div class="section-title">{_escape_html(section)}</div>', unsafe_allow_html=True)
        with st.container():
            for idx, item in enumerate(sec_items):
                item_id   = f"{section}_{idx}"
                iname     = item.get('ingredient_name', '')
                qty       = item.get('quantity', 0)
                unit      = item.get('unit', '')
                price     = item.get('estimated_price', 0.0)
                purchased = item_id in st.session_state.purchased_items

                # SECURITY: Escape shopping list data
                iname_safe = _escape_html(iname)
                unit_safe = _escape_html(unit)

                c1, c2 = st.columns([6, 1])
                with c1:
                    name_class = "shop-name done" if purchased else "shop-name"
                    st.markdown(
                        f'<div class="shop-row">'
                        f'<span class="{name_class}">{iname_safe}</span>'
                        f'<span class="shop-qty">{qty} {unit_safe}</span>'
                        f'<span class="shop-price">₹{price:.2f}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                with c2:
                    checked = st.checkbox("", value=purchased, key=f'chk_{item_id}', label_visibility='collapsed')
                    if checked:
                        st.session_state.purchased_items.add(item_id)
                    else:
                        st.session_state.purchased_items.discard(item_id)

                if not purchased:
                    remaining += price

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Remaining", f"₹{remaining:.2f}")
    with c2:
        st.metric("Total", f"₹{total_cost:.2f}")

# ============================================================================
# REMINDERS TAB
# ============================================================================

def render_reminders_tab():
    st.markdown(f'<div class="page-title">⏰ {t("reminder_title")}</div>', unsafe_allow_html=True)

    active = [r for r in st.session_state.reminders if r.get('status') in ('pending', 'delivered')]

    if not active:
        st.markdown("""
        <div class="card" style="text-align:center;padding:2.5rem;">
            <div style="font-size:2.5rem;margin-bottom:0.75rem;">✅</div>
            <div style="color:#5A4A28;font-size:0.9rem;">No active reminders.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    snooze_opts = {t('reminder_snooze_1h'): 1, t('reminder_snooze_3h'): 3, t('reminder_snooze_24h'): 24}

    for idx, reminder in enumerate(st.session_state.reminders):
        if reminder.get('status') not in ('pending', 'delivered'):
            continue
        rid     = reminder.get('reminder_id', f'r_{idx}')
        content = reminder.get('content', '')
        reason  = reminder.get('reason', '')

        # SECURITY: Escape reminder content
        content_safe = _escape_html(content)
        reason_safe = _escape_html(reason)

        st.markdown(
            f'<div class="reminder-item">'
            f'<div class="reminder-text">⏰ {content_safe}</div>'
            f'{"<div class=reminder-reason>" + reason_safe + "</div>" if reason else ""}'
            f'</div>',
            unsafe_allow_html=True
        )

        c1, c2, c3 = st.columns([2, 2, 3])
        with c1:
            if st.button(t('reminder_dismiss'), key=f'dis_{rid}', use_container_width=True):
                if api_client:
                    try:
                        api_client.dismiss_reminder(rid, st.session_state.session_id)
                    except (APIError, NetworkError) as e:
                        logger.error(f"Dismiss error: {e}")
                st.session_state.reminders[idx]['status'] = 'dismissed'
                st.rerun()
        with c2:
            snooze_sel = st.selectbox(
                "snooze", list(snooze_opts.keys()),
                key=f'snz_sel_{rid}', label_visibility='collapsed'
            )
        with c3:
            if st.button(f"💤 {t('reminder_snooze')}", key=f'snz_{rid}', use_container_width=True):
                hours = snooze_opts[snooze_sel]
                if api_client:
                    try:
                        api_client.snooze_reminder(rid, st.session_state.session_id, hours)
                    except (APIError, NetworkError) as e:
                        logger.error(f"Snooze error: {e}")
                st.success(f"Snoozed for {hours}h")
                st.rerun()

        st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)

# ============================================================================
# MAIN
# ============================================================================

def main():
    initialize_session_state()
    if not st.session_state.is_authenticated:
        render_login_screen()
        return

    render_navbar()

    st.markdown('<div style="height:0.75rem"></div>', unsafe_allow_html=True)
    render_tabs()
    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)

    # Reminder badge — show count in a small notice if reminders exist
    active_reminders = [r for r in st.session_state.reminders if r.get('status') in ('pending', 'delivered')]
    if active_reminders and st.session_state.active_tab != 'reminders':
        st.info(f"⏰ You have {len(active_reminders)} active reminder(s). [View →](#)")

    tab = st.session_state.active_tab
    if tab == 'chat':
        render_chat_tab()
    elif tab == 'recipes':
        render_recipes_tab()
    elif tab == 'shopping':
        render_shopping_tab()
    elif tab == 'reminders':
        render_reminders_tab()
    elif tab == 'upload':
        render_upload_tab()

if __name__ == "__main__":
    main()
