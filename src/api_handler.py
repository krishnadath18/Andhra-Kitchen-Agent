"""
API Handler for Andhra Kitchen Agent

Lambda function handler for API Gateway requests.
Handles image upload endpoint with validation.
"""

import json
import base64
import time
import logging
from datetime import datetime, timedelta, timezone
from email.parser import BytesParser
from email.policy import default
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.kitchen_agent_core import KitchenAgentCore
from src.auth_utils import AuthContext, AuthenticationError, require_authenticated_user
from src.vision_analyzer import VisionAnalyzer
from config.env import Config
from src.security_utils import (
    validate_session_id,
    validate_language,
    sanitize_user_input,
    validate_duration_hours,
    validate_recipe_count,
    validate_image_filename,
    validate_image_data,
    create_secure_response_headers,
    sanitize_for_logging
)
from src.rate_limiter import check_rate_limit, rate_limiter

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, Config.LOG_LEVEL))

# Initialize Kitchen Agent Core, Vision Analyzer, and Recipe Generator
kitchen_agent = KitchenAgentCore()
vision_analyzer = VisionAnalyzer()

# Import RecipeGenerator, AgentCoreOrchestrator, ShoppingOptimizer, and ReminderService
from src.recipe_generator import RecipeGenerator
from src.agentcore_orchestrator import AgentCoreOrchestrator
from src.shopping_optimizer import ShoppingOptimizer
from src.reminder_service import ReminderService

recipe_generator = RecipeGenerator()
agentcore_orchestrator = AgentCoreOrchestrator()
shopping_optimizer = ShoppingOptimizer()
reminder_service = ReminderService()

# Supported image formats
SUPPORTED_FORMATS = ['image/jpeg', 'image/png', 'image/heic']
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_JSON_REQUEST_SIZE_BYTES = Config.MAX_REQUEST_SIZE_BYTES
MAX_UPLOAD_REQUEST_SIZE_BYTES = Config.MAX_UPLOAD_REQUEST_SIZE_BYTES


def get_header(event: Dict[str, Any], header_name: str) -> Optional[str]:
    """Read a request header case-insensitively."""
    headers = event.get('headers') or {}
    for key, value in headers.items():
        if key.lower() == header_name.lower():
            return value
    return None


def get_auth_context(event: Dict[str, Any]) -> Tuple[Optional[AuthContext], Optional[Dict[str, Any]]]:
    """Authenticate the request and return either context or an API response."""
    try:
        return require_authenticated_user(event), None
    except AuthenticationError as exc:
        logger.warning(f"Authentication failed: {exc}")
        return None, create_response(
            status_code=401,
            body={
                'error': 'unauthorized',
                'message': str(exc)
            }
        )


def load_owned_session(
    raw_session_id: str,
    auth_context: AuthContext
) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Validate and load a session owned by the authenticated user."""
    try:
        session_id = validate_session_id(raw_session_id)
    except ValueError as exc:
        return None, None, create_response(
            status_code=400,
            body={
                'error': 'invalid_request',
                'message': f'Invalid session_id: {exc}'
            }
        )

    session_data = kitchen_agent.get_session(session_id)
    if not session_data:
        return None, None, create_response(
            status_code=404,
            body={
                'error': 'session_not_found',
                'message': f'Session not found: {session_id}. Please create a new session.'
            }
        )

    owner_sub = session_data.get('owner_sub')
    if not owner_sub:
        return None, None, create_response(
            status_code=401,
            body={
                'error': 'legacy_session_invalid',
                'message': 'This session was created before authentication was required. '
                           'Please sign in and create a new session.'
            }
        )

    if owner_sub != auth_context.sub:
        return None, None, create_response(
            status_code=403,
            body={
                'error': 'forbidden',
                'message': 'You do not have access to this session.'
            }
        )

    if not kitchen_agent.is_session_valid(session_data):
        return None, None, create_response(
            status_code=401,
            body={
                'error': 'session_expired',
                'message': 'Session has expired. Please create a new session.'
            }
        )

    return session_id, session_data, None


def enforce_rate_limit(session_id: str, endpoint: str) -> Optional[Dict[str, Any]]:
    """Enforce rate limiting with consistent headers and response shape."""
    result = check_rate_limit(session_id, endpoint)
    if result.allowed:
        return None

    retry_after = result.retry_after_seconds or 60
    status_code = result.http_status or 429
    if status_code == 503:
        logger.error(
            f"Rate limiter unavailable: session_id={session_id}, "
            f"endpoint={endpoint}, retry_after={retry_after}s"
        )
        error_code = 'service_unavailable'
        message = 'Rate limiting is temporarily unavailable. Please try again shortly.'
    else:
        logger.warning(
            f"Rate limit exceeded: session_id={session_id}, "
            f"endpoint={endpoint}, retry_after={retry_after}s"
        )
        error_code = 'rate_limit_exceeded'
        message = f'Rate limit exceeded. Please try again in {retry_after} seconds.'
    return create_response(
        status_code=status_code,
        body={
            'error': error_code,
            'message': message,
            'requests_limit': result.requests_limit,
            'reset_time': result.reset_time,
            'retry_after_seconds': retry_after
        },
        headers={
            'Retry-After': str(retry_after),
            'X-RateLimit-Limit': str(result.requests_limit),
            'X-RateLimit-Remaining': str(result.remaining),
            'X-RateLimit-Reset': result.reset_time
        }
    )


def get_request_body_size(event: Dict[str, Any]) -> int:
    """Return the decoded request body size in bytes."""
    content_length = get_header(event, 'Content-Length')
    if content_length:
        try:
            return int(content_length)
        except ValueError:
            logger.warning(f"Invalid Content-Length header: {content_length}")

    body = event.get('body', '')
    if not body:
        return 0

    if event.get('isBase64Encoded', False):
        try:
            return len(base64.b64decode(body))
        except Exception:
            return len(body.encode('utf-8'))

    return len(body.encode('utf-8'))


def ensure_request_size_limit(event: Dict[str, Any], max_size_bytes: int) -> None:
    """Reject requests that exceed the configured body-size limit."""
    request_size = get_request_body_size(event)
    if request_size > max_size_bytes:
        raise ValueError(
            f"Request body exceeds the maximum allowed size of {max_size_bytes} bytes"
        )


def get_rate_limit_headers(session_id: Optional[str], endpoint: Optional[str]) -> Dict[str, str]:
    """Return informational rate-limit headers without mutating counters."""
    if not Config.INCLUDE_RATE_LIMIT_HEADERS or not session_id or not endpoint:
        return {}

    try:
        info = rate_limiter.get_rate_limit_info(session_id, endpoint)
        if not info.get('enabled'):
            return {}

        reset_time = (
            datetime.now(timezone.utc) + timedelta(seconds=info['resets_in_seconds'])
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")

        return {
            'X-RateLimit-Limit': str(info['limit']),
            'X-RateLimit-Remaining': str(info['remaining']),
            'X-RateLimit-Reset': reset_time,
        }
    except Exception as exc:
        logger.warning(
            f"Failed to add rate limit headers: session_id={session_id}, "
            f"endpoint={endpoint}, error={exc}"
        )
        return {}


def validation_error_status_code(error: Exception) -> int:
    """Map validation errors to the appropriate HTTP status."""
    message = str(error).lower()
    if 'maximum allowed size' in message or 'exceeds' in message:
        return 413
    return 400


def parse_multipart_form(event: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, Dict[str, Any]]]:
    """Parse multipart/form-data into scalar fields and file payloads."""
    ensure_request_size_limit(event, MAX_UPLOAD_REQUEST_SIZE_BYTES)
    content_type = get_header(event, 'Content-Type') or ''
    if 'multipart/form-data' not in content_type.lower():
        raise ValueError('Content-Type must be multipart/form-data')

    body = event.get('body', '')
    if not body:
        raise ValueError('Request body is empty')

    body_bytes = base64.b64decode(body) if event.get('isBase64Encoded', False) else body.encode('utf-8')
    message = BytesParser(policy=default).parsebytes(
        f'Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n'.encode('utf-8') + body_bytes
    )

    if not message.is_multipart():
        raise ValueError('Request body is not valid multipart/form-data')

    fields: Dict[str, str] = {}
    files: Dict[str, Dict[str, Any]] = {}

    for part in message.iter_parts():
        if part.get_content_disposition() != 'form-data':
            continue

        field_name = part.get_param('name', header='content-disposition')
        if not field_name:
            continue

        payload = part.get_payload(decode=True) or b''
        filename = part.get_filename()
        if filename:
            files[field_name] = {
                'filename': filename,
                'content_type': part.get_content_type(),
                'content': payload,
            }
        else:
            charset = part.get_content_charset() or 'utf-8'
            fields[field_name] = payload.decode(charset)

    return fields, files


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for API Gateway requests.
    
    Routes requests to appropriate handlers based on HTTP method and path.
    
    Args:
        event: API Gateway event
        context: Lambda context
    
    Returns:
        API Gateway response with statusCode, headers, and body
    """
    try:
        # Extract request details
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        
        logger.info(f"Received request: {http_method} {path}")

        if http_method == 'OPTIONS':
            return create_response(
                status_code=200,
                body={'status': 'ok'},
            )
        
        # Route to appropriate handler
        if http_method == 'POST' and path == '/chat':
            return handle_chat(event)
        elif http_method == 'POST' and path == '/upload-image':
            return handle_upload_image(event)
        elif http_method == 'POST' and path == '/analyze-image':
            return handle_analyze_image(event)
        elif http_method == 'POST' and path == '/generate-recipes':
            return handle_generate_recipes(event)
        elif http_method == 'POST' and path == '/generate-shopping-list':
            return handle_generate_shopping_list(event)
        elif http_method == 'POST' and path == '/session':
            return handle_create_session(event)
        elif http_method == 'GET' and path.startswith('/session/'):
            return handle_get_session(event)
        elif http_method == 'GET' and path.startswith('/reminders/'):
            return handle_get_reminders(event)
        elif http_method == 'POST' and '/reminders/' in path and path.endswith('/dismiss'):
            return handle_dismiss_reminder(event)
        elif http_method == 'POST' and '/reminders/' in path and path.endswith('/snooze'):
            return handle_snooze_reminder(event)
        else:
            return create_response(
                status_code=404,
                body={'error': 'not_found', 'message': 'Endpoint not found'}
            )
    
    except Exception as e:
        logger.error(f"Unhandled error in lambda_handler: {str(e)}", exc_info=True)
        return create_response(
            status_code=500,
            body={
                'error': 'internal_server_error',
                'message': 'An unexpected error occurred'
            }
        )


