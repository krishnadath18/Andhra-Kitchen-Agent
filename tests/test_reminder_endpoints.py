"""
Unit tests for reminder management API endpoints

Tests for Tasks 12.8, 12.9, 12.10:
- GET /reminders/{session_id}
- POST /reminders/{reminder_id}/dismiss
- POST /reminders/{reminder_id}/snooze
"""

import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api_handler import (
    handle_get_reminders,
    handle_dismiss_reminder,
    handle_snooze_reminder
)


class TestGetRemindersEndpoint:
    """Test GET /reminders/{session_id} endpoint"""
    
    @patch('src.api_handler.reminder_service')
    def test_get_reminders_success(self, mock_reminder_service):
        """Test successful retrieval of reminders"""
        # Arrange
        session_id = "sess_test123"
        mock_reminders = [
            {
                'reminder_id': 'rem_001',
                'content': 'Buy curry leaves tomorrow',
                'reason': 'Fresh stock arrives on Wednesdays',
                'trigger_time': '2024-01-17T08:00:00Z',
                'status': 'pending',
                'reminder_type': 'shopping',
                'created_at': '2024-01-15T10:00:00Z'
            },
            {
                'reminder_id': 'rem_002',
                'content': 'Buy vegetables at Rythu Bazaar',
                'reason': 'Weekend prices are 20% cheaper',
                'trigger_time': '2024-01-20T08:00:00Z',
                'status': 'delivered',
                'reminder_type': 'shopping',
                'created_at': '2024-01-15T10:05:00Z'
            }
        ]
        mock_reminder_service.get_pending_reminders.return_value = mock_reminders
        
        event = {
            'httpMethod': 'GET',
            'path': f'/reminders/{session_id}',
            'headers': {},
            'body': None
        }
        
        # Act
        response = handle_get_reminders(event)
        
        # Assert
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['session_id'] == session_id
        assert body['count'] == 2
        assert len(body['reminders']) == 2
        assert body['reminders'][0]['reminder_id'] == 'rem_001'
        assert body['reminders'][1]['reminder_id'] == 'rem_002'
        
        # Verify service was called correctly
        mock_reminder_service.get_pending_reminders.assert_called_once_with(session_id)
    
    @patch('src.api_handler.reminder_service')
    def test_get_reminders_empty_list(self, mock_reminder_service):
        """Test retrieval when no reminders exist"""
        # Arrange
        session_id = "sess_test123"
        mock_reminder_service.get_pending_reminders.return_value = []
        
        event = {
            'httpMethod': 'GET',
            'path': f'/reminders/{session_id}',
            'headers': {},
            'body': None
        }
        
        # Act
        response = handle_get_reminders(event)
        
        # Assert
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['count'] == 0
        assert body['reminders'] == []
    
    def test_get_reminders_missing_session_id(self):
        """Test error when session_id is missing from path"""
        # Arrange
        event = {
            'httpMethod': 'GET',
            'path': '/reminders/',
            'headers': {},
            'body': None
        }
        
        # Act
        response = handle_get_reminders(event)
        
        # Assert
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_request'
        assert 'session_id' in body['message']
    
    @patch('src.api_handler.reminder_service')
    def test_get_reminders_service_error(self, mock_reminder_service):
        """Test error handling when service fails"""
        # Arrange
        session_id = "sess_test123"
        mock_reminder_service.get_pending_reminders.side_effect = Exception("DynamoDB error")
        
        event = {
            'httpMethod': 'GET',
            'path': f'/reminders/{session_id}',
            'headers': {},
            'body': None
        }
        
        # Act
        response = handle_get_reminders(event)
        
        # Assert
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['error'] == 'reminder_retrieval_failed'


