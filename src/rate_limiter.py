"""
Rate Limiter for Andhra Kitchen Agent

Implements per-session rate limiting to prevent abuse and DoS attacks.
Uses DynamoDB to track request counts per session per endpoint.
"""

import boto3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import logging
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.env import Config

logger = logging.getLogger(__name__)

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name=Config.AWS_REGION)


class RateLimiter:
    """
    Per-session rate limiter using DynamoDB.
    
    Tracks request counts per session per endpoint within time windows.
    Returns rate limit status and retry-after time when limit exceeded.
    """
    
    @dataclass(frozen=True)
    class RateLimitResult:
        allowed: bool
        retry_after_seconds: Optional[int]
        requests_limit: int
        remaining: int
        reset_time: str
        http_status: Optional[int] = None

        def __post_init__(self):
            if self.http_status is None:
                object.__setattr__(self, "http_status", 200 if self.allowed else 429)

    # Rate limit configuration per endpoint
    # Format: {endpoint: {'requests': max_requests, 'window': seconds}}
    RATE_LIMITS = {
        '/chat': {'requests': 50, 'window': 3600},              # 50 per hour
        '/analyze-image': {'requests': 10, 'window': 3600},     # 10 per hour
        '/generate-recipes': {'requests': 20, 'window': 3600},  # 20 per hour
        '/generate-shopping-list': {'requests': 15, 'window': 3600},  # 15 per hour
        '/upload-image': {'requests': 20, 'window': 3600},      # 20 per hour
        'default': {'requests': 100, 'window': 3600}            # 100 per hour default
    }
    
    def __init__(self, table_name: Optional[str] = None):
        """
        Initialize rate limiter.
        
        Args:
            table_name: DynamoDB table name for rate limits (optional)
        """
        self.table_name = table_name or 'kitchen-agent-rate-limits-dev'
        current_env = os.environ.get("ENVIRONMENT", Config.ENVIRONMENT)
        self.fail_closed = os.getenv(
            "RATE_LIMITER_FAIL_CLOSED",
            "true" if current_env == "prod" else "false"
        ).lower() == "true"
        self.retry_after_seconds = int(
            os.getenv(
                "RATE_LIMITER_RETRY_AFTER_SECONDS",
                str(Config.RATE_LIMITER_RETRY_AFTER_SECONDS)
            )
        )
        
        # Try to get or create table
        try:
            self.table = dynamodb.Table(self.table_name)
            # Test table exists
            self.table.load()
        except Exception as e:
            logger.warning(f"Rate limit table not found: {self.table_name}. Rate limiting disabled.")
            self.table = None
    def check_rate_limit(
        self,
        session_id: str,
        endpoint: str
    ) -> "RateLimiter.RateLimitResult":
        """
        Check if session has exceeded rate limit for endpoint.
        
        Args:
            session_id: Session identifier
            endpoint: API endpoint path
        
        Returns:
            Structured rate-limit status.
        """
        limit_config = self.RATE_LIMITS.get(endpoint, self.RATE_LIMITS['default'])
        max_requests = limit_config['requests']
        window_seconds = limit_config['window']
        current_time = datetime.now(timezone.utc)

        if not self.table:
            env = os.environ.get("ENVIRONMENT", "dev")
            reset_time = self._format_reset_time(current_time, window_seconds)
            if env == "prod" and self.fail_closed:
                logger.critical(
                    "Rate limit table unavailable in production - denying request for safety. "
                    f"endpoint={endpoint}, session_id={session_id}"
                )
                return self.RateLimitResult(
                    allowed=False,
                    retry_after_seconds=self.retry_after_seconds,
                    requests_limit=max_requests,
                    remaining=0,
                    reset_time=reset_time,
                    http_status=503,
                )

            logger.warning("Rate limit table unavailable - allowing request in dev mode.")
            return self.RateLimitResult(
                allowed=True,
                retry_after_seconds=None,
                requests_limit=max_requests,
                remaining=max_requests,
                reset_time=reset_time,
                http_status=200,
            )
        
        try:
            # Get current rate limit data
            response = self.table.get_item(
                Key={
                    'session_id': session_id,
                    'endpoint': endpoint
                }
            )
            
            if 'Item' in response:
                item = response['Item']
                window_start = datetime.fromisoformat(item['window_start'])
                request_count = int(item['request_count'])
                
                # Check if window has expired
                window_age = (current_time - window_start).total_seconds()
                
                if window_age > window_seconds:
                    # Window expired - reset counter
                    self._reset_window(session_id, endpoint, current_time)
                    return self.RateLimitResult(
                        allowed=True,
                        retry_after_seconds=None,
                        requests_limit=max_requests,
                        remaining=max_requests - 1,
                        reset_time=self._format_reset_time(current_time, window_seconds),
                        http_status=200,
                    )
                
                # Check if limit exceeded
                if request_count >= max_requests:
                    # Calculate retry-after time
                    retry_after = int(window_seconds - window_age)
                    logger.warning(
                        f"Rate limit exceeded: session_id={session_id}, "
                        f"endpoint={endpoint}, count={request_count}/{max_requests}"
                    )
                    return self.RateLimitResult(
                        allowed=False,
                        retry_after_seconds=retry_after,
                        requests_limit=max_requests,
                        remaining=0,
                        reset_time=self._format_reset_time(window_start, window_seconds),
                        http_status=429,
                    )
                
                # Increment counter
                self._increment_counter(session_id, endpoint)
                return self.RateLimitResult(
                    allowed=True,
                    retry_after_seconds=None,
                    requests_limit=max_requests,
                    remaining=max_requests - (request_count + 1),
                    reset_time=self._format_reset_time(window_start, window_seconds),
                    http_status=200,
                )
            
            else:
                # First request in window - create entry
                self._reset_window(session_id, endpoint, current_time)
                return self.RateLimitResult(
                    allowed=True,
                    retry_after_seconds=None,
                    requests_limit=max_requests,
                    remaining=max_requests - 1,
                    reset_time=self._format_reset_time(current_time, window_seconds),
                    http_status=200,
                )
        
        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}", exc_info=True)
            reset_time = self._format_reset_time(current_time, window_seconds)
            if os.environ.get("ENVIRONMENT", "dev") == "prod" and self.fail_closed:
                logger.critical(
                    "Rate limiter failed closed in production: "
                    f"session_id={session_id}, endpoint={endpoint}, error={e}"
                )
                return self.RateLimitResult(
                    allowed=False,
                    retry_after_seconds=self.retry_after_seconds,
                    requests_limit=max_requests,
                    remaining=0,
                    reset_time=reset_time,
                    http_status=503,
                )

            logger.warning("Rate limiter error in non-prod mode - allowing request.")
            return self.RateLimitResult(
                allowed=True,
                retry_after_seconds=None,
                requests_limit=max_requests,
                remaining=max_requests,
                reset_time=reset_time,
                http_status=200,
            )

    @staticmethod
    def _format_reset_time(window_start: datetime, window_seconds: int) -> str:
        reset_time = window_start + timedelta(seconds=window_seconds)
        return reset_time.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    
    def _reset_window(
        self,
        session_id: str,
        endpoint: str,
        window_start: datetime
    ):
        """
        Reset rate limit window for session/endpoint.
        
        Args:
            session_id: Session identifier
            endpoint: API endpoint path
            window_start: Start time of new window
        """
        try:
            # Get window duration for TTL
            limit_config = self.RATE_LIMITS.get(endpoint, self.RATE_LIMITS['default'])
            window_seconds = limit_config['window']
            
            # Calculate TTL (window end + 1 day buffer)
            ttl = int((window_start + timedelta(seconds=window_seconds + 86400)).timestamp())
            
            self.table.put_item(
                Item={
                    'session_id': session_id,
                    'endpoint': endpoint,
                    'request_count': 1,
                    'window_start': window_start.isoformat(),
                    'ttl': ttl
                }
            )
        except Exception as e:
            logger.error(f"Failed to reset rate limit window: {str(e)}", exc_info=True)
    
    def _increment_counter(
        self,
        session_id: str,
        endpoint: str
    ):
        """
        Increment request counter for session/endpoint.
        
        Args:
            session_id: Session identifier
            endpoint: API endpoint path
        """
        try:
            self.table.update_item(
                Key={
                    'session_id': session_id,
                    'endpoint': endpoint
                },
                UpdateExpression='SET request_count = request_count + :inc',
                ExpressionAttributeValues={':inc': 1}
            )
        except Exception as e:
            logger.error(f"Failed to increment rate limit counter: {str(e)}", exc_info=True)
    
    def get_rate_limit_info(
        self,
        session_id: str,
        endpoint: str
    ) -> Dict:
        """
        Get current rate limit status for session/endpoint.
        
        Args:
            session_id: Session identifier
            endpoint: API endpoint path
        
        Returns:
            Dictionary with rate limit information
        """
        if not self.table:
            return {
                'enabled': False,
                'message': 'Rate limiting disabled'
            }
        
        limit_config = self.RATE_LIMITS.get(endpoint, self.RATE_LIMITS['default'])
        
        try:
            response = self.table.get_item(
                Key={
                    'session_id': session_id,
                    'endpoint': endpoint
                }
            )
            
            if 'Item' in response:
                item = response['Item']
                window_start = datetime.fromisoformat(item['window_start'])
                request_count = int(item['request_count'])
                
                window_age = (datetime.now(timezone.utc) - window_start).total_seconds()
                remaining_time = int(limit_config['window'] - window_age)
                
                return {
                    'enabled': True,
                    'endpoint': endpoint,
                    'limit': limit_config['requests'],
                    'window_seconds': limit_config['window'],
                    'current_count': request_count,
                    'remaining': max(0, limit_config['requests'] - request_count),
                    'resets_in_seconds': max(0, remaining_time)
                }
            else:
                return {
                    'enabled': True,
                    'endpoint': endpoint,
                    'limit': limit_config['requests'],
                    'window_seconds': limit_config['window'],
                    'current_count': 0,
                    'remaining': limit_config['requests'],
                    'resets_in_seconds': limit_config['window']
                }
        
        except Exception as e:
            logger.error(f"Failed to get rate limit info: {str(e)}", exc_info=True)
            return {
                'enabled': False,
                'error': str(e)
            }
    
    @classmethod
    def create_rate_limit_table(cls, table_name: str = 'kitchen-agent-rate-limits-dev'):
        """
        Create DynamoDB table for rate limiting.
        
        Args:
            table_name: Name of the table to create
        
        Returns:
            Table resource
        """
        try:
            table = dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {'AttributeName': 'session_id', 'KeyType': 'HASH'},   # Partition key
                    {'AttributeName': 'endpoint', 'KeyType': 'RANGE'}     # Sort key
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'session_id', 'AttributeType': 'S'},
                    {'AttributeName': 'endpoint', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST',  # On-demand billing
                Tags=[
                    {'Key': 'Project', 'Value': 'Andhra-Kitchen-Agent'},
                    {'Key': 'Purpose', 'Value': 'Rate-Limiting'}
                ]
            )
            
            # Wait for table to be created
            table.wait_until_exists()
            
            # Enable TTL on the ttl attribute
            dynamodb_client = boto3.client('dynamodb', region_name=Config.AWS_REGION)
            dynamodb_client.update_time_to_live(
                TableName=table_name,
                TimeToLiveSpecification={
                    'Enabled': True,
                    'AttributeName': 'ttl'
                }
            )
            
            logger.info(f"Created rate limit table: {table_name}")
            return table
        
        except Exception as e:
            logger.error(f"Failed to create rate limit table: {str(e)}", exc_info=True)
            raise