def handle_chat(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST /chat endpoint.
    
    Accepts session_id, message, language (optional), context (optional)
    and calls AgentCoreOrchestrator.invoke_agent() to process the chat message.
    Returns response with suggested_actions, workflow_id, status, and execution_time_ms.
    
    Requirements: 1.1, 1.2, 1.5, 14.1, 14.2, 14.4, 14.5
    
    Args:
        event: API Gateway event
    
    Returns:
        API Gateway response with chat response and suggested actions
    """
    start_time = time.time()
    
    try:
        auth_context, auth_error = get_auth_context(event)
        if auth_error:
            return auth_error

        # Parse request body
        body = parse_request_body(event)
        
        session_id, _, session_error = load_owned_session(body.get('session_id', ''), auth_context)
        if session_error:
            return session_error
        
        # Validate and sanitize message
        raw_message = body.get('message', '')
        if not raw_message:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_request',
                    'message': 'Missing required field: message'
                }
            )
        
        try:
            message = sanitize_user_input(raw_message, max_length=5000)
        except ValueError as e:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_request',
                    'message': f'Invalid message: {str(e)}'
                }
            )
        
        # Optional fields
        language = body.get('language', 'en')
        try:
            language = validate_language(language)
        except ValueError as e:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_language',
                    'message': str(e)
                }
            )
        
        context = body.get('context', {})

        rate_limit_response = enforce_rate_limit(session_id, '/chat')
        if rate_limit_response:
            return rate_limit_response
        
        # Use sanitized logging
        logger.info(
            f"Processing chat message: session_id={session_id}, "
            f"message_length={len(message)}, language={language}, "
            f"context={sanitize_for_logging(context)}"
        )
        
        # Add language to context
        context['language'] = language
        if body.get('image_id'):
            context['image_id'] = body['image_id']
            context['image_uploaded'] = True
        
        # Requirement 1.1, 1.2: Call AgentCoreOrchestrator.invoke_agent()
        try:
            workflow_result = agentcore_orchestrator.invoke_agent(
                user_request=message,
                session_id=session_id,
                context=context
            )
        except Exception as e:
            logger.error(
                f"AgentCore invocation failed: session_id={session_id}, "
                f"error={str(e)}",
                exc_info=True
            )
            # Requirement 14.5: Return appropriate HTTP status codes
            return create_response(
                status_code=500,
                body={
                    'error': 'agent_invocation_failed',
                    'message': 'Failed to process chat message. Please try again.',
                    'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
                }
            )
        
        # Extract response and metadata from workflow result
        response_text = workflow_result.get('final_response', '')
        workflow_id = workflow_result.get('workflow_id', '')
        status = workflow_result.get('status', 'completed')
        execution_time_ms = workflow_result.get('execution_time_ms', 0)
        
        # Generate suggested actions based on workflow results
        suggested_actions = []
        subtask_results = workflow_result.get('subtask_results', {})
        
        # Check if we have inventory from vision analysis
        has_inventory = any('inventory' in result for result in subtask_results.values())
        if has_inventory:
            suggested_actions.append('view_recipes')
        
        # Check if we have recipes
        has_recipes = any('recipes' in result for result in subtask_results.values())
        if has_recipes:
            suggested_actions.extend(['view_recipes', 'generate_shopping_list'])
        
        # If no specific actions, suggest general actions
        if not suggested_actions:
            if 'image' in message.lower() or 'photo' in message.lower():
                suggested_actions.append('upload_image')
            else:
                suggested_actions.append('upload_image')
        
        # Update session with conversation history
        kitchen_agent.update_session_data(
            session_id=session_id,
            conversation_entry={
                'user_message': message,
                'agent_response': response_text
            }
        )
        
        # Calculate total elapsed time
        total_elapsed_time = int((time.time() - start_time) * 1000)
        
        logger.info(
            f"Chat message processed successfully: session_id={session_id}, "
            f"workflow_id={workflow_id}, status={status}, "
            f"execution_time_ms={total_elapsed_time}"
        )
        
        # Requirement 14.5: Return appropriate HTTP status codes (200 for success)
        return create_response(
            status_code=200,
            body={
                'response': response_text,
                'suggested_actions': suggested_actions,
                'workflow_id': workflow_id,
                'status': status,
                'execution_time_ms': total_elapsed_time,
                'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
            },
            rate_limit_session_id=session_id,
            rate_limit_endpoint='/chat'
        )
    
    except ValueError as e:
        logger.warning(f"Validation error in handle_chat: {str(e)}")
        return create_response(
            status_code=validation_error_status_code(e),
            body={
                'error': 'validation_error',
                'message': str(e)
            }
        )
    
    except Exception as e:
        logger.error(f"Error in handle_chat: {str(e)}", exc_info=True)
        # Requirement 14.5: Return appropriate HTTP status codes (500 for server errors)
        return create_response(
            status_code=500,
            body={
                'error': 'chat_processing_failed',
                'message': 'Failed to process chat message. Please try again.',
                'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
            }
        )


def handle_upload_image(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST /upload-image endpoint.
    
    Validates image format and size, uploads to S3, and returns image_id plus
    deprecated compatibility fields (`s3_url`, `s3_key`).
    
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
    
    Args:
        event: API Gateway event
    
    Returns:
        API Gateway response
    """
    try:
        auth_context, auth_error = get_auth_context(event)
        if auth_error:
            return auth_error

        content_type = get_header(event, 'Content-Type') or ''

        if 'multipart/form-data' in content_type.lower():
            fields, files = parse_multipart_form(event)
            session_id = fields.get('session_id')
            file_part = files.get('file') or next(iter(files.values()), None)
            if not session_id:
                return create_response(
                    status_code=400,
                    body={
                        'error': 'invalid_request',
                        'message': 'Missing required field: session_id'
                    }
                )
            if not file_part:
                return create_response(
                    status_code=400,
                    body={
                        'error': 'invalid_request',
                        'message': 'No image file provided'
                    }
                )
            image_data = file_part['content']
            provided_content_type = file_part.get('content_type') or 'application/octet-stream'
        else:
            body = parse_request_body(event, max_size_bytes=MAX_UPLOAD_REQUEST_SIZE_BYTES)
            session_id = body.get('session_id')
            if not session_id:
                return create_response(
                    status_code=400,
                    body={
                        'error': 'invalid_request',
                        'message': 'Missing required field: session_id'
                    }
                )

            image_data_b64 = body.get('image_data')
            provided_content_type = body.get('content_type', 'image/jpeg')
            if not image_data_b64:
                return create_response(
                    status_code=400,
                    body={
                        'error': 'invalid_request',
                        'message': 'Missing required field: image_data'
                    }
                )
            try:
                image_data = base64.b64decode(image_data_b64, validate=True)
            except Exception as exc:
                logger.error(f"Failed to decode base64 image: {exc}")
                return create_response(
                    status_code=400,
                    body={
                        'error': 'invalid_image_data',
                        'message': 'Invalid base64-encoded image data'
                    }
                )

        image_size = len(image_data)
        if image_size > MAX_FILE_SIZE_BYTES:
            return create_response(
                status_code=413,
                body={
                    'error': 'file_too_large',
                    'message': f'Image size exceeds {MAX_FILE_SIZE_MB}MB limit',
                    'max_size_mb': MAX_FILE_SIZE_MB,
                    'received_size_mb': round(image_size / (1024 * 1024), 2)
                }
            )

        if provided_content_type not in SUPPORTED_FORMATS:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_format',
                    'message': 'Unsupported image format. Supported formats: JPEG, PNG, HEIC',
                    'received_format': provided_content_type
                }
            )

        try:
            detected_content_type = validate_image_data(image_data, max_size_mb=MAX_FILE_SIZE_MB)
        except ValueError as exc:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_format',
                    'message': str(exc),
                    'received_format': provided_content_type
                }
            )

        if detected_content_type != provided_content_type:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_format',
                    'message': 'Declared image content type does not match the uploaded file.',
                    'received_format': provided_content_type,
                    'detected_format': detected_content_type
                }
            )

        session_id, _, session_error = load_owned_session(session_id, auth_context)
        if session_error:
            return session_error

        rate_limit_response = enforce_rate_limit(session_id, '/upload-image')
        if rate_limit_response:
            return rate_limit_response

        logger.info(
            f"Image upload validated: session_id={session_id}, "
            f"size={image_size} bytes, content_type={detected_content_type}"
        )
        
        # Requirement 3.3, 3.4: Call KitchenAgentCore.upload_image_to_s3()
        result = kitchen_agent.upload_image_to_s3(
            image_data=image_data,
            session_id=session_id,
            owner_sub=auth_context.sub,
            content_type=detected_content_type
        )
        
        # Requirement 3.5: Return image_id and s3_url
        return create_response(
            status_code=200,
            body={
                'session_id': session_id,
                'image_id': result['image_id'],
                's3_url': result['s3_url'],
                's3_key': result['s3_key'],
                'status': 'uploaded',
                'message': 'Image uploaded successfully. Analyzing ingredients...',
                'timestamp': result['timestamp']
            },
            rate_limit_session_id=session_id,
            rate_limit_endpoint='/upload-image'
        )
    
    except ValueError as e:
        logger.warning(f"Validation error in handle_upload_image: {str(e)}")
        return create_response(
            status_code=validation_error_status_code(e),
            body={
                'error': 'validation_error',
                'message': str(e)
            }
        )
    
    except Exception as e:
        logger.error(f"Error in handle_upload_image: {str(e)}", exc_info=True)
        return create_response(
            status_code=500,
            body={
                'error': 'upload_failed',
                'message': 'Failed to upload image. Please try again.'
            }
        )


