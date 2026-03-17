"""
Environment Configuration for Andhra Kitchen Agent

This module manages environment variables and AWS configuration.
Load environment variables from .env file or system environment.
"""

import os
from urllib.parse import urlparse
from pathlib import Path
from typing import Optional


# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class Config:
    """Configuration class for Andhra Kitchen Agent"""
    
    # AWS Configuration
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-south-1")
    AWS_ACCOUNT_ID: str = os.getenv("AWS_ACCOUNT_ID", "")
    
    # AWS Service Endpoints
    API_ENDPOINT: str = os.getenv("API_ENDPOINT", "")

    # Cognito Configuration
    COGNITO_REGION: str = os.getenv("COGNITO_REGION", os.getenv("AWS_REGION", "ap-south-1"))
    COGNITO_USER_POOL_ID: str = os.getenv("COGNITO_USER_POOL_ID", "")
    COGNITO_APP_CLIENT_ID: str = os.getenv("COGNITO_APP_CLIENT_ID", "")
    
    # DynamoDB Tables
    SESSIONS_TABLE: str = os.getenv("SESSIONS_TABLE", "kitchen-agent-sessions-dev")
    MARKET_PRICES_TABLE: str = os.getenv("MARKET_PRICES_TABLE", "kitchen-agent-market-prices-dev")
    REMINDERS_TABLE: str = os.getenv("REMINDERS_TABLE", "kitchen-agent-reminders-dev")
    
    # Lambda Configuration
    REMINDER_LAMBDA_ARN: str = os.getenv("REMINDER_LAMBDA_ARN", "")
    
    # S3 Configuration
    IMAGE_BUCKET: str = os.getenv("IMAGE_BUCKET", "")
    IMAGE_EXPIRY_HOURS: int = int(os.getenv("IMAGE_EXPIRY_HOURS", "24"))
    
    # Bedrock Configuration
    BEDROCK_REGION: str = os.getenv("BEDROCK_REGION", "ap-south-1")
    BEDROCK_MODEL_VISION: str = os.getenv(
        "BEDROCK_MODEL_VISION",
        "anthropic.claude-3-sonnet-20240229-v1:0"
    )
    BEDROCK_MODEL_CHAT: str = os.getenv(
        "BEDROCK_MODEL_CHAT",
        "anthropic.claude-3-haiku-20240307-v1:0"
    )
    BEDROCK_MODEL_RECIPE: str = os.getenv(
        "BEDROCK_MODEL_RECIPE",
        "anthropic.claude-3-haiku-20240307-v1:0"
    )
    
    # Vision Analyzer Configuration
    VISION_CONFIDENCE_HIGH: float = float(os.getenv("VISION_CONFIDENCE_HIGH", "0.7"))
    VISION_CONFIDENCE_MEDIUM: float = float(os.getenv("VISION_CONFIDENCE_MEDIUM", "0.5"))
    VISION_MAX_RETRIES: int = int(os.getenv("VISION_MAX_RETRIES", "3"))
    VISION_TIMEOUT_SECONDS: int = int(os.getenv("VISION_TIMEOUT_SECONDS", "10"))
    
    # Recipe Generator Configuration
    RECIPE_MIN_COUNT: int = int(os.getenv("RECIPE_MIN_COUNT", "2"))
    RECIPE_MAX_COUNT: int = int(os.getenv("RECIPE_MAX_COUNT", "5"))
    RECIPE_MAX_PREP_TIME: int = int(os.getenv("RECIPE_MAX_PREP_TIME", "30"))
    RECIPE_LOW_OIL_MAX_TBSP: float = float(os.getenv("RECIPE_LOW_OIL_MAX_TBSP", "2.0"))
    
    # Session Configuration
    SESSION_TTL_DAYS: int = int(os.getenv("SESSION_TTL_DAYS", "7"))
    
    # API Configuration
    API_RATE_LIMIT: int = int(os.getenv("API_RATE_LIMIT", "100"))
    API_BURST_LIMIT: int = int(os.getenv("API_BURST_LIMIT", "20"))
    MAX_REQUEST_SIZE_BYTES: int = int(os.getenv("MAX_REQUEST_SIZE_BYTES", str(1024 * 1024)))
    MAX_UPLOAD_REQUEST_SIZE_BYTES: int = int(
        os.getenv("MAX_UPLOAD_REQUEST_SIZE_BYTES", str(14 * 1024 * 1024))
    )
    
    # Application Configuration
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "dev")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    REQUIRE_HTTPS: bool = os.getenv("REQUIRE_HTTPS", "true").lower() == "true"
    HTTPS_REDIRECT_ENABLED: bool = os.getenv("HTTPS_REDIRECT_ENABLED", "false").lower() == "true"
    
    # Security Configuration
    # WARNING: ALLOWED_ORIGIN controls CORS and MUST be set explicitly in production.
    # Default None is only acceptable for local development (backend-only, no browser access).
    # SECURE ALTERNATIVE: Set ALLOWED_ORIGIN='https://yourdomain.com' in production env vars.
    _allowed_origin_env = os.getenv("ALLOWED_ORIGIN")
    ALLOWED_ORIGIN: Optional[str] = _allowed_origin_env
    RATE_LIMITER_FAIL_CLOSED: bool = os.getenv(
        "RATE_LIMITER_FAIL_CLOSED",
        "true" if ENVIRONMENT == "prod" else "false"
    ).lower() == "true"
    RATE_LIMITER_RETRY_AFTER_SECONDS: int = int(
        os.getenv("RATE_LIMITER_RETRY_AFTER_SECONDS", "60")
    )
    INPUT_VALIDATION_STRICT: bool = os.getenv("INPUT_VALIDATION_STRICT", "true").lower() == "true"
    MAX_WHITESPACE_RATIO: float = float(os.getenv("MAX_WHITESPACE_RATIO", "0.5"))
    SESSION_ID_STRICT_VALIDATION: bool = os.getenv(
        "SESSION_ID_STRICT_VALIDATION",
        "true"
    ).lower() == "true"
    SESSION_ID_RESERVED_KEYWORDS: str = os.getenv(
        "SESSION_ID_RESERVED_KEYWORDS",
        "admin,root,system,config,superuser,support,ops"
    )
    INCLUDE_RATE_LIMIT_HEADERS: bool = os.getenv(
        "INCLUDE_RATE_LIMIT_HEADERS",
        "true"
    ).lower() == "true"
    CSP_REPORT_URI: str = os.getenv("CSP_REPORT_URI", "")
    CSP_STRICT_MODE: bool = os.getenv("CSP_STRICT_MODE", "true").lower() == "true"
    CSP_ALLOW_INLINE_STYLES: bool = os.getenv(
        "CSP_ALLOW_INLINE_STYLES",
        "true"
    ).lower() == "true"
    PASSWORD_MIN_LENGTH: int = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
    PASSWORD_REQUIRE_SPECIAL: bool = os.getenv(
        "PASSWORD_REQUIRE_SPECIAL",
        "true"
    ).lower() == "true"
    SHOW_PASSWORD_STRENGTH: bool = os.getenv(
        "SHOW_PASSWORD_STRENGTH",
        "true"
    ).lower() == "true"
    
    # Supported Languages
    SUPPORTED_LANGUAGES: list = ["en", "te"]
    DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "en")
    
    # Market Configuration
    DEFAULT_MARKET: str = os.getenv("DEFAULT_MARKET", "rythu_bazaar_vijayawada")
    PRICE_OUTDATED_DAYS: int = int(os.getenv("PRICE_OUTDATED_DAYS", "30"))
    
    # Festival Configuration
    FESTIVAL_MODE_ENABLED: bool = os.getenv("FESTIVAL_MODE_ENABLED", "True").lower() == "true"
    FESTIVAL_SERVING_MULTIPLIER: float = float(os.getenv("FESTIVAL_SERVING_MULTIPLIER", "1.5"))
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate that required configuration is present.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        required_fields = [
            "AWS_ACCOUNT_ID",
            "API_ENDPOINT",
            "IMAGE_BUCKET",
            "COGNITO_USER_POOL_ID",
            "COGNITO_APP_CLIENT_ID",
        ]
        
        missing = []
        for field in required_fields:
            if not getattr(cls, field):
                missing.append(field)
        
        if missing:
            print(f"Missing required configuration: {', '.join(missing)}")
            return False

        cls.validate_cors_config()
        
        return True

    @classmethod
    def validate_cors_config(cls) -> bool:
        """
        Validate CORS configuration.

        In production, the allowed origin must be explicit HTTPS and must never
        be a wildcard.
        """
        allowed_origin = cls.ALLOWED_ORIGIN
        if cls.ENVIRONMENT != "prod":
            return True

        if not allowed_origin:
            raise ValueError(
                "SECURITY ERROR: ALLOWED_ORIGIN must be explicitly set in production. "
                "Set ALLOWED_ORIGIN to your frontend domain (for example, "
                "'https://yourdomain.com')."
            )

        if allowed_origin == "*":
            raise ValueError(
                "SECURITY ERROR: ALLOWED_ORIGIN='*' is not allowed in production. "
                "Use your specific frontend domain instead."
            )

        parsed = urlparse(allowed_origin)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(
                "SECURITY ERROR: ALLOWED_ORIGIN must be a valid HTTPS URL in production "
                f"(received {allowed_origin!r})."
            )

        return True
    
    @classmethod
    def get_dynamodb_table_name(cls, table_type: str) -> str:
        """
        Get DynamoDB table name for the given type.
        
        Args:
            table_type: Type of table ('sessions', 'market_prices', 'reminders')
        
        Returns:
            Full table name
        """
        table_map = {
            'sessions': cls.SESSIONS_TABLE,
            'market_prices': cls.MARKET_PRICES_TABLE,
            'reminders': cls.REMINDERS_TABLE
        }
        
        if table_type not in table_map:
            raise ValueError(f"Unknown table type: {table_type}")
        
        return table_map[table_type]
    
    @classmethod
    def get_bedrock_model(cls, model_type: str) -> str:
        """
        Get Bedrock model identifier for the given type.
        
        Args:
            model_type: Type of model ('vision', 'chat', 'recipe')
        
        Returns:
            Bedrock model identifier
        """
        model_map = {
            'vision': cls.BEDROCK_MODEL_VISION,
            'chat': cls.BEDROCK_MODEL_CHAT,
            'recipe': cls.BEDROCK_MODEL_RECIPE
        }
        
        if model_type not in model_map:
            raise ValueError(f"Unknown model type: {model_type}")
        
        return model_map[model_type]
    
    @classmethod
    def print_config(cls):
        """Print current configuration (excluding sensitive data)"""
        print("Andhra Kitchen Agent Configuration")
        print("=" * 50)
        print(f"Environment: {cls.ENVIRONMENT}")
        print(f"AWS Region: {cls.AWS_REGION}")
        print(f"AWS Account ID: {cls.AWS_ACCOUNT_ID[:4]}****")
        print(f"API Endpoint: {cls.API_ENDPOINT}")
        print(f"Image Bucket: {cls.IMAGE_BUCKET}")
        print(f"Sessions Table: {cls.SESSIONS_TABLE}")
        print(f"Market Prices Table: {cls.MARKET_PRICES_TABLE}")
        print(f"Reminders Table: {cls.REMINDERS_TABLE}")
        print(f"Bedrock Vision Model: {cls.BEDROCK_MODEL_VISION}")
        print(f"Bedrock Chat Model: {cls.BEDROCK_MODEL_CHAT}")
        print(f"Default Language: {cls.DEFAULT_LANGUAGE}")
        print(f"Debug Mode: {cls.DEBUG}")
        print("=" * 50)


