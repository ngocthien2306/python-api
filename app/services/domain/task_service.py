from typing import Dict, Any, List
from datetime import datetime
from app.repositories.task import TaskRepository
from app.models.task import Task, Subtask


class TaskService:
    """Service responsible for all task-related operations"""
    
    def __init__(self, task_repo: TaskRepository):
        self.task_repo = task_repo
    
    def create_task(self, task_data: Dict[str, Any], user_input: str, user_id: str) -> Dict[str, Any]:
        """Create a new task"""
        task = Task(
            user_id=user_id,
            title=task_data.get("title", "Untitled Task"),
            description=task_data.get("description", ""),
            priority=task_data.get("priority", "medium"),
            category=task_data.get("category", "other"),
            status=task_data.get("status", "pending"),
            tags=task_data.get("tags", []),
            creation_context=user_input
        )
        
        # Handle due date/time
        if task_data.get("dueDate"):
            try:
                task.due_date = datetime.strptime(task_data["dueDate"], "%Y-%m-%d")
            except ValueError:
                pass
        
        if task_data.get("dueTime"):
            task.due_time = task_data["dueTime"]
        
        task.estimated_duration = self._estimate_duration(task_data)
        
        # Add subtasks
        for subtask_title in task_data.get("subtasks", []):
            task.subtasks.append(Subtask(title=subtask_title))
        
        # Convert to database format
        task_doc = self._convert_task_to_db_format(task)
        
        task_id = self.task_repo.create(task_doc)
        return {
            "task_id": task_id,
            "title": task.title,
            "priority": task.priority,
            "category": task.category
        }
    
    def create_scheduled_task(self, task_data: Dict[str, Any], user_id: str, 
                            scheduled_date: datetime, context: str = "scheduled") -> str:
        """Create a task for scheduling purposes"""
        task = Task(
            user_id=user_id,
            title=task_data.get("title", "Untitled Task"),
            description=f"Scheduled task: {task_data.get('title')}",
            priority=task_data.get("priority", "medium"),
            category=task_data.get("category", "other"),
            tags=["scheduled", "auto-generated"],
            creation_context=context
        )
        
        if task_data.get("startTime"):
            task.due_date = scheduled_date
            task.due_time = task_data.get("startTime")
        
        task.scheduled_slot = {
            "date": scheduled_date,
            "startTime": task_data.get("startTime"),
            "endTime": task_data.get("endTime"),
            "flexibility": task_data.get("flexibility", "flexible")
        }
        task.estimated_duration = int(task_data.get("duration", 60))
        
        task_doc = self._convert_task_to_db_format(task)
        return self.task_repo.create(task_doc)
    
    def update_task(self, task_id: str, updates: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Update an existing task"""
        if not task_id:
            return {"success": False, "error": "Task ID required for update"}
        
        try:
            # Prepare update data
            update_data = {"updatedAt": datetime.now(), "lastModifiedBy": "ai"}
            
            for key, value in updates.items():
                if key == "dueDate" and value:
                    try:
                        update_data["dueDate"] = datetime.strptime(value, "%Y-%m-%d")
                    except ValueError:
                        continue
                elif key in ["title", "description", "priority", "category", "status", "dueTime"]:
                    update_data[key] = value
                elif key == "tags" and isinstance(value, list):
                    update_data["tags"] = value
            
            result = self.task_repo.update(task_id, update_data)
            
            return {
                "success": True,
                "task_id": task_id,
                "updated_fields": list(update_data.keys())
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def delete_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """Delete a task"""
        if not task_id:
            return {"success": False, "error": "Task ID required for deletion"}
        
        try:
            result = self.task_repo.delete(task_id)
            
            return {
                "success": True,
                "task_id": task_id,
                "deleted": result
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def query_tasks(self, user_id: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Query tasks based on filters"""
        try:
            query = {"userId": user_id}
            
            # Add filters
            if filters.get("status"):
                query["status"] = filters["status"]
            if filters.get("category"):
                query["category"] = filters["category"]
            if filters.get("priority"):
                query["priority"] = filters["priority"]
            if filters.get("tags"):
                query["tags"] = {"$in": filters["tags"]}
            
            # Date range filter
            if filters.get("dueDateRange"):
                date_range = filters["dueDateRange"]
                if date_range.get("start"):
                    query["dueDate"] = {"$gte": datetime.strptime(date_range["start"], "%Y-%m-%d")}
                if date_range.get("end"):
                    if "dueDate" not in query:
                        query["dueDate"] = {}
                    query["dueDate"]["$lte"] = datetime.strptime(date_range["end"], "%Y-%m-%d")
            
            tasks = self.task_repo.find_by_query(query, limit=filters.get("limit", 20))
            
            return {
                "success": True,
                "tasks_found": len(tasks),
                "tasks": [
                    {
                        "id": str(task.get("_id", task.get("id"))), 
                        "title": task["title"], 
                        "status": task["status"],
                        "priority": task.get("priority"),
                        "category": task.get("category"),
                        "dueDate": task.get("dueDate"),
                        "dueTime": task.get("dueTime")
                    } 
                    for task in tasks
                ]
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_user_tasks_summary(self, user_id: str) -> Dict[str, Any]:
        """Get task summary for user"""
        try:
            # Count tasks by status
            task_counts = {}
            for status in ["pending", "in_progress", "completed"]:
                query = {"userId": user_id, "status": status}
                count = len(self.task_repo.find_by_query(query, limit=1000))
                task_counts[status] = count
            
            # Recent activity
            recent_tasks = self.task_repo.find_by_query(
                {"userId": user_id}, 
                limit=5,
                sort=[("createdAt", -1)]
            )
            
            return {
                "success": True,
                "task_counts": task_counts,
                "recent_tasks": [{"title": t["title"], "status": t["status"]} for t in recent_tasks]
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _convert_task_to_db_format(self, task: Task) -> Dict[str, Any]:
        """Convert Task model to database format"""
        task_doc = task.dict()
        task_doc["userId"] = task_doc.pop("user_id")
        task_doc["dueDate"] = task_doc.pop("due_date")
        task_doc["dueTime"] = task_doc.pop("due_time")
        task_doc["estimatedDuration"] = task_doc.pop("estimated_duration")
        task_doc["creationContext"] = task_doc.pop("creation_context")
        task_doc["lastModifiedBy"] = task_doc.pop("last_modified_by")
        task_doc["scheduledSlot"] = task_doc.pop("scheduled_slot")
        task_doc["createdAt"] = task_doc.pop("created_at")
        task_doc["updatedAt"] = task_doc.pop("updated_at")
        
        task_doc["subtasks"] = [
            {"title": st.title, "completed": st.completed, "createdAt": st.created_at}
            for st in task.subtasks
        ]
        
        return task_doc
    
    def _estimate_duration(self, task_data: Dict[str, Any]) -> int:
        """Estimate task duration based on category and content"""
        category = task_data.get("category", "other")
        
        duration_map = {
            "meeting": 60, "work": 120, "personal": 30, "health": 60,
            "learning": 90, "shopping": 45, "communication": 15, "other": 60
        }
        
        base_duration = duration_map.get(category, 60)
        
        priority = task_data.get("priority", "medium")
        if priority == "urgent":
            base_duration = min(base_duration * 1.5, 180)
        elif priority == "low":
            base_duration = max(base_duration * 0.7, 15)
        
        return int(base_duration)