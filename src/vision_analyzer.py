"""
Vision Analyzer for Andhra Kitchen Agent

Uses Amazon Bedrock Claude 3 Sonnet to detect Andhra ingredients from images.
Implements confidence scoring, threshold filtering, and retry logic.
"""

import json
import time
import base64
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# Import configuration
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.env import Config
from src.validators import validate_inventory_schema

# Configure CloudWatch logging
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, Config.LOG_LEVEL))

# Add CloudWatch handler if running in AWS environment
if Config.ENVIRONMENT != 'local':
    try:
        import watchtower
        cloudwatch_handler = watchtower.CloudWatchLogHandler(
            log_group='/aws/andhra-kitchen-agent/vision-analyzer',
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


class VisionAnalyzer:
    """
    Analyzes kitchen images using Amazon Bedrock Claude 3 Sonnet
    to detect Andhra ingredients with confidence scores.
    """
    
    def __init__(self):
        """Initialize VisionAnalyzer with Bedrock client"""
        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=Config.BEDROCK_REGION
        )
        self.model_id = Config.BEDROCK_MODEL_VISION
        self.confidence_high = Config.VISION_CONFIDENCE_HIGH
        self.confidence_medium = Config.VISION_CONFIDENCE_MEDIUM
        self.max_retries = Config.VISION_MAX_RETRIES
        self.timeout = Config.VISION_TIMEOUT_SECONDS
        
        logger.info(
            f"VisionAnalyzer initialized: model={self.model_id}, "
            f"max_retries={self.max_retries}, timeout={self.timeout}s"
        )
        
        # Andhra ingredient knowledge base
        self.andhra_ingredients = {
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
            "drumstick": "మునగకాయ",
            "ridge_gourd": "బీరకాయ",
            "bottle_gourd": "సొరకాయ",
            "okra": "బెండకాయ",
            "potato": "బంగాళాదుంప",
            "carrot": "క్యారెట్"
        }
    
    def analyze_image(self, image_data: bytes, session_id: str, image_id: str) -> Dict[str, Any]:
        """
        Analyze an image to detect Andhra ingredients.
        
        Args:
            image_data: Binary image data (JPEG, PNG, or HEIC)
            session_id: User session identifier
            image_id: Unique image identifier
        
        Returns:
            Inventory JSON with detected ingredients
        
        Raises:
            Exception: If analysis fails after retries
        """
        start_time = time.time()
        
        logger.info(
            f"Starting image analysis: session_id={session_id}, "
            f"image_id={image_id}, size={len(image_data)} bytes"
        )
        
        # Encode image to base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Create prompt for Bedrock
        prompt = self._create_vision_prompt()
        
        # Call Bedrock with retry logic
        for attempt in range(self.max_retries):
            try:
                response = self._call_bedrock_vision(image_base64, prompt)
                detections = self._parse_bedrock_response(response)
                
                # Create Inventory JSON
                inventory = self._create_inventory_json(
                    detections,
                    session_id,
                    image_id,
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
                
                # Validate against schema
                is_valid, error = validate_inventory_schema(inventory)
                if not is_valid:
                    logger.error(
                        f"Generated invalid inventory: session_id={session_id}, "
                        f"image_id={image_id}, error={error}"
                    )
                    raise ValueError(f"Generated invalid inventory: {error}")
                
                logger.info(
                    f"Image analysis successful: session_id={session_id}, "
                    f"image_id={image_id}, detected_items={inventory['total_items']}, "
                    f"processing_time_ms={inventory['detection_metadata']['processing_time_ms']}"
                )
                
                return inventory
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                
                if error_code == 'ThrottlingException':
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"ThrottlingException from Bedrock: session_id={session_id}, "
                        f"image_id={image_id}, attempt={attempt + 1}/{self.max_retries}, "
                        f"retry_in={wait_time}s"
                    )
                    print(f"Throttled by Bedrock. Retrying in {wait_time}s... (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue
                elif error_code == 'ModelNotReadyException':
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"ModelNotReadyException from Bedrock: session_id={session_id}, "
                        f"image_id={image_id}, attempt={attempt + 1}/{self.max_retries}, "
                        f"retry_in={wait_time}s"
                    )
                    print(f"Model not ready. Retrying in {wait_time}s... (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(
                        f"Bedrock API error: session_id={session_id}, "
                        f"image_id={image_id}, error_code={error_code}, "
                        f"error_message={str(e)}"
                    )
                    raise Exception(f"Bedrock API error: {error_code} - {str(e)}")
            
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(
                        f"Vision analysis failed after all retries: session_id={session_id}, "
                        f"image_id={image_id}, attempts={self.max_retries}, "
                        f"error={str(e)}"
                    )
                    raise Exception(f"Vision analysis failed after {self.max_retries} attempts: {str(e)}")
                wait_time = 2 ** attempt
                logger.warning(
                    f"Vision analysis error, retrying: session_id={session_id}, "
                    f"image_id={image_id}, attempt={attempt + 1}/{self.max_retries}, "
                    f"error={str(e)}, retry_in={wait_time}s"
                )
                print(f"Error: {str(e)}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
        
        error_msg = f"Vision analysis failed after {self.max_retries} attempts"
        logger.error(
            f"{error_msg}: session_id={session_id}, image_id={image_id}"
        )
        raise Exception(error_msg)
    
    def _create_vision_prompt(self) -> str:
        """Create prompt for Bedrock vision model"""
        ingredient_list = ", ".join(self.andhra_ingredients.keys())
        
        return f"""You are an expert in identifying Andhra Pradesh cuisine ingredients from kitchen images.

Analyze this image and identify ALL visible Andhra ingredients. For each ingredient:
1. Identify the ingredient name (use English names from this list: {ingredient_list})
2. Estimate the quantity (be specific: count pieces, estimate weight in kg/grams)
3. Specify the unit (kg, grams, pieces, bunches, liters, ml, cups, tablespoons, teaspoons)
4. Assign a confidence score from 0.0 to 1.0 based on:
   - Visibility and clarity (0.9-1.0 for very clear)
   - Certainty of identification (0.7-0.9 for confident)
   - Partial visibility or uncertainty (0.5-0.7 for medium confidence)
   - Unclear or ambiguous (below 0.5 for low confidence)
5. Categorize: vegetable, fruit, grain, pulse, spice, dairy, meat, leafy_green, condiment, sweetener, oil, other
6. Assess freshness: fresh, good, moderate, poor, unknown
7. Detect storage location if visible: fridge, pantry, freezer, counter, unknown

Return ONLY a valid JSON array of detected ingredients in this exact format:
[
  {{
    "ingredient_name": "brinjal",
    "quantity": 4,
    "unit": "pieces",
    "confidence_score": 0.92,
    "category": "vegetable",
    "freshness": "fresh",
    "storage_location": "counter"
  }}
]

Important:
- Be thorough - identify ALL visible ingredients
- Use exact ingredient names from the provided list
- Be realistic with quantities
- Assign honest confidence scores
- If no ingredients are visible, return an empty array: []
- Return ONLY the JSON array, no other text"""
    
    def _call_bedrock_vision(self, image_base64: str, prompt: str) -> str:
        """
        Call Bedrock Claude 3 Sonnet with vision capability.
        
        Args:
            image_base64: Base64-encoded image
            prompt: Analysis prompt
        
        Returns:
            Model response text
        """
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "temperature": 0.3,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        }
        
        response = self.bedrock_runtime.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
    
    def _parse_bedrock_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse Bedrock response to extract ingredient detections.
        
        Args:
            response_text: Raw response from Bedrock
        
        Returns:
            List of detected ingredients
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
            detections = json.loads(response_text)
            if not isinstance(detections, list):
                raise ValueError("Response is not a JSON array")
            return detections
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse Bedrock response as JSON: {str(e)}")
    
    def _create_inventory_json(
        self,
        detections: List[Dict[str, Any]],
        session_id: str,
        image_id: str,
        processing_time_ms: int
    ) -> Dict[str, Any]:
        """
        Create Inventory JSON from detections.
        
        Args:
            detections: List of detected ingredients
            session_id: User session identifier
            image_id: Image identifier
            processing_time_ms: Processing time in milliseconds
        
        Returns:
            Complete Inventory JSON
        """
        # Add Telugu names to ingredients
        for detection in detections:
            ingredient_name = detection.get('ingredient_name', '')
            if ingredient_name in self.andhra_ingredients:
                detection['ingredient_name_telugu'] = self.andhra_ingredients[ingredient_name]
        
        inventory = {
            "total_items": len(detections),
            "detection_timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "session_id": session_id,
            "image_id": image_id,
            "ingredients": detections,
            "detection_metadata": {
                "model_version": self.model_id,
                "processing_time_ms": processing_time_ms,
                "image_quality": self._assess_image_quality(detections)
            }
        }
        
        return inventory
    
    def _assess_image_quality(self, detections: List[Dict[str, Any]]) -> str:
        """
        Assess image quality based on detection confidence scores.
        
        Args:
            detections: List of detected ingredients
        
        Returns:
            Quality assessment: excellent, good, fair, poor
        """
        if not detections:
            return "poor"
        
        avg_confidence = sum(d.get('confidence_score', 0) for d in detections) / len(detections)
        
        if avg_confidence >= 0.9:
            return "excellent"
        elif avg_confidence >= 0.75:
            return "good"
        elif avg_confidence >= 0.6:
            return "fair"
        else:
            return "poor"
    
    def filter_by_confidence(self, inventory: Dict[str, Any]) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Filter ingredients by confidence threshold.
        
        Args:
            inventory: Inventory JSON
        
        Returns:
            Tuple of (high_confidence, medium_confidence, low_confidence) ingredient lists
        """
        ingredients = inventory.get('ingredients', [])
        
        high = []
        medium = []
        low = []
        
        for ingredient in ingredients:
            confidence = ingredient.get('confidence_score', 0)
            if confidence >= self.confidence_high:
                high.append(ingredient)
            elif confidence >= self.confidence_medium:
                medium.append(ingredient)
            else:
                low.append(ingredient)
        
        return high, medium, low
    
    def get_confidence_summary(self, inventory: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get summary of confidence levels.
        
        Args:
            inventory: Inventory JSON
        
        Returns:
            Summary with counts and recommendations
        """
        high, medium, low = self.filter_by_confidence(inventory)
        
        return {
            "total_detected": inventory.get('total_items', 0),
            "high_confidence": {
                "count": len(high),
                "threshold": f">= {self.confidence_high}",
                "action": "automatically_included"
            },
            "medium_confidence": {
                "count": len(medium),
                "threshold": f"{self.confidence_medium} - {self.confidence_high}",
                "action": "user_confirmation_needed"
            },
            "low_confidence": {
                "count": len(low),
                "threshold": f"< {self.confidence_medium}",
                "action": "excluded"
            }
        }


if __name__ == "__main__":
    # Example usage
    print("Vision Analyzer for Andhra Kitchen Agent")
    print("=" * 50)
    print(f"Model: {Config.BEDROCK_MODEL_VISION}")
    print(f"Region: {Config.BEDROCK_REGION}")
    print(f"High Confidence Threshold: {Config.VISION_CONFIDENCE_HIGH}")
    print(f"Medium Confidence Threshold: {Config.VISION_CONFIDENCE_MEDIUM}")
    print(f"Max Retries: {Config.VISION_MAX_RETRIES}")
    print("=" * 50)
    
    # Initialize analyzer
    analyzer = VisionAnalyzer()
    print(f"\n✅ VisionAnalyzer initialized")
    print(f"   Andhra ingredients in knowledge base: {len(analyzer.andhra_ingredients)}")
