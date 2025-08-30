from typing import Dict, Any, List
from app.repositories.base import BaseRepository
from app.models.task import Task

class TaskRepository(BaseRepository[Task]):
    def get_collection_name(self) -> str:
        return "tasks"
    
    def find_by_user_and_status(self, user_id: str, status: str) -> List[Dict[str, Any]]:
        return self.find({"userId": user_id, "status": status})
    
    def find_pending_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        return self.find_by_user_and_status(user_id, "pending")
    
    def update_status(self, task_id: str, status: str) -> bool:
        return self.update(task_id, {"status": status})