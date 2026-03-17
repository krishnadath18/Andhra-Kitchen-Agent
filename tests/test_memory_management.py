"""
Unit tests for memory management in AgentCoreOrchestrator

Tests the store_memory() and retrieve_memory() methods that handle:
- Storing preferences with session_id association
- Storing allergies with high priority flag
- Retrieving memory by key and data_type
- 7-day TTL configuration
- Error handling and CloudWatch logging

Requirements: 7.1, 7.2, 7.3, 7.7, 16.3
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agentcore_orchestrator import AgentCoreOrchestrator
from botocore.exceptions import ClientError


class TestMemoryManagement(unittest.TestCase):
    """Test memory management functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock AWS clients
        self.mock_bedrock = Mock()
        self.mock_dynamodb = Mock()
        self.mock_sessions_table = Mock()
        
        # Patch boto3 clients
        self.bedrock_patcher = patch('boto3.client')
        self.dynamodb_patcher = patch('boto3.resource')
        
        self.mock_boto_client = self.bedrock_patcher.start()
        self.mock_boto_resource = self.dynamodb_patcher.start()
        
        # Configure mocks
        self.mock_boto_client.return_value = self.mock_bedrock
        self.mock_boto_resource.return_value = self.mock_dynamodb
        self.mock_dynamodb.Table.return_value = self.mock_sessions_table
        
        # Create orchestrator instance
        self.orchestrator = AgentCoreOrchestrator()
        
        # Test data
        self.test_session_id = 'sess_test123'
        self.test_ttl_days = 7
    
    def tearDown(self):
        """Clean up patches"""
        self.bedrock_patcher.stop()
        self.dynamodb_patcher.stop()
    
    # Test store_memory() functionality
    
    def test_store_preference_success(self):
        """Test storing a preference successfully"""
        # Arrange
        key = 'low_oil'
        value = True
        data_type = 'preferences'
        
        # Act
        result = self.orchestrator.store_memory(
            session_id=self.test_session_id,
            key=key,
            value=value,
            data_type=data_type,
            high_priority=False
        )
        
        # Assert
        self.assertTrue(result)
        self.mock_sessions_table.put_item.assert_called_once()
        
        # Verify the item structure
        call_args = self.mock_sessions_table.put_item.call_args
        item = call_args[1]['Item']
        
        self.assertEqual(item['session_id'], self.test_session_id)
        self.assertEqual(item['data_type'], data_type)
        self.assertEqual(item['key'], key)
        self.assertEqual(item['value'], value)
        self.assertFalse(item['high_priority'])
        self.assertIn('created_at', item)
        self.assertIn('updated_at', item)
        self.assertIn('expiry_timestamp', item)
    
    def test_store_allergy_with_high_priority(self):
        """Test storing an allergy with high priority flag"""
        # Arrange
        key = 'peanuts'
        value = True
        data_type = 'allergies'
        
        # Act
        result = self.orchestrator.store_memory(
            session_id=self.test_session_id,
            key=key,
            value=value,
            data_type=data_type,
            high_priority=True
        )
        
        # Assert
        self.assertTrue(result)
        
        # Verify high priority flag is set
        call_args = self.mock_sessions_table.put_item.call_args
        item = call_args[1]['Item']
        
        self.assertEqual(item['data_type'], 'allergies')
        self.assertTrue(item['high_priority'])
    
    def test_store_memory_ttl_configuration(self):
        """Test that TTL is set to 7 days from current time"""
        # Arrange
        key = 'vegetarian'
        value = True
        
        # Capture current time before call
        before_time = datetime.now(timezone.utc)
        
        # Act
        result = self.orchestrator.store_memory(
            session_id=self.test_session_id,
            key=key,
            value=value,
            data_type='preferences'
        )
        
        # Capture time after call
        after_time = datetime.now(timezone.utc)
        
        # Assert
        self.assertTrue(result)
        
        # Verify TTL is approximately 7 days from now
        call_args = self.mock_sessions_table.put_item.call_args
        item = call_args[1]['Item']
        ttl = item['expiry_timestamp']
        
        # Calculate expected TTL range
        expected_ttl_min = int((before_time + timedelta(days=7)).timestamp())
        expected_ttl_max = int((after_time + timedelta(days=7)).timestamp())
        
        self.assertGreaterEqual(ttl, expected_ttl_min)
        self.assertLessEqual(ttl, expected_ttl_max)
    
    def test_store_memory_session_association(self):
        """Test that memory is associated with session_id"""
        # Arrange
        session_id_1 = 'sess_user1'
        session_id_2 = 'sess_user2'
        key = 'spice_level'
        value = 'medium'
        
        # Act
        result1 = self.orchestrator.store_memory(session_id_1, key, value, 'preferences')
        result2 = self.orchestrator.store_memory(session_id_2, key, value, 'preferences')
        
        # Assert
        self.assertTrue(result1)
        self.assertTrue(result2)
        self.assertEqual(self.mock_sessions_table.put_item.call_count, 2)
        
        # Verify different session_ids were used
        calls = self.mock_sessions_table.put_item.call_args_list
        self.assertEqual(calls[0][1]['Item']['session_id'], session_id_1)
        self.assertEqual(calls[1][1]['Item']['session_id'], session_id_2)
    
    def test_store_memory_complex_value(self):
        """Test storing complex data structures"""
        # Arrange
        key = 'favorite_dishes'
        value = ['biryani', 'dosa', 'sambar']
        
        # Act
        result = self.orchestrator.store_memory(
            session_id=self.test_session_id,
            key=key,
            value=value,
            data_type='preferences'
        )
        
        # Assert
        self.assertTrue(result)
        
        call_args = self.mock_sessions_table.put_item.call_args
        item = call_args[1]['Item']
        self.assertEqual(item['value'], value)
    
    def test_store_memory_dynamodb_error(self):
        """Test error handling when DynamoDB put_item fails"""
        # Arrange
        self.mock_sessions_table.put_item.side_effect = ClientError(
            {'Error': {'Code': 'ProvisionedThroughputExceededException', 'Message': 'Throttled'}},
            'PutItem'
        )
        
        # Act
        result = self.orchestrator.store_memory(
            session_id=self.test_session_id,
            key='test_key',
            value='test_value',
            data_type='preferences'
        )
        
        # Assert
        self.assertFalse(result)
    
    def test_store_memory_unexpected_error(self):
        """Test error handling for unexpected exceptions"""
        # Arrange
        self.mock_sessions_table.put_item.side_effect = Exception("Unexpected error")
        
        # Act
        result = self.orchestrator.store_memory(
            session_id=self.test_session_id,
            key='test_key',
            value='test_value',
            data_type='preferences'
        )
        
        # Assert
        self.assertFalse(result)
    
    # Test retrieve_memory() functionality
    
    def test_retrieve_specific_preference(self):
        """Test retrieving a specific preference by key"""
        # Arrange
        key = 'low_oil'
        expected_value = True
        
        self.mock_sessions_table.get_item.return_value = {
            'Item': {
                'session_id': self.test_session_id,
                'data_type': 'preferences',
                'key': key,
                'value': expected_value,
                'high_priority': False
            }
        }
        
        # Act
        result = self.orchestrator.retrieve_memory(
            session_id=self.test_session_id,
            key=key,
            data_type='preferences'
        )
        
        # Assert
        self.assertEqual(result, expected_value)
        self.mock_sessions_table.get_item.assert_called_once_with(
            Key={
                'session_id': self.test_session_id,
                'data_type': 'preferences'
            }
        )
    
    def test_retrieve_specific_allergy(self):
        """Test retrieving a specific allergy by key"""
        # Arrange
        key = 'peanuts'
        expected_value = True
        
        self.mock_sessions_table.get_item.return_value = {
            'Item': {
                'session_id': self.test_session_id,
                'data_type': 'allergies',
                'key': key,
                'value': expected_value,
                'high_priority': True
            }
        }
        
        # Act
        result = self.orchestrator.retrieve_memory(
            session_id=self.test_session_id,
            key=key,
            data_type='allergies'
        )
        
        # Assert
        self.assertEqual(result, expected_value)
    
    def test_retrieve_memory_not_found(self):
        """Test retrieving memory that doesn't exist"""
        # Arrange
        self.mock_sessions_table.get_item.return_value = {}
        
        # Act
        result = self.orchestrator.retrieve_memory(
            session_id=self.test_session_id,
            key='nonexistent_key',
            data_type='preferences'
        )
        
        # Assert
        self.assertIsNone(result)
    
    def test_retrieve_all_preferences(self):
        """Test retrieving all preferences for a session"""
        # Arrange
        self.mock_sessions_table.query.return_value = {
            'Items': [
                {
                    'session_id': self.test_session_id,
                    'data_type': 'preferences',
                    'key': 'low_oil',
                    'value': True
                },
                {
                    'session_id': self.test_session_id,
                    'data_type': 'preferences',
                    'key': 'vegetarian',
                    'value': True
                },
                {
                    'session_id': self.test_session_id,
                    'data_type': 'preferences',
                    'key': 'spice_level',
                    'value': 'medium'
                }
            ]
        }
        
        # Act
        result = self.orchestrator.retrieve_memory(
            session_id=self.test_session_id,
            data_type='preferences'
        )
        
        # Assert
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 3)
        self.assertTrue(result['low_oil'])
        self.assertTrue(result['vegetarian'])
        self.assertEqual(result['spice_level'], 'medium')
    
    def test_retrieve_all_allergies(self):
        """Test retrieving all allergies for a session"""
        # Arrange
        self.mock_sessions_table.query.return_value = {
            'Items': [
                {
                    'session_id': self.test_session_id,
                    'data_type': 'allergies',
                    'key': 'peanuts',
                    'value': True,
                    'high_priority': True
                },
                {
                    'session_id': self.test_session_id,
                    'data_type': 'allergies',
                    'key': 'shellfish',
                    'value': True,
                    'high_priority': True
                }
            ]
        }
        
        # Act
        result = self.orchestrator.retrieve_memory(
            session_id=self.test_session_id,
            data_type='allergies'
        )
        
        # Assert
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 2)
        self.assertTrue(result['peanuts'])
        self.assertTrue(result['shellfish'])
    
    def test_retrieve_all_memory_items(self):
        """Test retrieving all memory items for a session"""
        # Arrange
        self.mock_sessions_table.query.return_value = {
            'Items': [
                {
                    'session_id': self.test_session_id,
                    'data_type': 'preferences',
                    'key': 'low_oil',
                    'value': True
                },
                {
                    'session_id': self.test_session_id,
                    'data_type': 'allergies',
                    'key': 'peanuts',
                    'value': True
                }
            ]
        }
        
        # Act
        result = self.orchestrator.retrieve_memory(
            session_id=self.test_session_id
        )
        
        # Assert
        self.assertIsInstance(result, dict)
        self.assertIn('preferences', result)
        self.assertIn('allergies', result)
        self.assertTrue(result['preferences']['low_oil'])
        self.assertTrue(result['allergies']['peanuts'])
    
    def test_retrieve_memory_dynamodb_error(self):
        """Test error handling when DynamoDB query fails"""
        # Arrange
        self.mock_sessions_table.query.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Table not found'}},
            'Query'
        )
        
        # Act
        result = self.orchestrator.retrieve_memory(
            session_id=self.test_session_id,
            data_type='preferences'
        )
        
        # Assert
        self.assertIsNone(result)
    
    def test_retrieve_memory_unexpected_error(self):
        """Test error handling for unexpected exceptions"""
        # Arrange
        self.mock_sessions_table.get_item.side_effect = Exception("Unexpected error")
        
        # Act
        result = self.orchestrator.retrieve_memory(
            session_id=self.test_session_id,
            key='test_key',
            data_type='preferences'
        )
        
        # Assert
        self.assertIsNone(result)
    
    # Integration tests
    
    def test_store_and_retrieve_preference_workflow(self):
        """Test complete workflow of storing and retrieving a preference"""
        # Arrange
        key = 'low_oil'
        value = True
        
        # Mock successful store
        self.mock_sessions_table.put_item.return_value = {}
        
        # Mock successful retrieve
        self.mock_sessions_table.get_item.return_value = {
            'Item': {
                'session_id': self.test_session_id,
                'data_type': 'preferences',
                'key': key,
                'value': value
            }
        }
        
        # Act
        store_result = self.orchestrator.store_memory(
            session_id=self.test_session_id,
            key=key,
            value=value,
            data_type='preferences'
        )
        
        retrieve_result = self.orchestrator.retrieve_memory(
            session_id=self.test_session_id,
            key=key,
            data_type='preferences'
        )
        
        # Assert
        self.assertTrue(store_result)
        self.assertEqual(retrieve_result, value)
    
    def test_store_and_retrieve_allergy_workflow(self):
        """Test complete workflow of storing and retrieving an allergy"""
        # Arrange
        key = 'peanuts'
        value = True
        
        # Mock successful store
        self.mock_sessions_table.put_item.return_value = {}
        
        # Mock successful retrieve
        self.mock_sessions_table.get_item.return_value = {
            'Item': {
                'session_id': self.test_session_id,
                'data_type': 'allergies',
                'key': key,
                'value': value,
                'high_priority': True
            }
        }
        
        # Act
        store_result = self.orchestrator.store_memory(
            session_id=self.test_session_id,
            key=key,
            value=value,
            data_type='allergies',
            high_priority=True
        )
        
        retrieve_result = self.orchestrator.retrieve_memory(
            session_id=self.test_session_id,
            key=key,
            data_type='allergies'
        )
        
        # Assert
        self.assertTrue(store_result)
        self.assertEqual(retrieve_result, value)
    
    def test_multiple_sessions_isolation(self):
        """Test that memory is isolated between different sessions"""
        # Arrange
        session_1 = 'sess_user1'
        session_2 = 'sess_user2'
        key = 'low_oil'
        
        # Mock store for both sessions
        self.mock_sessions_table.put_item.return_value = {}
        
        # Mock retrieve for session 1
        def mock_get_item(Key):
            if Key['session_id'] == session_1:
                return {
                    'Item': {
                        'session_id': session_1,
                        'data_type': 'preferences',
                        'key': key,
                        'value': True
                    }
                }
            else:
                return {
                    'Item': {
                        'session_id': session_2,
                        'data_type': 'preferences',
                        'key': key,
                        'value': False
                    }
                }
        
        self.mock_sessions_table.get_item.side_effect = mock_get_item
        
        # Act
        self.orchestrator.store_memory(session_1, key, True, 'preferences')
        self.orchestrator.store_memory(session_2, key, False, 'preferences')
        
        result_1 = self.orchestrator.retrieve_memory(session_1, key, 'preferences')
        result_2 = self.orchestrator.retrieve_memory(session_2, key, 'preferences')
        
        # Assert
        self.assertTrue(result_1)
        self.assertFalse(result_2)


if __name__ == '__main__':
    unittest.main()
