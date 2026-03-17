"""
Unit tests for ReminderService

Tests basic functionality of reminder scheduling, storage, and management.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.reminder_service import ReminderService
from config.env import Config


class TestReminderServiceBasic(unittest.TestCase):
    """Test basic ReminderService functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock AWS clients to avoid actual AWS calls
        self.mock_dynamodb = Mock()
        self.mock_eventbridge = Mock()
        self.mock_table = Mock()
        
        with patch('boto3.resource') as mock_resource, \
             patch('boto3.client') as mock_client:
            mock_resource.return_value.Table.return_value = self.mock_table
            mock_client.return_value = self.mock_eventbridge
            self.service = ReminderService()
            self.service.reminders_table = self.mock_table
            self.service.eventbridge = self.mock_eventbridge
    
    def test_initialization(self):
        """Test that ReminderService initializes correctly"""
        self.assertIsNotNone(self.service)
        self.assertEqual(len(self.service.price_sensitive_ingredients), 4)
        self.assertIn("curry_leaves", self.service.price_sensitive_ingredients)
    
    def test_store_reminder(self):
        """Test storing a reminder in DynamoDB"""
        reminder = {
            "session_id": "test_session",
            "reminder_id": "test_reminder",
            "content": "Test reminder",
            "reason": "Test reason",
            "trigger_time": datetime.now(timezone.utc).isoformat() + "Z",
            "status": "pending"
        }
        
        self.service.store_reminder(reminder)
        
        # Verify DynamoDB put_item was called
        self.mock_table.put_item.assert_called_once()
        call_args = self.mock_table.put_item.call_args
        stored_item = call_args[1]['Item']
        
        # Verify TTL was added
        self.assertIn('expiry_timestamp', stored_item)
        self.assertEqual(stored_item['session_id'], 'test_session')
        self.assertEqual(stored_item['reminder_id'], 'test_reminder')
    
    def test_get_pending_reminders(self):
        """Test retrieving pending reminders"""
        # Mock DynamoDB response
        self.mock_table.query.return_value = {
            'Items': [
                {
                    'session_id': 'test_session',
                    'reminder_id': 'rem_1',
                    'content': 'Reminder 1',
                    'status': 'pending'
                },
                {
                    'session_id': 'test_session',
                    'reminder_id': 'rem_2',
                    'content': 'Reminder 2',
                    'status': 'delivered'
                }
            ]
        }
        
        reminders = self.service.get_pending_reminders('test_session')
        
        # Verify query was called
        self.mock_table.query.assert_called_once()
        
        # Verify results
        self.assertEqual(len(reminders), 2)
        self.assertEqual(reminders[0]['reminder_id'], 'rem_1')
        self.assertEqual(reminders[1]['reminder_id'], 'rem_2')
    
    def test_dismiss_reminder(self):
        """Test dismissing a reminder"""
        self.mock_table.update_item.return_value = {
            'Attributes': {
                'session_id': 'test_session',
                'reminder_id': 'test_reminder',
                'status': 'dismissed'
            }
        }
        
        result = self.service.dismiss_reminder('test_reminder', 'test_session')
        
        # Verify update was called
        self.mock_table.update_item.assert_called_once()
        
        # Verify result
        self.assertEqual(result['status'], 'dismissed')

    def test_dismiss_reminder_not_found(self):
        """Missing reminders should raise ValueError instead of upserting."""
        self.mock_table.update_item.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'ConditionalCheckFailedException',
                    'Message': 'Not found'
                }
            },
            'UpdateItem'
        )

        with self.assertRaises(ValueError):
            self.service.dismiss_reminder('missing', 'test_session')
    
    def test_detect_price_sensitive_items(self):
        """Test detecting price-sensitive ingredients"""
        shopping_items = [
            {
                'ingredient_name': 'curry_leaves',
                'market_section': 'spices',
                'quantity': 1,
                'unit': 'bunch'
            },
            {
                'ingredient_name': 'rice',
                'market_section': 'grains',
                'quantity': 1,
                'unit': 'kg'
            },
            {
                'ingredient_name': 'brinjal',
                'market_section': 'vegetables',
                'quantity': 3,
                'unit': 'pieces'
            }
        ]
        
        suggestions = self.service.detect_price_sensitive_items(shopping_items)
        
        # Should detect curry_leaves and vegetables as price-sensitive
        self.assertGreaterEqual(len(suggestions), 2)
        
        # Verify suggestion structure
        for suggestion in suggestions:
            self.assertIn('ingredient', suggestion)
            self.assertIn('content', suggestion)
            self.assertIn('reason', suggestion)
            self.assertIn('trigger_time', suggestion)
            self.assertIn('reminder_type', suggestion)
    
    def test_get_next_optimal_day(self):
        """Test calculating next optimal shopping day"""
        # Test with Wednesday as optimal day
        next_day = self.service._get_next_optimal_day(['wednesday'])
        
        # Should return a datetime
        self.assertIsInstance(next_day, datetime)
        
        # Should be set to 8:00 AM
        self.assertEqual(next_day.hour, 8)
        self.assertEqual(next_day.minute, 0)
        
        # Should be a Wednesday
        self.assertEqual(next_day.strftime('%A').lower(), 'wednesday')
    
    def test_schedule_reminder_creates_eventbridge_rule(self):
        """Test that scheduling a reminder creates an EventBridge rule"""
        trigger_time = datetime.now(timezone.utc) + timedelta(days=1)
        
        # Mock successful operations
        self.mock_table.put_item.return_value = {}
        self.mock_eventbridge.put_rule.return_value = {}
        self.mock_eventbridge.put_targets.return_value = {}
        
        # Set Lambda ARN for testing
        self.service.lambda_arn = "arn:aws:lambda:ap-south-1:123456789012:function:test"
        
        reminder_id = self.service.schedule_reminder(
            session_id='test_session',
            content='Test reminder',
            trigger_time=trigger_time,
            reason='Test reason'
        )
        
        # Verify reminder ID was generated
        self.assertTrue(reminder_id.startswith('rem_'))
        
        # Verify DynamoDB put_item was called
        self.mock_table.put_item.assert_called_once()
        
        # Verify EventBridge put_rule was called
        self.mock_eventbridge.put_rule.assert_called_once()


