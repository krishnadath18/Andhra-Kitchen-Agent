# Requirements Document

## Introduction

The Andhra Kitchen Agent is a multilingual, AI-powered web application that helps families manage their kitchen inventory, discover nutritious Andhra-style recipes, optimize grocery shopping, and receive proactive cooking reminders. The system uses Amazon Bedrock for vision analysis, recipe generation, and multilingual chat, with Bedrock AgentCore orchestrating autonomous workflows including memory management and task decomposition. The application targets families in Andhra Pradesh (particularly Vijayawada region) who want to reduce food waste, cook traditional recipes efficiently, and manage dietary preferences.

## Glossary

- **Kitchen_Agent**: The AI-powered system that orchestrates all features including chat, vision analysis, recipe generation, and shopping optimization
- **Vision_Analyzer**: The Amazon Bedrock vision model component that detects ingredients from uploaded images
- **Recipe_Generator**: The Amazon Bedrock component that creates Andhra-style recipes based on available ingredients and preferences
- **AgentCore**: The Bedrock AgentCore service that decomposes tasks, manages memory, and coordinates tool calls
- **Memory_Store**: The persistent storage managed by AgentCore for family preferences, allergies, and historical data
- **Shopping_Optimizer**: The component that generates optimized shopping lists with Vijayawada market prices
- **Reminder_Service**: The AWS Lambda-based service that sends proactive notifications
- **Chat_Interface**: The Streamlit-based web UI for user interaction
- **Inventory_JSON**: The structured data format containing detected ingredients with quantities and confidence scores
- **User**: A family member interacting with the Kitchen Agent
- **Andhra_Ingredient**: Traditional ingredients used in Andhra cuisine (e.g., brinjal, gongura, curry leaves, tamarind, rice, dal)
- **Festival_Mode**: Special operational mode that adjusts recommendations for Telugu festivals

## Requirements

### Requirement 1: Multilingual Text Chat

**User Story:** As a User, I want to chat with the Kitchen Agent in English or Telugu, so that I can communicate in my preferred language.

#### Acceptance Criteria

1. WHEN a User submits a text message in English, THE Chat_Interface SHALL send the message to Amazon Bedrock for processing
2. WHEN a User submits a text message in Telugu, THE Chat_Interface SHALL send the message to Amazon Bedrock for processing
3. THE Kitchen_Agent SHALL detect the input language automatically
4. THE Kitchen_Agent SHALL respond in the same language as the User's input
5. WHEN the Kitchen_Agent generates a response, THE Chat_Interface SHALL display the response within 3 seconds

### Requirement 2: Voice Input Processing

**User Story:** As a User, I want to use voice input in English or Telugu, so that I can interact hands-free while cooking.

#### Acceptance Criteria

1. WHEN a User activates voice input, THE Chat_Interface SHALL capture audio through the browser microphone
2. THE Chat_Interface SHALL convert captured audio to text using browser speech recognition API
3. WHEN audio conversion completes, THE Chat_Interface SHALL send the transcribed text to the Kitchen_Agent
4. THE Kitchen_Agent SHALL process voice-transcribed text identically to typed text
5. IF audio conversion fails, THEN THE Chat_Interface SHALL display an error message and prompt the User to try again

### Requirement 3: Image Upload and Storage

**User Story:** As a User, I want to upload photos of my fridge or pantry, so that the system can identify available ingredients.

#### Acceptance Criteria

1. THE Chat_Interface SHALL accept image uploads in JPEG, PNG, and HEIC formats
2. THE Chat_Interface SHALL limit uploaded image file size to 10MB
3. WHEN a User uploads an image, THE Chat_Interface SHALL upload the image to S3 with a unique identifier
4. THE Chat_Interface SHALL generate a pre-signed S3 URL valid for 24 hours
5. IF upload fails, THEN THE Chat_Interface SHALL display an error message with retry option
6. THE Kitchen_Agent SHALL delete uploaded images from S3 after 24 hours

### Requirement 4: Ingredient Detection from Images

**User Story:** As a User, I want the system to identify Andhra ingredients from my photos, so that I know what I can cook with.

#### Acceptance Criteria

