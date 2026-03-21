"""
UI Styles for Andhra Kitchen Agent
Warm, traditional aesthetic with modern functionality
"""

def get_global_styles() -> str:
    """Return the complete CSS stylesheet for the application."""
    return """
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;1,400&family=Lora:ital,wght@0,400;0,500;1,400&family=Noto+Sans+Telugu:wght@400;500&display=swap" rel="stylesheet">
<style>
/* ── TOKENS ── */
:root {
    --ink:        #1a1a1a;
    --bark:       #2d2d2d;
    --tamarind:   #3a3a3a;
    --clay:       #666666;
    --turmeric:   #4a90e2;
    --saffron:    #5ba3f5;
    --gold:       #4a90e2;
    --cream:      #ffffff;
    --parchment:  #f5f5f5;
    --warm-off:   #fafafa;
    --border:     #e0e0e0;
    --border-sm:  #eeeeee;
    --leaf:       #4caf50;
    --chilli:     #f44336;
    --shadow:     rgba(0,0,0,0.1);
}

/* ── RESET STREAMLIT CHROME ── */
#MainMenu, footer, header { visibility: hidden; }

.stApp {
    background: var(--cream);
    font-family: 'Lora', Georgia, serif;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background: var(--bark) !important;
    border-right: 1px solid var(--border) !important;
}

[data-testid="stSidebar"] > div:first-child {
    padding: 0;
}

[data-testid="stSidebarNav"] { display: none; }

/* sidebar text overrides */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div {
    color: rgba(255,255,255,0.8) !important;
    font-family: 'Lora', serif !important;
}

/* ── SIDEBAR RADIO (history items) ── */
[data-testid="stSidebar"] .stRadio > label {
    color: var(--gold) !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.07em;
    font-style: italic;
}

[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
    padding: 7px 10px !important;
    border-radius: 8px !important;
    margin-bottom: 2px !important;
    transition: background 0.12s !important;
    font-size: 0.8rem !important;
    color: rgba(251,243,224,0.7) !important;
}

[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
    background: rgba(255,255,255,0.06) !important;
}

[data-testid="stSidebar"] [aria-checked="true"] {
    background: rgba(184,112,16,0.2) !important;
    border: 1px solid rgba(184,112,16,0.3) !important;
}

/* ── SIDEBAR BUTTON ── */
[data-testid="stSidebar"] .stButton button {
    background: rgba(184,112,16,0.15) !important;
    border: 1px dashed rgba(184,112,16,0.4) !important;
    border-radius: 8px !important;
    color: var(--gold) !important;
    font-family: 'Lora', serif !important;
    font-size: 0.82rem !important;
    width: 100% !important;
    transition: background 0.15s !important;
}

[data-testid="stSidebar"] .stButton button:hover {
    background: rgba(184,112,16,0.28) !important;
}

/* ── MAIN CONTENT AREA ── */
.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ── TOP STATUS BAR ── */
.topbar {
    padding: 0.65rem 1.5rem;
    border-bottom: 1px solid var(--border-sm);
    background: var(--warm-off);
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
}

.ct-status { display: flex; align-items: center; gap: 8px; }

.ct-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: #5A9E30;
    box-shadow: 0 0 6px rgba(90,158,48,0.5);
    display: inline-block;
}

.ct-label {
    font-family: 'Lora', serif; font-size: 0.8rem;
    color: var(--clay); font-style: italic;
}

.ct-label strong { color: var(--bark); font-style: normal; font-weight: 600; }

/* ── CHAT MESSAGE BUBBLES ── */
.msg-wrap { display: flex; gap: 10px; max-width: 760px; margin-bottom: 1.4rem; }
.msg-wrap.user { flex-direction: row-reverse; margin-left: auto; }

.av {
    width: 32px; height: 32px; border-radius: 50%;
    flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; margin-top: 2px;
}

.av-ai {
    background: var(--turmeric);
    border: 1px solid var(--border);
    box-shadow: 0 0 10px rgba(74,144,226,0.25);
}

.av-user { background: var(--parchment); border: 1px solid var(--border-sm); }

.bubble {
    max-width: calc(100% - 44px);
    padding: 11px 15px;
    font-family: 'Lora', serif;
    font-size: 0.875rem; line-height: 1.68;
    border-radius: 12px;
}

.bubble-ai {
    background: var(--warm-off);
    border: 1px solid var(--border-sm);
    color: var(--ink);
    border-radius: 4px 12px 12px 12px;
    box-shadow: 0 2px 10px var(--shadow);
}

.bubble-user {
    background: var(--parchment);
    border: 1px solid var(--border);
    color: var(--bark);
    border-radius: 12px 4px 12px 12px;
    box-shadow: 0 2px 10px var(--shadow);
}

.bubble strong { color: var(--turmeric); font-weight: 600; }
.bubble em { color: var(--clay); }

.msg-time {
    font-size: 0.66rem; color: #A08060;
    margin-top: 3px; padding: 0 3px;
    font-style: italic; font-family: 'Lora', serif;
}

.msg-wrap.user .msg-time { text-align: right; }

/* ── RECIPE RESULT CARD (inside bubble) ── */
.rr {
    margin-top: 10px;
    background: var(--parchment);
    border: 1px solid var(--border);
    border-radius: 10px; overflow: hidden;
}

.rr-head {
    padding: 9px 13px;
    background: linear-gradient(90deg, rgba(92,42,10,0.08), transparent);
    border-bottom: 1px solid var(--border-sm);
    display: flex; align-items: center; justify-content: space-between;
}

.rr-name { font-family: 'Playfair Display', serif; font-size: 1rem; font-weight: 600; color: var(--bark); }
.rr-te { font-family: 'Noto Sans Telugu', sans-serif; font-size: 0.68rem; color: var(--clay); }
.rr-badge { font-size: 0.72rem; color: var(--turmeric); font-style: italic; font-family: 'Lora', serif; }
.rr-stats { padding: 9px 13px; display: flex; gap: 1rem; flex-wrap: wrap; }
.rr-s { font-size: 0.73rem; color: var(--clay); display: flex; align-items: center; gap: 4px; }
.rr-s span { color: var(--bark); font-weight: 600; }

/* ── WELCOME CARD ── */
.welcome {
    max-width: 560px; margin: 2rem auto;
    text-align: center; padding: 2rem 1rem;
}

.wlc-orb {
    width: 66px; height: 66px;
    background: var(--turmeric);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 30px; margin: 0 auto 1.25rem;
    border: 2px solid var(--border);
    box-shadow: 0 0 28px rgba(74,144,226,0.2);
}

.wlc-namaste {
    font-family: 'Noto Sans Telugu', sans-serif;
    font-size: 1rem; color: var(--turmeric);
    margin-bottom: 0.35rem;
}

.wlc-h {
    font-family: 'Playfair Display', serif;
    font-size: 1.55rem; font-weight: 600;
    color: var(--bark); margin-bottom: 0.4rem;
}

.wlc-p { font-size: 0.85rem; color: var(--clay); line-height: 1.65; font-style: italic; }

.sug-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.65rem; text-align: left; margin-top: 1.4rem; }

.sug-card {
    padding: 11px 13px;
    background: var(--warm-off);
    border: 1px solid var(--border-sm);
    border-radius: 10px;
    cursor: pointer; transition: all 0.15s;
}

.sug-card:hover { border-color: var(--border); background: var(--parchment); }

.sug-icon { font-size: 1.15rem; margin-bottom: 5px; display: block; }
.sug-title { font-size: 0.8rem; color: var(--bark); font-weight: 600; line-height: 1.3; }
.sug-sub { font-size: 0.7rem; color: var(--clay); margin-top: 2px; font-style: italic; }

/* ── QUICK ACTIONS ── */
.qa-row { display: flex; gap: 0.45rem; flex-wrap: wrap; margin-bottom: 0.5rem; }

.qa {
    padding: 5px 11px; border-radius: 20px;
    background: var(--cream); border: 1px solid var(--border-sm);
    color: var(--clay); font-family: 'Lora', serif; font-size: 0.73rem;
    cursor: pointer; transition: all 0.13s; display: inline-block;
}

.qa:hover { border-color: var(--border); color: var(--turmeric); }

/* ── INPUT OVERRIDE ── */
.stTextArea textarea, .stTextInput input {
    background: var(--cream) !important;
    border: 1.5px solid var(--border-sm) !important;
    border-radius: 11px !important;
    color: var(--ink) !important;
    font-family: 'Lora', serif !important;
    font-size: 0.875rem !important;
    box-shadow: inset 0 1px 3px rgba(30,18,8,0.05) !important;
}

.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--border) !important;
    box-shadow: inset 0 1px 3px rgba(30,18,8,0.05), 0 0 0 3px rgba(184,112,16,0.08) !important;
}

.stTextArea textarea::placeholder, .stTextInput input::placeholder {
    color: #B09070 !important; font-style: italic;
}

/* ── SEND BUTTON ── */
div[data-testid="column"]:last-child .stButton button {
    background: var(--turmeric) !important;
    border: none !important;
    border-radius: 10px !important;
    color: white !important;
    font-family: 'Lora', serif !important;
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    width: 100% !important;
    height: 52px !important;
    box-shadow: 0 3px 12px rgba(74,144,226,0.35) !important;
    transition: background 0.15s !important;
}

div[data-testid="column"]:last-child .stButton button:hover {
    background: var(--saffron) !important;
}

/* ── TOPBAR BUTTONS ── */
.stButton button.ct-action {
    background: var(--cream) !important;
    border: 1px solid var(--border-sm) !important;
    border-radius: 7px !important;
    color: var(--clay) !important;
    font-family: 'Lora', serif !important;
    font-size: 0.76rem !important;
}

/* ── SELECTBOX / MISC ── */
.stSelectbox select {
    font-family: 'Lora', serif !important;
    background: var(--cream) !important;
    border-color: var(--border-sm) !important;
    color: var(--ink) !important;
}

/* ── FOOTER NOTE ── */
.in-foot {
    font-size: 0.66rem; color: #B09070;
    text-align: center; font-style: italic;
    font-family: 'Lora', serif; margin-top: 4px;
}

/* ── TYPING INDICATOR ── */
.typing-wrap { display: flex; gap: 10px; margin-bottom: 1.4rem; }

.typing-bubble {
    background: var(--warm-off);
    border: 1px solid var(--border-sm);
    border-radius: 4px 12px 12px 12px;
    padding: 12px 15px;
    display: flex; align-items: center; gap: 5px;
    box-shadow: 0 2px 10px var(--shadow);
}

@keyframes bounce {
    0%,60%,100% { opacity:.3; transform:translateY(0); }
    30% { opacity:1; transform:translateY(-4px); }
}

.tdot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--turmeric);
    animation: bounce 1.2s ease-in-out infinite;
    display: inline-block;
}

.tdot:nth-child(2) { animation-delay: .2s; }
.tdot:nth-child(3) { animation-delay: .4s; }

/* hide streamlit default labels */
.stTextArea label, .stTextInput label { display: none !important; }

/* column gap fix */
[data-testid="stHorizontalBlock"] { gap: 0.5rem !important; align-items: flex-end !important; }

/* scrollable message area */
.msgs-scroll {
    max-height: calc(100vh - 260px);
    overflow-y: auto;
    padding: 1.5rem 1.5rem 0.5rem;
    scrollbar-width: thin;
    scrollbar-color: var(--border-sm) transparent;
}
</style>
"""
