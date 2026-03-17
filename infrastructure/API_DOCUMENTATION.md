# Andhra Kitchen Agent - API Documentation

## Overview

The Andhra Kitchen Agent REST API provides endpoints for managing kitchen assistant functionality including chat, image analysis, recipe generation, shopping lists, and reminders.

**Base URL**: `https://{api-id}.execute-api.{region}.amazonaws.com/v1`

**Authentication**: `Authorization: Bearer <Cognito ID token>` is required on all application endpoints.

**Rate Limiting**: 100 requests/minute per session, burst limit of 20 requests

## Common Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Missing or invalid bearer token |
| 403 | Forbidden - Authenticated user does not own the resource |
| 404 | Not Found |
| 413 | Payload Too Large |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |

## Rate Limiting

All authenticated application responses include:
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`

When rate limit is exceeded, the API also returns:
- **Status Code**: 429
- **Headers**: `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- **Response**: `{"error": "rate_limit_exceeded", "retry_after_seconds": 60, ...}`

If the rate limiter backend is unavailable in production, the API fails closed with:
- **Status Code**: 503
- **Headers**: `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- **Response**: `{"error": "service_unavailable", ...}`

## Request Size Limits

- JSON requests larger than `1 MB` are rejected with `413 Payload Too Large`
- Upload requests larger than `14 MB` encoded payload size are rejected before parsing
- Image files larger than `10 MB` are rejected with `413 Payload Too Large`

---

## Endpoints

### 1. POST /session

Create a new user session.

**Headers**:
- `Authorization: Bearer <Cognito ID token>`

**Request**:
```json
{
  "language": "en"  // Optional: "en" or "te", defaults to "en"
}
```

**Response** (201):
```json
{
  "session_id": "sess_a1b2c3d4e5f6",
  "created_at": "2024-01-15T10:30:00Z",
  "expires_at": "2024-01-22T10:30:00Z",
  "user_language": "en"
}
```

**Error Codes**:
- 400: Invalid language parameter
- 401: Missing or invalid bearer token
- 500: Session creation failed

---

### 2. GET /session/{session_id}

Retrieve session data.

**Headers**:
- `Authorization: Bearer <Cognito ID token>`

**Path Parameters**:
- `session_id` (required): Session identifier

**Response** (200):
```json
{
  "session_id": "sess_a1b2c3d4e5f6",
  "user_language": "en",
  "preferences": {
    "dietary": "vegetarian",
    "spice_level": "medium"
  },
  "allergies": ["peanuts", "shellfish"],
  "conversation_history": [
    {
      "user_message": "I want to cook biryani",
      "agent_response": "Great! Let me help you...",
      "timestamp": "2024-01-15T10:35:00Z"
    }
  ],
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z"
}
```

**Error Codes**:
- 401: Missing or invalid bearer token
- 403: Session belongs to another authenticated user
- 404: Session not found
- 500: Database error

---

### 3. POST /chat

Send a chat message to the agent.

**Headers**:
- `Authorization: Bearer <Cognito ID token>`

**Request**:
```json
{
  "session_id": "sess_a1b2c3d4e5f6",
  "message": "I want to cook something with tomatoes",
  "language": "en",  // Optional: "en" or "te"
  "context": {}      // Optional: Additional context
}
```

**Response** (200):
```json
{
  "response": "I can help you make delicious tomato-based dishes! Do you have any other ingredients?",
  "suggested_actions": [
    "upload_image",
    "generate_recipes"
  ],
  "language": "en",
  "timestamp": "2024-01-15T10:35:00Z"
}
```

**Error Codes**:
- 400: Missing required fields (session_id, message)
- 401: Missing or invalid bearer token
- 403: Session belongs to another authenticated user
- 429: Rate limit exceeded
- 500: AgentCore invocation failed

---

### 4. POST /upload-image

Upload an image for ingredient detection.

**Headers**:
- `Authorization: Bearer <Cognito ID token>`

**Request** (multipart/form-data):
- `file`: Image file (JPEG, PNG, or HEIC)
- `session_id`: Session identifier

JSON uploads are also supported with base64-encoded `image_data` plus `content_type`.

**File Constraints**:
- Max size: 10 MB
- Formats: JPEG, PNG, HEIC

**Response** (200):
```json
{
  "session_id": "sess_a1b2c3d4e5f6",
  "image_id": "img_x1y2z3a4b5c6",
  "s3_url": "https://bucket.s3.amazonaws.com/...",
  "s3_key": "sess_a1b2c3d4e5f6/img_x1y2z3a4b5c6.jpg",
  "timestamp": "2024-01-15T10:40:00Z"
}
```

`s3_url` and `s3_key` remain in the response for compatibility but are deprecated. Clients must not send them back to `POST /analyze-image`.

**Error Codes**:
- 400: Invalid file format or size exceeded
- 401: Missing or invalid bearer token
- 403: Session belongs to another authenticated user
- 413: Payload too large (>10MB)
- 500: S3 upload failed

---

### 5. POST /analyze-image

Analyze uploaded image to detect ingredients.

**Headers**:
- `Authorization: Bearer <Cognito ID token>`

**Request**:
```json
{
  "session_id": "sess_a1b2c3d4e5f6",
  "image_id": "img_x1y2z3a4b5c6",
  "language": "en"  // Optional
}
```

**Response** (200):
```json
{
  "inventory": {
    "total_items": 5,
    "detection_timestamp": "2024-01-15T10:42:00Z",
    "ingredients": [
      {
        "ingredient_name": "Tomato",
        "quantity": 3,
        "unit": "pieces",
        "confidence_score": 0.95,
        "category": "vegetables"
      },
      {
        "ingredient_name": "Onion",
        "quantity": 2,
        "unit": "pieces",
        "confidence_score": 0.88,
        "category": "vegetables"
      }
    ]
  },
  "analysis_time_seconds": 8.5
}
```

**Confidence Score Interpretation**:
- `>= 0.7`: High confidence (automatically included)
- `0.5 - 0.7`: Medium confidence (flagged for user confirmation)
- `< 0.5`: Low confidence (excluded)

**Error Codes**:
- 400: Missing required fields or invalid image_id
- 401: Missing or invalid bearer token
- 403: Session or image belongs to another authenticated user
- 500: Vision analysis failed
- 504: Analysis timeout (>30 seconds)

---

### 6. POST /generate-recipes

Generate recipes based on available ingredients.

**Headers**:
- `Authorization: Bearer <Cognito ID token>`

**Request**:
```json
{
  "session_id": "sess_a1b2c3d4e5f6",
  "inventory": {
    "ingredients": [
      {"ingredient_name": "Tomato", "quantity": 3, "unit": "pieces"},
      {"ingredient_name": "Onion", "quantity": 2, "unit": "pieces"}
    ]
  },
  "preferences": {
    "dietary": "vegetarian",
    "low_oil": true
  },
  "allergies": ["peanuts"],
  "language": "en",
  "count": 3  // Optional: 2-5, defaults to 3
}
```

**Response** (200):
```json
{
  "recipes": [
    {
      "recipe_id": "recipe_abc123",
      "name": "Tomato Curry",
      "name_telugu": "టమాటో కూర",
      "ingredients": [
        {
          "name": "Tomato",
          "name_telugu": "టమాటో",
          "quantity": 3,
          "unit": "pieces"
        }
      ],
      "steps": [
        "Heat oil in a pan",
        "Add chopped onions and sauté",
        "Add tomatoes and cook until soft"
      ],
      "prep_time_minutes": 30,
      "servings": 4,
      "nutrition": {
        "calories": 120,
        "protein_g": 3,
        "carbohydrates_g": 18,
        "fat_g": 5,
        "fiber_g": 4
      },
      "estimated_cost_inr": 25,
      "cooking_method": "sautéing",
      "low_oil": true
    }
  ],
  "generation_time_seconds": 12.3
}
```

**Error Codes**:
- 400: Invalid inventory or parameters
- 401: Missing or invalid bearer token
- 403: Session belongs to another authenticated user
- 500: Recipe generation failed
- 503: Bedrock service unavailable

---

### 7. POST /generate-shopping-list

Generate shopping list for a recipe.

**Headers**:
- `Authorization: Bearer <Cognito ID token>`

**Request**:
```json
{
  "session_id": "sess_a1b2c3d4e5f6",
  "recipe_id": "recipe_abc123",
  "current_inventory": {
    "ingredients": [
      {"ingredient_name": "Tomato", "quantity": 1, "unit": "pieces"}
    ]
  },
  "language": "en"
}
```

**Response** (200):
```json
{
  "shopping_list": {
    "list_id": "list_xyz789",
    "recipe_id": "recipe_abc123",
    "items": [
      {
        "ingredient_name": "Tomato",
        "ingredient_name_telugu": "టమాటో",
        "quantity": 2,
        "unit": "pieces",
        "estimated_price_inr": 10,
        "market_section": "Vegetables"
      },
      {
        "ingredient_name": "Onion",
        "ingredient_name_telugu": "ఉల్లిపాయ",
        "quantity": 2,
        "unit": "pieces",
        "estimated_price_inr": 8,
        "market_section": "Vegetables"
      }
    ],
    "total_cost_inr": 18,
    "grouped_by_section": {
      "Vegetables": ["Tomato", "Onion"],
      "Spices": ["Turmeric", "Chili Powder"]
    }
  },
  "reminders": [
    {
      "reminder_id": "rem_123abc",
      "content": "Tomato prices may drop tomorrow",
      "reason": "price_sensitive",
      "trigger_time": "2024-01-16T10:00:00Z"
    }
  ]
}
```

**Error Codes**:
- 400: Invalid recipe_id or inventory
- 401: Missing or invalid bearer token
- 403: Session belongs to another authenticated user
- 404: Recipe not found
- 500: Shopping list generation failed

---

### 8. GET /reminders/{session_id}

Get pending reminders for a session.

**Headers**:
- `Authorization: Bearer <Cognito ID token>`

**Path Parameters**:
- `session_id` (required): Session identifier

**Response** (200):
```json
{
  "reminders": [
    {
      "reminder_id": "rem_123abc",
      "session_id": "sess_a1b2c3d4e5f6",
      "content": "Tomato prices may drop tomorrow",
      "reason": "price_sensitive",
      "status": "pending",
      "trigger_time": "2024-01-16T10:00:00Z",
      "created_at": "2024-01-15T10:45:00Z"
    }
  ]
}
```

**Reminder Status**:
- `pending`: Not yet triggered
- `delivered`: Triggered and shown to user
- `dismissed`: User dismissed the reminder
- `snoozed`: User snoozed the reminder

**Error Codes**:
- 401: Missing or invalid bearer token
- 403: Session belongs to another authenticated user
- 404: Session not found
- 500: Database query failed

---

### 9. POST /reminders/{reminder_id}/dismiss

Dismiss a reminder.

**Path Parameters**:
- `reminder_id` (required): Reminder identifier

**Headers**:
- `Authorization: Bearer <Cognito ID token>`

**Request**:
```json
{
  "session_id": "sess_a1b2c3d4e5f6"
}
```

**Response** (200):
```json
{
  "reminder_id": "rem_123abc",
  "status": "dismissed",
  "dismissed_at": "2024-01-15T11:00:00Z"
}
```

**Error Codes**:
- 401: Missing or invalid bearer token
- 403: Session belongs to another authenticated user
- 404: Reminder not found
- 500: Update failed

---

### 10. POST /reminders/{reminder_id}/snooze

Snooze a reminder for a specified duration.

**Path Parameters**:
- `reminder_id` (required): Reminder identifier

**Headers**:
- `Authorization: Bearer <Cognito ID token>`

**Request**:
```json
{
  "session_id": "sess_a1b2c3d4e5f6",
  "duration_hours": 24  // Required: 1-168 (1 week)
}
```

**Response** (200):
```json
{
  "reminder_id": "rem_123abc",
  "status": "snoozed",
  "new_trigger_time": "2024-01-16T11:00:00Z",
  "snoozed_at": "2024-01-15T11:00:00Z"
}
```

**Error Codes**:
- 400: Invalid duration_hours
- 401: Missing or invalid bearer token
- 403: Session belongs to another authenticated user
- 404: Reminder not found
- 500: Update failed

---

## Error Response Format

All error responses follow this format:

```json
{
  "error": "Error message",
  "error_code": "specific_error_code",
  "timestamp": "2024-01-15T10:00:00Z",
  "request_id": "req_abc123xyz"
}
```

## Common Error Codes

| Code | Description | Retry? |
|------|-------------|--------|
| `invalid_session` | Session not found or expired | No |
| `invalid_parameters` | Missing or invalid request parameters | No |
| `rate_limit_exceeded` | Too many requests | Yes (after delay) |
| `image_too_large` | Image exceeds 10MB limit | No |
| `invalid_image_format` | Unsupported image format | No |
| `vision_analysis_failed` | Image analysis error | Yes |
| `recipe_generation_failed` | Recipe generation error | Yes |
| `insufficient_ingredients` | Not enough ingredients for recipes | No |
| `bedrock_unavailable` | Bedrock service error | Yes |
| `database_error` | DynamoDB operation failed | Yes |
| `s3_upload_failed` | S3 upload error | Yes |

---

## Usage Examples

### Complete Workflow Example

```bash
# 1. Create session
curl -X POST https://api-id.execute-api.region.amazonaws.com/v1/session \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <COGNITO_ID_TOKEN>" \
  -d '{"language": "en"}'

