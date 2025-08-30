from fastapi import APIRouter, Depends, HTTPException
from app.services.ai_processor import AIProcessorService
from app.core.dependencies import get_database_manager
from app.schemas.ai_response import ProcessConversationRequest
from app.schemas.database import APIResponse

router = APIRouter()

@router.post("/process-conversation", response_model=APIResponse)
async def process_conversation(
    request: ProcessConversationRequest,
    db_manager = Depends(get_database_manager)
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
    db_manager = Depends(get_database_manager)
):
    try:
        task_counts = {}
        for status in ["pending", "in_progress", "completed"]:
            count = db_manager.task_repo.count({"userId": user_id, "status": status})
            task_counts[status] = count
        
        reminder_count = db_manager.reminder_repo.count({"userId": user_id, "status": "pending"})
        conversation_count = db_manager.conversation_repo.count({"userId": user_id})
        
        recent_tasks = db_manager.task_repo.find({"userId": user_id}, limit=5)
        
        return {
            "user_id": user_id,
            "task_counts": task_counts,
            "pending_reminders": reminder_count,
            "total_conversations": conversation_count,
            "recent_tasks": [{"title": t["title"], "status": t["status"]} for t in recent_tasks]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))