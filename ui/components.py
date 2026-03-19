"""
UI Components for Andhra Kitchen Agent
Renders all visual elements with the warm Andhra aesthetic.
"""

import streamlit as st
import logging
from ui.translations import t
from ui.handlers import _escape_html, display_error, check_password_strength, send_message
from ui.state import set_auth_state, clear_auth_state
from config.env import Config

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


def render_login_screen():
    """Render the Cognito sign-in form."""
    st.markdown(
        """
        <div style="max-width:420px;margin:6rem auto 0 auto;padding:2rem;background:#1E1508;border:1px solid #3A2510;border-radius:16px;">
            <div style="font-size:2rem;margin-bottom:0.75rem;">🔐</div>
            <div style="font-size:1.4rem;font-weight:700;color:#EAB840;margin-bottom:0.35rem;">Sign In</div>
            <div style="font-size:0.9rem;color:#7A3E14;margin-bottom:1.5rem;">Authenticate with Cognito to access your kitchen session.</div>
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


def render_navbar():
    """Render the top navigation bar with status and logout."""
    connected = st.session_state.is_authenticated and st.session_state.session_id is not None
    dot = '<span class="ct-dot"></span>' if connected else '<span class="ct-dot" style="background:#A01808;box-shadow:0 0 6px #A01808;"></span>'
    status_text = st.session_state.user_email if connected and st.session_state.user_email else ("Connected" if connected else "Offline")
    
    # SECURITY: Escape status text to prevent XSS (user_email comes from session state)
    status_text_safe = _escape_html(status_text)

    st.markdown(f"""
    <div class="topbar">
        <div class="ct-status">
            {dot}
            <span class="ct-label"><strong>{t('title')}</strong> · అంధ్ర వంటగది</span>
        </div>
        <div class="ct-status">
            <span class="ct-label">{status_text_safe}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Language selector and logout in columns
    col1, col2, col3 = st.columns([6, 1, 1])
    with col2:
        lang_options = {'🇬🇧 EN': 'en', '🇮🇳 TE': 'te'}
        sel = st.selectbox(
            "lang", list(lang_options.keys()),
            index=list(lang_options.values()).index(st.session_state.language),
            label_visibility='collapsed', key='lang_sel'
        )
        new_lang = lang_options[sel]
        if new_lang != st.session_state.language:
            st.session_state.language = new_lang
            st.rerun()
    with col3:
        if st.session_state.is_authenticated:
            if st.button("Logout", use_container_width=True, key='logout_btn'):
                try:
                    if auth_client and st.session_state.get('access_token'):
                        auth_client.logout(st.session_state.access_token)
                except AuthClientError as exc:
                    logger.error(f"Logout failed: {exc}")
                clear_auth_state()
                st.rerun()


def render_chat_tab():
    """Render the chat interface with message history."""
    history = st.session_state.conversation_history

    # Welcome state
    if not history:
        st.markdown("""
        <div class="welcome">
            <div class="wlc-orb">🍛</div>
            <div class="wlc-namaste">నమస్కారం</div>
            <div class="wlc-h">Welcome to Andhra Kitchen</div>
            <div class="wlc-p">Ask me about traditional recipes, identify ingredients from photos, or plan your shopping list.</div>
        </div>
        """, unsafe_allow_html=True)

        # Quick suggestions
        st.markdown('<div style="max-width:560px;margin:0 auto;">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.7rem;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:#7A3E14;margin:1.5rem 0 0.75rem 0;">TRY ASKING</div>', unsafe_allow_html=True)
        
        suggestions = [
            ("🍚", "Rice Dishes", "What can I cook with rice?"),
            ("🌶️", "Spicy Curries", "Give me a spicy curry recipe"),
            ("🥘", "Traditional", "How to make Pesarattu?"),
            ("🛒", "Shopping", "Plan my weekly shopping"),
        ]
        
        cols = st.columns(2)
        for idx, (icon, title, query) in enumerate(suggestions):
            with cols[idx % 2]:
                if st.button(f"{icon} {title}", key=f"sug_{idx}", use_container_width=True):
                    with st.spinner(t('loading')):
                        send_message(query)
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Message history
        st.markdown('<div class="msgs-scroll">', unsafe_allow_html=True)
        for msg in history:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            ts = msg.get('timestamp', '')
            
            # SECURITY: Escape all user content to prevent XSS
            content_safe = _escape_html(content)
            ts_safe = _escape_html(ts)
            
            if role == 'user':
                st.markdown(f"""
                <div class="msg-wrap user">
                    <div class="av av-user">👤</div>
                    <div>
                        <div class="bubble bubble-user">{content_safe}</div>
                        <div class="msg-time">{ts_safe}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="msg-wrap">
                    <div class="av av-ai">🍛</div>
                    <div>
                        <div class="bubble bubble-ai">{content_safe}</div>
                        <div class="msg-time">{ts_safe}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Input area
    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
    with st.form(key='chat_form', clear_on_submit=True):
        cols = st.columns([5, 1])
        with cols[0]:
            user_input = st.text_area(
                "msg", placeholder=t('chat_placeholder'),
                label_visibility='collapsed', key='chat_field', height=80
            )
        with cols[1]:
            st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
            submitted = st.form_submit_button("Send", use_container_width=True)

    if submitted and user_input:
        with st.spinner(t('loading')):
            send_message(user_input)
        st.rerun()

    # Quick actions
    st.markdown('<div class="qa-row">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🎤 Voice", use_container_width=True, key='voice_btn'):
            st.info("Voice input coming soon")
    with col2:
        if st.button("📷 Scan", use_container_width=True, key='scan_btn'):
            st.session_state.active_tab = 'upload'
            st.rerun()
    with col3:
        if st.button("🗑 Clear", use_container_width=True, key='clear_btn'):
            st.session_state.conversation_history = []
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def render_upload_tab():
    """Render the image upload and ingredient detection interface."""
    st.markdown('<div style="max-width:700px;margin:0 auto;">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:1.4rem;font-weight:700;color:#3A200E;margin-bottom:0.5rem;">📷 Scan Ingredients</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:0.85rem;color:#7A3E14;margin-bottom:1.5rem;">{t("upload_formats")}</div>', unsafe_allow_html=True)

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
            if st.button("🔍 Analyze", use_container_width=True, key='analyze_btn'):
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
                        # Dev fallback
                        st.session_state.detected_ingredients = {
                            'ingredients': [
                                {'ingredient_name': 'Tomato', 'quantity': 5, 'unit': 'pcs', 'confidence_score': 0.95},
                                {'ingredient_name': 'Onion', 'quantity': 3, 'unit': 'pcs', 'confidence_score': 0.65},
                                {'ingredient_name': 'Rice', 'quantity': 1, 'unit': 'kg', 'confidence_score': 0.88},
                            ]
                        }
                        st.warning("Mock data — backend not connected")
                st.rerun()

    # Detected ingredients
    if st.session_state.detected_ingredients:
        ingredients = st.session_state.detected_ingredients.get('ingredients', [])
        st.markdown(f'<div style="font-size:0.7rem;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:#7A3E14;margin:1.5rem 0 0.75rem 0;">{t("ingredients_detected")} ({len(ingredients)})</div>', unsafe_allow_html=True)

        for idx, ing in enumerate(ingredients):
            name = ing.get('ingredient_name', '')
            qty = ing.get('quantity', 0)
            unit = ing.get('unit', '')
            conf = ing.get('confidence_score', 0)

            # SECURITY: Escape user-provided ingredient data
            name_safe = _escape_html(name)
            unit_safe = _escape_html(unit)

            conf_label = t('confidence_high') if conf >= 0.7 else (t('confidence_medium') if conf >= 0.5 else t('confidence_low'))
            conf_color = '#285010' if conf >= 0.7 else ('#B87010' if conf >= 0.5 else '#A01808')

            cols = st.columns([4, 1, 1])
            with cols[0]:
                st.markdown(
                    f'<div style="padding:0.6rem 0;border-bottom:1px solid #EAD8B0;">'
                    f'<span style="font-size:0.9rem;color:#1E1208;font-weight:500;">{name_safe}</span> '
                    f'<span style="font-size:0.82rem;color:#7A3E14;margin-left:0.5rem;">{qty} {unit_safe}</span> '
                    f'<span style="font-size:0.68rem;padding:0.15rem 0.5rem;border-radius:10px;font-weight:600;background:{conf_color}20;color:{conf_color};border:1px solid {conf_color}40;margin-left:0.5rem;">{conf_label}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            with cols[1]:
                if 0.5 <= conf < 0.7:
                    if st.button("✓", key=f'conf_{idx}', use_container_width=True):
                        st.session_state.detected_ingredients['ingredients'][idx]['confidence_score'] = 0.95
                        st.rerun()
            with cols[2]:
                if st.button("✗", key=f'rem_{idx}', use_container_width=True):
                    st.session_state.detected_ingredients['ingredients'].pop(idx)
                    st.rerun()

        st.markdown("---")
        if st.button("🍳 Generate Recipes", use_container_width=True, key='gen_recipes'):
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

    st.markdown('</div>', unsafe_allow_html=True)


def render_recipes_tab():
    """Render the recipes list with selection."""
    st.markdown('<div style="max-width:800px;margin:0 auto;">', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:1.4rem;font-weight:700;color:#3A200E;margin-bottom:1rem;">📖 {t("recipe_title")}</div>', unsafe_allow_html=True)

    if not st.session_state.recipes:
        st.markdown("""
        <div style="text-align:center;padding:3rem 2rem;background:var(--warm-off);border:1px solid var(--border-sm);border-radius:12px;">
            <div style="font-size:2.5rem;margin-bottom:0.75rem;">🍳</div>
            <div style="color:#7A3E14;font-size:0.9rem;">No recipes yet. Upload a photo or ask in chat.</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("💬 Go to Chat", key='goto_chat'):
            st.session_state.active_tab = 'chat'
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        return

    for idx, recipe in enumerate(st.session_state.recipes):
        recipe_id = recipe.get('recipe_id', f'recipe_{idx}')
        name = recipe.get('name', 'Unknown Recipe')
        prep_time = recipe.get('prep_time', 'N/A')
        servings = recipe.get('servings', 1)
        ingredients = recipe.get('ingredients', [])
        steps = recipe.get('steps', [])
        nutrition = recipe.get('nutrition', {})
        cost = recipe.get('cost_per_serving', 0)
        is_selected = (
            st.session_state.selected_recipe and
            st.session_state.selected_recipe.get('recipe_id') == recipe_id
        )

        # SECURITY: Escape all recipe data
        name_safe = _escape_html(name)
        prep_time_safe = _escape_html(prep_time)

        border_color = 'var(--turmeric)' if is_selected else 'var(--border-sm)'
        
        st.markdown(f"""
        <div style="background:var(--warm-off);border:1px solid {border_color};border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1rem;">
            <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:0.75rem;">
                <div>
                    <div style="font-family:'Playfair Display',serif;font-size:1.05rem;font-weight:600;color:var(--bark);">{name_safe}</div>
                    <div style="font-size:0.78rem;color:#7A3E14;margin-top:0.3rem;">
                        ⏱ {prep_time_safe} · 👥 {servings} · ₹{cost:.0f}/serving
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        cols = st.columns([5, 1])
        with cols[1]:
            btn_label = "✓ Selected" if is_selected else "Select"
            if st.button(btn_label, key=f'sel_{idx}', use_container_width=True):
                st.session_state.selected_recipe = None if is_selected else recipe
                st.rerun()

        with st.expander("View Details"):
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Calories", f"{nutrition.get('calories', 0)}")
            m2.metric("Protein", f"{nutrition.get('protein', 0)}g")
            m3.metric("Carbs", f"{nutrition.get('carbohydrates', 0)}g")
            m4.metric("Fat", f"{nutrition.get('fat', 0)}g")
            m5.metric("Fiber", f"{nutrition.get('fiber', 0)}g")

            st.markdown(f'<div style="font-size:0.7rem;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:#7A3E14;margin:1rem 0 0.5rem 0;">{t("recipe_ingredients")}</div>', unsafe_allow_html=True)
            for ing in ingredients:
                ing_name_safe = _escape_html(ing.get('name', ''))
                ing_qty_safe = _escape_html(str(ing.get('quantity', '')))
                ing_unit_safe = _escape_html(ing.get('unit', ''))
                st.markdown(
                    f"<span style='display:inline-block;background:var(--parchment);border:1px solid var(--border);color:#7A3E14;border-radius:20px;padding:0.18rem 0.65rem;font-size:0.72rem;font-weight:500;margin:0.15rem 0.2rem;'>{ing_name_safe} · {ing_qty_safe} {ing_unit_safe}</span>",
                    unsafe_allow_html=True
                )

            st.markdown(f'<div style="font-size:0.7rem;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:#7A3E14;margin:1rem 0 0.5rem 0;">{t("recipe_steps")}</div>', unsafe_allow_html=True)
            for i, step in enumerate(steps, 1):
                step_safe = _escape_html(step)
                st.markdown(
                    f'<div style="padding:0.4rem 0;border-bottom:1px solid #EAD8B0;font-size:0.88rem;color:#3A200E;">'
                    f'<span style="color:#B87010;font-weight:600;margin-right:0.5rem;">{i}.</span>{step_safe}</div>',
                    unsafe_allow_html=True
                )

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

    st.markdown('</div>', unsafe_allow_html=True)


def render_shopping_tab():
    """Render the shopping list with checkboxes."""
    st.markdown('<div style="max-width:700px;margin:0 auto;">', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:1.4rem;font-weight:700;color:#3A200E;margin-bottom:1rem;">🛒 {t("shopping_list_title")}</div>', unsafe_allow_html=True)

    if not st.session_state.shopping_list:
        st.markdown("""
        <div style="text-align:center;padding:3rem 2rem;background:var(--warm-off);border:1px solid var(--border-sm);border-radius:12px;">
            <div style="font-size:2.5rem;margin-bottom:0.75rem;">🛒</div>
            <div style="color:#7A3E14;font-size:0.9rem;">No shopping list yet. Select a recipe first.</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("📖 Go to Recipes", key='goto_recipes'):
            st.session_state.active_tab = 'recipes'
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        return

    shopping_list = st.session_state.shopping_list
    items = shopping_list.get('items', [])
    total_cost = shopping_list.get('total_cost', 0)

    sections = {}
    for item in items:
        sec = item.get('market_section', 'Other')
        sections.setdefault(sec, []).append(item)

    remaining = 0.0
    for section, sec_items in sections.items():
        st.markdown(f'<div style="font-size:0.7rem;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:#7A3E14;margin:1.5rem 0 0.75rem 0;">{_escape_html(section)}</div>', unsafe_allow_html=True)
        
        for idx, item in enumerate(sec_items):
            item_id = f"{section}_{idx}"
            iname = item.get('ingredient_name', '')
            qty = item.get('quantity', 0)
            unit = item.get('unit', '')
            price = item.get('estimated_price', 0.0)
            purchased = item_id in st.session_state.purchased_items

            # SECURITY: Escape shopping list data
            iname_safe = _escape_html(iname)
            unit_safe = _escape_html(unit)

            cols = st.columns([6, 1])
            with cols[0]:
                text_style = "text-decoration:line-through;color:#7A3E14;" if purchased else "color:#1E1208;"
                st.markdown(
                    f'<div style="padding:0.55rem 0;border-bottom:1px solid #EAD8B0;display:flex;align-items:center;justify-content:space-between;">'
                    f'<span style="font-size:0.88rem;{text_style}">{iname_safe}</span>'
                    f'<span style="font-size:0.8rem;color:#7A3E14;min-width:70px;">{qty} {unit_safe}</span>'
                    f'<span style="font-size:0.85rem;color:#B87010;font-weight:500;min-width:60px;text-align:right;">₹{price:.2f}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            with cols[1]:
                checked = st.checkbox("", value=purchased, key=f'chk_{item_id}', label_visibility='collapsed')
                if checked:
                    st.session_state.purchased_items.add(item_id)
                else:
                    st.session_state.purchased_items.discard(item_id)

            if not purchased:
                remaining += price

    st.markdown("---")
    cols = st.columns(2)
    with cols[0]:
        st.metric("Remaining", f"₹{remaining:.2f}")
    with cols[1]:
        st.metric("Total", f"₹{total_cost:.2f}")

    st.markdown('</div>', unsafe_allow_html=True)


def render_reminders_tab():
    """Render active reminders with dismiss/snooze actions."""
    st.markdown('<div style="max-width:700px;margin:0 auto;">', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:1.4rem;font-weight:700;color:#3A200E;margin-bottom:1rem;">⏰ {t("reminder_title")}</div>', unsafe_allow_html=True)

    active = [r for r in st.session_state.reminders if r.get('status') in ('pending', 'delivered')]

    if not active:
        st.markdown("""
        <div style="text-align:center;padding:3rem 2rem;background:var(--warm-off);border:1px solid var(--border-sm);border-radius:12px;">
            <div style="font-size:2.5rem;margin-bottom:0.75rem;">✅</div>
            <div style="color:#7A3E14;font-size:0.9rem;">No active reminders.</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        return

    snooze_opts = {t('reminder_snooze_1h'): 1, t('reminder_snooze_3h'): 3, t('reminder_snooze_24h'): 24}

    for idx, reminder in enumerate(st.session_state.reminders):
        if reminder.get('status') not in ('pending', 'delivered'):
            continue
        rid = reminder.get('reminder_id', f'r_{idx}')
        content = reminder.get('content', '')
        reason = reminder.get('reason', '')

        # SECURITY: Escape reminder content
        content_safe = _escape_html(content)
        reason_safe = _escape_html(reason)

        st.markdown(
            f'<div style="background:var(--warm-off);border:1px solid var(--border);border-left:3px solid var(--turmeric);border-radius:12px;padding:1rem 1.25rem;margin-bottom:0.75rem;">'
            f'<div style="font-size:0.92rem;color:#1E1208;">⏰ {content_safe}</div>'
            f'{"<div style=font-size:0.78rem;color:#7A3E14;margin-top:0.3rem;>" + reason_safe + "</div>" if reason else ""}'
            f'</div>',
            unsafe_allow_html=True
        )

        cols = st.columns([2, 2, 3])
        with cols[0]:
            if st.button(t('reminder_dismiss'), key=f'dis_{rid}', use_container_width=True):
                if api_client:
                    try:
                        api_client.dismiss_reminder(rid, st.session_state.session_id)
                    except (APIError, NetworkError) as e:
                        logger.error(f"Dismiss error: {e}")
                st.session_state.reminders[idx]['status'] = 'dismissed'
                st.rerun()
        with cols[1]:
            snooze_sel = st.selectbox(
                "snooze", list(snooze_opts.keys()),
                key=f'snz_sel_{rid}', label_visibility='collapsed'
            )
        with cols[2]:
            if st.button(f"💤 {t('reminder_snooze')}", key=f'snz_{rid}', use_container_width=True):
                hours = snooze_opts[snooze_sel]
                if api_client:
                    try:
                        api_client.snooze_reminder(rid, st.session_state.session_id, hours)
                    except (APIError, NetworkError) as e:
                        logger.error(f"Snooze error: {e}")
                st.success(f"Snoozed for {hours}h")
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
