"""
Security Utilities for Andhra Kitchen Agent

Provides input validation, sanitization, and security helper functions.
"""

import os
import re
from typing import Optional, Any, Dict
import logging

logger = logging.getLogger(__name__)


DEFAULT_RESERVED_SESSION_KEYWORDS = {
    keyword.strip().lower()
    for keyword in os.getenv(
        "SESSION_ID_RESERVED_KEYWORDS",
        "admin,root,system,config,superuser,support,ops"
    ).split(",")
    if keyword.strip()
}


def _strict_session_validation_enabled() -> bool:
    return os.getenv("SESSION_ID_STRICT_VALIDATION", "true").lower() == "true"


def _input_validation_strict_enabled() -> bool:
    return os.getenv("INPUT_VALIDATION_STRICT", "true").lower() == "true"


def _max_whitespace_ratio() -> float:
    try:
        return float(os.getenv("MAX_WHITESPACE_RATIO", "0.5"))
    except ValueError:
        return 0.5


def _is_sensitive_field(field_name: str) -> bool:
    field_name = field_name.lower()
    sensitive_markers = {
        'allergies',
        'preferences',
        'email',
        'phone',
        'password',
        'token',
        'api_key',
        'apikey',
        'secret',
        'authorization',
        'conversation_history',
        'id_token',
        'access_token',
        'refresh_token',
    }
    return any(marker in field_name for marker in sensitive_markers)


def validate_session_id(session_id: str) -> str:
    """
    Validate session ID format.
    
    Args:
        session_id: Session identifier to validate
    
    Returns:
        Validated session_id
    
    Raises:
        ValueError: If session_id format is invalid
    """
    if not session_id:
        raise ValueError("session_id is required")

    if _strict_session_validation_enabled():
        lowered = session_id.lower()
        dangerous_fragments = ('..', './', '.\\', '//', '\\\\')
        if any(fragment in session_id for fragment in dangerous_fragments):
            logger.warning(f"Rejected session_id with path traversal pattern: {session_id}")
            raise ValueError("Invalid session_id: path traversal patterns are not allowed")

        if session_id.startswith('/') or re.match(r'^[a-zA-Z]:[\\/]', session_id):
            logger.warning(f"Rejected session_id with absolute path pattern: {session_id}")
            raise ValueError("Invalid session_id: absolute path patterns are not allowed")
    
    # Only allow alphanumeric, underscores, and hyphens, max 64 chars
    if not re.match(r'^[a-zA-Z0-9_-]{1,64}$', session_id):
        raise ValueError(
            "Invalid session_id format. Must be alphanumeric with underscores/hyphens, max 64 characters"
        )

    if _strict_session_validation_enabled():
        segments = [segment for segment in re.split(r'[_-]+', lowered) if segment]
        if lowered in DEFAULT_RESERVED_SESSION_KEYWORDS or any(
            segment in DEFAULT_RESERVED_SESSION_KEYWORDS for segment in segments
        ):
            logger.warning(f"Rejected reserved session_id: {session_id}")
            raise ValueError("Invalid session_id: reserved keywords are not allowed")
    
    return session_id


def validate_language(language: str) -> str:
    """
    Validate language parameter.
    
    Args:
        language: Language code to validate
    
    Returns:
        Validated language code
    
    Raises:
        ValueError: If language is invalid
    """
    ALLOWED_LANGUAGES = ['en', 'te']
    
    if language not in ALLOWED_LANGUAGES:
        raise ValueError(f"Invalid language. Must be one of: {', '.join(ALLOWED_LANGUAGES)}")
    
    return language


