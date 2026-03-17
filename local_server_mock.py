"""
Local Development Server with MOCK AWS Services

This server runs WITHOUT real AWS credentials for local testing.
Uses moto to mock AWS services (DynamoDB, S3, Bedrock).

Usage:
    python local_server_mock.py
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
from pathlib import Path
import json
from datetime import datetime, timedelta, timezone
import uuid

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up moto mocking BEFORE importing AWS services
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['AWS_SECURITY_TOKEN'] = 'testing'
os.environ['AWS_SESSION_TOKEN'] = 'testing'
os.environ['AWS_DEFAULT_REGION'] = 'ap-south-1'

from moto import mock_aws

# Start mocking AWS services
mock = mock_aws()
mock.start()

# Now import boto3 and create tables
import boto3

# Create mock DynamoDB tables
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')

# Create sessions table
sessions_table = dynamodb.create_table(
    TableName='kitchen-agent-sessions-dev',
    KeySchema=[
        {'AttributeName': 'session_id', 'KeyType': 'HASH'},
        {'AttributeName': 'data_type', 'KeyType': 'RANGE'}
    ],
    AttributeDefinitions=[
        {'AttributeName': 'session_id', 'AttributeType': 'S'},
        {'AttributeName': 'data_type', 'AttributeType': 'S'}
    ],
    BillingMode='PAY_PER_REQUEST'
)

# Create market prices table
prices_table = dynamodb.create_table(
    TableName='kitchen-agent-market-prices-dev',
    KeySchema=[
        {'AttributeName': 'ingredient_name', 'KeyType': 'HASH'},
        {'AttributeName': 'market_name', 'KeyType': 'RANGE'}
    ],
    AttributeDefinitions=[
        {'AttributeName': 'ingredient_name', 'AttributeType': 'S'},
        {'AttributeName': 'market_name', 'AttributeType': 'S'}
    ],
    BillingMode='PAY_PER_REQUEST'
)

# Create reminders table
reminders_table = dynamodb.create_table(
    TableName='kitchen-agent-reminders-dev',
    KeySchema=[
        {'AttributeName': 'session_id', 'KeyType': 'HASH'},
        {'AttributeName': 'reminder_id', 'KeyType': 'RANGE'}
    ],
    AttributeDefinitions=[
        {'AttributeName': 'session_id', 'AttributeType': 'S'},
        {'AttributeName': 'reminder_id', 'AttributeType': 'S'}
    ],
    BillingMode='PAY_PER_REQUEST'
)

# Seed some sample market prices
prices_table.put_item(Item={
    'ingredient_name': 'tomato',
    'market_name': 'rythu_bazaar_vijayawada',
    'price_per_unit': 40,
    'unit': 'kg',
    'last_updated': datetime.now(timezone.utc).isoformat() + 'Z'
})

prices_table.put_item(Item={
    'ingredient_name': 'onion',
    'market_name': 'rythu_bazaar_vijayawada',
    'price_per_unit': 30,
    'unit': 'kg',
    'last_updated': datetime.now(timezone.utc).isoformat() + 'Z'
})

prices_table.put_item(Item={
    'ingredient_name': 'rice',
    'market_name': 'rythu_bazaar_vijayawada',
    'price_per_unit': 50,
    'unit': 'kg',
    'last_updated': datetime.now(timezone.utc).isoformat() + 'Z'
})

print("✅ Mock DynamoDB tables created and seeded")

# Now import the handlers
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
CORS(app)

def lambda_event_from_flask(flask_request, path_params=None):
    """Convert Flask request to Lambda event format."""
    body = None
    if flask_request.data:
        try:
            body = flask_request.get_data(as_text=True)
        except:
            body = None
    
    event = {
        'httpMethod': flask_request.method,
        'path': flask_request.path,
        'pathParameters': path_params or {},
        'queryStringParameters': dict(flask_request.args) if flask_request.args else None,
        'headers': dict(flask_request.headers),
        'body': body
    }
    return event

def lambda_response_to_flask(lambda_response):
    """Convert Lambda response to Flask response."""
    body = lambda_response.get('body', {})
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except:
            pass
    return jsonify(body), lambda_response.get('statusCode', 200)

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
    event = lambda_event_from_flask(request)
    response = handle_upload_image(event)
    return lambda_response_to_flask(response)

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
    return jsonify({
        'status': 'healthy',
        'service': 'andhra-kitchen-agent',
        'mode': 'MOCK (No AWS credentials needed)'
    }), 200

if __name__ == '__main__':
    print("=" * 60)
    print("🍛 Andhra Kitchen Agent - MOCK Development Server")
    print("=" * 60)
    print("✅ Running in MOCK mode - No AWS credentials needed!")
    print("✅ Using moto to simulate AWS services")
    print("✅ DynamoDB tables created in memory")
    print("=" * 60)
    print("Server starting on http://localhost:5000")
    print("=" * 60)
    print("\n⚠️  NOTE: Bedrock AI features will return mock responses")
    print("⚠️  This is for UI/UX testing only\n")
    
    # WARNING: Never use debug=True with host='0.0.0.0' in production.
    # This exposes the interactive debugger to the network, allowing
    # arbitrary code execution. For local testing only, bind to 127.0.0.1.
    # SECURE ALTERNATIVE: app.run(host='127.0.0.1', port=5000, debug=False)
    app.run(host='127.0.0.1', port=5000, debug=False)
