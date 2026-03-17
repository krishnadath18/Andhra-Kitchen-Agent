# Security Vulnerabilities Audit Fixes - Bugfix Design

## Overview

This design document provides comprehensive technical solutions for 12 security vulnerabilities identified in the Andhra Kitchen Agent codebase. The vulnerabilities span critical security domains including rate limiting, CORS configuration, input validation, session management, error handling, and logging. The fixes implement defense-in-depth security principles with fail-closed defaults, comprehensive input validation, and secure error handling. All fixes are designed to maintain backward compatibility while significantly improving the security posture of the application.

## Glossary

- **Bug_Condition (C)**: The condition that triggers each security vulnerability
- **Property (P)**: The desired secure behavior after implementing the fix
- **Preservation**: Existing functionality that must remain unchanged by security fixes
- **Fail-Closed**: Security pattern where errors result in denying access rather than allowing it
- **Fail-Open**: Insecure pattern where errors result in allowing access (current vulnerable state)
- **CORS (Cross-Origin Resource Sharing)**: HTTP header-based mechanism controlling cross-origin requests
- **CSP (Content Security Policy)**: HTTP header that prevents XSS attacks by controlling resource loading
- **PII (Personally Identifiable Information)**: Sensitive user data requiring protection in logs
- **Path Traversal**: Attack technique using special characters (../) to access unauthorized files
- **Rate Limiting**: Mechanism to control request frequency and prevent DoS attacks
- **DynamoDB**: AWS NoSQL database service used for rate limiting and session storage
- **S3**: AWS object storage service used for image uploads
- **Bedrock**: AWS AI service used for chat and recipe generation
- **Cognito**: AWS authentication service managing user identities


## Bug Details

### CRITICAL SEVERITY BUGS

#### Bug 1: Rate Limiter Fail-Open Behavior

**Current Vulnerable Behavior:**
The rate limiter in `src/rate_limiter.py` (lines 140-191) fails open when DynamoDB errors occur in production. When the rate limit table is unavailable or exceptions are raised, the system allows requests through, enabling unlimited API access and potential DoS attacks.

**Bug Condition:**
```
FUNCTION isBugCondition_RateLimiter(X)
  INPUT: X of type RateLimitRequest
  OUTPUT: boolean
  
  RETURN (X.environment = "prod") AND 
         (X.dynamodb_error = true OR X.exception_occurred = true)
END FUNCTION
```

**Examples:**
- Attacker triggers DynamoDB throttling by overwhelming the rate limit table → All requests allowed
- Network partition isolates application from DynamoDB → All requests allowed
- DynamoDB credentials expire → All requests allowed
- Malicious actor intentionally corrupts rate limit data → All requests allowed


#### Bug 2: CORS Wildcard Configuration Not Enforced

**Current Vulnerable Behavior:**
The CORS configuration in `config/env.py` (lines 95-115) only logs a warning when ALLOWED_ORIGIN="*" in production but allows the application to start. This permits any origin to access the API, enabling cross-origin attacks, token theft, and unauthorized data access.

**Bug Condition:**
```
FUNCTION isBugCondition_CORS(X)
  INPUT: X of type CORSConfig
  OUTPUT: boolean
  
  RETURN (X.environment = "prod") AND 
         (X.allowed_origin = "*")
END FUNCTION
```

**Examples:**
- Production deployment with ALLOWED_ORIGIN="*" → Malicious website can steal user tokens
- Attacker hosts phishing site that makes cross-origin requests → User data compromised
- Configuration mistake in production → All origins allowed, security bypassed


### HIGH SEVERITY BUGS

#### Bug 3: Missing Input Validation in Chat Handler

**Current Vulnerable Behavior:**
The chat handler in `src/api_handler.py` (lines 250-280) only validates message length (5000 chars) but doesn't sanitize for injection patterns, script tags, or command injection attempts. The `sanitize_user_input` function in `src/security_utils.py` only removes control characters but doesn't detect malicious patterns.

**Bug Condition:**
```
FUNCTION isBugCondition_ChatInput(X)
  INPUT: X of type ChatMessage
  OUTPUT: boolean
  
  RETURN (contains_sql_injection(X.message) OR
          contains_script_tags(X.message) OR
          contains_command_injection(X.message) OR
          excessive_whitespace(X.message)) AND
         length(X.message) <= 5000
END FUNCTION
```

**Examples:**
- Message: `"'; DROP TABLE users; --" + " " * 4970` → Passes length check, SQL injection attempt
- Message: `"<script>alert('XSS')</script>"` → Script tag injection
- Message: `"; cat /etc/passwd #"` → Command injection attempt
- Message: `"test" + "\n" * 4000` → Excessive whitespace DoS


#### Bug 4: Insufficient Session ID Validation

**Current Vulnerable Behavior:**
The `validate_session_id` function in `src/security_utils.py` (lines 20-35) uses regex validation but doesn't check for path traversal patterns or reserved keywords. Session IDs like "user123--..-data" pass validation but could enable path traversal attacks.

**Bug Condition:**
```
FUNCTION isBugCondition_SessionID(X)
  INPUT: X of type SessionID
  OUTPUT: boolean
  
  RETURN matches_regex(X.value, '^[a-zA-Z0-9_-]{1,64}$') AND
         (contains(X.value, "..") OR
          X.value IN ["admin", "system", "root", "config"])
END FUNCTION
```

**Examples:**
- Session ID: `"user123--..-data"` → Contains ".." but passes regex
- Session ID: `"admin"` → Reserved keyword, security risk
- Session ID: `"..--..--etc"` → Path traversal pattern
- Session ID: `"system-config"` → Contains reserved keyword


#### Bug 5: Image Upload Cleanup Failure

**Current Vulnerable Behavior:**
The `upload_image_to_s3` function in `src/kitchen_agent_core.py` (lines 130-145) uploads to S3 first, then stores metadata in DynamoDB. If metadata storage fails, the cleanup logic may fail silently, leaving orphaned S3 objects that accumulate over time.

**Bug Condition:**
```
FUNCTION isBugCondition_ImageUpload(X)
  INPUT: X of type ImageUploadOperation
  OUTPUT: boolean
  
  RETURN (X.s3_upload_success = true) AND
         (X.dynamodb_metadata_storage_failed = true)
END FUNCTION
```

**Examples:**
- S3 upload succeeds, DynamoDB throttled → Orphaned S3 object
- S3 upload succeeds, DynamoDB credentials expired → Orphaned S3 object
- S3 upload succeeds, metadata validation fails → Orphaned S3 object
- Repeated failures → Storage exhaustion, increased costs

### MEDIUM SEVERITY BUGS

#### Bug 6: Nested PII in Logs

**Current Vulnerable Behavior:**
The `sanitize_for_logging` function in `src/security_utils.py` (lines 120-150) only redacts top-level sensitive fields but doesn't recursively traverse nested structures. PII in nested objects and arrays leaks to CloudWatch logs.

**Bug Condition:**
```
FUNCTION isBugCondition_Logging(X)
  INPUT: X of type LogData
  OUTPUT: boolean
  
  RETURN (X.field_name = "conversation_history") AND
         contains_nested_pii(X.value) AND
         only_top_level_redacted(X.sanitization)
END FUNCTION
```

**Examples:**
- Log: `{"conversation_history": [{"user": "My email is user@example.com"}]}` → Email leaked
- Log: `{"metadata": {"user_phone": "555-1234"}}` → Phone number leaked
- Log: `{"nested": {"deep": {"email": "test@example.com"}}}` → Deep PII leaked


#### Bug 7: Error Messages Expose Internal Details

**Current Vulnerable Behavior:**
Error handling throughout `src/api_handler.py` and `src/kitchen_agent_core.py` exposes implementation details like service names (DynamoDB, S3, Bedrock), regions, and stack traces in production error messages.

**Bug Condition:**
```
FUNCTION isBugCondition_ErrorMessages(X)
  INPUT: X of type ErrorResponse
  OUTPUT: boolean
  
  RETURN (X.environment = "prod") AND
         (contains(X.message, "DynamoDB") OR
          contains(X.message, "S3") OR
          contains(X.message, "Bedrock") OR
          contains_stack_trace(X.message))
END FUNCTION
```

**Examples:**
- Error: `"DynamoDB table 'users' unavailable in us-east-1"` → Exposes service and region
- Error: `"S3 bucket 'kitchen-images-prod' access denied"` → Exposes bucket name
- Error: `"Bedrock model anthropic.claude-3 throttled"` → Exposes model details

#### Bug 8: No Request Size Limits

**Current Vulnerable Behavior:**
The `parse_request_body` function in `src/api_handler.py` parses JSON without checking content-length first. Extremely large payloads (>1MB) can cause memory exhaustion and DoS.

**Bug Condition:**
```
FUNCTION isBugCondition_RequestSize(X)
  INPUT: X of type HTTPRequest
  OUTPUT: boolean
  
  RETURN (X.content_length > 1048576) AND
         no_size_check_before_parse(X)
END FUNCTION
```

**Examples:**
- Request with 10MB JSON payload → Memory exhaustion
- Request with 100MB payload → Service crash
- Repeated large requests → DoS attack