def sanitize_user_input(text: str, max_length: int = 5000) -> str:
    """
    Sanitize user text input.
    
    Args:
        text: User input text
        max_length: Maximum allowed length
    
    Returns:
        Sanitized text
    
    Raises:
        ValueError: If text is invalid
    """
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    
    # Remove null bytes
    text = text.replace('\x00', '')

    if _input_validation_strict_enabled():
        whitespace_ratio = sum(1 for char in text if char.isspace()) / max(len(text), 1)
        if whitespace_ratio > _max_whitespace_ratio():
            logger.warning("Rejected input with excessive whitespace ratio")
            raise ValueError("Input contains excessive whitespace")

        lowered = text.lower()
        malicious_patterns = {
            "SQL injection": [
                r"\bunion\s+select\b",
                r"\bdrop\s+table\b",
                r"\binsert\s+into\b",
                r"\bdelete\s+from\b",
                r"\bupdate\s+\w+\s+set\b",
                r"\balter\s+table\b",
                r"\bsleep\s*\(",
                r"\bbenchmark\s*\(",
            ],
            "XSS": [
                r"<\s*script\b",
                r"javascript\s*:",
                r"<\s*iframe\b",
                r"on\w+\s*=",
            ],
            "command injection": [
                r"(?:^|[\s;&|`])(?:cat|curl|wget|bash|sh|powershell|cmd|rm|ls)\b",
                r"\$\(",
                r"`[^`]+`",
                r"/etc/passwd",
            ],
        }

        for attack_type, patterns in malicious_patterns.items():
            if any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in patterns):
                logger.warning(f"Rejected user input containing {attack_type.lower()} pattern")
                raise ValueError(f"Input contains disallowed {attack_type.lower()} patterns")
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length]
    
    # Remove control characters except newlines, tabs, and carriage returns
    text = ''.join(
        char for char in text 
        if char.isprintable() or char in '\n\t\r'
    )

    # Normalize whitespace in otherwise valid input.
    text = re.sub(r'[ \t\r\f\v]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def validate_duration_hours(hours: float) -> float:
    """
    Validate reminder duration.
    
    Args:
        hours: Duration in hours
    
    Returns:
        Validated duration
    
    Raises:
        ValueError: If duration is invalid
    """
    try:
        hours = float(hours)
    except (ValueError, TypeError):
        raise ValueError("duration_hours must be a number")
    
    # Min 6 minutes (0.1 hours), max 1 week (168 hours)
    if not 0.1 <= hours <= 168:
        raise ValueError("Duration must be between 0.1 and 168 hours (1 week)")
    
    return hours


def validate_recipe_count(count: int) -> int:
    """
    Validate recipe count parameter.
    
    Args:
        count: Number of recipes to generate
    
    Returns:
        Validated count
    
    Raises:
        ValueError: If count is invalid
    """
    try:
        count = int(count)
    except (ValueError, TypeError):
        raise ValueError("count must be an integer")
    
    if not 1 <= count <= 10:
        raise ValueError("Recipe count must be between 1 and 10")
    
    return count


def validate_dynamodb_key(key: str, key_name: str = "key") -> str:
    """
    Validate DynamoDB key format to prevent injection.
    
    Args:
        key: Key value to validate
        key_name: Name of the key (for error messages)
    
    Returns:
        Validated key
    
    Raises:
        ValueError: If key format is invalid
    """
    if not key:
        raise ValueError(f"{key_name} is required")
    
    # Allow alphanumeric, underscores, hyphens, max 255 chars
    if not re.match(r'^[a-zA-Z0-9_-]{1,255}$', key):
        raise ValueError(
            f"Invalid {key_name} format. Must be alphanumeric with underscores/hyphens, max 255 characters"
        )
    
    return key


def sanitize_for_logging(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove sensitive fields from log data.
    
    Args:
        data: Dictionary to sanitize
    
    Returns:
        Sanitized dictionary with sensitive fields redacted
    """
    if isinstance(data, tuple):
        return tuple(sanitize_for_logging(item) for item in data)

    if isinstance(data, list):
        return [sanitize_for_logging(item) for item in data]

    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    for key, value in data.items():
        if _is_sensitive_field(key):
            sanitized[key] = '[REDACTED]'
        elif isinstance(value, dict):
            sanitized[key] = sanitize_for_logging(value)
        elif isinstance(value, (list, tuple)):
            sanitized[key] = sanitize_for_logging(value)
        else:
            sanitized[key] = value
    
    return sanitized


def validate_image_filename(filename: str) -> str:
    """
    Validate and sanitize image filename.
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    
    Raises:
        ValueError: If filename is invalid
    """
    if not filename:
        raise ValueError("Filename is required")
    
    # Extract extension
    parts = filename.lower().split('.')
    if len(parts) < 2:
        raise ValueError("Filename must have an extension")
    
    ext = parts[-1]
    ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'heic']
    
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Invalid file extension: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Sanitize filename - remove special characters
    safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    # Prevent path traversal
    if '..' in safe_filename or '/' in safe_filename or '\\' in safe_filename:
        raise ValueError("Invalid filename: path traversal detected")
    
    return safe_filename


def validate_image_data(image_data: bytes, max_size_mb: int = 10) -> str:
    """
    Validate image data with enhanced security checks.
    
    Args:
        image_data: Binary image data
        max_size_mb: Maximum allowed size in MB
    
    Returns:
        Canonical MIME type if valid
    
    Raises:
        ValueError: If image data is invalid
    """
    if not image_data:
        raise ValueError("Image data is required")
    
    # Check size
    max_size_bytes = max_size_mb * 1024 * 1024
    if len(image_data) > max_size_bytes:
        raise ValueError(
            f"Image size ({len(image_data) / 1024 / 1024:.2f}MB) exceeds "
            f"maximum allowed size ({max_size_mb}MB)"
        )
    
    # Check for null bytes (potential exploit)
    if b'\x00' * 100 in image_data:
        raise ValueError("Invalid image data: suspicious null byte sequence detected")
    
    # SECURITY: Validate MIME type using magic bytes (file signature)
    # This prevents file type spoofing via extension manipulation
    try:
        # Check magic bytes for common image formats
        if image_data.startswith(b'\xff\xd8\xff'):
            # JPEG magic bytes
            mime_type = 'image/jpeg'
        elif image_data.startswith(b'\x89PNG\r\n\x1a\n'):
            # PNG magic bytes
            mime_type = 'image/png'
        elif image_data[4:12] in {
            b'ftypheic',
            b'ftypheix',
            b'ftyphevc',
            b'ftypheim',
            b'ftypmif1',
            b'ftypmsf1'
        }:
            # HEIC magic bytes (at offset 4)
            mime_type = 'image/heic'
        else:
            raise ValueError("Unsupported or invalid image format")
        
        logger.info(f"Detected image MIME type from magic bytes: {mime_type}")
        
    except Exception as e:
        logger.error(f"Failed to validate image magic bytes: {str(e)}")
        raise ValueError(f"Invalid image format: {str(e)}")
    
    return mime_type


def validate_image_with_pil(image_data: bytes) -> bool:
    """
    Validate image can be opened with PIL (optional enhanced validation).
    
    WARNING: This requires Pillow library: pip install Pillow
    Only use if Pillow is installed in your environment.
    
    Args:
        image_data: Binary image data
    
    Returns:
        True if valid
    
    Raises:
        ValueError: If image cannot be opened
        ImportError: If Pillow is not installed
    """
    try:
        from PIL import Image
        import io
        
        # Try to open and verify image
        img = Image.open(io.BytesIO(image_data))
        img.verify()
        
        logger.info(f"PIL validation passed: format={img.format}, size={img.size}")
        return True
        
    except ImportError:
        logger.warning("Pillow not installed - skipping PIL validation")
        raise ImportError("Pillow library required for enhanced image validation")
    
    except Exception as e:
        logger.error(f"PIL validation failed: {str(e)}")
        raise ValueError(f"Invalid image file: {str(e)}")


def create_secure_response_headers(allowed_origin: Optional[str] = None) -> Dict[str, str]:
    """
    Create secure HTTP response headers.
    
    Args:
        allowed_origin: Specific origin to allow (None = no CORS)
    
    Returns:
        Dictionary of security headers
    """
    allow_inline_styles = os.getenv("CSP_ALLOW_INLINE_STYLES", "true").lower() == "true"
    csp_report_uri = os.getenv("CSP_REPORT_URI", "").strip()
    strict_csp = os.getenv("CSP_STRICT_MODE", "true").lower() == "true"

    style_src = "style-src 'self' 'unsafe-inline'" if allow_inline_styles else "style-src 'self'"
    csp_directives = [
        "default-src 'self'",
        "base-uri 'self'",
        "frame-ancestors 'none'",
        "form-action 'self'",
        "object-src 'none'",
        "img-src 'self' data: https:",
        "connect-src 'self' https:",
        "script-src 'self'",
        style_src,
    ]
    if strict_csp:
        csp_directives.append("upgrade-insecure-requests")
    if csp_report_uri:
        csp_directives.append(f"report-uri {csp_report_uri}")

    headers = {
        'Content-Type': 'application/json',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': '; '.join(csp_directives),
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Vary': 'Origin'
    }
    
    # Add CORS header if origin specified
    if allowed_origin:
        headers['Access-Control-Allow-Origin'] = allowed_origin
    
    return headers


if __name__ == "__main__":
    # Test validation functions
    print("Security Utils - Validation Tests")
    print("=" * 50)
    
    # Test session ID validation
    try:
        validate_session_id("sess_abc123")
        print("✓ Valid session_id accepted")
    except ValueError as e:
        print(f"✗ Valid session_id rejected: {e}")
    
    try:
        validate_session_id("sess_abc'; DROP TABLE--")
        print("✗ Invalid session_id accepted (SQL injection)")
    except ValueError:
        print("✓ Invalid session_id rejected (SQL injection)")
    
    # Test input sanitization
    dirty_input = "Hello\x00World\x01Test"
    clean_input = sanitize_user_input(dirty_input)
    print(f"✓ Sanitized input: '{clean_input}'")
    
    # Test log sanitization
    sensitive_data = {
        'session_id': 'sess_123',
        'allergies': ['peanuts', 'shellfish'],
        'preferences': {'low_oil': True}
    }
    sanitized = sanitize_for_logging(sensitive_data)
    print(f"✓ Sanitized logs: {sanitized}")
    
    print("=" * 50)
