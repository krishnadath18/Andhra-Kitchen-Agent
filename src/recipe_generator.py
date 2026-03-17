"""
Recipe Generator for Andhra Kitchen Agent

Uses Amazon Bedrock Claude 3 Haiku to generate Andhra-style recipes based on
available ingredients and user preferences. Includes nutrition calculation,
cost estimation, and multilingual support.
"""

import json
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# Import configuration
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.env import Config
from src.validators import validate_recipe_schema

# Configure CloudWatch logging
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, Config.LOG_LEVEL))

# Add CloudWatch handler if running in AWS environment
if Config.ENVIRONMENT != 'local':
    try:
        import watchtower
        cloudwatch_handler = watchtower.CloudWatchLogHandler(
            log_group='/aws/andhra-kitchen-agent/recipe-generator',
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


class RecipeGenerator:
    """
    Generates Andhra-style recipes using Amazon Bedrock Claude 3 Haiku.
    Includes nutrition calculation, cost estimation, and multilingual support.
    """
    
    def __init__(self):
        """Initialize RecipeGenerator with Bedrock and DynamoDB clients"""
        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=Config.BEDROCK_REGION
        )
        self.dynamodb = boto3.resource(
            service_name='dynamodb',
            region_name=Config.AWS_REGION
        )
        self.market_prices_table = self.dynamodb.Table(Config.MARKET_PRICES_TABLE)
        self.sessions_table = self.dynamodb.Table(Config.SESSIONS_TABLE)
        
        self.model_id = Config.BEDROCK_MODEL_RECIPE
        self.max_retries = 3
        self.temperature = 0.7
        self.max_tokens = 4096
        
        logger.info(
            f"RecipeGenerator initialized: model={self.model_id}, "
            f"temperature={self.temperature}, max_tokens={self.max_tokens}"
        )
        
        # Andhra ingredient translations
        self.ingredient_translations = {
            "brinjal": "వంకాయ",
            "gongura": "గోంగూర",
            "curry_leaves": "కరివేపాకు",
            "tamarind": "చింతపండు",
            "rice": "బియ్యం",
            "toor_dal": "కందిపప్పు",
            "chana_dal": "శనగపప్పు",
            "urad_dal": "మినుములు",
            "green_chili": "పచ్చిమిర్చి",
            "red_chili": "ఎండుమిర్చి",
            "turmeric": "పసుపు",
            "coriander_powder": "ధనియాల పొడి",
            "cumin_seeds": "జీలకర్ర",
            "mustard_seeds": "ఆవాలు",
            "fenugreek_seeds": "మెంతులు",
            "asafoetida": "ఇంగువ",
            "coconut": "కొబ్బరి",
            "jaggery": "బెల్లం",
            "sesame_seeds": "నువ్వులు",
            "peanuts": "వేరుశనగలు",
            "tomato": "టమాటో",
            "onion": "ఉల్లిపాయ",
            "garlic": "వెల్లుల్లి",
            "ginger": "అల్లం",
            "oil": "నూనె",
            "salt": "ఉప్పు"
        }
        
        # USDA/IFCT nutrition data (per 100g)
        self.nutrition_data = {
            "brinjal": {"calories": 25, "protein": 1.0, "carbs": 6.0, "fat": 0.2, "fiber": 3.0},
            "rice": {"calories": 130, "protein": 2.7, "carbs": 28.0, "fat": 0.3, "fiber": 0.4},
            "toor_dal": {"calories": 343, "protein": 22.0, "carbs": 62.0, "fat": 1.5, "fiber": 15.0},
            "oil": {"calories": 884, "protein": 0.0, "carbs": 0.0, "fat": 100.0, "fiber": 0.0},
            "onion": {"calories": 40, "protein": 1.1, "carbs": 9.3, "fat": 0.1, "fiber": 1.7},
            "tomato": {"calories": 18, "protein": 0.9, "carbs": 3.9, "fat": 0.2, "fiber": 1.2},
            "potato": {"calories": 77, "protein": 2.0, "carbs": 17.0, "fat": 0.1, "fiber": 2.2},
            "ginger": {"calories": 80, "protein": 1.8, "carbs": 18.0, "fat": 0.8, "fiber": 2.0},
            "garlic": {"calories": 149, "protein": 6.4, "carbs": 33.0, "fat": 0.5, "fiber": 2.1},
            "coconut": {"calories": 354, "protein": 3.3, "carbs": 15.0, "fat": 33.0, "fiber": 9.0},
            "peanuts": {"calories": 567, "protein": 25.8, "carbs": 16.0, "fat": 49.0, "fiber": 8.5},
            "tamarind": {"calories": 239, "protein": 2.8, "carbs": 62.0, "fat": 0.6, "fiber": 5.1},
            "jaggery": {"calories": 383, "protein": 0.4, "carbs": 98.0, "fat": 0.1, "fiber": 0.0},
            "curry_leaves": {"calories": 108, "protein": 6.1, "carbs": 18.0, "fat": 1.0, "fiber": 6.4},
            "green_chili": {"calories": 40, "protein": 2.0, "carbs": 9.0, "fat": 0.2, "fiber": 1.5},
            "turmeric": {"calories": 312, "protein": 9.7, "carbs": 67.0, "fat": 3.3, "fiber": 22.0},
            "mustard_seeds": {"calories": 508, "protein": 26.0, "carbs": 28.0, "fat": 36.0, "fiber": 12.0},
            "cumin_seeds": {"calories": 375, "protein": 18.0, "carbs": 44.0, "fat": 22.0, "fiber": 11.0}
        }
    def __init__(self):
        """Initialize RecipeGenerator with Bedrock and DynamoDB clients"""
        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=Config.BEDROCK_REGION
        )
        self.dynamodb = boto3.resource(
            service_name='dynamodb',
            region_name=Config.AWS_REGION
        )
        self.market_prices_table = self.dynamodb.Table(Config.MARKET_PRICES_TABLE)
        self.sessions_table = self.dynamodb.Table(Config.SESSIONS_TABLE)

        self.model_id = Config.BEDROCK_MODEL_RECIPE
        self.max_retries = 3
        self.temperature = 0.7
        self.max_tokens = 4096

        logger.info(
            f"RecipeGenerator initialized: model={self.model_id}, "
            f"temperature={self.temperature}, max_tokens={self.max_tokens}"
        )

        # Andhra ingredient translations
        self.ingredient_translations = {
            "brinjal": "వంకాయ",
            "gongura": "గోంగూర",
            "curry_leaves": "కరివేపాకు",
            "tamarind": "చింతపండు",
            "rice": "బియ్యం",
            "toor_dal": "కందిపప్పు",
            "chana_dal": "శనగపప్పు",
            "urad_dal": "మినుములు",
            "green_chili": "పచ్చిమిర్చి",
            "red_chili": "ఎండుమిర్చి",
            "turmeric": "పసుపు",
            "coriander_powder": "ధనియాల పొడి",
            "cumin_seeds": "జీలకర్ర",
            "mustard_seeds": "ఆవాలు",
            "fenugreek_seeds": "మెంతులు",
            "asafoetida": "ఇంగువ",
            "coconut": "కొబ్బరి",
            "jaggery": "బెల్లం",
            "sesame_seeds": "నువ్వులు",
            "peanuts": "వేరుశనగలు",
            "tomato": "టమాటో",
            "onion": "ఉల్లిపాయ",
            "garlic": "వెల్లుల్లి",
            "ginger": "అల్లం",
            "oil": "నూనె",
            "salt": "ఉప్పు"
        }

        # USDA/IFCT nutrition data (per 100g)
        self.nutrition_data = {
            "brinjal": {"calories": 25, "protein": 1.0, "carbs": 6.0, "fat": 0.2, "fiber": 3.0},
            "rice": {"calories": 130, "protein": 2.7, "carbs": 28.0, "fat": 0.3, "fiber": 0.4},
            "toor_dal": {"calories": 343, "protein": 22.0, "carbs": 62.0, "fat": 1.5, "fiber": 15.0},
            "oil": {"calories": 884, "protein": 0.0, "carbs": 0.0, "fat": 100.0, "fiber": 0.0},
            "onion": {"calories": 40, "protein": 1.1, "carbs": 9.3, "fat": 0.1, "fiber": 1.7},
            "tomato": {"calories": 18, "protein": 0.9, "carbs": 3.9, "fat": 0.2, "fiber": 1.2},
            "potato": {"calories": 77, "protein": 2.0, "carbs": 17.0, "fat": 0.1, "fiber": 2.2},
            "ginger": {"calories": 80, "protein": 1.8, "carbs": 18.0, "fat": 0.8, "fiber": 2.0},
            "garlic": {"calories": 149, "protein": 6.4, "carbs": 33.0, "fat": 0.5, "fiber": 2.1},
            "coconut": {"calories": 354, "protein": 3.3, "carbs": 15.0, "fat": 33.0, "fiber": 9.0},
            "peanuts": {"calories": 567, "protein": 25.8, "carbs": 16.0, "fat": 49.0, "fiber": 8.5},
            "tamarind": {"calories": 239, "protein": 2.8, "carbs": 62.0, "fat": 0.6, "fiber": 5.1},
            "jaggery": {"calories": 383, "protein": 0.4, "carbs": 98.0, "fat": 0.1, "fiber": 0.0},
            "curry_leaves": {"calories": 108, "protein": 6.1, "carbs": 18.0, "fat": 1.0, "fiber": 6.4},
            "green_chili": {"calories": 40, "protein": 2.0, "carbs": 9.0, "fat": 0.2, "fiber": 1.5},
            "turmeric": {"calories": 312, "protein": 9.7, "carbs": 67.0, "fat": 3.3, "fiber": 22.0},
            "mustard_seeds": {"calories": 508, "protein": 26.0, "carbs": 28.0, "fat": 36.0, "fiber": 12.0},
            "cumin_seeds": {"calories": 375, "protein": 18.0, "carbs": 44.0, "fat": 22.0, "fiber": 11.0}
        }
    
    def get_user_preferences(self, session_id: str) -> Dict[str, Any]:
        """
        Query DynamoDB sessions table for user dietary preferences.
        
        Args:
            session_id: User session identifier
        
        Returns:
            Dictionary containing user preferences (low_oil, vegetarian, spice_level, preferred_ingredients)
            Returns empty dict if session not found or error occurs
        """
        try:
            response = self.sessions_table.get_item(
                Key={
                    'session_id': session_id,
                    'data_type': 'profile'
                }
            )
            
            if 'Item' in response:
                preferences = response['Item'].get('preferences', {})
                logger.info(
                    f"Retrieved user preferences: session_id={session_id}, "
                    f"preferences={preferences}"
                )
                return preferences
            else:
                logger.info(
                    f"No preferences found for session: session_id={session_id}"
                )
                return {}
        
        except ClientError as e:
            logger.error(
                f"Error retrieving preferences: session_id={session_id}, "
                f"error={str(e)}"
            )
            return {}
    
    def get_user_allergies(self, session_id: str) -> List[str]:
        """
        Query DynamoDB sessions table for user allergies.
        
        Args:
            session_id: User session identifier
        
        Returns:
            List of allergen names to exclude from recipes
            Returns empty list if session not found or error occurs
        """
        try:
            response = self.sessions_table.get_item(
                Key={
                    'session_id': session_id,
                    'data_type': 'profile'
                }
            )
            
            if 'Item' in response:
                allergies = response['Item'].get('allergies', [])
                logger.info(
                    f"Retrieved user allergies: session_id={session_id}, "
                    f"allergies={allergies}"
                )
                return allergies
            else:
                logger.info(
                    f"No allergies found for session: session_id={session_id}"
                )
                return []
        
        except ClientError as e:
            logger.error(
                f"Error retrieving allergies: session_id={session_id}, "
                f"error={str(e)}"
            )
            return []
    
    def get_user_profile(self, session_id: str) -> tuple[Dict[str, Any], List[str]]:
        """
        Query DynamoDB sessions table for both preferences and allergies in a single call.
        
        Args:
            session_id: User session identifier
        
        Returns:
            Tuple of (preferences dict, allergies list)
            Returns (empty dict, empty list) if session not found or error occurs
        """
        try:
            response = self.sessions_table.get_item(
                Key={
                    'session_id': session_id,
                    'data_type': 'profile'
                }
            )
            
            if 'Item' in response:
                preferences = response['Item'].get('preferences', {})
                allergies = response['Item'].get('allergies', [])
                logger.info(
                    f"Retrieved user profile: session_id={session_id}, "
                    f"preferences={preferences}, allergies={allergies}"
                )
                return preferences, allergies
            else:
                logger.info(
                    f"No profile found for session: session_id={session_id}"
                )
                return {}, []
        
        except ClientError as e:
            logger.error(
                f"Error retrieving user profile: session_id={session_id}, "
                f"error={str(e)}"
            )
            return {}, []
    
    def generate_recipes(
        self,
        inventory: Dict[str, Any],
        preferences: Optional[Dict[str, Any]] = None,
        allergies: Optional[List[str]] = None,
        language: str = "en",
        count: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generate Andhra-style recipes based on available ingredients.
        
        Args:
            inventory: Inventory JSON with detected ingredients
            preferences: User dietary preferences (low_oil, vegetarian, spice_level)
            allergies: List of allergens to exclude
            language: Output language ('en' or 'te')
            count: Number of recipes to generate (2-5)
        
        Returns:
            List of Recipe JSON objects
        
        Raises:
            Exception: If recipe generation fails after retries
        """
        start_time = time.time()
        
        # Validate inputs
        if count < Config.RECIPE_MIN_COUNT:
            count = Config.RECIPE_MIN_COUNT
        if count > Config.RECIPE_MAX_COUNT:
            count = Config.RECIPE_MAX_COUNT
        
        if preferences is None:
            preferences = {}
        if allergies is None:
            allergies = []
        
        session_id = inventory.get('session_id', 'unknown')
        
        logger.info(
            f"Starting recipe generation: session_id={session_id}, "
            f"ingredients={inventory.get('total_items', 0)}, count={count}, "
            f"language={language}, preferences={preferences}, allergies={allergies}"
        )
        
        # Create prompt for Bedrock
        prompt = self._create_recipe_prompt(inventory, preferences, allergies, language, count)
        
        # Call Bedrock with retry logic
        for attempt in range(self.max_retries):
            try:
                response = self._call_bedrock_recipe(prompt)
                recipes_data = self._parse_bedrock_response(response)
                
                # Process each recipe
                recipes = []
                for idx, recipe_data in enumerate(recipes_data):
                    # Add metadata
                    recipe_data['recipe_id'] = f"recipe_{session_id}_{int(time.time())}_{idx}"
                    recipe_data['session_id'] = session_id
                    recipe_data['created_at'] = datetime.now(timezone.utc).isoformat() + "Z"
                    
                    # Calculate nutrition
                    nutrition = self.calculate_nutrition(
                        recipe_data.get('ingredients', []),
                        recipe_data.get('cooking_method', 'sauteing'),
                        recipe_data.get('servings', 4)
                    )
                    recipe_data['nutrition'] = nutrition
                    
                    # Estimate cost
                    cost = self.estimate_cost(
                        recipe_data.get('ingredients', []),
                        recipe_data.get('servings', 4)
                    )
                    recipe_data['estimated_cost'] = cost
                    recipe_data['cost_per_serving'] = round(cost / recipe_data.get('servings', 4), 2)
                    
                    # Format recipe
                    formatted_recipe = self.format_recipe(recipe_data, language)
                    
                    # Validate against schema
                    is_valid, error = validate_recipe_schema(formatted_recipe)
                    if not is_valid:
                        logger.warning(
                            f"Generated invalid recipe: session_id={session_id}, "
                            f"recipe_idx={idx}, error={error}"
                        )
                        continue
                    
                    recipes.append(formatted_recipe)
                
                if not recipes:
                    raise ValueError("No valid recipes generated")
                
                logger.info(
                    f"Recipe generation successful: session_id={session_id}, "
                    f"generated={len(recipes)}, "
                    f"processing_time_ms={int((time.time() - start_time) * 1000)}"
                )
                
                return recipes
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                
                if error_code == 'ThrottlingException':
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"ThrottlingException from Bedrock: session_id={session_id}, "
                        f"attempt={attempt + 1}/{self.max_retries}, retry_in={wait_time}s"
                    )
                    print(f"Throttled by Bedrock. Retrying in {wait_time}s... (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(
                        f"Bedrock API error: session_id={session_id}, "
                        f"error_code={error_code}, error_message={str(e)}"
                    )
                    raise Exception(f"Bedrock API error: {error_code} - {str(e)}")
            
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(
                        f"Recipe generation failed after all retries: session_id={session_id}, "
                        f"attempts={self.max_retries}, error={str(e)}"
                    )
                    raise Exception(f"Recipe generation failed after {self.max_retries} attempts: {str(e)}")
                wait_time = 2 ** attempt
                logger.warning(
                    f"Recipe generation error, retrying: session_id={session_id}, "
                    f"attempt={attempt + 1}/{self.max_retries}, error={str(e)}, retry_in={wait_time}s"
                )
                print(f"Error: {str(e)}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
        
        error_msg = f"Recipe generation failed after {self.max_retries} attempts"
        logger.error(f"{error_msg}: session_id={session_id}")
        raise Exception(error_msg)
    
    def _create_recipe_prompt(
        self,
        inventory: Dict[str, Any],
        preferences: Dict[str, Any],
        allergies: List[str],
        language: str,
        count: int
    ) -> str:
        """Create prompt for Bedrock recipe generation"""
        # Extract ingredient names
        ingredients = inventory.get('ingredients', [])
        ingredient_names = [ing.get('ingredient_name', '') for ing in ingredients]
        ingredient_list = ", ".join(ingredient_names)
        
        # Build constraints
        constraints = []
        if preferences.get('low_oil'):
            constraints.append(f"- Use maximum {Config.RECIPE_LOW_OIL_MAX_TBSP} tablespoons of oil per serving")
            constraints.append("- Prefer cooking methods: steaming, grilling, air-frying, pressure cooking, boiling")
        if preferences.get('vegetarian'):
            constraints.append("- Strictly vegetarian (no meat, fish, or eggs)")
        if allergies:
            allergen_list = ", ".join(allergies)
            constraints.append(f"- MUST EXCLUDE these allergens: {allergen_list}")
        
        spice_level = preferences.get('spice_level', 'medium')
        constraints.append(f"- Spice level: {spice_level}")
        constraints.append(f"- Preparation time: prioritize recipes under {Config.RECIPE_MAX_PREP_TIME} minutes")
        
        constraints_text = "\n".join(constraints) if constraints else "- No special constraints"
        
        language_instruction = ""
        if language == "te":
            language_instruction = """
Generate recipe names and step instructions in Telugu. Use Telugu script for names and instructions.
Include both English and Telugu names for ingredients."""
        else:
            language_instruction = "Generate recipe names and step instructions in English."
        
        return f"""You are an expert in Andhra Pradesh cuisine. Generate {count} authentic, nutritious Andhra-style recipes using the available ingredients.

Available Ingredients:
{ingredient_list}

Constraints:
{constraints_text}

{language_instruction}

Return ONLY a valid JSON array of {count} recipes in this exact format:
[
  {{
    "name": "Recipe Name",
    "name_english": "Recipe Name in English",
    "name_telugu": "రెసిపీ పేరు (if Telugu output)",
    "description": "Brief description of the dish",
    "prep_time": 10,
    "cook_time": 20,
    "total_time": 30,
    "servings": 4,
    "difficulty": "easy",
    "ingredients": [
      {{
        "name": "ingredient_name",
        "name_telugu": "తెలుగు పేరు",
        "quantity": 3,
        "unit": "pieces",
        "optional": false
      }}
    ],
    "steps": [
      {{
        "step_number": 1,
        "instruction": "Step instruction",
        "instruction_telugu": "దశ సూచన (if Telugu output)",
        "duration": 5
      }}
    ],
    "cooking_method": "sauteing",
    "oil_quantity": 0.5,
    "spice_level": "{spice_level}",
    "tags": ["vegetarian", "quick", "traditional"],
    "allergen_info": [],
    "dietary_info": ["vegetarian"],
    "region": "coastal_andhra",
    "health_benefits": "Low oil recipe promotes heart health (if applicable)"
  }}
]

Important:
- Use ONLY the available ingredients listed above
- Follow ALL constraints strictly
- Ensure recipes are authentic Andhra-style
- Be specific with quantities and units
- Provide clear, numbered cooking steps
- Include cooking method (steaming, boiling, frying, grilling, baking, pressure_cooking, sauteing, etc.)
- Calculate oil_quantity per serving in tablespoons
- Return ONLY the JSON array, no other text"""
    
    def _call_bedrock_recipe(self, prompt: str) -> str:
        """
        Call Bedrock Claude 3 Haiku for recipe generation.
        
        Args:
            prompt: Recipe generation prompt
        
        Returns:
            Model response text
        """
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "system": "You are an expert in Andhra Pradesh cuisine. Generate authentic, nutritious recipes using traditional cooking methods."
        }
        
        response = self.bedrock_runtime.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
    
    def _parse_bedrock_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse Bedrock response to extract recipe data.
        
        Args:
            response_text: Raw response from Bedrock
        
        Returns:
            List of recipe dictionaries
        """
        # Extract JSON from response (handle markdown code blocks)
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        try:
            recipes = json.loads(response_text)
            if not isinstance(recipes, list):
                raise ValueError("Response is not a JSON array")
            return recipes
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse Bedrock response as JSON: {str(e)}")
    
    def calculate_nutrition(
        self,
        ingredients: List[Dict[str, Any]],
        cooking_method: str,
        servings: int = 4
    ) -> Dict[str, Any]:
        """
        Calculate nutrition information using USDA/IFCT data.
        
        Args:
            ingredients: List of recipe ingredients with quantities
            cooking_method: Cooking method (affects fat content)
            servings: Number of servings
        
        Returns:
            Nutrition information per serving
        """
        total_calories = 0
        total_protein = 0
        total_carbs = 0
        total_fat = 0
        total_fiber = 0
        
        for ingredient in ingredients:
            name = ingredient.get('name', '').lower().replace(' ', '_')
            quantity = ingredient.get('quantity', 0)
            unit = ingredient.get('unit', '').lower()
            
            # Get nutrition data
            nutrition = self.nutrition_data.get(name, {
                "calories": 50, "protein": 1.0, "carbs": 10.0, "fat": 0.5, "fiber": 1.0
            })
            
            # Convert quantity to grams (rough estimates)
            grams = self._convert_to_grams(quantity, unit, name)
            
            # Calculate nutrition (per 100g in database)
            factor = grams / 100.0
            total_calories += nutrition['calories'] * factor
            total_protein += nutrition['protein'] * factor
            total_carbs += nutrition['carbs'] * factor
            total_fat += nutrition['fat'] * factor
            total_fiber += nutrition['fiber'] * factor
        
        # Apply cooking method adjustments
        if cooking_method in ['frying', 'deep_frying']:
            total_fat *= 1.2  # +20% fat for frying
            total_calories += total_fat * 9 * 0.2  # Additional calories from fat
        
        # Calculate per serving
        return {
            "calories": round(total_calories / servings, 1),
            "protein": round(total_protein / servings, 1),
            "carbohydrates": round(total_carbs / servings, 1),
            "fat": round(total_fat / servings, 1),
            "fiber": round(total_fiber / servings, 1),
            "accuracy_margin": "±10%"
        }
    
    def _convert_to_grams(self, quantity: float, unit: str, ingredient: str) -> float:
        """Convert ingredient quantity to grams (rough estimates)"""
        unit = unit.lower()
        
        # Weight units
        if unit in ['kg', 'kilogram', 'kilograms']:
            return quantity * 1000
        if unit in ['g', 'gram', 'grams']:
            return quantity
        
        # Volume units (approximate)
        if unit in ['cup', 'cups']:
            return quantity * 200
        if unit in ['tablespoon', 'tablespoons', 'tbsp']:
            return quantity * 15
        if unit in ['teaspoon', 'teaspoons', 'tsp']:
            return quantity * 5
        if unit in ['ml', 'milliliter', 'milliliters']:
            return quantity
        if unit in ['liter', 'liters', 'l']:
            return quantity * 1000
        
        # Piece-based estimates
        if unit in ['piece', 'pieces']:
            piece_weights = {
                'brinjal': 150, 'tomato': 100, 'onion': 100,
                'potato': 150, 'green_chili': 5
            }
            return quantity * piece_weights.get(ingredient, 100)
        
        if unit in ['bunch', 'bunches']:
            return quantity * 50
        
        # Default
        return quantity * 10
    
    def estimate_cost(
        self,
        ingredients: List[Dict[str, Any]],
        servings: int = 4
    ) -> float:
        """
        Estimate recipe cost using DynamoDB market prices.
        
        Args:
            ingredients: List of recipe ingredients with quantities
            servings: Number of servings
        
        Returns:
            Estimated total cost in INR
        """
        total_cost = 0.0
        
        for ingredient in ingredients:
            name = ingredient.get('name', '').lower().replace(' ', '_')
            quantity = ingredient.get('quantity', 0)
            unit = ingredient.get('unit', '').lower()
            
            # Query DynamoDB for market price
            try:
                response = self.market_prices_table.get_item(
                    Key={
                        'ingredient_name': name,
                        'market_name': Config.DEFAULT_MARKET
                    }
                )
                
                if 'Item' in response:
                    price_per_unit = float(response['Item'].get('price_per_unit', 0))
                    price_unit = response['Item'].get('unit', 'kg').lower()
                    
                    # Convert quantity to price unit
                    quantity_in_price_unit = self._convert_units(quantity, unit, price_unit)
                    ingredient_cost = price_per_unit * quantity_in_price_unit
                    total_cost += ingredient_cost
                else:
                    # Estimate if price not found
                    total_cost += self._estimate_ingredient_cost(name, quantity, unit)
            
            except Exception as e:
                logger.warning(f"Failed to get price for {name}: {str(e)}")
                total_cost += self._estimate_ingredient_cost(name, quantity, unit)
        
        return round(total_cost, 2)
    
    def _convert_units(self, quantity: float, from_unit: str, to_unit: str) -> float:
        """Convert quantity from one unit to another"""
        from_unit = from_unit.lower()
        to_unit = to_unit.lower()
        
        # Convert to grams first
        grams = self._convert_to_grams(quantity, from_unit, '')
        
        # Convert from grams to target unit
        if to_unit in ['kg', 'kilogram']:
            return grams / 1000
        if to_unit in ['g', 'gram', 'grams']:
            return grams
        if to_unit in ['piece', 'pieces']:
            return grams / 100  # Assume 100g per piece
        
        return quantity  # Return original if conversion not possible
    
    def _estimate_ingredient_cost(self, name: str, quantity: float, unit: str) -> float:
        """Estimate ingredient cost when price data unavailable"""
        # Rough estimates in INR
        base_prices = {
            'brinjal': 30, 'rice': 50, 'oil': 150, 'onion': 40,
            'tomato': 50, 'potato': 30, 'dal': 100, 'spices': 200
        }
        
        # Get base price (per kg)
        base_price = base_prices.get(name, 50)
        
        # Convert to kg
        kg = self._convert_to_grams(quantity, unit, name) / 1000
        
        return base_price * kg
    
    def format_recipe(self, recipe_data: Dict[str, Any], language: str) -> Dict[str, Any]:
        """
        Format recipe for structured output.
        
        Args:
            recipe_data: Raw recipe data from Bedrock
            language: Output language
        
        Returns:
            Formatted Recipe JSON
        """
        # Add Telugu translations for ingredients if not present
        for ingredient in recipe_data.get('ingredients', []):
            name = ingredient.get('name', '').lower().replace(' ', '_')
            if 'name_telugu' not in ingredient and name in self.ingredient_translations:
                ingredient['name_telugu'] = self.ingredient_translations[name]
        
        # Ensure required fields exist
        if 'name_english' not in recipe_data:
            recipe_data['name_english'] = recipe_data.get('name', 'Andhra Recipe')
        
        # Set language-specific name
        if language == 'te' and 'name_telugu' in recipe_data:
            recipe_data['name'] = recipe_data['name_telugu']
        else:
            recipe_data['name'] = recipe_data['name_english']
        
        return recipe_data


if __name__ == "__main__":
    # Example usage
    print("Recipe Generator for Andhra Kitchen Agent")
    print("=" * 50)
    print(f"Model: {Config.BEDROCK_MODEL_RECIPE}")
    print(f"Region: {Config.BEDROCK_REGION}")
    print(f"Recipe Count Range: {Config.RECIPE_MIN_COUNT}-{Config.RECIPE_MAX_COUNT}")
    print(f"Max Prep Time: {Config.RECIPE_MAX_PREP_TIME} minutes")
    print(f"Low Oil Max: {Config.RECIPE_LOW_OIL_MAX_TBSP} tbsp per serving")
    print("=" * 50)
    
    # Initialize generator
    generator = RecipeGenerator()
    print(f"\n✅ RecipeGenerator initialized")
    print(f"   Ingredient translations: {len(generator.ingredient_translations)}")
    print(f"   Nutrition database entries: {len(generator.nutrition_data)}")
