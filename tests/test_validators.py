"""
Unit tests for JSON schema validators

Run with: python -m pytest tests/test_validators.py -v
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from validators import (
    validate_inventory_schema,
    validate_recipe_schema,
    validate_shopping_list_schema,
    validate_json_file
)


def load_test_fixture(filename):
    """Load a test fixture JSON file"""
    fixture_path = Path(__file__).parent / "fixtures" / filename
    with open(fixture_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_inventory_schema_valid():
    """Test that valid inventory data passes validation"""
    inventory_data = load_test_fixture("test_inventory.json")
    is_valid, error = validate_inventory_schema(inventory_data)
    assert is_valid, f"Validation failed: {error}"
    print("✅ Inventory schema validation passed")


def test_recipe_schema_valid():
    """Test that valid recipe data passes validation"""
    recipe_data = load_test_fixture("test_recipe.json")
    is_valid, error = validate_recipe_schema(recipe_data)
    assert is_valid, f"Validation failed: {error}"
    print("✅ Recipe schema validation passed")


def test_shopping_list_schema_valid():
    """Test that valid shopping list data passes validation"""
    shopping_list_data = load_test_fixture("test_shopping_list.json")
    is_valid, error = validate_shopping_list_schema(shopping_list_data)
    assert is_valid, f"Validation failed: {error}"
    print("✅ Shopping list schema validation passed")


def test_inventory_schema_invalid_missing_required():
    """Test that inventory data missing required fields fails validation"""
    invalid_data = {
        "total_items": 1
        # Missing detection_timestamp and ingredients
    }
    is_valid, error = validate_inventory_schema(invalid_data)
    assert not is_valid, "Validation should have failed for missing required fields"
    assert "required" in error.lower() or "missing" in error.lower()
    print("✅ Inventory schema correctly rejects missing required fields")


def test_inventory_schema_invalid_confidence_range():
    """Test that inventory data with invalid confidence score fails validation"""
    invalid_data = {
        "total_items": 1,
        "detection_timestamp": "2024-01-15T10:30:00Z",
        "ingredients": [
            {
                "ingredient_name": "brinjal",
                "quantity": 3,
                "unit": "pieces",
                "confidence_score": 1.5  # Invalid: > 1.0
            }
        ]
    }
    is_valid, error = validate_inventory_schema(invalid_data)
    assert not is_valid, "Validation should have failed for confidence_score > 1.0"
    print("✅ Inventory schema correctly rejects invalid confidence scores")


def test_recipe_schema_invalid_negative_time():
    """Test that recipe data with negative time fails validation"""
    invalid_data = {
        "recipe_id": "recipe_test",
        "name": "Test Recipe",
        "ingredients": [{"name": "test", "quantity": 1, "unit": "piece"}],
        "steps": [{"step_number": 1, "instruction": "Test"}],
        "prep_time": -5,  # Invalid: negative
        "servings": 4,
        "nutrition": {"calories": 100, "protein": 5, "carbohydrates": 10, "fat": 3}
    }
    is_valid, error = validate_recipe_schema(invalid_data)
    assert not is_valid, "Validation should have failed for negative prep_time"
    print("✅ Recipe schema correctly rejects negative time values")


def test_shopping_list_schema_invalid_negative_price():
    """Test that shopping list data with negative price fails validation"""
    invalid_data = {
        "list_id": "list_test",
        "recipe_id": "recipe_test",
        "items": [
            {
                "ingredient_name": "test",
                "quantity": 1,
                "unit": "piece",
                "estimated_price": -10  # Invalid: negative
            }
        ],
        "total_cost": -10
    }
    is_valid, error = validate_shopping_list_schema(invalid_data)
    assert not is_valid, "Validation should have failed for negative price"
    print("✅ Shopping list schema correctly rejects negative prices")


def test_validate_json_file():
    """Test validating JSON files directly"""
    fixture_dir = Path(__file__).parent / "fixtures"
    
    # Test inventory file
    is_valid, error = validate_json_file(
        str(fixture_dir / "test_inventory.json"),
        "inventory"
    )
    assert is_valid, f"Inventory file validation failed: {error}"
    
    # Test recipe file
    is_valid, error = validate_json_file(
        str(fixture_dir / "test_recipe.json"),
        "recipe"
    )
    assert is_valid, f"Recipe file validation failed: {error}"
    
    # Test shopping list file
    is_valid, error = validate_json_file(
        str(fixture_dir / "test_shopping_list.json"),
        "shopping_list"
    )
    assert is_valid, f"Shopping list file validation failed: {error}"
    
    print("✅ All JSON file validations passed")


if __name__ == "__main__":
    print("Running JSON Schema Validator Tests")
    print("=" * 50)
    
    try:
        test_inventory_schema_valid()
        test_recipe_schema_valid()
        test_shopping_list_schema_valid()
        test_inventory_schema_invalid_missing_required()
        test_inventory_schema_invalid_confidence_range()
        test_recipe_schema_invalid_negative_time()
        test_shopping_list_schema_invalid_negative_price()
        test_validate_json_file()
        
        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED!")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)
