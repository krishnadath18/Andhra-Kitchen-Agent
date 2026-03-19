"""
Multilingual UI Text for Andhra Kitchen Agent
Supports English and Telugu.
"""

import streamlit as st

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
    """Get translated text for the current language."""
    return UI_TEXT[st.session_state.get('language', 'en')].get(key, key)