def handle_analyze_image(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST /analyze-image endpoint.
    
    Accepts session_id, image_id, and language, then resolves the image
    server-side before calling VisionAnalyzer.
    to detect ingredients from the uploaded image.
    
    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7
    
    Args:
        event: API Gateway event
    
    Returns:
        API Gateway response with Inventory JSON
    """
    try:
        auth_context, auth_error = get_auth_context(event)
        if auth_error:
            return auth_error

        # Parse request body
        body = parse_request_body(event)
        
        # Requirement 4.1: Extract required fields
        session_id = body.get('session_id')
        image_id = body.get('image_id')
        language = body.get('language', 'en')
        
        # Validate required fields
        if not session_id:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_request',
                    'message': 'Missing required field: session_id'
                }
            )
        
        if not image_id:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_request',
                    'message': 'Missing required field: image_id'
                }
            )

        try:
            language = validate_language(language)
        except ValueError as exc:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_language',
                    'message': str(exc)
                }
            )
        
        session_id, _, session_error = load_owned_session(session_id, auth_context)
        if session_error:
            return session_error

        rate_limit_response = enforce_rate_limit(session_id, '/analyze-image')
        if rate_limit_response:
            return rate_limit_response
        
        logger.info(
            f"Analyzing image: session_id={session_id}, "
            f"image_id={image_id}, language={language}"
        )

        try:
            image_data = kitchen_agent.get_image_bytes(
                session_id=session_id,
                image_id=image_id,
                owner_sub=auth_context.sub
            )
        except Exception as e:
            logger.error(
                f"Failed to retrieve image from S3: session_id={session_id}, "
                f"image_id={image_id}, error={str(e)}"
            )
            return create_response(
                status_code=422,
                body={
                    'error': 'image_retrieval_failed',
                    'message': 'Could not retrieve image from storage. Please try uploading again.'
                }
            )
        
        # Requirement 4.1, 4.2, 4.3, 4.4, 4.5: Call VisionAnalyzer.analyze_image()
        try:
            inventory = vision_analyzer.analyze_image(
                image_data=image_data,
                session_id=session_id,
                image_id=image_id
            )
        except Exception as e:
            logger.error(
                f"Vision analysis failed: session_id={session_id}, "
                f"image_id={image_id}, error={str(e)}"
            )
            # Requirement 4.7: Handle analysis failures with error messages
            return create_response(
                status_code=422,
                body={
                    'error': 'analysis_failed',
                    'message': 'Could not analyze image. Please ensure the photo is clear and well-lit.',
                    'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
                }
            )
        
        # Requirement 4.6: Complete analysis within 10 seconds (handled by VisionAnalyzer timeout)
        # Requirement 4.5: Return Inventory JSON
        total_items = inventory.get('total_items', 0)
        
        # Generate appropriate message based on language and results
        if language == 'te':
            if total_items == 0:
                message = "ఏ పదార్థాలు కనుగొనబడలేదు. దయచేసి మరొక ఫోటో అప్‌లోడ్ చేయండి."
            elif total_items == 1:
                message = "1 పదార్థం కనుగొనబడింది! రెసిపీ సూచనలు కావాలా?"
            else:
                message = f"{total_items} పదార్థాలు కనుగొనబడ్డాయి! రెసిపీ సూచనలు కావాలా?"
        else:
            if total_items == 0:
                message = "No ingredients detected. Please try uploading another photo."
            elif total_items == 1:
                message = "Found 1 ingredient! Would you like recipe suggestions?"
            else:
                message = f"Found {total_items} ingredients! Would you like recipe suggestions?"
        
        logger.info(
            f"Image analysis successful: session_id={session_id}, "
            f"image_id={image_id}, total_items={total_items}"
        )
        
        # Return Inventory JSON with success message
        return create_response(
            status_code=200,
            body={
                'session_id': session_id,
                'image_id': image_id,
                'inventory': inventory,
                'message': message,
                'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
            },
            rate_limit_session_id=session_id,
            rate_limit_endpoint='/analyze-image'
        )
    
    except ValueError as e:
        logger.warning(f"Validation error in handle_analyze_image: {str(e)}")
        return create_response(
            status_code=validation_error_status_code(e),
            body={
                'error': 'validation_error',
                'message': str(e)
            }
        )
    
    except Exception as e:
        logger.error(f"Error in handle_analyze_image: {str(e)}", exc_info=True)
        return create_response(
            status_code=500,
            body={
                'error': 'analysis_failed',
                'message': 'Failed to analyze image. Please try again.'
            }
        )


def handle_generate_recipes(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST /generate-recipes endpoint.
    
    Accepts session_id, inventory, preferences, allergies, language, count
    and calls RecipeGenerator.generate_recipes() to create Andhra-style recipes.
    
    Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8
    
    Args:
        event: API Gateway event
    
    Returns:
        API Gateway response with list of Recipe JSON objects
    """
    try:
        auth_context, auth_error = get_auth_context(event)
        if auth_error:
            return auth_error

        # Parse request body
        body = parse_request_body(event)
        
        # Requirement 8.1: Extract required fields
        session_id = body.get('session_id')
        inventory = body.get('inventory')
        
        # Optional fields
        preferences = body.get('preferences')
        allergies = body.get('allergies')
        language = body.get('language', 'en')
        count = body.get('count', 3)
        
        session_id, _, session_error = load_owned_session(session_id, auth_context)
        if session_error:
            return session_error

        if not inventory:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_request',
                    'message': 'Missing required field: inventory'
                }
            )
        
        # Validate inventory has ingredients
        if not isinstance(inventory, dict):
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_request',
                    'message': 'Invalid inventory format. Expected JSON object.'
                }
            )
        
        total_items = inventory.get('total_items', 0)
        if total_items == 0:
            # Requirement 8.4: Handle empty inventory
            if language == 'te':
                message = "తగినంత పదార్థాలు కనుగొనబడలేదు. దయచేసి మరిన్ని ఫోటోలు అప్‌లోడ్ చేయండి లేదా మీ వద్ద ఉన్నవి వివరించండి."
            else:
                message = "Not enough ingredients detected. Please upload more photos or describe what you have."
            
            return create_response(
                status_code=400,
                body={
                    'error': 'insufficient_ingredients',
                    'message': message
                }
            )
        
        # Validate count is within bounds (2-5)
        try:
            count = validate_recipe_count(count)
        except ValueError:
            count = 3  # Default to 3 if invalid
        if count < 2 or count > 5:
            count = 3

        rate_limit_response = enforce_rate_limit(session_id, '/generate-recipes')
        if rate_limit_response:
            return rate_limit_response
        
        logger.info(
            f"Generating recipes: session_id={session_id}, "
            f"total_items={total_items}, count={count}, language={language}"
        )
        
        # Add session_id to inventory if not present
        if 'session_id' not in inventory:
            inventory['session_id'] = session_id
        
        # Requirement 8.1, 8.2: Call RecipeGenerator.generate_recipes()
        # RecipeGenerator will query Memory Store for preferences/allergies if not provided
        try:
            recipes = recipe_generator.generate_recipes(
                inventory=inventory,
                preferences=preferences,
                allergies=allergies,
                language=language,
                count=count
            )
        except Exception as e:
            logger.error(
                f"Recipe generation failed: session_id={session_id}, "
                f"error={str(e)}"
            )
            # Requirement 8.8: Handle recipe generation failures
            if language == 'te':
                message = "రెసిపీలు రూపొందించడం విఫలమైంది. దయచేసి మళ్లీ ప్రయత్నించండి."
            else:
                message = "Failed to generate recipes. Please try again."
            
            return create_response(
                status_code=500,
                body={
                    'error': 'recipe_generation_failed',
                    'message': message,
                    'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
                }
            )
        
        # Requirement 8.7: Generate between 2 and 5 recipe options
        if not recipes or len(recipes) == 0:
            if language == 'te':
                message = "అందుబాటులో ఉన్న పదార్థాలతో రెసిపీలు రూపొందించడం సాధ్యం కాలేదు."
            else:
                message = "Could not generate recipes with available ingredients."
            
            return create_response(
                status_code=422,
                body={
                    'error': 'no_recipes_generated',
                    'message': message,
                    'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
                }
            )
        
        # Generate appropriate message based on language and recipe count
        recipe_count = len(recipes)
        if language == 'te':
            if recipe_count == 1:
                message = "మీ పదార్థాల ఆధారంగా 1 రెసిపీ సూచన ఇక్కడ ఉంది!"
            else:
                message = f"మీ పదార్థాల ఆధారంగా {recipe_count} రెసిపీ సూచనలు ఇక్కడ ఉన్నాయి!"
        else:
            if recipe_count == 1:
                message = "Here is 1 recipe suggestion based on your ingredients!"
            else:
                message = f"Here are {recipe_count} recipe suggestions based on your ingredients!"
        
        logger.info(
            f"Recipe generation successful: session_id={session_id}, "
            f"recipe_count={recipe_count}"
        )
        
        # Requirement 8.3, 8.5, 8.6: Return list of Recipe JSON objects
        # Each recipe includes: name, prep_time, serving_size, estimated_cost,
        # cooking_steps, nutrition_information
        return create_response(
            status_code=200,
            body={
                'session_id': session_id,
                'recipes': recipes,
                'message': message,
                'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
            },
            rate_limit_session_id=session_id,
            rate_limit_endpoint='/generate-recipes'
        )
    
    except ValueError as e:
        logger.warning(f"Validation error in handle_generate_recipes: {str(e)}")
        return create_response(
            status_code=validation_error_status_code(e),
            body={
                'error': 'validation_error',
                'message': str(e)
            }
        )
    
    except Exception as e:
        logger.error(f"Error in handle_generate_recipes: {str(e)}", exc_info=True)
        return create_response(
            status_code=500,
            body={
                'error': 'recipe_generation_failed',
                'message': 'Failed to generate recipes. Please try again.'
            }
        )


