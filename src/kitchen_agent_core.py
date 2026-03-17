"""
Kitchen Agent Core for Andhra Kitchen Agent

Central orchestration class that manages:
- Chat message routing to Bedrock AgentCore
- S3 image uploads with unique identifiers
- Session management (create, get, update)
- Response synthesis from AgentCore outputs
- Error handling with retry logic
"""

import json
import time
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# Import configuration
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.env import Config

# Configure CloudWatch logging
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, Config.LOG_LEVEL))

# Add CloudWatch handler if running in AWS environment
if Config.ENVIRONMENT != 'local':
    try:
        import watchtower
        cloudwatch_handler = watchtower.CloudWatchLogHandler(
            log_group='/aws/andhra-kitchen-agent/kitchen-agent-core',
            stream_name=f'{Config.ENVIRONMENT}-{datetime.now(timezone.utc).strftime("%Y-%m-%d")}'
        )
        cloudwatch_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(cloudwatch_handler)
    except ImportError:
        # watchtower not installed, use console logging only
        pass

# Add console handler for local development
console_handler = logging.StreamHandler()
console_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)
logger.addHandler(console_handler)


class KitchenAgentCore:
    """
    Core orchestration class for Andhra Kitchen Agent.
    
    Responsibilities:
    - Route chat messages to Bedrock AgentCore
    - Upload images to S3 with unique identifiers
    - Manage user sessions (create, get, update)
    - Synthesize responses from AgentCore tool outputs
    - Handle errors with retry logic
    """
    
    def __init__(self):
        """Initialize KitchenAgentCore with AWS clients"""
        self.s3_client = boto3.client('s3', region_name=Config.AWS_REGION)
        self.dynamodb = boto3.resource('dynamodb', region_name=Config.AWS_REGION)
        self.bedrock_agent_runtime = boto3.client(
            service_name='bedrock-agent-runtime',
            region_name=Config.BEDROCK_REGION
        )
        
        # DynamoDB tables
        self.sessions_table = self.dynamodb.Table(Config.SESSIONS_TABLE)
        
        # Configuration
        self.image_bucket = Config.IMAGE_BUCKET
        self.image_expiry_hours = Config.IMAGE_EXPIRY_HOURS
        self.session_ttl_days = Config.SESSION_TTL_DAYS
        self.max_retries = 3
        
        logger.info(
            f"KitchenAgentCore initialized: "
            f"region={Config.AWS_REGION}, "
            f"image_bucket={self.image_bucket}, "
            f"sessions_table={Config.SESSIONS_TABLE}"
        )
    
    def upload_image_to_s3(
        self,
        image_data: bytes,
        session_id: str,
        owner_sub: str,
        content_type: str = 'image/jpeg'
    ) -> Dict[str, Any]:
        """
        Upload image to S3 with unique identifier and generate pre-signed URL.
        
        Requirements: 3.3, 3.4
        
        Args:
            image_data: Binary image data
            session_id: User session identifier
            owner_sub: Cognito subject that owns the session
            content_type: Image MIME type (image/jpeg, image/png, image/heic)
        
        Returns:
            Dictionary with:
                - image_id: Unique image identifier
                - s3_url: Pre-signed S3 URL (valid for 24 hours)
                - timestamp: ISO 8601 timestamp
        
        Raises:
            ClientError: If S3 upload fails
            ValueError: If parameters are invalid
        """
        start_time = time.time()
        
        # Validate inputs
        if not image_data:
            raise ValueError("image_data cannot be empty")
        
        if not session_id:
            raise ValueError("session_id is required")

        if not owner_sub:
            raise ValueError("owner_sub is required")
        
        # Generate unique image ID
        image_id = f"img_{uuid.uuid4().hex[:12]}"
        
        # Determine file extension from content type
        extension_map = {
            'image/jpeg': 'jpg',
            'image/png': 'png',
            'image/heic': 'heic'
        }
        extension = extension_map.get(content_type, 'jpg')
        
        # Construct S3 key: session_id/image_id.ext
        s3_key = f"{session_id}/{image_id}.{extension}"
        
        logger.info(
            f"Uploading image to S3: "
            f"session_id={session_id}, image_id={image_id}, "
            f"size={len(image_data)} bytes, content_type={content_type}"
        )
        
        try:
            # Upload to S3 with metadata
            self.s3_client.put_object(
                Bucket=self.image_bucket,
                Key=s3_key,
                Body=image_data,
                ContentType=content_type,
                Metadata={
                    'session_id': session_id,
                    'image_id': image_id,
                    'owner_sub': owner_sub,
                    'uploaded_at': datetime.now(timezone.utc).isoformat()
                }
            )

            try:
                self.store_image_metadata(
                    session_id=session_id,
                    image_id=image_id,
                    owner_sub=owner_sub,
                    s3_key=s3_key,
                    content_type=content_type,
                )
            except Exception:
                try:
                    self.s3_client.delete_object(Bucket=self.image_bucket, Key=s3_key)
                    logger.info(
                        "Cleaned up orphaned image after metadata failure: "
                        f"session_id={session_id}, image_id={image_id}, s3_key={s3_key}"
                    )
                except Exception as cleanup_error:
                    logger.critical(
                        "WARNING: Image metadata storage failed and S3 cleanup also failed. "
                        "Secure alternative: keep the explicit delete_object cleanup path and "
                        "investigate storage consistency immediately. "
                        f"session_id={session_id}, image_id={image_id}, error={cleanup_error}"
                    )
                raise

            self.verify_image_upload_complete(session_id=session_id, image_id=image_id)

            # Generate pre-signed URL (valid for 24 hours)
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.image_bucket,
                    'Key': s3_key
                },
                ExpiresIn=self.image_expiry_hours * 3600
            )
            
            elapsed_time = time.time() - start_time
            logger.info(
                f"Image uploaded successfully: "
                f"image_id={image_id}, s3_key={s3_key}, "
                f"elapsed_time={elapsed_time:.2f}s"
            )
            
            return {
                'image_id': image_id,
                's3_url': presigned_url,
                's3_key': s3_key,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(
                f"S3 upload failed: "
                f"session_id={session_id}, image_id={image_id}, "
                f"error_code={error_code}",
                exc_info=True
            )
            raise

    def _get_session_item(self, session_id: str, data_type: str) -> Optional[Dict[str, Any]]:
        """Retrieve a raw item from the sessions table by composite key."""
        try:
            response = self.sessions_table.get_item(
                Key={
                    'session_id': session_id,
                    'data_type': data_type
                }
            )
            return response.get('Item')
        except ClientError as e:
            logger.error(
                f"Error retrieving session item: session_id={session_id}, "
                f"data_type={data_type}, error={str(e)}",
                exc_info=True
            )
            return None
        
        except Exception as e:
            logger.error(
                f"Unexpected error in upload_image_to_s3: "
                f"session_id={session_id}, image_id={image_id}, "
                f"error={str(e)}",
                exc_info=True
            )
            raise
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data from DynamoDB.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Session data dictionary or None if not found
        """
        return self._get_session_item(session_id, 'profile')

    def create_session(
        self,
        language: str = 'en',
        owner_sub: str = '',
        owner_email: Optional[str] = None
    ) -> str:
        """
        Create a new session in DynamoDB.
        
        Args:
            language: Initial language preference
            owner_sub: Cognito subject that owns the session
            owner_email: Authenticated user email if available
        
        Returns:
            New session_id
        """
        session_id = f"sess_{uuid.uuid4().hex[:12]}"

        if not owner_sub:
            raise ValueError("owner_sub is required")
        
        # Calculate TTL (7 days from now)
        ttl = int((datetime.now(timezone.utc) + timedelta(days=self.session_ttl_days)).timestamp())
        
        try:
            self.sessions_table.put_item(
                Item={
                    'session_id': session_id,
                    'data_type': 'profile',
                    'user_language': language,
                    'owner_sub': owner_sub,
                    'owner_email': owner_email,
                    'preferences': {},
                    'allergies': [],
                    'conversation_history': [],
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat(),
                    'expiry_timestamp': ttl
                }
            )
            
            logger.info(f"Session created: session_id={session_id}, language={language}")
            
            return session_id
        
        except ClientError as e:
            logger.error(
                f"Error creating session: session_id={session_id}, "
                f"error={str(e)}",
                exc_info=True
            )
            raise

    def store_image_metadata(
        self,
        session_id: str,
        image_id: str,
        owner_sub: str,
        s3_key: str,
        content_type: str
    ) -> None:
        """Store uploaded image metadata in the sessions table."""
        expiry_timestamp = int(
            (datetime.now(timezone.utc) + timedelta(hours=self.image_expiry_hours)).timestamp()
        )
        self.sessions_table.put_item(
            Item={
                'session_id': session_id,
                'data_type': f'image#{image_id}',
                'image_id': image_id,
                'owner_sub': owner_sub,
                's3_key': s3_key,
                'content_type': content_type,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'expiry_timestamp': expiry_timestamp,
            }
        )

    def get_image_metadata(self, session_id: str, image_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve uploaded image metadata."""
        return self._get_session_item(session_id, f'image#{image_id}')

    def verify_image_upload_complete(self, session_id: str, image_id: str) -> bool:
        """Verify that both image metadata and the S3 object exist after upload."""
        metadata = self.get_image_metadata(session_id, image_id)
        if not metadata:
            raise ValueError("Image upload metadata was not persisted")

        s3_key = metadata.get('s3_key')
        if not s3_key:
            raise ValueError("Image upload metadata is missing the S3 key")

        try:
            self.s3_client.head_object(Bucket=self.image_bucket, Key=s3_key)
        except ClientError as exc:
            logger.warning(
                "WARNING: Image upload verification found metadata without a matching "
                "S3 object. Secure alternative: verify both DynamoDB metadata and "
                "S3 object presence before returning upload success. "
                f"session_id={session_id}, image_id={image_id}, s3_key={s3_key}"
            )
            raise ValueError("Image upload object was not persisted") from exc

        return True

    def get_image_bytes(
        self,
        session_id: str,
        image_id: str,
        owner_sub: Optional[str] = None
    ) -> bytes:
        """Load image bytes from S3 using server-side metadata lookups only."""
        metadata = self.get_image_metadata(session_id, image_id)
        if not metadata:
            raise ValueError(f"Image metadata not found: {image_id}")

        stored_owner = metadata.get('owner_sub')
        if owner_sub and stored_owner != owner_sub:
            raise PermissionError("Image does not belong to the authenticated user")

        s3_key = metadata.get('s3_key')
        expected_prefix = f"{session_id}/{image_id}."
        if not s3_key or not s3_key.startswith(expected_prefix):
            raise ValueError("Stored image key is invalid")

        response = self.s3_client.get_object(Bucket=self.image_bucket, Key=s3_key)
        return response['Body'].read()

    def detect_language(self, text: str) -> str:
        if not text or not text.strip():
            return 'en'
        telugu_chars = sum(1 for char in text if '\u0C00' <= char <= '\u0C7F')
        total_chars = sum(1 for char in text if char.isalpha())
        if total_chars == 0:
            return 'en'
        telugu_ratio = telugu_chars / total_chars
        if telugu_ratio > 0.3:
            logger.debug(f"Language detected: Telugu (telugu_chars={telugu_chars}, total_chars={total_chars}, ratio={telugu_ratio:.2f})")
            return 'te'
        else:
            logger.debug(f"Language detected: English (telugu_chars={telugu_chars}, total_chars={total_chars}, ratio={telugu_ratio:.2f})")
            return 'en'
    
    def ensure_language_consistency(self, input_language: str, response_text: str):
        detected_language = self.detect_language(response_text)
        is_consistent = (detected_language == input_language)
        if not is_consistent:
            logger.warning(f"Language inconsistency detected: expected={input_language}, detected={detected_language}")
        return is_consistent, detected_language
    
    def update_session_language(self, session_id: str, language: str):
        try:
            self.sessions_table.update_item(
                Key={'session_id': session_id, 'data_type': 'profile'},
                UpdateExpression='SET user_language = :lang, updated_at = :updated',
                ExpressionAttributeValues={':lang': language, ':updated': datetime.now(timezone.utc).isoformat()}
            )
            logger.info(f"Session language updated: session_id={session_id}, language={language}")
        except ClientError as e:
            logger.error(f"Error updating session language: session_id={session_id}, error={str(e)}", exc_info=True)
            raise

    def is_session_valid(self, session_data: Dict[str, Any]) -> bool:
        """
        Check if a session is still valid (not expired).
        
        Requirements: 16.3, 16.4
        
        Args:
            session_data: Session data dictionary from DynamoDB
        
        Returns:
            True if session is valid (within 7-day window), False otherwise
        """
        if not session_data:
            return False
        
        # Check if expiry_timestamp exists
        expiry_timestamp = session_data.get('expiry_timestamp')
        if not expiry_timestamp:
            logger.warning(f"Session missing expiry_timestamp: session_id={session_data.get('session_id')}")
            return False
        
        # Compare with current time
        current_timestamp = int(datetime.now(timezone.utc).timestamp())
        is_valid = current_timestamp < expiry_timestamp
        
        if not is_valid:
            logger.info(
                f"Session expired: session_id={session_data.get('session_id')}, "
                f"expiry={expiry_timestamp}, current={current_timestamp}"
            )
        
        return is_valid
    
    def restore_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Restore session data if still valid (within 7-day window).
        
        Requirements: 16.4
        
        Args:
            session_id: Session identifier
        
        Returns:
            Session data dictionary if valid, None if expired or not found
        """
        logger.info(f"Attempting to restore session: session_id={session_id}")
        
        try:
            # Retrieve session data
            session_data = self.get_session(session_id)
            
            if not session_data:
                logger.info(f"Session not found: session_id={session_id}")
                return None
            
            # Check if session is still valid
            if not self.is_session_valid(session_data):
                logger.info(f"Session expired, cannot restore: session_id={session_id}")
                return None
            
            # Session is valid, update the TTL to extend it
            new_ttl = int((datetime.now(timezone.utc) + timedelta(days=self.session_ttl_days)).timestamp())
            
            self.sessions_table.update_item(
                Key={
                    'session_id': session_id,
                    'data_type': 'profile'
                },
                UpdateExpression='SET expiry_timestamp = :ttl, updated_at = :updated',
                ExpressionAttributeValues={
                    ':ttl': new_ttl,
                    ':updated': datetime.now(timezone.utc).isoformat()
                }
            )
            
            logger.info(
                f"Session restored successfully: session_id={session_id}, "
                f"new_expiry={new_ttl}"
            )
            
            return session_data
        
        except ClientError as e:
            logger.error(
                f"Error restoring session: session_id={session_id}, "
                f"error={str(e)}",
                exc_info=True
            )
            return None
    
    def update_session_data(
        self,
        session_id: str,
        conversation_entry: Optional[Dict[str, str]] = None,
        preferences: Optional[Dict[str, Any]] = None,
        allergies: Optional[List[str]] = None
    ) -> bool:
        """
        Update session data with conversation history, preferences, or allergies.
        
        Requirements: 16.2, 16.5
        
        Args:
            session_id: Session identifier
            conversation_entry: Optional dict with 'user_message' and 'agent_response'
            preferences: Optional dict of user preferences to merge
            allergies: Optional list of allergies to add
        
        Returns:
            True if update successful, False otherwise
        """
        logger.info(
            f"Updating session data: session_id={session_id}, "
            f"has_conversation={conversation_entry is not None}, "
            f"has_preferences={preferences is not None}, "
            f"has_allergies={allergies is not None}"
        )
        
        try:
            # Build update expression dynamically
            update_parts = []
            expression_values = {}
            
            # Always update the updated_at timestamp
            update_parts.append('updated_at = :updated')
            expression_values[':updated'] = datetime.now(timezone.utc).isoformat()
            
            # Update conversation history if provided
            if conversation_entry:
                # Add timestamp to conversation entry
                conversation_entry['timestamp'] = datetime.now(timezone.utc).isoformat()
                
                update_parts.append('conversation_history = list_append(if_not_exists(conversation_history, :empty_list), :conversation)')
                expression_values[':conversation'] = [conversation_entry]
                expression_values[':empty_list'] = []
            
            # Update preferences if provided
            if preferences:
                # Retrieve current session to merge preferences
                session_data = self.get_session(session_id)
                if session_data:
                    current_prefs = session_data.get('preferences', {})
                    # Merge new preferences with existing ones
                    merged_prefs = {**current_prefs, **preferences}
                    update_parts.append('preferences = :prefs')
                    expression_values[':prefs'] = merged_prefs
                else:
                    logger.warning(f"Session not found for preference update: session_id={session_id}")
                    return False
            
            # Update allergies if provided
            if allergies:
                # Retrieve current session to merge allergies
                session_data = self.get_session(session_id)
                if session_data:
                    current_allergies = session_data.get('allergies', [])
                    # Add new allergies (avoid duplicates)
                    merged_allergies = list(set(current_allergies + allergies))
                    update_parts.append('allergies = :allergies')
                    expression_values[':allergies'] = merged_allergies
                else:
                    logger.warning(f"Session not found for allergy update: session_id={session_id}")
                    return False
            
            # Construct and execute update
            update_expression = 'SET ' + ', '.join(update_parts)
            
            self.sessions_table.update_item(
                Key={
                    'session_id': session_id,
                    'data_type': 'profile'
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
            logger.info(f"Session data updated successfully: session_id={session_id}")
            return True
        
        except ClientError as e:
            logger.error(
                f"Error updating session data: session_id={session_id}, "
                f"error={str(e)}",
                exc_info=True
            )
            return False

    def format_error_response(
        self,
        error_code: str,
        error_type: str,
        language: str = 'en',
        retry_available: bool = True,
        technical_details: str = '',
        suggestions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Format user-friendly error response with bilingual support.

        Requirements: 17.1, 17.5, 17.6

        Args:
            error_code: Error code identifier
            error_type: Type of error (bedrock, s3, vision, recipe)
            language: Response language ('en' or 'te')
            retry_available: Whether retry is possible
            technical_details: Technical error details for logging
            suggestions: List of actionable suggestions

        Returns:
            Dictionary with error_code, user_friendly_message, retry_available, suggestions, timestamp
        """
        # Log error to CloudWatch (Requirement 17.1, 17.6)
        # Note: Logging is done by the specific error handler methods
        # (handle_bedrock_error, handle_s3_error, handle_vision_error, handle_recipe_error)
        # to provide context-specific messages (Requirement 17.1, 17.6)
        # Error messages in English and Telugu
        error_messages = {
            'bedrock_throttled': {
                'en': "The system is busy right now. Please wait a moment and try again.",
                'te': "సిస్టమ్ ఇప్పుడు బిజీగా ఉంది. దయచేసి కొంత సమయం వేచి ఉండి మళ్లీ ప్రయత్నించండి."
            },
            'bedrock_unavailable': {
                'en': "The AI service is temporarily unavailable. Please try again in a few minutes.",
                'te': "AI సేవ తాత్కాలికంగా అందుబాటులో లేదు. దయచేసి కొన్ని నిమిషాల్లో మళ్లీ ప్రయత్నించండి."
            },
            's3_upload_failed': {
                'en': "Image upload failed. Please check your connection and try again.",
                'te': "చిత్రం అప్‌లోడ్ విఫలమైంది. దయచేసి మీ కనెక్షన్ తనిఖీ చేసి మళ్లీ ప్రయత్నించండి."
            },
            'vision_analysis_failed': {
                'en': "Could not analyze the image. Please try uploading a clearer photo.",
                'te': "చిత్రాన్ని విశ్లేషించలేకపోయాము. దయచేసి స్పష్టమైన ఫోటో అప్‌లోడ్ చేయండి."
            },
            'recipe_generation_failed': {
                'en': "Could not generate recipe. Please try again or upload more ingredient photos.",
                'te': "రెసిపీని రూపొందించలేకపోయాము. దయచేసి మళ్లీ ప్రయత్నించండి లేదా మరిన్ని పదార్థాల ఫోటోలు అప్‌లోడ్ చేయండి."
            },
            'insufficient_ingredients': {
                'en': "Not enough ingredients detected. Please upload more photos of your ingredients.",
                'te': "తగినంత పదార్థాలు కనుగొనబడలేదు. దయచేసి మీ పదార్థాల మరిన్ని ఫోటోలు అప్‌లోడ్ చేయండి."
            },
            'generic_error': {
                'en': "Something went wrong. Please try again.",
                'te': "ఏదో తప్పు జరిగింది. దయచేసి మళ్లీ ప్రయత్నించండి."
            }
        }

        # Default suggestions in English and Telugu
        default_suggestions = {
            'bedrock_throttled': {
                'en': ['Wait 30 seconds', 'Try again'],
                'te': ['30 సెకన్లు వేచి ఉండండి', 'మళ్లీ ప్రయత్నించండి']
            },
            'bedrock_unavailable': {
                'en': ['Wait a few minutes', 'Try again later'],
                'te': ['కొన్ని నిమిషాలు వేచి ఉండండి', 'తర్వాత మళ్లీ ప్రయత్నించండి']
            },
            's3_upload_failed': {
                'en': ['Check internet connection', 'Try again', 'Use a smaller image'],
                'te': ['ఇంటర్నెట్ కనెక్షన్ తనిఖీ చేయండి', 'మళ్లీ ప్రయత్నించండి', 'చిన్న చిత్రాన్ని ఉపయోగించండి']
            },
            'vision_analysis_failed': {
                'en': ['Take a clearer photo', 'Ensure good lighting', 'Try again'],
                'te': ['స్పష్టమైన ఫోటో తీయండి', 'మంచి వెలుతురు ఉండేలా చూడండి', 'మళ్లీ ప్రయత్నించండి']
            },
            'recipe_generation_failed': {
                'en': ['Upload more ingredient photos', 'Try again', 'Check your ingredients'],
                'te': ['మరిన్ని పదార్థాల ఫోటోలు అప్‌లోడ్ చేయండి', 'మళ్లీ ప్రయత్నించండి', 'మీ పదార్థాలను తనిఖీ చేయండి']
            },
            'insufficient_ingredients': {
                'en': ['Upload photos of all ingredients', 'Take clearer photos', 'Try again'],
                'te': ['అన్ని పదార్థాల ఫోటోలు అప్‌లోడ్ చేయండి', 'స్పష్టమైన ఫోటోలు తీయండి', 'మళ్లీ ప్రయత్నించండి']
            },
            'generic_error': {
                'en': ['Try again', 'Check your connection'],
                'te': ['మళ్లీ ప్రయత్నించండి', 'మీ కనెక్షన్ తనిఖీ చేయండి']
            }
        }

        # Get message and suggestions
        message = error_messages.get(error_code, error_messages['generic_error']).get(language, 'en')

        if suggestions is None:
            suggestions = default_suggestions.get(error_code, default_suggestions['generic_error']).get(language, 'en')

        return {
            'error_code': error_code,
            'user_friendly_message': message,
            'retry_available': retry_available,
            'suggestions': suggestions,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def handle_bedrock_error(
        self,
        error: Exception,
        operation: str,
        language: str = 'en',
        attempt: int = 1
    ) -> Dict[str, Any]:
        """
        Handle Bedrock API errors with retry logic.

        Requirements: 17.1, 17.5, 17.6

        Args:
            error: Exception from Bedrock API
            operation: Operation being performed (chat, recipe_generation, vision_analysis)
            language: Response language
            attempt: Current retry attempt number

        Returns:
            Formatted error response dictionary
        """
        # Determine error code
        error_code = 'generic_error'

        if isinstance(error, ClientError):
            aws_error_code = error.response['Error']['Code']

            if aws_error_code == 'ThrottlingException':
                error_code = 'bedrock_throttled'
                logger.warning(
                    f"Bedrock throttled: operation={operation}, attempt={attempt}, "
                    f"error={aws_error_code}"
                )
            elif aws_error_code in ['ModelNotReadyException', 'ServiceUnavailableException']:
                error_code = 'bedrock_unavailable'
                logger.error(
                    f"Bedrock unavailable: operation={operation}, attempt={attempt}, "
                    f"error={aws_error_code}",
                    exc_info=True
                )
            else:
                logger.error(
                    f"Bedrock error: operation={operation}, attempt={attempt}, "
                    f"error={aws_error_code}",
                    exc_info=True
                )
        else:
            logger.error(
                f"Unexpected Bedrock error: operation={operation}, attempt={attempt}, "
                f"error={str(error)}",
                exc_info=True
            )

        return self.format_error_response(
            error_code=error_code,
            error_type='bedrock',
            language=language,
            retry_available=True,
            technical_details=str(error)
        )

    def handle_s3_error(
        self,
        error: Exception,
        session_id: str,
        language: str = 'en'
    ) -> Dict[str, Any]:
        """
        Handle S3 upload errors.

        Requirements: 17.2, 17.5, 17.6

        Args:
            error: Exception from S3 operation
            session_id: User session identifier
            language: Response language

        Returns:
            Formatted error response dictionary
        """
        error_details = str(error)

        if isinstance(error, ClientError):
            aws_error_code = error.response['Error']['Code']
            error_details = f"{aws_error_code}: {error.response['Error']['Message']}"

            logger.error(
                f"S3 upload failed: session_id={session_id}, "
                f"error={aws_error_code}",
                exc_info=True
            )
        else:
            logger.error(
                f"S3 upload failed: session_id={session_id}, "
                f"error={str(error)}",
                exc_info=True
            )

        return self.format_error_response(
            error_code='s3_upload_failed',
            error_type='s3',
            language=language,
            retry_available=True,
            technical_details=error_details
        )

    def handle_vision_error(
        self,
        error: Exception,
        session_id: str,
        image_id: str,
        language: str = 'en'
    ) -> Dict[str, Any]:
        """
        Handle Vision Analyzer errors with guidance.

        Requirements: 17.3, 17.5, 17.6

        Args:
            error: Exception from vision analysis
            session_id: User session identifier
            image_id: Image identifier
            language: Response language

        Returns:
            Formatted error response dictionary with photo quality guidance
        """
        logger.error(
            f"Vision analysis failed: session_id={session_id}, "
            f"image_id={image_id}, error={str(error)}",
            exc_info=True
        )

        # Provide specific guidance for improving photo quality
        guidance_en = [
            'Take a clearer photo with good lighting',
            'Ensure ingredients are visible',
            'Avoid blurry or dark images',
            'Try again'
        ]

        guidance_te = [
            'మంచి వెలుతురుతో స్పష్టమైన ఫోటో తీయండి',
            'పదార్థాలు కనిపించేలా చూడండి',
            'అస్పష్టమైన లేదా చీకటి చిత్రాలను నివారించండి',
            'మళ్లీ ప్రయత్నించండి'
        ]

        suggestions = guidance_te if language == 'te' else guidance_en

        return self.format_error_response(
            error_code='vision_analysis_failed',
            error_type='vision',
            language=language,
            retry_available=True,
            technical_details=str(error),
            suggestions=suggestions
        )

    def handle_recipe_error(
        self,
        error: Exception,
        session_id: str,
        language: str = 'en',
        insufficient_ingredients: bool = False
    ) -> Dict[str, Any]:
        """
        Handle Recipe Generator errors with suggestions.

        Requirements: 17.4, 17.5, 17.6

        Args:
            error: Exception from recipe generation
            session_id: User session identifier
            language: Response language
            insufficient_ingredients: Whether error is due to insufficient ingredients

        Returns:
            Formatted error response dictionary with actionable suggestions
        """
        error_code = 'insufficient_ingredients' if insufficient_ingredients else 'recipe_generation_failed'

        logger.error(
            f"Recipe generation failed: session_id={session_id}, "
            f"insufficient_ingredients={insufficient_ingredients}, "
            f"error={str(error)}",
            exc_info=True
        )

        return self.format_error_response(
            error_code=error_code,
            error_type='recipe',
            language=language,
            retry_available=True,
            technical_details=str(error)
        )

    
