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
        
        elif action == "update":
            results.update(self._update_task(task_action, user_id))
            
        elif action == "delete":
            results.update(self._delete_task(task_action, user_id))
            
        elif action == "query":
            results.update(self._query_tasks(user_id, task_action.dict().get("filters", {})))
        
        return results
    
    def _handle_scheduling(self, parsed_response: AIResponse, user_input: str, user_id: str) -> Dict[str, Any]:
        scheduling_action = parsed_response.schedulingAction
        schedule_type = scheduling_action.type
        results = {"type": schedule_type}
        
        if schedule_type == "daily_planning":
            results.update(self._create_daily_schedule(scheduling_action.dict(), user_id))
        elif schedule_type == "weekly_planning":
            results.update(self._create_weekly_schedule(scheduling_action.dict(), user_id))
        elif schedule_type == "rescheduling":
            results.update(self._handle_rescheduling(scheduling_action.dict(), user_id))
        
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
        
        # Detect conflicts
        conflicts = self._detect_time_conflicts(schedule.time_slots)
        schedule.conflicts = len(conflicts)
        
        # Create reminders for scheduled tasks
        for i, time_slot in enumerate(schedule.time_slots):
            if time_slot.get("taskId"):
                task_data = tasks[i] if i < len(tasks) else {}
                reminders = self._create_schedule_reminders(
                    time_slot["taskId"], task_data, user_id, today
                )
                all_reminders.extend(reminders)
        
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
            "conflicts_detected": len(conflicts),
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
    
    def _create_weekly_schedule(self, scheduling_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Create weekly schedule with tasks and reminders"""
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())  # Monday
        
        schedule = Schedule(user_id, start_of_week, "weekly")
        schedule.end_date = start_of_week + timedelta(days=6)
        schedule.weekly_goals = []
        
        all_reminders = []
        created_tasks = []
        
        # Create daily schedules for the week
        for day_offset in range(7):  # Monday to Sunday
            current_date = start_of_week + timedelta(days=day_offset)
            
            daily_tasks = self._generate_weekly_tasks(day_offset, scheduling_data)
            
            daily_schedule = {
                "date": current_date,
                "dayName": current_date.strftime("%A"),
                "tasks": [],
                "workload": 0
            }
            
            for task_data in daily_tasks:
                # Create task
                task = Task(user_id, task_data["title"])
                task.description = f"Weekly planned: {task_data['title']}"
                task.priority = task_data.get("priority", "medium")
                task.category = task_data.get("category", "work")
                task.tags = ["weekly-plan", "auto-generated"]
                task.due_date = current_date
                task.due_time = task_data.get("startTime")
                task.scheduled_slot = {
                    "date": current_date,
                    "startTime": task_data.get("startTime"),
                    "endTime": task_data.get("endTime"),
                    "flexibility": "flexible"
                }
                task.estimated_duration = task_data.get("duration", 60)
                task.creation_context = "weekly-planning"
                
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
                created_tasks.append(task_id)
                
                # Create reminders for weekly tasks
                reminders = self._create_schedule_reminders(
                    task_id, task_data, user_id, current_date.date()
                )
                all_reminders.extend(reminders)
                
                daily_schedule["tasks"].append({
                    "taskId": task_id,
                    "title": task_data["title"],
                    "startTime": task_data.get("startTime"),
                    "duration": task_data.get("duration", 60)
                })
                daily_schedule["workload"] += task_data.get("duration", 60)
            
            schedule.daily_schedules.append(daily_schedule)
            schedule.total_workload += daily_schedule["workload"]
        
        # Save weekly schedule
        schedule_doc = schedule.to_dict()
        schedule_doc["userId"] = schedule_doc.pop("user_id")
        schedule_doc["endDate"] = schedule.end_date
        schedule_doc["weeklyGoals"] = schedule.weekly_goals
        schedule_doc["dailySchedules"] = schedule.daily_schedules
        schedule_doc["totalWorkload"] = schedule_doc.pop("total_workload")
        schedule_doc["createdAt"] = schedule_doc.pop("created_at")
        schedule_doc["updatedAt"] = schedule_doc.pop("updated_at")
        
        schedule_id = self.schedule_repo.create(schedule_doc)
        
        return {
            "schedule_id": schedule_id,
            "type": "weekly_planning",
            "week_start": start_of_week.isoformat(),
            "total_workload": schedule.total_workload,
            "created_tasks": created_tasks,
            "created_reminders": all_reminders,
            "daily_schedules": len(schedule.daily_schedules)
        }
    
    def _generate_weekly_tasks(self, day_offset: int, scheduling_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate sample tasks for weekly planning"""
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        current_day = day_names[day_offset]
        
        # Sample task generation based on day
        if day_offset < 5:  # Weekdays
            tasks = [
                {
                    "title": f"Morning standup - {current_day}",
                    "startTime": "09:00",
                    "endTime": "09:30",
                    "duration": 30,
                    "category": "meeting",
                    "priority": "medium"
                },
                {
                    "title": f"Focus work block - {current_day}",
                    "startTime": "10:00", 
                    "endTime": "12:00",
                    "duration": 120,
                    "category": "deep_work",
                    "priority": "high"
                }
            ]
        else:  # Weekends
            tasks = [
                {
                    "title": f"Personal time - {current_day}",
                    "startTime": "10:00",
                    "endTime": "11:00", 
                    "duration": 60,
                    "category": "personal",
                    "priority": "low"
                }
            ]
        
        return tasks
    
    def _update_task(self, task_action, user_id: str) -> Dict[str, Any]:
        """Update an existing task"""
        task_id = task_action.dict().get("taskId")
        updates = task_action.dict().get("updates", {})
        
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
    
    def _delete_task(self, task_action, user_id: str) -> Dict[str, Any]:
        """Delete a task and associated reminders"""
        task_id = task_action.dict().get("taskId")
        
        if not task_id:
            return {"success": False, "error": "Task ID required for deletion"}
        
        try:
            # Delete associated reminders first
            self.reminder_repo.delete_by_task_id(task_id)
            
            # Delete the task
            result = self.task_repo.delete(task_id)
            
            return {
                "success": True,
                "task_id": task_id,
                "deleted": result
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _query_tasks(self, user_id: str, filters: Dict[str, Any]) -> Dict[str, Any]:
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
                        "id": task.get("_id", task.get("id")), 
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
    
    def _create_schedule_reminders(self, task_id: str, task_data: Dict[str, Any], user_id: str, date) -> List[Dict[str, Any]]:
        """Create reminders for scheduled tasks"""
        start_time = task_data.get("startTime")
        category = task_data.get("category", "other") 
        priority = task_data.get("priority", "medium")
        
        if not start_time:
            return []
        
        created_reminders = []
        
        try:
            # Parse start time
            start_datetime = datetime.combine(
                date,
                datetime.strptime(start_time, "%H:%M").time()
            )
            
            # Define reminder rules based on task type and priority
            reminder_rules = self._get_reminder_rules(category, priority)
            
            for rule in reminder_rules:
                trigger_time = start_datetime - timedelta(minutes=rule["minutes"])
                
                # Only create reminder if it's in the future
                if trigger_time > datetime.now():
                    reminder = Reminder(user_id, ObjectId(task_id))
                    reminder.type = "schedule"
                    reminder.trigger_time = trigger_time
                    reminder.before_due = f"{rule['minutes']}m"
                    reminder.message = rule["message"].format(
                        task=task_data.get("title", "Task"),
                        time=start_time
                    )
                    reminder.channel = "notification"
                    reminder.priority = rule["priority"]
                    reminder.schedule_type = "auto-generated"
                    
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
                        "before_start": rule["minutes"]
                    })
        
        except Exception as e:
            print(f"Failed to create schedule reminders: {e}")
        
        return created_reminders
    
    def _get_reminder_rules(self, category: str, priority: str) -> List[Dict[str, Any]]:
        """Get reminder rules based on task category and priority"""
        base_rules = []
        
        # Category-specific rules
        if category == "meeting":
            base_rules = [
                {"minutes": 15, "message": "Chuẩn bị meeting '{task}' trong 15 phút (lúc {time})", "priority": "high"},
                {"minutes": 5, "message": "Meeting '{task}' bắt đầu trong 5 phút!", "priority": "urgent"}
            ]
        
        elif category == "deep_work" or category == "work":
            base_rules = [
                {"minutes": 30, "message": "Chuẩn bị focus work '{task}' trong 30 phút", "priority": "medium"},
                {"minutes": 10, "message": "Bắt đầu '{task}' trong 10 phút (lúc {time})", "priority": "high"}
            ]
        
        elif category == "communication":
            base_rules = [
                {"minutes": 10, "message": "Chuẩn bị gọi điện '{task}' trong 10 phút", "priority": "medium"},
                {"minutes": 2, "message": "Gọi điện '{task}' ngay bây giờ (lúc {time})!", "priority": "high"}
            ]
        
        elif category == "admin":
            base_rules = [
                {"minutes": 15, "message": "Task admin '{task}' bắt đầu trong 15 phút", "priority": "low"}
            ]
        
        else:  # default for other categories
            base_rules = [
                {"minutes": 15, "message": "Task '{task}' bắt đầu trong 15 phút (lúc {time})", "priority": "medium"}
            ]
        
        # Priority adjustments
        if priority == "urgent":
            # Add extra urgent reminder
            base_rules.append({
                "minutes": 1, 
                "message": "🚨 URGENT: '{task}' bắt đầu NGAY BÂY GIỜ!", 
                "priority": "urgent"
            })
        
        elif priority == "high":
            # Add early warning
            base_rules.insert(0, {
                "minutes": 60,
                "message": "High priority task '{task}' sẽ bắt đầu trong 1 tiếng (lúc {time})",
                "priority": "medium"
            })
        
        return base_rules
    
    def _handle_rescheduling(self, scheduling_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Handle rescheduling requests"""
        return {
            "type": "rescheduling", 
            "message": "Rescheduling logic would be implemented here",
            "success": True
        }
    
    def _detect_time_conflicts(self, time_slots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect conflicts between time slots"""
        conflicts = []
        
        for i, slot1 in enumerate(time_slots):
            for j, slot2 in enumerate(time_slots[i+1:], i+1):
                if self._times_overlap(slot1, slot2):
                    conflicts.append({
                        "type": "time_overlap",
                        "description": f"Conflict between '{slot1['taskTitle']}' and '{slot2['taskTitle']}'",
                        "slots": [i, j],
                        "suggestions": [
                            f"Move '{slot2['taskTitle']}' to later time",
                            f"Reduce duration of '{slot1['taskTitle']}'"
                        ]
                    })
        
        return conflicts
    
    def _times_overlap(self, slot1: Dict[str, Any], slot2: Dict[str, Any]) -> bool:
        """Check if two time slots overlap"""
        try:
            start1 = datetime.strptime(slot1.get("startTime", "00:00"), "%H:%M")
            end1 = datetime.strptime(slot1.get("endTime", "00:00"), "%H:%M") 
            start2 = datetime.strptime(slot2.get("startTime", "00:00"), "%H:%M")
            end2 = datetime.strptime(slot2.get("endTime", "00:00"), "%H:%M")
            
            return not (end1 <= start2 or end2 <= start1)
        except:
            return False
    
    def get_user_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of user's data"""
        try:
            # Count tasks by status
            task_counts = {}
            for status in ["pending", "in_progress", "completed"]:
                query = {"userId": user_id, "status": status}
                count = len(self.task_repo.find_by_query(query, limit=1000))  # Assuming count method doesn't exist
                task_counts[status] = count
            
            # Count reminders
            reminder_query = {"userId": user_id, "status": "pending"}
            reminder_count = len(self.reminder_repo.find_by_query(reminder_query, limit=1000))
            
            # Count conversations
            conversation_query = {"userId": user_id}
            conversation_count = len(self.conversation_repo.find_by_query(conversation_query, limit=1000))
            
            # Recent activity
            recent_tasks = self.task_repo.find_by_query(
                {"userId": user_id}, 
                limit=5,
                sort=[("createdAt", -1)]
            )
            
            return {
                "success": True,
                "user_id": user_id,
                "task_counts": task_counts,
                "pending_reminders": reminder_count,
                "total_conversations": conversation_count,
                "recent_tasks": [{"title": t["title"], "status": t["status"]} for t in recent_tasks]
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_upcoming_reminders(self, user_id: str, hours_ahead: int = 24) -> List[Dict[str, Any]]:
        """Get upcoming reminders for user"""
        try:
            now = datetime.now()
            end_time = now + timedelta(hours=hours_ahead)
            
            reminder_query = {
                "userId": user_id,
                "status": "pending",
                "triggerTime": {"$gte": now, "$lte": end_time}
            }
            
            reminders = self.reminder_repo.find_by_query(
                reminder_query, 
                sort=[("triggerTime", 1)],
                limit=50
            )
            
            result = []
            for reminder in reminders:
                # Get associated task
                task_id = reminder.get("taskId")
                task = None
                if task_id:
                    task = self.task_repo.find_by_id(str(task_id))
                
                result.append({
                    "reminder_id": str(reminder.get("_id", reminder.get("id"))),
                    "trigger_time": reminder["triggerTime"].isoformat(),
                    "message": reminder["message"],
                    "task_title": task["title"] if task else "Unknown Task",
                    "task_id": str(task_id) if task_id else None,
                    "type": reminder.get("type", "time"),
                    "priority": reminder.get("priority", "medium")
                })
            
            return result
            
        except Exception as e:
            print(f"Error fetching upcoming reminders: {e}")
            return []
    
    def mark_reminder_sent(self, reminder_id: str) -> bool:
        """Mark reminder as sent"""
        try:
            update_data = {
                "status": "sent",
                "sentAt": datetime.now()
            }
            
            result = self.reminder_repo.update(reminder_id, update_data)
            return result is not None
            
        except Exception as e:
            print(f"Error marking reminder as sent: {e}")
            return False