def handle_generate_shopping_list(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST /generate-shopping-list endpoint.
    
    Accepts session_id, recipe_id, current_inventory, language
    and generates an optimized shopping list with reminders for price-sensitive items.
    
    Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 11.1
    
    Args:
        event: API Gateway event
    
    Returns:
        API Gateway response with Shopping List JSON and reminders
    """
    try:
        auth_context, auth_error = get_auth_context(event)
        if auth_error:
            return auth_error

        # Parse request body
        body = parse_request_body(event)
        
        # Extract required fields
        session_id = body.get('session_id')
        recipe_id = body.get('recipe_id')
        
        # Optional fields
        current_inventory = body.get('current_inventory', {})
        language = body.get('language', 'en')
        
        session_id, session_data, session_error = load_owned_session(session_id, auth_context)
        if session_error:
            return session_error

        if not recipe_id:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_request',
                    'message': 'Missing required field: recipe_id'
                }
            )
        
        # Validate language parameter
        if language not in ['en', 'te']:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_language',
                    'message': 'Language must be either "en" or "te"'
                }
            )
        
        logger.info(
            f"Generating shopping list: session_id={session_id}, "
            f"recipe_id={recipe_id}, language={language}"
        )

        rate_limit_response = enforce_rate_limit(session_id, '/generate-shopping-list')
        if rate_limit_response:
            return rate_limit_response
        
        # Get recipe from session data
        # Recipes are stored in last_recipes or we need to retrieve from memory
        recipe = None
        last_recipes = session_data.get('last_recipes', [])
        
        for r in last_recipes:
            if r.get('recipe_id') == recipe_id:
                recipe = r
                break
        
        if not recipe:
            logger.warning(
                f"Recipe not found in session: session_id={session_id}, "
                f"recipe_id={recipe_id}"
            )
            if language == 'te':
                message = "రెసిపీ కనుగొనబడలేదు. దయచేసి మొదట రెసిపీలను రూపొందించండి."
            else:
                message = "Recipe not found. Please generate recipes first."
            
            return create_response(
                status_code=404,
                body={
                    'error': 'recipe_not_found',
                    'message': message
                }
            )
        
        # Add session_id to recipe if not present
        if 'session_id' not in recipe:
            recipe['session_id'] = session_id
        
        # If current_inventory is empty, use last_inventory from session
        if not current_inventory or current_inventory.get('total_items', 0) == 0:
            current_inventory = session_data.get('last_inventory', {})
            logger.info(
                f"Using last_inventory from session: session_id={session_id}, "
                f"total_items={current_inventory.get('total_items', 0)}"
            )
        
        # Ensure current_inventory has required structure
        if not isinstance(current_inventory, dict):
            current_inventory = {'total_items': 0, 'ingredients': []}
        if 'ingredients' not in current_inventory:
            current_inventory['ingredients'] = []
        if 'total_items' not in current_inventory:
            current_inventory['total_items'] = len(current_inventory.get('ingredients', []))
        
        # Requirement 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7:
        # Call ShoppingOptimizer.generate_shopping_list()
        try:
            shopping_list = shopping_optimizer.generate_shopping_list(
                recipe=recipe,
                current_inventory=current_inventory,
                language=language
            )
        except Exception as e:
            logger.error(
                f"Shopping list generation failed: session_id={session_id}, "
                f"recipe_id={recipe_id}, error={str(e)}"
            )
            if language == 'te':
                message = "షాపింగ్ జాబితా రూపొందించడం విఫలమైంది. దయచేసి మళ్లీ ప్రయత్నించండి."
            else:
                message = "Failed to generate shopping list. Please try again."
            
            return create_response(
                status_code=500,
                body={
                    'error': 'shopping_list_generation_failed',
                    'message': message,
                    'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
                }
            )
        
        # Requirement 11.1: Detect price-sensitive items and schedule reminders
        reminders = []
        shopping_items = shopping_list.get('items', [])
        
        if shopping_items:
            try:
                # Detect price-sensitive items
                price_sensitive_suggestions = reminder_service.detect_price_sensitive_items(
                    shopping_items
                )
                
                logger.info(
                    f"Detected price-sensitive items: session_id={session_id}, "
                    f"count={len(price_sensitive_suggestions)}"
                )
                
                # Schedule reminders for price-sensitive items
                for suggestion in price_sensitive_suggestions:
                    try:
                        # Calculate trigger time (e.g., tomorrow morning at 8 AM)
                        from datetime import timedelta
                        trigger_time = datetime.now(timezone.utc) + timedelta(days=1)
                        trigger_time = trigger_time.replace(hour=8, minute=0, second=0, microsecond=0)
                        
                        # Schedule reminder
                        reminder_id = reminder_service.schedule_reminder(
                            session_id=session_id,
                            content=suggestion['content'],
                            trigger_time=trigger_time,
                            reason=suggestion['reason'],
                            reminder_type='shopping'
                        )
                        
                        # Add to reminders list
                        reminders.append({
                            'reminder_id': reminder_id,
                            'content': suggestion['content'],
                            'reason': suggestion['reason'],
                            'trigger_time': trigger_time.isoformat() + 'Z'
                        })
                        
                        logger.info(
                            f"Reminder scheduled: session_id={session_id}, "
                            f"reminder_id={reminder_id}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to schedule reminder: session_id={session_id}, "
                            f"error={str(e)}"
                        )
                        # Continue even if reminder scheduling fails
                        
            except Exception as e:
                logger.warning(
                    f"Price-sensitive detection failed: session_id={session_id}, "
                    f"error={str(e)}"
                )
                # Continue even if price-sensitive detection fails
        
        # Add reminders to shopping list
        shopping_list['reminders'] = reminders
        
        # Generate appropriate message based on language
        total_cost = shopping_list.get('total_cost', 0)
        item_count = len(shopping_items)
        
        if language == 'te':
            if item_count == 0:
                message = "మీ వద్ద అన్ని పదార్థాలు ఉన్నాయి! షాపింగ్ అవసరం లేదు."
            elif item_count == 1:
                message = f"షాపింగ్ జాబితా సిద్ధంగా ఉంది! మొత్తం అంచనా ఖర్చు: ₹{total_cost}"
            else:
                message = f"షాపింగ్ జాబితా సిద్ధంగా ఉంది! మొత్తం అంచనా ఖర్చు: ₹{total_cost}"
        else:
            if item_count == 0:
                message = "You have all the ingredients! No shopping needed."
            elif item_count == 1:
                message = f"Shopping list ready! Total estimated cost: ₹{total_cost}"
            else:
                message = f"Shopping list ready! Total estimated cost: ₹{total_cost}"
        
        logger.info(
            f"Shopping list generation successful: session_id={session_id}, "
            f"recipe_id={recipe_id}, items={item_count}, total_cost={total_cost}, "
            f"reminders={len(reminders)}"
        )
        
        # Return Shopping List JSON with reminders
        return create_response(
            status_code=200,
            body={
                'session_id': session_id,
                'shopping_list': shopping_list,
                'message': message,
                'reminders': reminders,
                'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
            },
            rate_limit_session_id=session_id,
            rate_limit_endpoint='/generate-shopping-list'
        )
    
    except ValueError as e:
        logger.warning(f"Validation error in handle_generate_shopping_list: {str(e)}")
        return create_response(
            status_code=validation_error_status_code(e),
            body={
                'error': 'validation_error',
                'message': str(e)
            }
        )
    
    except Exception as e:
        logger.error(f"Error in handle_generate_shopping_list: {str(e)}", exc_info=True)
        return create_response(
            status_code=500,
            body={
                'error': 'shopping_list_generation_failed',
                'message': 'Failed to generate shopping list. Please try again.'
            }
        )


def handle_create_session(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST /session endpoint.
    
    Creates a new session with optional language parameter.
    Generates unique session_id, creates session record in DynamoDB,
    sets expiry_timestamp to 7 days from creation.
    
    Requirements: 16.1, 16.3
    
    Args:
        event: API Gateway event
    
    Returns:
        API Gateway response with session_id and timestamps
    """
    try:
        auth_context, auth_error = get_auth_context(event)
        if auth_error:
            return auth_error

        # Parse request body
        body = parse_request_body(event)
        
        # Extract optional language parameter (default: 'en')
        language = body.get('language', 'en')
        
        # Validate language parameter
        if language not in ['en', 'te']:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_language',
                    'message': 'Language must be either "en" or "te"'
                }
            )
        
        logger.info(f"Creating new session with language={language}")
        
        # Requirement 16.1: Generate unique session_id
        # Requirement 16.3: Create session record in DynamoDB with 7-day expiry
        session_id = kitchen_agent.create_session(
            language=language,
            owner_sub=auth_context.sub,
            owner_email=auth_context.email
        )
        
        # Retrieve the created session to get timestamps
        session_data = kitchen_agent.get_session(session_id)
        
        if not session_data:
            logger.error(f"Failed to retrieve newly created session: {session_id}")
            return create_response(
                status_code=500,
                body={
                    'error': 'session_creation_failed',
                    'message': 'Failed to create session. Please try again.'
                }
            )
        
        # Calculate expires_at from expiry_timestamp
        created_at = session_data.get('created_at')
        expiry_timestamp = session_data.get('expiry_timestamp')
        
        # Convert Unix timestamp to ISO 8601
        # Handle Decimal from DynamoDB
        from datetime import datetime
        from decimal import Decimal
        if isinstance(expiry_timestamp, Decimal):
            expiry_timestamp = int(expiry_timestamp)
        expires_at = (
            datetime.fromtimestamp(expiry_timestamp, timezone.utc)
            .replace(tzinfo=None)
            .isoformat() + 'Z'
        )
        
        logger.info(
            f"Session created successfully: session_id={session_id}, "
            f"language={language}, expires_at={expires_at}"
        )
        
        # Return session_id and timestamps
        return create_response(
            status_code=201,
            body={
                'session_id': session_id,
                'created_at': created_at + 'Z' if not created_at.endswith('Z') else created_at,
                'expires_at': expires_at
            }
        )
    
    except Exception as e:
        logger.error(f"Error in handle_create_session: {str(e)}", exc_info=True)
        return create_response(
            status_code=500,
            body={
                'error': 'session_creation_failed',
                'message': 'Failed to create session. Please try again.'
            }
        )


