# Security Audit Report
**Andhra Kitchen Agent - Comprehensive Security Analysis**

> Historical note: this audit captures the pre-remediation state. The current implementation now enforces Cognito bearer authentication, owner-bound sessions/images/reminders, and restrictive CORS.

**Date**: 2026-03-13  
**Auditor**: Kiro AI Security Audit  
**Scope**: Complete codebase security review  
**Status**: ⚠️ CRITICAL ISSUES FOUND

---

## Executive Summary

This security audit identified **12 security vulnerabilities** across the Andhra Kitchen Agent codebase, ranging from **CRITICAL** to **LOW** severity at the time of review. The most critical issues include:

- **CRITICAL**: HTTP allowed for non-localhost URLs (MITM vulnerability)
- **CRITICAL**: No authentication/authorization on API endpoints at audit time
- **HIGH**: CORS configured to allow all origins (`*`)
- **HIGH**: Missing input validation and sanitization
- **HIGH**: Unrestricted IP access in API Gateway policy

**Current Note**: Treat this report as an audit baseline, not the current deployment state. The current implementation now enforces Cognito bearer authentication, owner-bound sessions/images/reminders, and restrictive CORS.

---

## Vulnerability Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 2 | 🔴 Unresolved |
| HIGH | 5 | 🔴 Unresolved |
| MEDIUM | 3 | 🟡 Unresolved |
| LOW | 2 | 🟢 Acceptable |

---

## Detailed Findings

### 🔴 CRITICAL SEVERITY

#### 1. HTTP Allowed for Non-Localhost URLs (MITM Risk)
**Location**: `src/api_client.py:52`  
**Severity**: CRITICAL  
**CWE**: CWE-319 (Cleartext Transmission of Sensitive Information)

**Description**:
```python
# WARNING: HTTP allowed for non-localhost URLs (MITM risk)
if not url.startswith(('http://', 'https://')):
    url = f'http://{url}'
```

The code allows HTTP connections to non-localhost URLs, exposing data to man-in-the-middle (MITM) attacks. All sensitive data (session IDs, user preferences, recipes, images) transmitted over HTTP can be intercepted.

**Impact**:
- Session hijacking
- Data interception (recipes, shopping lists, user preferences)
- Credential theft if authentication is added later
- Privacy violations (user dietary preferences, allergies)

**Recommendation**:
```python
# SECURE ALTERNATIVE:
if not url.startswith(('http://', 'https://')):
    # Default to HTTPS for security
    url = f'https://{url}'

# Only allow HTTP for localhost/127.0.0.1
if url.startswith('http://') and not any(
    host in url for host in ['localhost', '127.0.0.1', '[::1]']
):
    raise ValueError(
        "HTTP connections are only allowed for localhost. "
        "Use HTTPS for remote connections."
    )
```

---

#### 2. No Authentication/Authorization on API Endpoints
**Location**: `src/api_handler.py` (all endpoints), `infrastructure/cloudformation/api-gateway.yaml`  
**Severity**: CRITICAL  
**CWE**: CWE-306 (Missing Authentication for Critical Function)

**Remediation Status**:
This finding has been addressed in the current implementation. Application routes now require Cognito bearer authentication and enforce session ownership checks.

**Description**:
All API endpoints were configured with `AuthorizationType: NONE` at the time of audit:
- `/chat` - No authentication at audit time
- `/session` - No authentication at audit time
- `/upload-image` - No authentication at audit time
- `/analyze-image` - No authentication at audit time
- `/generate-recipes` - No authentication at audit time
- `/generate-shopping-list` - No authentication at audit time
- `/reminders/*` - No authentication at audit time

**Impact**:
- **Unauthorized access** to all user data
- **Session hijacking** - anyone with a session_id can access user data
- **Data manipulation** - attackers can create/modify sessions, recipes, reminders
- **Resource abuse** - unlimited API calls to expensive Bedrock services
- **Privacy violations** - access to user allergies, preferences, shopping habits

