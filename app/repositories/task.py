from typing import Dict, Any, List, Optional
from datetime import datetime
from app.repositories.base import BaseRepository
from app.models.task import Task, TaskUpdate

class TaskRepository(BaseRepository[Task]):
    def get_collection_name(self) -> str:
        return "tasks"
    
    def get_tasks_by_user_id(self, user_id: str) -> List[Task]:
        """Get all tasks for a specific user"""
        task_dicts = self.find({"user_id": user_id})
        tasks = []
        for task_dict in task_dicts:
            # Convert _id to id for the Task model
            if "_id" in task_dict:
                task_dict["id"] = str(task_dict["_id"])
            tasks.append(Task(**task_dict))
        return tasks
    
    def find_by_user_and_status(self, user_id: str, status: str) -> List[Dict[str, Any]]:
        return self.find({"user_id": user_id, "status": status})
    
    def find_pending_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        return self.find_by_user_and_status(user_id, "pending")
    
    def update_status(self, task_id: str, status: str) -> bool:
        return self.update(task_id, {"status": status, "updated_at": datetime.now()})
    
    def update_task(self, task_id: str, task_update: TaskUpdate) -> bool:
        """Update a task with the provided data"""
        update_data = {}
        
        # Only include fields that are not None
        if task_update.title is not None:
            update_data["title"] = task_update.title
        if task_update.description is not None:
            update_data["description"] = task_update.description
        if task_update.priority is not None:
            update_data["priority"] = task_update.priority
        if task_update.category is not None:
            update_data["category"] = task_update.category
        if task_update.status is not None:
            update_data["status"] = task_update.status
            # If status is completed, set completed_at
            if task_update.status == "completed":
                update_data["completed_at"] = datetime.now()
        if task_update.tags is not None:
            update_data["tags"] = task_update.tags
        if task_update.due_date is not None:
            update_data["due_date"] = task_update.due_date
        if task_update.due_time is not None:
            update_data["due_time"] = task_update.due_time
        if task_update.estimated_duration is not None:
            update_data["estimated_duration"] = task_update.estimated_duration
        if task_update.actual_duration is not None:
            update_data["actual_duration"] = task_update.actual_duration
        if task_update.completed_at is not None:
            update_data["completed_at"] = task_update.completed_at
        
        # Always update the updated_at timestamp
        update_data["updated_at"] = datetime.now()
        
        return self.update(task_id, update_data)
    
    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get a single task by ID"""
        task_dict = self.find_by_id(task_id)
        if task_dict:
            # Convert _id to id for the Task model
            if "_id" in task_dict:
                task_dict["id"] = str(task_dict["_id"])
            return Task(**task_dict)
        return None