#### Bug 9: Missing HTTPS Enforcement

**Current Vulnerable Behavior:**
The `check_https_security` function in `app.py` (lines 30-50) only displays a warning when production is accessed over HTTP but doesn't redirect or refuse the connection. Tokens and session data are transmitted in plaintext.

**Bug Condition:**
```
FUNCTION isBugCondition_HTTPS(X)
  INPUT: X of type HTTPConnection
  OUTPUT: boolean
  
  RETURN (X.environment = "prod") AND
         (X.protocol = "http") AND
         (X.host != "localhost")
END FUNCTION
```

**Examples:**
- User accesses `http://app.example.com` → Warning shown but connection allowed
- Man-in-the-middle attack → Tokens intercepted
- Public WiFi access over HTTP → Session hijacking

### LOW SEVERITY BUGS

#### Bug 10: Weak Password Requirements UI

**Current Vulnerable Behavior:**
The password input in `app.py` (lines 550-580) has no client-side validation or strength meter. Users can attempt weak passwords without guidance, leading to poor user experience and potential account compromise.

**Bug Condition:**
```
FUNCTION isBugCondition_Password(X)
  INPUT: X of type PasswordInput
  OUTPUT: boolean
  
  RETURN (X.password_strength = "weak") AND
         no_client_side_validation(X) AND
         no_requirements_displayed(X)
END FUNCTION
```

**Examples:**
- User enters "123456" → No warning until server rejection
- User enters "password" → No strength feedback
- User doesn't know requirements → Multiple failed attempts


#### Bug 11: Permissive CSP Headers

**Current Vulnerable Behavior:**
The `create_secure_response_headers` function in `src/security_utils.py` (lines 230-250) sets CSP to `"default-src 'self'"` which may allow inline scripts, reducing XSS protection.

**Bug Condition:**
```
FUNCTION isBugCondition_CSP(X)
  INPUT: X of type SecurityHeaders
  OUTPUT: boolean
  
  RETURN (X.csp_policy = "default-src 'self'") AND
         allows_inline_scripts(X.csp_policy)
END FUNCTION
```

**Examples:**
- Inline script injection → CSP doesn't block
- XSS attack via inline event handlers → Not prevented
- Reduced defense-in-depth → Easier exploitation

#### Bug 12: Missing Rate Limit Headers on Success

**Current Vulnerable Behavior:**
The `enforce_rate_limit` function in `src/api_handler.py` (lines 130-160) only returns rate limit headers on 429 responses. Successful 200 responses don't include X-RateLimit-* headers, preventing clients from proactively managing rate limits.

**Bug Condition:**
```
FUNCTION isBugCondition_RateLimitHeaders(X)
  INPUT: X of type APIResponse
  OUTPUT: boolean
  
  RETURN (X.http_status = 200) AND
         (X.rate_limit_headers_present = false)
END FUNCTION
```

**Examples:**
- Client makes 49 requests → No warning before hitting limit
- Client can't implement exponential backoff → Poor API experience
- No visibility into remaining quota → Unexpected 429 errors


## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**

**Rate Limiting (Bugs 1, 12):**
- When DynamoDB is available and user is within limits → Continue to allow requests
- When DynamoDB is available and user exceeds limits → Continue to return HTTP 429
- Rate limit configuration per endpoint → Remain unchanged
- TTL-based window expiration → Continue to work as designed

**CORS Configuration (Bug 2):**
- When ALLOWED_ORIGIN is properly configured with specific domain → Continue to enforce CORS correctly
- When running in development with ALLOWED_ORIGIN="*" → Continue to allow permissive CORS for local testing
- CORS headers on OPTIONS requests → Continue to work

**Input Validation (Bugs 3, 4):**
- When valid chat messages under 5000 chars with no malicious content → Continue to process normally
- When valid session IDs (alphanumeric, hyphens, underscores, no traversal) → Continue to accept
- Existing validation for other fields → Remain unchanged

**Image Upload (Bug 5):**
- When S3 upload and metadata storage both succeed → Continue to return success
- When S3 upload fails initially → Continue to return error without metadata storage
- Image format validation → Continue to work
- Pre-signed URL generation → Continue to work

**Logging and Error Handling (Bugs 6, 7):**
- When logging non-sensitive data → Continue to log normally
- When errors occur in development → Continue to provide detailed messages for debugging
- CloudWatch log structure → Remain unchanged
- Error response format → Maintain compatibility

**Request Processing (Bug 8):**
- When clients send reasonably-sized requests (<1MB) → Continue to parse and process normally
- JSON parsing logic → Remain unchanged for valid requests
- Multipart form parsing → Continue to work

**HTTPS and Authentication (Bugs 9, 10):**
- When users access via HTTPS in production → Continue to serve securely
- When passwords meet Cognito requirements → Continue to accept and create accounts
- Cognito integration → Remain unchanged
- Token validation → Continue to work

**Security Headers (Bug 11):**
- When application serves content with proper headers → Continue to protect against attacks
- Other security headers (X-Frame-Options, etc.) → Remain unchanged
- CORS headers → Continue to work with Bug 2 fix

**Scope:**
All inputs and operations that do NOT trigger the bug conditions should be completely unaffected by these fixes. The fixes implement additional security checks without breaking existing valid use cases.


## Hypothesized Root Cause

### Critical Severity Root Causes

**Bug 1: Rate Limiter Fail-Open**
Root causes:
1. **Defensive Programming Prioritized Availability**: The original implementation assumed allowing requests during errors was safer than blocking them
2. **Lack of Security-First Design**: Error handling didn't consider DoS attack scenarios
3. **Insufficient Production Testing**: DynamoDB failure scenarios not tested in production-like environments
4. **Missing Fail-Closed Pattern**: No awareness of security best practice to deny by default

**Bug 2: CORS Wildcard Not Enforced**
Root causes:
1. **Separation of Validation and Enforcement**: Warning logged but no enforcement mechanism
2. **Configuration Flexibility Over Security**: Allowed wildcard for convenience without blocking deployment
3. **Missing Startup Validation**: No pre-flight checks to prevent insecure configurations
4. **Inadequate Security Review**: CORS security implications not fully understood

### High Severity Root Causes

**Bug 3: Missing Input Validation**
Root causes:
1. **Length-Only Validation**: Assumed length check was sufficient for security
2. **Trust in Downstream Processing**: Expected Bedrock to handle malicious input
3. **Incomplete Sanitization Function**: `sanitize_user_input` only removes control characters
4. **No Pattern Detection**: Missing regex patterns for common injection attacks

**Bug 4: Insufficient Session ID Validation**
Root causes:
1. **Format vs Security Validation**: Regex checked format but not semantic security
2. **Missing Path Traversal Checks**: Didn't consider file system security implications
3. **No Reserved Keyword List**: Didn't anticipate privilege escalation risks
4. **Incomplete Security Review**: Session ID usage in file paths not analyzed

**Bug 5: Image Upload Cleanup Failure**
Root causes:
1. **No Transactional Guarantees**: S3 and DynamoDB operations not atomic
2. **Silent Failure Handling**: Cleanup errors logged but not surfaced
3. **Optimistic Success Assumption**: Assumed metadata storage would succeed
4. **Missing Compensating Transaction**: No rollback mechanism for partial failures


### Medium Severity Root Causes

**Bug 6: Nested PII in Logs**
Root causes:
1. **Shallow Sanitization**: Only top-level field redaction implemented
2. **Complex Data Structures**: Conversation history contains nested objects
3. **Missing Recursive Traversal**: Sanitization function doesn't handle nested structures
4. **Incomplete PII Detection**: Doesn't scan for PII patterns in nested content

**Bug 7: Verbose Error Messages**
Root causes:
1. **Same Error Format for All Environments**: No environment-aware error abstraction
2. **Debugging Convenience**: Detailed errors helpful in development, exposed in production
3. **Missing Error Message Mapping**: No generic message layer for production
4. **Insufficient Security Awareness**: Information disclosure risks not considered

**Bug 8: No Request Size Limits**
Root causes:
1. **Per-Field Validation Only**: Size checked per field, not globally
2. **Parser Invoked Before Size Check**: JSON parsing happens before validation
3. **Missing Middleware**: No global request size enforcement layer
4. **DoS Scenarios Not Considered**: Memory exhaustion attacks not anticipated

**Bug 9: HTTPS Not Enforced**
Root causes:
1. **Warning vs Enforcement**: Security check only warns, doesn't block
2. **Streamlit Limitations**: Framework doesn't provide built-in HTTPS enforcement
3. **Deployment Assumption**: Assumed reverse proxy would handle HTTPS
4. **Missing Redirect Logic**: No automatic HTTP to HTTPS redirect

### Low Severity Root Causes

**Bug 10: No Password Strength UI**
Root causes:
1. **Server-Side Validation Only**: Relied solely on Cognito validation
2. **Poor User Experience**: No client-side guidance before submission
3. **Missing UI Components**: No strength meter or requirements display
4. **Backend-First Approach**: Didn't consider client-side UX improvements