# Load environment variables from .env file if it exists
def load_env_file(env_file: Optional[str] = None):
    """
    Load environment variables from .env file.
    
    Args:
        env_file: Path to .env file (default: PROJECT_ROOT/.env)
    """
    if env_file is None:
        env_file = PROJECT_ROOT / ".env"
    else:
        env_file = Path(env_file)
    
    if not env_file.exists():
        print(f"Warning: .env file not found at {env_file}")
        return
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key, value)
    
    print(f"Loaded environment variables from {env_file}")


# Auto-load .env file on module import
env_file_path = PROJECT_ROOT / ".env"
if env_file_path.exists():
    load_env_file()
    Config.ENVIRONMENT = os.getenv("ENVIRONMENT", Config.ENVIRONMENT)
    Config.ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", Config.ALLOWED_ORIGIN)
    Config.REQUIRE_HTTPS = os.getenv(
        "REQUIRE_HTTPS",
        "true" if Config.ENVIRONMENT == "prod" else str(Config.REQUIRE_HTTPS)
    ).lower() == "true"
    Config.HTTPS_REDIRECT_ENABLED = os.getenv(
        "HTTPS_REDIRECT_ENABLED",
        str(Config.HTTPS_REDIRECT_ENABLED)
    ).lower() == "true"
    Config.RATE_LIMITER_FAIL_CLOSED = os.getenv(
        "RATE_LIMITER_FAIL_CLOSED",
        "true" if Config.ENVIRONMENT == "prod" else "false"
    ).lower() == "true"
    Config.RATE_LIMITER_RETRY_AFTER_SECONDS = int(
        os.getenv("RATE_LIMITER_RETRY_AFTER_SECONDS", str(Config.RATE_LIMITER_RETRY_AFTER_SECONDS))
    )
    Config.MAX_REQUEST_SIZE_BYTES = int(
        os.getenv("MAX_REQUEST_SIZE_BYTES", str(Config.MAX_REQUEST_SIZE_BYTES))
    )
    Config.MAX_UPLOAD_REQUEST_SIZE_BYTES = int(
        os.getenv("MAX_UPLOAD_REQUEST_SIZE_BYTES", str(Config.MAX_UPLOAD_REQUEST_SIZE_BYTES))
    )

if Config.ENVIRONMENT == "prod":
    Config.validate_cors_config()


if __name__ == "__main__":
    # Print configuration when run directly
    Config.print_config()
    
    # Validate configuration
    if Config.validate():
        print("\n✅ Configuration is valid")
    else:
        print("\n❌ Configuration is invalid - check required fields")
