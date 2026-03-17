"""
Unit tests for POST /generate-recipes endpoint

Tests the API handler for recipe generation endpoint.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import the handler
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api_handler import handle_generate_recipes, lambda_handler


class TestGenerateRecipesEndpoint:
    """Test suite for POST /generate-recipes endpoint"""
    
    def test_missing_session_id(self):
        """Test that missing session_id returns 400 error"""
        event = {
            'httpMethod': 'POST',
            'path': '/generate-recipes',
            'body': json.dumps({
                'inventory': {'total_items': 2, 'ingredients': []}
            })
        }
        
        response = handle_generate_recipes(event)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_request'
        assert 'session_id' in body['message']
    
    def test_missing_inventory(self):
        """Test that missing inventory returns 400 error"""
        event = {
            'httpMethod': 'POST',
            'path': '/generate-recipes',
            'body': json.dumps({
                'session_id': 'test_session_123'
            })
        }
        
        response = handle_generate_recipes(event)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_request'
        assert 'inventory' in body['message']
    
    def test_empty_inventory(self):
        """Test that empty inventory returns 400 error"""
        event = {
            'httpMethod': 'POST',
            'path': '/generate-recipes',
            'body': json.dumps({
                'session_id': 'test_session_123',
                'inventory': {'total_items': 0, 'ingredients': []}
            })
        }
        
        response = handle_generate_recipes(event)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'insufficient_ingredients'
        assert 'Not enough ingredients' in body['message']
    
    def test_invalid_inventory_format(self):
        """Test that invalid inventory format returns 400 error"""
        event = {
            'httpMethod': 'POST',
            'path': '/generate-recipes',
            'body': json.dumps({
                'session_id': 'test_session_123',
                'inventory': 'invalid_string'
            })
        }
        
        response = handle_generate_recipes(event)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_request'
        assert 'Invalid inventory format' in body['message']
    
    @patch('src.api_handler.recipe_generator')
    def test_successful_recipe_generation(self, mock_recipe_gen):
        """Test successful recipe generation with valid inputs"""
        # Mock recipe generator response
        mock_recipes = [
            {
                'recipe_id': 'recipe_test_001',
                'name': 'Brinjal Curry',
                'name_english': 'Brinjal Curry',
                'name_telugu': 'వంకాయ కూర',
                'prep_time': 10,
                'cook_time': 20,
                'total_time': 30,
                'servings': 4,
                'ingredients': [
                    {'name': 'brinjal', 'quantity': 3, 'unit': 'pieces'}
                ],
                'steps': [
                    {'step_number': 1, 'instruction': 'Cut brinjals'}
                ],
                'nutrition': {
                    'calories': 120,
                    'protein': 2.5,
                    'carbohydrates': 15,
                    'fat': 6,
                    'fiber': 4
                },
                'estimated_cost': 40,
                'cost_per_serving': 10
            }
        ]
        mock_recipe_gen.generate_recipes.return_value = mock_recipes
        
        event = {
            'httpMethod': 'POST',
            'path': '/generate-recipes',
            'body': json.dumps({
                'session_id': 'test_session_123',
                'inventory': {
                    'total_items': 2,
                    'ingredients': [
                        {'ingredient_name': 'brinjal', 'quantity': 3, 'unit': 'pieces', 'confidence_score': 0.9}
                    ]
                },
                'language': 'en',
                'count': 3
            })
        }
        
        response = handle_generate_recipes(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['session_id'] == 'test_session_123'
        assert 'recipes' in body
        assert len(body['recipes']) == 1
        assert body['recipes'][0]['name'] == 'Brinjal Curry'
        assert 'recipe suggestion' in body['message']  # Singular for 1 recipe
        
        # Verify recipe generator was called with correct parameters
        mock_recipe_gen.generate_recipes.assert_called_once()
        call_args = mock_recipe_gen.generate_recipes.call_args
        assert call_args[1]['language'] == 'en'
        assert call_args[1]['count'] == 3
    
    @patch('src.api_handler.recipe_generator')
    def test_recipe_generation_with_preferences(self, mock_recipe_gen):
        """Test recipe generation with preferences and allergies"""
        mock_recipes = [
            {
                'recipe_id': 'recipe_test_002',
                'name': 'Low Oil Curry',
                'servings': 4,
                'ingredients': [],
                'steps': [],
                'nutrition': {'calories': 100, 'protein': 2, 'carbohydrates': 10, 'fat': 3, 'fiber': 2},
                'estimated_cost': 30,
                'cost_per_serving': 7.5
            }
        ]
        mock_recipe_gen.generate_recipes.return_value = mock_recipes
        
        event = {
            'httpMethod': 'POST',
            'path': '/generate-recipes',
            'body': json.dumps({
                'session_id': 'test_session_123',
                'inventory': {
                    'total_items': 3,
                    'ingredients': [
                        {'ingredient_name': 'brinjal', 'quantity': 3, 'unit': 'pieces', 'confidence_score': 0.9}
                    ]
                },
                'preferences': {
                    'low_oil': True,
                    'vegetarian': True
                },
                'allergies': ['peanuts'],
                'language': 'en',
                'count': 2
            })
        }
        
        response = handle_generate_recipes(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'recipes' in body
        
        # Verify preferences and allergies were passed
        call_args = mock_recipe_gen.generate_recipes.call_args
        assert call_args[1]['preferences'] == {'low_oil': True, 'vegetarian': True}
        assert call_args[1]['allergies'] == ['peanuts']
    
    @patch('src.api_handler.recipe_generator')
    def test_recipe_generation_telugu_language(self, mock_recipe_gen):
        """Test recipe generation with Telugu language"""
        mock_recipes = [
            {
                'recipe_id': 'recipe_test_003',
                'name': 'వంకాయ కూర',
                'servings': 4,
                'ingredients': [],
                'steps': [],
                'nutrition': {'calories': 120, 'protein': 2.5, 'carbohydrates': 15, 'fat': 6, 'fiber': 4},
                'estimated_cost': 40,
                'cost_per_serving': 10
            }
        ]
        mock_recipe_gen.generate_recipes.return_value = mock_recipes
        
        event = {
            'httpMethod': 'POST',
            'path': '/generate-recipes',
            'body': json.dumps({
                'session_id': 'test_session_123',
                'inventory': {
                    'total_items': 2,
                    'ingredients': [
                        {'ingredient_name': 'brinjal', 'quantity': 3, 'unit': 'pieces', 'confidence_score': 0.9}
                    ]
                },
                'language': 'te',
                'count': 3
            })
        }
        
        response = handle_generate_recipes(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'recipes' in body
        # Telugu message should be present
        assert 'రెసిపీ సూచనలు' in body['message'] or 'రెసిపీ సూచన' in body['message']
    
    @patch('src.api_handler.recipe_generator')
    def test_recipe_generation_failure(self, mock_recipe_gen):
        """Test handling of recipe generation failure"""
        mock_recipe_gen.generate_recipes.side_effect = Exception("Bedrock API error")
        
        event = {
            'httpMethod': 'POST',
            'path': '/generate-recipes',
            'body': json.dumps({
                'session_id': 'test_session_123',
                'inventory': {
                    'total_items': 2,
                    'ingredients': [
                        {'ingredient_name': 'brinjal', 'quantity': 3, 'unit': 'pieces', 'confidence_score': 0.9}
                    ]
                },
                'language': 'en',
                'count': 3
            })
        }
        
        response = handle_generate_recipes(event)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['error'] == 'recipe_generation_failed'
        assert 'Failed to generate recipes' in body['message']
    
    @patch('src.api_handler.recipe_generator')
    def test_no_recipes_generated(self, mock_recipe_gen):
        """Test handling when no recipes are generated"""
        mock_recipe_gen.generate_recipes.return_value = []
        
        event = {
            'httpMethod': 'POST',
            'path': '/generate-recipes',
            'body': json.dumps({
                'session_id': 'test_session_123',
                'inventory': {
                    'total_items': 1,
                    'ingredients': [
                        {'ingredient_name': 'unknown_item', 'quantity': 1, 'unit': 'pieces', 'confidence_score': 0.9}
                    ]
                },
                'language': 'en',
                'count': 3
            })
        }
        
        response = handle_generate_recipes(event)
        
        assert response['statusCode'] == 422
        body = json.loads(response['body'])
        assert body['error'] == 'no_recipes_generated'
    
    @patch('src.api_handler.recipe_generator')
    def test_count_validation(self, mock_recipe_gen):
        """Test that count is validated and defaults to 3 if invalid"""
        mock_recipes = [{'recipe_id': 'test', 'name': 'Test Recipe', 'servings': 4, 'ingredients': [], 'steps': [], 'nutrition': {}, 'estimated_cost': 0, 'cost_per_serving': 0}]
        mock_recipe_gen.generate_recipes.return_value = mock_recipes
        
        # Test with count > 5
        event = {
            'httpMethod': 'POST',
            'path': '/generate-recipes',
            'body': json.dumps({
                'session_id': 'test_session_123',
                'inventory': {'total_items': 2, 'ingredients': []},
                'count': 10
            })
        }
        
        response = handle_generate_recipes(event)
        assert response['statusCode'] == 200
        
        # Verify count was capped at 3 (default)
        call_args = mock_recipe_gen.generate_recipes.call_args
        assert call_args[1]['count'] == 3
    
    @patch('src.api_handler.recipe_generator')
    def test_lambda_handler_routing(self, mock_recipe_gen):
        """Test that lambda_handler routes to generate-recipes endpoint"""
        mock_recipes = [{'recipe_id': 'test', 'name': 'Test', 'servings': 4, 'ingredients': [], 'steps': [], 'nutrition': {}, 'estimated_cost': 0, 'cost_per_serving': 0}]
        mock_recipe_gen.generate_recipes.return_value = mock_recipes
        
        event = {
            'httpMethod': 'POST',
            'path': '/generate-recipes',
            'body': json.dumps({
                'session_id': 'test_session_123',
                'inventory': {'total_items': 2, 'ingredients': []}
            })
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'recipes' in body


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