**Bug 11: Permissive CSP**
Root causes:
1. **Generic CSP Policy**: Not tailored to application's actual needs
2. **Incomplete XSS Protection**: Didn't block inline scripts explicitly
3. **Default Security Headers**: Used basic CSP without hardening
4. **Missing Security Audit**: CSP effectiveness not tested

**Bug 12: Missing Rate Limit Headers**
Root causes:
1. **Error-Only Headers**: Headers only added on rate limit errors
2. **Not Treated as Standard Metadata**: Rate limit info not part of normal response
3. **Missing API Best Practices**: Standard rate limit headers not implemented
4. **Client Experience Not Considered**: Proactive rate limit management not supported


## Correctness Properties

Property 1: Bug Condition - Rate Limiter Fail-Closed in Production

_For any_ rate limit check where DynamoDB errors occur in production environment, the fixed rate limiter SHALL reject the request with HTTP 503, include retry-after headers, and log the error, preventing DoS attacks through error exploitation.

**Validates: Requirements 2.1**

Property 2: Bug Condition - CORS Wildcard Enforcement

_For any_ application startup where ALLOWED_ORIGIN is set to "*" in production environment, the fixed configuration loader SHALL raise ValueError and refuse to start, preventing cross-origin attacks.

**Validates: Requirements 2.2**

Property 3: Bug Condition - Input Validation for Chat Messages

_For any_ chat message containing SQL injection patterns, script tags, command injection attempts, or excessive whitespace, the fixed input validator SHALL reject the message with HTTP 400 and descriptive error, preventing injection attacks.

**Validates: Requirements 2.3**

Property 4: Bug Condition - Session ID Path Traversal Prevention

_For any_ session ID containing path traversal patterns (../, ..\) or reserved keywords (admin, system, root), the fixed validator SHALL reject with ValueError, preventing unauthorized file access.

**Validates: Requirements 2.4**

Property 5: Bug Condition - Image Upload Cleanup on Metadata Failure

_For any_ image upload where S3 succeeds but DynamoDB metadata storage fails, the fixed upload function SHALL delete the orphaned S3 object, log the cleanup action, and return error to client, preventing resource leaks.

**Validates: Requirements 2.5**

Property 6: Bug Condition - Recursive PII Sanitization in Logs

_For any_ log data containing nested structures with PII (emails, phone numbers, addresses), the fixed sanitization function SHALL recursively redact all PII at any nesting level, preventing PII exposure in CloudWatch.

**Validates: Requirements 2.6**

Property 7: Bug Condition - Generic Error Messages in Production

_For any_ internal error in production environment, the fixed error handler SHALL return generic client message while logging detailed error internally, preventing information disclosure.

**Validates: Requirements 2.7**

Property 8: Bug Condition - Request Size Limit Enforcement

_For any_ HTTP request with content-length exceeding 1MB, the fixed request handler SHALL reject with HTTP 413 before parsing, preventing memory exhaustion DoS attacks.

**Validates: Requirements 2.8**

Property 9: Bug Condition - HTTPS Enforcement in Production

_For any_ HTTP connection attempt to production application (non-localhost), the fixed connection handler SHALL redirect to HTTPS or refuse connection, preventing plaintext data transmission.

**Validates: Requirements 2.9**

Property 10: Bug Condition - Password Strength UI Feedback

_For any_ password input during registration, the fixed UI SHALL display requirements and real-time strength feedback, improving user experience and password quality.

**Validates: Requirements 2.10**

Property 11: Bug Condition - Strict CSP Headers

_For any_ HTTP response, the fixed header function SHALL set strict CSP policy blocking inline scripts and restricting resource loading, enhancing XSS protection.

**Validates: Requirements 2.11**

Property 12: Bug Condition - Rate Limit Headers on All Responses

_For any_ API response (including successful 200 responses), the fixed response handler SHALL include X-RateLimit-Limit, X-RateLimit-Remaining, and X-RateLimit-Reset headers, enabling proactive client rate limit management.

**Validates: Requirements 2.12**

Property 13: Preservation - Normal Rate Limiting Behavior

_For any_ rate limit check where DynamoDB is available and user is within limits, the fixed rate limiter SHALL produce the same result as the original, preserving normal request processing.

**Validates: Requirements 3.1, 3.2**

Property 14: Preservation - Valid CORS Configuration

_For any_ CORS configuration with specific domain in production or wildcard in development, the fixed configuration SHALL produce the same result as the original, preserving valid CORS behavior.

**Validates: Requirements 3.3, 3.4**

Property 15: Preservation - Valid Input Processing

_For any_ valid chat message or session ID without malicious content, the fixed validators SHALL produce the same result as the original, preserving normal input processing.

**Validates: Requirements 3.5, 3.6**

Property 16: Preservation - Successful Image Upload

_For any_ image upload where both S3 and DynamoDB succeed, the fixed upload function SHALL produce the same result as the original, preserving successful upload flow.

**Validates: Requirements 3.7, 3.8**

Property 17: Preservation - Non-Sensitive Logging

_For any_ log data without sensitive information, the fixed sanitization SHALL produce the same result as the original, preserving normal logging behavior.

**Validates: Requirements 3.9, 3.10**

Property 18: Preservation - Normal Request Processing

_For any_ HTTP request under 1MB and HTTPS connections, the fixed handlers SHALL produce the same result as the original, preserving normal request processing.

**Validates: Requirements 3.11, 3.12**

Property 19: Preservation - Valid Authentication

_For any_ valid password meeting Cognito requirements, the fixed UI SHALL allow submission and account creation, preserving authentication flow.

**Validates: Requirements 3.13, 3.14**

Property 20: Preservation - Rate Limit Information

_For any_ rate limit response, the fixed headers SHALL include accurate limit information, preserving rate limit transparency.

**Validates: Requirements 3.15, 3.16**


## Fix Implementation

### CRITICAL SEVERITY FIXES

#### Bug 1: Rate Limiter Fail-Closed Implementation

**File**: `src/rate_limiter.py`

**Function**: `check_rate_limit` (lines 140-191)

**Specific Changes**:

1. **Modify Error Handling Logic**:
   - Change lines 177-191 to fail closed in production
   - Keep fail-open behavior only in development for debugging
   - Add structured logging for security events

2. **Implementation**:
```python
except Exception as e:
    logger.error(f"Rate limit check failed: {str(e)}", exc_info=True)
    reset_time = self._format_reset_time(current_time, window_seconds)
    
    # SECURITY: Fail closed in production to prevent DoS attacks
    # When rate limiter fails, deny requests rather than allowing unlimited access
    if os.environ.get("ENVIRONMENT", "dev") == "prod":
        logger.critical(
            f"SECURITY: Rate limiter failed in production - denying request. "
            f"session_id={session_id}, endpoint={endpoint}, error={str(e)}"
        )
        return self.RateLimitResult(
            allowed=False,
            retry_after_seconds=60,  # Retry after 1 minute
            requests_limit=max_requests,
            remaining=0,
            reset_time=reset_time,
        )
    
    # Development: Allow request but log warning
    logger.warning(
        f"Rate limiter error in development - allowing request. "
        f"session_id={session_id}, endpoint={endpoint}"
    )
    return self.RateLimitResult(
        allowed=True,
        retry_after_seconds=None,
        requests_limit=max_requests,
        remaining=max_requests,
        reset_time=reset_time,
    )
```

3. **Add Monitoring**:
   - Log all rate limiter failures with CRITICAL level in production
   - Include session_id, endpoint, and error details for investigation
   - Set up CloudWatch alarms for rate limiter failures

4. **Configuration**:
   - Add `RATE_LIMITER_FAIL_CLOSED` environment variable (default: true in prod)
   - Add `RATE_LIMITER_RETRY_AFTER_SECONDS` configuration (default: 60)

**Rollback Plan**:
- Revert to original fail-open behavior if false positives occur
- Monitor error rates and adjust retry-after timing
- Implement circuit breaker if DynamoDB issues persist


#### Bug 2: CORS Wildcard Enforcement Implementation

**File**: `config/env.py`

**Section**: CORS Configuration (lines 95-115)

**Specific Changes**:

1. **Replace Warning with ValueError**:
   - Remove the `warnings.warn()` call
   - Raise `ValueError` to prevent application startup
   - Provide clear error message with remediation steps

2. **Implementation**:
```python
# Enforce explicit CORS configuration in production
if ENVIRONMENT == "prod":
    if _allowed_origin_env is None:
        raise ValueError(
            "SECURITY ERROR: ALLOWED_ORIGIN must be explicitly set in production. "
            "Set ALLOWED_ORIGIN environment variable to your domain (e.g., 'https://yourdomain.com'). "
            "Never use '*' in production as it allows any origin to access your API."
        )
    if _allowed_origin_env == "*":
        # SECURITY: Wildcard CORS in production is a critical vulnerability
        # It allows any website to make authenticated requests to your API
        raise ValueError(
            "SECURITY ERROR: ALLOWED_ORIGIN='*' is not allowed in production. "
            "This configuration allows any origin to access your API, enabling "
            "cross-origin attacks, token theft, and unauthorized data access. "
            "Set ALLOWED_ORIGIN to your specific domain (e.g., 'https://yourdomain.com')."
        )

ALLOWED_ORIGIN: Optional[str] = _allowed_origin_env
```