**Recommendation**:
```yaml
# Add API Key authentication (minimum)
ChatMethod:
  Type: AWS::ApiGateway::Method
  Properties:
    AuthorizationType: API_KEY
    ApiKeyRequired: true

# Better: Use AWS IAM or Cognito
ChatMethod:
  Type: AWS::ApiGateway::Method
  Properties:
    AuthorizationType: AWS_IAM  # or COGNITO_USER_POOLS
```

**Additional Recommendations**:
1. Implement AWS Cognito User Pools for user authentication
2. Add API Gateway authorizer Lambda for custom auth logic
3. Implement session validation middleware
4. Add rate limiting per user/API key
5. Log all authentication failures

---

### 🟠 HIGH SEVERITY

#### 3. CORS Allows All Origins (`*`)
**Location**: `infrastructure/cloudformation/api-gateway.yaml:88`  
**Severity**: HIGH  
**CWE**: CWE-942 (Permissive Cross-domain Policy with Untrusted Domains)

**Description**:
```yaml
method.response.header.Access-Control-Allow-Origin: "'*'"
```

CORS is configured to allow requests from ANY origin, enabling cross-site request forgery (CSRF) and data theft.

**Impact**:
- Malicious websites can make API requests on behalf of users
- Session tokens can be stolen via XSS + CORS
- Data exfiltration from legitimate user sessions

**Recommendation**:
```yaml
# Restrict to specific trusted origins
method.response.header.Access-Control-Allow-Origin: "'https://yourdomain.com'"

# Or use environment-specific origins
method.response.header.Access-Control-Allow-Origin: !Sub "'https://${Environment}.yourdomain.com'"

# For multiple origins, implement dynamic CORS in Lambda
```

---

#### 4. Missing Input Validation and Sanitization
**Location**: Multiple files - `src/api_handler.py`, `src/api_client.py`, `app.py`  
**Severity**: HIGH  
**CWE**: CWE-20 (Improper Input Validation)

**Description**:
User inputs are not validated or sanitized before processing:

**Examples**:
1. **Session ID** - No format validation, could contain injection payloads
2. **Language parameter** - Only validates `['en', 'te']` but doesn't sanitize
3. **Recipe ID** - No validation, direct use in DynamoDB queries
4. **Duration hours** - Basic type check but no range validation
5. **User messages** - No sanitization before sending to Bedrock
6. **File uploads** - Comment indicates client-side validation insufficient (line 145)

**Impact**:
- **NoSQL Injection** in DynamoDB queries
- **Command Injection** if inputs reach shell commands
- **XSS** if unsanitized data is rendered in UI
- **Path Traversal** in file operations
- **DoS** via malformed inputs

**Recommendation**:
```python
import re
from typing import Optional

def validate_session_id(session_id: str) -> Optional[str]:
    """Validate session ID format."""
    # Only allow alphanumeric and underscores, max 64 chars
    if not re.match(r'^[a-zA-Z0-9_]{1,64}$', session_id):
        raise ValueError("Invalid session_id format")
    return session_id

def sanitize_user_input(text: str, max_length: int = 5000) -> str:
    """Sanitize user text input."""
    # Remove null bytes
    text = text.replace('\x00', '')
    # Limit length
    text = text[:max_length]
    # Remove control characters except newlines/tabs
    text = ''.join(char for char in text if char.isprintable() or char in '\n\t')
    return text.strip()

def validate_duration_hours(hours: float) -> float:
    """Validate reminder duration."""
    if not 0.1 <= hours <= 168:  # Max 1 week
        raise ValueError("Duration must be between 0.1 and 168 hours")
    return hours
```

**Apply validation to all endpoints**:
```python
# In handle_chat_message
session_id = validate_session_id(body.get('session_id', ''))
message = sanitize_user_input(body.get('message', ''))

# In handle_snooze_reminder
duration_hours = validate_duration_hours(float(body.get('duration_hours')))
```

