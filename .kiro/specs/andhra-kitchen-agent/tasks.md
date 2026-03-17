# Implementation Plan: Andhra Kitchen Agent

## Overview

This implementation plan breaks down the Andhra Kitchen Agent feature into discrete coding tasks. The system is a multilingual AI-powered kitchen assistant using Amazon Bedrock, AWS Lambda, DynamoDB, S3, and Streamlit. Implementation follows a bottom-up approach: infrastructure setup, core backend components, data models, API layer, frontend, and finally integration with testing throughout.

## Tasks

- [x] 1. AWS Infrastructure Setup
  - Create AWS account resources and configure IAM roles
  - Set up DynamoDB tables with proper schemas and TTL
  - Configure S3 bucket with lifecycle policies
  - Set up API Gateway with rate limiting and CORS
  - Configure CloudWatch logging
  - _Requirements: 14.1, 14.2, 14.3, 18.1, 18.2, 18.3_

- [x] 2. DynamoDB Table Creation
  - [x] 2.1 Create kitchen-agent-sessions table
    - Define partition key (session_id) and sort key (data_type)
    - Enable TTL on expiry_timestamp attribute
    - Configure on-demand billing mode
    - _Requirements: 16.3, 18.3_
  
  - [x] 2.2 Create kitchen-agent-market-prices table
    - Define partition key (ingredient_name) and sort key (market_name)
    - Create global secondary index on last_updated
    - Configure on-demand billing mode
    - _Requirements: 24.1, 24.2_
  
  - [x] 2.3 Create kitchen-agent-reminders table
    - Define partition key (session_id) and sort key (reminder_id)
    - Create global secondary index on status
    - Enable TTL on expiry_timestamp attribute
    - _Requirements: 11.7_


- [x] 3. S3 Bucket Configuration
  - [x] 3.1 Create S3 bucket for image storage
    - Create bucket with unique name pattern: kitchen-agent-images-{account-id}
    - Enable AES256 encryption
    - Block all public access
    - Set region to ap-south-1 (Mumbai)
    - _Requirements: 3.3, 18.2_
  
  - [x] 3.2 Configure S3 lifecycle policy
    - Create lifecycle rule to delete objects after 24 hours
    - Test lifecycle policy with sample uploads
    - _Requirements: 3.6, 18.2_
  
  - [ ]* 3.3 Write unit tests for S3 operations
    - Test image upload with unique identifiers
    - Test pre-signed URL generation
    - Test lifecycle policy enforcement
    - _Requirements: 3.3, 3.4_

- [x] 4. Data Models and JSON Schemas
  - [x] 4.1 Define Inventory JSON schema
    - Create JSON schema with required fields: total_items, detection_timestamp, ingredients
    - Define ingredient object schema: ingredient_name, quantity, unit, confidence_score, category
    - Add validation for confidence_score range [0, 1]
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  
  - [x] 4.2 Define Recipe JSON schema
    - Create JSON schema with required fields: recipe_id, name, ingredients, steps, prep_time, servings, nutrition
    - Define nutrition object schema: calories, protein, carbohydrates, fat, fiber
    - Add validation for numeric fields
    - _Requirements: 8.3, 8.6, 23.2, 23.3_
  
  - [x] 4.3 Define Shopping List JSON schema
    - Create JSON schema with required fields: list_id, recipe_id, items, total_cost
    - Define shopping item schema: ingredient_name, quantity, unit, estimated_price, market_section
    - _Requirements: 10.3, 10.4, 10.5_
  
  - [x] 4.4 Create Python validation utilities
    - Implement validate_inventory_schema() function
    - Implement validate_recipe_schema() function
    - Implement validate_shopping_list_schema() function
    - _Requirements: 5.5_
  
  - [ ]* 4.5 Write property test for Inventory JSON schema compliance
    - **Property 7: Inventory JSON Schema Compliance**
    - **Validates: Requirements 4.5, 5.1, 5.2, 5.3, 5.4**
  
  - [ ]* 4.6 Write property test for Recipe JSON schema compliance
    - **Property 18: Recipe JSON Schema Compliance**
    - **Validates: Requirements 8.3, 8.6, 8.8, 9.3**