class TestDismissReminderEndpoint:
    """Test POST /reminders/{reminder_id}/dismiss endpoint"""
    
    @patch('src.api_handler.reminder_service')
    def test_dismiss_reminder_success(self, mock_reminder_service):
        """Test successful dismissal of reminder"""
        # Arrange
        session_id = "sess_test123"
        reminder_id = "rem_001"
        
        mock_updated_reminder = {
            'reminder_id': reminder_id,
            'content': 'Buy curry leaves tomorrow',
            'reason': 'Fresh stock arrives on Wednesdays',
            'trigger_time': '2024-01-17T08:00:00Z',
            'status': 'dismissed',
            'reminder_type': 'shopping',
            'created_at': '2024-01-15T10:00:00Z',
            'updated_at': '2024-01-16T12:00:00Z'
        }
        mock_reminder_service.dismiss_reminder.return_value = mock_updated_reminder
        
        event = {
            'httpMethod': 'POST',
            'path': f'/reminders/{reminder_id}/dismiss',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'session_id': session_id})
        }
        
        # Act
        response = handle_dismiss_reminder(event)
        
        # Assert
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['session_id'] == session_id
        assert body['reminder']['reminder_id'] == reminder_id
        assert body['reminder']['status'] == 'dismissed'
        assert 'dismissed successfully' in body['message']
        
        # Verify service was called correctly
        mock_reminder_service.dismiss_reminder.assert_called_once_with(
            reminder_id=reminder_id,
            session_id=session_id
        )
    
    def test_dismiss_reminder_missing_session_id(self):
        """Test error when session_id is missing from body"""
        # Arrange
        reminder_id = "rem_001"
        event = {
            'httpMethod': 'POST',
            'path': f'/reminders/{reminder_id}/dismiss',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({})
        }
        
        # Act
        response = handle_dismiss_reminder(event)
        
        # Assert
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_request'
        assert 'session_id' in body['message']
    
    def test_dismiss_reminder_missing_reminder_id(self):
        """Test error when reminder_id is missing from path"""
        # Arrange
        event = {
            'httpMethod': 'POST',
            'path': '/reminders//dismiss',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'session_id': 'sess_test123'})
        }
        
        # Act
        response = handle_dismiss_reminder(event)
        
        # Assert
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_request'
    
    @patch('src.api_handler.reminder_service')
    def test_dismiss_reminder_not_found(self, mock_reminder_service):
        """Test error when reminder doesn't exist"""
        # Arrange
        session_id = "sess_test123"
        reminder_id = "rem_nonexistent"
        mock_reminder_service.dismiss_reminder.side_effect = ValueError("Reminder not found")
        
        event = {
            'httpMethod': 'POST',
            'path': f'/reminders/{reminder_id}/dismiss',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'session_id': session_id})
        }
        
        # Act
        response = handle_dismiss_reminder(event)
        
        # Assert
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error'] == 'reminder_not_found'


