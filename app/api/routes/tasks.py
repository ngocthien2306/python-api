import traceback
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from app.api.routes.auth import get_current_user
from app.repositories.user import UserRepository
from app.repositories.task import TaskRepository
from app.api.routes.auth import get_user_repository
from app.core.database import get_database
from app.models.task import Task, TaskResponse, TaskUpdate, TaskUpdateRequest

router = APIRouter()

def get_task_repository():
    """Dependency to get task repository."""
    db = get_database()
    return TaskRepository(db)

@router.get("/tasks-user/{user_id}", response_model=List[TaskResponse])
async def get_user_tasks(
    user_id: str,
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
        
        # Get tasks for the user
        tasks = task_repo.get_tasks_by_user_id(str(user_id))
        
        return [
            TaskResponse(
                id=str(task.id),
                title=task.title,
                description=task.description,
                status=task.status,
                priority=task.priority,
                due_date=task.due_date,
                due_time=task.due_time,
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
        tasks = task_repo.get_tasks_by_user_id(str(current_user.username))
        
        return [
            TaskResponse(
                id=str(task.id),
                title=task.title,
                description=task.description,
                status=task.status,
                priority=task.priority,
                due_date=task.due_date,
                due_time=task.due_time,
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
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tasks: {str(e)}"
        )

@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_update_request: TaskUpdateRequest,
    # current_user=Depends(get_current_user),
    task_repo: TaskRepository = Depends(get_task_repository)
):
    """Update a specific task"""
    try:
        # Get the task first to check ownership
        existing_task = task_repo.get_task_by_id(task_id)
        if not existing_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Check if the current user owns this task
        # if str(existing_task.user_id) != str(current_user.id):
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Permission denied: You can only update your own tasks"
        #     )
        
        # Convert request to TaskUpdate
        task_update = task_update_request.to_task_update()
        
        # Update the task
        success = task_repo.update_task(task_id, task_update)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update task"
            )
        
        # Get the updated task
        updated_task = task_repo.get_task_by_id(task_id)
        if not updated_task:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve updated task"
            )
        
        return TaskResponse(
            id=str(updated_task.id),
            title=updated_task.title,
            description=updated_task.description,
            status=updated_task.status,
            priority=updated_task.priority,
            due_date=updated_task.due_date,
            due_time=updated_task.due_time,
            created_at=updated_task.created_at,
            updated_at=updated_task.updated_at,
            user_id=str(updated_task.user_id),
            tags=updated_task.tags,
            category=updated_task.category,
            estimated_duration=updated_task.estimated_duration,
            actual_duration=updated_task.actual_duration,
            completed_at=updated_task.completed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task: {str(e)}"
        )

@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    # current_user=Depends(get_current_user),
    task_repo: TaskRepository = Depends(get_task_repository)
):
    """Delete a specific task"""
    try:
        # Get the task first to check ownership
        existing_task = task_repo.get_task_by_id(task_id)
        if not existing_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Check if the current user owns this task
        # if str(existing_task.user_id) != str(current_user.id):
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Permission denied: You can only delete your own tasks"
        #     )
        
        # Delete the task
        success = task_repo.delete(task_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete task"
            )
        
        return {"message": "Task deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete task: {str(e)}"
        )

@router.put("/tasks/{task_id}/complete", response_model=TaskResponse)
async def mark_task_complete(
    task_id: str,
    task_repo: TaskRepository = Depends(get_task_repository)
):
    """Mark a specific task as completed - simple endpoint for task operations"""
    try:
        # Get the task first
        existing_task = task_repo.get_task_by_id(task_id)
        if not existing_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Create TaskUpdate for completion
        from app.models.task import TaskUpdate
        from datetime import datetime
        
        task_update = TaskUpdate(
            status="completed",
            completed_at=datetime.now()
        )
        
        # Update the task
        success = task_repo.update_task(task_id, task_update)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to mark task as completed"
            )
        
        # Get the updated task
        updated_task = task_repo.get_task_by_id(task_id)
        if not updated_task:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve completed task"
            )
        
        return TaskResponse(
            id=str(updated_task.id),
            title=updated_task.title,
            description=updated_task.description,
            status=updated_task.status,
            priority=updated_task.priority,
            due_date=updated_task.due_date,
            due_time=updated_task.due_time,
            created_at=updated_task.created_at,
            updated_at=updated_task.updated_at,
            user_id=str(updated_task.user_id),
            tags=updated_task.tags,
            category=updated_task.category,
            estimated_duration=updated_task.estimated_duration,
            actual_duration=updated_task.actual_duration,
            completed_at=updated_task.completed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark task as completed: {str(e)}"
        )