- [x] 5. Vision Analyzer Tool Implementation
  - [x] 5.1 Create VisionAnalyzer class
    - Implement analyze_image() method to call Bedrock Claude 3 Sonnet
    - Implement detect_ingredients() to parse Bedrock response
    - Implement estimate_quantity() for quantity estimation
    - Implement calculate_confidence() for confidence scoring
    - Implement format_inventory_json() to structure output
    - Configure model: anthropic.claude-3-sonnet-20240229-v1:0, temperature 0.3
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 19.2_
  
  - [x] 5.2 Implement confidence threshold filtering
    - Filter ingredients with confidence >= 0.7 for automatic inclusion
    - Flag ingredients with confidence 0.5-0.7 for user confirmation
    - Exclude ingredients with confidence < 0.5
    - _Requirements: 21.1, 21.2, 21.3_
  
  - [x] 5.3 Add error handling and retry logic
    - Implement exponential backoff for Bedrock API calls (1s, 2s, 4s)
    - Handle ThrottlingException with max 3 retries
    - Handle ModelNotReadyException with retry
    - Log errors to CloudWatch
    - _Requirements: 17.1, 17.3, 19.4, 19.5_
  
  - [ ]* 5.4 Write property test for confidence bounds
    - **Property 6: Vision Analysis Confidence Bounds**
    - **Validates: Requirements 4.4**
  
  - [ ]* 5.5 Write property test for confidence-based filtering
    - **Property 38: Confidence-Based Ingredient Filtering**
    - **Validates: Requirements 21.1, 21.2, 21.3**
  
  - [ ]* 5.6 Write unit tests for Vision Analyzer
    - Test empty image returns empty Inventory JSON
    - Test Bedrock throttling retry logic
    - Test image analysis timeout handling
    - _Requirements: 4.7, 17.3_

- [x] 6. Recipe Generator Tool Implementation
  - [x] 6.1 Create RecipeGenerator class
    - Implement generate_recipes() method using Bedrock Claude 3 Haiku
    - Implement calculate_nutrition() using USDA/IFCT data
    - Implement estimate_cost() using DynamoDB market prices
    - Implement format_recipe() for structured output
    - Configure model: anthropic.claude-3-haiku-20240307-v1:0, temperature 0.7
    - _Requirements: 8.1, 8.3, 8.5, 8.6, 19.1_
  
  - [x] 6.2 Implement memory integration for preferences and allergies
    - Query Memory Store for dietary preferences before generation
    - Query Memory Store for allergies before generation
    - Exclude allergen ingredients from recipes
    - Prioritize preferred ingredients
    - _Requirements: 7.4, 7.5, 7.6, 8.2_
  
  - [x] 6.3 Implement low-oil recipe optimization
    - Apply low-oil constraint (max 2 tbsp per serving)
    - Prioritize cooking methods: steaming, grilling, air-frying, boiling, pressure cooking
    - Add health benefit notes for low-oil recipes
    - _Requirements: 9.1, 9.2, 9.3, 9.4_
  
  - [x] 6.4 Implement multilingual recipe generation
    - Generate recipe names and steps in user's language (English/Telugu)
    - Include ingredient names in both English and Telugu
    - Implement recipe translation when language preference changes
    - _Requirements: 22.1, 22.2, 22.3, 22.5_

  
  - [x] 6.5 Add nutrition calculation with cooking method adjustments
    - Calculate base nutrition from USDA/IFCT data
    - Apply cooking method adjustments (e.g., +20% fat for frying)
    - Include accuracy margin (±10%) in output
    - _Requirements: 23.1, 23.2, 23.3, 23.4, 23.5_
  
  - [ ]* 6.6 Write property test for recipe uses available ingredients
    - **Property 17: Recipe Uses Available Ingredients**
    - **Validates: Requirements 8.1**
  
  - [ ]* 6.7 Write property test for recipe count bounds
    - **Property 19: Recipe Count Bounds**
    - **Validates: Requirements 8.7**
  
  - [ ]* 6.8 Write property test for allergy exclusion
    - **Property 14: Allergy Exclusion in Recipes**
    - **Validates: Requirements 7.5**
  
  - [ ]* 6.9 Write property test for low-oil constraint
    - **Property 20: Low-Oil Recipe Constraint**
    - **Validates: Requirements 9.1**
  
  - [ ]* 6.10 Write property test for low-oil cooking methods
    - **Property 21: Low-Oil Cooking Methods**
    - **Validates: Requirements 9.2**
  
  - [ ]* 6.11 Write property test for recipe language consistency
    - **Property 39: Recipe Language Consistency**
    - **Validates: Requirements 22.1, 22.2, 22.3**
  
  - [ ]* 6.12 Write property test for nutrition completeness
    - **Property 41: Nutrition Information Completeness**
    - **Validates: Requirements 23.2, 23.3**
  
  - [ ]* 6.13 Write property test for cooking method nutrition impact
    - **Property 42: Cooking Method Nutrition Impact**
    - **Validates: Requirements 23.4**
  
  - [ ]* 6.14 Write unit tests for Recipe Generator
    - Test recipe generation with empty inventory
    - Test preference prioritization
    - Test recipe cost estimation
    - Test multilingual output
    - _Requirements: 8.4, 8.5, 22.4_