# Response: {"session_id": "sess_abc123", ...}

# 2. Upload image
curl -X POST https://api-id.execute-api.region.amazonaws.com/v1/upload-image \
  -H "Authorization: Bearer <COGNITO_ID_TOKEN>" \
  -F "file=@kitchen.jpg" \
  -F "session_id=sess_abc123"

# Response: {"image_id": "img_xyz789", "s3_url": "...", "s3_key": "...", ...}

# 3. Analyze image
curl -X POST https://api-id.execute-api.region.amazonaws.com/v1/analyze-image \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <COGNITO_ID_TOKEN>" \
  -d '{
    "session_id": "sess_abc123",
    "image_id": "img_xyz789",
    "language": "en"
  }'

# Response: {"inventory": {...}, ...}

# 4. Generate recipes
curl -X POST https://api-id.execute-api.region.amazonaws.com/v1/generate-recipes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <COGNITO_ID_TOKEN>" \
  -d '{
    "session_id": "sess_abc123",
    "inventory": {...},
    "language": "en",
    "count": 3
  }'

# Response: {"recipes": [...], ...}

# 5. Generate shopping list
curl -X POST https://api-id.execute-api.region.amazonaws.com/v1/generate-shopping-list \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <COGNITO_ID_TOKEN>" \
  -d '{
    "session_id": "sess_abc123",
    "recipe_id": "recipe_abc123",
    "current_inventory": {...},
    "language": "en"
  }'

