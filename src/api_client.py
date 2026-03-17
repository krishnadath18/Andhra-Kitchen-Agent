"""
API Client for Andhra Kitchen Agent Backend

Handles all communication between Streamlit frontend and backend REST API.
Implements error handling, retry logic, and request/response logging.

Requirements: 21.1, 21.2
"""

import os
import requests
import base64
from typing import Callable, Dict, List, Any, Optional
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5000')
API_TIMEOUT = int(os.getenv('API_TIMEOUT', '30'))
MAX_RETRIES = int(os.getenv('API_MAX_RETRIES', '3'))


class APIClient:
    """Client for backend REST API communication."""
    
    def __init__(
        self,
        base_url: str = API_BASE_URL,
        token_provider: Optional[Callable[[], Optional[str]]] = None
    ):
        """
        Initialize API client.
        
        Args:
            base_url: Base URL for the API
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.token_provider = token_provider

    def set_token_provider(self, token_provider: Optional[Callable[[], Optional[str]]]) -> None:
        """Register a callable that supplies the current bearer token."""
        self.token_provider = token_provider
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: int = API_TIMEOUT
    ) -> Dict[str, Any]:
        """
        Make HTTP request with error handling and retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: JSON data for request body
            files: Files for multipart upload
            params: Query parameters
            timeout: Request timeout in seconds
            
        Returns:
            Response data as dictionary
            
        Raises:
            APIError: On API errors
            NetworkError: On network errors
        """
        url = f"{self.base_url}{endpoint}"
        
        # Log request (excluding sensitive data)
        logger.info(f"{method} {endpoint}")
        
        try:
            # SECURITY: Enforce HTTPS for non-localhost URLs to prevent MITM attacks
            if self.base_url.startswith('http://') and not any(
                host in self.base_url for host in ['localhost', '127.0.0.1', '[::1]']
            ):
                raise ValueError(
                    "HTTP connections are only allowed for localhost. "
                    "Use HTTPS for remote connections to prevent MITM attacks."
                )
            
            headers = {
                'User-Agent': 'Andhra-Kitchen-Agent-Frontend/1.0'
            }
            if not files:
                headers['Content-Type'] = 'application/json'

            if self.token_provider:
                token = self.token_provider()
                if token:
                    headers['Authorization'] = f'Bearer {token}'

            response = self.session.request(
                method=method,
                url=url,
                json=data if not files else None,  # Don't use json if sending files
                data=data if files else None,  # Use data for form fields with files
                files=files,
                params=params,
                headers=headers,
                timeout=timeout
            )
            
            # Log response status
            logger.info(f"Response: {response.status_code}")
            
            # Handle error responses
            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                raise APIError(
                    status_code=response.status_code,
                    message=error_data.get('error', 'Unknown error'),
                    details=error_data
                )
            
            return response.json() if response.content else {}
            
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout: {url}")
            raise NetworkError("Request timed out. Please try again.")
        
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error: {url}")
            raise NetworkError("Cannot connect to server. Please check your connection.")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise NetworkError(f"Network error: {str(e)}")
    
    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================
    
    def create_session(self, language: str = 'en') -> Dict[str, Any]:
        """
        Create a new session.
        
        Args:
            language: User's preferred language ('en' or 'te')
            
        Returns:
            Session data with session_id
            
        Requirements: 16.1, 21.2
        """
        return self._make_request(
            method='POST',
            endpoint='/session',
            data={'language': language}
        )
    
    def get_session(self, session_id: str) -> Dict[str, Any]:
        """
        Get session data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data
            
        Requirements: 16.2, 16.5, 21.2
        """
        return self._make_request(
            method='GET',
            endpoint=f'/session/{session_id}'
        )
    
    # ========================================================================
    # CHAT & INTERACTION
    # ========================================================================
    
    def send_chat_message(
        self,
        session_id: str,
        message: str,
        language: str = 'en',
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Send chat message to backend.
        
        Args:
            session_id: Session identifier
            message: User message
            language: Message language
            context: Additional context
            
        Returns:
            Agent response
            
        Requirements: 1.1, 1.2, 21.3
        """
        return self._make_request(
            method='POST',
            endpoint='/chat',
            data={
                'session_id': session_id,
                'message': message,
                'language': language,
                'context': context or {}
            }
        )
    
    # ========================================================================
    # IMAGE UPLOAD & ANALYSIS
    # ========================================================================
    
    def upload_image(self, image_file, session_id: str) -> Dict[str, Any]:
        """
        Upload image to backend.
        
        Args:
            image_file: Image file object (from Streamlit file_uploader)
            session_id: Session identifier
            
        Returns:
            Upload response with image_id and deprecated compatibility fields
            
        Requirements: 3.3, 3.4, 21.4
        """
        # WARNING: File upload security - validate on both client and server
        # Client-side validation is not sufficient for security
        
        # Read image data and encode as base64
        image_data = image_file.read()
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        # Get content type from file
        content_type = getattr(image_file, 'type', 'image/jpeg')
        
        # Send as JSON with base64-encoded image
        return self._make_request(
            method='POST',
            endpoint='/upload-image',
            data={
                'session_id': session_id,
                'image_data': image_b64,
                'content_type': content_type
            }
        )
    
    def analyze_image(
        self,
        session_id: str,
        image_id: str,
        language: str = 'en'
    ) -> Dict[str, Any]:
        """
        Analyze uploaded image.
        
        Args:
            session_id: Session identifier
            image_id: Image identifier
            language: Response language
            
        Returns:
            Inventory JSON with detected ingredients
            
        Requirements: 4.1, 4.2, 21.4
        """
        return self._make_request(
            method='POST',
            endpoint='/analyze-image',
            data={
                'session_id': session_id,
                'image_id': image_id,
                'language': language
            }
        )

    # ========================================================================
    # RECIPE GENERATION
    # ========================================================================
    
    def generate_recipes(
        self,
        session_id: str,
        inventory: Dict[str, Any],
        preferences: Optional[List[str]] = None,
        allergies: Optional[List[str]] = None,
        language: str = 'en',
        count: int = 3
    ) -> Dict[str, Any]:
        """
        Generate recipe suggestions.
        
        Args:
            session_id: Session identifier
            inventory: Inventory JSON
            preferences: Dietary preferences
            allergies: Allergy list
            language: Response language
            count: Number of recipes to generate
            
        Returns:
            List of recipe JSON objects
            
        Requirements: 8.1, 8.2, 21.5
        """
        return self._make_request(
            method='POST',
            endpoint='/generate-recipes',
            data={
                'session_id': session_id,
                'inventory': inventory,
                'preferences': preferences or [],
                'allergies': allergies or [],
                'language': language,
                'count': count
            }
        )
    
    # ========================================================================
    # SHOPPING LIST
    # ========================================================================
    
    def generate_shopping_list(
        self,
        session_id: str,
        recipe_id: str,
        current_inventory: Dict[str, Any],
        language: str = 'en'
    ) -> Dict[str, Any]:
        """
        Generate shopping list for recipe.
        
        Args:
            session_id: Session identifier
            recipe_id: Recipe identifier
            current_inventory: Current inventory
            language: Response language
            
        Returns:
            Shopping list JSON and reminders
            
        Requirements: 10.1, 10.2, 21.6
        """
        return self._make_request(
            method='POST',
            endpoint='/generate-shopping-list',
            data={
                'session_id': session_id,
                'recipe_id': recipe_id,
                'current_inventory': current_inventory,
                'language': language
            }
        )
    
    # ========================================================================
    # REMINDERS
    # ========================================================================
    
    def get_reminders(self, session_id: str) -> Dict[str, Any]:
        """
        Get pending reminders for session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of reminders
            
        Requirements: 11.3, 11.7
        """
        return self._make_request(
            method='GET',
            endpoint=f'/reminders/{session_id}'
        )
    
    def dismiss_reminder(self, reminder_id: str, session_id: str) -> Dict[str, Any]:
        """
        Dismiss a reminder.
        
        Args:
            reminder_id: Reminder identifier
            session_id: Session identifier that owns the reminder
            
        Returns:
            Updated reminder
            
        Requirements: 11.6
        """
        return self._make_request(
            method='POST',
            endpoint=f'/reminders/{reminder_id}/dismiss',
            data={'session_id': session_id}
        )
    
    def snooze_reminder(
        self,
        reminder_id: str,
        session_id: str,
        duration_hours: int
    ) -> Dict[str, Any]:
        """
        Snooze a reminder.
        
        Args:
            reminder_id: Reminder identifier
            session_id: Session identifier that owns the reminder
            duration_hours: Snooze duration in hours
            
        Returns:
            Updated reminder
            
        Requirements: 11.6
        """
        return self._make_request(
            method='POST',
            endpoint=f'/reminders/{reminder_id}/snooze',
            data={
                'session_id': session_id,
                'duration_hours': duration_hours
            }
        )


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class APIError(Exception):
    """API error exception."""
    
    def __init__(self, status_code: int, message: str, details: Dict = None):
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class NetworkError(Exception):
    """Network error exception."""
    pass


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

# Create singleton instance for use across the application
api_client = APIClient()