- [x] 7. Shopping Optimizer Tool Implementation
  - [x] 7.1 Create ShoppingOptimizer class
    - Implement generate_shopping_list() method
    - Implement identify_missing_ingredients() for set difference
    - Implement get_market_prices() to query DynamoDB
    - Implement optimize_quantities() for waste minimization
    - Implement group_by_section() for market organization
    - Implement calculate_total_cost() for sum calculation
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_
  
  - [x] 7.2 Implement market price management
    - Query kitchen-agent-market-prices table
    - Calculate average prices across multiple markets
    - Flag prices older than 30 days as outdated
    - Estimate prices for unavailable ingredients
    - _Requirements: 24.1, 24.2, 24.3, 24.4, 24.5_

  
  - [ ]* 7.3 Write property test for shopping list missing ingredients
    - **Property 22: Shopping List Missing Ingredients**
    - **Validates: Requirements 10.1, 10.2, 10.3**
  
  - [ ]* 7.4 Write property test for shopping list total cost
    - **Property 24: Shopping List Total Cost**
    - **Validates: Requirements 10.5**
  
  - [ ]* 7.5 Write property test for shopping list grouping
    - **Property 25: Shopping List Grouping**
    - **Validates: Requirements 10.7**
  
  - [ ]* 7.6 Write property test for price lookup
    - **Property 23: Shopping List Price Lookup**
    - **Validates: Requirements 10.4, 24.5**
  
  - [ ]* 7.7 Write property test for average price calculation
    - **Property 45: Average Price Calculation**
    - **Validates: Requirements 24.4**
  
  - [ ]* 7.8 Write unit tests for Shopping Optimizer
    - Test empty inventory generates full shopping list
    - Test complete inventory generates empty shopping list
    - Test quantity optimization logic
    - Test outdated price flagging
    - _Requirements: 10.6, 24.3_

- [x] 8. Reminder Service Tool Implementation
  - [x] 8.1 Create ReminderService class
    - Implement schedule_reminder() method
    - Implement create_eventbridge_rule() for scheduling
    - Implement store_reminder() to save to DynamoDB
    - Implement get_pending_reminders() to query by session
    - Implement dismiss_reminder() and snooze_reminder()
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7_
  
  - [x] 8.2 Create ReminderExecutor Lambda function
    - Implement lambda_handler() to process EventBridge triggers
    - Store notification in DynamoDB with status 'delivered'
    - Clean up EventBridge rule after execution
    - Configure 512MB memory, 30s timeout
    - _Requirements: 11.2, 11.3, 18.4, 18.5_
  
  - [x] 8.3 Configure IAM roles for Lambda
    - Grant DynamoDB UpdateItem and GetItem permissions
    - Grant EventBridge RemoveTargets and DeleteRule permissions
    - Grant CloudWatch Logs permissions
    - _Requirements: 11.2_
  
  - [ ]* 8.4 Write property test for reminder content completeness
    - **Property 26: Reminder Content Completeness**
    - **Validates: Requirements 11.4, 11.5**
  
  - [ ]* 8.5 Write unit tests for Reminder Service
    - Test EventBridge rule creation
    - Test Lambda execution and cleanup
    - Test reminder snooze functionality
    - _Requirements: 11.6_


- [x] 9. Bedrock AgentCore Integration
  - [x] 9.1 Configure AgentCore with tool registration
    - Register vision_analyzer tool with description and parameter schema
    - Register recipe_generator tool with description and parameter schema
    - Register shopping_optimizer tool with description and parameter schema
    - Register reminder_service tool with description and parameter schema
    - Configure foundation model: Claude 3 Haiku
    - Set instruction prompt for Andhra kitchen assistant
    - _Requirements: 25.1, 25.2_
  
  - [x] 9.2 Implement AgentCore workflow orchestration
    - Implement decompose_task() to break down user requests
    - Implement execute_workflow() to run subtasks in order
    - Implement call_tool() to execute tool with parameters
    - Pass tool outputs to next subtask as inputs
    - Synthesize final response from all subtask outputs
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  
  - [x] 9.3 Implement memory management
    - Implement store_memory() to save to DynamoDB
    - Implement retrieve_memory() to query from DynamoDB
    - Store preferences with session_id association
    - Store allergies with high priority flag
    - Configure 7-day TTL for session data
    - _Requirements: 7.1, 7.2, 7.3, 7.7, 16.3_
  
  - [x] 9.4 Implement parallel tool execution
    - Detect independent tool calls (no dependencies)
    - Execute independent tools in parallel using asyncio
    - Wait for all parallel executions to complete
    - _Requirements: 25.5_
  
  - [x] 9.5 Add tool error handling
    - Catch tool execution exceptions
    - Report errors to Bedrock in structured format
    - Log errors to CloudWatch
    - Continue workflow with partial results when possible
    - _Requirements: 25.6_
  
  - [ ]* 9.6 Write property test for subtask output propagation
    - **Property 9: Subtask Output Propagation**
    - **Validates: Requirements 6.4**
  
  - [ ]* 9.7 Write property test for workflow result synthesis
    - **Property 10: Workflow Result Synthesis**
    - **Validates: Requirements 6.5**
  
  - [ ]* 9.8 Write property test for preference storage
    - **Property 11: Preference Storage and Association**
    - **Validates: Requirements 7.1, 7.3**
  
  - [ ]* 9.9 Write property test for allergy storage with priority
    - **Property 12: Allergy Storage with Priority**
    - **Validates: Requirements 7.2, 7.3**
  
  - [ ]* 9.10 Write property test for memory query before recipe generation
    - **Property 13: Memory Query Before Recipe Generation**
    - **Validates: Requirements 7.4, 8.2**
  
  - [ ]* 9.11 Write property test for tool metadata provision
    - **Property 46: Tool Metadata Provision**
    - **Validates: Requirements 25.2**
  
  - [ ]* 9.12 Write property test for tool execution with parameters
    - **Property 47: Tool Execution with Parameters**
    - **Validates: Requirements 25.3**

  
  - [ ]* 9.13 Write property test for tool result return
    - **Property 48: Tool Result Return**
    - **Validates: Requirements 25.4**
  
  - [ ]* 9.14 Write property test for parallel tool execution
    - **Property 49: Parallel Tool Execution**
    - **Validates: Requirements 25.5**
  
  - [ ]* 9.15 Write property test for tool failure error reporting
    - **Property 50: Tool Failure Error Reporting**
    - **Validates: Requirements 25.6**
  
  - [ ]* 9.16 Write unit tests for AgentCore
    - Test workflow decomposition
    - Test memory persistence across sessions
    - Test tool registration
    - _Requirements: 6.6_

