#!/usr/bin/env python3

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import init_database
from app.services.reminder_email_service import ReminderEmailService

async def test_new_reminder_logic():
    """Test the new reminder logic with real-time calculation."""
    print("🚀 Testing new reminder logic...")
    
    try:
        # Initialize database first
        print("🔧 Initializing database...")
        init_database()
        print("✅ Database initialized successfully")
        
        service = ReminderEmailService()
        print("✅ ReminderEmailService initialized successfully")
        
        # Test the new logic
        print("\n🔍 Testing process_due_reminders with new logic...")
        result = await service.process_due_reminders()
        print(f"Result: {result}")
        
        if result.get('success'):
            print(f"✅ Found {result.get('total_reminders', 0)} reminders")
            print(f"   Sent: {result.get('successful_sends', 0)}")
            print(f"   Failed: {result.get('failed_sends', 0)}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
        
        # Test parse before_due function
        print("\n🔍 Testing beforeDue parsing...")
        test_cases = ['15m', '1h', '2h30m', '1d', '2d12h45m']
        for case in test_cases:
            minutes = service._parse_before_due_to_minutes(case)
            print(f"   '{case}' → {minutes} minutes")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting new reminder logic test...")
    asyncio.run(test_new_reminder_logic())
    print("✨ Test completed!")