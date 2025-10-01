#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import init_database
from app.services.reminder_email_service import ReminderEmailService

async def test_reminder_service():
    """Test the reminder email service functionality."""
    print("Testing ReminderEmailService...")
    
    try:
        # Initialize database first
        print("🔧 Initializing database...")
        init_database()
        print("✅ Database initialized successfully")
        
        service = ReminderEmailService()
        print("✅ ReminderEmailService initialized successfully")
        
        # Test process_due_reminders method
        print("\n🔍 Testing process_due_reminders...")
        result = await service.process_due_reminders()
        print(f"Result: {result}")
        
        if result.get('success'):
            print(f"✅ Found {result.get('total_reminders', 0)} reminders")
            print(f"   Sent: {result.get('successful_sends', 0)}")
            print(f"   Failed: {result.get('failed_sends', 0)}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
        
        # Test with a sample user (you can replace with a real user ID)
        print("\n🔍 Testing send_test_reminder_email...")
        test_user_id = "68db8ad08abd68e0ebd22453"  # Replace with actual user ID
        test_result = await service.send_test_reminder_email(test_user_id)
        
        if test_result:
            print("✅ Test reminder email sent successfully")
        else:
            print("❌ Failed to send test reminder email")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting reminder email service test...")
    asyncio.run(test_reminder_service())
    print("✨ Test completed!")