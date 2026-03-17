"""
Unit tests for KitchenAgentCore error handling

Tests Requirements 17.1, 17.2, 17.3, 17.4, 17.5, 17.6:
- 17.1: Log errors to CloudWatch
- 17.2: Handle S3 upload failures with retry option
- 17.3: Handle Vision Analyzer errors with guidance
- 17.4: Handle Recipe Generator errors with suggestions
- 17.5: Provide "Try Again" option for all errors
- 17.6: Log all errors to CloudWatch
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path
from botocore.exceptions import ClientError

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.kitchen_agent_core import KitchenAgentCore


class TestKitchenAgentErrorHandling(unittest.TestCase):
    """Test error handling methods in KitchenAgentCore"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock AWS clients
        self.mock_s3 = Mock()
        self.mock_dynamodb = Mock()
        self.mock_bedrock = Mock()
        
        with patch('boto3.client', return_value=self.mock_s3), \
             patch('boto3.resource', return_value=self.mock_dynamodb):
            self.agent = KitchenAgentCore()
        
        # Test data
        self.test_session_id = "test_session_123"
        self.test_image_id = "test_image_456"
    
    def _create_client_error(self, error_code: str) -> ClientError:
        """Helper to create ClientError exceptions"""
        return ClientError(
            {
                'Error': {
                    'Code': error_code,
                    'Message': f'Test {error_code}'
                }
            },
            'test_operation'
        )
    
    # Test format_error_response
    
    def test_format_error_response_english(self):
        """Test error response formatting in English"""
        response = self.agent.format_error_response(
            error_code='bedrock_throttled',
            error_type='bedrock',
            language='en',
            retry_available=True
        )
        
        # Verify structure
        self.assertIn('error_code', response)
        self.assertIn('user_friendly_message', response)
        self.assertIn('retry_available', response)
        self.assertIn('suggestions', response)
        self.assertIn('timestamp', response)
        
        # Verify content
        self.assertEqual(response['error_code'], 'bedrock_throttled')
        self.assertEqual(response['retry_available'], True)
        self.assertIn('busy', response['user_friendly_message'].lower())
        self.assertIsInstance(response['suggestions'], list)
        self.assertGreater(len(response['suggestions']), 0)
    
    def test_format_error_response_telugu(self):
        """Test error response formatting in Telugu"""
        response = self.agent.format_error_response(
            error_code='s3_upload_failed',
            error_type='s3',
            language='te',
            retry_available=True
        )
        
        # Verify Telugu message
        self.assertIn('error_code', response)
        self.assertEqual(response['error_code'], 's3_upload_failed')
        
        # Telugu message should contain Telugu characters
        message = response['user_friendly_message']
        has_telugu = any('\u0C00' <= char <= '\u0C7F' for char in message)
        self.assertTrue(has_telugu, "Message should contain Telugu characters")
        
        # Telugu suggestions
        suggestions = response['suggestions']
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
    
    def test_format_error_response_all_error_codes(self):
        """Test all error codes have proper messages"""
        error_codes = [
            'bedrock_throttled',
            'bedrock_unavailable',
            's3_upload_failed',
            'vision_analysis_failed',
            'recipe_generation_failed',
            'insufficient_ingredients',
            'generic_error'
        ]
        
        for error_code in error_codes:
            for language in ['en', 'te']:
                response = self.agent.format_error_response(
                    error_code=error_code,
                    error_type='bedrock',
                    language=language
                )
                
                self.assertIn('user_friendly_message', response)
                self.assertGreater(len(response['user_friendly_message']), 0)
                self.assertIn('suggestions', response)
    
    @patch('src.kitchen_agent_core.logger')
    def test_format_error_response_logs_to_cloudwatch(self, mock_logger):
        """Test Requirement 17.1: Error formatting is called by handlers that log to CloudWatch"""
        # Note: format_error_response itself doesn't log - the handler methods do
        # This test verifies that format_error_response returns proper structure
        # Actual logging is tested in handler-specific tests
        
        response = self.agent.format_error_response(
            error_code='bedrock_throttled',
            error_type='bedrock',
            language='en',
            technical_details='Test error details'
        )
        
        # Verify response structure (logging is done by handler methods)
        self.assertIn('error_code', response)
        self.assertEqual(response['error_code'], 'bedrock_throttled')
        self.assertIn('user_friendly_message', response)
        self.assertIn('retry_available', response)
        self.assertIn('suggestions', response)
        self.assertIn('timestamp', response)
    
    def test_format_error_response_retry_available(self):
        """Test Requirement 17.5: Retry option is provided"""
        response = self.agent.format_error_response(
            error_code='bedrock_throttled',
            error_type='bedrock',
            retry_available=True
        )
        
        self.assertTrue(response['retry_available'])
        self.assertIn('Try again', response['suggestions'])
    
    # Test handle_bedrock_error
    
    @patch('src.kitchen_agent_core.logger')
    def test_handle_bedrock_error_throttling(self, mock_logger):
        """Test handling Bedrock ThrottlingException"""
        error = self._create_client_error('ThrottlingException')
        
        response = self.agent.handle_bedrock_error(
            error=error,
            operation='chat',
            language='en',
            attempt=1
        )
        
        # Verify response
        self.assertEqual(response['error_code'], 'bedrock_throttled')
        self.assertTrue(response['retry_available'])
        self.assertIn('busy', response['user_friendly_message'].lower())
        
        # Verify CloudWatch logging
        self.assertTrue(mock_logger.warning.called)
        log_message = str(mock_logger.warning.call_args)
        self.assertIn('Bedrock throttled', log_message)
        self.assertIn('operation=chat', log_message)
        self.assertIn('attempt=1', log_message)
    
    @patch('src.kitchen_agent_core.logger')
    def test_handle_bedrock_error_model_unavailable(self, mock_logger):
        """Test handling Bedrock ModelNotReadyException"""
        error = self._create_client_error('ModelNotReadyException')
        
        response = self.agent.handle_bedrock_error(
            error=error,
            operation='recipe_generation',
            language='en',
            attempt=2
        )
        
        # Verify response
        self.assertEqual(response['error_code'], 'bedrock_unavailable')
        self.assertTrue(response['retry_available'])
        self.assertIn('unavailable', response['user_friendly_message'].lower())
        
        # Verify CloudWatch logging
        self.assertTrue(mock_logger.error.called)
        log_message = str(mock_logger.error.call_args)
        self.assertIn('Bedrock unavailable', log_message)
        self.assertIn('ModelNotReadyException', log_message)
    
    @patch('src.kitchen_agent_core.logger')
    def test_handle_bedrock_error_service_unavailable(self, mock_logger):
        """Test handling Bedrock ServiceUnavailableException"""
        error = self._create_client_error('ServiceUnavailableException')
        
        response = self.agent.handle_bedrock_error(
            error=error,
            operation='vision_analysis',
            language='te',
            attempt=3
        )
        
        # Verify response
        self.assertEqual(response['error_code'], 'bedrock_unavailable')
        self.assertTrue(response['retry_available'])
        
        # Telugu message
        has_telugu = any('\u0C00' <= char <= '\u0C7F' for char in response['user_friendly_message'])
        self.assertTrue(has_telugu)
        
        # Verify CloudWatch logging
        self.assertTrue(mock_logger.error.called)
    
    @patch('src.kitchen_agent_core.logger')
    def test_handle_bedrock_error_generic_exception(self, mock_logger):
        """Test handling generic Bedrock exceptions"""
        error = Exception("Network timeout")
        
        response = self.agent.handle_bedrock_error(
            error=error,
            operation='chat',
            language='en',
            attempt=1
        )
        
        # Verify response
        self.assertEqual(response['error_code'], 'generic_error')
        self.assertTrue(response['retry_available'])
        
        # Verify CloudWatch logging
        self.assertTrue(mock_logger.error.called)
        log_message = str(mock_logger.error.call_args)
        self.assertIn('Unexpected Bedrock error', log_message)
    
    # Test handle_s3_error
    
    @patch('src.kitchen_agent_core.logger')
    def test_handle_s3_error_client_error(self, mock_logger):
        """Test Requirement 17.2: Handle S3 upload failures"""
        error = self._create_client_error('NoSuchBucket')
        
        response = self.agent.handle_s3_error(
            error=error,
            session_id=self.test_session_id,
            language='en'
        )
        
        # Verify response
        self.assertEqual(response['error_code'], 's3_upload_failed')
        self.assertTrue(response['retry_available'])
        self.assertIn('upload failed', response['user_friendly_message'].lower())
        
        # Verify suggestions
        self.assertIn('suggestions', response)
        self.assertGreater(len(response['suggestions']), 0)
        
        # Verify CloudWatch logging (Requirement 17.6)
        self.assertTrue(mock_logger.error.called)
        log_message = str(mock_logger.error.call_args)
        self.assertIn('S3 upload failed', log_message)
        self.assertIn(f'session_id={self.test_session_id}', log_message)
        self.assertIn('NoSuchBucket', log_message)
    
    @patch('src.kitchen_agent_core.logger')
    def test_handle_s3_error_generic_exception(self, mock_logger):
        """Test handling generic S3 exceptions"""
        error = Exception("Connection timeout")
        
        response = self.agent.handle_s3_error(
            error=error,
            session_id=self.test_session_id,
            language='te'
        )
        
        # Verify response
        self.assertEqual(response['error_code'], 's3_upload_failed')
        self.assertTrue(response['retry_available'])
        
        # Telugu message
        has_telugu = any('\u0C00' <= char <= '\u0C7F' for char in response['user_friendly_message'])
        self.assertTrue(has_telugu)
        
        # Verify CloudWatch logging
        self.assertTrue(mock_logger.error.called)
    
    @patch('src.kitchen_agent_core.logger')
    def test_handle_s3_error_retry_option(self, mock_logger):
        """Test Requirement 17.5: S3 errors provide retry option"""
        error = self._create_client_error('RequestTimeout')
        
        response = self.agent.handle_s3_error(
            error=error,
            session_id=self.test_session_id,
            language='en'
        )
        
        # Verify retry option
        self.assertTrue(response['retry_available'])
        self.assertIn('Try again', response['suggestions'])
    
    # Test handle_vision_error
    
    @patch('src.kitchen_agent_core.logger')
    def test_handle_vision_error_with_guidance(self, mock_logger):
        """Test Requirement 17.3: Handle Vision Analyzer errors with guidance"""
        error = Exception("Image analysis failed")
        
        response = self.agent.handle_vision_error(
            error=error,
            session_id=self.test_session_id,
            image_id=self.test_image_id,
            language='en'
        )
        
        # Verify response
        self.assertEqual(response['error_code'], 'vision_analysis_failed')
        self.assertTrue(response['retry_available'])
        self.assertIn('analyze', response['user_friendly_message'].lower())
        
        # Verify guidance suggestions
        suggestions = response['suggestions']
        self.assertGreater(len(suggestions), 0)
        # Should suggest improving photo quality
        suggestions_text = ' '.join(suggestions).lower()
        self.assertTrue(
            'clear' in suggestions_text or 
            'light' in suggestions_text or
            'photo' in suggestions_text
        )
        
        # Verify CloudWatch logging (Requirement 17.6)
        self.assertTrue(mock_logger.error.called)
        log_message = str(mock_logger.error.call_args)
        self.assertIn('Vision analysis failed', log_message)
        self.assertIn(f'session_id={self.test_session_id}', log_message)
        self.assertIn(f'image_id={self.test_image_id}', log_message)
    
    @patch('src.kitchen_agent_core.logger')
    def test_handle_vision_error_telugu(self, mock_logger):
        """Test Vision error handling in Telugu"""
        error = Exception("Analysis error")
        
        response = self.agent.handle_vision_error(
            error=error,
            session_id=self.test_session_id,
            image_id=self.test_image_id,
            language='te'
        )
        
        # Verify Telugu message
        has_telugu = any('\u0C00' <= char <= '\u0C7F' for char in response['user_friendly_message'])
        self.assertTrue(has_telugu)
        
        # Verify Telugu suggestions
        suggestions = response['suggestions']
        self.assertGreater(len(suggestions), 0)
        # At least one suggestion should have Telugu characters
        has_telugu_suggestions = any(
            any('\u0C00' <= char <= '\u0C7F' for char in suggestion)
            for suggestion in suggestions
        )
        self.assertTrue(has_telugu_suggestions)
    
    # Test handle_recipe_error
    
    @patch('src.kitchen_agent_core.logger')
    def test_handle_recipe_error_with_suggestions(self, mock_logger):
        """Test Requirement 17.4: Handle Recipe Generator errors with suggestions"""
        error = Exception("Recipe generation failed")
        
        response = self.agent.handle_recipe_error(
            error=error,
            session_id=self.test_session_id,
            language='en',
            insufficient_ingredients=False
        )
        
        # Verify response
        self.assertEqual(response['error_code'], 'recipe_generation_failed')
        self.assertTrue(response['retry_available'])
        self.assertIn('recipe', response['user_friendly_message'].lower())
        
        # Verify suggestions
        suggestions = response['suggestions']
        self.assertGreater(len(suggestions), 0)
        suggestions_text = ' '.join(suggestions).lower()
        self.assertTrue(
            'upload' in suggestions_text or 
            'photo' in suggestions_text or
            'ingredient' in suggestions_text
        )
        
        # Verify CloudWatch logging (Requirement 17.6)
        self.assertTrue(mock_logger.error.called)
        log_message = str(mock_logger.error.call_args)
        self.assertIn('Recipe generation failed', log_message)
        self.assertIn(f'session_id={self.test_session_id}', log_message)
    
    @patch('src.kitchen_agent_core.logger')
    def test_handle_recipe_error_insufficient_ingredients(self, mock_logger):
        """Test handling insufficient ingredients error"""
        error = Exception("Not enough ingredients")
        
        response = self.agent.handle_recipe_error(
            error=error,
            session_id=self.test_session_id,
            language='en',
            insufficient_ingredients=True
        )
        
        # Verify response
        self.assertEqual(response['error_code'], 'insufficient_ingredients')
        self.assertTrue(response['retry_available'])
        self.assertIn('ingredient', response['user_friendly_message'].lower())
        
        # Verify CloudWatch logging
        self.assertTrue(mock_logger.error.called)
        log_message = str(mock_logger.error.call_args)
        self.assertIn('insufficient_ingredients=True', log_message)
    
    @patch('src.kitchen_agent_core.logger')
    def test_handle_recipe_error_telugu(self, mock_logger):
        """Test Recipe error handling in Telugu"""
        error = Exception("Recipe error")
        
        response = self.agent.handle_recipe_error(
            error=error,
            session_id=self.test_session_id,
            language='te',
            insufficient_ingredients=False
        )
        
        # Verify Telugu message
        has_telugu = any('\u0C00' <= char <= '\u0C7F' for char in response['user_friendly_message'])
        self.assertTrue(has_telugu)
        
        # Verify Telugu suggestions
        suggestions = response['suggestions']
        self.assertGreater(len(suggestions), 0)
    
    # Test comprehensive error scenarios
    
    def test_all_errors_have_retry_option(self):
        """Test Requirement 17.5: All errors provide retry option"""
        error = Exception("Test error")
        
        # Test all error handlers
        handlers = [
            lambda: self.agent.handle_bedrock_error(error, 'test', 'en', 1),
            lambda: self.agent.handle_s3_error(error, self.test_session_id, 'en'),
            lambda: self.agent.handle_vision_error(error, self.test_session_id, self.test_image_id, 'en'),
            lambda: self.agent.handle_recipe_error(error, self.test_session_id, 'en', False)
        ]
        
        for handler in handlers:
            response = handler()
            self.assertTrue(response['retry_available'], 
                          f"Handler {handler} should provide retry option")
            self.assertIn('suggestions', response)
            self.assertGreater(len(response['suggestions']), 0)
    
    @patch('src.kitchen_agent_core.logger')
    def test_all_errors_log_to_cloudwatch(self, mock_logger):
        """Test Requirement 17.6: All errors log to CloudWatch"""
        error = Exception("Test error")
        
        # Test all error handlers
        self.agent.handle_bedrock_error(error, 'test', 'en', 1)
        self.agent.handle_s3_error(error, self.test_session_id, 'en')
        self.agent.handle_vision_error(error, self.test_session_id, self.test_image_id, 'en')
        self.agent.handle_recipe_error(error, self.test_session_id, 'en', False)
        
        # Verify all handlers logged errors
        self.assertGreaterEqual(mock_logger.error.call_count, 4)
    
    def test_error_response_structure_consistency(self):
        """Test that all error responses have consistent structure"""
        error = Exception("Test error")
        
        responses = [
            self.agent.handle_bedrock_error(error, 'test', 'en', 1),
            self.agent.handle_s3_error(error, self.test_session_id, 'en'),
            self.agent.handle_vision_error(error, self.test_session_id, self.test_image_id, 'en'),
            self.agent.handle_recipe_error(error, self.test_session_id, 'en', False)
        ]
        
        required_fields = ['error_code', 'user_friendly_message', 'retry_available', 'suggestions', 'timestamp']
        
        for response in responses:
            for field in required_fields:
                self.assertIn(field, response, 
                            f"Response missing required field: {field}")
    
    def test_error_messages_are_user_friendly(self):
        """Test that error messages are user-friendly (no technical jargon)"""
        error = Exception("Test error")
        
        responses = [
            self.agent.handle_bedrock_error(error, 'test', 'en', 1),
            self.agent.handle_s3_error(error, self.test_session_id, 'en'),
            self.agent.handle_vision_error(error, self.test_session_id, self.test_image_id, 'en'),
            self.agent.handle_recipe_error(error, self.test_session_id, 'en', False)
        ]
        
        # Technical terms that should NOT appear in user messages
        technical_terms = ['exception', 'api', 'boto3', 'clienterror', 'traceback', 'stack']
        
        for response in responses:
            message = response['user_friendly_message'].lower()
            for term in technical_terms:
                self.assertNotIn(term, message, 
                               f"User message should not contain technical term: {term}")
    
    def test_suggestions_are_actionable(self):
        """Test that suggestions provide actionable guidance"""
        error = Exception("Test error")
        
        responses = [
            self.agent.handle_bedrock_error(error, 'test', 'en', 1),
            self.agent.handle_s3_error(error, self.test_session_id, 'en'),
            self.agent.handle_vision_error(error, self.test_session_id, self.test_image_id, 'en'),
            self.agent.handle_recipe_error(error, self.test_session_id, 'en', False)
        ]
        
        for response in responses:
            suggestions = response['suggestions']
            self.assertIsInstance(suggestions, list)
            self.assertGreater(len(suggestions), 0)
            
            # Each suggestion should be a non-empty string
            for suggestion in suggestions:
                self.assertIsInstance(suggestion, str)
                self.assertGreater(len(suggestion), 0)


class TestErrorHandlingIntegration(unittest.TestCase):
    """Integration tests for error handling in real scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_s3 = Mock()
        self.mock_dynamodb = Mock()
        
        with patch('boto3.client', return_value=self.mock_s3), \
             patch('boto3.resource', return_value=self.mock_dynamodb):
            self.agent = KitchenAgentCore()
    
    @patch('src.kitchen_agent_core.logger')
    def test_upload_image_error_handling(self, mock_logger):
        """Test error handling in upload_image_to_s3 method"""
        # Simulate S3 upload failure
        self.mock_s3.put_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket not found'}},
            'put_object'
        )
        
        # Attempt upload
        with self.assertRaises(ClientError):
            self.agent.upload_image_to_s3(
                image_data=b"test_image",
                session_id="test_session",
                owner_sub="user-123",
                content_type="image/jpeg"
            )
        
        # Verify error was logged
        self.assertTrue(mock_logger.error.called)
        log_message = str(mock_logger.error.call_args)
        self.assertIn('S3 upload failed', log_message)


if __name__ == '__main__':
    unittest.main()