---

#### 5. Unrestricted IP Access in API Gateway
**Location**: `infrastructure/cloudformation/api-gateway.yaml:20-26`  
**Severity**: HIGH  
**CWE**: CWE-284 (Improper Access Control)

**Description**:
```yaml
Condition:
  IpAddress:
    aws:SourceIp:
      - '0.0.0.0/0'  # WARNING: Restrict to specific IPs in production
```

API Gateway policy allows access from ANY IP address worldwide.

**Impact**:
- No geographic restrictions
- Enables attacks from anywhere
- No IP-based rate limiting
- Difficult to block malicious actors

**Recommendation**:
```yaml
# Restrict to known IP ranges
Condition:
  IpAddress:
    aws:SourceIp:
      - '203.0.113.0/24'  # Your office network
      - '198.51.100.0/24'  # Your cloud provider
      # Add CloudFront IP ranges if using CDN

# Or use AWS WAF for advanced IP filtering
```

---

#### 6. File Upload Validation Insufficient
**Location**: `src/api_client.py:145`  
**Severity**: HIGH  
**CWE**: CWE-434 (Unrestricted Upload of File with Dangerous Type)

**Description**:
```python
# WARNING: File upload validation comment indicates client-side validation not sufficient
```

File uploads rely on client-side validation, which can be bypassed.

**Impact**:
- **Malicious file uploads** (malware, scripts)
- **Storage exhaustion** via large files
- **Image processing exploits** (malformed images crashing Bedrock)
- **Path traversal** via crafted filenames

**Recommendation**:
```python
import magic  # python-magic library
from PIL import Image

def validate_image_upload(file_data: bytes, filename: str) -> tuple[bool, str]:
    """Validate uploaded image file."""
    
    # 1. Check file size (max 10MB)
    MAX_SIZE = 10 * 1024 * 1024
    if len(file_data) > MAX_SIZE:
        return False, "File too large (max 10MB)"
    
    # 2. Validate MIME type using magic bytes
    mime = magic.from_buffer(file_data, mime=True)
    ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/heic']
    if mime not in ALLOWED_TYPES:
        return False, f"Invalid file type: {mime}"
    
    # 3. Validate file extension
    ext = filename.lower().split('.')[-1]
    if ext not in ['jpg', 'jpeg', 'png', 'heic']:
        return False, f"Invalid file extension: {ext}"
    
    # 4. Verify image can be opened (prevents malformed images)
    try:
        img = Image.open(io.BytesIO(file_data))
        img.verify()
    except Exception as e:
        return False, f"Invalid image file: {str(e)}"
    
    # 5. Sanitize filename
    safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    
    return True, safe_filename
```

---

#### 7. No Rate Limiting Per User/Session
**Location**: `infrastructure/cloudformation/api-gateway.yaml:60-65`  
**Severity**: HIGH  
**CWE**: CWE-770 (Allocation of Resources Without Limits)

**Description**:
Rate limiting is configured globally but not per user/session:
```yaml
Throttle:
  BurstLimit: 20
  RateLimit: 100
Quota:
  Limit: 10000
  Period: DAY
```

**Impact**:
- Single user can exhaust quota for all users
- No protection against per-user abuse
- Expensive Bedrock API calls can be triggered repeatedly
- DoS via resource exhaustion