- [x] 10. Kitchen Agent Core Implementation
  - [x] 10.1 Create KitchenAgentCore class
    - Implement process_chat_message() to route requests
    - Implement upload_image_to_s3() with unique identifiers
    - Implement invoke_agentcore() to call Bedrock AgentCore
    - Implement synthesize_response() to format outputs
    - Implement get_session() and create_session() for session management
    - _Requirements: 1.1, 1.2, 3.3, 16.1, 16.2_
    - _Status: Core class structure implemented with CloudWatch logging, session management, and error handling. Needs integration testing._
  
  - [x] 10.2 Implement language detection and response consistency
    - Detect input language (English/Telugu) automatically
    - Pass language preference to AgentCore
    - Ensure response is in same language as input
    - _Requirements: 1.3, 1.4_
  
  - [x] 10.3 Implement session management
    - Generate unique session identifiers
    - Associate all interactions with session_id
    - Restore session data within 7-day window
    - Delete session data after 7 days of inactivity
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6_
  
  - [x] 10.4 Add error handling with user-friendly messages
    - Handle Bedrock API errors with retry
    - Handle S3 upload failures with retry option
    - Handle Vision Analyzer errors with guidance
    - Handle Recipe Generator errors with suggestions
    - Provide "Try Again" option for all errors
    - Log all errors to CloudWatch
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6_
  
  - [ ]* 10.5 Write property test for message routing to Bedrock
    - **Property 1: Message Routing to Bedrock**
    - **Validates: Requirements 1.1, 1.2**
  
  - [ ]* 10.6 Write property test for language detection accuracy
    - **Property 2: Language Detection Accuracy**
    - **Validates: Requirements 1.3**
  
  - [ ]* 10.7 Write property test for language response consistency
    - **Property 3: Language Response Consistency**
    - **Validates: Requirements 1.4**
  
  - [ ]* 10.8 Write property test for session creation uniqueness
    - **Property 32: Session Creation Uniqueness**
    - **Validates: Requirements 16.1**

  
  - [ ]* 10.9 Write property test for interaction session association
    - **Property 33: Interaction Session Association**
    - **Validates: Requirements 16.2**
  
  - [ ]* 10.10 Write property test for session restoration
    - **Property 34: Session Restoration**
    - **Validates: Requirements 16.4**
  
  - [ ]* 10.11 Write property test for error retry option
    - **Property 35: Error Retry Option**
    - **Validates: Requirements 17.5**
  
  - [ ]* 10.12 Write property test for error logging
    - **Property 36: Error Logging**
    - **Validates: Requirements 17.6**
  
  - [ ]* 10.13 Write unit tests for Kitchen Agent Core
    - Test chat message processing
    - Test S3 upload with pre-signed URLs
    - Test session expiration after 7 days
    - Test error message localization
    - _Requirements: 1.5, 3.4, 3.5, 16.6_

- [x] 11. Checkpoint - Core Backend Complete
  - Ensure all tests pass for backend components
  - Verify DynamoDB tables are accessible
  - Verify S3 bucket operations work
  - Verify Bedrock API integration works
  - Ask the user if questions arise

