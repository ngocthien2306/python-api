from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from pydantic import BaseModel
from app.api.routes.auth import get_current_user
from app.repositories.user import UserRepository
from app.api.routes.auth import get_user_repository
from app.services.reminder_email_service import ReminderEmailService
from app.services.reminder_update_service import ReminderUpdateService

router = APIRouter()

class CreateReminderRequest(BaseModel):
    task_id: str
    before_due: str = "15m"  # e.g., "15m", "1h", "2h30m", "1d"
    message: str = ""
    type: str = "time"
    channel: str = "notification"
    priority: str = "medium"

class ReminderResponse(BaseModel):
    id: str
    user_id: str
    task_id: str
    type: str
    trigger_time: str
    before_due: str
    message: str
    channel: str
    status: str
    priority: str
    created_at: str
    updated_at: str

@router.post("/reminders", response_model=Dict[str, Any])
async def create_reminder(
    request: CreateReminderRequest,
    current_user = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Create a new reminder for a task."""
    try:
        reminder_service = ReminderUpdateService()
        
        success = await reminder_service.create_reminder_for_task(
            task_id=request.task_id,
            user_id=str(current_user.id),
            reminder_data={
                "beforeDue": request.before_due,
                "message": request.message,
                "type": request.type,
                "channel": request.channel,
                "priority": request.priority
            }
        )
        
        if success:
            return {
                "success": True,
                "message": "Reminder created successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create reminder"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create reminder: {str(e)}"
        )

@router.get("/reminders/upcoming", response_model=List[Dict[str, Any]])
async def get_upcoming_reminders(
    hours_ahead: int = 24,
    current_user = Depends(get_current_user)
):
    """Get upcoming reminders for the current user."""
    try:
        reminder_service = ReminderEmailService()
        reminders = await reminder_service.get_upcoming_reminders(
            user_id=str(current_user.id),
            hours_ahead=hours_ahead
        )
        
        return reminders
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get upcoming reminders: {str(e)}"
        )

@router.post("/reminders/process", response_model=Dict[str, Any])
async def process_due_reminders(
    current_user = Depends(get_current_user)
):
    """Manually trigger processing of due reminders (admin only)."""
    try:
        reminder_service = ReminderEmailService()
        result = await reminder_service.process_due_reminders()
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process reminders: {str(e)}"
        )

@router.post("/reminders/test/{user_id}", response_model=Dict[str, Any])
async def send_test_reminder(
    user_id: str,
    current_user = Depends(get_current_user)
):
    """Send a test reminder email to a user."""
    try:
        reminder_service = ReminderEmailService()
        success = await reminder_service.send_test_reminder_email(user_id)
        
        if success:
            return {
                "success": True,
                "message": f"Test reminder email sent to user {user_id}"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to send test reminder email"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test reminder: {str(e)}"
        )