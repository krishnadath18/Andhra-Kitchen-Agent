"""
Unit tests for RecipeGenerator

Tests recipe generation, nutrition calculation, cost estimation, and formatting.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.recipe_generator import RecipeGenerator
from src.validators import validate_recipe_schema


class TestRecipeGenerator:
    """Test suite for RecipeGenerator class"""
    
    @pytest.fixture
    def generator(self):
        """Create RecipeGenerator instance"""
        with patch('boto3.client'), patch('boto3.resource'):
            return RecipeGenerator()
    
    @pytest.fixture
    def sample_inventory(self):
        """Sample inventory JSON"""
        return {
            "total_items": 4,
            "detection_timestamp": "2024-01-15T10:30:00Z",
            "session_id": "sess_test123",
            "ingredients": [
                {
                    "ingredient_name": "brinjal",
                    "quantity": 3,
                    "unit": "pieces",
                    "confidence_score": 0.92
                },
                {
                    "ingredient_name": "rice",
                    "quantity": 1,
                    "unit": "kg",
                    "confidence_score": 0.95
                },
                {
                    "ingredient_name": "oil",
                    "quantity": 2,
                    "unit": "tablespoons",
                    "confidence_score": 0.88
                },
                {
                    "ingredient_name": "onion",
                    "quantity": 2,
                    "unit": "pieces",
                    "confidence_score": 0.90
                }
            ]
        }
    
    def test_initialization(self, generator):
        """Test RecipeGenerator initialization"""
        assert generator.model_id == "anthropic.claude-3-haiku-20240307-v1:0"
        assert generator.temperature == 0.7
        assert generator.max_tokens == 4096
        assert generator.max_retries == 3
        assert len(generator.ingredient_translations) > 0
        assert len(generator.nutrition_data) > 0
    
    def test_create_recipe_prompt(self, generator, sample_inventory):
        """Test recipe prompt creation"""
        prompt = generator._create_recipe_prompt(
            inventory=sample_inventory,
            preferences={"low_oil": True, "vegetarian": True},
            allergies=["peanuts"],
            language="en",
            count=3
        )
        
        assert "brinjal" in prompt
        assert "rice" in prompt
        assert "oil" in prompt
        assert "onion" in prompt
        assert "tablespoons" in prompt.lower()  # Check for oil constraint
        assert "vegetarian" in prompt.lower()
        assert "peanuts" in prompt
        assert "3" in prompt  # recipe count
    
    def test_create_recipe_prompt_telugu(self, generator, sample_inventory):
        """Test recipe prompt creation for Telugu language"""
        prompt = generator._create_recipe_prompt(
            inventory=sample_inventory,
            preferences={},
            allergies=[],
            language="te",
            count=2
        )
        
        assert "Telugu" in prompt
        assert "తెలుగు" in prompt or "telugu" in prompt.lower()
    
    def test_parse_bedrock_response(self, generator):
        """Test parsing Bedrock response"""
        response_text = '''```json
[
  {
    "name": "Brinjal Curry",
    "prep_time": 10,
    "cook_time": 20,
    "servings": 4,
    "ingredients": [{"name": "brinjal", "quantity": 3, "unit": "pieces"}],
    "steps": [{"step_number": 1, "instruction": "Cut brinjals"}]
  }
]
```'''
        
        recipes = generator._parse_bedrock_response(response_text)
        
        assert isinstance(recipes, list)
        assert len(recipes) == 1
        assert recipes[0]['name'] == "Brinjal Curry"
        assert recipes[0]['prep_time'] == 10
    
    def test_parse_bedrock_response_without_markdown(self, generator):
        """Test parsing Bedrock response without markdown"""
        response_text = '''[
  {
    "name": "Rice Dish",
    "prep_time": 15,
    "servings": 4,
    "ingredients": [],
    "steps": []
  }
]'''
        
        recipes = generator._parse_bedrock_response(response_text)
        
        assert isinstance(recipes, list)
        assert len(recipes) == 1
        assert recipes[0]['name'] == "Rice Dish"
    
    def test_parse_bedrock_response_invalid_json(self, generator):
        """Test parsing invalid JSON response"""
        response_text = "This is not JSON"
        
        with pytest.raises(ValueError, match="Failed to parse"):
            generator._parse_bedrock_response(response_text)
    
    def test_calculate_nutrition(self, generator):
        """Test nutrition calculation"""
        ingredients = [
            {"name": "brinjal", "quantity": 300, "unit": "grams"},
            {"name": "rice", "quantity": 200, "unit": "grams"},
            {"name": "oil", "quantity": 2, "unit": "tablespoons"}
        ]
        
        nutrition = generator.calculate_nutrition(
            ingredients=ingredients,
            cooking_method="sauteing",
            servings=4
        )
        
        assert 'calories' in nutrition
        assert 'protein' in nutrition
        assert 'carbohydrates' in nutrition
        assert 'fat' in nutrition
        assert 'fiber' in nutrition
        assert nutrition['accuracy_margin'] == "±10%"
        
        # Check reasonable values
        assert nutrition['calories'] > 0
        assert nutrition['protein'] >= 0
        assert nutrition['carbohydrates'] >= 0
        assert nutrition['fat'] >= 0
    
    def test_calculate_nutrition_frying_adjustment(self, generator):
        """Test nutrition calculation with frying method (fat increase)"""
        ingredients = [
            {"name": "potato", "quantity": 400, "unit": "grams"},
            {"name": "oil", "quantity": 4, "unit": "tablespoons"}
        ]
        
        nutrition_sauteing = generator.calculate_nutrition(
            ingredients=ingredients,
            cooking_method="sauteing",
            servings=4
        )
        
        nutrition_frying = generator.calculate_nutrition(
            ingredients=ingredients,
            cooking_method="frying",
            servings=4
        )
        
        # Frying should have more fat and calories
        assert nutrition_frying['fat'] > nutrition_sauteing['fat']
        assert nutrition_frying['calories'] > nutrition_sauteing['calories']
    
    def test_convert_to_grams(self, generator):
        """Test unit conversion to grams"""
        # Weight units
        assert generator._convert_to_grams(1, "kg", "") == 1000
        assert generator._convert_to_grams(500, "grams", "") == 500
        
        # Volume units
        assert generator._convert_to_grams(1, "cup", "") == 200
        assert generator._convert_to_grams(1, "tablespoon", "") == 15
        assert generator._convert_to_grams(1, "teaspoon", "") == 5
        
        # Piece-based
        assert generator._convert_to_grams(1, "pieces", "brinjal") == 150
        assert generator._convert_to_grams(1, "pieces", "tomato") == 100
        
        # Bunches
        assert generator._convert_to_grams(1, "bunch", "") == 50
    
    def test_estimate_cost_with_mock_dynamodb(self, generator):
        """Test cost estimation with mocked DynamoDB"""
        ingredients = [
            {"name": "brinjal", "quantity": 3, "unit": "pieces"},
            {"name": "rice", "quantity": 1, "unit": "kg"}
        ]
        
        # Mock DynamoDB response
        mock_table = Mock()
        mock_table.get_item.side_effect = [
            {
                'Item': {
                    'ingredient_name': 'brinjal',
                    'price_per_unit': 30.0,
                    'unit': 'kg'
                }
            },
            {
                'Item': {
                    'ingredient_name': 'rice',
                    'price_per_unit': 50.0,
                    'unit': 'kg'
                }
            }
        ]
        generator.market_prices_table = mock_table
        
        cost = generator.estimate_cost(ingredients, servings=4)
        
        assert cost > 0
        assert isinstance(cost, float)
    
    def test_estimate_cost_fallback(self, generator):
        """Test cost estimation fallback when price not found"""
        ingredients = [
            {"name": "unknown_ingredient", "quantity": 1, "unit": "kg"}
        ]
        
        # Mock DynamoDB to return no item
        mock_table = Mock()
        mock_table.get_item.return_value = {}
        generator.market_prices_table = mock_table
        
        cost = generator.estimate_cost(ingredients, servings=4)
        
        # Should use fallback estimation
        assert cost > 0
        assert isinstance(cost, float)
    
    def test_format_recipe_english(self, generator):
        """Test recipe formatting for English"""
        recipe_data = {
            "name": "Brinjal Curry",
            "name_english": "Brinjal Curry",
            "name_telugu": "వంకాయ కూర",
            "prep_time": 10,
            "cook_time": 20,
            "servings": 4,
            "ingredients": [
                {"name": "brinjal", "quantity": 3, "unit": "pieces"}
            ],
            "steps": [
                {"step_number": 1, "instruction": "Cut brinjals"}
            ]
        }
        
        formatted = generator.format_recipe(recipe_data, language="en")
        
        assert formatted['name'] == "Brinjal Curry"
        assert formatted['name_english'] == "Brinjal Curry"
        assert 'name_telugu' in formatted
    
    def test_format_recipe_telugu(self, generator):
        """Test recipe formatting for Telugu"""
        recipe_data = {
            "name": "Brinjal Curry",
            "name_english": "Brinjal Curry",
            "name_telugu": "వంకాయ కూర",
            "prep_time": 10,
            "servings": 4,
            "ingredients": [
                {"name": "brinjal", "quantity": 3, "unit": "pieces"}
            ],
            "steps": []
        }
        
        formatted = generator.format_recipe(recipe_data, language="te")
        
        assert formatted['name'] == "వంకాయ కూర"
        assert formatted['name_english'] == "Brinjal Curry"
    
    def test_format_recipe_adds_telugu_translations(self, generator):
        """Test that format_recipe adds Telugu translations for ingredients"""
        recipe_data = {
            "name": "Test Recipe",
            "ingredients": [
                {"name": "brinjal", "quantity": 3, "unit": "pieces"},
                {"name": "curry_leaves", "quantity": 1, "unit": "bunch"}
            ],
            "steps": []
        }
        
        formatted = generator.format_recipe(recipe_data, language="en")
        
        # Check Telugu translations were added
        assert formatted['ingredients'][0]['name_telugu'] == "వంకాయ"
        assert formatted['ingredients'][1]['name_telugu'] == "కరివేపాకు"
    
    def test_convert_units(self, generator):
        """Test unit conversion"""
        # kg to grams
        assert generator._convert_units(1, "kg", "grams") == 1000
        
        # grams to kg
        assert generator._convert_units(1000, "grams", "kg") == 1
        
        # tablespoons to grams
        result = generator._convert_units(2, "tablespoons", "grams")
        assert result == 30  # 2 * 15
    
    def test_estimate_ingredient_cost(self, generator):
        """Test ingredient cost estimation"""
        cost = generator._estimate_ingredient_cost("brinjal", 1, "kg")
        assert cost > 0
        assert isinstance(cost, float)
        
        cost = generator._estimate_ingredient_cost("unknown", 0.5, "kg")
        assert cost > 0


class TestRecipeGeneratorIntegration:
    """Integration tests requiring AWS credentials"""
    
    @pytest.mark.skip(reason="Requires AWS credentials and Bedrock access")
    def test_generate_recipes_real(self):
        """Test actual recipe generation with Bedrock (requires AWS)"""
        generator = RecipeGenerator()
        
        inventory = {
            "total_items": 3,
            "session_id": "test_session",
            "ingredients": [
                {"ingredient_name": "brinjal", "quantity": 3, "unit": "pieces"},
                {"ingredient_name": "rice", "quantity": 1, "unit": "kg"},
                {"ingredient_name": "oil", "quantity": 2, "unit": "tablespoons"}
            ]
        }
        
        recipes = generator.generate_recipes(
            inventory=inventory,
            preferences={"low_oil": True},
            allergies=[],
            language="en",
            count=2
        )
        
        assert len(recipes) >= 2
        for recipe in recipes:
            is_valid, error = validate_recipe_schema(recipe)
            assert is_valid, f"Invalid recipe: {error}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