3. **Add Validation Function**:
```python
@classmethod
def validate_cors_config(cls) -> bool:
    """
    Validate CORS configuration is secure.
    
    Returns:
        True if configuration is valid
    
    Raises:
        ValueError: If CORS configuration is insecure in production
    """
    if cls.ENVIRONMENT == "prod":
        if cls.ALLOWED_ORIGIN is None:
            raise ValueError("ALLOWED_ORIGIN must be set in production")
        if cls.ALLOWED_ORIGIN == "*":
            raise ValueError("ALLOWED_ORIGIN='*' not allowed in production")
        # Validate it's a proper URL
        if not cls.ALLOWED_ORIGIN.startswith(('https://', 'http://localhost')):
            raise ValueError("ALLOWED_ORIGIN must be HTTPS in production")
    return True
```

4. **Update Startup Validation**:
   - Call `validate_cors_config()` in `Config.validate()`
   - Add to required configuration checks

**Rollback Plan**:
- If deployment fails, temporarily set specific domain in ALLOWED_ORIGIN
- Document proper CORS configuration in deployment guide
- Add pre-deployment validation script


### HIGH SEVERITY FIXES

#### Bug 3: Input Validation Enhancement Implementation

**File**: `src/security_utils.py`

**Function**: `sanitize_user_input` (lines 60-85)

**Specific Changes**:

1. **Add Malicious Pattern Detection**:
```python
def sanitize_user_input(text: str, max_length: int = 5000) -> str:
    """
    Sanitize user text input with enhanced security checks.
    
    Args:
        text: User input text
        max_length: Maximum allowed length
    
    Returns:
        Sanitized text
    
    Raises:
        ValueError: If text contains malicious patterns
    """
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Check for SQL injection patterns
    sql_patterns = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(--\s*$)",
        r"(;\s*DROP\b)",
        r"('\s*OR\s*'1'\s*=\s*'1)",
    ]
    
    for pattern in sql_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(f"SQL injection attempt detected: pattern={pattern}")
            raise ValueError("Invalid message content: potential SQL injection detected")
    
    # Check for script tags and XSS patterns
    xss_patterns = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",  # Event handlers like onclick=
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
    ]
    
    for pattern in xss_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(f"XSS attempt detected: pattern={pattern}")
            raise ValueError("Invalid message content: potential XSS detected")
    
    # Check for command injection patterns
    cmd_patterns = [
        r"[;&|`$]",  # Shell metacharacters
        r"\$\(.*\)",  # Command substitution
        r"`.*`",      # Backtick command execution
    ]
    
    for pattern in cmd_patterns:
        if re.search(pattern, text):
            logger.warning(f"Command injection attempt detected: pattern={pattern}")
            raise ValueError("Invalid message content: potential command injection detected")
    
    # Check for excessive whitespace (potential DoS)
    whitespace_count = sum(1 for c in text if c.isspace())
    if whitespace_count > len(text) * 0.5:  # More than 50% whitespace
        logger.warning(f"Excessive whitespace detected: {whitespace_count}/{len(text)}")
        raise ValueError("Invalid message content: excessive whitespace")
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    # Limit length
    if len(text) > max_length:
        raise ValueError(f"Message exceeds maximum length of {max_length} characters")
    
    # Remove control characters except newlines, tabs, and carriage returns
    text = ''.join(
        char for char in text 
        if char.isprintable() or char in '\n\t\r'
    )
    
    return text.strip()
```

2. **Add Configuration**:
   - Add `INPUT_VALIDATION_STRICT` environment variable (default: true)
   - Add `MAX_WHITESPACE_RATIO` configuration (default: 0.5)

**Rollback Plan**:
- If false positives occur, adjust pattern matching
- Add whitelist for specific legitimate patterns
- Implement gradual rollout with monitoring


#### Bug 4: Session ID Validation Enhancement Implementation

**File**: `src/security_utils.py`

**Function**: `validate_session_id` (lines 20-35)

**Specific Changes**:

1. **Add Path Traversal and Reserved Keyword Checks**:
```python
def validate_session_id(session_id: str) -> str:
    """
    Validate session ID format with enhanced security checks.
    
    Args:
        session_id: Session identifier to validate
    
    Returns:
        Validated session_id
    
    Raises:
        ValueError: If session_id format is invalid or contains security risks
    """
    if not session_id:
        raise ValueError("session_id is required")
    
    # Only allow alphanumeric, underscores, and hyphens, max 64 chars
    if not re.match(r'^[a-zA-Z0-9_-]{1,64}$', session_id):
        raise ValueError(
            "Invalid session_id format. Must be alphanumeric with underscores/hyphens, max 64 characters"
        )
    
    # SECURITY: Check for path traversal patterns
    # These patterns could be used to access unauthorized files
    path_traversal_patterns = [
        '..',      # Parent directory
        './',      # Current directory
        '\\',      # Windows path separator
        '//',      # Double slash
    ]
    
    for pattern in path_traversal_patterns:
        if pattern in session_id:
            logger.warning(f"Path traversal attempt in session_id: {session_id}")
            raise ValueError(
                f"Invalid session_id: contains path traversal pattern '{pattern}'"
            )
    
    # SECURITY: Check for reserved keywords that could enable privilege escalation
    reserved_keywords = [
        'admin', 'administrator', 'root', 'system', 'config',
        'superuser', 'sudo', 'master', 'owner', 'god',
        'test', 'demo', 'guest', 'public', 'default'
    ]
    
    session_id_lower = session_id.lower()
    for keyword in reserved_keywords:
        if keyword in session_id_lower:
            logger.warning(f"Reserved keyword in session_id: {session_id}")
            raise ValueError(
                f"Invalid session_id: contains reserved keyword '{keyword}'"
            )
    
    # SECURITY: Prevent absolute paths
    if session_id.startswith('/') or (len(session_id) > 1 and session_id[1] == ':'):
        logger.warning(f"Absolute path in session_id: {session_id}")
        raise ValueError("Invalid session_id: absolute paths not allowed")
    
    return session_id
```

2. **Add to Configuration**:
   - Add `SESSION_ID_RESERVED_KEYWORDS` environment variable for customization
   - Add `SESSION_ID_STRICT_VALIDATION` flag (default: true)

**Rollback Plan**:
- If legitimate session IDs are rejected, adjust reserved keyword list
- Add exception mechanism for specific patterns if needed
- Monitor validation failures and adjust patterns


#### Bug 5: Image Upload Cleanup Implementation

**File**: `src/kitchen_agent_core.py`

**Function**: `upload_image_to_s3` (lines 130-180)

**Specific Changes**:

1. **Enhance Cleanup Logic with Explicit Error Handling**:
```python
try:
    self.store_image_metadata(
        session_id=session_id,
        image_id=image_id,
        owner_sub=owner_sub,
        s3_key=s3_key,
        content_type=content_type,
    )
except Exception as metadata_error:
    # SECURITY: Cleanup orphaned S3 object to prevent resource leaks
    logger.error(
        f"Metadata storage failed - cleaning up S3 object: "
        f"session_id={session_id}, image_id={image_id}, "
        f"s3_key={s3_key}, error={str(metadata_error)}",
        exc_info=True
    )
    
    try:
        self.s3_client.delete_object(
            Bucket=self.image_bucket,
            Key=s3_key
        )
        logger.info(
            f"Successfully cleaned up orphaned S3 object: "
            f"session_id={session_id}, image_id={image_id}, s3_key={s3_key}"
        )
    except Exception as cleanup_error:
        # CRITICAL: Cleanup failed - manual intervention required
        logger.critical(
            f"CRITICAL: Failed to cleanup orphaned S3 object. "
            f"Manual deletion required: bucket={self.image_bucket}, "
            f"key={s3_key}, session_id={session_id}, image_id={image_id}, "
            f"cleanup_error={str(cleanup_error)}",
            exc_info=True
        )
        # Set up CloudWatch alarm for this critical error
    
    # Re-raise original error to client
    raise ValueError(
        f"Image upload failed: metadata storage error. "
        f"Please try again. Image ID: {image_id}"
    ) from metadata_error
```

2. **Add Monitoring**:
   - CloudWatch alarm for cleanup failures
   - Metric for orphaned object count
   - Daily cleanup job to detect and remove orphaned objects

3. **Add Cleanup Verification**:
```python
def verify_image_upload_complete(self, session_id: str, image_id: str) -> bool:
    """Verify both S3 object and metadata exist."""
    try:
        metadata = self.get_image_metadata(session_id, image_id)
        if not metadata:
            return False
        
        s3_key = metadata.get('s3_key')
        self.s3_client.head_object(Bucket=self.image_bucket, Key=s3_key)
        return True
    except Exception:
        return False
