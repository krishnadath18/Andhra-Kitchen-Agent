"""
Tests for Recipe Generator Memory Integration (Task 6.2)

Tests the methods that query DynamoDB for user preferences and allergies.
"""

import pytest
import boto3
from moto import mock_aws
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.recipe_generator import RecipeGenerator
from config.env import Config


@pytest.fixture
def dynamodb_setup():
    """Set up mock DynamoDB with sessions table"""
    with mock_aws():
        # Create DynamoDB resource
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create sessions table
        table = dynamodb.create_table(
            TableName=Config.SESSIONS_TABLE,
            KeySchema=[
                {'AttributeName': 'session_id', 'KeyType': 'HASH'},
                {'AttributeName': 'data_type', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'session_id', 'AttributeType': 'S'},
                {'AttributeName': 'data_type', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Wait for table to be created
        table.meta.client.get_waiter('table_exists').wait(TableName=Config.SESSIONS_TABLE)
        
        yield dynamodb, table


def test_get_user_preferences_with_data(dynamodb_setup):
    """Test retrieving user preferences when data exists"""
    dynamodb, table = dynamodb_setup
    
    # Insert test session data
    session_id = "test_session_123"
    ttl = int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
    
    table.put_item(
        Item={
            'session_id': session_id,
            'data_type': 'profile',
            'user_language': 'en',
            'preferences': {
                'low_oil': True,
                'vegetarian': True,
                'spice_level': 'medium',
                'preferred_ingredients': ['brinjal', 'gongura']
            },
            'allergies': ['peanuts', 'shellfish'],
            'created_at': datetime.now(timezone.utc).isoformat(),
            'expiry_timestamp': ttl
        }
    )
    
    # Create RecipeGenerator (it will use the mocked DynamoDB)
    generator = RecipeGenerator()
    generator.sessions_table = table
    
    # Test get_user_preferences
    preferences = generator.get_user_preferences(session_id)
    
    assert preferences is not None
    assert preferences['low_oil'] is True
    assert preferences['vegetarian'] is True
    assert preferences['spice_level'] == 'medium'
    assert 'brinjal' in preferences['preferred_ingredients']
    assert 'gongura' in preferences['preferred_ingredients']


def test_get_user_allergies_with_data(dynamodb_setup):
    """Test retrieving user allergies when data exists"""
    dynamodb, table = dynamodb_setup
    
    # Insert test session data
    session_id = "test_session_456"
    ttl = int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
    
    table.put_item(
        Item={
            'session_id': session_id,
            'data_type': 'profile',
            'user_language': 'en',
            'preferences': {},
            'allergies': ['peanuts', 'shellfish', 'dairy'],
            'created_at': datetime.now(timezone.utc).isoformat(),
            'expiry_timestamp': ttl
        }
    )
    
    # Create RecipeGenerator
    generator = RecipeGenerator()
    generator.sessions_table = table
    
    # Test get_user_allergies
    allergies = generator.get_user_allergies(session_id)
    
    assert allergies is not None
    assert len(allergies) == 3
    assert 'peanuts' in allergies
    assert 'shellfish' in allergies
    assert 'dairy' in allergies


def test_get_user_profile_with_data(dynamodb_setup):
    """Test retrieving both preferences and allergies in a single call"""
    dynamodb, table = dynamodb_setup
    
    # Insert test session data
    session_id = "test_session_789"
    ttl = int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
    
    table.put_item(
        Item={
            'session_id': session_id,
            'data_type': 'profile',
            'user_language': 'te',
            'preferences': {
                'low_oil': False,
                'vegetarian': False,
                'spice_level': 'hot'
            },
            'allergies': ['gluten'],
            'created_at': datetime.now(timezone.utc).isoformat(),
            'expiry_timestamp': ttl
        }
    )
    
    # Create RecipeGenerator
    generator = RecipeGenerator()
    generator.sessions_table = table
    
    # Test get_user_profile
    preferences, allergies = generator.get_user_profile(session_id)
    
    assert preferences is not None
    assert allergies is not None
    assert preferences['low_oil'] is False
    assert preferences['vegetarian'] is False
    assert preferences['spice_level'] == 'hot'
    assert len(allergies) == 1
    assert 'gluten' in allergies


def test_get_user_preferences_no_session(dynamodb_setup):
    """Test retrieving preferences when session doesn't exist"""
    dynamodb, table = dynamodb_setup
    
    # Create RecipeGenerator
    generator = RecipeGenerator()
    generator.sessions_table = table
    
    # Test with non-existent session
    preferences = generator.get_user_preferences("nonexistent_session")
    
    assert preferences == {}


def test_get_user_allergies_no_session(dynamodb_setup):
    """Test retrieving allergies when session doesn't exist"""
    dynamodb, table = dynamodb_setup
    
    # Create RecipeGenerator
    generator = RecipeGenerator()
    generator.sessions_table = table
    
    # Test with non-existent session
    allergies = generator.get_user_allergies("nonexistent_session")
    
    assert allergies == []


def test_get_user_profile_no_session(dynamodb_setup):
    """Test retrieving profile when session doesn't exist"""
    dynamodb, table = dynamodb_setup
    
    # Create RecipeGenerator
    generator = RecipeGenerator()
    generator.sessions_table = table
    
    # Test with non-existent session
    preferences, allergies = generator.get_user_profile("nonexistent_session")
    
    assert preferences == {}
    assert allergies == []


def test_get_user_preferences_empty_preferences(dynamodb_setup):
    """Test retrieving preferences when preferences field is empty"""
    dynamodb, table = dynamodb_setup
    
    # Insert test session data with empty preferences
    session_id = "test_session_empty"
    ttl = int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
    
    table.put_item(
        Item={
            'session_id': session_id,
            'data_type': 'profile',
            'user_language': 'en',
            'preferences': {},
            'allergies': [],
            'created_at': datetime.now(timezone.utc).isoformat(),
            'expiry_timestamp': ttl
        }
    )
    
    # Create RecipeGenerator
    generator = RecipeGenerator()
    generator.sessions_table = table
    
    # Test get_user_preferences
    preferences = generator.get_user_preferences(session_id)
    
    assert preferences == {}


def test_get_user_allergies_empty_allergies(dynamodb_setup):
    """Test retrieving allergies when allergies field is empty"""
    dynamodb, table = dynamodb_setup
    
    # Insert test session data with empty allergies
    session_id = "test_session_no_allergies"
    ttl = int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
    
    table.put_item(
        Item={
            'session_id': session_id,
            'data_type': 'profile',
            'user_language': 'en',
            'preferences': {'low_oil': True},
            'allergies': [],
            'created_at': datetime.now(timezone.utc).isoformat(),
            'expiry_timestamp': ttl
        }
    )
    
    # Create RecipeGenerator
    generator = RecipeGenerator()
    generator.sessions_table = table
    
    # Test get_user_allergies
    allergies = generator.get_user_allergies(session_id)
    
    assert allergies == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
