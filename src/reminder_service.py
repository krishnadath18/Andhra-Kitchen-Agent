"""
Reminder Service for Andhra Kitchen Agent

Schedules proactive reminders for optimal shopping times using AWS EventBridge
and Lambda. Stores reminder data in DynamoDB and supports dismiss/snooze operations.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# Import configuration
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.env import Config

# Configure CloudWatch logging
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, Config.LOG_LEVEL))

# Add CloudWatch handler if running in AWS environment
if Config.ENVIRONMENT != 'local':
    try:
        import watchtower
        cloudwatch_handler = watchtower.CloudWatchLogHandler(
            log_group='/aws/andhra-kitchen-agent/reminder-service',
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


class ReminderService:
    """
    Schedules and manages proactive reminders for shopping and cooking.
    Uses AWS EventBridge for scheduling and DynamoDB for storage.
    """
    
    def __init__(self):
        """Initialize ReminderService with AWS clients"""
        self.dynamodb = boto3.resource(
            service_name='dynamodb',
            region_name=Config.AWS_REGION
        )
        self.eventbridge = boto3.client(
            service_name='events',
            region_name=Config.AWS_REGION
        )
        self.reminders_table = self.dynamodb.Table(Config.REMINDERS_TABLE)
        
        # Lambda function ARN for reminder execution
        # Format: arn:aws:lambda:region:account-id:function:function-name
        self.lambda_arn = Config.REMINDER_LAMBDA_ARN if hasattr(Config, 'REMINDER_LAMBDA_ARN') else None
        
        logger.info(
            f"ReminderService initialized: "
            f"reminders_table={Config.REMINDERS_TABLE}, "
            f"region={Config.AWS_REGION}"
        )
        
        # Price-sensitive ingredients and their optimal shopping days
        self.price_sensitive_ingredients = {
            "curry_leaves": {
                "best_days": ["wednesday"],
                "reason": "Fresh stock arrives on Wednesdays at Rythu Bazaar",
                "price_difference": "20-30% cheaper"
            },
            "vegetables": {
                "best_days": ["saturday", "sunday"],
                "reason": "Weekend Rythu Bazaar has best prices",
                "price_difference": "15-25% cheaper"
            },
            "leafy_greens": {
                "best_days": ["wednesday", "saturday"],
                "reason": "Fresh arrivals at Rythu Bazaar",
                "price_difference": "20-30% cheaper"
            },
            "fish": {
                "best_days": ["tuesday", "friday"],
                "reason": "Fresh catch days at Benz Circle market",
                "price_difference": "30-40% cheaper"
            }
        }
    
    def schedule_reminder(
        self,
        session_id: str,
        content: str,
        trigger_time: datetime,
        reason: str,
        reminder_type: str = "shopping"
    ) -> str:
        """
        Schedule a reminder for a specific time.
        
        Implements Requirements 11.1, 11.2, 11.3, 11.4, 11.5:
        - Detects price-sensitive ingredients
        - Schedules reminders using EventBridge
        - Stores reminder content in DynamoDB
        - Includes reminder content and reason
        
        Args:
            session_id: User session identifier
            content: Reminder message content
            trigger_time: When to trigger the reminder
            reason: Reason for the reminder
            reminder_type: Type of reminder ('shopping', 'cooking', 'festival')
        
        Returns:
            reminder_id: Unique identifier for the scheduled reminder
        
        Raises:
            Exception: If scheduling fails
        """
        # Generate unique reminder ID
        reminder_id = f"rem_{uuid.uuid4().hex[:12]}"
        
        logger.info(
            f"Scheduling reminder: session_id={session_id}, "
            f"reminder_id={reminder_id}, trigger_time={trigger_time.isoformat()}, "
            f"type={reminder_type}"
        )
        
        try:
            # Store reminder in DynamoDB first
            self.store_reminder({
                "session_id": session_id,
                "reminder_id": reminder_id,
                "content": content,
                "reason": reason,
                "reminder_type": reminder_type,
                "trigger_time": trigger_time.isoformat() + "Z",
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat() + "Z",
                "eventbridge_rule_name": f"kitchen-agent-reminder-{reminder_id}"
            })
            
            # Create EventBridge rule for scheduling
            self.create_eventbridge_rule(reminder_id, trigger_time, session_id, content, reason)
            
            logger.info(
                f"Reminder scheduled successfully: session_id={session_id}, "
                f"reminder_id={reminder_id}"
            )
            
            return reminder_id
            
        except Exception as e:
            logger.error(
                f"Failed to schedule reminder: session_id={session_id}, "
                f"reminder_id={reminder_id}, error={str(e)}"
            )
            raise Exception(f"Failed to schedule reminder: {str(e)}")
    
    def create_eventbridge_rule(
        self,
        reminder_id: str,
        trigger_time: datetime,
        session_id: str,
        content: str,
        reason: str
    ) -> None:
        """
        Create an EventBridge rule to trigger reminder at specified time.
        
        Implements Requirement 11.2: Schedule reminders using EventBridge
        
        Args:
            reminder_id: Unique reminder identifier
            trigger_time: When to trigger the reminder
            session_id: User session identifier
            content: Reminder content
            reason: Reminder reason
        
        Raises:
            Exception: If EventBridge rule creation fails
        """
        rule_name = f"kitchen-agent-reminder-{reminder_id}"
        
        # Create cron expression for the trigger time
        # Format: cron(minutes hours day month ? year)
        cron_expression = (
            f"cron({trigger_time.minute} {trigger_time.hour} "
            f"{trigger_time.day} {trigger_time.month} ? {trigger_time.year})"
        )
        
        try:
            # Create the rule
            self.eventbridge.put_rule(
                Name=rule_name,
                ScheduleExpression=cron_expression,
                State='ENABLED',
                Description=f"Reminder for session {session_id}: {content[:50]}"
            )
            
            # Add Lambda target if ARN is configured
            if self.lambda_arn:
                self.eventbridge.put_targets(
                    Rule=rule_name,
                    Targets=[
                        {
                            'Id': '1',
                            'Arn': self.lambda_arn,
                            'Input': json.dumps({
                                'reminder_id': reminder_id,
                                'session_id': session_id,
                                'content': content,
                                'reason': reason
                            })
                        }
                    ]
                )
            
            logger.info(
                f"EventBridge rule created: rule_name={rule_name}, "
                f"trigger_time={trigger_time.isoformat()}"
            )
            
        except ClientError as e:
            logger.error(
                f"Failed to create EventBridge rule: rule_name={rule_name}, "
                f"error={str(e)}"
            )
            raise Exception(f"Failed to create EventBridge rule: {str(e)}")
    
    def store_reminder(self, reminder: Dict[str, Any]) -> None:
        """
        Store reminder in DynamoDB.
        
        Implements Requirement 11.7: Store reminders in DynamoDB with 7-day TTL
        
        Args:
            reminder: Reminder data dictionary
        
        Raises:
            Exception: If DynamoDB write fails
        """
        try:
            # Calculate TTL (7 days from now)
            ttl_timestamp = int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
            reminder['expiry_timestamp'] = ttl_timestamp
            
            # Write to DynamoDB
            self.reminders_table.put_item(Item=reminder)
            
            logger.info(
                f"Reminder stored in DynamoDB: session_id={reminder.get('session_id')}, "
                f"reminder_id={reminder.get('reminder_id')}, ttl={ttl_timestamp}"
            )
            
        except ClientError as e:
            logger.error(
                f"Failed to store reminder: reminder_id={reminder.get('reminder_id')}, "
                f"error={str(e)}"
            )
            raise Exception(f"Failed to store reminder: {str(e)}")
    
    def get_pending_reminders(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Query pending reminders for a session.
        
        Implements Requirement 11.3: Retrieve pending reminders for display
        
        Args:
            session_id: User session identifier
        
        Returns:
            List of pending reminder dictionaries
        """
        try:
            response = self.reminders_table.query(
                KeyConditionExpression='session_id = :sid',
                FilterExpression='#status IN (:pending, :delivered)',
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':sid': session_id,
                    ':pending': 'pending',
                    ':delivered': 'delivered'
                }
            )
            
            reminders = response.get('Items', [])
            
            logger.info(
                f"Retrieved pending reminders: session_id={session_id}, "
                f"count={len(reminders)}"
            )
            
            return reminders
            
        except ClientError as e:
            logger.error(
                f"Failed to retrieve reminders: session_id={session_id}, "
                f"error={str(e)}"
            )
            return []
    
    def dismiss_reminder(self, reminder_id: str, session_id: str) -> Dict[str, Any]:
        """
        Dismiss a reminder by marking it as dismissed.
        
        Implements Requirement 11.6: Support dismiss operation
        
        Args:
            reminder_id: Unique reminder identifier
            session_id: User session identifier
        
        Returns:
            Updated reminder data
        
        Raises:
            Exception: If update fails
        """
        try:
            response = self.reminders_table.update_item(
                Key={
                    'session_id': session_id,
                    'reminder_id': reminder_id
                },
                UpdateExpression='SET #status = :dismissed, updated_at = :now',
                ConditionExpression='attribute_exists(reminder_id)',
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':dismissed': 'dismissed',
                    ':now': datetime.now(timezone.utc).isoformat() + "Z"
                },
                ReturnValues='ALL_NEW'
            )
            
            updated_reminder = response.get('Attributes', {})
            
            logger.info(
                f"Reminder dismissed: session_id={session_id}, "
                f"reminder_id={reminder_id}"
            )
            
            return updated_reminder
            
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') == 'ConditionalCheckFailedException':
                raise ValueError("Reminder not found") from e
            logger.error(
                f"Failed to dismiss reminder: session_id={session_id}, "
                f"reminder_id={reminder_id}, error={str(e)}"
            )
            raise Exception(f"Failed to dismiss reminder: {str(e)}")
    
    def snooze_reminder(
        self,
        reminder_id: str,
        session_id: str,
        duration: timedelta
    ) -> Dict[str, Any]:
        """
        Snooze a reminder by rescheduling it for later.
        
        Implements Requirement 11.6: Support snooze operation
        
        Args:
            reminder_id: Unique reminder identifier
            session_id: User session identifier
            duration: How long to snooze (timedelta)
        
        Returns:
            Updated reminder data with new trigger time
        
        Raises:
            Exception: If snooze operation fails
        """
        try:
            # Get current reminder
            response = self.reminders_table.get_item(
                Key={
                    'session_id': session_id,
                    'reminder_id': reminder_id
                }
            )
            
            if 'Item' not in response:
                raise ValueError(f"Reminder not found: {reminder_id}")
            
            reminder = response['Item']
            old_trigger_time = datetime.fromisoformat(
                reminder['trigger_time'].replace('Z', '+00:00')
            )
            
            # Calculate new trigger time
            new_trigger_time = datetime.now(timezone.utc) + duration
            
            # Update reminder in DynamoDB
            update_response = self.reminders_table.update_item(
                Key={
                    'session_id': session_id,
                    'reminder_id': reminder_id
                },
                UpdateExpression='SET #status = :snoozed, trigger_time = :new_time, updated_at = :now',
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':snoozed': 'snoozed',
                    ':new_time': new_trigger_time.isoformat() + "Z",
                    ':now': datetime.now(timezone.utc).isoformat() + "Z"
                },
                ReturnValues='ALL_NEW'
            )
            
            # Delete old EventBridge rule
            old_rule_name = reminder.get('eventbridge_rule_name')
            if old_rule_name:
                try:
                    # Remove targets first
                    self.eventbridge.remove_targets(
                        Rule=old_rule_name,
                        Ids=['1']
                    )
                    # Delete rule
                    self.eventbridge.delete_rule(Name=old_rule_name)
                    logger.info(f"Deleted old EventBridge rule: {old_rule_name}")
                except ClientError as e:
                    logger.warning(
                        f"Failed to delete old EventBridge rule: {old_rule_name}, "
                        f"error={str(e)}"
                    )
            
            # Create new EventBridge rule with new time
            self.create_eventbridge_rule(
                reminder_id,
                new_trigger_time,
                session_id,
                reminder['content'],
                reminder['reason']
            )
            
            updated_reminder = update_response.get('Attributes', {})
            
            logger.info(
                f"Reminder snoozed: session_id={session_id}, "
                f"reminder_id={reminder_id}, "
                f"old_time={old_trigger_time.isoformat()}, "
                f"new_time={new_trigger_time.isoformat()}"
            )
            
            return updated_reminder
            
        except ClientError as e:
            logger.error(
                f"Failed to snooze reminder: session_id={session_id}, "
                f"reminder_id={reminder_id}, error={str(e)}"
            )
            raise Exception(f"Failed to snooze reminder: {str(e)}")
    
    def detect_price_sensitive_items(
        self,
        shopping_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect price-sensitive ingredients in shopping list and generate reminder suggestions.
        
        Implements Requirement 11.1: Detect price-sensitive ingredients
        
        Args:
            shopping_items: List of shopping items
        
        Returns:
            List of reminder suggestions with optimal shopping times
        """
        suggestions = []
        
        for item in shopping_items:
            ingredient_name = item.get('ingredient_name', '').lower()
            section = item.get('market_section', '')
            
            # Check if ingredient is price-sensitive
            price_info = None
            if ingredient_name in self.price_sensitive_ingredients:
                price_info = self.price_sensitive_ingredients[ingredient_name]
            elif section in self.price_sensitive_ingredients:
                price_info = self.price_sensitive_ingredients[section]
            
            if price_info:
                # Calculate next optimal shopping day
                best_days = price_info['best_days']
                next_day = self._get_next_optimal_day(best_days)
                
                suggestions.append({
                    'ingredient': ingredient_name,
                    'content': f"Buy {ingredient_name} on {next_day.strftime('%A')}",
                    'reason': f"{price_info['reason']} ({price_info['price_difference']})",
                    'trigger_time': next_day,
                    'reminder_type': 'shopping'
                })
        
        logger.info(
            f"Detected price-sensitive items: count={len(suggestions)}"
        )
        
        return suggestions
    
    def _get_next_optimal_day(self, best_days: List[str]) -> datetime:
        """
        Calculate the next occurrence of an optimal shopping day.
        
        Args:
            best_days: List of day names (e.g., ['wednesday', 'saturday'])
        
        Returns:
            datetime for the next optimal day at 8:00 AM
        """
        # Map day names to weekday numbers (0=Monday, 6=Sunday)
        day_map = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        today = datetime.now(timezone.utc)
        current_weekday = today.weekday()
        
        # Find the nearest optimal day
        target_weekdays = [day_map[day.lower()] for day in best_days if day.lower() in day_map]
        
        if not target_weekdays:
            # Default to tomorrow if no valid days
            return today + timedelta(days=1)
        
        # Find the next occurrence
        days_ahead = []
        for target_day in target_weekdays:
            if target_day > current_weekday:
                days_ahead.append(target_day - current_weekday)
            else:
                days_ahead.append(7 - current_weekday + target_day)
        
        next_day = today + timedelta(days=min(days_ahead))
        
        # Set time to 8:00 AM
        next_day = next_day.replace(hour=8, minute=0, second=0, microsecond=0)
        
        return next_day


if __name__ == "__main__":
    # Example usage
    print("Reminder Service for Andhra Kitchen Agent")
    print("=" * 50)
    print(f"Reminders Table: {Config.REMINDERS_TABLE}")
    print(f"Region: {Config.AWS_REGION}")
    print("=" * 50)
    
    # Initialize service
    service = ReminderService()
    print(f"\n✅ ReminderService initialized")
    print(f"   Price-sensitive ingredients tracked: {len(service.price_sensitive_ingredients)}")