# Global rate limiter instance
rate_limiter = RateLimiter()


def check_rate_limit(session_id: str, endpoint: str) -> RateLimiter.RateLimitResult:
    """
    Convenience function to check rate limit.
    
    Args:
        session_id: Session identifier
        endpoint: API endpoint path
    
    Returns:
        Structured rate-limit status.
    """
    return rate_limiter.check_rate_limit(session_id, endpoint)


if __name__ == "__main__":
    # Test rate limiter
    print("Rate Limiter - Test Suite")
    print("=" * 50)
    
    # Test configuration
    print("\nRate Limit Configuration:")
    for endpoint, config in RateLimiter.RATE_LIMITS.items():
        print(f"  {endpoint}: {config['requests']} requests per {config['window']}s")
    
    # Test rate limit check (without DynamoDB)
    print("\nTesting rate limit check (table not required):")
    limiter = RateLimiter('test-table-does-not-exist')
    result = limiter.check_rate_limit('test_session', '/chat')
    print(f"  Allowed: {result.allowed}, Retry After: {result.retry_after_seconds}")
    
    print("\n" + "=" * 50)
    print("Note: To fully test rate limiting, create the DynamoDB table:")
    print("  python -c 'from src.rate_limiter import RateLimiter; RateLimiter.create_rate_limit_table()'")
