"""
Unit tests for AgentCore Configuration

Tests tool registration, parameter validation, and configuration generation.
"""

import unittest
import json
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agentcore_config import AgentCoreConfig


class TestAgentCoreConfig(unittest.TestCase):
    """Test cases for AgentCore configuration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = AgentCoreConfig()
    
    def test_foundation_model_configuration(self):
        """Test that foundation model is correctly configured"""
        self.assertEqual(
            AgentCoreConfig.FOUNDATION_MODEL,
            "anthropic.claude-3-haiku-20240307-v1:0"
        )
    
    def test_instruction_prompt_exists(self):
        """Test that instruction prompt is defined and non-empty"""
        self.assertIsNotNone(AgentCoreConfig.INSTRUCTION_PROMPT)
        self.assertGreater(len(AgentCoreConfig.INSTRUCTION_PROMPT), 100)
        self.assertIn("Andhra Pradesh", AgentCoreConfig.INSTRUCTION_PROMPT)
    
    def test_tool_definitions_count(self):
        """Test that all 4 tools are defined"""
        self.assertEqual(len(AgentCoreConfig.TOOL_DEFINITIONS), 4)
    
    def test_tool_names(self):
        """Test that all expected tools are present"""
        tool_names = [tool['name'] for tool in AgentCoreConfig.TOOL_DEFINITIONS]
        expected_tools = [
            'vision_analyzer',
            'recipe_generator',
            'shopping_optimizer',
            'reminder_service'
        ]
        
        for expected_tool in expected_tools:
            self.assertIn(expected_tool, tool_names)
    
    def test_vision_analyzer_tool_schema(self):
        """Test vision_analyzer tool has correct schema"""
        tool = AgentCoreConfig.get_tool_by_name('vision_analyzer')
        
        self.assertIsNotNone(tool)
        self.assertEqual(tool['name'], 'vision_analyzer')
        self.assertIn('description', tool)
        self.assertIn('parameters', tool)
        
        # Check required parameters
        params = tool['parameters']
        self.assertIn('required', params)
        self.assertIn('session_id', params['required'])
        self.assertIn('image_id', params['required'])
        
        # Check parameter properties
        properties = params['properties']
        self.assertIn('session_id', properties)
        self.assertIn('image_id', properties)
    
    def test_recipe_generator_tool_schema(self):
        """Test recipe_generator tool has correct schema"""
        tool = AgentCoreConfig.get_tool_by_name('recipe_generator')
        
        self.assertIsNotNone(tool)
        self.assertEqual(tool['name'], 'recipe_generator')
        
        # Check required parameters
        params = tool['parameters']
        self.assertIn('inventory', params['required'])
        self.assertIn('session_id', params['required'])
        self.assertIn('language', params['required'])
        
        # Check optional parameters exist
        properties = params['properties']
        self.assertIn('preferences', properties)
        self.assertIn('allergies', properties)
        self.assertIn('count', properties)
    
    def test_shopping_optimizer_tool_schema(self):
        """Test shopping_optimizer tool has correct schema"""
        tool = AgentCoreConfig.get_tool_by_name('shopping_optimizer')
        
        self.assertIsNotNone(tool)
        self.assertEqual(tool['name'], 'shopping_optimizer')
        
        # Check required parameters
        params = tool['parameters']
        self.assertIn('recipe_id', params['required'])
        self.assertIn('recipe', params['required'])
        self.assertIn('inventory', params['required'])
        self.assertIn('session_id', params['required'])
    
    def test_reminder_service_tool_schema(self):
        """Test reminder_service tool has correct schema"""
        tool = AgentCoreConfig.get_tool_by_name('reminder_service')
        
        self.assertIsNotNone(tool)
        self.assertEqual(tool['name'], 'reminder_service')
        
        # Check required parameters
        params = tool['parameters']
        self.assertIn('session_id', params['required'])
        self.assertIn('content', params['required'])
        self.assertIn('trigger_time', params['required'])
        self.assertIn('reason', params['required'])
    
    def test_get_tool_schemas(self):
        """Test getting all tool schemas"""
        schemas = AgentCoreConfig.get_tool_schemas()
        
        self.assertEqual(len(schemas), 4)
        self.assertIsInstance(schemas, list)
        
        for schema in schemas:
            self.assertIn('name', schema)
            self.assertIn('description', schema)
            self.assertIn('parameters', schema)
    
    def test_get_tool_by_name_valid(self):
        """Test retrieving a tool by valid name"""
        tool = AgentCoreConfig.get_tool_by_name('vision_analyzer')
        
        self.assertIsNotNone(tool)
        self.assertEqual(tool['name'], 'vision_analyzer')
    
    def test_get_tool_by_name_invalid(self):
        """Test retrieving a tool by invalid name returns None"""
        tool = AgentCoreConfig.get_tool_by_name('nonexistent_tool')
        
        self.assertIsNone(tool)
    
    def test_validate_tool_parameters_valid(self):
        """Test parameter validation with valid parameters"""
        valid_params = {
            'session_id': 'sess_abc123',
            'image_id': 'img_xyz789'
        }
        
        is_valid, error = AgentCoreConfig.validate_tool_parameters(
            'vision_analyzer',
            valid_params
        )
        
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_validate_tool_parameters_missing_required(self):
        """Test parameter validation with missing required parameter"""
        invalid_params = {
            'session_id': 'sess_abc123'
            # Missing image_id
        }
        
        is_valid, error = AgentCoreConfig.validate_tool_parameters(
            'vision_analyzer',
            invalid_params
        )
        
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertIn('Missing required parameter', error)
    
    def test_validate_tool_parameters_invalid_tool(self):
        """Test parameter validation with invalid tool name"""
        is_valid, error = AgentCoreConfig.validate_tool_parameters(
            'nonexistent_tool',
            {}
        )
        
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertIn('not found', error)
    
    def test_validate_tool_parameters_wrong_type(self):
        """Test parameter validation with wrong parameter type"""
        invalid_params = {
            'session_id': 123,
            'image_id': 'img_xyz789'
        }
        
        is_valid, error = AgentCoreConfig.validate_tool_parameters(
            'vision_analyzer',
            invalid_params
        )
        
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertIn('must be a string', error)
    
    def test_create_agent_configuration(self):
        """Test creating complete agent configuration"""
        config = self.config.create_agent_configuration('test-agent')
        
        self.assertIn('agentName', config)
        self.assertEqual(config['agentName'], 'test-agent')
        self.assertIn('foundationModel', config)
        self.assertEqual(config['foundationModel'], AgentCoreConfig.FOUNDATION_MODEL)
        self.assertIn('instruction', config)
        self.assertIn('description', config)
        self.assertIn('tools', config)
        self.assertEqual(len(config['tools']), 4)
    
    def test_format_tools_for_bedrock(self):
        """Test formatting tools for Bedrock API"""
        formatted_tools = self.config._format_tools_for_bedrock()
        
        self.assertEqual(len(formatted_tools), 4)
        
        for tool in formatted_tools:
            self.assertIn('toolSpec', tool)
            self.assertIn('name', tool['toolSpec'])
            self.assertIn('description', tool['toolSpec'])
            self.assertIn('inputSchema', tool['toolSpec'])
            self.assertIn('json', tool['toolSpec']['inputSchema'])
    
    def test_recipe_generator_preferences_schema(self):
        """Test recipe_generator preferences parameter schema"""
        tool = AgentCoreConfig.get_tool_by_name('recipe_generator')
        preferences = tool['parameters']['properties']['preferences']
        
        self.assertIn('properties', preferences)
        prefs_props = preferences['properties']
        
        # Check low_oil preference
        self.assertIn('low_oil', prefs_props)
        self.assertEqual(prefs_props['low_oil']['type'], 'boolean')
        
        # Check vegetarian preference
        self.assertIn('vegetarian', prefs_props)
        self.assertEqual(prefs_props['vegetarian']['type'], 'boolean')
        
        # Check spice_level preference
        self.assertIn('spice_level', prefs_props)
        self.assertEqual(prefs_props['spice_level']['type'], 'string')
        self.assertIn('enum', prefs_props['spice_level'])
        self.assertIn('mild', prefs_props['spice_level']['enum'])
        self.assertIn('medium', prefs_props['spice_level']['enum'])
        self.assertIn('hot', prefs_props['spice_level']['enum'])
    
    def test_recipe_generator_count_constraints(self):
        """Test recipe_generator count parameter has min/max constraints"""
        tool = AgentCoreConfig.get_tool_by_name('recipe_generator')
        count_param = tool['parameters']['properties']['count']
        
        self.assertEqual(count_param['type'], 'integer')
        self.assertEqual(count_param['minimum'], 2)
        self.assertEqual(count_param['maximum'], 5)
    
    def test_reminder_service_priority_enum(self):
        """Test reminder_service priority parameter has correct enum values"""
        tool = AgentCoreConfig.get_tool_by_name('reminder_service')
        priority_param = tool['parameters']['properties']['priority']
        
        self.assertEqual(priority_param['type'], 'string')
        self.assertIn('enum', priority_param)
        self.assertIn('low', priority_param['enum'])
        self.assertIn('medium', priority_param['enum'])
        self.assertIn('high', priority_param['enum'])
    
    def test_all_tools_have_descriptions(self):
        """Test that all tools have non-empty descriptions"""
        for tool in AgentCoreConfig.TOOL_DEFINITIONS:
            self.assertIn('description', tool)
            self.assertGreater(len(tool['description']), 50)
    
    def test_all_required_parameters_have_descriptions(self):
        """Test that all required parameters have descriptions"""
        for tool in AgentCoreConfig.TOOL_DEFINITIONS:
            params = tool['parameters']
            required = params.get('required', [])
            properties = params.get('properties', {})
            
            for req_param in required:
                self.assertIn(req_param, properties)
                self.assertIn('description', properties[req_param])
                self.assertGreater(len(properties[req_param]['description']), 10)


class TestAgentCoreConfigIntegration(unittest.TestCase):
    """Integration tests for AgentCore configuration"""
    
    def test_vision_analyzer_complete_workflow(self):
        """Test complete workflow for vision_analyzer tool"""
        # Get tool schema
        tool = AgentCoreConfig.get_tool_by_name('vision_analyzer')
        self.assertIsNotNone(tool)
        
        # Prepare valid parameters
        params = {
            'session_id': 'sess_123',
            'image_id': 'img_456'
        }
        
        # Validate parameters
        is_valid, error = AgentCoreConfig.validate_tool_parameters('vision_analyzer', params)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_recipe_generator_complete_workflow(self):
        """Test complete workflow for recipe_generator tool"""
        # Get tool schema
        tool = AgentCoreConfig.get_tool_by_name('recipe_generator')
        self.assertIsNotNone(tool)
        
        # Prepare valid parameters with all optional fields
        params = {
            'inventory': {
                'total_items': 3,
                'ingredients': [
                    {'ingredient_name': 'brinjal', 'quantity': 3, 'unit': 'pieces'}
                ]
            },
            'session_id': 'sess_123',
            'preferences': {
                'low_oil': True,
                'vegetarian': True,
                'spice_level': 'medium'
            },
            'allergies': ['peanuts'],
            'language': 'en',
            'count': 3
        }
        
        # Validate parameters
        is_valid, error = AgentCoreConfig.validate_tool_parameters('recipe_generator', params)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_shopping_optimizer_complete_workflow(self):
        """Test complete workflow for shopping_optimizer tool"""
        # Get tool schema
        tool = AgentCoreConfig.get_tool_by_name('shopping_optimizer')
        self.assertIsNotNone(tool)
        
        # Prepare valid parameters
        params = {
            'recipe_id': 'recipe_123',
            'recipe': {
                'name': 'Brinjal Curry',
                'ingredients': [
                    {'name': 'brinjal', 'quantity': 3, 'unit': 'pieces'}
                ]
            },
            'inventory': {
                'total_items': 1,
                'ingredients': [
                    {'ingredient_name': 'rice', 'quantity': 1, 'unit': 'kg'}
                ]
            },
            'session_id': 'sess_123',
            'language': 'en'
        }
        
        # Validate parameters
        is_valid, error = AgentCoreConfig.validate_tool_parameters('shopping_optimizer', params)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_reminder_service_complete_workflow(self):
        """Test complete workflow for reminder_service tool"""
        # Get tool schema
        tool = AgentCoreConfig.get_tool_by_name('reminder_service')
        self.assertIsNotNone(tool)
        
        # Prepare valid parameters
        params = {
            'session_id': 'sess_123',
            'content': 'Buy fresh curry leaves tomorrow',
            'trigger_time': '2024-01-16T08:00:00Z',
            'reason': 'Prices are lower on Wednesdays at Gandhi Nagar market',
            'priority': 'medium'
        }
        
        # Validate parameters
        is_valid, error = AgentCoreConfig.validate_tool_parameters('reminder_service', params)
        self.assertTrue(is_valid)
        self.assertIsNone(error)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