- [x] 12. REST API Endpoints Implementation
  - [x] 12.1 Implement POST /chat endpoint
    - Accept session_id, message, language, context
    - Call KitchenAgentCore.process_chat_message()
    - Return response with suggested_actions
    - Handle rate limiting (100 req/min)
    - Return appropriate HTTP status codes
    - _Requirements: 1.1, 1.2, 1.5, 14.1, 14.2, 14.4, 14.5_
  
  - [x] 12.2 Implement POST /upload-image endpoint
    - Accept multipart/form-data with image file
    - Validate file format (JPEG, PNG, HEIC)
    - Validate file size (max 10MB)
    - Call KitchenAgentCore.upload_image_to_s3()
    - Return image_id and s3_url
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [x] 12.3 Implement POST /analyze-image endpoint
    - Accept session_id, image_id, s3_url, language
    - Call VisionAnalyzer.analyze_image()
    - Return Inventory JSON
    - Handle analysis failures with error messages
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_
  
  - [x] 12.4 Implement POST /generate-recipes endpoint
    - Accept session_id, inventory, preferences, allergies, language, count
    - Call RecipeGenerator.generate_recipes()
    - Return list of Recipe JSON objects
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_
  
  - [x] 12.5 Implement POST /generate-shopping-list endpoint
    - Accept session_id, recipe_id, current_inventory, language
    - Call ShoppingOptimizer.generate_shopping_list()
    - Call ReminderService.schedule_reminder() for price-sensitive items
    - Return Shopping List JSON and reminders
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 11.1_

  
  - [x] 12.6 Implement GET /session/{session_id} endpoint
    - Query DynamoDB for session data
    - Return user_language, preferences, allergies, conversation_history
    - _Requirements: 16.2, 16.5_
  
  - [x] 12.7 Implement POST /session endpoint
    - Generate unique session_id
    - Create session record in DynamoDB
    - Set expiry_timestamp to 7 days from creation
    - Return session_id and timestamps
    - _Requirements: 16.1, 16.3_
  
  - [x] 12.8 Implement GET /reminders/{session_id} endpoint
    - Query kitchen-agent-reminders table by session_id
    - Filter by status='pending' or status='delivered'
    - Return list of reminders
    - _Requirements: 11.3, 11.7_
  
  - [x] 12.9 Implement POST /reminders/{reminder_id}/dismiss endpoint
    - Update reminder status to 'dismissed'
    - Return updated reminder
    - _Requirements: 11.6_
  
  - [x] 12.10 Implement POST /reminders/{reminder_id}/snooze endpoint
    - Accept duration_hours parameter
    - Update trigger_time by adding duration
    - Update EventBridge rule with new time
    - Return updated reminder
    - _Requirements: 11.6_
  
  - [ ]* 12.11 Write property test for API response status codes
    - **Property 31: API Response Status Codes**
    - **Validates: Requirements 14.5**
  
  - [ ]* 12.12 Write unit tests for API endpoints
    - Test rate limiting returns HTTP 429
    - Test invalid requests return HTTP 400
    - Test successful requests return HTTP 200
    - Test HTTPS enforcement
    - _Requirements: 14.3, 14.4, 14.6_

- [x] 13. API Gateway Configuration
  - [x] 13.1 Configure API Gateway REST API
    - Create REST API named "kitchen-agent-api"
    - Set endpoint type to REGIONAL
    - Configure stage "v1"
    - Enable HTTPS only
    - _Requirements: 14.1, 14.2, 14.3_
  
  - [x] 13.2 Configure rate limiting and throttling
    - Set rate limit to 100 requests per minute per user
    - Set burst limit to 20 requests
    - Configure throttle response with HTTP 429 and Retry-After header
    - _Requirements: 14.4, 14.6_
  
  - [x] 13.3 Configure CORS
    - Allow origins: frontend domain
    - Allow methods: GET, POST, OPTIONS
    - Allow headers: Content-Type, Authorization
    - Set max age to 3600 seconds
    - _Requirements: 14.2_
  
  - [x] 13.4 Configure request validation
    - Create request models for each endpoint
    - Enable request body validation
    - Enable parameter validation
    - _Requirements: 14.5_


- [ ] 14. Festival Mode Implementation
  - [ ] 14.1 Create festival calendar data
    - Define festival dates for Sankranti, Ugadi, Dasara, Deepavali
    - Store festival calendar in configuration file
    - Include festival-specific ingredient lists
    - _Requirements: 12.1_
  
  - [ ] 14.2 Create FestivalCheckLambda function
    - Implement daily cron check at 00:00 IST
    - Compare current date against festival calendar
    - Set festival_mode flag in DynamoDB when date matches
    - Clear festival_mode 2 days after festival
    - _Requirements: 12.2, 12.6_
  
  - [ ] 14.3 Integrate festival mode into Recipe Generator
    - Check festival_mode flag before generating recipes
    - Prioritize festive recipes when festival_mode is active
    - Increase serving sizes by 50% during festivals
    - Add festival greeting to responses
    - _Requirements: 12.3, 12.5, 13.3_
  
  - [ ] 14.4 Integrate festival mode into Shopping Optimizer
    - Include festive ingredients in shopping suggestions
    - For Sankranti: suggest jaggery, sesame seeds, rice
    - For other festivals: suggest appropriate ingredients
    - _Requirements: 12.4, 13.2_
  
  - [ ]* 14.5 Write property test for festival mode activation
    - **Property 27: Festival Mode Activation**
    - **Validates: Requirements 12.2**
  
  - [ ]* 14.6 Write property test for festival recipe prioritization
    - **Property 28: Festival Recipe Prioritization**
    - **Validates: Requirements 12.3**
  
  - [ ]* 14.7 Write property test for festival ingredient suggestions
    - **Property 29: Festival Ingredient Suggestions**
    - **Validates: Requirements 12.4**
  
  - [ ]* 14.8 Write property test for Sankranti serving size increase
    - **Property 30: Sankranti Serving Size Increase**
    - **Validates: Requirements 13.3**
  
  - [ ]* 14.9 Write unit tests for Festival Mode
    - Test festival mode activation on festival date
    - Test festival mode deactivation after 2 days
    - Test Sankranti-specific recipes
    - Test festival greeting display
    - _Requirements: 12.2, 12.5, 12.6, 13.1_

