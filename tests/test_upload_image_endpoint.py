"""
Tests for POST /upload-image endpoint

Tests Requirements 3.1, 3.2, 3.3, 3.4, 3.5
"""

import json
import base64
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import the handler
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api_handler import handle_upload_image, parse_multipart_image, create_response, MAX_FILE_SIZE_BYTES


class TestUploadImageEndpoint:
    """Test suite for POST /upload-image endpoint"""
    
    def test_missing_session_id(self):
        """Test that missing session_id returns 400 error"""
        event = {
            'httpMethod': 'POST',
            'path': '/upload-image',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({}),
            'isBase64Encoded': False
        }
        
        response = handle_upload_image(event)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_request'
        assert 'session_id' in body['message']
    
    def test_missing_image_data_json_request(self):
        """JSON uploads must still include image_data."""
        event = {
            'httpMethod': 'POST',
            'path': '/upload-image',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'session_id': 'sess_test123'}),
            'isBase64Encoded': False
        }
        
        response = handle_upload_image(event)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_request'
    
    def test_unsupported_image_format(self):
        """Requirement 3.1: Test that unsupported formats are rejected"""
        event = {
            'httpMethod': 'POST',
            'path': '/upload-image',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'session_id': 'sess_test123',
                'content_type': 'image/gif',
                'image_data': base64.b64encode(b'fake_image_data').decode('utf-8')
            }),
            'isBase64Encoded': False
        }
        
        response = handle_upload_image(event)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'invalid_format'
        assert 'JPEG, PNG, HEIC' in body['message']
    
    def test_file_too_large(self):
        """Requirement 3.2: Test that files over 10MB are rejected"""
        # Create image data larger than 10MB
        large_image = b'x' * (MAX_FILE_SIZE_BYTES + 1)
        
        event = {
            'httpMethod': 'POST',
            'path': '/upload-image',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'session_id': 'sess_test123',
                'content_type': 'image/jpeg',
                'image_data': base64.b64encode(large_image).decode('utf-8')
            }),
            'isBase64Encoded': False
        }
        
        response = handle_upload_image(event)
        
        assert response['statusCode'] == 413
        body = json.loads(response['body'])
        assert body['error'] == 'file_too_large'
        assert body['max_size_mb'] == 10
    
    @patch('src.api_handler.kitchen_agent')
    def test_successful_upload_jpeg(self, mock_agent):
        """Requirements 3.3, 3.4, 3.5: Test successful JPEG upload"""
        # Mock image data
        image_data = b'\xff\xd8\xff\xe0' + b'x' * 1000  # JPEG header + data
        mock_agent.get_session.return_value = {'session_id': 'sess_test123'}
        
        # Mock KitchenAgentCore response
        mock_agent.upload_image_to_s3.return_value = {
            'image_id': 'img_abc123',
            's3_url': 'https://s3.amazonaws.com/bucket/sess_test123/img_abc123.jpg',
            's3_key': 'sess_test123/img_abc123.jpg',
            'timestamp': '2024-01-15T10:30:00Z'
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/upload-image',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'session_id': 'sess_test123',
                'content_type': 'image/jpeg',
                'image_data': base64.b64encode(image_data).decode('utf-8')
            }),
            'isBase64Encoded': False
        }
        
        response = handle_upload_image(event)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Requirement 3.5: Verify image_id and s3_url are returned
        assert body['image_id'] == 'img_abc123'
        assert body['s3_url'] == 'https://s3.amazonaws.com/bucket/sess_test123/img_abc123.jpg'
        assert body['session_id'] == 'sess_test123'
        assert body['status'] == 'uploaded'
        assert 'timestamp' in body
        
        # Verify KitchenAgentCore was called correctly
        mock_agent.upload_image_to_s3.assert_called_once_with(
            image_data=image_data,
            session_id='sess_test123',
            owner_sub='user-123',
            content_type='image/jpeg'
        )
    
    @patch('src.api_handler.kitchen_agent')
    def test_successful_upload_png(self, mock_agent):
        """Requirement 3.1: Test successful PNG upload"""
        # Mock PNG image data
        image_data = b'\x89PNG\r\n\x1a\n' + b'x' * 1000  # PNG header + data
        mock_agent.get_session.return_value = {'session_id': 'sess_test123'}
        
        # Mock KitchenAgentCore response
        mock_agent.upload_image_to_s3.return_value = {
            'image_id': 'img_def456',
            's3_url': 'https://s3.amazonaws.com/bucket/sess_test123/img_def456.png',
            's3_key': 'sess_test123/img_def456.png',
            'timestamp': '2024-01-15T10:30:00Z'
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/upload-image',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'session_id': 'sess_test123',
                'content_type': 'image/png',
                'image_data': base64.b64encode(image_data).decode('utf-8')
            }),
            'isBase64Encoded': False
        }
        
        response = handle_upload_image(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['image_id'] == 'img_def456'
        assert '.png' in body['s3_url']
    
    @patch('src.api_handler.kitchen_agent')
    def test_successful_upload_heic(self, mock_agent):
        """Requirement 3.1: Test successful HEIC upload"""
        # Mock HEIC image data
        image_data = b'\x00\x00\x00\x18ftypheic' + b'x' * 100
        mock_agent.get_session.return_value = {'session_id': 'sess_test123'}
        
        # Mock KitchenAgentCore response
        mock_agent.upload_image_to_s3.return_value = {
            'image_id': 'img_ghi789',
            's3_url': 'https://s3.amazonaws.com/bucket/sess_test123/img_ghi789.heic',
            's3_key': 'sess_test123/img_ghi789.heic',
            'timestamp': '2024-01-15T10:30:00Z'
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/upload-image',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'session_id': 'sess_test123',
                'content_type': 'image/heic',
                'image_data': base64.b64encode(image_data).decode('utf-8')
            }),
            'isBase64Encoded': False
        }
        
        response = handle_upload_image(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['image_id'] == 'img_ghi789'
        assert '.heic' in body['s3_url']
    
    @patch('src.api_handler.kitchen_agent')
    def test_upload_failure(self, mock_agent):
        """Test handling of S3 upload failure"""
        # Mock image data
        image_data = b'\xff\xd8\xff\xe0' + b'x' * 1000
        mock_agent.get_session.return_value = {'session_id': 'sess_test123'}
        
        # Mock upload failure
        mock_agent.upload_image_to_s3.side_effect = Exception("S3 error")
        
        event = {
            'httpMethod': 'POST',
            'path': '/upload-image',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'session_id': 'sess_test123',
                'content_type': 'image/jpeg',
                'image_data': base64.b64encode(image_data).decode('utf-8')
            }),
            'isBase64Encoded': False
        }
        
        response = handle_upload_image(event)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['error'] == 'upload_failed'

    @patch('src.api_handler.kitchen_agent')
    def test_true_multipart_upload(self, mock_agent):
        """Multipart form-data uploads should be parsed end-to-end."""
        image_data = b'\xff\xd8\xff\xe0' + b'x' * 256
        boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
        multipart_body = (
            f'--{boundary}\r\n'
            'Content-Disposition: form-data; name="session_id"\r\n\r\n'
            'sess_test123\r\n'
            f'--{boundary}\r\n'
            'Content-Disposition: form-data; name="file"; filename="fridge.jpg"\r\n'
            'Content-Type: image/jpeg\r\n\r\n'
        ).encode('utf-8') + image_data + f'\r\n--{boundary}--\r\n'.encode('utf-8')

        mock_agent.get_session.return_value = {'session_id': 'sess_test123'}
        mock_agent.upload_image_to_s3.return_value = {
            'image_id': 'img_multipart',
            's3_url': 'https://s3.amazonaws.com/bucket/sess_test123/img_multipart.jpg',
            's3_key': 'sess_test123/img_multipart.jpg',
            'timestamp': '2024-01-15T10:30:00Z'
        }

        event = {
            'httpMethod': 'POST',
            'path': '/upload-image',
            'headers': {'Content-Type': f'multipart/form-data; boundary={boundary}'},
            'body': base64.b64encode(multipart_body).decode('utf-8'),
            'isBase64Encoded': True
        }

        response = handle_upload_image(event)

        assert response['statusCode'] == 200
        mock_agent.upload_image_to_s3.assert_called_once()