def handle_get_session(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle GET /session/{session_id} endpoint.
    
    Retrieves session data from DynamoDB including user_language,
    preferences, allergies, and conversation_history.
    
    Requirements: 16.2, 16.5
    
    Args:
        event: API Gateway event
    
    Returns:
        API Gateway response with session profile data
    """
    try:
        auth_context, auth_error = get_auth_context(event)
        if auth_error:
            return auth_error

        # Extract session_id from path
        path = event.get('path', '')
        
        # Parse session_id from path: /session/{session_id}
        path_parts = path.split('/')
        if len(path_parts) < 3:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_request',
                    'message': 'Missing session_id in path'
                }
            )
        
        session_id = path_parts[2]
        
        if not session_id:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_request',
                    'message': 'Missing session_id in path'
                }
            )
        
        session_id, session_data, session_error = load_owned_session(session_id, auth_context)
        if session_error:
            return session_error

        logger.info(f"Retrieving session data: session_id={session_id}")
        
        # Requirement 16.5: Return user_language, preferences, allergies, conversation_history
        response_body = {
            'session_id': session_id,
            'user_language': session_data.get('user_language', 'en'),
            'preferences': session_data.get('preferences', {}),
            'allergies': session_data.get('allergies', []),
            'conversation_history': session_data.get('conversation_history', []),
            'created_at': session_data.get('created_at'),
            'updated_at': session_data.get('updated_at')
        }
        
        # Include last_inventory if present
        if 'last_inventory' in session_data:
            response_body['last_inventory'] = session_data['last_inventory']
        
        logger.info(
            f"Session data retrieved successfully: session_id={session_id}, "
            f"language={response_body['user_language']}"
        )
        
        return create_response(
            status_code=200,
            body=response_body
        )
    
    except Exception as e:
        logger.error(f"Error in handle_get_session: {str(e)}", exc_info=True)
        return create_response(
            status_code=500,
            body={
                'error': 'session_retrieval_failed',
                'message': 'Failed to retrieve session. Please try again.'
            }
        )


def handle_get_reminders(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle GET /reminders/{session_id} endpoint.
    
    Query kitchen-agent-reminders table by session_id.
    Filter by status='pending' or status='delivered'.
    Return list of reminders.
    
    Requirements: 11.3, 11.7
    
    Args:
        event: API Gateway event
    
    Returns:
        API Gateway response with list of reminders
    """
    try:
        auth_context, auth_error = get_auth_context(event)
        if auth_error:
            return auth_error

        # Extract session_id from path
        path = event.get('path', '')
        
        # Parse session_id from path: /reminders/{session_id}
        path_parts = path.split('/')
        if len(path_parts) < 3:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_request',
                    'message': 'Missing session_id in path'
                }
            )
        
        session_id = path_parts[2]
        
        if not session_id:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_request',
                    'message': 'Missing session_id in path'
                }
            )
        
        session_id, _, session_error = load_owned_session(session_id, auth_context)
        if session_error:
            return session_error

        logger.info(f"Retrieving reminders: session_id={session_id}")
        
        # Requirement 11.3: Query reminders by session_id with status filter
        try:
            reminders = reminder_service.get_pending_reminders(session_id)
        except Exception as e:
            logger.error(
                f"Failed to retrieve reminders: session_id={session_id}, "
                f"error={str(e)}"
            )
            return create_response(
                status_code=500,
                body={
                    'error': 'reminder_retrieval_failed',
                    'message': 'Failed to retrieve reminders. Please try again.',
                    'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
                }
            )
        
        # Convert reminders to response format
        reminder_list = []
        for reminder in reminders:
            reminder_list.append({
                'reminder_id': reminder.get('reminder_id'),
                'content': reminder.get('content'),
                'reason': reminder.get('reason'),
                'trigger_time': reminder.get('trigger_time'),
                'status': reminder.get('status'),
                'reminder_type': reminder.get('reminder_type', 'shopping'),
                'created_at': reminder.get('created_at')
            })
        
        logger.info(
            f"Reminders retrieved successfully: session_id={session_id}, "
            f"count={len(reminder_list)}"
        )
        
        return create_response(
            status_code=200,
            body={
                'session_id': session_id,
                'reminders': reminder_list,
                'count': len(reminder_list),
                'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
            }
        )
    
    except Exception as e:
        logger.error(f"Error in handle_get_reminders: {str(e)}", exc_info=True)
        return create_response(
            status_code=500,
            body={
                'error': 'reminder_retrieval_failed',
                'message': 'Failed to retrieve reminders. Please try again.'
            }
        )