# Response: {"shopping_list": {...}, "reminders": [...]}
```

---

## Best Practices

1. **Session Management**:
   - Sign in and obtain a Cognito ID token before calling the API
   - Create a session at app start
   - Store session_id in client storage
   - Sessions expire after 7 days of inactivity

2. **Error Handling**:
   - Always check response status codes
   - Implement retry logic for 5xx errors
   - Show user-friendly error messages

3. **Rate Limiting**:
   - Implement client-side rate limiting
   - Handle 429 responses with exponential backoff
   - Cache responses when appropriate

4. **Image Upload**:
   - Validate file size client-side (<10MB)
   - Validate file format (JPEG, PNG, HEIC)
   - Show upload progress to users

5. **Language Support**:
   - Detect user language preference
   - Pass language parameter consistently
   - Display content in user's language

---

## Testing

Use the provided Postman collection or curl commands to test endpoints.

**Test Session ID**: Use any valid session_id from POST /session

**Test Image**: Use sample images from `tests/fixtures/`

---

## Support

For API issues or questions:
- Check CloudWatch logs for detailed error information
- Review the deployment guide for configuration issues
- Ensure all AWS services are properly configured

---

## Changelog

### v1.0.0 (2024-01-15)
- Initial API release
- All 10 endpoints implemented
- Rate limiting enabled
- CORS configured
- Request validation enabled
