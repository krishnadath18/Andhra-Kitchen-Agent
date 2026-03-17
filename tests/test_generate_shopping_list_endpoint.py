"""
Unit tests for POST /generate-shopping-list endpoint

Tests the API handler for shopping list generation endpoint.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone

# Import the handler
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api_handler import handle_generate_shopping_list, lambda_handler


class TestGenerateShoppingListEndpoint:
    """Test suite for POST /generate-shopping-list endpoint"""
    
    def test_missing_session_id(self):
        """Test that missing session_id returns 400 error"""
        event = {
            'httpMethod': 'POST',
            'path': '/generate-shopping-list',
            'body': json.dumps({
                'recipe_id': 'recipe_test_001'
            })
        }
        
        response = handle_generate_shopping_list(event)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_request'
        assert 'session_id' in body['message']
    
    def test_missing_recipe_id(self):
        """Test that missing recipe_id returns 400 error"""
        event = {
            'httpMethod': 'POST',
            'path': '/generate-shopping-list',
            'body': json.dumps({
                'session_id': 'test_session_123'
            })
        }
        
        response = handle_generate_shopping_list(event)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_request'
        assert 'recipe_id' in body['message']
    
    def test_invalid_language(self):
        """Test that invalid language returns 400 error"""
        event = {
            'httpMethod': 'POST',
            'path': '/generate-shopping-list',
            'body': json.dumps({
                'session_id': 'test_session_123',
                'recipe_id': 'recipe_test_001',
                'language': 'fr'
            })
        }
        
        response = handle_generate_shopping_list(event)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_language'
    
    @patch('src.api_handler.kitchen_agent')
    def test_session_not_found(self, mock_kitchen_agent):
        """Test that non-existent session returns 404 error"""
        mock_kitchen_agent.get_session.return_value = None
        
        event = {
            'httpMethod': 'POST',
            'path': '/generate-shopping-list',
            'body': json.dumps({
                'session_id': 'nonexistent_session',
                'recipe_id': 'recipe_test_001'
            })
        }
        
        response = handle_generate_shopping_list(event)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error'] == 'session_not_found'
    
    @patch('src.api_handler.kitchen_agent')
    def test_recipe_not_found(self, mock_kitchen_agent):
        """Test that non-existent recipe returns 404 error"""
        mock_kitchen_agent.get_session.return_value = {
            'session_id': 'test_session_123',
            'last_recipes': [
                {'recipe_id': 'recipe_other_001', 'name': 'Other Recipe'}
            ]
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/generate-shopping-list',
            'body': json.dumps({
                'session_id': 'test_session_123',
                'recipe_id': 'recipe_test_001',
                'language': 'en'
            })
        }
        
        response = handle_generate_shopping_list(event)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error'] == 'recipe_not_found'
        assert 'Recipe not found' in body['message']
    
    @patch('src.api_handler.reminder_service')
    @patch('src.api_handler.shopping_optimizer')
    @patch('src.api_handler.kitchen_agent')
    def test_successful_shopping_list_generation(
        self, mock_kitchen_agent, mock_shopping_optimizer, mock_reminder_service
    ):
        """Test successful shopping list generation with valid inputs"""
        # Mock session data with recipe
        mock_kitchen_agent.get_session.return_value = {
            'session_id': 'test_session_123',
            'last_recipes': [
                {
                    'recipe_id': 'recipe_test_001',
                    'name': 'Brinjal Curry',
                    'ingredients': [
                        {'name': 'brinjal', 'quantity': 3, 'unit': 'pieces'},
                        {'name': 'curry_leaves', 'quantity': 10, 'unit': 'pieces'}
                    ]
                }
            ],
            'last_inventory': {
                'total_items': 1,
                'ingredients': [
                    {'ingredient_name': 'brinjal', 'quantity': 3, 'unit': 'pieces'}
                ]
            }
        }
        
        # Mock shopping list response
        mock_shopping_list = {
            'list_id': 'list_test_001',
            'recipe_id': 'recipe_test_001',
            'recipe_name': 'Brinjal Curry',
            'session_id': 'test_session_123',
            'created_at': datetime.now(timezone.utc).isoformat() + 'Z',
            'items': [
                {
                    'ingredient_name': 'curry_leaves',
                    'quantity': 10,
                    'unit': 'pieces',
                    'estimated_price': 5,
                    'market_section': 'spices'
                }
            ],
            'total_cost': 5,
            'optimized_total_cost': 5,
            'grouped_by_section': {},
            'reminders': []
        }
        mock_shopping_optimizer.generate_shopping_list.return_value = mock_shopping_list
        
        # Mock price-sensitive detection
        mock_reminder_service.detect_price_sensitive_items.return_value = [
            {
                'content': 'Buy fresh curry leaves tomorrow',
                'reason': 'Prices are lower on Wednesdays'
            }
        ]
        mock_reminder_service.schedule_reminder.return_value = 'rem_test_001'
        
        event = {
            'httpMethod': 'POST',
            'path': '/generate-shopping-list',
            'body': json.dumps({
                'session_id': 'test_session_123',
                'recipe_id': 'recipe_test_001',
                'language': 'en'
            })
        }
        
        response = handle_generate_shopping_list(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['session_id'] == 'test_session_123'
        assert 'shopping_list' in body
        assert body['shopping_list']['list_id'] == 'list_test_001'
        assert 'Shopping list ready' in body['message']
        assert '₹5' in body['message']
        assert 'reminders' in body
        assert len(body['reminders']) == 1
        
        # Verify shopping optimizer was called
        mock_shopping_optimizer.generate_shopping_list.assert_called_once()
        
        # Verify reminder service was called
        mock_reminder_service.detect_price_sensitive_items.assert_called_once()
        mock_reminder_service.schedule_reminder.assert_called_once()
    
    @patch('src.api_handler.shopping_optimizer')
    @patch('src.api_handler.kitchen_agent')
    def test_shopping_list_with_current_inventory(
        self, mock_kitchen_agent, mock_shopping_optimizer
    ):
        """Test shopping list generation with provided current_inventory"""
        mock_kitchen_agent.get_session.return_value = {
            'session_id': 'test_session_123',
            'last_recipes': [
                {
                    'recipe_id': 'recipe_test_001',
                    'name': 'Test Recipe',
                    'ingredients': []
                }
            ]
        }
        
        mock_shopping_list = {
            'list_id': 'list_test_001',
            'recipe_id': 'recipe_test_001',
            'items': [],
            'total_cost': 0,
            'reminders': []
        }
        mock_shopping_optimizer.generate_shopping_list.return_value = mock_shopping_list
        
        current_inventory = {
            'total_items': 2,
            'ingredients': [
                {'ingredient_name': 'brinjal', 'quantity': 3, 'unit': 'pieces'}
            ]
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/generate-shopping-list',
            'body': json.dumps({
                'session_id': 'test_session_123',
                'recipe_id': 'recipe_test_001',
                'current_inventory': current_inventory,
                'language': 'en'
            })
        }
        
        response = handle_generate_shopping_list(event)
        
        assert response['statusCode'] == 200
        
        # Verify current_inventory was used
        call_args = mock_shopping_optimizer.generate_shopping_list.call_args
        assert call_args[1]['current_inventory'] == current_inventory
    
    @patch('src.api_handler.shopping_optimizer')
    @patch('src.api_handler.kitchen_agent')
    def test_shopping_list_telugu_language(
        self, mock_kitchen_agent, mock_shopping_optimizer
    ):
        """Test shopping list generation with Telugu language"""
        mock_kitchen_agent.get_session.return_value = {
            'session_id': 'test_session_123',
            'last_recipes': [
                {
                    'recipe_id': 'recipe_test_001',
                    'name': 'వంకాయ కూర',
                    'ingredients': []
                }
            ],
            'last_inventory': {'total_items': 0, 'ingredients': []}
        }
        
        mock_shopping_list = {
            'list_id': 'list_test_001',
            'recipe_id': 'recipe_test_001',
            'items': [
                {'ingredient_name': 'curry_leaves', 'estimated_price': 5}
            ],
            'total_cost': 5,
            'reminders': []
        }
        mock_shopping_optimizer.generate_shopping_list.return_value = mock_shopping_list
        
        event = {
            'httpMethod': 'POST',
            'path': '/generate-shopping-list',
            'body': json.dumps({
                'session_id': 'test_session_123',
                'recipe_id': 'recipe_test_001',
                'language': 'te'
            })
        }
        
        response = handle_generate_shopping_list(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        # Telugu message should be present
        assert 'షాపింగ్ జాబితా సిద్ధంగా ఉంది' in body['message']
    
    @patch('src.api_handler.shopping_optimizer')
    @patch('src.api_handler.kitchen_agent')
    def test_empty_shopping_list(
        self, mock_kitchen_agent, mock_shopping_optimizer
    ):
        """Test when all ingredients are available (empty shopping list)"""
        mock_kitchen_agent.get_session.return_value = {
            'session_id': 'test_session_123',
            'last_recipes': [
                {
                    'recipe_id': 'recipe_test_001',
                    'name': 'Test Recipe',
                    'ingredients': []
                }
            ],
            'last_inventory': {'total_items': 5, 'ingredients': []}
        }
        
        mock_shopping_list = {
            'list_id': 'list_test_001',
            'recipe_id': 'recipe_test_001',
            'items': [],
            'total_cost': 0,
            'reminders': []
        }
        mock_shopping_optimizer.generate_shopping_list.return_value = mock_shopping_list
        
        event = {
            'httpMethod': 'POST',
            'path': '/generate-shopping-list',
            'body': json.dumps({
                'session_id': 'test_session_123',
                'recipe_id': 'recipe_test_001',
                'language': 'en'
            })
        }
        
        response = handle_generate_shopping_list(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'You have all the ingredients' in body['message']
    
    @patch('src.api_handler.shopping_optimizer')
    @patch('src.api_handler.kitchen_agent')
    def test_shopping_list_generation_failure(
        self, mock_kitchen_agent, mock_shopping_optimizer
    ):
        """Test handling of shopping list generation failure"""
        mock_kitchen_agent.get_session.return_value = {
            'session_id': 'test_session_123',
            'last_recipes': [
                {
                    'recipe_id': 'recipe_test_001',
                    'name': 'Test Recipe',
                    'ingredients': []
                }
            ]
        }
        
        mock_shopping_optimizer.generate_shopping_list.side_effect = Exception("DynamoDB error")
        
        event = {
            'httpMethod': 'POST',
            'path': '/generate-shopping-list',
            'body': json.dumps({
                'session_id': 'test_session_123',
                'recipe_id': 'recipe_test_001',
                'language': 'en'
            })
        }
        
        response = handle_generate_shopping_list(event)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['error'] == 'shopping_list_generation_failed'
        assert 'Failed to generate shopping list' in body['message']
    
    @patch('src.api_handler.reminder_service')
    @patch('src.api_handler.shopping_optimizer')
    @patch('src.api_handler.kitchen_agent')
    def test_reminder_scheduling_failure_continues(
        self, mock_kitchen_agent, mock_shopping_optimizer, mock_reminder_service
    ):
        """Test that reminder scheduling failure doesn't break shopping list generation"""
        mock_kitchen_agent.get_session.return_value = {
            'session_id': 'test_session_123',
            'last_recipes': [
                {
                    'recipe_id': 'recipe_test_001',
                    'name': 'Test Recipe',
                    'ingredients': []
                }
            ],
            'last_inventory': {'total_items': 0, 'ingredients': []}
        }
        
        mock_shopping_list = {
            'list_id': 'list_test_001',
            'recipe_id': 'recipe_test_001',
            'items': [
                {'ingredient_name': 'curry_leaves', 'estimated_price': 5, 'market_section': 'spices'}
            ],
            'total_cost': 5,
            'reminders': []
        }
        mock_shopping_optimizer.generate_shopping_list.return_value = mock_shopping_list
        
        # Mock price-sensitive detection succeeds but scheduling fails
        mock_reminder_service.detect_price_sensitive_items.return_value = [
            {'content': 'Test reminder', 'reason': 'Test reason'}
        ]
        mock_reminder_service.schedule_reminder.side_effect = Exception("EventBridge error")
        
        event = {
            'httpMethod': 'POST',
            'path': '/generate-shopping-list',
            'body': json.dumps({
                'session_id': 'test_session_123',
                'recipe_id': 'recipe_test_001',
                'language': 'en'
            })
        }
        
        response = handle_generate_shopping_list(event)
        
        # Should still succeed even if reminder scheduling fails
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'shopping_list' in body
        # Reminders list should be empty since scheduling failed
        assert len(body['reminders']) == 0
    
    @patch('src.api_handler.shopping_optimizer')
    @patch('src.api_handler.kitchen_agent')
    def test_lambda_handler_routing(
        self, mock_kitchen_agent, mock_shopping_optimizer
    ):
        """Test that lambda_handler routes to generate-shopping-list endpoint"""
        mock_kitchen_agent.get_session.return_value = {
            'session_id': 'test_session_123',
            'last_recipes': [
                {
                    'recipe_id': 'recipe_test_001',
                    'name': 'Test Recipe',
                    'ingredients': []
                }
            ],
            'last_inventory': {'total_items': 0, 'ingredients': []}
        }
        
        mock_shopping_list = {
            'list_id': 'list_test_001',
            'recipe_id': 'recipe_test_001',
            'items': [],
            'total_cost': 0,
            'reminders': []
        }
        mock_shopping_optimizer.generate_shopping_list.return_value = mock_shopping_list
        
        event = {
            'httpMethod': 'POST',
            'path': '/generate-shopping-list',
            'body': json.dumps({
                'session_id': 'test_session_123',
                'recipe_id': 'recipe_test_001'
            })
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'shopping_list' in body


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
