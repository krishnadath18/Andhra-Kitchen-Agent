"""
JSON Schema Validators for Andhra Kitchen Agent

This module provides validation utilities for Inventory, Recipe, and Shopping List JSON schemas.
Uses jsonschema library for validation against JSON Schema Draft 7.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Tuple
from jsonschema import validate, ValidationError, Draft7Validator
from datetime import datetime


# Get schema directory path
SCHEMA_DIR = Path(__file__).parent.parent / "schemas"


def load_schema(schema_name: str) -> Dict[str, Any]:
    """
    Load a JSON schema from the schemas directory.
    
    Args:
        schema_name: Name of the schema file (e.g., 'inventory_schema.json')
    
    Returns:
        Dict containing the JSON schema
    
    Raises:
        FileNotFoundError: If schema file doesn't exist
        json.JSONDecodeError: If schema file is invalid JSON
    """
    schema_path = SCHEMA_DIR / schema_name
    
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# Load schemas at module level for reuse
INVENTORY_SCHEMA = load_schema("inventory_schema.json")
RECIPE_SCHEMA = load_schema("recipe_schema.json")
SHOPPING_LIST_SCHEMA = load_schema("shopping_list_schema.json")


def validate_inventory_schema(inventory_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate inventory data against the Inventory JSON schema.
    
    Args:
        inventory_data: Dictionary containing inventory data
    
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if validation passes, False otherwise
        - error_message: Empty string if valid, error description if invalid
    
    Example:
        >>> data = {
        ...     "total_items": 2,
        ...     "detection_timestamp": "2024-01-15T10:30:00Z",
        ...     "ingredients": [
        ...         {
        ...             "ingredient_name": "brinjal",
        ...             "quantity": 3,
        ...             "unit": "pieces",
        ...             "confidence_score": 0.92
        ...         }
        ...     ]
        ... }
        >>> is_valid, error = validate_inventory_schema(data)
        >>> print(is_valid)
        True
    """
    try:
        validate(instance=inventory_data, schema=INVENTORY_SCHEMA)
        return True, ""
    except ValidationError as e:
        return False, f"Validation error: {e.message} at path: {'.'.join(str(p) for p in e.path)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def validate_recipe_schema(recipe_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate recipe data against the Recipe JSON schema.
    
    Args:
        recipe_data: Dictionary containing recipe data
    
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if validation passes, False otherwise
        - error_message: Empty string if valid, error description if invalid
    
    Example:
        >>> data = {
        ...     "recipe_id": "recipe_vankaya_curry_001",
        ...     "name": "Brinjal Curry",
        ...     "ingredients": [{"name": "brinjal", "quantity": 3, "unit": "pieces"}],
        ...     "steps": [{"step_number": 1, "instruction": "Cut brinjals"}],
        ...     "prep_time": 10,
        ...     "servings": 4,
        ...     "nutrition": {"calories": 120, "protein": 2.5, "carbohydrates": 15, "fat": 6}
        ... }
        >>> is_valid, error = validate_recipe_schema(data)
        >>> print(is_valid)
        True
    """
    try:
        validate(instance=recipe_data, schema=RECIPE_SCHEMA)
        return True, ""
    except ValidationError as e:
        return False, f"Validation error: {e.message} at path: {'.'.join(str(p) for p in e.path)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def validate_shopping_list_schema(shopping_list_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate shopping list data against the Shopping List JSON schema.
    
    Args:
        shopping_list_data: Dictionary containing shopping list data
    
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if validation passes, False otherwise
        - error_message: Empty string if valid, error description if invalid
    
    Example:
        >>> data = {
        ...     "list_id": "list_abc123",
        ...     "recipe_id": "recipe_vankaya_curry_001",
        ...     "items": [
        ...         {
        ...             "ingredient_name": "mustard_seeds",
        ...             "quantity": 1,
        ...             "unit": "teaspoon",
        ...             "estimated_price": 5
        ...         }
        ...     ],
        ...     "total_cost": 5
        ... }
        >>> is_valid, error = validate_shopping_list_schema(data)
        >>> print(is_valid)
        True
    """
    try:
        validate(instance=shopping_list_data, schema=SHOPPING_LIST_SCHEMA)
        return True, ""
    except ValidationError as e:
        return False, f"Validation error: {e.message} at path: {'.'.join(str(p) for p in e.path)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def validate_json_file(file_path: str, schema_type: str) -> Tuple[bool, str]:
    """
    Validate a JSON file against the specified schema type.
    
    Args:
        file_path: Path to the JSON file to validate
        schema_type: Type of schema ('inventory', 'recipe', or 'shopping_list')
    
    Returns:
        Tuple of (is_valid, error_message)
    
    Raises:
        ValueError: If schema_type is not recognized
        FileNotFoundError: If file doesn't exist
    """
    if schema_type not in ['inventory', 'recipe', 'shopping_list']:
        raise ValueError(f"Unknown schema type: {schema_type}. Must be 'inventory', 'recipe', or 'shopping_list'")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {str(e)}"
    
    if schema_type == 'inventory':
        return validate_inventory_schema(data)
    elif schema_type == 'recipe':
        return validate_recipe_schema(data)
    else:  # shopping_list
        return validate_shopping_list_schema(data)


