"""
Unit tests for POST /chat endpoint

Tests the chat endpoint implementation including:
- Request validation
- AgentCore integration
- Response formatting
- Error handling
- Rate limiting
- Session validation
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone

# Import the handler
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api_handler import handle_chat, lambda_handler


class TestChatEndpoint:
    """Test suite for POST /chat endpoint"""
    
    def test_chat_missing_session_id(self):
        """Test that missing session_id returns 400 error"""
        event = {
            'httpMethod': 'POST',
            'path': '/chat',
            'body': json.dumps({
                'message': 'Hello'
            })
        }
        
        response = handle_chat(event)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_request'
        assert 'session_id' in body['message']
    
    def test_chat_missing_message(self):
        """Test that missing message returns 400 error"""
        event = {
            'httpMethod': 'POST',
            'path': '/chat',
            'body': json.dumps({
                'session_id': 'sess_test123'
            })
        }
        
        response = handle_chat(event)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_request'
        assert 'message' in body['message']
    
    def test_chat_invalid_language(self):
        """Test that invalid language returns 400 error"""
        event = {
            'httpMethod': 'POST',
            'path': '/chat',
            'body': json.dumps({
                'session_id': 'sess_test123',
                'message': 'Hello',
                'language': 'fr'  # Invalid language
            })
        }
        
        response = handle_chat(event)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_language'
    
    @patch('src.api_handler.kitchen_agent')
    def test_chat_session_not_found(self, mock_kitchen_agent):
        """Test that non-existent session returns 404 error"""
        mock_kitchen_agent.get_session.return_value = None
        
        event = {
            'httpMethod': 'POST',
            'path': '/chat',
            'body': json.dumps({
                'session_id': 'sess_nonexistent',
                'message': 'Hello'
            })
        }
        
        response = handle_chat(event)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error'] == 'session_not_found'
    
    @patch('src.api_handler.kitchen_agent')
    def test_chat_session_expired(self, mock_kitchen_agent):
        """Test that expired session returns 401 error"""
        # Mock session data that is expired
        mock_kitchen_agent.get_session.return_value = {
            'session_id': 'sess_expired',
            'expiry_timestamp': int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp())
        }
        mock_kitchen_agent.is_session_valid.return_value = False
        
        event = {
            'httpMethod': 'POST',
            'path': '/chat',
            'body': json.dumps({
                'session_id': 'sess_expired',
                'message': 'Hello'
            })
        }
        
        response = handle_chat(event)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error'] == 'session_expired'
    
    @patch('src.api_handler.agentcore_orchestrator')
    @patch('src.api_handler.kitchen_agent')
    def test_chat_successful_english(self, mock_kitchen_agent, mock_orchestrator):
        """Test successful chat message in English"""
        # Mock valid session
        mock_kitchen_agent.get_session.return_value = {
            'session_id': 'sess_test123',
            'user_language': 'en',
            'expiry_timestamp': int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
        }
        mock_kitchen_agent.is_session_valid.return_value = True
        mock_kitchen_agent.update_session_data.return_value = True
        
        # Mock AgentCore response
        mock_orchestrator.invoke_agent.return_value = {
            'workflow_id': 'workflow_abc123',
            'session_id': 'sess_test123',
            'subtask_results': {},
            'final_response': 'Hello! How can I help you today?',
            'execution_time_ms': 1234,
            'status': 'completed',
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/chat',
            'body': json.dumps({
                'session_id': 'sess_test123',
                'message': 'Hello',
                'language': 'en'
            })
        }
        
        response = handle_chat(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['response'] == 'Hello! How can I help you today?'
        assert body['workflow_id'] == 'workflow_abc123'
        assert body['status'] == 'completed'
        assert 'execution_time_ms' in body
        assert 'suggested_actions' in body
        assert 'timestamp' in body
        
        # Verify AgentCore was called with correct parameters
        mock_orchestrator.invoke_agent.assert_called_once()
        call_args = mock_orchestrator.invoke_agent.call_args
        assert call_args[1]['user_request'] == 'Hello'
        assert call_args[1]['session_id'] == 'sess_test123'
        assert call_args[1]['context']['language'] == 'en'
        
        # Verify session was updated with conversation
        mock_kitchen_agent.update_session_data.assert_called_once()
    
    @patch('src.api_handler.agentcore_orchestrator')
    @patch('src.api_handler.kitchen_agent')
    def test_chat_successful_telugu(self, mock_kitchen_agent, mock_orchestrator):
        """Test successful chat message in Telugu"""
        # Mock valid session
        mock_kitchen_agent.get_session.return_value = {
            'session_id': 'sess_test123',
            'user_language': 'te',
            'expiry_timestamp': int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
        }
        mock_kitchen_agent.is_session_valid.return_value = True
        mock_kitchen_agent.update_session_data.return_value = True
        
        # Mock AgentCore response in Telugu
        mock_orchestrator.invoke_agent.return_value = {
            'workflow_id': 'workflow_abc123',
            'session_id': 'sess_test123',
            'subtask_results': {},
            'final_response': 'నమస్కారం! నేను మీకు ఎలా సహాయం చేయగలను?',
            'execution_time_ms': 1234,
            'status': 'completed',
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/chat',
            'body': json.dumps({
                'session_id': 'sess_test123',
                'message': 'నమస్కారం',
                'language': 'te'
            })
        }
        
        response = handle_chat(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['response'] == 'నమస్కారం! నేను మీకు ఎలా సహాయం చేయగలను?'
        assert body['status'] == 'completed'
        
        # Verify language was passed to AgentCore
        call_args = mock_orchestrator.invoke_agent.call_args
        assert call_args[1]['context']['language'] == 'te'
    
    @patch('src.api_handler.agentcore_orchestrator')
    @patch('src.api_handler.kitchen_agent')
    def test_chat_with_context(self, mock_kitchen_agent, mock_orchestrator):
        """Test chat message with context (image uploaded)"""
        # Mock valid session
        mock_kitchen_agent.get_session.return_value = {
            'session_id': 'sess_test123',
            'user_language': 'en',
            'expiry_timestamp': int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
        }
        mock_kitchen_agent.is_session_valid.return_value = True
        mock_kitchen_agent.update_session_data.return_value = True
        
        # Mock AgentCore response with inventory
        mock_orchestrator.invoke_agent.return_value = {
            'workflow_id': 'workflow_abc123',
            'session_id': 'sess_test123',
            'subtask_results': {
                'subtask_1': {
                    'inventory': {
                        'total_items': 3,
                        'ingredients': []
                    }
                }
            },
            'final_response': 'Found 3 ingredients! Would you like recipe suggestions?',
            'execution_time_ms': 5234,
            'status': 'completed',
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/chat',
            'body': json.dumps({
                'session_id': 'sess_test123',
                'message': 'I uploaded a photo. Can you suggest recipes?',
                'language': 'en',
                'context': {
                    'image_uploaded': True,
                    'image_id': 'img_xyz789'
                }
            })
        }
        
        response = handle_chat(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'completed'
        assert 'view_recipes' in body['suggested_actions']
        
        # Verify context was passed to AgentCore
        call_args = mock_orchestrator.invoke_agent.call_args
        assert call_args[1]['context']['image_uploaded'] is True
        assert call_args[1]['context']['image_id'] == 'img_xyz789'
    
    @patch('src.api_handler.agentcore_orchestrator')
    @patch('src.api_handler.kitchen_agent')
    def test_chat_with_recipes_result(self, mock_kitchen_agent, mock_orchestrator):
        """Test chat response includes shopping list action when recipes are generated"""
        # Mock valid session
        mock_kitchen_agent.get_session.return_value = {
            'session_id': 'sess_test123',
            'user_language': 'en',
            'expiry_timestamp': int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
        }
        mock_kitchen_agent.is_session_valid.return_value = True
        mock_kitchen_agent.update_session_data.return_value = True
        
        # Mock AgentCore response with recipes
        mock_orchestrator.invoke_agent.return_value = {
            'workflow_id': 'workflow_abc123',
            'session_id': 'sess_test123',
            'subtask_results': {
                'subtask_1': {
                    'recipes': [
                        {'recipe_id': 'recipe_1', 'name': 'Brinjal Curry'},
                        {'recipe_id': 'recipe_2', 'name': 'Dal Fry'}
                    ]
                }
            },
            'final_response': 'Here are 2 recipe suggestions!',
            'execution_time_ms': 8500,
            'status': 'completed',
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/chat',
            'body': json.dumps({
                'session_id': 'sess_test123',
                'message': 'Show me recipes',
                'language': 'en'
            })
        }
        
        response = handle_chat(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'view_recipes' in body['suggested_actions']
        assert 'generate_shopping_list' in body['suggested_actions']
    
    @patch('src.api_handler.agentcore_orchestrator')
    @patch('src.api_handler.kitchen_agent')
    def test_chat_agentcore_failure(self, mock_kitchen_agent, mock_orchestrator):
        """Test that AgentCore failure returns 500 error"""
        # Mock valid session
        mock_kitchen_agent.get_session.return_value = {
            'session_id': 'sess_test123',
            'user_language': 'en',
            'expiry_timestamp': int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
        }
        mock_kitchen_agent.is_session_valid.return_value = True
        
        # Mock AgentCore failure
        mock_orchestrator.invoke_agent.side_effect = Exception('Bedrock API error')
        
        event = {
            'httpMethod': 'POST',
            'path': '/chat',
            'body': json.dumps({
                'session_id': 'sess_test123',
                'message': 'Hello'
            })
        }
        
        response = handle_chat(event)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['error'] == 'agent_invocation_failed'
    
    @patch('src.api_handler.agentcore_orchestrator')
    @patch('src.api_handler.kitchen_agent')
    def test_chat_default_language(self, mock_kitchen_agent, mock_orchestrator):
        """Test that language defaults to 'en' when not provided"""
        # Mock valid session
        mock_kitchen_agent.get_session.return_value = {
            'session_id': 'sess_test123',
            'user_language': 'en',
            'expiry_timestamp': int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
        }
        mock_kitchen_agent.is_session_valid.return_value = True
        mock_kitchen_agent.update_session_data.return_value = True
        
        # Mock AgentCore response
        mock_orchestrator.invoke_agent.return_value = {
            'workflow_id': 'workflow_abc123',
            'session_id': 'sess_test123',
            'subtask_results': {},
            'final_response': 'Hello!',
            'execution_time_ms': 1000,
            'status': 'completed',
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/chat',
            'body': json.dumps({
                'session_id': 'sess_test123',
                'message': 'Hello'
                # No language specified
            })
        }
        
        response = handle_chat(event)
        
        assert response['statusCode'] == 200
        
        # Verify default language was used
        call_args = mock_orchestrator.invoke_agent.call_args
        assert call_args[1]['context']['language'] == 'en'
    
    @patch('src.api_handler.agentcore_orchestrator')
    @patch('src.api_handler.kitchen_agent')
    def test_chat_suggested_actions_upload_image(self, mock_kitchen_agent, mock_orchestrator):
        """Test that suggested actions include upload_image when appropriate"""
        # Mock valid session
        mock_kitchen_agent.get_session.return_value = {
            'session_id': 'sess_test123',
            'user_language': 'en',
            'expiry_timestamp': int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
        }
        mock_kitchen_agent.is_session_valid.return_value = True
        mock_kitchen_agent.update_session_data.return_value = True
        
        # Mock AgentCore response with no specific results
        mock_orchestrator.invoke_agent.return_value = {
            'workflow_id': 'workflow_abc123',
            'session_id': 'sess_test123',
            'subtask_results': {},
            'final_response': 'I can help you with recipes. Please upload a photo of your ingredients.',
            'execution_time_ms': 1000,
            'status': 'completed',
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/chat',
            'body': json.dumps({
                'session_id': 'sess_test123',
                'message': 'I want to cook something',
                'language': 'en'
            })
        }
        
        response = handle_chat(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'upload_image' in body['suggested_actions']
    
    def test_chat_via_lambda_handler(self):
        """Test chat endpoint through lambda_handler routing"""
        with patch('src.api_handler.kitchen_agent') as mock_kitchen_agent, \
             patch('src.api_handler.agentcore_orchestrator') as mock_orchestrator:
            
            # Mock valid session
            mock_kitchen_agent.get_session.return_value = {
                'session_id': 'sess_test123',
                'user_language': 'en',
                'expiry_timestamp': int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
            }
            mock_kitchen_agent.is_session_valid.return_value = True
            mock_kitchen_agent.update_session_data.return_value = True
            
            # Mock AgentCore response
            mock_orchestrator.invoke_agent.return_value = {
                'workflow_id': 'workflow_abc123',
                'session_id': 'sess_test123',
                'subtask_results': {},
                'final_response': 'Hello!',
                'execution_time_ms': 1000,
                'status': 'completed',
                'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
            }
            
            event = {
                'httpMethod': 'POST',
                'path': '/chat',
                'body': json.dumps({
                    'session_id': 'sess_test123',
                    'message': 'Hello'
                })
            }
            
            response = lambda_handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert 'response' in body
            assert 'workflow_id' in body


class TestChatEndpointIntegration:
    """Integration tests for chat endpoint with rate limiting"""
    
    @patch('src.api_handler.agentcore_orchestrator')
    @patch('src.api_handler.kitchen_agent')
    def test_chat_response_format(self, mock_kitchen_agent, mock_orchestrator):
        """Test that response format matches specification"""
        # Mock valid session
        mock_kitchen_agent.get_session.return_value = {
            'session_id': 'sess_test123',
            'user_language': 'en',
            'expiry_timestamp': int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
        }
        mock_kitchen_agent.is_session_valid.return_value = True
        mock_kitchen_agent.update_session_data.return_value = True
        
        # Mock AgentCore response
        mock_orchestrator.invoke_agent.return_value = {
            'workflow_id': 'workflow_abc123',
            'session_id': 'sess_test123',
            'subtask_results': {
                'subtask_1': {
                    'inventory': {'total_items': 3},
                    'recipes': [{'recipe_id': 'recipe_1'}]
                }
            },
            'final_response': '✅ Found 3 ingredients! ✅ Generated 2 recipes!',
            'execution_time_ms': 5234,
            'status': 'completed',
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/chat',
            'body': json.dumps({
                'session_id': 'sess_test123',
                'message': 'I uploaded a photo. Can you suggest recipes?',
                'language': 'en',
                'context': {
                    'image_uploaded': True,
                    'image_id': 'img_xyz789'
                }
            })
        }
        
        response = handle_chat(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Verify all required fields are present
        assert 'response' in body
        assert 'suggested_actions' in body
        assert 'workflow_id' in body
        assert 'status' in body
        assert 'execution_time_ms' in body
        assert 'timestamp' in body
        
        # Verify field types
        assert isinstance(body['response'], str)
        assert isinstance(body['suggested_actions'], list)
        assert isinstance(body['workflow_id'], str)
        assert isinstance(body['status'], str)
        assert isinstance(body['execution_time_ms'], int)
        assert isinstance(body['timestamp'], str)
        
        # Verify suggested actions
        assert 'view_recipes' in body['suggested_actions']
        assert 'generate_shopping_list' in body['suggested_actions']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