**Recommendation**:
```python
# Implement per-session rate limiting in Lambda
from datetime import datetime, timedelta
import boto3

dynamodb = boto3.resource('dynamodb')
rate_limit_table = dynamodb.Table('kitchen-agent-rate-limits')

def check_rate_limit(session_id: str, endpoint: str) -> bool:
    """Check if session has exceeded rate limit."""
    
    # Define limits per endpoint
    LIMITS = {
        '/chat': {'requests': 50, 'window': 3600},  # 50 per hour
        '/analyze-image': {'requests': 10, 'window': 3600},  # 10 per hour
        '/generate-recipes': {'requests': 20, 'window': 3600},  # 20 per hour
    }
    
    limit_config = LIMITS.get(endpoint, {'requests': 100, 'window': 3600})
    
    # Get current request count
    response = rate_limit_table.get_item(
        Key={'session_id': session_id, 'endpoint': endpoint}
    )
    
    if 'Item' in response:
        item = response['Item']
        window_start = datetime.fromisoformat(item['window_start'])
        request_count = item['request_count']
        
        # Check if window expired
        if datetime.utcnow() - window_start > timedelta(seconds=limit_config['window']):
            # Reset window
            request_count = 0
            window_start = datetime.utcnow()
        
        # Check limit
        if request_count >= limit_config['requests']:
            return False  # Rate limit exceeded
        
        # Increment count
        rate_limit_table.update_item(
            Key={'session_id': session_id, 'endpoint': endpoint},
            UpdateExpression='SET request_count = request_count + :inc',
            ExpressionAttributeValues={':inc': 1}
        )
    else:
        # First request in window
        rate_limit_table.put_item(Item={
            'session_id': session_id,
            'endpoint': endpoint,
            'request_count': 1,
            'window_start': datetime.utcnow().isoformat()
        })
    
    return True  # Within limit
```

---

### 🟡 MEDIUM SEVERITY

#### 8. Sensitive Data in Logs
**Location**: Multiple files - all logger.info/error calls  
**Severity**: MEDIUM  
**CWE**: CWE-532 (Insertion of Sensitive Information into Log File)

**Description**:
Logs contain potentially sensitive information:
- Session IDs
- User preferences (dietary restrictions)
- Allergies
- Recipe details
- Shopping lists
- Error messages with stack traces

**Examples**:
```python
logger.info(f"Retrieved user preferences: session_id={session_id}, preferences={preferences}")
logger.info(f"Retrieved user allergies: session_id={session_id}, allergies={allergies}")
```

**Impact**:
- Privacy violations if logs are compromised
- Compliance issues (GDPR, HIPAA for health data)
- Information disclosure to unauthorized personnel

**Recommendation**:
```python
def sanitize_for_logging(data: dict) -> dict:
    """Remove sensitive fields from log data."""
    SENSITIVE_FIELDS = ['allergies', 'preferences', 'email', 'phone']
    return {k: '[REDACTED]' if k in SENSITIVE_FIELDS else v 
            for k, v in data.items()}

# Use in logging
logger.info(
    f"Retrieved user profile: session_id={session_id}, "
    f"data={sanitize_for_logging(profile_data)}"
)
```

---

#### 9. No SQL Injection Protection for DynamoDB
**Location**: `src/kitchen_agent_core.py`, `src/reminder_service.py`, `src/shopping_optimizer.py`  
**Severity**: MEDIUM  
**CWE**: CWE-943 (Improper Neutralization of Special Elements in Data Query Logic)

**Description**:
DynamoDB queries use user-provided values without validation:

```python
# Potentially vulnerable
response = self.sessions_table.get_item(
    Key={
        'session_id': session_id,  # User-provided, not validated
        'data_type': 'profile'
    }
)
```

While DynamoDB's parameterized queries provide some protection, lack of input validation can still cause issues.

**Impact**:
- Unexpected query behavior
- Data leakage via crafted session IDs
- DoS via malformed queries

**Recommendation**:
```python
# Validate all DynamoDB key values
def validate_dynamodb_key(key: str, key_name: str) -> str:
    """Validate DynamoDB key format."""
    # Remove special characters that could cause issues
    if not re.match(r'^[a-zA-Z0-9_-]{1,255}$', key):
        raise ValueError(f"Invalid {key_name} format")
    return key

# Use in queries
session_id = validate_dynamodb_key(session_id, 'session_id')
response = self.sessions_table.get_item(
    Key={'session_id': session_id, 'data_type': 'profile'}
)
```

---