1. WHEN an image is uploaded to S3, THE Vision_Analyzer SHALL analyze the image using Amazon Bedrock vision models
2. THE Vision_Analyzer SHALL detect Andhra_Ingredients visible in the image
3. THE Vision_Analyzer SHALL estimate quantities for each detected ingredient (e.g., "3 brinjals", "1 bunch curry leaves")
4. THE Vision_Analyzer SHALL assign confidence scores between 0 and 1 for each detected ingredient
5. THE Vision_Analyzer SHALL output results as Inventory_JSON containing ingredient names, quantities, and confidence scores
6. THE Vision_Analyzer SHALL complete analysis within 10 seconds
7. IF no Andhra_Ingredients are detected, THEN THE Vision_Analyzer SHALL return an empty Inventory_JSON

### Requirement 5: Inventory JSON Format

**User Story:** As a developer, I want a standardized inventory format, so that downstream components can process ingredient data consistently.

#### Acceptance Criteria

1. THE Vision_Analyzer SHALL structure Inventory_JSON with fields: ingredient_name, quantity, unit, confidence_score, and detection_timestamp
2. THE Inventory_JSON SHALL use English names for all ingredients regardless of input language
3. THE Inventory_JSON SHALL represent quantities as numeric values with appropriate units (kg, grams, pieces, bunches)
4. THE Inventory_JSON SHALL include a total_items count field
5. THE Inventory_JSON SHALL validate against a predefined JSON schema before processing

### Requirement 6: Autonomous Workflow Decomposition

**User Story:** As a User, I want the system to automatically break down my request into steps, so that I get comprehensive assistance without multiple prompts.

#### Acceptance Criteria

1. WHEN a User request is received, THE AgentCore SHALL analyze the request and decompose it into subtasks
2. THE AgentCore SHALL identify required tools for each subtask (vision analysis, memory lookup, recipe generation, shopping optimization)
3. THE AgentCore SHALL execute subtasks in optimal order based on dependencies
4. THE AgentCore SHALL pass outputs from one subtask as inputs to dependent subtasks
5. WHEN all subtasks complete, THE AgentCore SHALL synthesize results into a unified response
6. THE Kitchen_Agent SHALL complete workflow decomposition and execution within 30 seconds

### Requirement 7: Family Preferences and Allergy Memory

**User Story:** As a User, I want the system to remember my family's dietary preferences and allergies, so that I receive personalized recommendations.

#### Acceptance Criteria

1. WHEN a User mentions a dietary preference, THE AgentCore SHALL store the preference in Memory_Store
2. WHEN a User mentions an allergy, THE AgentCore SHALL store the allergy in Memory_Store with high priority flag
3. THE Memory_Store SHALL associate preferences and allergies with the User's session identifier
4. WHEN generating recipes, THE Recipe_Generator SHALL query Memory_Store for relevant preferences and allergies
5. THE Recipe_Generator SHALL exclude ingredients that match stored allergies
6. THE Recipe_Generator SHALL prioritize ingredients that match stored preferences
7. THE Memory_Store SHALL persist data across user sessions

### Requirement 8: Recipe Generation from Inventory

**User Story:** As a User, I want to receive quick nutritious Andhra-style recipes based on my available ingredients, so that I can cook efficiently with what I have.

#### Acceptance Criteria

1. WHEN Inventory_JSON is available, THE Recipe_Generator SHALL generate Andhra-style recipes using detected ingredients
2. THE Recipe_Generator SHALL query Memory_Store for family preferences and allergies before generating recipes
3. THE Recipe_Generator SHALL include recipe name, preparation time, serving size, estimated cost in INR, cooking steps, and nutrition information
4. THE Recipe_Generator SHALL prioritize recipes with preparation time under 30 minutes
5. THE Recipe_Generator SHALL calculate estimated cost based on Vijayawada market prices
6. THE Recipe_Generator SHALL provide nutrition information including calories, protein, carbohydrates, and fat per serving
7. THE Recipe_Generator SHALL generate between 2 and 5 recipe options per request
8. THE Recipe_Generator SHALL format cooking steps as numbered instructions

### Requirement 9: Low-Oil Recipe Optimization

**User Story:** As a health-conscious User, I want recipes that use minimal oil, so that my family eats healthier meals.

#### Acceptance Criteria

1. WHERE low-oil preference is stored in Memory_Store, THE Recipe_Generator SHALL prioritize recipes using 2 tablespoons or less oil per serving
2. WHERE low-oil preference is stored, THE Recipe_Generator SHALL suggest cooking methods like steaming, grilling, or air-frying
3. THE Recipe_Generator SHALL indicate oil quantity explicitly in each recipe
4. WHERE low-oil preference is stored, THE Recipe_Generator SHALL include a health benefit note in the recipe description

### Requirement 10: Shopping List Generation