def handle_dismiss_reminder(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST /reminders/{reminder_id}/dismiss endpoint.
    
    Update reminder status to 'dismissed'.
    Return updated reminder.
    
    Requirements: 11.6
    
    Args:
        event: API Gateway event
    
    Returns:
        API Gateway response with updated reminder
    """
    try:
        auth_context, auth_error = get_auth_context(event)
        if auth_error:
            return auth_error

        # Extract reminder_id from path
        path = event.get('path', '')
        
        # Parse reminder_id from path: /reminders/{reminder_id}/dismiss
        path_parts = path.split('/')
        if len(path_parts) < 3:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_request',
                    'message': 'Missing reminder_id in path'
                }
            )
        
        reminder_id = path_parts[2]
        
        if not reminder_id:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_request',
                    'message': 'Missing reminder_id in path'
                }
            )
        
        # Parse request body to get session_id
        body = parse_request_body(event)
        session_id = body.get('session_id')
        
        if not session_id:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_request',
                    'message': 'Missing required field: session_id'
                }
            )
        
        session_id, _, session_error = load_owned_session(session_id, auth_context)
        if session_error:
            return session_error

        logger.info(
            f"Dismissing reminder: session_id={session_id}, "
            f"reminder_id={reminder_id}"
        )
        
        # Requirement 11.6: Update reminder status to 'dismissed'
        try:
            updated_reminder = reminder_service.dismiss_reminder(
                reminder_id=reminder_id,
                session_id=session_id
            )
        except ValueError as e:
            logger.warning(
                f"Reminder not found: session_id={session_id}, "
                f"reminder_id={reminder_id}"
            )
            return create_response(
                status_code=404,
                body={
                    'error': 'reminder_not_found',
                    'message': f'Reminder not found: {reminder_id}'
                }
            )
        except Exception as e:
            logger.error(
                f"Failed to dismiss reminder: session_id={session_id}, "
                f"reminder_id={reminder_id}, error={str(e)}"
            )
            return create_response(
                status_code=500,
                body={
                    'error': 'reminder_dismiss_failed',
                    'message': 'Failed to dismiss reminder. Please try again.',
                    'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
                }
            )
        
        # Format response
        response_reminder = {
            'reminder_id': updated_reminder.get('reminder_id'),
            'content': updated_reminder.get('content'),
            'reason': updated_reminder.get('reason'),
            'trigger_time': updated_reminder.get('trigger_time'),
            'status': updated_reminder.get('status'),
            'reminder_type': updated_reminder.get('reminder_type', 'shopping'),
            'created_at': updated_reminder.get('created_at'),
            'updated_at': updated_reminder.get('updated_at')
        }
        
        logger.info(
            f"Reminder dismissed successfully: session_id={session_id}, "
            f"reminder_id={reminder_id}"
        )
        
        return create_response(
            status_code=200,
            body={
                'session_id': session_id,
                'reminder': response_reminder,
                'message': 'Reminder dismissed successfully',
                'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
            }
        )
    
    except Exception as e:
        logger.error(f"Error in handle_dismiss_reminder: {str(e)}", exc_info=True)
        return create_response(
            status_code=500,
            body={
                'error': 'reminder_dismiss_failed',
                'message': 'Failed to dismiss reminder. Please try again.'
            }
        )


def handle_snooze_reminder(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST /reminders/{reminder_id}/snooze endpoint.
    
    Accept duration_hours parameter.
    Update trigger_time by adding duration.
    Update EventBridge rule with new time.
    Return updated reminder.
    
    Requirements: 11.6
    
    Args:
        event: API Gateway event
    
    Returns:
        API Gateway response with updated reminder
    """
    try:
        auth_context, auth_error = get_auth_context(event)
        if auth_error:
            return auth_error

        # Extract reminder_id from path
        path = event.get('path', '')
        
        # Parse reminder_id from path: /reminders/{reminder_id}/snooze
        path_parts = path.split('/')
        if len(path_parts) < 3:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_request',
                    'message': 'Missing reminder_id in path'
                }
            )
        
        reminder_id = path_parts[2]
        
        if not reminder_id:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_request',
                    'message': 'Missing reminder_id in path'
                }
            )
        
        # Parse request body to get session_id and duration_hours
        body = parse_request_body(event)
        session_id = body.get('session_id')
        duration_hours = body.get('duration_hours')
        
        if not session_id:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_request',
                    'message': 'Missing required field: session_id'
                }
            )
        
        if duration_hours is None:
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_request',
                    'message': 'Missing required field: duration_hours'
                }
            )
        
        # Validate duration_hours is a positive number
        try:
            duration_hours = validate_duration_hours(duration_hours)
        except (ValueError, TypeError):
            return create_response(
                status_code=400,
                body={
                    'error': 'invalid_duration',
                    'message': 'duration_hours must be between 0.1 and 168 hours'
                }
            )
        
        session_id, _, session_error = load_owned_session(session_id, auth_context)
        if session_error:
            return session_error

        logger.info(
            f"Snoozing reminder: session_id={session_id}, "
            f"reminder_id={reminder_id}, duration_hours={duration_hours}"
        )
        
        # Requirement 11.6: Snooze reminder by updating trigger_time and EventBridge rule
        try:
            from datetime import timedelta
            duration = timedelta(hours=duration_hours)
            
            updated_reminder = reminder_service.snooze_reminder(
                reminder_id=reminder_id,
                session_id=session_id,
                duration=duration
            )
        except ValueError as e:
            logger.warning(
                f"Reminder not found: session_id={session_id}, "
                f"reminder_id={reminder_id}"
            )
            return create_response(
                status_code=404,
                body={
                    'error': 'reminder_not_found',
                    'message': f'Reminder not found: {reminder_id}'
                }
            )
        except Exception as e:
            logger.error(
                f"Failed to snooze reminder: session_id={session_id}, "
                f"reminder_id={reminder_id}, error={str(e)}"
            )
            return create_response(
                status_code=500,
                body={
                    'error': 'reminder_snooze_failed',
                    'message': 'Failed to snooze reminder. Please try again.',
                    'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
                }
            )
        
        # Format response
        response_reminder = {
            'reminder_id': updated_reminder.get('reminder_id'),
            'content': updated_reminder.get('content'),
            'reason': updated_reminder.get('reason'),
            'trigger_time': updated_reminder.get('trigger_time'),
            'status': updated_reminder.get('status'),
            'reminder_type': updated_reminder.get('reminder_type', 'shopping'),
            'created_at': updated_reminder.get('created_at'),
            'updated_at': updated_reminder.get('updated_at')
        }
        
        logger.info(
            f"Reminder snoozed successfully: session_id={session_id}, "
            f"reminder_id={reminder_id}, new_trigger_time={response_reminder['trigger_time']}"
        )
        
        return create_response(
            status_code=200,
            body={
                'session_id': session_id,
                'reminder': response_reminder,
                'message': f'Reminder snoozed for {duration_hours} hours',
                'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
            }
        )
    
    except Exception as e:
        logger.error(f"Error in handle_snooze_reminder: {str(e)}", exc_info=True)
        return create_response(
            status_code=500,
            body={
                'error': 'reminder_snooze_failed',
                'message': 'Failed to snooze reminder. Please try again.'
            }
        )


