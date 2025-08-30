import traceback
from typing import Dict, Any, List
from datetime import datetime, timedelta
from app.repositories.conversation import ConversationRepository
from app.repositories.task import TaskRepository
from app.repositories.reminder import ReminderRepository
from app.repositories.schedule import ScheduleRepository
from app.models.conversation import Conversation, Message
from app.models.task import Task, Subtask
from app.models.reminder import Reminder
from app.models.schedule import Schedule, TimeSlot
from app.schemas.ai_response import AIResponse
from bson import ObjectId

class DatabaseManagerService:
    def __init__(self, conversation_repo: ConversationRepository, 
                 task_repo: TaskRepository, reminder_repo: ReminderRepository,
                 schedule_repo: ScheduleRepository):
        self.conversation_repo = conversation_repo
        self.task_repo = task_repo
        self.reminder_repo = reminder_repo
        self.schedule_repo = schedule_repo
    
    def process_ai_response(self, parsed_response: AIResponse, user_input: str, 
                          user_id: str) -> Dict[str, Any]:
        session_id = f"{user_id}_{int(datetime.now().timestamp())}"
        results = {"session_id": session_id, "operations": []}
        
        try:
            mode = parsed_response.mode
            
            conv_result = self._save_conversation(parsed_response, user_input, user_id, session_id)
            results["operations"].append({"type": "conversation", "result": conv_result})
            
            if mode == "conversation":
                results["mode_processed"] = "conversation_only"
            elif mode == "simple_task":
                task_result = self._handle_simple_task(parsed_response, user_input, user_id)
                results["operations"].append({"type": "simple_task", "result": task_result})
            elif mode == "scheduling":
                schedule_result = self._handle_scheduling(parsed_response, user_input, user_id)
                results["operations"].append({"type": "scheduling", "result": schedule_result})
            
            return {"success": True, "results": results}
            
        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": str(e), "partial_results": results}
    
    def _save_conversation(self, parsed_response: AIResponse, user_input: str, 
                          user_id: str, session_id: str) -> Dict[str, Any]:
        conversation = Conversation(user_id, session_id)
        conversation.active_topics = self._extract_topics(user_input)
        conversation.user_mood = self._detect_mood(user_input)
        
        conversation.messages.append(Message(
            timestamp=datetime.now(),
            role="user",
            content=user_input,
            intent=parsed_response.intent,
            confidence=parsed_response.confidence,
            mode=parsed_response.mode
        ))
        
        for msg in parsed_response.messages:
            conversation.messages.append(Message(
                timestamp=datetime.now(),
                role="assistant",
                content=msg.text,
                facialExpression=msg.facialExpression,
                animation=msg.animation
            ))
        
        conv_doc = conversation.to_dict()
        conv_doc["userId"] = conv_doc.pop("user_id")
        conv_doc["sessionId"] = conv_doc.pop("session_id")
        conv_doc["activeTopics"] = conv_doc.pop("active_topics")
        conv_doc["userMood"] = conv_doc.pop("user_mood")
        conv_doc["createdAt"] = conv_doc.pop("created_at")
        conv_doc["updatedAt"] = conv_doc.pop("updated_at")
        
        conv_doc["messages"] = [
            {
                "timestamp": msg.timestamp,
                "role": msg.role,
                "content": msg.content,
                **{k: v for k, v in msg.__dict__.items() if k not in ["timestamp", "role", "content"]}
            }
            for msg in conversation.messages
        ]
        
        conv_id = self.conversation_repo.create(conv_doc)
        return {"conversation_id": conv_id, "messages_count": len(conversation.messages)}
    
    def _handle_simple_task(self, parsed_response: AIResponse, user_input: str, user_id: str) -> Dict[str, Any]:
        task_action = parsed_response.taskAction
        action = task_action.action
        results = {"action": action}
        
        if action == "create" and task_action.task:
            task_result = self._create_task(task_action.task.dict(), user_input, user_id)
            results.update(task_result)
            
            if task_result.get("task_id"):
                reminder_result = self._create_reminders(
                    task_result["task_id"], 
                    task_action.task.dict(), 
                    user_id
                )
                results["reminders"] = reminder_result
        
        return results
    
    def _handle_scheduling(self, parsed_response: AIResponse, user_input: str, user_id: str) -> Dict[str, Any]:
        scheduling_action = parsed_response.schedulingAction
        schedule_type = scheduling_action.type
        results = {"type": schedule_type}
        
        if schedule_type == "daily_planning":
            results.update(self._create_daily_schedule(scheduling_action.dict(), user_id))
        
        return results
    
    def _create_task(self, task_data: Dict[str, Any], user_input: str, user_id: str) -> Dict[str, Any]:
        task = Task(user_id, task_data.get("title", "Untitled Task"))
        task.description = task_data.get("description", "")
        task.priority = task_data.get("priority", "medium")
        task.category = task_data.get("category", "other")
        task.status = task_data.get("status", "pending")
        task.tags = task_data.get("tags", [])
        task.creation_context = user_input
        
        if task_data.get("dueDate"):
            try:
                task.due_date = datetime.strptime(task_data["dueDate"], "%Y-%m-%d")
            except ValueError:
                pass
        
        if task_data.get("dueTime"):
            task.due_time = task_data["dueTime"]
        
        task.estimated_duration = self._estimate_duration(task_data)
        
        for subtask_title in task_data.get("subtasks", []):
            task.subtasks.append(Subtask(subtask_title))
        
        task_doc = task.to_dict()
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
        
        task_id = self.task_repo.create(task_doc)
        return {
            "task_id": task_id,
            "title": task.title,
            "priority": task.priority,
            "category": task.category
        }
    
    def _create_reminders(self, task_id: str, task_data: Dict[str, Any], user_id: str) -> List[Dict[str, Any]]:
        reminders = task_data.get("reminders", [])
        if not reminders:
            reminders = [{"type": "time", "beforeDue": "15m"}]
        
        task_doc = self.task_repo.find_by_id(task_id)
        if not task_doc or not task_doc.get("dueDate"):
            return []
        
        created_reminders = []
        
        for reminder_data in reminders:
            try:
                due_datetime = task_doc["dueDate"]
                if task_doc.get("dueTime"):
                    due_time = datetime.strptime(task_doc["dueTime"], "%H:%M").time()
                    due_datetime = datetime.combine(due_datetime.date(), due_time)
                
                before_minutes = self._parse_before_due(reminder_data.get("beforeDue", "15m"))
                trigger_time = due_datetime - timedelta(minutes=before_minutes)
                
                if trigger_time > datetime.now():
                    reminder = Reminder(user_id, ObjectId(task_id))
                    reminder.type = reminder_data.get("type", "time")
                    reminder.trigger_time = trigger_time
                    reminder.before_due = reminder_data.get("beforeDue", "15m")
                    reminder.message = reminder_data.get("message") or f"Reminder: {task_doc['title']} due in {reminder_data.get('beforeDue', '15m')}"
                    
                    reminder_doc = reminder.to_dict()
                    reminder_doc["userId"] = reminder_doc.pop("user_id")
                    reminder_doc["taskId"] = reminder_doc.pop("task_id")
                    reminder_doc["triggerTime"] = reminder_doc.pop("trigger_time")
                    reminder_doc["beforeDue"] = reminder_doc.pop("before_due")
                    reminder_doc["scheduleType"] = reminder_doc.pop("schedule_type")
                    reminder_doc["slotIndex"] = reminder_doc.pop("slot_index")
                    reminder_doc["ruleIndex"] = reminder_doc.pop("rule_index")
                    reminder_doc["createdAt"] = reminder_doc.pop("created_at")
                    reminder_doc["updatedAt"] = reminder_doc.pop("updated_at")
                    
                    reminder_id = self.reminder_repo.create(reminder_doc)
                    created_reminders.append({
                        "reminder_id": reminder_id,
                        "trigger_time": trigger_time.isoformat(),
                        "message": reminder.message,
                        "before_due": reminder.before_due
                    })
            
            except Exception as e:
                continue
        
        return created_reminders
    
    def _create_daily_schedule(self, scheduling_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        today = datetime.now().date()
        tasks = scheduling_data.get("tasks", [])
        
        schedule = Schedule(user_id, datetime.combine(today, datetime.min.time()), "daily")
        schedule.version = 1
        
        total_minutes = 0
        created_tasks = []
        all_reminders = []
        
        for task_data in tasks:
            time_slot_dict = {
                "startTime": task_data.get("startTime"),
                "endTime": task_data.get("endTime"),
                "taskTitle": task_data.get("title"),
                "category": task_data.get("category", "other"),
                "priority": task_data.get("priority", "medium"),
                "flexibility": task_data.get("flexibility", "flexible"),
                "duration": task_data.get("duration", 60),
                "autoScheduled": True,
                "confidence": 0.8,
                "taskId": None
            }
            
            task = Task(user_id, task_data.get("title"))
            task.description = f"Scheduled task: {task_data.get('title')}"
            task.priority = task_data.get("priority", "medium")
            task.category = task_data.get("category", "other")
            task.tags = ["scheduled", "auto-generated"]
            task.creation_context = "auto-scheduled"
            
            if task_data.get("startTime"):
                task.due_date = datetime.combine(today, datetime.min.time())
                task.due_time = task_data.get("startTime")
            
            task.scheduled_slot = {
                "date": datetime.combine(today, datetime.min.time()),
                "startTime": task_data.get("startTime"),
                "endTime": task_data.get("endTime"),
                "flexibility": task_data.get("flexibility", "flexible")
            }
            task.estimated_duration = int(task_data.get("duration", 60))
            
            task_doc = task.to_dict()
            task_doc["userId"] = task_doc.pop("user_id")
            task_doc["dueDate"] = task_doc.pop("due_date")
            task_doc["dueTime"] = task_doc.pop("due_time")
            task_doc["estimatedDuration"] = task_doc.pop("estimated_duration")
            task_doc["creationContext"] = task_doc.pop("creation_context")
            task_doc["lastModifiedBy"] = task_doc.pop("last_modified_by")
            task_doc["scheduledSlot"] = task_doc.pop("scheduled_slot")
            task_doc["createdAt"] = task_doc.pop("created_at")
            task_doc["updatedAt"] = task_doc.pop("updated_at")
            task_doc["subtasks"] = []
            
            task_id = self.task_repo.create(task_doc)
            time_slot_dict["taskId"] = task_id
            created_tasks.append(task_id)
            
            schedule.time_slots.append(time_slot_dict)
            total_minutes += int(task_data.get("duration", 60))
        
        schedule.total_workload = total_minutes
        schedule.conflicts = 0
        
        schedule_doc = schedule.to_dict()
        schedule_doc["userId"] = schedule_doc.pop("user_id")
        schedule_doc["timeSlots"] = schedule.time_slots
        schedule_doc["totalWorkload"] = schedule_doc.pop("total_workload")
        schedule_doc["createdAt"] = schedule_doc.pop("created_at")
        schedule_doc["updatedAt"] = schedule_doc.pop("updated_at")
        
        schedule_id = self.schedule_repo.create(schedule_doc)
        
        return {
            "schedule_id": schedule_id,
            "date": today.isoformat(),
            "tasks_count": len(tasks),
            "total_workload": total_minutes,
            "conflicts_detected": 0,
            "created_tasks": created_tasks,
            "created_reminders": all_reminders
        }
    
    def _extract_topics(self, text: str) -> List[str]:
        keywords = ["meeting", "deadline", "project", "client", "report", "call"]
        return [kw for kw in keywords if kw.lower() in text.lower()]
    
    def _detect_mood(self, text: str) -> str:
        stress_words = ["stress", "panic", "overwhelmed", "chaos", "deadline"]
        happy_words = ["great", "excited", "good", "awesome", "perfect"]
        
        text_lower = text.lower()
        
        if any(word in text_lower for word in stress_words):
            return "stressed"
        elif any(word in text_lower for word in happy_words):
            return "positive"
        else:
            return "neutral"
    
    def _parse_before_due(self, before_str: str) -> int:
        mapping = {
            "15m": 15, "30m": 30, "1h": 60, "2h": 120, "1d": 1440,
            "5m": 5, "10m": 10, "45m": 45, "3h": 180, "4h": 240
        }
        return mapping.get(before_str, 15)
    
    def _estimate_duration(self, task_data: Dict[str, Any]) -> int:
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