**User Story:** As a User, I want an optimized shopping list with local market prices, so that I can shop efficiently and minimize waste.

#### Acceptance Criteria

1. WHEN a recipe is selected, THE Shopping_Optimizer SHALL compare recipe ingredients against Inventory_JSON
2. THE Shopping_Optimizer SHALL identify missing ingredients required for the recipe
3. THE Shopping_Optimizer SHALL generate a shopping list containing only missing ingredients
4. THE Shopping_Optimizer SHALL include estimated prices for each item based on Vijayawada market data
5. THE Shopping_Optimizer SHALL calculate total estimated shopping cost
6. THE Shopping_Optimizer SHALL suggest optimal quantities to minimize waste (e.g., "buy 250g instead of 500g")
7. THE Shopping_Optimizer SHALL group items by market section (vegetables, spices, grains)

### Requirement 11: Proactive Reminder Scheduling

**User Story:** As a User, I want to receive timely reminders about shopping and cooking, so that I can plan ahead and get the best prices.

#### Acceptance Criteria

1. WHEN the Shopping_Optimizer detects a price-sensitive ingredient, THE AgentCore SHALL invoke the Reminder_Service
2. THE Reminder_Service SHALL schedule reminders using AWS Lambda with EventBridge triggers
3. THE Reminder_Service SHALL send reminders via the Chat_Interface when the User next logs in
4. THE Reminder_Service SHALL include reminder content specifying the action (e.g., "Buy fresh curry leaves tomorrow")
5. THE Reminder_Service SHALL include the reason for the reminder (e.g., "prices low on Wednesdays")
6. THE Kitchen_Agent SHALL allow Users to dismiss or snooze reminders
7. THE Reminder_Service SHALL store scheduled reminders in DynamoDB with TTL of 7 days

### Requirement 12: Festival Mode Activation

**User Story:** As a User, I want the system to automatically adjust recommendations during Telugu festivals, so that I can prepare appropriate festive meals.

#### Acceptance Criteria

1. THE Kitchen_Agent SHALL maintain a calendar of major Telugu festivals (Sankranti, Ugadi, Dasara, Deepavali)
2. WHEN the current date matches a festival date, THE Kitchen_Agent SHALL activate Festival_Mode
3. WHILE Festival_Mode is active, THE Recipe_Generator SHALL prioritize traditional festive recipes
4. WHILE Festival_Mode is active, THE Shopping_Optimizer SHALL suggest festive ingredients (jaggery, sesame seeds, special sweets)
5. WHILE Festival_Mode is active, THE Chat_Interface SHALL display a festival greeting banner
6. THE Kitchen_Agent SHALL deactivate Festival_Mode 2 days after the festival date

### Requirement 13: Sankranti Special Adjustments

**User Story:** As a User celebrating Sankranti, I want recipe suggestions for traditional Sankranti dishes, so that I can prepare authentic festive meals.

#### Acceptance Criteria

1. WHILE Festival_Mode is active for Sankranti, THE Recipe_Generator SHALL suggest recipes for ariselu, pongal, and tilgul
2. WHILE Festival_Mode is active for Sankranti, THE Shopping_Optimizer SHALL include jaggery, sesame seeds, and rice in shopping suggestions
3. WHILE Festival_Mode is active for Sankranti, THE Recipe_Generator SHALL increase suggested serving sizes by 50 percent to account for guests

### Requirement 14: API Gateway Integration

**User Story:** As a developer, I want secure API endpoints for the web application, so that the frontend can communicate with backend services.

#### Acceptance Criteria

1. THE Kitchen_Agent SHALL expose REST API endpoints through AWS API Gateway
2. THE API Gateway SHALL provide endpoints for chat, image upload, recipe retrieval, and shopping list generation
3. THE API Gateway SHALL enforce HTTPS for all requests
4. THE API Gateway SHALL implement rate limiting of 100 requests per minute per User
5. THE API Gateway SHALL return appropriate HTTP status codes (200, 400, 401, 500)
6. IF rate limit is exceeded, THEN THE API Gateway SHALL return HTTP 429 with retry-after header

### Requirement 15: Streamlit Web Interface

**User Story:** As a User, I want a simple web interface to interact with the Kitchen Agent, so that I can access all features from my browser.

#### Acceptance Criteria