class TestKitchenAgentCoreUpload:
    """Test suite for KitchenAgentCore.upload_image_to_s3 method"""
    
    @patch('boto3.client')
    def test_upload_image_to_s3_success(self, mock_boto_client):
        """Requirements 3.3, 3.4: Test successful S3 upload"""
        from src.kitchen_agent_core import KitchenAgentCore
        
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        # Mock presigned URL
        mock_s3.generate_presigned_url.return_value = 'https://s3.amazonaws.com/presigned-url'
        
        # Create instance
        agent = KitchenAgentCore()
        agent.s3_client = mock_s3
        agent.store_image_metadata = MagicMock()
        agent.verify_image_upload_complete = MagicMock(return_value=True)
        
        # Test upload
        image_data = b'\xff\xd8\xff\xe0' + b'test_image_data'
        result = agent.upload_image_to_s3(
            image_data=image_data,
            session_id='sess_test123',
            owner_sub='user-123',
            content_type='image/jpeg'
        )
        
        # Verify result
        assert 'image_id' in result
        assert result['image_id'].startswith('img_')
        assert result['s3_url'] == 'https://s3.amazonaws.com/presigned-url'
        assert 'timestamp' in result
        
        # Verify S3 put_object was called
        mock_s3.put_object.assert_called_once()
        call_args = mock_s3.put_object.call_args
        assert call_args[1]['Body'] == image_data
        assert call_args[1]['ContentType'] == 'image/jpeg'
        assert 'session_id' in call_args[1]['Metadata']
    
    @patch('boto3.client')
    def test_upload_image_empty_data(self, mock_boto_client):
        """Test that empty image data raises ValueError"""
        from src.kitchen_agent_core import KitchenAgentCore
        
        agent = KitchenAgentCore()
        
        with pytest.raises(ValueError, match="image_data cannot be empty"):
            agent.upload_image_to_s3(
                image_data=b'',
                session_id='sess_test123',
                owner_sub='user-123',
                content_type='image/jpeg'
            )
    
    @patch('boto3.client')
    def test_upload_image_missing_session_id(self, mock_boto_client):
        """Test that missing session_id raises ValueError"""
        from src.kitchen_agent_core import KitchenAgentCore
        
        agent = KitchenAgentCore()
        
        with pytest.raises(ValueError, match="session_id is required"):
            agent.upload_image_to_s3(
                image_data=b'test_data',
                session_id='',
                owner_sub='user-123',
                content_type='image/jpeg'
            )
    
    @patch('boto3.client')
    def test_upload_image_png_extension(self, mock_boto_client):
        """Test that PNG images get correct file extension"""
        from src.kitchen_agent_core import KitchenAgentCore
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.generate_presigned_url.return_value = 'https://s3.amazonaws.com/presigned-url'
        
        agent = KitchenAgentCore()
        agent.s3_client = mock_s3
        agent.store_image_metadata = MagicMock()
        agent.verify_image_upload_complete = MagicMock(return_value=True)
        
        result = agent.upload_image_to_s3(
            image_data=b'\x89PNG\r\n\x1a\n',
            session_id='sess_test123',
            owner_sub='user-123',
            content_type='image/png'
        )
        
        # Verify S3 key has .png extension
        call_args = mock_s3.put_object.call_args
        s3_key = call_args[1]['Key']
        assert s3_key.endswith('.png')
    
    @patch('boto3.client')
    def test_upload_image_heic_extension(self, mock_boto_client):
        """Test that HEIC images get correct file extension"""
        from src.kitchen_agent_core import KitchenAgentCore
        
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.generate_presigned_url.return_value = 'https://s3.amazonaws.com/presigned-url'
        
        agent = KitchenAgentCore()
        agent.s3_client = mock_s3
        agent.store_image_metadata = MagicMock()
        agent.verify_image_upload_complete = MagicMock(return_value=True)
        
        result = agent.upload_image_to_s3(
            image_data=b'heic_data',
            session_id='sess_test123',
            owner_sub='user-123',
            content_type='image/heic'
        )
        
        # Verify S3 key has .heic extension
        call_args = mock_s3.put_object.call_args
        s3_key = call_args[1]['Key']
        assert s3_key.endswith('.heic')

    @patch('boto3.client')
    def test_verify_image_upload_complete_checks_s3_object(self, mock_boto_client):
        """Upload verification should confirm both metadata and S3 object presence."""
        from src.kitchen_agent_core import KitchenAgentCore

        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        agent = KitchenAgentCore()
        agent.s3_client = mock_s3
        agent.get_image_metadata = MagicMock(
            return_value={
                's3_key': 'sess_test123/img_abc123.jpg'
            }
        )

        assert agent.verify_image_upload_complete('sess_test123', 'img_abc123') is True
        mock_s3.head_object.assert_called_once_with(
            Bucket=agent.image_bucket,
            Key='sess_test123/img_abc123.jpg'
        )

    @patch('boto3.client')
    def test_verify_image_upload_complete_raises_when_s3_object_missing(self, mock_boto_client):
        """Upload verification should fail if metadata exists but the S3 object does not."""
        from botocore.exceptions import ClientError
        from src.kitchen_agent_core import KitchenAgentCore

        mock_s3 = MagicMock()
        mock_s3.head_object.side_effect = ClientError(
            {'Error': {'Code': '404', 'Message': 'Not Found'}},
            'HeadObject'
        )
        mock_boto_client.return_value = mock_s3

        agent = KitchenAgentCore()
        agent.s3_client = mock_s3
        agent.get_image_metadata = MagicMock(
            return_value={
                's3_key': 'sess_test123/img_abc123.jpg'
            }
        )

        with pytest.raises(ValueError, match='object was not persisted'):
            agent.verify_image_upload_complete('sess_test123', 'img_abc123')


class TestResponseHelpers:
    """Test helper functions"""
    
    def test_create_response_default_headers(self):
        """Test that create_response includes CORS headers"""
        response = create_response(
            status_code=200,
            body={'message': 'success'}
        )
        
        assert response['statusCode'] == 200
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Content-Type'] == 'application/json'
        
        body = json.loads(response['body'])
        assert body['message'] == 'success'
    
    def test_create_response_custom_headers(self):
        """Test that custom headers are merged"""
        response = create_response(
            status_code=201,
            body={'id': '123'},
            headers={'X-Custom-Header': 'value'}
        )
        
        assert response['headers']['X-Custom-Header'] == 'value'
        assert 'Access-Control-Allow-Origin' in response['headers']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
