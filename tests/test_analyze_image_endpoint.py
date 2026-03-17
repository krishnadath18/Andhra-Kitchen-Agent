"""
Tests for POST /analyze-image endpoint

Tests Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import the handler
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api_handler import handle_analyze_image, create_response


class TestAnalyzeImageEndpoint:
    """Test suite for POST /analyze-image endpoint"""
    
    def test_missing_session_id(self):
        """Test that missing session_id returns 400 error"""
        event = {
            'httpMethod': 'POST',
            'path': '/analyze-image',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'image_id': 'img_test123',
                'language': 'en'
            }),
            'isBase64Encoded': False
        }
        
        response = handle_analyze_image(event)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_request'
        assert 'session_id' in body['message']
    
    def test_missing_image_id(self):
        """Test that missing image_id returns 400 error"""
        event = {
            'httpMethod': 'POST',
            'path': '/analyze-image',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'session_id': 'sess_test123',
                'language': 'en'
            }),
            'isBase64Encoded': False
        }
        
        response = handle_analyze_image(event)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_request'
        assert 'image_id' in body['message']
    
    @patch('src.api_handler.kitchen_agent')
    @patch('src.api_handler.vision_analyzer')
    def test_missing_s3_url_is_ignored(self, mock_analyzer, mock_kitchen_agent):
        """Legacy s3_url omission should not matter because the server resolves images internally."""
        mock_kitchen_agent.get_image_bytes.return_value = b'fake_image_data'
        mock_analyzer.analyze_image.return_value = {
            'total_items': 0,
            'ingredients': [],
            'session_id': 'sess_test123',
            'image_id': 'img_test123'
        }
        event = {
            'httpMethod': 'POST',
            'path': '/analyze-image',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'session_id': 'sess_test123',
                'image_id': 'img_test123',
                'language': 'en'
            }),
            'isBase64Encoded': False
        }
        
        response = handle_analyze_image(event)
        
        assert response['statusCode'] == 200
    
    @patch('src.api_handler.kitchen_agent')
    def test_image_retrieval_failure(self, mock_kitchen_agent):
        """Requirement 4.7: Test handling of S3 retrieval failure"""
        mock_kitchen_agent.get_image_bytes.side_effect = Exception("S3 error")
        
        event = {
            'httpMethod': 'POST',
            'path': '/analyze-image',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'session_id': 'sess_test123',
                'image_id': 'img_test123',
                'language': 'en'
            }),
            'isBase64Encoded': False
        }
        
        response = handle_analyze_image(event)
        
        assert response['statusCode'] == 422
        body = json.loads(response['body'])
        assert body['error'] == 'image_retrieval_failed'
        assert 'retrieve image' in body['message']
    
    @patch('src.api_handler.vision_analyzer')
    @patch('src.api_handler.kitchen_agent')
    def test_vision_analysis_failure(self, mock_kitchen_agent, mock_analyzer):
        """Requirement 4.7: Test handling of vision analysis failure"""
        mock_kitchen_agent.get_image_bytes.return_value = b'fake_image_data'
        
        # Mock vision analyzer to raise exception
        mock_analyzer.analyze_image.side_effect = Exception("Bedrock error")
        
        event = {
            'httpMethod': 'POST',
            'path': '/analyze-image',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'session_id': 'sess_test123',
                'image_id': 'img_test123',
                'language': 'en'
            }),
            'isBase64Encoded': False
        }
        
        response = handle_analyze_image(event)
        
        assert response['statusCode'] == 422
        body = json.loads(response['body'])
        assert body['error'] == 'analysis_failed'
        assert 'clear and well-lit' in body['message']
    
    @patch('src.api_handler.vision_analyzer')
    @patch('src.api_handler.kitchen_agent')
    def test_successful_analysis_with_ingredients(self, mock_kitchen_agent, mock_analyzer):
        """Requirements 4.1, 4.2, 4.3, 4.4, 4.5: Test successful analysis with detected ingredients"""
        mock_kitchen_agent.get_image_bytes.return_value = b'fake_image_data'
        
        # Mock vision analyzer response
        mock_inventory = {
            'total_items': 3,
            'detection_timestamp': '2024-01-15T10:31:30Z',
            'session_id': 'sess_test123',
            'image_id': 'img_test123',
            'ingredients': [
                {
                    'ingredient_name': 'brinjal',
                    'ingredient_name_telugu': 'వంకాయ',
                    'quantity': 3,
                    'unit': 'pieces',
                    'confidence_score': 0.92,
                    'category': 'vegetable'
                },
                {
                    'ingredient_name': 'curry_leaves',
                    'ingredient_name_telugu': 'కరివేపాకు',
                    'quantity': 1,
                    'unit': 'bunches',
                    'confidence_score': 0.88,
                    'category': 'spice'
                },
                {
                    'ingredient_name': 'rice',
                    'ingredient_name_telugu': 'బియ్యం',
                    'quantity': 2,
                    'unit': 'kg',
                    'confidence_score': 0.95,
                    'category': 'grain'
                }
            ]
        }
        mock_analyzer.analyze_image.return_value = mock_inventory
        
        event = {
            'httpMethod': 'POST',
            'path': '/analyze-image',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'session_id': 'sess_test123',
                'image_id': 'img_test123',
                'language': 'en'
            }),
            'isBase64Encoded': False
        }
        
        response = handle_analyze_image(event)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Requirement 4.5: Verify Inventory JSON is returned
        assert body['session_id'] == 'sess_test123'
        assert body['image_id'] == 'img_test123'
        assert 'inventory' in body
        assert body['inventory']['total_items'] == 3
        assert len(body['inventory']['ingredients']) == 3
        
        # Verify message
        assert 'Found 3 ingredients' in body['message']
        assert 'recipe suggestions' in body['message']
        
        # Verify timestamp
        assert 'timestamp' in body
        
        # Verify vision analyzer was called correctly
        mock_analyzer.analyze_image.assert_called_once_with(
            image_data=b'fake_image_data',
            session_id='sess_test123',
            image_id='img_test123'
        )
    
    @patch('src.api_handler.vision_analyzer')
    @patch('src.api_handler.kitchen_agent')
    def test_successful_analysis_no_ingredients(self, mock_kitchen_agent, mock_analyzer):
        """Requirement 4.7: Test successful analysis with no ingredients detected"""
        mock_kitchen_agent.get_image_bytes.return_value = b'fake_image_data'
        
        # Mock vision analyzer response with no ingredients
        mock_inventory = {
            'total_items': 0,
            'detection_timestamp': '2024-01-15T10:31:30Z',
            'session_id': 'sess_test123',
            'image_id': 'img_test123',
            'ingredients': []
        }
        mock_analyzer.analyze_image.return_value = mock_inventory
        
        event = {
            'httpMethod': 'POST',
            'path': '/analyze-image',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'session_id': 'sess_test123',
                'image_id': 'img_test123',
                'language': 'en'
            }),
            'isBase64Encoded': False
        }
        
        response = handle_analyze_image(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['inventory']['total_items'] == 0
        assert 'No ingredients detected' in body['message']
    
    @patch('src.api_handler.vision_analyzer')
    @patch('src.api_handler.kitchen_agent')
    def test_successful_analysis_telugu_language(self, mock_kitchen_agent, mock_analyzer):
        """Test successful analysis with Telugu language response"""
        mock_kitchen_agent.get_image_bytes.return_value = b'fake_image_data'
        
        # Mock vision analyzer response
        mock_inventory = {
            'total_items': 2,
            'detection_timestamp': '2024-01-15T10:31:30Z',
            'session_id': 'sess_test123',
            'image_id': 'img_test123',
            'ingredients': [
                {
                    'ingredient_name': 'brinjal',
                    'ingredient_name_telugu': 'వంకాయ',
                    'quantity': 3,
                    'unit': 'pieces',
                    'confidence_score': 0.92,
                    'category': 'vegetable'
                },
                {
                    'ingredient_name': 'rice',
                    'ingredient_name_telugu': 'బియ్యం',
                    'quantity': 2,
                    'unit': 'kg',
                    'confidence_score': 0.95,
                    'category': 'grain'
                }
            ]
        }
        mock_analyzer.analyze_image.return_value = mock_inventory
        
        event = {
            'httpMethod': 'POST',
            'path': '/analyze-image',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'session_id': 'sess_test123',
                'image_id': 'img_test123',
                'language': 'te'
            }),
            'isBase64Encoded': False
        }
        
        response = handle_analyze_image(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Verify Telugu message
        assert 'పదార్థాలు కనుగొనబడ్డాయి' in body['message']
        assert 'రెసిపీ సూచనలు' in body['message']
    
    @patch('src.api_handler.vision_analyzer')
    @patch('src.api_handler.kitchen_agent')
    def test_successful_analysis_single_ingredient(self, mock_kitchen_agent, mock_analyzer):
        """Test successful analysis with single ingredient (singular message)"""
        mock_kitchen_agent.get_image_bytes.return_value = b'fake_image_data'
        
        # Mock vision analyzer response with 1 ingredient
        mock_inventory = {
            'total_items': 1,
            'detection_timestamp': '2024-01-15T10:31:30Z',
            'session_id': 'sess_test123',
            'image_id': 'img_test123',
            'ingredients': [
                {
                    'ingredient_name': 'brinjal',
                    'ingredient_name_telugu': 'వంకాయ',
                    'quantity': 3,
                    'unit': 'pieces',
                    'confidence_score': 0.92,
                    'category': 'vegetable'
                }
            ]
        }
        mock_analyzer.analyze_image.return_value = mock_inventory
        
        event = {
            'httpMethod': 'POST',
            'path': '/analyze-image',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'session_id': 'sess_test123',
                'image_id': 'img_test123',
                'language': 'en'
            }),
            'isBase64Encoded': False
        }
        
        response = handle_analyze_image(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'Found 1 ingredient' in body['message']
    
    @patch('src.api_handler.vision_analyzer')
    @patch('src.api_handler.kitchen_agent')
    def test_default_language_is_english(self, mock_kitchen_agent, mock_analyzer):
        """Test that default language is English when not specified"""
        mock_kitchen_agent.get_image_bytes.return_value = b'fake_image_data'
        
        # Mock vision analyzer response
        mock_inventory = {
            'total_items': 1,
            'detection_timestamp': '2024-01-15T10:31:30Z',
            'session_id': 'sess_test123',
            'image_id': 'img_test123',
            'ingredients': [
                {
                    'ingredient_name': 'brinjal',
                    'quantity': 3,
                    'unit': 'pieces',
                    'confidence_score': 0.92,
                    'category': 'vegetable'
                }
            ]
        }
        mock_analyzer.analyze_image.return_value = mock_inventory
        
        event = {
            'httpMethod': 'POST',
            'path': '/analyze-image',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'session_id': 'sess_test123',
                'image_id': 'img_test123',
                # language not specified
            }),
            'isBase64Encoded': False
        }
        
        response = handle_analyze_image(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        # Should be English message
        assert 'Found' in body['message']
        assert 'ingredient' in body['message']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