1. THE Chat_Interface SHALL implement a web UI using Streamlit framework
2. THE Chat_Interface SHALL display a chat history panel showing User messages and Kitchen_Agent responses
3. THE Chat_Interface SHALL provide a text input field for typing messages
4. THE Chat_Interface SHALL provide a voice input button for speech capture
5. THE Chat_Interface SHALL provide an image upload button for photo selection
6. THE Chat_Interface SHALL display generated recipes in formatted cards with images
7. THE Chat_Interface SHALL display shopping lists in a table format with checkboxes
8. THE Chat_Interface SHALL provide language toggle between English and Telugu
9. THE Chat_Interface SHALL be responsive and functional on mobile browsers with screen width 360px or greater

### Requirement 16: Session Management

**User Story:** As a User, I want my conversation history and preferences to persist during my session, so that I don't have to repeat information.

#### Acceptance Criteria

1. WHEN a User first accesses the Chat_Interface, THE Kitchen_Agent SHALL create a unique session identifier
2. THE Kitchen_Agent SHALL associate all User interactions with the session identifier
3. THE AgentCore SHALL store session data in Memory_Store for 7 days
4. WHEN a User returns within 7 days, THE Kitchen_Agent SHALL restore the previous session
5. THE Chat_Interface SHALL display conversation history from the current session
6. THE Kitchen_Agent SHALL delete session data after 7 days of inactivity

### Requirement 17: Error Handling and User Feedback

**User Story:** As a User, I want clear error messages when something goes wrong, so that I understand what happened and how to proceed.

#### Acceptance Criteria

1. IF Amazon Bedrock API returns an error, THEN THE Kitchen_Agent SHALL log the error and display a user-friendly message
2. IF S3 upload fails, THEN THE Chat_Interface SHALL display "Image upload failed. Please check your connection and try again"
3. IF Vision_Analyzer cannot process an image, THEN THE Kitchen_Agent SHALL display "Could not analyze image. Please ensure the photo is clear and well-lit"
4. IF Recipe_Generator cannot create recipes, THEN THE Kitchen_Agent SHALL display "Not enough ingredients detected. Please upload more photos or describe what you have"
5. THE Kitchen_Agent SHALL provide a "Try Again" option for all error scenarios
6. THE Kitchen_Agent SHALL log all errors to CloudWatch for debugging

### Requirement 18: AWS Free Tier Compliance

**User Story:** As a cost-conscious developer, I want the application to operate within AWS Free Tier limits, so that I can run it without incurring charges.

#### Acceptance Criteria

1. THE Kitchen_Agent SHALL use AWS services that offer Free Tier allowances (Lambda, S3, API Gateway, DynamoDB)
2. THE Kitchen_Agent SHALL implement S3 lifecycle policies to delete images after 24 hours
3. THE Kitchen_Agent SHALL use DynamoDB on-demand pricing with TTL for automatic data expiration
4. THE Kitchen_Agent SHALL limit Lambda function memory to 512MB
5. THE Kitchen_Agent SHALL limit Lambda function timeout to 30 seconds
6. THE Kitchen_Agent SHALL implement request throttling to stay within Free Tier limits

### Requirement 19: Bedrock Model Configuration

**User Story:** As a developer, I want to configure which Bedrock models to use, so that I can optimize for cost and performance.

#### Acceptance Criteria

1. THE Kitchen_Agent SHALL use Amazon Bedrock Claude 3 Haiku for chat and recipe generation
2. THE Vision_Analyzer SHALL use Amazon Bedrock Claude 3 Sonnet for image analysis
3. THE Kitchen_Agent SHALL store model identifiers in environment variables
4. THE Kitchen_Agent SHALL implement retry logic with exponential backoff for Bedrock API calls
5. IF a Bedrock model is unavailable, THEN THE Kitchen_Agent SHALL retry up to 3 times before returning an error

### Requirement 20: Recipe Round-Trip Validation

**User Story:** As a developer, I want to ensure recipe data integrity, so that recipes can be reliably stored and retrieved.

#### Acceptance Criteria

1. THE Recipe_Generator SHALL output recipes in structured JSON format
2. THE Kitchen_Agent SHALL validate recipe JSON against a predefined schema
3. THE Kitchen_Agent SHALL serialize recipe JSON for storage in Memory_Store
4. WHEN retrieving a stored recipe, THE Kitchen_Agent SHALL deserialize the JSON
5. FOR ALL valid recipe JSON objects, serializing then deserializing SHALL produce an equivalent object (round-trip property)
6. IF deserialization fails, THEN THE Kitchen_Agent SHALL log the error and regenerate the recipe

### Requirement 21: Ingredient Confidence Threshold

**User Story:** As a User, I want the system to only use ingredients it's confident about, so that recipe suggestions are accurate.