def parse_request_body(
    event: Dict[str, Any],
    max_size_bytes: int = MAX_JSON_REQUEST_SIZE_BYTES
) -> Dict[str, Any]:
    """
    Parse request body from API Gateway event.
    
    Args:
        event: API Gateway event
    
    Returns:
        Parsed body as dictionary
    """
    ensure_request_size_limit(event, max_size_bytes)
    body = event.get('body', '')
    
    if not body:
        return {}
    
    # Handle base64 encoded body
    if event.get('isBase64Encoded', False):
        body = base64.b64decode(body).decode('utf-8')
    
    # Try to parse as JSON
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        # For multipart/form-data, return empty dict
        # (will be parsed separately)
        return {}


def check_rate_limit_for_request(
    session_id: str,
    endpoint: str
) -> Optional[Dict[str, Any]]:
    """
    Check rate limit for a request and return error response if exceeded.
    
    Args:
        session_id: Session identifier
        endpoint: API endpoint path
    
    Returns:
        Error response dict if rate limit exceeded, None if allowed
    """
    return enforce_rate_limit(session_id, endpoint)


def parse_multipart_image(event: Dict[str, Any]) -> tuple[Optional[bytes], Optional[str]]:
    """
    Parse image data from multipart/form-data request.
    
    This is a simplified parser for demonstration.
    In production, use a proper multipart parser library.
    
    Args:
        event: API Gateway event
    
    Returns:
        Tuple of (image_data, content_type)
    """
    fields, files = parse_multipart_form(event)
    _ = fields  # preserve signature compatibility for callers that only need the file
    file_part = files.get('file') or next(iter(files.values()), None)
    if not file_part:
        return None, None
    return file_part['content'], file_part.get('content_type')