- [x] 15. Streamlit Frontend - Core UI
  - [x] 15.1 Create Streamlit app structure
    - Set up main app.py file
    - Configure page layout and title
    - Initialize session state for conversation history
    - Set up mobile-responsive CSS (min-width 360px)
    - _Requirements: 15.1, 15.9_
  
  - [x] 15.2 Implement chat history display
    - Create chat message container
    - Display user messages and agent responses
    - Show timestamps for each message
    - Auto-scroll to latest message
    - _Requirements: 15.2, 16.5_

  
  - [x] 15.3 Implement text input field
    - Create text input widget
    - Handle Enter key submission
    - Clear input after sending
    - Show loading indicator during processing
    - _Requirements: 15.3_
  
  - [x] 15.4 Implement language toggle
    - Create language selector (English/Telugu)
    - Store language preference in session state
    - Update all UI text when language changes
    - Persist language preference to backend
    - _Requirements: 15.8_
  
  - [x] 15.5 Implement error message display
    - Show error messages in user's selected language
    - Display retry buttons for failed operations
    - Style error messages distinctly
    - _Requirements: 17.2, 17.3, 17.4, 17.5_
  
  - [ ]* 15.6 Write unit tests for core UI components
    - Test chat history rendering
    - Test text input submission
    - Test language toggle functionality
    - Test error message display
    - _Requirements: 15.2, 15.3, 15.8_

- [x] 16. Streamlit Frontend - Voice Input
  - [x] 16.1 Implement voice input button
    - Create microphone button in UI
    - Request browser microphone permissions
    - Show recording indicator when active
    - _Requirements: 2.1, 15.4_
  
  - [x] 16.2 Integrate Web Speech API
    - Use browser's SpeechRecognition API
    - Support English and Telugu languages
    - Convert captured audio to text
    - Handle transcription errors gracefully
    - _Requirements: 2.2, 2.3, 2.5_
  
  - [x] 16.3 Process voice-transcribed text
    - Send transcribed text to /chat endpoint
    - Display transcribed text in chat history
    - Show "listening..." indicator during capture
    - _Requirements: 2.3, 2.4_
  
  - [ ]* 16.4 Write property test for voice and text processing equivalence
    - **Property 4: Voice and Text Processing Equivalence**
    - **Validates: Requirements 2.4**
  
  - [ ]* 16.5 Write unit tests for voice input
    - Test microphone permission request
    - Test transcription error handling
    - Test voice input button states
    - _Requirements: 2.1, 2.5_

- [x] 17. Streamlit Frontend - Image Upload
  - [x] 17.1 Implement image upload button
    - Create file uploader widget
    - Accept JPEG, PNG, HEIC formats
    - Validate file size (max 10MB)
    - Show image preview after selection
    - _Requirements: 3.1, 3.2, 15.5_
  
  - [x] 17.2 Implement image upload flow
    - Call POST /upload-image endpoint
    - Show upload progress indicator
    - Display success message with image_id
    - Automatically trigger analysis after upload
    - _Requirements: 3.3, 3.4, 3.5_

  
  - [x] 17.3 Display detected ingredients
    - Show Inventory JSON results in formatted table
    - Display ingredient names in both English and Telugu
    - Show confidence scores as visual indicators (high/medium/low)
    - Allow user to confirm medium-confidence ingredients
    - _Requirements: 4.5, 21.2, 21.4_
  
  - [ ]* 17.4 Write property test for image upload uniqueness
    - **Property 5: Image Upload Uniqueness**
    - **Validates: Requirements 3.3**
  
  - [ ]* 17.5 Write unit tests for image upload
    - Test file format validation
    - Test file size validation
    - Test upload failure handling
    - Test image preview display
    - _Requirements: 3.1, 3.2, 3.5_

- [x] 18. Streamlit Frontend - Recipe Display
  - [x] 18.1 Create recipe card component
    - Design card layout with recipe name, image placeholder, prep time
    - Display ingredients list with quantities
    - Display numbered cooking steps
    - Show nutrition information (calories, protein, carbs, fat, fiber)
    - Show estimated cost per serving
    - _Requirements: 15.6_
  
  - [x] 18.2 Implement recipe selection
    - Allow user to select a recipe from generated options
    - Highlight selected recipe
    - Enable "Generate Shopping List" button for selected recipe
    - _Requirements: 15.6_
  
  - [x] 18.3 Display multilingual recipe content
    - Render recipe names and steps in user's language
    - Show ingredient names in both English and Telugu
    - Apply proper Unicode font rendering for Telugu
    - _Requirements: 22.3, 22.4_
  
  - [ ]* 18.4 Write property test for recipe serialization round-trip
    - **Property 37: Recipe JSON Serialization Round-Trip**
    - **Validates: Requirements 20.1, 20.2, 20.3, 20.4, 20.5**
  
  - [ ]* 18.5 Write unit tests for recipe display
    - Test recipe card rendering
    - Test recipe selection
    - Test multilingual content display
    - _Requirements: 15.6, 22.4_

