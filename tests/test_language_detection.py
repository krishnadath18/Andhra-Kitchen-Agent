"""
Unit tests for language detection and response consistency in KitchenAgentCore.

Tests Requirements 1.3 and 1.4:
- Automatic language detection (English/Telugu)
- Response language consistency with input
- Session language preference storage
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.kitchen_agent_core import KitchenAgentCore


class TestLanguageDetection:
    """Test language detection functionality"""
    
    @pytest.fixture
    def agent_core(self):
        """Create KitchenAgentCore instance with mocked AWS clients"""
        with patch('boto3.client'), \
             patch('boto3.resource'):
            agent = KitchenAgentCore()
            agent.sessions_table = Mock()
            return agent
    
    def test_detect_english_text(self, agent_core):
        """Test detection of English text"""
        english_texts = [
            "What can I cook with brinjal?",
            "Show me recipes for curry",
            "I need a shopping list",
            "Hello, how are you?",
            "Can you help me with cooking?"
        ]
        
        for text in english_texts:
            result = agent_core.detect_language(text)
            assert result == 'en', f"Failed to detect English in: {text}"
    
    def test_detect_telugu_text(self, agent_core):
        """Test detection of Telugu text"""
        telugu_texts = [
            "వంకాయతో ఏమి వండగలను?",
            "కూర వంటకాలు చూపించు",
            "నాకు షాపింగ్ జాబితా కావాలి",
            "నమస్కారం, ఎలా ఉన్నారు?",
            "వంట చేయడంలో సహాయం చేయగలరా?"
        ]
        
        for text in telugu_texts:
            result = agent_core.detect_language(text)
            assert result == 'te', f"Failed to detect Telugu in: {text}"
    
    def test_detect_mixed_language_defaults_to_english(self, agent_core):
        """Test that mixed language text defaults to English"""
        # Text with very few Telugu characters should default to English
        mixed_texts = [
            "I want to cook వం curry",  # Only 2 Telugu chars out of 15 = 13%
            "Can you help with కూ?"  # Only 2 Telugu chars out of 14 = 14%
        ]
        
        for text in mixed_texts:
            result = agent_core.detect_language(text)
            # Mixed language with less than 30% Telugu should default to English
            assert result == 'en', f"Mixed text should default to English: {text}"
    
    def test_detect_empty_text_defaults_to_english(self, agent_core):
        """Test that empty or whitespace text defaults to English"""
        empty_texts = ["", "   ", "\n", "\t"]
        
        for text in empty_texts:
            result = agent_core.detect_language(text)
            assert result == 'en', f"Empty text should default to English: '{text}'"
    
    def test_detect_numbers_only_defaults_to_english(self, agent_core):
        """Test that numeric-only text defaults to English"""
        numeric_texts = ["123", "456.78", "100%", "2024"]
        
        for text in numeric_texts:
            result = agent_core.detect_language(text)
            assert result == 'en', f"Numeric text should default to English: {text}"
    
    def test_detect_telugu_with_punctuation(self, agent_core):
        """Test Telugu detection with punctuation and special characters"""
        telugu_texts = [
            "వంకాయ కూర ఎలా చేయాలి?",
            "నాకు వంటకాలు కావాలి!",
            "బియ్యం, పప్పు, కూరగాయలు",
        ]
        
        for text in telugu_texts:
            result = agent_core.detect_language(text)
            assert result == 'te', f"Failed to detect Telugu with punctuation: {text}"
    
    def test_detect_english_with_punctuation(self, agent_core):
        """Test English detection with punctuation and special characters"""
        english_texts = [
            "What's for dinner?",
            "I need recipes, please!",
            "Brinjal, rice, and dal",
        ]
        
        for text in english_texts:
            result = agent_core.detect_language(text)
            assert result == 'en', f"Failed to detect English with punctuation: {text}"
    
    def test_telugu_ratio_threshold(self, agent_core):
        """Test that Telugu detection uses 30% threshold"""
        # Text with exactly 30% Telugu characters should be detected as English
        # "abc వం" has 2 Telugu chars out of 5 total = 40% Telugu
        text_above_threshold = "abc వం"
        result = agent_core.detect_language(text_above_threshold)
        assert result == 'te', "Text with >30% Telugu should be detected as Telugu"
        
        # "abcdef వం" has 2 Telugu chars out of 8 total = 25% Telugu
        text_below_threshold = "abcdef వం"
        result = agent_core.detect_language(text_below_threshold)
        assert result == 'en', "Text with <30% Telugu should be detected as English"


class TestLanguageConsistency:
    """Test language response consistency validation"""
    
    @pytest.fixture
    def agent_core(self):
        """Create KitchenAgentCore instance with mocked AWS clients"""
        with patch('boto3.client'), \
             patch('boto3.resource'):
            agent = KitchenAgentCore()
            agent.sessions_table = Mock()
            return agent
    
    def test_consistent_english_response(self, agent_core):
        """Test validation of consistent English response"""
        input_language = 'en'
        response_text = "Here are some recipes you can make with brinjal."
        
        is_consistent, detected = agent_core.ensure_language_consistency(
            input_language, response_text
        )
        
        assert is_consistent is True
        assert detected == 'en'
    
    def test_consistent_telugu_response(self, agent_core):
        """Test validation of consistent Telugu response"""
        input_language = 'te'
        response_text = "వంకాయతో మీరు ఈ వంటకాలు చేయవచ్చు."
        
        is_consistent, detected = agent_core.ensure_language_consistency(
            input_language, response_text
        )
        
        assert is_consistent is True
        assert detected == 'te'
    
    def test_inconsistent_response_english_expected(self, agent_core):
        """Test detection of inconsistent response when English expected"""
        input_language = 'en'
        response_text = "వంకాయతో మీరు ఈ వంటకాలు చేయవచ్చు."
        
        is_consistent, detected = agent_core.ensure_language_consistency(
            input_language, response_text
        )
        
        assert is_consistent is False
        assert detected == 'te'
    
    def test_inconsistent_response_telugu_expected(self, agent_core):
        """Test detection of inconsistent response when Telugu expected"""
        input_language = 'te'
        response_text = "Here are some recipes you can make with brinjal."
        
        is_consistent, detected = agent_core.ensure_language_consistency(
            input_language, response_text
        )
        
        assert is_consistent is False
        assert detected == 'en'
    
    def test_empty_response_defaults_to_english(self, agent_core):
        """Test that empty response defaults to English"""
        input_language = 'te'
        response_text = ""
        
        is_consistent, detected = agent_core.ensure_language_consistency(
            input_language, response_text
        )
        
        assert is_consistent is False
        assert detected == 'en'


class TestSessionLanguageUpdate:
    """Test session language preference storage"""
    
    @pytest.fixture
    def agent_core(self):
        """Create KitchenAgentCore instance with mocked AWS clients"""
        with patch('boto3.client'), \
             patch('boto3.resource'):
            agent = KitchenAgentCore()
            agent.sessions_table = Mock()
            return agent
    
    def test_update_session_language_to_telugu(self, agent_core):
        """Test updating session language to Telugu"""
        session_id = "sess_test123"
        language = "te"
        
        agent_core.update_session_language(session_id, language)
        
        # Verify DynamoDB update was called with correct parameters
        agent_core.sessions_table.update_item.assert_called_once()
        call_args = agent_core.sessions_table.update_item.call_args
        
        assert call_args[1]['Key']['session_id'] == session_id
        assert call_args[1]['Key']['data_type'] == 'profile'
        assert ':lang' in call_args[1]['ExpressionAttributeValues']
        assert call_args[1]['ExpressionAttributeValues'][':lang'] == language
    
    def test_update_session_language_to_english(self, agent_core):
        """Test updating session language to English"""
        session_id = "sess_test456"
        language = "en"
        
        agent_core.update_session_language(session_id, language)
        
        # Verify DynamoDB update was called with correct parameters
        agent_core.sessions_table.update_item.assert_called_once()
        call_args = agent_core.sessions_table.update_item.call_args
        
        assert call_args[1]['Key']['session_id'] == session_id
        assert call_args[1]['ExpressionAttributeValues'][':lang'] == language
    
    def test_update_session_language_includes_timestamp(self, agent_core):
        """Test that language update includes updated_at timestamp"""
        session_id = "sess_test789"
        language = "te"
        
        agent_core.update_session_language(session_id, language)
        
        call_args = agent_core.sessions_table.update_item.call_args
        assert ':updated' in call_args[1]['ExpressionAttributeValues']
        
        # Verify timestamp is in ISO format
        timestamp = call_args[1]['ExpressionAttributeValues'][':updated']
        datetime.fromisoformat(timestamp)  # Should not raise exception
    
    def test_update_session_language_handles_error(self, agent_core):
        """Test error handling when session update fails"""
        from botocore.exceptions import ClientError
        
        session_id = "sess_error"
        language = "en"
        
        # Mock ClientError
        error_response = {'Error': {'Code': 'ResourceNotFoundException'}}
        agent_core.sessions_table.update_item.side_effect = ClientError(
            error_response, 'UpdateItem'
        )
        
        with pytest.raises(ClientError):
            agent_core.update_session_language(session_id, language)


class TestLanguageDetectionIntegration:
    """Integration tests for language detection workflow"""
    
    @pytest.fixture
    def agent_core(self):
        """Create KitchenAgentCore instance with mocked AWS clients"""
        with patch('boto3.client'), \
             patch('boto3.resource'):
            agent = KitchenAgentCore()
            agent.sessions_table = Mock()
            return agent
    
    def test_detect_and_update_session_english(self, agent_core):
        """Test complete workflow: detect English and update session"""
        session_id = "sess_workflow1"
        user_input = "What can I cook today?"
        
        # Detect language
        detected_lang = agent_core.detect_language(user_input)
        assert detected_lang == 'en'
        
        # Update session
        agent_core.update_session_language(session_id, detected_lang)
        
        # Verify update was called
        agent_core.sessions_table.update_item.assert_called_once()
    
    def test_detect_and_update_session_telugu(self, agent_core):
        """Test complete workflow: detect Telugu and update session"""
        session_id = "sess_workflow2"
        user_input = "ఈరోజు ఏమి వండగలను?"
        
        # Detect language
        detected_lang = agent_core.detect_language(user_input)
        assert detected_lang == 'te'
        
        # Update session
        agent_core.update_session_language(session_id, detected_lang)
        
        # Verify update was called with Telugu
        call_args = agent_core.sessions_table.update_item.call_args
        assert call_args[1]['ExpressionAttributeValues'][':lang'] == 'te'
    
    def test_detect_validate_and_update_consistent_flow(self, agent_core):
        """Test full flow: detect input, validate response, update session"""
        session_id = "sess_workflow3"
        user_input = "Show me brinjal recipes"
        response = "Here are some delicious brinjal recipes for you."
        
        # Detect input language
        input_lang = agent_core.detect_language(user_input)
        assert input_lang == 'en'
        
        # Validate response consistency
        is_consistent, response_lang = agent_core.ensure_language_consistency(
            input_lang, response
        )
        assert is_consistent is True
        assert response_lang == 'en'
        
        # Update session
        agent_core.update_session_language(session_id, input_lang)
        
        # Verify complete workflow
        agent_core.sessions_table.update_item.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
