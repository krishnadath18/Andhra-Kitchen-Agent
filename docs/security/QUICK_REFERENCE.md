# Security Quick Reference Card
**For Developers Working on Andhra Kitchen Agent**

---

## 🚨 Security Rules (MUST FOLLOW)

### 1. Always Validate User Input
```python
from src.security_utils import validate_session_id, sanitize_user_input

# Validate session IDs
session_id = validate_session_id(user_input)

# Sanitize text input
message = sanitize_user_input(user_message, max_length=5000)
```

### 2. Never Log Sensitive Data
```python
from src.security_utils import sanitize_for_logging

# BAD ❌
logger.info(f"User data: {user_data}")

# GOOD ✅
logger.info(f"User data: {sanitize_for_logging(user_data)}")
```

### 3. Always Use HTTPS (Except Localhost)
```python
# Automatic enforcement in api_client.py
# Will raise ValueError for http://example.com
# Will allow http://localhost:5000
```

### 4. Use Security Headers
```python
from src.security_utils import create_secure_response_headers

# Automatic in create_response()
# No action needed - already implemented
```

---

## 📋 Validation Functions Available

### Session & User Input
```python
from src.security_utils import (
    validate_session_id,      # Validates session ID format
    validate_language,         # Validates language code (en/te)
    sanitize_user_input,       # Removes malicious content
)

# Usage
session_id = validate_session_id(raw_session_id)  # Raises ValueError if invalid
language = validate_language(raw_language)         # Raises ValueError if invalid
clean_text = sanitize_user_input(raw_text)        # Returns sanitized string
```

### Numeric Validation
```python
from src.security_utils import (
    validate_duration_hours,   # 0.1 to 168 hours
    validate_recipe_count,     # 1 to 10 recipes
)

# Usage
hours = validate_duration_hours(user_hours)        # Raises ValueError if invalid
count = validate_recipe_count(user_count)          # Raises ValueError if invalid
```

### Database & Files
```python
from src.security_utils import (
    validate_dynamodb_key,     # Prevents NoSQL injection
    validate_image_filename,   # Prevents path traversal
    validate_image_data,       # Validates file size
)

# Usage
safe_key = validate_dynamodb_key(user_key, 'session_id')
safe_filename = validate_image_filename(uploaded_filename)
validate_image_data(image_bytes, max_size_mb=10)  # Raises ValueError if invalid
```

---

## 🔒 Common Security Patterns

### Pattern 1: API Endpoint with Validation
```python
def handle_endpoint(event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        body = parse_request_body(event)
        
        # Validate required fields
        session_id = validate_session_id(body.get('session_id', ''))
        message = sanitize_user_input(body.get('message', ''))
        language = validate_language(body.get('language', 'en'))
        
        # Process request
        result = process_data(session_id, message, language)
        
        return create_response(200, {'result': result})
        
    except ValueError as e:
        return create_response(400, {'error': 'validation_error', 'message': str(e)})
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return create_response(500, {'error': 'internal_error'})
```

### Pattern 2: DynamoDB Query with Validation
```python
from src.security_utils import validate_dynamodb_key

def get_user_data(session_id: str) -> dict:
    # Validate before query
    safe_session_id = validate_dynamodb_key(session_id, 'session_id')
    
    response = dynamodb_table.get_item(
        Key={'session_id': safe_session_id, 'data_type': 'profile'}
    )
    
    return response.get('Item', {})
```

### Pattern 3: Logging with Sanitization
```python
from src.security_utils import sanitize_for_logging

def process_user_request(user_data: dict):
    # Sanitize before logging
    logger.info(f"Processing request: {sanitize_for_logging(user_data)}")
    
    # Process data
    result = do_processing(user_data)
    
    # Sanitize result before logging
    logger.info(f"Result: {sanitize_for_logging(result)}")
```

---

## ⚠️ Security Anti-Patterns (DON'T DO THIS)

### ❌ DON'T: Use User Input Directly
```python
# BAD - No validation
session_id = body.get('session_id')
query = f"SELECT * FROM users WHERE id = {session_id}"  # SQL injection risk
```