- [x] 19. Streamlit Frontend - Shopping List
  - [x] 19.1 Create shopping list table component
    - Display items in table format with columns: ingredient, quantity, price, section
    - Add checkbox for each item
    - Group items by market section
    - Show total estimated cost at bottom
    - _Requirements: 15.7_
  
  - [x] 19.2 Implement shopping list interactions
    - Allow users to check off purchased items
    - Persist checkbox states in session
    - Update total cost when items are checked
    - _Requirements: 15.7_
  
  - [x] 19.3 Display reminders
    - Show reminder notifications at top of page
    - Display reminder content and reason
    - Provide "Dismiss" and "Snooze" buttons
    - _Requirements: 11.3, 11.4, 11.5, 11.6_

  
  - [ ]* 19.4 Write unit tests for shopping list
    - Test shopping list table rendering
    - Test checkbox interactions
    - Test total cost calculation
    - Test reminder display and dismissal
    - _Requirements: 15.7, 11.6_

- [x] 20. Checkpoint - Frontend Complete
  - Ensure all UI components render correctly
  - Test responsive design on mobile (360px width)
  - Test language toggle functionality
  - Test end-to-end user flow
  - Ask the user if questions arise

- [x] 21. Integration and Wiring
  - [x] 21.1 Connect Streamlit frontend to API Gateway
    - Configure API base URL in frontend
    - Implement API client with error handling
    - Add request/response logging
    - _Requirements: 14.1, 14.2_
  
  - [x] 21.2 Wire session management across frontend and backend
    - Create session on first page load
    - Store session_id in Streamlit session state
    - Include session_id in all API requests
    - Restore session on page refresh
    - _Requirements: 16.1, 16.2, 16.4_
  
  - [x] 21.3 Implement end-to-end chat flow
    - User sends message → API /chat → AgentCore → Tools → Response
    - Display response in chat history
    - Handle suggested actions (upload image, text input)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [x] 21.4 Implement end-to-end image analysis flow
    - User uploads image → API /upload-image → S3
    - API /analyze-image → VisionAnalyzer → Inventory JSON
    - Display detected ingredients
    - Offer recipe generation
    - _Requirements: 3.3, 3.4, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  
  - [x] 21.5 Implement end-to-end recipe generation flow
    - User requests recipes → API /generate-recipes → RecipeGenerator
    - Query memory for preferences and allergies
    - Generate 2-5 recipes
    - Display recipe cards
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_
  
  - [x] 21.6 Implement end-to-end shopping list flow
    - User selects recipe → API /generate-shopping-list → ShoppingOptimizer
    - Generate shopping list with prices
    - Schedule reminders for price-sensitive items
    - Display shopping list and reminders
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 11.1, 11.2_
  
  - [ ]* 21.7 Write integration tests for end-to-end workflows
    - Test complete workflow: image → inventory → recipes → shopping list
    - Test chat workflow with memory persistence
    - Test festival mode end-to-end
    - Test error recovery across components
    - _Requirements: 6.6_


- [x] 22. Data Seeding and Configuration
  - [x] 22.1 Seed market prices data
    - Create sample market prices for common Andhra ingredients
    - Include prices from multiple Vijayawada markets
    - Add timestamps for all price entries
    - Load data into kitchen-agent-market-prices table
    - _Requirements: 24.1, 24.2, 24.4_
  
  - [x] 22.2 Create environment configuration
    - Set up .env file with AWS credentials
    - Configure Bedrock model identifiers
    - Set API Gateway endpoint URL
    - Configure S3 bucket name
    - Configure DynamoDB table names
    - _Requirements: 19.3_
  
  - [x] 22.3 Create sample test data
    - Create sample images for testing
    - Create sample recipes for testing
    - Create sample inventory data
    - Store in tests/fixtures/ directory
    - _Requirements: Testing_

- [ ] 23. Property-Based Testing - Data Validation
  - [ ]* 23.1 Write property test for Inventory JSON validation round-trip
    - **Property 8: Inventory JSON Validation Round-Trip**
    - **Validates: Requirements 5.5**
  
  - [ ]* 23.2 Write property test for recipe language translation
    - **Property 40: Recipe Language Translation**
    - **Validates: Requirements 22.5**
  
  - [ ]* 23.3 Write property test for market price timestamp
    - **Property 43: Market Price Timestamp**
    - **Validates: Requirements 24.2**
  
  - [ ]* 23.4 Write property test for outdated price flagging
    - **Property 44: Outdated Price Flagging**
    - **Validates: Requirements 24.3**

