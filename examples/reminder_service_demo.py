"""
Demo script for ReminderService

Shows how to use the ReminderService to schedule, retrieve, and manage reminders.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.reminder_service import ReminderService
from config.env import Config


def demo_basic_reminder_scheduling():
    """Demonstrate basic reminder scheduling"""
    print("\n" + "=" * 60)
    print("DEMO 1: Basic Reminder Scheduling")
    print("=" * 60)
    
    service = ReminderService()
    
    # Schedule a reminder for tomorrow at 8 AM
    trigger_time = datetime.now(timezone.utc) + timedelta(days=1)
    trigger_time = trigger_time.replace(hour=8, minute=0, second=0, microsecond=0)
    
    print(f"\nScheduling reminder for: {trigger_time.isoformat()}")
    
    try:
        reminder_id = service.schedule_reminder(
            session_id="demo_session_001",
            content="Buy fresh curry leaves at Rythu Bazaar",
            trigger_time=trigger_time,
            reason="Prices are 20-30% cheaper on Wednesdays",
            reminder_type="shopping"
        )
        
        print(f"✅ Reminder scheduled successfully!")
        print(f"   Reminder ID: {reminder_id}")
        print(f"   Trigger Time: {trigger_time.strftime('%A, %B %d at %I:%M %p')}")
        
    except Exception as e:
        print(f"❌ Failed to schedule reminder: {str(e)}")


def demo_price_sensitive_detection():
    """Demonstrate price-sensitive ingredient detection"""
    print("\n" + "=" * 60)
    print("DEMO 2: Price-Sensitive Ingredient Detection")
    print("=" * 60)
    
    service = ReminderService()
    
    # Sample shopping list
    shopping_items = [
        {
            'ingredient_name': 'curry_leaves',
            'market_section': 'spices',
            'quantity': 1,
            'unit': 'bunch'
        },
        {
            'ingredient_name': 'brinjal',
            'market_section': 'vegetables',
            'quantity': 3,
            'unit': 'pieces'
        },
        {
            'ingredient_name': 'rice',
            'market_section': 'grains',
            'quantity': 2,
            'unit': 'kg'
        },
        {
            'ingredient_name': 'fish',
            'market_section': 'meat',
            'quantity': 500,
            'unit': 'grams'
        }
    ]
    
    print("\nAnalyzing shopping list for price-sensitive items...")
    print(f"Total items: {len(shopping_items)}")
    
    suggestions = service.detect_price_sensitive_items(shopping_items)
    
    print(f"\n✅ Found {len(suggestions)} price-sensitive items:")
    
    for i, suggestion in enumerate(suggestions, 1):
        print(f"\n{i}. {suggestion['ingredient'].upper()}")
        print(f"   Content: {suggestion['content']}")
        print(f"   Reason: {suggestion['reason']}")
        print(f"   Best time: {suggestion['trigger_time'].strftime('%A at %I:%M %p')}")


def demo_reminder_retrieval():
    """Demonstrate retrieving pending reminders"""
    print("\n" + "=" * 60)
    print("DEMO 3: Retrieving Pending Reminders")
    print("=" * 60)
    
    service = ReminderService()
    
    session_id = "demo_session_001"
    
    print(f"\nRetrieving reminders for session: {session_id}")
    
    try:
        reminders = service.get_pending_reminders(session_id)
        
        if reminders:
            print(f"✅ Found {len(reminders)} pending reminder(s):")
            
            for i, reminder in enumerate(reminders, 1):
                print(f"\n{i}. Reminder ID: {reminder.get('reminder_id')}")
                print(f"   Content: {reminder.get('content')}")
                print(f"   Reason: {reminder.get('reason')}")
                print(f"   Status: {reminder.get('status')}")
                print(f"   Trigger Time: {reminder.get('trigger_time')}")
        else:
            print("ℹ️  No pending reminders found")
            
    except Exception as e:
        print(f"❌ Failed to retrieve reminders: {str(e)}")


def demo_reminder_dismissal():
    """Demonstrate dismissing a reminder"""
    print("\n" + "=" * 60)
    print("DEMO 4: Dismissing a Reminder")
    print("=" * 60)
    
    service = ReminderService()
    
    # First, get pending reminders
    session_id = "demo_session_001"
    reminders = service.get_pending_reminders(session_id)
    
    if reminders:
        reminder_id = reminders[0].get('reminder_id')
        print(f"\nDismissing reminder: {reminder_id}")
        
        try:
            updated = service.dismiss_reminder(reminder_id, session_id)
            print(f"✅ Reminder dismissed successfully!")
            print(f"   New status: {updated.get('status')}")
            
        except Exception as e:
            print(f"❌ Failed to dismiss reminder: {str(e)}")
    else:
        print("ℹ️  No reminders to dismiss")


def demo_reminder_snooze():
    """Demonstrate snoozing a reminder"""
    print("\n" + "=" * 60)
    print("DEMO 5: Snoozing a Reminder")
    print("=" * 60)
    
    service = ReminderService()
    
    # First, get pending reminders
    session_id = "demo_session_001"
    reminders = service.get_pending_reminders(session_id)
    
    if reminders:
        reminder_id = reminders[0].get('reminder_id')
        old_time = reminders[0].get('trigger_time')
        
        print(f"\nSnoozing reminder: {reminder_id}")
        print(f"Current trigger time: {old_time}")
        
        # Snooze for 24 hours
        snooze_duration = timedelta(hours=24)
        
        try:
            updated = service.snooze_reminder(reminder_id, session_id, snooze_duration)
            print(f"✅ Reminder snoozed successfully!")
            print(f"   New trigger time: {updated.get('trigger_time')}")
            print(f"   Status: {updated.get('status')}")
            
        except Exception as e:
            print(f"❌ Failed to snooze reminder: {str(e)}")
    else:
        print("ℹ️  No reminders to snooze")


def main():
    """Run all demos"""
    print("\n" + "=" * 60)
    print("REMINDER SERVICE DEMO")
    print("=" * 60)
    print(f"\nEnvironment: {Config.ENVIRONMENT}")
    print(f"AWS Region: {Config.AWS_REGION}")
    print(f"Reminders Table: {Config.REMINDERS_TABLE}")
    
    # Note: These demos require actual AWS credentials and resources
    print("\n⚠️  NOTE: These demos require AWS credentials and DynamoDB/EventBridge access")
    print("⚠️  Make sure your .env file is configured correctly")
    
    try:
        # Demo 1: Basic scheduling
        demo_basic_reminder_scheduling()
        
        # Demo 2: Price-sensitive detection
        demo_price_sensitive_detection()
        
        # Demo 3: Retrieval
        # demo_reminder_retrieval()
        
        # Demo 4: Dismissal
        # demo_reminder_dismissal()
        
        # Demo 5: Snooze
        # demo_reminder_snooze()
        
        print("\n" + "=" * 60)
        print("DEMO COMPLETE")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        print("\nMake sure you have:")
        print("1. AWS credentials configured")
        print("2. DynamoDB tables created")
        print("3. EventBridge permissions")
        print("4. .env file with correct values")


if __name__ == "__main__":
    main()
