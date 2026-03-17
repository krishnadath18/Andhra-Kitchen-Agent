"""
Local Development Server for Andhra Kitchen Agent

This server wraps the Lambda handlers for local development.
Run this alongside Streamlit for local testing.

Usage:
    python local_server.py
"""

import sys
import os
import json
import base64
from pathlib import Path

# Load .env FIRST before any other imports so Config class picks up the values
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    with open(_env_file, 'r') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _key, _value = _line.split('=', 1)
                os.environ[_key.strip()] = _value.strip().strip('"').strip("'")

from flask import Flask, request, jsonify
from flask_cors import CORS

# Import Lambda handlers
from src.api_handler import (
    handle_create_session,
    handle_get_session,
    handle_chat,
    handle_upload_image,
    handle_analyze_image,
    handle_generate_recipes,
    handle_generate_shopping_list,
    handle_get_reminders,
    handle_dismiss_reminder,
    handle_snooze_reminder
)

app = Flask(__name__)
# WARNING: CORS(app) with no restrictions allows any origin.
# Secure alternative: restrict to localhost only for local dev.
CORS(app, origins=["http://localhost:8501", "http://127.0.0.1:8501"])

def lambda_event_from_flask(flask_request, path_params=None):
    """Convert Flask request to Lambda event format."""
    event = {
        'httpMethod': flask_request.method,
        'path': flask_request.path,
        'pathParameters': path_params or {},
        'queryStringParameters': dict(flask_request.args) or None,
        'headers': dict(flask_request.headers),
        'body': flask_request.get_data(as_text=True) if flask_request.data else None,
        'requestContext': {}
    }
    return event

def lambda_response_to_flask(lambda_response):
    """Convert Lambda response to Flask response."""
    body = lambda_response.get('body', '{}')
    # Parse JSON string to dictionary
    if isinstance(body, str):
        import json
        body = json.loads(body)
    response_headers = lambda_response.get('headers', {})
    return jsonify(body), lambda_response.get('statusCode', 200), response_headers

# Session endpoints
@app.route('/session', methods=['POST'])
def create_session():
    event = lambda_event_from_flask(request)
    response = handle_create_session(event)
    return lambda_response_to_flask(response)

@app.route('/session/<session_id>', methods=['GET'])
def get_session(session_id):
    event = lambda_event_from_flask(request, {'session_id': session_id})
    response = handle_get_session(event)
    return lambda_response_to_flask(response)

# Chat endpoint
@app.route('/chat', methods=['POST'])
def chat():
    event = lambda_event_from_flask(request)
    response = handle_chat(event)
    return lambda_response_to_flask(response)

# Image endpoints
@app.route('/upload-image', methods=['POST'])
def upload_image():
    """Handle image upload with proper multipart form-data parsing."""
    try:
        print(f"[DEBUG] Upload request received")
        print(f"[DEBUG] Content-Type: {request.content_type}")
        print(f"[DEBUG] Files in request: {list(request.files.keys())}")
        print(f"[DEBUG] Form data: {list(request.form.keys())}")
        print(f"[DEBUG] Request data length: {len(request.data)}")
        print(f"[DEBUG] Request headers: {dict(request.headers)}")
        
        # For Flask, handle file uploads directly
        if 'file' in request.files:
            uploaded_file = request.files['file']
            session_id = request.form.get('session_id', '')
            
            print(f"[DEBUG] File found: {uploaded_file.filename}")
            print(f"[DEBUG] Session ID: {session_id}")
            print(f"[DEBUG] Content type: {uploaded_file.content_type}")
            
            # Read image data
            image_data = uploaded_file.read()
            content_type = uploaded_file.content_type or 'image/jpeg'
            
            print(f"[DEBUG] Image size: {len(image_data)} bytes")
            
            # Create Lambda-style event with JSON body containing base64 image
            event = {
                'httpMethod': 'POST',
                'path': '/upload-image',
                'headers': {
                    'Content-Type': 'application/json',
                    **{k: v for k, v in request.headers.items() if k.lower() == 'authorization'}
                },
                'body': json.dumps({
                    'session_id': session_id,
                    'image_data': base64.b64encode(image_data).decode('utf-8'),
                    'content_type': content_type
                }),
                'requestContext': lambda_event_from_flask(request).get('requestContext', {})
            }
        else:
            print(f"[DEBUG] No file in request, using standard Lambda event conversion")
            event = lambda_event_from_flask(request)
        
        response = handle_upload_image(event)
        print(f"[DEBUG] Response status: {response.get('statusCode')}")
        if response.get('statusCode') >= 400:
            body = json.loads(response.get('body', '{}'))
            print(f"[DEBUG] Error response: {body}")
        return lambda_response_to_flask(response)
    except Exception as e:
        print(f"[ERROR] Upload failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'upload_failed', 'message': str(e)}), 500

@app.route('/analyze-image', methods=['POST'])
def analyze_image():
    event = lambda_event_from_flask(request)
    response = handle_analyze_image(event)
    return lambda_response_to_flask(response)

# Recipe endpoints
@app.route('/generate-recipes', methods=['POST'])
def generate_recipes():
    event = lambda_event_from_flask(request)
    response = handle_generate_recipes(event)
    return lambda_response_to_flask(response)

# Shopping list endpoint
@app.route('/generate-shopping-list', methods=['POST'])
def generate_shopping_list():
    event = lambda_event_from_flask(request)
    response = handle_generate_shopping_list(event)
    return lambda_response_to_flask(response)

# Reminder endpoints
@app.route('/reminders/<session_id>', methods=['GET'])
def get_reminders(session_id):
    event = lambda_event_from_flask(request, {'session_id': session_id})
    response = handle_get_reminders(event)
    return lambda_response_to_flask(response)

@app.route('/reminders/<reminder_id>/dismiss', methods=['POST'])
def dismiss_reminder(reminder_id):
    event = lambda_event_from_flask(request, {'reminder_id': reminder_id})
    response = handle_dismiss_reminder(event)
    return lambda_response_to_flask(response)

@app.route('/reminders/<reminder_id>/snooze', methods=['POST'])
def snooze_reminder(reminder_id):
    event = lambda_event_from_flask(request, {'reminder_id': reminder_id})
    response = handle_snooze_reminder(event)
    return lambda_response_to_flask(response)

# Health check
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'andhra-kitchen-agent'}), 200

if __name__ == '__main__':
    print("=" * 60)
    print("🍛 Andhra Kitchen Agent - Local Development Server")
    print("=" * 60)
    print("Server starting on http://localhost:5000")
    print("Make sure to:")
    print("  1. Configure AWS credentials (aws configure)")
    print("  2. Set up .env file with AWS settings")
    print("  3. Deploy AWS infrastructure (DynamoDB, S3, etc.)")
    print("=" * 60)
    
    # WARNING: host='0.0.0.0' with debug=True exposes the server and the interactive
    # debugger to the entire network. Secure alternative: bind to 127.0.0.1 only,
    # and never run debug=True outside of a fully isolated local machine.
    app.run(host='127.0.0.1', port=5000, debug=False)