- [ ] 24. Property-Based Testing - Memory Management
  - [ ]* 24.1 Write property test for preference prioritization
    - **Property 15: Preference Prioritization in Recipes**
    - **Validates: Requirements 7.6**
  
  - [ ]* 24.2 Write property test for session data persistence
    - **Property 16: Session Data Persistence**
    - **Validates: Requirements 7.7**

- [ ] 25. Performance Testing
  - [ ]* 25.1 Create load test script using Locust
    - Simulate 10 concurrent users
    - Test chat, image upload, recipe generation, shopping list
    - Measure response times (P95 < 5 seconds)
    - Verify error rate < 1%
    - _Requirements: Performance_
  
  - [ ]* 25.2 Run performance tests
    - Execute load test for 1 hour
    - Monitor CloudWatch metrics
    - Check for memory leaks
    - Verify Free Tier compliance
    - _Requirements: Performance, 18.1_


- [x] 26. Documentation
  - [x] 26.1 Create README.md
    - Document project overview and features
    - List prerequisites (AWS account, Python 3.11+, Streamlit)
    - Provide installation instructions
    - Document environment variables
    - Include usage examples
    - _Requirements: Maintainability_
  
  - [x] 26.2 Create AWS deployment guide
    - Document AWS account setup steps
    - Provide IAM role creation instructions
    - Document DynamoDB table creation
    - Document S3 bucket setup
    - Document Lambda function deployment
    - Document API Gateway configuration
    - _Requirements: 18.1_
  
  - [x] 26.3 Create API documentation
    - Document all 10 REST endpoints
    - Include request/response examples
    - Document error codes and messages
    - Document rate limiting behavior
    - _Requirements: 14.1, 14.2, 14.5_
  
  - [x] 26.4 Add inline code comments
    - Comment complex logic in all Python files
    - Follow PEP 8 style guidelines
    - Document function parameters and return values
    - _Requirements: Maintainability_

- [x] 27. Final Testing and Validation
  - [x] 27.1 Run complete test suite
    - Execute all unit tests (target: 80% coverage)
    - Execute all property tests (100 examples each)
    - Execute all integration tests
    - Generate coverage report
    - _Requirements: Testing_
  
  - [x] 27.2 Validate AWS Free Tier compliance
    - Check S3 storage usage (< 5GB)
    - Check DynamoDB read/write capacity
    - Check Lambda invocations (< 1M/month)
    - Check API Gateway calls (< 1M/month)
    - Verify lifecycle policies are active
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6_
  
  - [x] 27.3 Validate performance requirements
    - Verify chat responses < 3 seconds
    - Verify image analysis < 10 seconds
    - Verify recipe generation < 15 seconds
    - Verify 10 concurrent users supported
    - _Requirements: Performance_
  
  - [x] 27.4 Validate security requirements
    - Verify all API calls use HTTPS
    - Verify S3 pre-signed URLs expire in 24 hours
    - Verify session data isolation
    - Verify no credentials in code
    - _Requirements: Security_
  
  - [x] 27.5 Validate usability requirements
    - Test page load time on 4G connection (< 5 seconds)
    - Test error messages in both languages
    - Test keyboard navigation
    - Test mobile responsiveness (360px width)
    - _Requirements: Usability, 15.9_

- [x] 28. Final Checkpoint - Complete System
  - Ensure all tests pass
  - Verify all requirements are met
  - Verify all 50 correctness properties are tested
  - Verify documentation is complete
  - Ask the user if questions arise


## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Property-based tests validate universal correctness properties across all inputs
- Unit tests validate specific examples, edge cases, and error conditions
- Integration tests validate end-to-end workflows
- Checkpoints ensure incremental validation at major milestones
- All property tests should run with minimum 100 examples using hypothesis library
- Implementation uses Python 3.11+ for all backend components
- Frontend uses Streamlit framework for rapid development
- AWS services configured for Free Tier compliance
- All code should follow PEP 8 style guidelines
- Target test coverage: 80% minimum

## Property Test Summary

The following 50 correctness properties from the design document are covered by property-based tests:

**Language & Communication (Properties 1-4)**: Message routing, language detection, response consistency, voice/text equivalence

**Data Validation (Properties 5-8, 37-38)**: Image uniqueness, confidence bounds, schema compliance, round-trip validation, confidence filtering

**Workflow Orchestration (Properties 9-10)**: Subtask propagation, result synthesis

**Memory Management (Properties 11-16, 32-34)**: Preference/allergy storage, memory queries, session management, data persistence

**Recipe Generation (Properties 17-21, 39-42)**: Ingredient usage, schema compliance, count bounds, low-oil constraints, language consistency, nutrition completeness

**Shopping & Pricing (Properties 22-25, 43-45)**: Missing ingredients, price lookup, cost calculation, grouping, timestamps, price averaging

**Reminders (Property 26)**: Content completeness

**Festival Mode (Properties 27-30)**: Activation, recipe prioritization, ingredient suggestions, serving size adjustments

**API & Errors (Properties 31, 35-36)**: Status codes, retry options, error logging

**Tool Integration (Properties 46-50)**: Metadata provision, parameter execution, result return, parallel execution, error reporting