#### Acceptance Criteria

1. THE Vision_Analyzer SHALL only include ingredients with confidence scores of 0.7 or higher in Inventory_JSON
2. WHERE an ingredient has confidence score between 0.5 and 0.7, THE Kitchen_Agent SHALL ask the User for confirmation
3. THE Kitchen_Agent SHALL exclude ingredients with confidence scores below 0.5 from recipe generation
4. THE Chat_Interface SHALL display confidence scores as visual indicators (high, medium, low) next to detected ingredients

### Requirement 22: Multilingual Recipe Display

**User Story:** As a Telugu-speaking User, I want to view recipes in Telugu, so that I can follow instructions in my native language.

#### Acceptance Criteria

1. WHEN the User's language preference is Telugu, THE Recipe_Generator SHALL generate recipe names and steps in Telugu
2. WHEN the User's language preference is English, THE Recipe_Generator SHALL generate recipe names and steps in English
3. THE Recipe_Generator SHALL maintain ingredient names in both English and Telugu in the output
4. THE Chat_Interface SHALL render Telugu text using appropriate Unicode fonts
5. THE Kitchen_Agent SHALL translate existing recipes when the User changes language preference

### Requirement 23: Nutrition Calculation Accuracy

**User Story:** As a health-conscious User, I want accurate nutrition information, so that I can make informed dietary choices.

#### Acceptance Criteria

1. THE Recipe_Generator SHALL calculate nutrition values based on USDA and IFCT (Indian Food Composition Tables) data
2. THE Recipe_Generator SHALL provide nutrition information per serving
3. THE Recipe_Generator SHALL include calories, protein (grams), carbohydrates (grams), fat (grams), and fiber (grams)
4. THE Recipe_Generator SHALL account for cooking method impact on nutrition (e.g., oil absorption during frying)
5. THE Recipe_Generator SHALL indicate nutrition values with +/- 10 percent accuracy margin

### Requirement 24: Market Price Data Management

**User Story:** As a developer, I want to maintain current market prices, so that shopping cost estimates remain accurate.

#### Acceptance Criteria

1. THE Shopping_Optimizer SHALL store Vijayawada market prices in a DynamoDB table
2. THE Shopping_Optimizer SHALL include price update timestamps for each ingredient
3. THE Kitchen_Agent SHALL flag prices older than 30 days as potentially outdated
4. THE Shopping_Optimizer SHALL use average prices across multiple Vijayawada markets
5. WHERE price data is unavailable, THE Shopping_Optimizer SHALL estimate based on similar ingredients

### Requirement 25: AgentCore Tool Integration

**User Story:** As a developer, I want AgentCore to orchestrate tool calls efficiently, so that the system responds quickly to user requests.

#### Acceptance Criteria

1. THE AgentCore SHALL register tools for vision analysis, recipe generation, shopping optimization, and reminder scheduling
2. THE AgentCore SHALL provide tool descriptions and parameter schemas to Bedrock
3. WHEN Bedrock requests a tool call, THE AgentCore SHALL execute the tool with provided parameters
4. THE AgentCore SHALL return tool results to Bedrock for response synthesis
5. THE AgentCore SHALL execute independent tool calls in parallel when possible
6. THE AgentCore SHALL handle tool execution failures gracefully and report errors to Bedrock

## Non-Functional Requirements

### Performance

- Recipe generation SHALL complete within 15 seconds
- Image analysis SHALL complete within 10 seconds
- Chat responses SHALL appear within 3 seconds
- The Chat_Interface SHALL support 10 concurrent users

### Security

- All API calls SHALL use HTTPS encryption
- S3 image URLs SHALL use pre-signed URLs with 24-hour expiration
- User session data SHALL be isolated per session identifier
- AWS credentials SHALL be stored in environment variables, never in code

### Reliability

- The Kitchen_Agent SHALL maintain 99% uptime during business hours (6 AM to 11 PM IST)
- The Kitchen_Agent SHALL implement automatic retry for transient failures
- The Kitchen_Agent SHALL gracefully degrade when optional services are unavailable

### Usability

- The Chat_Interface SHALL load within 5 seconds on 4G mobile connections
- Error messages SHALL be displayed in the User's selected language
- The Chat_Interface SHALL be operable with keyboard navigation only

### Maintainability

- All code SHALL include inline comments explaining complex logic
- Configuration values SHALL be externalized to environment variables
- The codebase SHALL follow PEP 8 style guidelines for Python code