class TestReminderServicePriceSensitivity(unittest.TestCase):
    """Test price-sensitive ingredient detection"""
    
    def setUp(self):
        """Set up test fixtures"""
        with patch('boto3.resource'), patch('boto3.client'):
            self.service = ReminderService()
    
    def test_curry_leaves_price_sensitivity(self):
        """Test that curry leaves are detected as price-sensitive"""
        items = [{'ingredient_name': 'curry_leaves', 'market_section': 'spices'}]
        suggestions = self.service.detect_price_sensitive_items(items)
        
        self.assertEqual(len(suggestions), 1)
        self.assertIn('curry_leaves', suggestions[0]['ingredient'])
        self.assertIn('wednesday', suggestions[0]['reason'].lower())
    
    def test_vegetables_price_sensitivity(self):
        """Test that vegetables section is detected as price-sensitive"""
        items = [{'ingredient_name': 'brinjal', 'market_section': 'vegetables'}]
        suggestions = self.service.detect_price_sensitive_items(items)
        
        self.assertEqual(len(suggestions), 1)
        self.assertIn('rythu bazaar', suggestions[0]['reason'].lower())
    
    def test_non_price_sensitive_items(self):
        """Test that non-price-sensitive items don't generate suggestions"""
        items = [
            {'ingredient_name': 'salt', 'market_section': 'condiments'},
            {'ingredient_name': 'rice', 'market_section': 'grains'}
        ]
        suggestions = self.service.detect_price_sensitive_items(items)
        
        # Salt and rice (grains) are not in price-sensitive list
        self.assertEqual(len(suggestions), 0)


if __name__ == '__main__':
    unittest.main()
