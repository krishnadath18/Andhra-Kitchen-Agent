"""
Reminder Executor Lambda Function

Processes EventBridge triggers to deliver reminders.
Stores notification in DynamoDB and cleans up EventBridge rule.

Requirements: 11.2, 11.3, 18.4, 18.5
"""

import json
import os
import boto3
from datetime import datetime, timezone
from typing import Dict, Any
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
events = boto3.client('events')

# Environment variables
REMINDERS_TABLE = os.environ.get('REMINDERS_TABLE', 'kitchen-agent-reminders')

# Get DynamoDB table
reminders_table = dynamodb.Table(REMINDERS_TABLE)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for reminder execution.
    
    Args:
        event: EventBridge event with reminder details
        context: Lambda context
        
    Returns:
        Response with status
        
    Requirements: 11.2, 11.3
    """
    try:
        logger.info(f"Processing reminder event: {json.dumps(event)}")
        
        # Extract reminder details from event
        detail = event.get('detail', {})
        reminder_id = detail.get('reminder_id')
        session_id = detail.get('session_id')
        rule_name = detail.get('rule_name')
        
        if not reminder_id or not session_id:
            logger.error("Missing reminder_id or session_id in event")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required fields'})
            }
        
        # Update reminder status to 'delivered' in DynamoDB
        update_reminder_status(session_id, reminder_id)
        
        # Clean up EventBridge rule
        if rule_name:
            cleanup_eventbridge_rule(rule_name)
        
        logger.info(f"Successfully processed reminder: {reminder_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Reminder delivered successfully',
                'reminder_id': reminder_id
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing reminder: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def update_reminder_status(session_id: str, reminder_id: str) -> None:
    """
    Update reminder status to 'delivered' in DynamoDB.
    
    Args:
        session_id: Session identifier
        reminder_id: Reminder identifier
        
    Requirements: 11.2, 11.3
    """
    try:
        response = reminders_table.update_item(
            Key={
                'session_id': session_id,
                'reminder_id': reminder_id
            },
            UpdateExpression='SET #status = :status, delivered_at = :delivered_at',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': 'delivered',
                ':delivered_at': datetime.now(timezone.utc).isoformat()
            },
            ReturnValues='UPDATED_NEW'
        )
        
        logger.info(f"Updated reminder status: {reminder_id}")
        
    except Exception as e:
        logger.error(f"Error updating reminder status: {str(e)}")
        raise


def cleanup_eventbridge_rule(rule_name: str) -> None:
    """
    Clean up EventBridge rule after execution.
    
    Args:
        rule_name: EventBridge rule name
        
    Requirements: 11.2
    """
    try:
        # Remove targets from rule
        events.remove_targets(
            Rule=rule_name,
            Ids=['1']  # Target ID used when creating the rule
        )
        
        # Delete the rule
        events.delete_rule(Name=rule_name)
        
        logger.info(f"Cleaned up EventBridge rule: {rule_name}")
        
    except events.exceptions.ResourceNotFoundException:
        logger.warning(f"Rule not found: {rule_name}")
    except Exception as e:
        logger.error(f"Error cleaning up EventBridge rule: {str(e)}")
        # Don't raise - rule cleanup is not critical
