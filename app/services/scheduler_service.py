import asyncio
import logging
import os
from datetime import datetime
from typing import Optional
from app.services.reminder_email_service import ReminderEmailService
from app.services.reminder_notification_service import ReminderNotificationService

# Setup file logging for reminder system
def setup_reminder_logger():
    main_logger = logging.getLogger('reminder_system')
    main_logger.setLevel(logging.INFO)
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Create file handler for main system
    log_file = os.path.join(log_dir, 'reminder_system.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger (avoid duplicates)
    if not main_logger.handlers:
        main_logger.addHandler(file_handler)
        main_logger.addHandler(console_handler)
    
    return main_logger

def setup_email_reminder_logger():
    email_logger = logging.getLogger('email_reminders')
    email_logger.setLevel(logging.INFO)
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Create file handler for email reminders
    log_file = os.path.join(log_dir, 'email_reminders.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Add handler to logger (avoid duplicates)
    if not email_logger.handlers:
        email_logger.addHandler(file_handler)
    
    return email_logger

def setup_notification_reminder_logger():
    notification_logger = logging.getLogger('notification_reminders')
    notification_logger.setLevel(logging.INFO)
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Create file handler for notification reminders
    log_file = os.path.join(log_dir, 'notification_reminders.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Add handler to logger (avoid duplicates)
    if not notification_logger.handlers:
        notification_logger.addHandler(file_handler)
    
    return notification_logger

logger = setup_reminder_logger()
email_logger = setup_email_reminder_logger()
notification_logger = setup_notification_reminder_logger()

class SchedulerService:
    def __init__(self):
        self.email_reminder_service = ReminderEmailService()
        self.notification_reminder_service = ReminderNotificationService()
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.check_interval = 60  # Check every 60 seconds
        
    async def start(self):
        """Start the scheduler service."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
            
        self.is_running = True
        self.task = asyncio.create_task(self._run_scheduler())
        logger.info("Scheduler service started")
        
    async def stop(self):
        """Stop the scheduler service."""
        if not self.is_running or not self.task:
            return
            
        self.is_running = False
        self.task.cancel()
        try:
            await self.task
        except asyncio.CancelledError:
            pass
        logger.info("Scheduler service stopped")
        
    async def _run_scheduler(self):
        """Main scheduler loop."""
        logger.info("Starting scheduler loop...")
        
        while self.is_running:
            try:
                await self._check_and_send_reminders()
                
                # Wait for next check interval
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                logger.info("Scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                # Continue running even if there's an error
                await asyncio.sleep(self.check_interval)
                
    async def _check_and_send_reminders(self):
        """Check and send due reminders with detailed logging."""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"🔍 [{current_time}] Starting reminder check cycle...")
            
            # Process email reminders
            email_result = await self.email_reminder_service.process_due_reminders()
            
            if email_result.get('success'):
                total = email_result.get('total_reminders', 0)
                sent = email_result.get('successful_sends', 0)
                failed = email_result.get('failed_sends', 0)
                
                if total > 0:
                    email_logger.info(f"📧 [{current_time}] Email reminders - Processed {total}: {sent} sent successfully, {failed} failed")
                    
                    # Log details if available
                    if hasattr(self.email_reminder_service, '_last_processed_reminders'):
                        for reminder_info in self.email_reminder_service._last_processed_reminders:
                            email_logger.info(f"   📧 Email reminder {reminder_info.get('id', 'unknown')} for task '{reminder_info.get('task_title', 'unknown')}' → User: {reminder_info.get('user_id', 'unknown')}")
                else:
                    email_logger.info(f"ℹ️  [{current_time}] No due email reminders found")
            else:
                error_msg = email_result.get('error', 'Unknown error')
                email_logger.error(f"❌ [{current_time}] Failed to process email reminders: {error_msg}")
            
            # Process notification reminders
            notification_result = await self.notification_reminder_service.process_due_reminders()
            
            if notification_result.get('success'):
                total = notification_result.get('total_reminders', 0)
                sent = notification_result.get('successful_sends', 0)
                failed = notification_result.get('failed_sends', 0)
                
                if total > 0:
                    notification_logger.info(f"📱 [{current_time}] Notification reminders - Processed {total}: {sent} sent successfully, {failed} failed")
                    
                    # Log details if available
                    if hasattr(self.notification_reminder_service, '_last_processed_reminders'):
                        for reminder_info in self.notification_reminder_service._last_processed_reminders:
                            notification_logger.info(f"   📱 Notification reminder {reminder_info.get('id', 'unknown')} for task '{reminder_info.get('task_title', 'unknown')}' → User: {reminder_info.get('user_id', 'unknown')}")
                else:
                    notification_logger.info(f"ℹ️  [{current_time}] No due notification reminders found")
            else:
                error_msg = notification_result.get('error', 'Unknown error')
                notification_logger.error(f"❌ [{current_time}] Failed to process notification reminders: {error_msg}")
                
        except Exception as e:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.error(f"💥 [{current_time}] Exception in reminder check: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

# Global scheduler instance
_scheduler_instance: Optional[SchedulerService] = None

def get_scheduler() -> SchedulerService:
    """Get the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = SchedulerService()
    return _scheduler_instance

async def start_scheduler():
    """Start the global scheduler."""
    scheduler = get_scheduler()
    await scheduler.start()
    
async def stop_scheduler():
    """Stop the global scheduler."""
    scheduler = get_scheduler()
    await scheduler.stop()