### ✅ DO: Validate First
```python
# GOOD - Validated
session_id = validate_session_id(body.get('session_id', ''))
# Now safe to use
```

---

### ❌ DON'T: Log Sensitive Data
```python
# BAD - Logs PII
logger.info(f"User allergies: {user_allergies}")
logger.info(f"User preferences: {user_preferences}")
```

### ✅ DO: Sanitize Logs
```python
# GOOD - Redacted
logger.info(f"User data: {sanitize_for_logging({'allergies': user_allergies})}")
```

---

### ❌ DON'T: Allow HTTP for Remote URLs
```python
# BAD - Insecure
url = f"http://{remote_server}/api"
response = requests.get(url)
```

### ✅ DO: Use HTTPS
```python
# GOOD - Secure (enforced automatically in api_client.py)
url = f"https://{remote_server}/api"
response = requests.get(url)
```

---

### ❌ DON'T: Trust File Extensions
```python
# BAD - Can be spoofed
if filename.endswith('.jpg'):
    process_image(file_data)
```

### ✅ DO: Validate File Content
```python
# GOOD - Validates actual content
validate_image_data(file_data)
safe_filename = validate_image_filename(filename)
```

---

## 🧪 Testing Your Code

### Test Input Validation
```python
# Test that invalid input is rejected
try:
    validate_session_id("invalid'; DROP TABLE--")
    assert False, "Should have raised ValueError"
except ValueError:
    pass  # Expected

# Test that valid input is accepted
try:
    validate_session_id("sess_abc123")
except ValueError:
    assert False, "Should have accepted valid session_id"
```

### Test Log Sanitization
```python
from src.security_utils import sanitize_for_logging

data = {'session_id': 'sess_123', 'allergies': ['peanuts']}
sanitized = sanitize_for_logging(data)

assert sanitized['session_id'] == 'sess_123'
assert sanitized['allergies'] == '[REDACTED]'
```

### Run Built-in Tests
```bash
# Run security utils test suite
python src/security_utils.py

# Expected output:
# ✓ Valid session_id accepted
# ✓ Invalid session_id rejected (SQL injection)
# ✓ Sanitized input: 'HelloWorldTest'
# ✓ Sanitized logs: {...}
```

---

## 🚀 Production Checklist

Before deploying to production:

- [ ] All user inputs validated using security_utils functions
- [ ] All logs sanitized using sanitize_for_logging()
- [ ] HTTPS enforced (automatic in api_client.py)
- [ ] Security headers enabled (automatic in create_response())
- [ ] ALLOWED_ORIGIN configured for production domain
- [ ] Authentication deployed (see SECURITY_FIXES.md)
- [ ] Rate limiting implemented (see SECURITY_FIXES.md)
- [ ] Security testing completed

---

## 📚 Documentation

- **Full Details**: `SECURITY_FIXES.md`
- **Security Audit**: `SECURITY.md`
- **Implementation Summary**: `SECURITY_IMPLEMENTATION_SUMMARY.md`
- **Code Reference**: `src/security_utils.py`

---

## 🆘 Common Issues

### Issue: ValueError on valid session_id
**Cause**: Session ID contains invalid characters  
**Fix**: Only use alphanumeric, underscores, hyphens (max 64 chars)

### Issue: HTTP connection rejected
**Cause**: Trying to use HTTP for remote URL  
**Fix**: Use HTTPS or localhost for development

### Issue: CORS error in browser
**Cause**: ALLOWED_ORIGIN not configured  
**Fix**: Set `ALLOWED_ORIGIN=https://yourdomain.com` in environment

---

## 💡 Pro Tips

1. **Always validate at the boundary** - Validate input as soon as it enters your system
2. **Fail securely** - Return generic error messages, log details internally
3. **Use type hints** - Helps catch errors early: `def func(session_id: str) -> dict:`
4. **Test edge cases** - Empty strings, null bytes, very long inputs, special characters
5. **Review security_utils.py** - See examples of proper validation patterns

---

**Last Updated**: 2026-03-13  
**Version**: 1.0  
**For Questions**: See FIXES.md or README.md
