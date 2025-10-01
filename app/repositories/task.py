from typing import Dict, Any, List, Optional
from datetime import datetime
from app.repositories.base import BaseRepository
from app.models.task import Task, TaskUpdate

class TaskRepository(BaseRepository[Task]):
    def get_collection_name(self) -> str:
        return "tasks"
    
    def get_tasks_by_user_id(self, user_id: str) -> List[Task]:
        """Get all tasks for a specific user"""
        task_dicts = self.find({"userId": user_id})
        tasks = []
        for task_dict in task_dicts:
            # Convert database format to Task model format
            task_dict = self._convert_db_to_task_format(task_dict)
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
            update_data["dueDate"] = task_update.due_date
        if task_update.due_time is not None:
            update_data["dueTime"] = task_update.due_time
        if task_update.estimated_duration is not None:
            update_data["estimated_duration"] = task_update.estimated_duration
        if task_update.actual_duration is not None:
            update_data["actual_duration"] = task_update.actual_duration
        if task_update.completed_at is not None:
            update_data["completed_at"] = task_update.completed_at
        
        # Always update the updated_at timestamp
        update_data["updatedAt"] = datetime.now()
        
        return self.update(task_id, update_data)
    
    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get a single task by ID"""
        task_dict = self.find_by_id(task_id)
        if task_dict:
            # Convert database format to Task model format
            task_dict = self._convert_db_to_task_format(task_dict)
            return Task(**task_dict)
        return None
    
    def _convert_db_to_task_format(self, task_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Convert database camelCase format to Task model snake_case format"""
        converted = {}
        
        # Handle _id -> id conversion
        if "_id" in task_dict:
            converted["id"] = str(task_dict["_id"])
        
        # Convert camelCase database fields to snake_case model fields
        field_mapping = {
            "userId": "user_id",
            "dueDate": "due_date", 
            "dueTime": "due_time",
            "estimatedDuration": "estimated_duration",
            "actualDuration": "actual_duration",
            "creationContext": "creation_context",
            "lastModifiedBy": "last_modified_by",
            "scheduledSlot": "scheduled_slot",
            "createdAt": "created_at",
            "updatedAt": "updated_at",
            "completedAt": "completed_at"
        }
        
        # Copy direct fields (no conversion needed)
        direct_fields = ["title", "description", "priority", "category", "status", "tags", "subtasks"]
        for field in direct_fields:
            if field in task_dict:
                converted[field] = task_dict[field]
        
        # Handle reference_links field
        if "referenceLinks" in task_dict:
            converted["reference_links"] = task_dict["referenceLinks"]
        
        # Convert mapped fields
        for db_field, model_field in field_mapping.items():
            if db_field in task_dict:
                converted[model_field] = task_dict[db_field]
        
        # Set defaults for missing required fields
        if "user_id" not in converted:
            converted["user_id"] = ""
        if "title" not in converted:
            converted["title"] = "Untitled Task"
        if "tags" not in converted:
            converted["tags"] = []
        if "subtasks" not in converted:
            converted["subtasks"] = []
        if "reference_links" not in converted:
            converted["reference_links"] = []
            
        return converted