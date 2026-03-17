"""
Unit tests for VisionAnalyzer error handling and retry logic

Tests Requirements 17.1, 17.3, 19.4, 19.5:
- 17.1: Log errors to CloudWatch
- 17.3: Handle vision analyzer errors with user-friendly messages
- 19.4: Implement retry logic with exponential backoff for Bedrock API calls
- 19.5: Retry up to 3 times before returning an error
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import time
from pathlib import Path
from botocore.exceptions import ClientError

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.vision_analyzer import VisionAnalyzer
from config.env import Config


class TestVisionAnalyzerErrorHandling(unittest.TestCase):
    """Test error handling and retry logic in VisionAnalyzer"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock boto3 client to avoid AWS calls
        self.mock_bedrock = Mock()
        
        # Patch validate_inventory_schema to always return success
        self.validate_patcher = patch('src.vision_analyzer.validate_inventory_schema', return_value=(True, None))
        self.validate_patcher.start()
        
        with patch('boto3.client', return_value=self.mock_bedrock):
            self.analyzer = VisionAnalyzer()
        
        # Sample test data
        self.test_image_data = b"fake_image_data"
        self.test_session_id = "test_session_123"
        self.test_image_id = "test_image_456"
    
    def tearDown(self):
        """Clean up patches"""
        self.validate_patcher.stop()
    
    def _create_client_error(self, error_code: str) -> ClientError:
        """Helper to create ClientError exceptions"""
        return ClientError(
            {
                'Error': {
                    'Code': error_code,
                    'Message': f'Test {error_code}'
                }
            },
            'invoke_model'
        )
    
    def _create_successful_response(self) -> dict:
        """Helper to create a successful Bedrock response"""
        # Return a valid inventory JSON structure
        valid_inventory = {
            "total_items": 0,
            "detection_timestamp": "2024-01-01T00:00:00Z",
            "session_id": self.test_session_id,
            "image_id": self.test_image_id,
            "ingredients": [],
            "detection_metadata": {
                "model_version": "test-model",
                "processing_time_ms": 100,
                "image_quality": "poor"
            }
        }
        return {
            'body': MagicMock(
                read=MagicMock(return_value=b'{"content": [{"text": "[]"}]}')
            )
        }
    
    def _mock_successful_analysis(self):
        """Helper to mock the entire analysis process successfully"""
        # Mock the validate_inventory_schema to return success
        with patch('src.vision_analyzer.validate_inventory_schema', return_value=(True, None)):
            pass
    
    @patch('src.vision_analyzer.logger')
    @patch('time.sleep')
    def test_throttling_exception_retry_with_exponential_backoff(self, mock_sleep, mock_logger):
        """Test Requirement 19.4: Exponential backoff for ThrottlingException (1s, 2s, 4s)"""
        # First 2 calls fail with throttling, 3rd succeeds
        self.mock_bedrock.invoke_model.side_effect = [
            self._create_client_error('ThrottlingException'),
            self._create_client_error('ThrottlingException'),
            self._create_successful_response()
        ]
        
        # Execute
        result = self.analyzer.analyze_image(
            self.test_image_data,
            self.test_session_id,
            self.test_image_id
        )
        
        # Verify exponential backoff: 2^0=1s, 2^1=2s
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_any_call(1)  # First retry: 2^0 = 1s
        mock_sleep.assert_any_call(2)  # Second retry: 2^1 = 2s
        
        # Verify 3 attempts were made
        self.assertEqual(self.mock_bedrock.invoke_model.call_count, 3)
        
        # Verify CloudWatch logging
        self.assertTrue(mock_logger.warning.called)
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        self.assertTrue(any('ThrottlingException' in str(call) for call in warning_calls))
    
    @patch('src.vision_analyzer.logger')
    @patch('time.sleep')
    def test_model_not_ready_exception_retry(self, mock_sleep, mock_logger):
        """Test Requirement 19.4: Retry on ModelNotReadyException"""
        # First call fails with ModelNotReadyException, 2nd succeeds
        self.mock_bedrock.invoke_model.side_effect = [
            self._create_client_error('ModelNotReadyException'),
            self._create_successful_response()
        ]
        
        # Execute
        result = self.analyzer.analyze_image(
            self.test_image_data,
            self.test_session_id,
            self.test_image_id
        )
        
        # Verify retry happened
        self.assertEqual(mock_sleep.call_count, 1)
        mock_sleep.assert_called_with(1)  # First retry: 2^0 = 1s
        
        # Verify 2 attempts were made
        self.assertEqual(self.mock_bedrock.invoke_model.call_count, 2)
        
        # Verify CloudWatch logging
        self.assertTrue(mock_logger.warning.called)
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        self.assertTrue(any('ModelNotReadyException' in str(call) for call in warning_calls))
    
    @patch('src.vision_analyzer.logger')
    @patch('time.sleep')
    def test_max_retries_3_attempts(self, mock_sleep, mock_logger):
        """Test Requirement 19.5: Max 3 retries before returning error"""
        # All 3 attempts fail with throttling
        self.mock_bedrock.invoke_model.side_effect = [
            self._create_client_error('ThrottlingException'),
            self._create_client_error('ThrottlingException'),
            self._create_client_error('ThrottlingException')
        ]
        
        # Execute and expect exception
        with self.assertRaises(Exception) as context:
            self.analyzer.analyze_image(
                self.test_image_data,
                self.test_session_id,
                self.test_image_id
            )
        
        # Verify error message - the last attempt raises the ClientError directly
        exception_str = str(context.exception)
        self.assertTrue(
            'Bedrock API error' in exception_str or 
            'ThrottlingException' in exception_str or
            'Vision analysis failed' in exception_str,
            f"Unexpected error message: {exception_str}"
        )
        
        # Verify exactly 3 attempts were made
        self.assertEqual(self.mock_bedrock.invoke_model.call_count, 3)
        
        # Verify exponential backoff was applied: 1s, 2s, 4s (3 sleeps for 3 failures)
        self.assertEqual(mock_sleep.call_count, 3)
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)
        mock_sleep.assert_any_call(4)
        
        # Verify CloudWatch error logging
        self.assertTrue(mock_logger.error.called or mock_logger.warning.called)
    
    @patch('src.vision_analyzer.logger')
    def test_non_retryable_error_fails_immediately(self, mock_logger):
        """Test that non-retryable errors fail immediately without retry"""
        # Simulate a non-retryable error
        self.mock_bedrock.invoke_model.side_effect = self._create_client_error('ValidationException')
        
        # Execute and expect exception
        with self.assertRaises(Exception) as context:
            self.analyzer.analyze_image(
                self.test_image_data,
                self.test_session_id,
                self.test_image_id
            )
        
        # Verify error message
        self.assertIn('Bedrock API error', str(context.exception))
        self.assertIn('ValidationException', str(context.exception))
        
        # Verify only 1 attempt was made (no retries)
        self.assertEqual(self.mock_bedrock.invoke_model.call_count, 1)
        
        # Verify CloudWatch error logging
        self.assertTrue(mock_logger.error.called)
        error_calls = [str(call) for call in mock_logger.error.call_args_list]
        self.assertTrue(any('ValidationException' in str(call) for call in error_calls))
    
    @patch('src.vision_analyzer.logger')
    @patch('time.sleep')
    def test_exponential_backoff_timing(self, mock_sleep, mock_logger):
        """Test that exponential backoff follows 2^attempt pattern"""
        # All attempts fail to test full backoff sequence
        self.mock_bedrock.invoke_model.side_effect = [
            self._create_client_error('ThrottlingException'),
            self._create_client_error('ThrottlingException'),
            self._create_client_error('ThrottlingException')
        ]
        
        # Execute and expect exception
        with self.assertRaises(Exception):
            self.analyzer.analyze_image(
                self.test_image_data,
                self.test_session_id,
                self.test_image_id
            )
        
        # Verify exponential backoff sequence: 2^0=1, 2^1=2, 2^2=4 (3 sleeps for 3 failures)
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        self.assertEqual(sleep_calls, [1, 2, 4])
    
    @patch('src.vision_analyzer.logger')
    def test_cloudwatch_logging_on_success(self, mock_logger):
        """Test Requirement 17.1: Log successful operations to CloudWatch"""
        # Successful response
        self.mock_bedrock.invoke_model.return_value = self._create_successful_response()
        
        # Execute
        result = self.analyzer.analyze_image(
            self.test_image_data,
            self.test_session_id,
            self.test_image_id
        )
        
        # Verify info logging for success
        self.assertTrue(mock_logger.info.called)
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        
        # Check for start and success log messages
        self.assertTrue(any('Starting image analysis' in str(call) for call in info_calls))
        self.assertTrue(any('Image analysis successful' in str(call) for call in info_calls))
    
    @patch('src.vision_analyzer.logger')
    @patch('time.sleep')
    def test_cloudwatch_logging_on_retry(self, mock_sleep, mock_logger):
        """Test Requirement 17.1: Log retry attempts to CloudWatch"""
        # First call fails, second succeeds
        self.mock_bedrock.invoke_model.side_effect = [
            self._create_client_error('ThrottlingException'),
            self._create_successful_response()
        ]
        
        # Execute
        result = self.analyzer.analyze_image(
            self.test_image_data,
            self.test_session_id,
            self.test_image_id
        )
        
        # Verify warning logging for retry
        self.assertTrue(mock_logger.warning.called)
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        
        # Check for retry information in logs
        self.assertTrue(any('ThrottlingException' in str(call) for call in warning_calls))
        self.assertTrue(any('attempt=' in str(call) for call in warning_calls))
        self.assertTrue(any('retry_in=' in str(call) for call in warning_calls))
    
    @patch('src.vision_analyzer.logger')
    def test_cloudwatch_logging_on_failure(self, mock_logger):
        """Test Requirement 17.1: Log failures to CloudWatch"""
        # All attempts fail
        self.mock_bedrock.invoke_model.side_effect = self._create_client_error('ServiceUnavailableException')
        
        # Execute and expect exception
        with self.assertRaises(Exception):
            self.analyzer.analyze_image(
                self.test_image_data,
                self.test_session_id,
                self.test_image_id
            )
        
        # Verify error logging
        self.assertTrue(mock_logger.error.called)
        error_calls = [str(call) for call in mock_logger.error.call_args_list]
        
        # Check for error details in logs
        self.assertTrue(any('ServiceUnavailableException' in str(call) for call in error_calls))
        self.assertTrue(any('session_id=' in str(call) for call in error_calls))
        self.assertTrue(any('image_id=' in str(call) for call in error_calls))
    
    @patch('src.vision_analyzer.logger')
    @patch('time.sleep')
    def test_generic_exception_retry(self, mock_sleep, mock_logger):
        """Test that generic exceptions are retried with exponential backoff"""
        # First 2 calls fail with generic exception, 3rd succeeds
        self.mock_bedrock.invoke_model.side_effect = [
            Exception("Network error"),
            Exception("Timeout error"),
            self._create_successful_response()
        ]
        
        # Execute
        result = self.analyzer.analyze_image(
            self.test_image_data,
            self.test_session_id,
            self.test_image_id
        )
        
        # Verify retries happened
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)
        
        # Verify 3 attempts were made
        self.assertEqual(self.mock_bedrock.invoke_model.call_count, 3)
        
        # Verify warning logging for retries
        self.assertTrue(mock_logger.warning.called)
    
    @patch('src.vision_analyzer.logger')
    @patch('time.sleep')
    def test_generic_exception_max_retries(self, mock_sleep, mock_logger):
        """Test that generic exceptions fail after max retries"""
        # All 3 attempts fail with generic exception
        self.mock_bedrock.invoke_model.side_effect = Exception("Persistent error")
        
        # Execute and expect exception
        with self.assertRaises(Exception) as context:
            self.analyzer.analyze_image(
                self.test_image_data,
                self.test_session_id,
                self.test_image_id
            )
        
        # Verify error message includes retry count
        self.assertIn('failed after 3 attempts', str(context.exception))
        
        # Verify exactly 3 attempts were made
        self.assertEqual(self.mock_bedrock.invoke_model.call_count, 3)
        
        # Verify error logging
        self.assertTrue(mock_logger.error.called)
        error_calls = [str(call) for call in mock_logger.error.call_args_list]
        self.assertTrue(any('failed after all retries' in str(call) for call in error_calls))
    
    @patch('src.vision_analyzer.logger')
    def test_logging_includes_session_and_image_ids(self, mock_logger):
        """Test that all logs include session_id and image_id for traceability"""
        # Successful response
        self.mock_bedrock.invoke_model.return_value = self._create_successful_response()
        
        # Execute
        result = self.analyzer.analyze_image(
            self.test_image_data,
            self.test_session_id,
            self.test_image_id
        )
        
        # Verify all log calls include session_id and image_id
        all_log_calls = (
            mock_logger.info.call_args_list +
            mock_logger.warning.call_args_list +
            mock_logger.error.call_args_list
        )
        
        for log_call in all_log_calls:
            log_message = str(log_call)
            self.assertTrue(
                'session_id=' in log_message or 'image_id=' in log_message,
                f"Log message missing identifiers: {log_message}"
            )
    
    @patch('src.vision_analyzer.logger')
    def test_logging_includes_processing_time(self, mock_logger):
        """Test that successful analysis logs include processing time"""
        # Successful response
        self.mock_bedrock.invoke_model.return_value = self._create_successful_response()
        
        # Execute
        result = self.analyzer.analyze_image(
            self.test_image_data,
            self.test_session_id,
            self.test_image_id
        )
        
        # Verify success log includes processing time
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        self.assertTrue(
            any('processing_time_ms=' in str(call) for call in info_calls),
            "Success log should include processing_time_ms"
        )
    
    def test_max_retries_configuration(self):
        """Test that max retries is configurable from Config"""
        self.assertEqual(self.analyzer.max_retries, Config.VISION_MAX_RETRIES)
        self.assertEqual(self.analyzer.max_retries, 3)
    
    def test_timeout_configuration(self):
        """Test that timeout is configurable from Config"""
        self.assertEqual(self.analyzer.timeout, Config.VISION_TIMEOUT_SECONDS)
        self.assertEqual(self.analyzer.timeout, 10)


class TestVisionAnalyzerInitializationLogging(unittest.TestCase):
    """Test logging during VisionAnalyzer initialization"""
    
    @patch('src.vision_analyzer.logger')
    def test_initialization_logging(self, mock_logger):
        """Test that initialization is logged to CloudWatch"""
        with patch('boto3.client'):
            analyzer = VisionAnalyzer()
        
        # Verify initialization was logged
        self.assertTrue(mock_logger.info.called)
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        
        # Check for initialization details
        self.assertTrue(any('VisionAnalyzer initialized' in str(call) for call in info_calls))
        self.assertTrue(any('model=' in str(call) for call in info_calls))
        self.assertTrue(any('max_retries=' in str(call) for call in info_calls))


if __name__ == '__main__':
    unittest.main()
