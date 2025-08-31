from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user_token
from app.models.user import TokenData
from app.services.ai_processor import AIProcessorService
from app.core.dependencies import (
    get_database_manager, 
    get_user_analytics_service,
    get_reminder_service,
    get_task_service,
    get_schedule_service,
    get_conversation_service
)
from app.schemas.ai_response import ProcessConversationRequest
from app.schemas.database import APIResponse

router = APIRouter()

@router.post("/process-conversation", response_model=APIResponse)
async def process_conversation(
    request: ProcessConversationRequest,
    db_manager = Depends(get_database_manager),
):
    try:
        ai_processor = AIProcessorService(db_manager)
        result = ai_processor.process_conversation(request)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "AI Assistant API"}

@router.get("/stats/{user_id}")
async def get_user_stats(
    user_id: str,
    analytics_service = Depends(get_user_analytics_service),
    current_user_token: TokenData = Depends(get_current_user_token)
):
    """Get comprehensive user statistics using the new analytics service"""
    try:
        # Use the new UserAnalyticsService instead of direct repo access
        result = analytics_service.get_comprehensive_user_summary(user_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to get user stats"))
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ NEW ROUTES USING REFACTORED SERVICES ============

@router.get("/tasks/{user_id}")
async def get_user_tasks(
    user_id: str,
    status: str = None,
    category: str = None,
    priority: str = None,
    limit: int = 20,
    task_service = Depends(get_task_service),
    current_user_token: TokenData = Depends(get_current_user_token)
):
    """Get user tasks with filters using TaskService"""
    try:
        filters = {"limit": limit}
        if status:
            filters["status"] = status
        if category:
            filters["category"] = category  
        if priority:
            filters["priority"] = priority
            
        result = task_service.query_tasks(user_id, filters)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
            
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reminders/{user_id}")
async def get_upcoming_reminders(
    user_id: str,
    hours_ahead: int = 24,
    reminder_service = Depends(get_reminder_service)
):
    """Get upcoming reminders using ReminderService"""
    try:
        reminders = reminder_service.get_upcoming_reminders(user_id, hours_ahead)
        return {
            "user_id": user_id,
            "hours_ahead": hours_ahead,
            "reminders": reminders,
            "count": len(reminders)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reminders/{reminder_id}/mark-sent")
async def mark_reminder_sent(
    reminder_id: str,
    reminder_service = Depends(get_reminder_service)
):
    """Mark reminder as sent using ReminderService"""
    try:
        success = reminder_service.mark_reminder_sent(reminder_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Reminder not found or already sent")
            
        return {"success": True, "reminder_id": reminder_id, "status": "sent"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schedules/{user_id}")
async def get_user_schedules(
    user_id: str,
    days_ahead: int = 7,
    schedule_service = Depends(get_schedule_service)
):
    """Get user schedule summary using ScheduleService"""
    try:
        result = schedule_service.get_user_schedule_summary(user_id, days_ahead)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
            
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{user_id}")  
async def get_conversation_history(
    user_id: str,
    limit: int = 10,
    session_id: str = None,
    conversation_service = Depends(get_conversation_service)
):
    """Get conversation history using ConversationService"""
    try:
        conversations = conversation_service.get_conversation_history(user_id, limit, session_id)
        return {
            "user_id": user_id,
            "conversations": conversations,
            "count": len(conversations)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{user_id}/analysis")
async def get_conversation_analysis(
    user_id: str,
    days_back: int = 30,
    conversation_service = Depends(get_conversation_service)
):
    """Get conversation pattern analysis using ConversationService"""
    try:
        result = conversation_service.analyze_conversation_patterns(user_id, days_back)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
            
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/{user_id}/performance")
async def get_user_performance(
    user_id: str,
    days_back: int = 30,
    analytics_service = Depends(get_user_analytics_service)
):
    """Get user performance metrics using UserAnalyticsService"""
    try:
        result = analytics_service.get_user_performance_metrics(user_id, days_back)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
            
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/{user_id}/comprehensive")
async def get_comprehensive_analytics(
    user_id: str,
    db_manager = Depends(get_database_manager)
):
    """Get comprehensive user analytics using DatabaseManager orchestrator"""
    try:
        # This demonstrates using the orchestrator for complex operations
        user_summary = db_manager.get_user_summary(user_id)
        upcoming_reminders = db_manager.get_upcoming_reminders(user_id, 48)
        conversation_history = db_manager.get_conversation_history(user_id, 5)
        performance_metrics = db_manager.analyze_user_patterns(user_id, 30)
        
        return {
            "user_id": user_id,
            "summary": user_summary,
            "upcoming_reminders": {
                "count": len(upcoming_reminders),
                "reminders": upcoming_reminders[:3]  # Show only top 3
            },
            "recent_conversations": {
                "count": len(conversation_history),
                "conversations": conversation_history
            },
            "performance": performance_metrics
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))