#### 10. Missing HTTPS Enforcement in Streamlit App
**Location**: `app.py`  
**Severity**: MEDIUM  
**CWE**: CWE-319 (Cleartext Transmission of Sensitive Information)

**Description**:
Streamlit app doesn't enforce HTTPS connections. Configuration depends on deployment environment.

**Impact**:
- Session cookies transmitted over HTTP
- User inputs (messages, preferences) sent in cleartext
- MITM attacks on frontend-backend communication

**Recommendation**:
```python
# Add to app.py
import streamlit as st

# Force HTTPS redirect
if st.get_option('server.enableXsrfProtection'):
    # Check if request is HTTP
    if not st.session_state.get('https_checked'):
        st.session_state.https_checked = True
        # Add warning if not HTTPS
        if 'https' not in st.get_option('server.baseUrlPath'):
            st.warning("⚠️ This app should be accessed via HTTPS for security")
```

**Deployment Configuration**:
```toml
# .streamlit/config.toml
[server]
enableXsrfProtection = true
enableCORS = false
cookieSecret = "your-secret-key-here"  # Generate securely

[browser]
serverAddress = "yourdomain.com"
serverPort = 443
```

---

### 🟢 LOW SEVERITY

#### 11. Hardcoded AWS Region
**Location**: `config/env.py`  
**Severity**: LOW  
**CWE**: CWE-547 (Use of Hard-coded, Security-relevant Constants)

**Description**:
AWS regions are hardcoded in configuration:
```python
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
BEDROCK_REGION = os.getenv('BEDROCK_REGION', 'us-east-1')
```

**Impact**:
- Limited flexibility for multi-region deployments
- Potential compliance issues if data must stay in specific regions

**Recommendation**:
- Ensure environment variables are set in production
- Document region requirements
- Consider multi-region support for disaster recovery

---

#### 12. Missing Security Headers
**Location**: `src/api_handler.py:create_response()`  
**Severity**: LOW  
**CWE**: CWE-693 (Protection Mechanism Failure)

**Description**:
API responses don't include security headers:
- No `X-Content-Type-Options`
- No `X-Frame-Options`
- No `Content-Security-Policy`
- No `Strict-Transport-Security`

**Impact**:
- Increased XSS risk
- Clickjacking vulnerability
- MIME-sniffing attacks

**Recommendation**:
```python
def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create API Gateway response with security headers."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': 'https://yourdomain.com',  # Not '*'
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        },
        'body': json.dumps(body)
    }
```

---

## Additional Security Concerns

### 1. No Secrets Management
**Observation**: No evidence of AWS Secrets Manager or Parameter Store usage for sensitive configuration.

**Recommendation**:
- Store API keys, database credentials in AWS Secrets Manager
- Rotate secrets regularly
- Use IAM roles instead of access keys where possible

### 2. No Encryption at Rest Configuration
**Observation**: DynamoDB tables don't explicitly enable encryption at rest in code.

**Recommendation**:
```python
# Enable encryption for DynamoDB tables
table = dynamodb.create_table(
    TableName='kitchen-agent-sessions',
    SSESpecification={
        'Enabled': True,
        'SSEType': 'KMS',  # Use AWS KMS
        'KMSMasterKeyId': 'your-kms-key-id'
    },
    # ... other configuration
)
```

### 3. No Security Monitoring/Alerting
**Observation**: No CloudWatch alarms for security events.

**Recommendation**:
- Set up CloudWatch alarms for:
  - Failed authentication attempts
  - Unusual API call patterns
  - DynamoDB throttling (potential DoS)
  - Lambda errors
  - S3 unauthorized access attempts

### 4. Lambda Function Permissions
**Observation**: Lambda IAM roles not reviewed (not in provided code).

**Recommendation**:
- Follow principle of least privilege
- Separate IAM roles per Lambda function
- Restrict S3 bucket access to specific prefixes
- Limit DynamoDB actions to required operations only

---

## Compliance Considerations

