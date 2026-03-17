"""
Integration test for POST /generate-recipes endpoint

Tests the complete flow from API handler to RecipeGenerator.
This test requires AWS credentials and Bedrock access.
"""

import json
import pytest
from unittest.mock import patch
from datetime import datetime

# Import the handler
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api_handler import lambda_handler


@pytest.mark.integration
class TestGenerateRecipesIntegration:
    """Integration tests for POST /generate-recipes endpoint"""
    
    def test_generate_recipes_with_brinjal_inventory(self):
        """
        Test recipe generation with a real inventory containing brinjal.
        
        This test verifies:
        - Endpoint accepts valid inventory JSON
        - RecipeGenerator is called correctly
        - Response contains valid Recipe JSON objects
        - Recipes include all required fields
        """
        # Create a realistic inventory from image analysis
        inventory = {
            "total_items": 4,
            "detection_timestamp": "2024-01-15T10:31:30Z",
            "session_id": "test_integration_session",
            "ingredients": [
                {
                    "ingredient_name": "brinjal",
                    "ingredient_name_telugu": "వంకాయ",
                    "quantity": 3,
                    "unit": "pieces",
                    "confidence_score": 0.92,
                    "category": "vegetable"
                },
                {
                    "ingredient_name": "curry_leaves",
                    "ingredient_name_telugu": "కరివేపాకు",
                    "quantity": 1,
                    "unit": "bunches",
                    "confidence_score": 0.88,
                    "category": "spice"
                },
                {
                    "ingredient_name": "rice",
                    "ingredient_name_telugu": "బియ్యం",
                    "quantity": 2,
                    "unit": "kg",
                    "confidence_score": 0.95,
                    "category": "grain"
                },
                {
                    "ingredient_name": "tamarind",
                    "ingredient_name_telugu": "చింతపండు",
                    "quantity": 100,
                    "unit": "grams",
                    "confidence_score": 0.78,
                    "category": "spice"
                }
            ]
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/generate-recipes',
            'body': json.dumps({
                'session_id': 'test_integration_session',
                'inventory': inventory,
                'preferences': {
                    'low_oil': True,
                    'vegetarian': True,
                    'spice_level': 'medium'
                },
                'allergies': [],
                'language': 'en',
                'count': 2
            })
        }
        
        # Mock Bedrock call to avoid actual API calls in tests
        with patch('src.recipe_generator.RecipeGenerator._call_bedrock_recipe') as mock_bedrock:
            # Mock Bedrock response with realistic recipe data (as JSON array)
            mock_bedrock.return_value = json.dumps([
                {
                    "name": "Brinjal Curry",
                    "name_english": "Brinjal Curry",
                    "name_telugu": "వంకాయ కూర",
                    "description": "Traditional Andhra-style brinjal curry",
                    "prep_time": 10,
                    "cook_time": 20,
                    "total_time": 30,
                    "servings": 4,
                    "difficulty": "easy",
                    "ingredients": [
                        {"name": "brinjal", "quantity": 3, "unit": "pieces"},
                        {"name": "tamarind", "quantity": 50, "unit": "grams"},
                        {"name": "curry_leaves", "quantity": 10, "unit": "pieces"},
                        {"name": "oil", "quantity": 2, "unit": "tablespoons"}
                    ],
                    "steps": [
                        {"step_number": 1, "instruction": "Cut brinjals into medium pieces"},
                        {"step_number": 2, "instruction": "Heat oil and add curry leaves"},
                        {"step_number": 3, "instruction": "Add brinjal and cook until tender"}
                    ],
                    "cooking_method": "sauteing",
                    "oil_quantity": 0.5,
                    "tags": ["low-oil", "vegetarian", "traditional"]
                },
                {
                    "name": "Tamarind Rice",
                    "name_english": "Tamarind Rice",
                    "name_telugu": "పులిహోర",
                    "description": "Tangy tamarind rice with spices",
                    "prep_time": 5,
                    "cook_time": 15,
                    "total_time": 20,
                    "servings": 4,
                    "difficulty": "easy",
                    "ingredients": [
                        {"name": "rice", "quantity": 2, "unit": "cups"},
                        {"name": "tamarind", "quantity": 50, "unit": "grams"},
                        {"name": "curry_leaves", "quantity": 10, "unit": "pieces"},
                        {"name": "oil", "quantity": 1.5, "unit": "tablespoons"}
                    ],
                    "steps": [
                        {"step_number": 1, "instruction": "Cook rice and let it cool"},
                        {"step_number": 2, "instruction": "Prepare tamarind paste"},
                        {"step_number": 3, "instruction": "Mix rice with tamarind and spices"}
                    ],
                    "cooking_method": "boiling",
                    "oil_quantity": 0.375,
                    "tags": ["low-oil", "vegetarian", "quick"]
                }
            ])
            
            response = lambda_handler(event, None)
        
        # Verify response
        assert response['statusCode'] == 200
        
        body = json.loads(response['body'])
        assert body['session_id'] == 'test_integration_session'
        assert 'recipes' in body
        assert len(body['recipes']) == 2
        
        # Verify first recipe structure
        recipe1 = body['recipes'][0]
        assert 'recipe_id' in recipe1
        assert recipe1['name'] == 'Brinjal Curry'
        assert recipe1['servings'] == 4
        assert 'ingredients' in recipe1
        assert 'steps' in recipe1
        assert 'nutrition' in recipe1
        assert 'estimated_cost' in recipe1
        assert 'cost_per_serving' in recipe1
        
        # Verify nutrition information is present
        nutrition = recipe1['nutrition']
        assert 'calories' in nutrition
        assert 'protein' in nutrition
        assert 'carbohydrates' in nutrition
        assert 'fat' in nutrition
        assert 'fiber' in nutrition
        
        # Verify low-oil constraint is respected
        assert recipe1.get('oil_quantity', 0) <= 2.0  # Max 2 tbsp per serving
        
        print(f"\n✓ Generated {len(body['recipes'])} recipes successfully")
        print(f"✓ Recipe 1: {recipe1['name']} - ₹{recipe1['cost_per_serving']}/serving")
        print(f"✓ Recipe 2: {body['recipes'][1]['name']} - ₹{body['recipes'][1]['cost_per_serving']}/serving")
    
    def test_generate_recipes_telugu_output(self):
        """Test recipe generation with Telugu language output"""
        inventory = {
            "total_items": 2,
            "ingredients": [
                {
                    "ingredient_name": "brinjal",
                    "quantity": 3,
                    "unit": "pieces",
                    "confidence_score": 0.9
                }
            ]
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/generate-recipes',
            'body': json.dumps({
                'session_id': 'test_telugu_session',
                'inventory': inventory,
                'language': 'te',
                'count': 1
            })
        }
        
        with patch('src.recipe_generator.RecipeGenerator._call_bedrock_recipe') as mock_bedrock:
            mock_bedrock.return_value = json.dumps([
                {
                    "name": "వంకాయ కూర",
                    "name_english": "Brinjal Curry",
                    "name_telugu": "వంకాయ కూర",
                    "description": "సాంప్రదాయ ఆంధ్ర వంకాయ కూర",
                    "prep_time": 10,
                    "cook_time": 20,
                    "total_time": 30,
                    "servings": 4,
                    "difficulty": "easy",
                    "ingredients": [
                        {"name": "brinjal", "quantity": 3, "unit": "pieces"}
                    ],
                    "steps": [
                        {"step_number": 1, "instruction": "వంకాయలను ముక్కలు చేయండి"}
                    ],
                    "cooking_method": "sauteing",
                    "tags": ["vegetarian"]
                }
            ])
            
            response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Verify Telugu message
        assert 'రెసిపీ సూచన' in body['message']
        
        # Verify recipe has Telugu name
        recipe = body['recipes'][0]
        assert recipe['name'] == 'వంకాయ కూర'
        
        print(f"\n✓ Telugu recipe generated: {recipe['name']}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'integration'])
