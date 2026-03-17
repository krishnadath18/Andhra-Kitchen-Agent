"""
Tests for session endpoints

Tests Requirements 16.1, 16.2, 16.3, 16.5
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone

# Import the handlers
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api_handler import (
    handle_create_session,
    handle_get_session,
    create_response
)


class TestCreateSessionEndpoint:
    """Test suite for POST /session endpoint (Task 12.7)"""
    
    @patch('src.api_handler.kitchen_agent')
    def test_create_session_default_language(self, mock_agent):
        """Requirement 16.1, 16.3: Test session creation with default language"""
        # Mock session creation
        session_id = 'sess_abc123'
        created_at = datetime.now(timezone.utc).isoformat()
        expiry_timestamp = int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
        
        mock_agent.create_session.return_value = session_id
        mock_agent.get_session.return_value = {
            'session_id': session_id,
            'data_type': 'profile',
            'user_language': 'en',
            'preferences': {},
            'allergies': [],
            'conversation_history': [],
            'created_at': created_at,
            'updated_at': created_at,
            'expiry_timestamp': expiry_timestamp
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/session',
            'body': json.dumps({}),
            'isBase64Encoded': False
        }
        
        response = handle_create_session(event)
        
        # Verify response
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        
        # Requirement 16.1: Verify unique session_id is returned
        assert body['session_id'] == session_id
        assert body['session_id'].startswith('sess_')
        
        # Requirement 16.3: Verify timestamps are returned
        assert 'created_at' in body
        assert 'expires_at' in body
        
        # Verify create_session was called with default language
        mock_agent.create_session.assert_called_once_with(
            language='en',
            owner_sub='user-123',
            owner_email='user@example.com'
        )
    
    @patch('src.api_handler.kitchen_agent')
    def test_create_session_english_language(self, mock_agent):
        """Requirement 16.1: Test session creation with English language"""
        session_id = 'sess_def456'
        created_at = datetime.now(timezone.utc).isoformat()
        expiry_timestamp = int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
        
        mock_agent.create_session.return_value = session_id
        mock_agent.get_session.return_value = {
            'session_id': session_id,
            'data_type': 'profile',
            'user_language': 'en',
            'preferences': {},
            'allergies': [],
            'conversation_history': [],
            'created_at': created_at,
            'updated_at': created_at,
            'expiry_timestamp': expiry_timestamp
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/session',
            'body': json.dumps({'language': 'en'}),
            'isBase64Encoded': False
        }
        
        response = handle_create_session(event)
        
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['session_id'] == session_id
        
        mock_agent.create_session.assert_called_once_with(
            language='en',
            owner_sub='user-123',
            owner_email='user@example.com'
        )
    
    @patch('src.api_handler.kitchen_agent')
    def test_create_session_telugu_language(self, mock_agent):
        """Requirement 16.1: Test session creation with Telugu language"""
        session_id = 'sess_ghi789'
        created_at = datetime.now(timezone.utc).isoformat()
        expiry_timestamp = int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
        
        mock_agent.create_session.return_value = session_id
        mock_agent.get_session.return_value = {
            'session_id': session_id,
            'data_type': 'profile',
            'user_language': 'te',
            'preferences': {},
            'allergies': [],
            'conversation_history': [],
            'created_at': created_at,
            'updated_at': created_at,
            'expiry_timestamp': expiry_timestamp
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/session',
            'body': json.dumps({'language': 'te'}),
            'isBase64Encoded': False
        }
        
        response = handle_create_session(event)
        
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['session_id'] == session_id
        
        mock_agent.create_session.assert_called_once_with(
            language='te',
            owner_sub='user-123',
            owner_email='user@example.com'
        )
    
    def test_create_session_invalid_language(self):
        """Test that invalid language returns 400 error"""
        event = {
            'httpMethod': 'POST',
            'path': '/session',
            'body': json.dumps({'language': 'fr'}),
            'isBase64Encoded': False
        }
        
        response = handle_create_session(event)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_language'
        assert 'en' in body['message'] and 'te' in body['message']
    
    @patch('src.api_handler.kitchen_agent')
    def test_create_session_expiry_7_days(self, mock_agent):
        """Requirement 16.3: Test that expiry_timestamp is set to 7 days from creation"""
        session_id = 'sess_jkl012'
        now = datetime.now(timezone.utc)
        created_at = now.isoformat()
        # Calculate expiry as exactly 7 days from now
        expires_at = now + timedelta(days=7)
        expiry_timestamp = int(expires_at.timestamp())
        
        mock_agent.create_session.return_value = session_id
        mock_agent.get_session.return_value = {
            'session_id': session_id,
            'data_type': 'profile',
            'user_language': 'en',
            'preferences': {},
            'allergies': [],
            'conversation_history': [],
            'created_at': created_at,
            'updated_at': created_at,
            'expiry_timestamp': expiry_timestamp
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/session',
            'body': json.dumps({}),
            'isBase64Encoded': False
        }
        
        response = handle_create_session(event)
        
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        
        # Verify session_id and timestamps are present
        assert body['session_id'] == session_id
        assert 'created_at' in body
        assert 'expires_at' in body
        
        # Parse expires_at timestamp from response
        expires_dt = datetime.fromisoformat(body['expires_at'].replace('Z', '+00:00'))
        
        # Verify the expiry timestamp matches what we set (within 1 second tolerance)
        expected_expires = datetime.fromtimestamp(expiry_timestamp, tz=timezone.utc)
        time_diff = abs((expires_dt - expected_expires).total_seconds())
        assert time_diff < 1  # Should be exact match
    
    @patch('src.api_handler.kitchen_agent')
    def test_create_session_failure(self, mock_agent):
        """Test handling of session creation failure"""
        mock_agent.create_session.side_effect = Exception("DynamoDB error")
        
        event = {
            'httpMethod': 'POST',
            'path': '/session',
            'body': json.dumps({}),
            'isBase64Encoded': False
        }
        
        response = handle_create_session(event)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['error'] == 'session_creation_failed'
    
    @patch('src.api_handler.kitchen_agent')
    def test_create_session_retrieval_failure(self, mock_agent):
        """Test handling when session retrieval fails after creation"""
        mock_agent.create_session.return_value = 'sess_xyz999'
        mock_agent.get_session.return_value = None
        
        event = {
            'httpMethod': 'POST',
            'path': '/session',
            'body': json.dumps({}),
            'isBase64Encoded': False
        }
        
        response = handle_create_session(event)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['error'] == 'session_creation_failed'


class TestGetSessionEndpoint:
    """Test suite for GET /session/{session_id} endpoint (Task 12.6)"""
    
    @patch('src.api_handler.kitchen_agent')
    def test_get_session_success(self, mock_agent):
        """Requirement 16.2, 16.5: Test successful session retrieval"""
        session_id = 'sess_abc123'
        
        mock_agent.get_session.return_value = {
            'session_id': session_id,
            'data_type': 'profile',
            'user_language': 'en',
            'preferences': {
                'low_oil': True,
                'vegetarian': True,
                'spice_level': 'medium'
            },
            'allergies': ['peanuts', 'shellfish'],
            'conversation_history': [
                {
                    'timestamp': '2024-01-15T10:30:00Z',
                    'user_message': 'What can I cook?',
                    'agent_response': 'I can help you with that!'
                }
            ],
            'created_at': '2024-01-15T10:00:00',
            'updated_at': '2024-01-15T10:30:00'
        }
        
        event = {
            'httpMethod': 'GET',
            'path': f'/session/{session_id}',
            'pathParameters': {'session_id': session_id}
        }
        
        response = handle_get_session(event)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Requirement 16.2, 16.5: Verify all required fields are returned
        assert body['session_id'] == session_id
        assert body['user_language'] == 'en'
        assert body['preferences'] == {
            'low_oil': True,
            'vegetarian': True,
            'spice_level': 'medium'
        }
        assert body['allergies'] == ['peanuts', 'shellfish']
        assert len(body['conversation_history']) == 1
        assert body['created_at'] == '2024-01-15T10:00:00'
        assert body['updated_at'] == '2024-01-15T10:30:00'
        
        # Verify get_session was called correctly
        mock_agent.get_session.assert_called_once_with(session_id)
    
    @patch('src.api_handler.kitchen_agent')
    def test_get_session_with_inventory(self, mock_agent):
        """Requirement 16.5: Test session retrieval with last_inventory"""
        session_id = 'sess_def456'
        
        mock_agent.get_session.return_value = {
            'session_id': session_id,
            'data_type': 'profile',
            'user_language': 'te',
            'preferences': {},
            'allergies': [],
            'conversation_history': [],
            'last_inventory': {
                'total_items': 3,
                'detection_timestamp': '2024-01-15T10:00:00Z',
                'ingredients': [
                    {
                        'ingredient_name': 'brinjal',
                        'quantity': 2,
                        'unit': 'pieces',
                        'confidence_score': 0.95
                    }
                ]
            },
            'created_at': '2024-01-15T09:00:00',
            'updated_at': '2024-01-15T10:00:00'
        }
        
        event = {
            'httpMethod': 'GET',
            'path': f'/session/{session_id}',
            'pathParameters': {'session_id': session_id}
        }
        
        response = handle_get_session(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Verify last_inventory is included
        assert 'last_inventory' in body
        assert body['last_inventory']['total_items'] == 3
        assert len(body['last_inventory']['ingredients']) == 1
    
    @patch('src.api_handler.kitchen_agent')
    def test_get_session_not_found(self, mock_agent):
        """Test that non-existent session returns 404"""
        session_id = 'sess_nonexistent'
        mock_agent.get_session.return_value = None
        
        event = {
            'httpMethod': 'GET',
            'path': f'/session/{session_id}',
            'pathParameters': {'session_id': session_id}
        }
        
        response = handle_get_session(event)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error'] == 'session_not_found'
        assert session_id in body['message']
    
    def test_get_session_missing_session_id(self):
        """Test that missing session_id in path returns 400"""
        event = {
            'httpMethod': 'GET',
            'path': '/session/',
            'pathParameters': {}
        }
        
        response = handle_get_session(event)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_request'
        assert 'session_id' in body['message']
    
    @patch('src.api_handler.kitchen_agent')
    def test_get_session_empty_preferences(self, mock_agent):
        """Test session with empty preferences and allergies"""
        session_id = 'sess_ghi789'
        
        mock_agent.get_session.return_value = {
            'session_id': session_id,
            'data_type': 'profile',
            'user_language': 'en',
            'preferences': {},
            'allergies': [],
            'conversation_history': [],
            'created_at': '2024-01-15T10:00:00',
            'updated_at': '2024-01-15T10:00:00'
        }
        
        event = {
            'httpMethod': 'GET',
            'path': f'/session/{session_id}',
            'pathParameters': {'session_id': session_id}
        }
        
        response = handle_get_session(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Verify empty collections are returned as empty
        assert body['preferences'] == {}
        assert body['allergies'] == []
        assert body['conversation_history'] == []
    
    @patch('src.api_handler.kitchen_agent')
    def test_get_session_retrieval_error(self, mock_agent):
        """Test handling of DynamoDB retrieval error"""
        session_id = 'sess_jkl012'
        mock_agent.get_session.side_effect = Exception("DynamoDB error")
        
        event = {
            'httpMethod': 'GET',
            'path': f'/session/{session_id}',
            'pathParameters': {'session_id': session_id}
        }
        
        response = handle_get_session(event)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['error'] == 'session_retrieval_failed'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