```

**Rollback Plan**:
- If cleanup causes issues, add retry logic with exponential backoff
- Implement async cleanup queue for failed deletions
- Add manual cleanup script for orphaned objects


### MEDIUM SEVERITY FIXES

#### Bug 6: Recursive PII Sanitization Implementation

**File**: `src/security_utils.py`

**Function**: `sanitize_for_logging` (lines 120-150)

**Specific Changes**:

1. **Implement Recursive Sanitization**:
```python
def sanitize_for_logging(data: Any, depth: int = 0, max_depth: int = 10) -> Any:
    """
    Recursively remove sensitive fields from log data.
    
    Args:
        data: Data to sanitize (dict, list, or primitive)
        depth: Current recursion depth
        max_depth: Maximum recursion depth to prevent infinite loops
    
    Returns:
        Sanitized data with sensitive fields redacted
    """
    # Prevent infinite recursion
    if depth > max_depth:
        return '[MAX_DEPTH_EXCEEDED]'
    
    # Sensitive field names to redact
    SENSITIVE_FIELDS = {
        'allergies', 'preferences', 'email', 'phone', 'phone_number',
        'password', 'token', 'api_key', 'secret', 'access_token',
        'refresh_token', 'id_token', 'ssn', 'credit_card',
        'conversation_history', 'address', 'location', 'ip_address',
        'user_agent', 'session_token', 'auth_token'
    }
    
    # PII patterns to detect in string values
    PII_PATTERNS = [
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]'),  # Email
        (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE_REDACTED]'),  # Phone
        (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]'),  # SSN
        (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD_REDACTED]'),  # Credit card
    ]
    
    # Handle dictionaries recursively
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            # Check if key is sensitive
            if key.lower() in SENSITIVE_FIELDS:
                sanitized[key] = '[REDACTED]'
            else:
                # Recursively sanitize value
                sanitized[key] = sanitize_for_logging(value, depth + 1, max_depth)
        return sanitized
    
    # Handle lists recursively
    elif isinstance(data, list):
        return [sanitize_for_logging(item, depth + 1, max_depth) for item in data]
    
    # Handle strings - check for PII patterns
    elif isinstance(data, str):
        sanitized_str = data
        for pattern, replacement in PII_PATTERNS:
            sanitized_str = re.sub(pattern, replacement, sanitized_str)
        return sanitized_str
    
    # Return primitives as-is
    else:
        return data
```

2. **Update All Logging Calls**:
   - Replace direct logging of user data with sanitized versions
   - Add sanitization to CloudWatch handler
   - Update error logging to sanitize exception messages

**Rollback Plan**:
- If over-redaction occurs, adjust sensitive field list
- Add configuration for PII patterns
- Implement gradual rollout with monitoring


#### Bug 7: Generic Error Messages Implementation

**File**: `src/api_handler.py`

**Function**: Multiple error handling locations

**Specific Changes**:

1. **Create Environment-Aware Error Formatter**:
```python
def create_error_response(
    error_code: str,
    internal_message: str,
    status_code: int = 500,
    include_details: bool = None
) -> Dict[str, Any]:
    """
    Create error response with environment-aware message detail.
    
    Args:
        error_code: Error code identifier
        internal_message: Detailed error message for logging
        status_code: HTTP status code
        include_details: Override for detail inclusion (None = auto-detect from env)
    
    Returns:
        Error response dictionary
    """
    # Determine if we should include details
    if include_details is None:
        include_details = Config.ENVIRONMENT != "prod"
    
    # Log detailed error internally
    logger.error(
        f"Error occurred: code={error_code}, status={status_code}, "
        f"details={internal_message}",
        exc_info=True
    )
    
    # Generic error messages for production
    GENERIC_MESSAGES = {
        'database_error': 'A database error occurred. Please try again.',
        'storage_error': 'A storage error occurred. Please try again.',
        'ai_service_error': 'The AI service is temporarily unavailable.',
        'internal_error': 'An internal error occurred. Please try again.',
        'validation_error': 'Invalid request data provided.',
        'authentication_error': 'Authentication failed.',
        'authorization_error': 'You do not have permission to access this resource.',
    }
    
    # Use generic message in production, detailed in development
    if include_details:
        message = internal_message
    else:
        message = GENERIC_MESSAGES.get(error_code, 'An error occurred. Please try again.')
    
    return {
        'error': error_code,
        'message': message,
        'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
    }
```

2. **Update Error Handling Throughout Codebase**:
```python
# Example: Replace DynamoDB error exposure
except ClientError as e:
    error_code = e.response['Error']['Code']
    # OLD: return {'error': f'DynamoDB error: {error_code}'}
    # NEW:
    return create_error_response(
        error_code='database_error',
        internal_message=f'DynamoDB error: {error_code}, table={table_name}',
        status_code=503
    )

# Example: Replace S3 error exposure
except ClientError as e:
    # OLD: return {'error': f'S3 upload failed: {str(e)}'}
    # NEW:
    return create_error_response(
        error_code='storage_error',
        internal_message=f'S3 upload failed: bucket={bucket}, key={key}, error={str(e)}',
        status_code=500
    )
```

3. **Add Configuration**:
   - Add `ERROR_DETAIL_LEVEL` environment variable (none/minimal/full)
   - Add `EXPOSE_STACK_TRACES` flag (default: false in prod)

**Rollback Plan**:
- If debugging becomes difficult, temporarily enable detailed errors
- Add request ID tracking for error correlation
- Implement secure error detail retrieval for support team


#### Bug 8: Request Size Limit Implementation

**File**: `src/api_handler.py`

**Function**: `lambda_handler` and `parse_request_body`

**Specific Changes**:

1. **Add Global Request Size Check**:
```python
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for API Gateway requests with request size validation.
    """
    try:
        # SECURITY: Check request size before parsing to prevent DoS
        content_length = int(event.get('headers', {}).get('Content-Length', 0))
        MAX_REQUEST_SIZE = 1048576  # 1MB in bytes
        
        if content_length > MAX_REQUEST_SIZE:
            logger.warning(
                f"Request size exceeds limit: {content_length} bytes "
                f"(max: {MAX_REQUEST_SIZE})"
            )
            return create_response(
                status_code=413,
                body={
                    'error': 'payload_too_large',
                    'message': f'Request body exceeds maximum size of {MAX_REQUEST_SIZE / 1024 / 1024}MB',
                    'max_size_mb': MAX_REQUEST_SIZE / 1024 / 1024,
                    'received_size_mb': round(content_length / 1024 / 1024, 2)
                }
            )
        
        # Extract request details
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        
        logger.info(f"Received request: {http_method} {path}")
        
        # ... rest of handler logic
```

2. **Add Size Check to Parse Function**:
```python
def parse_request_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse JSON request body with size validation.
    
    Args:
        event: API Gateway event
    
    Returns:
        Parsed request body
    
    Raises:
        ValueError: If body is too large or invalid JSON
    """
    body = event.get('body', '')
    
    if not body:
        return {}
    
    # Check body size before parsing
    body_size = len(body.encode('utf-8'))
    MAX_BODY_SIZE = 1048576  # 1MB
    
    if body_size > MAX_BODY_SIZE:
        raise ValueError(
            f'Request body too large: {body_size} bytes (max: {MAX_BODY_SIZE})'
        )
    
    try:
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(body).decode('utf-8')
        
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise ValueError(f'Invalid JSON in request body: {str(e)}')
    except Exception as e:
        raise ValueError(f'Failed to parse request body: {str(e)}')
```

3. **Add Configuration**:
   - Add `MAX_REQUEST_SIZE_MB` environment variable (default: 1)
   - Add `MAX_MULTIPART_SIZE_MB` for file uploads (default: 10)
   - Add per-endpoint size limits configuration

**Rollback Plan**:
- If legitimate requests are rejected, increase size limit
- Add endpoint-specific size limits
- Monitor request size distribution


#### Bug 9: HTTPS Enforcement Implementation

**File**: `app.py`

**Function**: `check_https_security` (lines 30-50)

**Specific Changes**:

1. **Implement HTTPS Redirect/Enforcement**:
```python
def check_https_security():
    """
    SECURITY: Enforce HTTPS in production to prevent token interception.
    HTTP connections expose session tokens and user data to man-in-the-middle attacks.
    """
    if 'https_checked' not in st.session_state:
        st.session_state.https_checked = True
        is_production = os.getenv('ENVIRONMENT', 'dev') == 'prod'
        is_localhost = os.getenv('STREAMLIT_SERVER_ADDRESS', 'localhost') in ['localhost', '127.0.0.1']
        
        if is_production and not is_localhost:
            # Check if connection is HTTPS
            # Note: Streamlit doesn't expose protocol directly, check via headers
            headers = st.context.headers if hasattr(st, 'context') else {}
            is_https = (
                headers.get('X-Forwarded-Proto', '').lower() == 'https' or
                headers.get('X-Forwarded-Ssl', '').lower() == 'on' or
                os.getenv('STREAMLIT_SERVER_ENABLE_HTTPS', 'false').lower() == 'true'
            )
            
            if not is_https:
                # SECURITY: Refuse HTTP connections in production
                st.error(
                    "🔒 SECURITY ERROR: This application must be accessed via HTTPS. "
                    "HTTP connections are not allowed in production as they expose "
                    "your authentication tokens and personal data to interception."
                )
                st.stop()  # Stop execution to prevent data exposure
                
            # Verify XSRF protection is enabled
            enable_xsrf = os.getenv('STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION', 'true').lower() == 'true'
            if not enable_xsrf:
                st.error("⚠️ SECURITY WARNING: XSRF protection is disabled.")
                logger.critical("SECURITY: XSRF protection disabled in production")
                st.stop()
