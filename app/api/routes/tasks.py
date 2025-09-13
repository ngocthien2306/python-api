from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from app.api.routes.auth import get_current_user
from app.repositories.user import UserRepository
from app.repositories.task import TaskRepository
from app.api.routes.auth import get_user_repository
from app.core.database import get_database
from app.models.task import Task, TaskResponse

router = APIRouter()

def get_task_repository():
    """Dependency to get task repository."""
    db = get_database()
    return TaskRepository(db)

@router.get("/tasks/{user_id}", response_model=List[TaskResponse])
async def get_user_tasks(
    user_id: str,
    current_user=Depends(get_current_user),
    task_repo: TaskRepository = Depends(get_task_repository),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Get tasks for a specific user by user_id (username)"""
    try:
        # Get user by username
        target_user = user_repo.get_user_by_username(user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # For now, allow users to see only their own tasks
        # In the future, you might want to add permission checks
        if str(current_user.id) != str(target_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        
        # Get tasks for the user
        tasks = task_repo.get_tasks_by_user_id(str(target_user.id))
        
        return [
            TaskResponse(
                id=str(task.id),
                title=task.title,
                description=task.description,
                status=task.status,
                priority=task.priority,
                due_date=task.due_date,
                created_at=task.created_at,
                updated_at=task.updated_at,
                user_id=str(task.user_id),
                tags=task.tags,
                category=task.category,
                estimated_duration=task.estimated_duration,
                actual_duration=task.actual_duration,
                completed_at=task.completed_at
            ) for task in tasks
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tasks: {str(e)}"
        )

@router.get("/my-tasks", response_model=List[TaskResponse])
async def get_current_user_tasks(
    current_user=Depends(get_current_user),
    task_repo: TaskRepository = Depends(get_task_repository)
):
    """Get tasks for the current authenticated user"""
    try:
        tasks = task_repo.get_tasks_by_user_id(str(current_user.id))
        
        return [
            TaskResponse(
                id=str(task.id),
                title=task.title,
                description=task.description,
                status=task.status,
                priority=task.priority,
                due_date=task.due_date,
                created_at=task.created_at,
                updated_at=task.updated_at,
                user_id=str(task.user_id),
                tags=task.tags,
                category=task.category,
                estimated_duration=task.estimated_duration,
                actual_duration=task.actual_duration,
                completed_at=task.completed_at
            ) for task in tasks
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tasks: {str(e)}"
        )