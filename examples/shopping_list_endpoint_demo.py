"""
Demonstration of POST /generate-shopping-list endpoint

This script demonstrates how to use the shopping list generation endpoint
with mock data to show the complete flow.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api_handler import handle_generate_shopping_list


def build_demo_auth_context():
    """Create a lightweight auth context for local handler demos."""
    return Mock(sub='demo-user', email='demo@example.com', claims={'sub': 'demo-user'})


def demo_shopping_list_generation():
    """Demonstrate shopping list generation with mock data"""
    
    print("\n" + "=" * 70)
    print("DEMO: POST /generate-shopping-list Endpoint")
    print("=" * 70)
    
    # Sample recipe data
    sample_recipe = {
        'recipe_id': 'recipe_demo_001',
        'name': 'Brinjal Curry',
        'name_english': 'Brinjal Curry',
        'name_telugu': 'వంకాయ కూర',
        'ingredients': [
            {'name': 'brinjal', 'quantity': 3, 'unit': 'pieces'},
            {'name': 'curry_leaves', 'quantity': 10, 'unit': 'pieces'},
            {'name': 'tamarind', 'quantity': 50, 'unit': 'grams'},
            {'name': 'oil', 'quantity': 2, 'unit': 'tablespoons'},
            {'name': 'mustard_seeds', 'quantity': 1, 'unit': 'teaspoon'},
            {'name': 'turmeric', 'quantity': 0.5, 'unit': 'teaspoon'},
            {'name': 'red_chili_powder', 'quantity': 1, 'unit': 'teaspoon'},
            {'name': 'salt', 'quantity': 1, 'unit': 'teaspoon'}
        ],
        'servings': 4,
        'prep_time': 10,
        'cook_time': 20
    }
    
    # Sample current inventory (user has some ingredients)
    current_inventory = {
        'total_items': 2,
        'ingredients': [
            {'ingredient_name': 'brinjal', 'quantity': 3, 'unit': 'pieces', 'confidence_score': 0.92},
            {'ingredient_name': 'salt', 'quantity': 1, 'unit': 'kg', 'confidence_score': 0.95}
        ]
    }
    
    # Create API Gateway event
    event = {
        'httpMethod': 'POST',
        'path': '/generate-shopping-list',
        'headers': {'Authorization': 'Bearer <COGNITO_ID_TOKEN>'},
        'body': json.dumps({
            'session_id': 'demo_session_123',
            'recipe_id': 'recipe_demo_001',
            'current_inventory': current_inventory,
            'language': 'en'
        })
    }
    
    print("\n📋 Request Details:")
    print(f"   Session ID: demo_session_123")
    print(f"   Recipe: {sample_recipe['name']}")
    print(f"   Current Inventory: {current_inventory['total_items']} items")
    print(f"   Language: English")
    
    # Mock the dependencies
    with patch('src.api_handler.kitchen_agent') as mock_kitchen_agent, \
         patch('src.api_handler.get_auth_context', return_value=(build_demo_auth_context(), None)), \
         patch('src.api_handler.shopping_optimizer') as mock_shopping_optimizer, \
         patch('src.api_handler.reminder_service') as mock_reminder_service:
        
        # Mock session data
        mock_kitchen_agent.get_session.return_value = {
            'session_id': 'demo_session_123',
            'owner_sub': 'demo-user',
            'last_recipes': [sample_recipe],
            'last_inventory': current_inventory
        }
        mock_kitchen_agent.is_session_valid.return_value = True
        
        # Mock shopping list generation
        mock_shopping_list = {
            'list_id': 'list_demo_001',
            'recipe_id': 'recipe_demo_001',
            'recipe_name': 'Brinjal Curry',
            'session_id': 'demo_session_123',
            'created_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'items': [
                {
                    'ingredient_name': 'curry_leaves',
                    'quantity': 10,
                    'unit': 'pieces',
                    'estimated_price': 5,
                    'optimized_quantity': 1,
                    'optimized_unit': 'bunch',
                    'optimized_price': 5,
                    'market_section': 'spices'
                },
                {
                    'ingredient_name': 'tamarind',
                    'quantity': 50,
                    'unit': 'grams',
                    'estimated_price': 10,
                    'optimized_quantity': 100,
                    'optimized_unit': 'grams',
                    'optimized_price': 15,
                    'market_section': 'spices'
                },
                {
                    'ingredient_name': 'oil',
                    'quantity': 2,
                    'unit': 'tablespoons',
                    'estimated_price': 8,
                    'optimized_quantity': 500,
                    'optimized_unit': 'ml',
                    'optimized_price': 80,
                    'market_section': 'condiments'
                },
                {
                    'ingredient_name': 'mustard_seeds',
                    'quantity': 1,
                    'unit': 'teaspoon',
                    'estimated_price': 3,
                    'optimized_quantity': 50,
                    'optimized_unit': 'grams',
                    'optimized_price': 5,
                    'market_section': 'spices'
                },
                {
                    'ingredient_name': 'turmeric',
                    'quantity': 0.5,
                    'unit': 'teaspoon',
                    'estimated_price': 2,
                    'optimized_quantity': 50,
                    'optimized_unit': 'grams',
                    'optimized_price': 10,
                    'market_section': 'spices'
                },
                {
                    'ingredient_name': 'red_chili_powder',
                    'quantity': 1,
                    'unit': 'teaspoon',
                    'estimated_price': 4,
                    'optimized_quantity': 100,
                    'optimized_unit': 'grams',
                    'optimized_price': 20,
                    'market_section': 'spices'
                }
            ],
            'total_cost': 32,
            'optimized_total_cost': 135,
            'grouped_by_section': {
                'spices': [
                    {'ingredient_name': 'curry_leaves', 'price': 5},
                    {'ingredient_name': 'tamarind', 'price': 15},
                    {'ingredient_name': 'mustard_seeds', 'price': 5},
                    {'ingredient_name': 'turmeric', 'price': 10},
                    {'ingredient_name': 'red_chili_powder', 'price': 20}
                ],
                'condiments': [
                    {'ingredient_name': 'oil', 'price': 80}
                ]
            },
            'reminders': []
        }
        mock_shopping_optimizer.generate_shopping_list.return_value = mock_shopping_list
        
        # Mock price-sensitive detection
        mock_reminder_service.detect_price_sensitive_items.return_value = [
            {
                'content': 'Buy fresh curry leaves tomorrow',
                'reason': 'Prices are lower on Wednesdays at Gandhi Nagar market'
            }
        ]
        mock_reminder_service.schedule_reminder.return_value = 'rem_demo_001'
        
        # Call the handler
        response = handle_generate_shopping_list(event)
        
        # Parse response
        status_code = response['statusCode']
        body = json.loads(response['body'])
        
        print(f"\n✅ Response Status: {status_code}")
        
        if status_code == 200:
            print("\n📝 Shopping List Generated:")
            print(f"   List ID: {body['shopping_list']['list_id']}")
            print(f"   Recipe: {body['shopping_list']['recipe_name']}")
            print(f"   Total Items: {len(body['shopping_list']['items'])}")
            print(f"   Total Cost: ₹{body['shopping_list']['total_cost']}")
            print(f"   Optimized Cost: ₹{body['shopping_list']['optimized_total_cost']}")
            
            print("\n🛒 Items to Buy:")
            for item in body['shopping_list']['items']:
                print(f"   • {item['ingredient_name']}: {item['quantity']} {item['unit']} "
                      f"(₹{item['estimated_price']}) → Optimized: {item['optimized_quantity']} "
                      f"{item['optimized_unit']} (₹{item['optimized_price']})")
            
            print("\n📦 Grouped by Section:")
            for section, items in body['shopping_list']['grouped_by_section'].items():
                print(f"   {section.upper()}:")
                for item in items:
                    print(f"      • {item['ingredient_name']}: ₹{item['price']}")
            
            if body['reminders']:
                print("\n⏰ Reminders Scheduled:")
                for reminder in body['reminders']:
                    print(f"   • {reminder['content']}")
                    print(f"     Reason: {reminder['reason']}")
                    print(f"     Trigger Time: {reminder['trigger_time']}")
            
            print(f"\n💬 Message: {body['message']}")
        else:
            print(f"\n❌ Error: {body.get('error', 'Unknown error')}")
            print(f"   Message: {body.get('message', 'No message')}")


def demo_telugu_language():
    """Demonstrate shopping list generation with Telugu language"""
    
    print("\n" + "=" * 70)
    print("DEMO: Shopping List Generation in Telugu")
    print("=" * 70)
    
    event = {
        'httpMethod': 'POST',
        'path': '/generate-shopping-list',
        'headers': {'Authorization': 'Bearer <COGNITO_ID_TOKEN>'},
        'body': json.dumps({
            'session_id': 'demo_session_te',
            'recipe_id': 'recipe_demo_001',
            'language': 'te'
        })
    }
    
    with patch('src.api_handler.kitchen_agent') as mock_kitchen_agent, \
         patch('src.api_handler.get_auth_context', return_value=(build_demo_auth_context(), None)), \
         patch('src.api_handler.shopping_optimizer') as mock_shopping_optimizer:
        
        mock_kitchen_agent.get_session.return_value = {
            'session_id': 'demo_session_te',
            'owner_sub': 'demo-user',
            'last_recipes': [
                {
                    'recipe_id': 'recipe_demo_001',
                    'name': 'వంకాయ కూర',
                    'ingredients': []
                }
            ],
            'last_inventory': {'total_items': 0, 'ingredients': []}
        }
        mock_kitchen_agent.is_session_valid.return_value = True
        
        mock_shopping_list = {
            'list_id': 'list_demo_te',
            'recipe_id': 'recipe_demo_001',
            'items': [
                {'ingredient_name': 'curry_leaves', 'estimated_price': 5}
            ],
            'total_cost': 5,
            'reminders': []
        }
        mock_shopping_optimizer.generate_shopping_list.return_value = mock_shopping_list
        
        response = handle_generate_shopping_list(event)
        body = json.loads(response['body'])
        
        print(f"\n✅ Response Status: {response['statusCode']}")
        print(f"💬 Telugu Message: {body['message']}")


def demo_empty_shopping_list():
    """Demonstrate when all ingredients are available"""
    
    print("\n" + "=" * 70)
    print("DEMO: All Ingredients Available (Empty Shopping List)")
    print("=" * 70)
    
    event = {
        'httpMethod': 'POST',
        'path': '/generate-shopping-list',
        'headers': {'Authorization': 'Bearer <COGNITO_ID_TOKEN>'},
        'body': json.dumps({
            'session_id': 'demo_session_empty',
            'recipe_id': 'recipe_demo_001',
            'language': 'en'
        })
    }
    
    with patch('src.api_handler.kitchen_agent') as mock_kitchen_agent, \
         patch('src.api_handler.get_auth_context', return_value=(build_demo_auth_context(), None)), \
         patch('src.api_handler.shopping_optimizer') as mock_shopping_optimizer:
        
        mock_kitchen_agent.get_session.return_value = {
            'session_id': 'demo_session_empty',
            'owner_sub': 'demo-user',
            'last_recipes': [
                {
                    'recipe_id': 'recipe_demo_001',
                    'name': 'Simple Recipe',
                    'ingredients': []
                }
            ],
            'last_inventory': {'total_items': 10, 'ingredients': []}
        }
        mock_kitchen_agent.is_session_valid.return_value = True
        
        mock_shopping_list = {
            'list_id': 'list_demo_empty',
            'recipe_id': 'recipe_demo_001',
            'items': [],
            'total_cost': 0,
            'reminders': []
        }
        mock_shopping_optimizer.generate_shopping_list.return_value = mock_shopping_list
        
        response = handle_generate_shopping_list(event)
        body = json.loads(response['body'])
        
        print(f"\n✅ Response Status: {response['statusCode']}")
        print(f"💬 Message: {body['message']}")
        print(f"🛒 Items to Buy: {len(body['shopping_list']['items'])}")


if __name__ == '__main__':
    try:
        # Demo 1: Basic shopping list generation
        demo_shopping_list_generation()
        
        # Demo 2: Telugu language
        demo_telugu_language()
        
        # Demo 3: Empty shopping list
        demo_empty_shopping_list()
        
        print("\n" + "=" * 70)
        print("✅ All demos completed successfully!")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()