```

2. **Add Nginx/ALB Configuration Documentation**:
```nginx
# Nginx configuration for HTTPS enforcement
server {
    listen 80;
    server_name app.example.com;
    
    # Redirect all HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name app.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Forwarded-Proto $scheme;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Ssl on;
    }
}
```

3. **Add Configuration**:
   - Add `REQUIRE_HTTPS` environment variable (default: true in prod)
   - Add `HTTPS_REDIRECT_ENABLED` flag
   - Document reverse proxy setup requirements

**Rollback Plan**:
- If HTTPS setup fails, temporarily allow HTTP with warning
- Provide clear deployment documentation
- Add health check endpoint that bypasses HTTPS check


### LOW SEVERITY FIXES

#### Bug 10: Password Strength UI Implementation

**File**: `app.py`

**Function**: `render_login_screen` (lines 550-580)

**Specific Changes**:

1. **Add Password Requirements Display and Strength Meter**:
```python
def render_login_screen():
    """Render the Cognito sign-in form with password strength feedback."""
    st.markdown(
        """
        <div style="max-width:420px;margin:6rem auto 0 auto;padding:2rem;background:#141208;border:1px solid #2A2015;border-radius:16px;">
            <div style="font-size:2rem;margin-bottom:0.75rem;">🔐</div>
            <div style="font-size:1.4rem;font-weight:700;color:#F0C040;margin-bottom:0.35rem;">Sign In</div>
            <div style="font-size:0.9rem;color:#7A6535;margin-bottom:1.5rem;">Authenticate with Cognito to access your kitchen session.</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password", key="password_input")
        
        # Display password requirements
        if password:
            strength, feedback = check_password_strength(password)
            
            st.markdown("**Password Requirements:**")
            requirements = [
                ("✓" if len(password) >= 8 else "✗", "At least 8 characters"),
                ("✓" if re.search(r'[A-Z]', password) else "✗", "One uppercase letter"),
                ("✓" if re.search(r'[a-z]', password) else "✗", "One lowercase letter"),
                ("✓" if re.search(r'\d', password) else "✗", "One number"),
                ("✓" if re.search(r'[^A-Za-z0-9]', password) else "✗", "One special character"),
            ]
            
            for check, req in requirements:
                color = "#4CAF50" if check == "✓" else "#E84040"
                st.markdown(f"<span style='color:{color}'>{check}</span> {req}", unsafe_allow_html=True)
            
            # Display strength meter
            strength_colors = {
                'weak': '#E84040',
                'fair': '#E8890C',
                'good': '#C4956A',
                'strong': '#4CAF50'
            }
            st.markdown(
                f"<div style='margin-top:0.5rem;'>Strength: "
                f"<span style='color:{strength_colors[strength]};font-weight:600;'>{strength.upper()}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
        
        submitted = st.form_submit_button("Sign In", use_container_width=True)

def check_password_strength(password: str) -> tuple[str, str]:
    """
    Check password strength and provide feedback.
    
    Returns:
        Tuple of (strength_level, feedback_message)
    """
    score = 0
    feedback = []
    
    if len(password) >= 8:
        score += 1
    else:
        feedback.append("Use at least 8 characters")
    
    if len(password) >= 12:
        score += 1
    
    if re.search(r'[A-Z]', password):
        score += 1
    else:
        feedback.append("Add uppercase letters")
    
    if re.search(r'[a-z]', password):
        score += 1
    else:
        feedback.append("Add lowercase letters")
    
    if re.search(r'\d', password):
        score += 1
    else:
        feedback.append("Add numbers")
    
    if re.search(r'[^A-Za-z0-9]', password):
        score += 1
    else:
        feedback.append("Add special characters")
    
    # Determine strength level
    if score <= 2:
        return 'weak', '; '.join(feedback)
    elif score <= 3:
        return 'fair', '; '.join(feedback)
    elif score <= 4:
        return 'good', 'Consider adding more variety'
    else:
        return 'strong', 'Excellent password!'
```

2. **Add Configuration**:
   - Add `PASSWORD_MIN_LENGTH` (default: 8)
   - Add `PASSWORD_REQUIRE_SPECIAL` (default: true)
   - Add `SHOW_PASSWORD_STRENGTH` (default: true)

**Rollback Plan**:
- If UI issues occur, make strength meter optional
- Add toggle to hide/show requirements
- Ensure server-side validation remains primary


#### Bug 11: Strict CSP Headers Implementation

**File**: `src/security_utils.py`

**Function**: `create_secure_response_headers` (lines 230-250)

**Specific Changes**:

1. **Implement Strict CSP Policy**:
```python
def create_secure_response_headers(allowed_origin: Optional[str] = None) -> Dict[str, str]:
    """
    Create secure HTTP response headers with strict CSP.
    
    Args:
        allowed_origin: Specific origin to allow (None = no CORS)
    
    Returns:
        Dictionary of security headers
    """
    # SECURITY: Strict Content Security Policy to prevent XSS attacks
    # This policy blocks inline scripts, inline styles, and restricts resource loading
    csp_directives = [
        "default-src 'self'",
        "script-src 'self'",  # No inline scripts, no eval()
        "style-src 'self' 'unsafe-inline'",  # Allow inline styles for Streamlit
        "img-src 'self' data: https:",  # Allow images from self, data URIs, and HTTPS
        "font-src 'self' data:",
        "connect-src 'self'",  # API calls only to same origin
        "frame-ancestors 'none'",  # Prevent clickjacking
        "base-uri 'self'",  # Prevent base tag injection
        "form-action 'self'",  # Forms only submit to same origin
        "object-src 'none'",  # Block plugins
        "upgrade-insecure-requests",  # Upgrade HTTP to HTTPS
    ]
    
    headers = {
        'Content-Type': 'application/json',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
        'Content-Security-Policy': '; '.join(csp_directives),
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=(), payment=()',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Vary': 'Origin',
        'X-Permitted-Cross-Domain-Policies': 'none',
    }
    
    # Add CORS header if origin specified
    if allowed_origin:
        headers['Access-Control-Allow-Origin'] = allowed_origin
    
    return headers
```

2. **Add CSP Reporting**:
```python
def create_secure_response_headers_with_reporting(
    allowed_origin: Optional[str] = None,
    csp_report_uri: Optional[str] = None
) -> Dict[str, str]:
    """Create headers with CSP violation reporting."""
    headers = create_secure_response_headers(allowed_origin)
    
    if csp_report_uri:
        # Add report-uri for CSP violations
        csp = headers['Content-Security-Policy']
        headers['Content-Security-Policy'] = f"{csp}; report-uri {csp_report_uri}"
    
    return headers
```

3. **Add Configuration**:
   - Add `CSP_REPORT_URI` environment variable
   - Add `CSP_STRICT_MODE` flag (default: true)
   - Add `CSP_ALLOW_INLINE_STYLES` for Streamlit compatibility

**Rollback Plan**:
- If CSP breaks functionality, add specific exceptions
- Use CSP report-only mode initially
- Gradually tighten policy based on violation reports


#### Bug 12: Rate Limit Headers on All Responses Implementation

**File**: `src/api_handler.py`

**Function**: `create_response` and all response creation

**Specific Changes**:

1. **Add Rate Limit Headers to All Responses**:
```python
def create_response(
    status_code: int,
    body: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    session_id: Optional[str] = None,
    endpoint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create API Gateway response with security headers and rate limit info.
    
    Args:
        status_code: HTTP status code
        body: Response body dictionary
        headers: Additional headers
        session_id: Session ID for rate limit headers
        endpoint: Endpoint for rate limit headers
    
    Returns:
        API Gateway response dictionary
    """
    # Get base security headers
    response_headers = create_secure_response_headers(
        allowed_origin=Config.ALLOWED_ORIGIN
    )
    
    # Add rate limit headers if session and endpoint provided
    if session_id and endpoint:
        try:
            rate_limit_result = check_rate_limit(session_id, endpoint)
            response_headers.update({
                'X-RateLimit-Limit': str(rate_limit_result.requests_limit),
                'X-RateLimit-Remaining': str(rate_limit_result.remaining),
                'X-RateLimit-Reset': rate_limit_result.reset_time,
            })
        except Exception as e:
            # Don't fail response if rate limit headers fail
            logger.warning(f"Failed to add rate limit headers: {str(e)}")
    
    # Merge with additional headers
    if headers:
        response_headers.update(headers)
    
    return {
        'statusCode': status_code,
        'headers': response_headers,
        'body': json.dumps(body, ensure_ascii=False)
    }
```

2. **Update All Handler Functions**:
```python
def handle_chat(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle POST /chat endpoint with rate limit headers."""
    # ... existing logic ...
    
    # Return response with rate limit headers
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
        session_id=session_id,
        endpoint='/chat'
    )
```

3. **Add Helper Function**:
```python
def get_rate_limit_headers(session_id: str, endpoint: str) -> Dict[str, str]:
    """
    Get rate limit headers for a session and endpoint.
    
    Returns:
        Dictionary with X-RateLimit-* headers
    """
    try:
        result = check_rate_limit(session_id, endpoint)
        return {
            'X-RateLimit-Limit': str(result.requests_limit),
            'X-RateLimit-Remaining': str(result.remaining),
            'X-RateLimit-Reset': result.reset_time,
        }
    except Exception as e:
        logger.warning(f"Failed to get rate limit headers: {str(e)}")
        return {}
```

4. **Add Configuration**:
   - Add `INCLUDE_RATE_LIMIT_HEADERS` flag (default: true)
   - Add `RATE_LIMIT_HEADER_FORMAT` (standard/custom)

**Rollback Plan**:
- If headers cause issues, make them optional
- Add configuration to disable for specific endpoints
- Monitor header size impact on responses


## Testing Strategy

### Validation Approach

The testing strategy follows a three-phase approach:
1. **Exploratory Bug Condition Checking**: Surface counterexamples on unfixed code to confirm vulnerabilities
2. **Fix Checking**: Verify fixes work correctly for all bug conditions
3. **Preservation Checking**: Ensure existing functionality remains unchanged

### Exploratory Bug Condition Checking

**Goal**: Demonstrate each vulnerability exists in the current code before implementing fixes.

**Critical Severity Tests**:

1. **Bug 1 - Rate Limiter Fail-Open**:
   - Simulate DynamoDB unavailability (disconnect network, invalid credentials)
   - Verify requests are allowed through (VULNERABLE)
   - Expected: Unlimited requests possible, DoS vulnerability confirmed

2. **Bug 2 - CORS Wildcard**:
   - Set ALLOWED_ORIGIN="*" in production environment
   - Start application
   - Verify application starts with only warning (VULNERABLE)
   - Expected: Application runs, cross-origin attacks possible

**High Severity Tests**:

3. **Bug 3 - Input Validation**:
   - Send chat message: `"'; DROP TABLE users; --" + " " * 4970`
   - Verify message is processed (VULNERABLE)
   - Expected: SQL injection pattern accepted

4. **Bug 4 - Session ID Validation**:
   - Use session ID: `"user123--..-data"`
   - Verify session ID is accepted (VULNERABLE)
   - Expected: Path traversal pattern accepted

5. **Bug 5 - Image Upload Cleanup**:
   - Upload image, simulate DynamoDB failure during metadata storage
   - Check S3 for orphaned object
   - Expected: S3 object remains, cleanup fails

**Medium Severity Tests**:

6. **Bug 6 - Nested PII**:
   - Log conversation with nested email: `{"history": [{"user": "email@test.com"}]}`
   - Check CloudWatch logs
   - Expected: Email visible in logs (VULNERABLE)

7. **Bug 7 - Error Messages**:
   - Trigger DynamoDB error in production
   - Check error message returned to client
   - Expected: "DynamoDB table 'users' unavailable" exposed

8. **Bug 8 - Request Size**:
   - Send 10MB JSON payload
   - Monitor memory usage
   - Expected: Parser attempts to load entire payload, memory spike

9. **Bug 9 - HTTPS Enforcement**:
   - Access production app via HTTP
   - Verify connection allowed
   - Expected: Warning shown but connection proceeds (VULNERABLE)

**Low Severity Tests**:

10. **Bug 10 - Password UI**:
    - Enter weak password "123456"
    - Check for client-side feedback
    - Expected: No requirements shown, no strength meter

11. **Bug 11 - CSP Headers**:
    - Check response headers
    - Verify CSP policy
    - Expected: Generic "default-src 'self'" without inline script blocking

12. **Bug 12 - Rate Limit Headers**:
    - Make successful API request (200 response)
    - Check response headers
    - Expected: No X-RateLimit-* headers present


### Fix Checking

**Goal**: Verify that for all inputs where bug conditions hold, the fixed functions produce expected secure behavior.

**Test Approach**: For each bug, write tests that trigger the bug condition and assert the fix works correctly.

**Critical Severity Fix Tests**:

1. **Bug 1 - Rate Limiter Fail-Closed**:
```python
def test_rate_limiter_fails_closed_in_production():
    # Simulate DynamoDB error in production
    with mock.patch.dict(os.environ, {'ENVIRONMENT': 'prod'}):
        with mock.patch.object(rate_limiter.table, 'get_item', side_effect=Exception("DynamoDB error")):
            result = rate_limiter.check_rate_limit('test_session', '/chat')
            
            assert result.allowed == False
            assert result.retry_after_seconds == 60
            assert result.remaining == 0
```

2. **Bug 2 - CORS Enforcement**:
```python
def test_cors_wildcard_rejected_in_production():
    with mock.patch.dict(os.environ, {'ENVIRONMENT': 'prod', 'ALLOWED_ORIGIN': '*'}):
        with pytest.raises(ValueError, match="ALLOWED_ORIGIN='\\*' is not allowed"):
            importlib.reload(config.env)
```

**High Severity Fix Tests**:

3. **Bug 3 - Input Validation**:
```python
def test_sql_injection_rejected():
    malicious_input = "'; DROP TABLE users; --"
    with pytest.raises(ValueError, match="potential SQL injection"):
        sanitize_user_input(malicious_input)

def test_xss_rejected():
    malicious_input = "<script>alert('XSS')</script>"
    with pytest.raises(ValueError, match="potential XSS"):
        sanitize_user_input(malicious_input)
```

4. **Bug 4 - Session ID Validation**:
```python
def test_path_traversal_rejected():
    with pytest.raises(ValueError, match="path traversal"):
        validate_session_id("user123--..-data")

def test_reserved_keyword_rejected():
    with pytest.raises(ValueError, match="reserved keyword"):
        validate_session_id("admin")
```

5. **Bug 5 - Image Upload Cleanup**:
```python
def test_orphaned_s3_object_cleaned_up():
    # Mock S3 success, DynamoDB failure
    with mock.patch.object(kitchen_agent, 'store_image_metadata', side_effect=Exception("DynamoDB error")):
        with pytest.raises(ValueError):
            kitchen_agent.upload_image_to_s3(image_data, session_id, owner_sub)
        
        # Verify S3 object was deleted
        with pytest.raises(ClientError):
            kitchen_agent.s3_client.head_object(Bucket=bucket, Key=s3_key)
```

**Medium Severity Fix Tests**:

6. **Bug 6 - Recursive PII Sanitization**:
```python
def test_nested_pii_redacted():
    data = {
        "conversation_history": [
            {"user": "My email is test@example.com", "assistant": "Hello"}
        ]
    }
    sanitized = sanitize_for_logging(data)
    assert "[EMAIL_REDACTED]" in str(sanitized)
    assert "test@example.com" not in str(sanitized)
```

7. **Bug 7 - Generic Error Messages**:
```python
def test_production_errors_generic():
    with mock.patch.dict(os.environ, {'ENVIRONMENT': 'prod'}):
        response = create_error_response(
            'database_error',
            'DynamoDB table users unavailable in us-east-1',
            503
        )
        assert 'DynamoDB' not in response['message']
        assert 'us-east-1' not in response['message']
```

8. **Bug 8 - Request Size Limit**:
```python
def test_large_request_rejected():
    event = {
        'headers': {'Content-Length': '10485760'},  # 10MB
        'body': 'x' * 10485760
    }
    response = lambda_handler(event, None)
    assert response['statusCode'] == 413
```

9. **Bug 9 - HTTPS Enforcement**:
```python
def test_http_refused_in_production():
    with mock.patch.dict(os.environ, {'ENVIRONMENT': 'prod'}):
        with mock.patch('streamlit.context.headers', {'X-Forwarded-Proto': 'http'}):
            with pytest.raises(st.script_runner.StopException):
                check_https_security()
```

**Low Severity Fix Tests**:

10. **Bug 10 - Password Strength UI**:
```python
def test_password_requirements_displayed():
    # Test that UI shows requirements
    strength, feedback = check_password_strength("weak")
    assert strength == 'weak'
    assert len(feedback) > 0
```

11. **Bug 11 - Strict CSP**:
```python
def test_csp_blocks_inline_scripts():
    headers = create_secure_response_headers()
    csp = headers['Content-Security-Policy']
    assert "script-src 'self'" in csp
    assert "'unsafe-inline'" not in csp or "script-src" not in csp
```

12. **Bug 12 - Rate Limit Headers**:
```python
def test_rate_limit_headers_on_success():
    response = create_response(200, {'result': 'ok'}, session_id='test', endpoint='/chat')
    headers = response['headers']
    assert 'X-RateLimit-Limit' in headers
    assert 'X-RateLimit-Remaining' in headers
    assert 'X-RateLimit-Reset' in headers
```


### Preservation Checking

**Goal**: Verify that for all inputs where bug conditions do NOT hold, the fixed functions produce the same results as the original functions.

**Test Approach**: Property-based testing is recommended to generate many test cases automatically and catch edge cases.

**Preservation Test Cases**:

1. **Rate Limiting Preservation**:
```python
@given(st.text(min_size=1, max_size=64, alphabet=string.ascii_letters + string.digits))
def test_normal_rate_limiting_preserved(session_id):
    # When DynamoDB is available and within limits
    result_original = rate_limiter_original.check_rate_limit(session_id, '/chat')
    result_fixed = rate_limiter_fixed.check_rate_limit(session_id, '/chat')
    
    if result_original.allowed:
        assert result_fixed.allowed == result_original.allowed
        assert result_fixed.remaining == result_original.remaining
```

2. **CORS Configuration Preservation**:
```python
def test_valid_cors_preserved():
    # Development with wildcard
    with mock.patch.dict(os.environ, {'ENVIRONMENT': 'dev', 'ALLOWED_ORIGIN': '*'}):
        config = Config()
        assert config.ALLOWED_ORIGIN == '*'
    
    # Production with specific domain
    with mock.patch.dict(os.environ, {'ENVIRONMENT': 'prod', 'ALLOWED_ORIGIN': 'https://example.com'}):
        config = Config()
        assert config.ALLOWED_ORIGIN == 'https://example.com'
```

3. **Valid Input Preservation**:
```python
@given(st.text(min_size=1, max_size=5000, alphabet=string.printable))
def test_valid_input_preserved(message):
    # Filter out messages with malicious patterns
    assume(not any(pattern in message for pattern in ['<script', 'DROP TABLE', ';--']))
    
    try:
        result = sanitize_user_input(message)
        assert len(result) <= 5000
        assert isinstance(result, str)
    except ValueError:
        # Some random strings may still trigger validation
        pass
```

4. **Valid Session ID Preservation**:
```python
@given(st.text(min_size=1, max_size=64, alphabet=string.ascii_letters + string.digits + '_-'))
def test_valid_session_id_preserved(session_id):
    # Filter out IDs with traversal patterns or reserved keywords
    assume('..' not in session_id)
    assume(session_id.lower() not in ['admin', 'root', 'system'])
    
    result = validate_session_id(session_id)
    assert result == session_id
```

5. **Successful Image Upload Preservation**:
```python
def test_successful_upload_preserved():
    # When both S3 and DynamoDB succeed
    result = kitchen_agent.upload_image_to_s3(image_data, session_id, owner_sub)
    
    assert 'image_id' in result
    assert 's3_url' in result
    assert 's3_key' in result
    
    # Verify both S3 and metadata exist
    assert kitchen_agent.verify_image_upload_complete(session_id, result['image_id'])
```

6. **Non-Sensitive Logging Preservation**:
```python
def test_non_sensitive_data_preserved():
    data = {
        'session_id': 'test123',
        'endpoint': '/chat',
        'status': 'success'
    }
    sanitized = sanitize_for_logging(data)
    assert sanitized == data  # No changes for non-sensitive data
```

7. **Normal Request Processing Preservation**:
```python
def test_small_requests_preserved():
    event = {
        'headers': {'Content-Length': '1024'},  # 1KB
        'body': json.dumps({'message': 'Hello'})
    }
    response = lambda_handler(event, None)
    assert response['statusCode'] in [200, 400, 401, 403]  # Not 413
```

8. **HTTPS Connection Preservation**:
```python
def test_https_connections_preserved():
    with mock.patch.dict(os.environ, {'ENVIRONMENT': 'prod'}):
        with mock.patch('streamlit.context.headers', {'X-Forwarded-Proto': 'https'}):
            # Should not raise exception
            check_https_security()
```

9. **Valid Password Preservation**:
```python
def test_strong_passwords_accepted():
    strong_password = "MyStr0ng!Pass"
    strength, feedback = check_password_strength(strong_password)
    assert strength in ['good', 'strong']
```

10. **Security Headers Preservation**:
```python
def test_other_security_headers_preserved():
    headers = create_secure_response_headers()
    
    # Verify all security headers still present
    assert headers['X-Content-Type-Options'] == 'nosniff'
    assert headers['X-Frame-Options'] == 'DENY'
    assert 'Strict-Transport-Security' in headers
```


### Unit Tests

**Critical Severity Unit Tests**:
- Test rate limiter fail-closed behavior with various DynamoDB errors
- Test rate limiter fail-open in development environment
- Test CORS configuration validation at startup
- Test CORS wildcard rejection in production
- Test CORS specific domain acceptance

**High Severity Unit Tests**:
- Test SQL injection pattern detection (10+ patterns)
- Test XSS pattern detection (script tags, event handlers, iframes)
- Test command injection pattern detection (shell metacharacters)
- Test excessive whitespace detection
- Test path traversal pattern detection (../, ..\, //, \\)
- Test reserved keyword detection (admin, root, system, etc.)
- Test S3 cleanup on metadata failure
- Test S3 cleanup failure logging
- Test cleanup verification function

**Medium Severity Unit Tests**:
- Test recursive PII sanitization (nested dicts, lists, deep nesting)
- Test PII pattern detection (email, phone, SSN, credit card)
- Test max depth prevention in recursive sanitization
- Test generic error messages in production
- Test detailed error messages in development
- Test request size limit enforcement (1MB, 10MB, 100MB)
- Test multipart form size limits
- Test HTTPS enforcement in production
- Test HTTP allowed in development

**Low Severity Unit Tests**:
- Test password strength calculation (weak, fair, good, strong)
- Test password requirements display
- Test CSP directive parsing
- Test inline script blocking
- Test rate limit header inclusion on all responses
- Test rate limit header accuracy

### Property-Based Tests

**Input Validation Properties**:
```python
@given(st.text(min_size=1, max_size=10000))
def test_sanitize_never_returns_malicious_content(text):
    try:
        result = sanitize_user_input(text)
        # Result should never contain malicious patterns
        assert not re.search(r'<script', result, re.IGNORECASE)
        assert not re.search(r'DROP\s+TABLE', result, re.IGNORECASE)
    except ValueError:
        # Rejection is acceptable
        pass
```

**Session ID Validation Properties**:
```python
@given(st.text(min_size=1, max_size=100))
def test_validate_session_id_never_allows_traversal(session_id):
    try:
        result = validate_session_id(session_id)
        # Result should never contain traversal patterns
        assert '..' not in result
        assert '/' not in result
        assert '\\' not in result
    except ValueError:
        # Rejection is acceptable
        pass
```

**PII Sanitization Properties**:
```python
@given(st.recursive(
    st.dictionaries(st.text(), st.text()),
    lambda children: st.dictionaries(st.text(), children)
))
def test_sanitize_removes_all_pii(data):
    sanitized = sanitize_for_logging(data)
    # No email patterns should remain
    assert not re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', str(sanitized))
```

### Integration Tests

**End-to-End Security Tests**:

1. **Rate Limiting Integration**:
   - Deploy application with DynamoDB
   - Make 50 requests to /chat endpoint
   - Verify 51st request returns 429
   - Simulate DynamoDB failure
   - Verify requests are denied with 503

2. **CORS Integration**:
   - Deploy with ALLOWED_ORIGIN="*" in production
   - Verify deployment fails
   - Deploy with specific domain
   - Verify CORS headers correct

3. **Input Validation Integration**:
   - Send malicious chat messages through full API stack
   - Verify all rejected with 400
   - Send valid messages
   - Verify all processed successfully

4. **Image Upload Integration**:
   - Upload image, simulate metadata failure
   - Verify S3 object cleaned up
   - Check CloudWatch logs for cleanup confirmation
   - Verify error returned to client

5. **Error Handling Integration**:
   - Trigger various errors in production
   - Verify all return generic messages
   - Check CloudWatch for detailed internal logs
   - Verify no service names exposed

6. **HTTPS Integration**:
   - Access production app via HTTP
   - Verify connection refused
   - Access via HTTPS
   - Verify connection succeeds

7. **Security Headers Integration**:
   - Make API requests
   - Verify all responses include security headers
   - Verify CSP policy correct
   - Verify rate limit headers present

### Security Testing

**Penetration Testing Scenarios**:

1. **DoS Attack Simulation**:
   - Attempt to overwhelm rate limiter
   - Attempt memory exhaustion with large payloads
   - Attempt to trigger DynamoDB errors

2. **Injection Attack Simulation**:
   - Attempt SQL injection in all input fields
   - Attempt XSS in chat messages
   - Attempt command injection
   - Attempt path traversal in session IDs

3. **Information Disclosure Testing**:
   - Trigger various error conditions
   - Verify no internal details exposed
   - Check logs for PII leakage
   - Verify error messages generic

4. **Authentication Bypass Testing**:
   - Attempt to use reserved session IDs
   - Attempt path traversal to access other sessions
   - Verify all attempts blocked

5. **CORS Attack Simulation**:
   - Attempt cross-origin requests from malicious domain
   - Verify CORS policy enforced
   - Attempt to bypass with various headers

### Performance Testing

**Load Testing with Security Fixes**:
- Measure rate limiter performance under load
- Measure input validation overhead
- Measure PII sanitization performance
- Verify no significant performance degradation

**Monitoring and Alerting**:
- Set up CloudWatch alarms for security events
- Monitor rate limiter failures
- Monitor cleanup failures
- Monitor validation rejections
- Track security header compliance