def get_schema_info(schema_type: str) -> Dict[str, Any]:
    """
    Get information about a schema including required fields and examples.
    
    Args:
        schema_type: Type of schema ('inventory', 'recipe', or 'shopping_list')
    
    Returns:
        Dictionary with schema information
    """
    schemas = {
        'inventory': INVENTORY_SCHEMA,
        'recipe': RECIPE_SCHEMA,
        'shopping_list': SHOPPING_LIST_SCHEMA
    }
    
    if schema_type not in schemas:
        raise ValueError(f"Unknown schema type: {schema_type}")
    
    schema = schemas[schema_type]
    
    return {
        'title': schema.get('title', ''),
        'description': schema.get('description', ''),
        'required_fields': schema.get('required', []),
        'properties': list(schema.get('properties', {}).keys())
    }


if __name__ == "__main__":
    # Example usage and testing
    print("Andhra Kitchen Agent - Schema Validators")
    print("=" * 50)
    
    # Test Inventory Schema
    print("\n1. Testing Inventory Schema:")
    inventory_example = {
        "total_items": 2,
        "detection_timestamp": "2024-01-15T10:30:00Z",
        "session_id": "sess_test123",
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
                "ingredient_name": "gongura",
                "ingredient_name_telugu": "గోంగూర",
                "quantity": 1,
                "unit": "bunches",
                "confidence_score": 0.88,
                "category": "leafy_green"
            }
        ]
    }
    is_valid, error = validate_inventory_schema(inventory_example)
    print(f"   Valid: {is_valid}")
    if not is_valid:
        print(f"   Error: {error}")
    
    # Test Recipe Schema
    print("\n2. Testing Recipe Schema:")
    recipe_example = {
        "recipe_id": "recipe_vankaya_curry_001",
        "name": "Brinjal Curry",
        "name_telugu": "వంకాయ కూర",
        "ingredients": [
            {"name": "brinjal", "quantity": 3, "unit": "pieces"},
            {"name": "oil", "quantity": 2, "unit": "tablespoons"}
        ],
        "steps": [
            {"step_number": 1, "instruction": "Cut brinjals into pieces"},
            {"step_number": 2, "instruction": "Heat oil and add spices"}
        ],
        "prep_time": 10,
        "cook_time": 20,
        "total_time": 30,
        "servings": 4,
        "nutrition": {
            "calories": 120,
            "protein": 2.5,
            "carbohydrates": 15,
            "fat": 6,
            "fiber": 4
        }
    }
    is_valid, error = validate_recipe_schema(recipe_example)
    print(f"   Valid: {is_valid}")
    if not is_valid:
        print(f"   Error: {error}")
    
    # Test Shopping List Schema
    print("\n3. Testing Shopping List Schema:")
    shopping_list_example = {
        "list_id": "list_abc123",
        "recipe_id": "recipe_vankaya_curry_001",
        "items": [
            {
                "ingredient_name": "mustard_seeds",
                "quantity": 1,
                "unit": "teaspoon",
                "estimated_price": 5,
                "market_section": "spices"
            }
        ],
        "total_cost": 5
    }
    is_valid, error = validate_shopping_list_schema(shopping_list_example)
    print(f"   Valid: {is_valid}")
    if not is_valid:
        print(f"   Error: {error}")
    
    print("\n" + "=" * 50)
    print("All schema validators loaded successfully!")