def create_response(
    status_code: int,
    body: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    rate_limit_session_id: Optional[str] = None,
    rate_limit_endpoint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create API Gateway response with security headers.
    
    Args:
        status_code: HTTP status code
        body: Response body dictionary
        headers: Optional additional headers
    
    Returns:
        API Gateway response dictionary with security headers
    """
    # Get allowed origin dynamically from os.environ (not cached Config class)
    import os
    allowed_origin = os.environ.get("ALLOWED_ORIGIN") or (Config.ALLOWED_ORIGIN if hasattr(Config, 'ALLOWED_ORIGIN') else None)
    if not allowed_origin and os.environ.get("ENVIRONMENT", Config.ENVIRONMENT) != "prod":
        # WARNING: Falling back to localhost CORS is for local/test environments only.
        # Secure alternative for deployed environments: set ALLOWED_ORIGIN explicitly.
        allowed_origin = "http://localhost:8501"
    
    # Create secure headers using security_utils
    secure_headers = create_secure_response_headers(allowed_origin)
    
    # Add CORS headers - ALLOWED_ORIGIN must be set explicitly in all environments.
    # WARNING: Wildcard CORS (Access-Control-Allow-Origin: *) allows any site to call
    # this API. Secure alternative: set ALLOWED_ORIGIN to your specific frontend domain.
    if not allowed_origin:
        raise ValueError(
            "ALLOWED_ORIGIN is not configured. Set it to your frontend domain "
            "(e.g. https://your-app.example.com) to prevent cross-origin abuse."
        )
    
    # Merge with any additional headers
    if headers:
        secure_headers.update(headers)

    rate_limit_headers = get_rate_limit_headers(rate_limit_session_id, rate_limit_endpoint)
    for key, value in rate_limit_headers.items():
        secure_headers.setdefault(key, value)
    
    return {
        'statusCode': status_code,
        'headers': secure_headers,
        'body': json.dumps(body)
    }