### GDPR (General Data Protection Regulation)
**Concerns**:
- User data (allergies, preferences) stored without explicit consent mechanism
- No data retention policy visible
- No data deletion/export functionality
- Logs contain personal data

**Recommendations**:
1. Implement consent management
2. Add data export endpoint (GDPR Article 20)
3. Add data deletion endpoint (GDPR Article 17)
4. Document data retention policies
5. Implement audit logging for data access

### HIPAA (Health Information)
**Concerns**:
- Allergy information could be considered health data
- No encryption in transit enforcement
- Logs contain health-related data

**Recommendations**:
1. Enforce HTTPS everywhere
2. Encrypt all data at rest
3. Implement access controls
4. Enable audit logging
5. Sign Business Associate Agreement (BAA) with AWS

---

## Remediation Priority

### Immediate (Before Production)
1. ✅ **Fix HTTP/HTTPS issue** (CRITICAL #1)
2. ✅ **Implement authentication** (CRITICAL #2)
3. ✅ **Restrict CORS origins** (HIGH #3)
4. ✅ **Add input validation** (HIGH #4)
5. ✅ **Restrict IP access** (HIGH #5)

### Short Term (Within 1 Month)
6. ✅ **Implement file upload validation** (HIGH #6)
7. ✅ **Add per-user rate limiting** (HIGH #7)
8. ✅ **Sanitize logs** (MEDIUM #8)
9. ✅ **Add DynamoDB input validation** (MEDIUM #9)

### Medium Term (Within 3 Months)
10. ✅ **Enforce HTTPS in Streamlit** (MEDIUM #10)
11. ✅ **Add security headers** (LOW #12)
12. ✅ **Implement secrets management**
13. ✅ **Enable encryption at rest**
14. ✅ **Set up security monitoring**

---

## Testing Recommendations

### Security Testing Checklist
- [ ] Penetration testing by third party
- [ ] OWASP ZAP automated scan
- [ ] SQL/NoSQL injection testing
- [ ] XSS testing on all input fields
- [ ] CSRF testing
- [ ] Authentication bypass attempts
- [ ] Authorization testing (horizontal/vertical privilege escalation)
- [ ] Rate limiting verification
- [ ] File upload security testing
- [ ] API fuzzing

### Tools Recommended
- **OWASP ZAP**: Web application security scanner
- **Burp Suite**: Manual penetration testing
- **AWS Inspector**: Automated security assessment
- **AWS GuardDuty**: Threat detection
- **Snyk**: Dependency vulnerability scanning
- **Bandit**: Python security linter

---

## Secure Development Practices

### Code Review Checklist
- [ ] All user inputs validated and sanitized
- [ ] Authentication required for all endpoints
- [ ] Authorization checks for data access
- [ ] HTTPS enforced everywhere
- [ ] Secrets not hardcoded
- [ ] Error messages don't leak sensitive info
- [ ] Logging doesn't contain PII
- [ ] Rate limiting implemented
- [ ] Security headers present

### Dependency Management
```bash
# Check for vulnerable dependencies
pip install safety
safety check --json

# Update requirements.txt with pinned versions
pip freeze > requirements.txt
```

---

## Conclusion

The Andhra Kitchen Agent has **significant security vulnerabilities** that must be addressed before production deployment. The most critical issues are:

1. **Lack of authentication** - Anyone can access all data
2. **HTTP allowed** - Data transmitted in cleartext
3. **No input validation** - Vulnerable to injection attacks

**Estimated Remediation Effort**: 2-3 weeks for critical issues, 1-2 months for complete security hardening.

**Risk Assessment**: 
- **Current State**: HIGH RISK - Not suitable for production
- **After Critical Fixes**: MEDIUM RISK - Acceptable for beta/staging
- **After All Fixes**: LOW RISK - Production ready

---

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [AWS Security Best Practices](https://aws.amazon.com/security/best-practices/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

**Report Generated**: 2026-03-13  
**Next Review**: After remediation (recommended within 30 days)