class TestSnoozeReminderEndpoint:
    """Test POST /reminders/{reminder_id}/snooze endpoint"""
    
    @patch('src.api_handler.reminder_service')
    def test_snooze_reminder_success(self, mock_reminder_service):
        """Test successful snoozing of reminder"""
        # Arrange
        session_id = "sess_test123"
        reminder_id = "rem_001"
        duration_hours = 2
        
        new_trigger_time = (datetime.now(timezone.utc) + timedelta(hours=duration_hours)).isoformat() + 'Z'
        mock_updated_reminder = {
            'reminder_id': reminder_id,
            'content': 'Buy curry leaves tomorrow',
            'reason': 'Fresh stock arrives on Wednesdays',
            'trigger_time': new_trigger_time,
            'status': 'snoozed',
            'reminder_type': 'shopping',
            'created_at': '2024-01-15T10:00:00Z',
            'updated_at': '2024-01-16T12:00:00Z'
        }
        mock_reminder_service.snooze_reminder.return_value = mock_updated_reminder
        
        event = {
            'httpMethod': 'POST',
            'path': f'/reminders/{reminder_id}/snooze',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'session_id': session_id,
                'duration_hours': duration_hours
            })
        }
        
        # Act
        response = handle_snooze_reminder(event)
        
        # Assert
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['session_id'] == session_id
        assert body['reminder']['reminder_id'] == reminder_id
        assert body['reminder']['status'] == 'snoozed'
        assert 'hours' in body['message']
        assert 'snoozed' in body['message'].lower()
        
        # Verify service was called correctly
        mock_reminder_service.snooze_reminder.assert_called_once()
        call_args = mock_reminder_service.snooze_reminder.call_args
        assert call_args.kwargs['reminder_id'] == reminder_id
        assert call_args.kwargs['session_id'] == session_id
        assert isinstance(call_args.kwargs['duration'], timedelta)
    
    def test_snooze_reminder_missing_session_id(self):
        """Test error when session_id is missing from body"""
        # Arrange
        reminder_id = "rem_001"
        event = {
            'httpMethod': 'POST',
            'path': f'/reminders/{reminder_id}/snooze',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'duration_hours': 2})
        }
        
        # Act
        response = handle_snooze_reminder(event)
        
        # Assert
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_request'
        assert 'session_id' in body['message']
    
    def test_snooze_reminder_missing_duration(self):
        """Test error when duration_hours is missing from body"""
        # Arrange
        reminder_id = "rem_001"
        event = {
            'httpMethod': 'POST',
            'path': f'/reminders/{reminder_id}/snooze',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'session_id': 'sess_test123'})
        }
        
        # Act
        response = handle_snooze_reminder(event)
        
        # Assert
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_request'
        assert 'duration_hours' in body['message']
    
    def test_snooze_reminder_invalid_duration(self):
        """Test error when duration_hours is not a positive number"""
        # Arrange
        reminder_id = "rem_001"
        event = {
            'httpMethod': 'POST',
            'path': f'/reminders/{reminder_id}/snooze',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'session_id': 'sess_test123',
                'duration_hours': -1
            })
        }
        
        # Act
        response = handle_snooze_reminder(event)
        
        # Assert
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_duration'
    
    @patch('src.api_handler.reminder_service')
    def test_snooze_reminder_not_found(self, mock_reminder_service):
        """Test error when reminder doesn't exist"""
        # Arrange
        session_id = "sess_test123"
        reminder_id = "rem_nonexistent"
        mock_reminder_service.snooze_reminder.side_effect = ValueError("Reminder not found")
        
        event = {
            'httpMethod': 'POST',
            'path': f'/reminders/{reminder_id}/snooze',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'session_id': session_id,
                'duration_hours': 2
            })
        }
        
        # Act
        response = handle_snooze_reminder(event)
        
        # Assert
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error'] == 'reminder_not_found'
    
    @patch('src.api_handler.reminder_service')
    def test_snooze_reminder_with_float_duration(self, mock_reminder_service):
        """Test snoozing with fractional hours (e.g., 1.5 hours)"""
        # Arrange
        session_id = "sess_test123"
        reminder_id = "rem_001"
        duration_hours = 1.5
        
        new_trigger_time = (datetime.now(timezone.utc) + timedelta(hours=duration_hours)).isoformat() + 'Z'
        mock_updated_reminder = {
            'reminder_id': reminder_id,
            'content': 'Buy curry leaves tomorrow',
            'reason': 'Fresh stock arrives on Wednesdays',
            'trigger_time': new_trigger_time,
            'status': 'snoozed',
            'reminder_type': 'shopping',
            'created_at': '2024-01-15T10:00:00Z',
            'updated_at': '2024-01-16T12:00:00Z'
        }
        mock_reminder_service.snooze_reminder.return_value = mock_updated_reminder
        
        event = {
            'httpMethod': 'POST',
            'path': f'/reminders/{reminder_id}/snooze',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'session_id': session_id,
                'duration_hours': duration_hours
            })
        }
        
        # Act
        response = handle_snooze_reminder(event)
        
        # Assert
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['reminder']['status'] == 'snoozed'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
