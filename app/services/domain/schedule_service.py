from typing import Dict, Any, List
from datetime import datetime, timedelta
from app.repositories.schedule import ScheduleRepository
from app.models.schedule import Schedule
from app.services.domain.task_service import TaskService
from app.services.domain.reminder_service import ReminderService
from app.services.scheduling.conflict_detector import ConflictDetectionService


class ScheduleService:
    """Service responsible for all schedule-related operations"""
    
    def __init__(self, schedule_repo: ScheduleRepository, task_service: TaskService, 
                 reminder_service: ReminderService, conflict_detector: ConflictDetectionService):
        self.schedule_repo = schedule_repo
        self.task_service = task_service
        self.reminder_service = reminder_service
        self.conflict_detector = conflict_detector
    
    def create_daily_schedule(self, scheduling_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Create daily schedule with tasks and reminders"""
        today = datetime.now().date()
        tasks = scheduling_data.get("tasks", [])
        
        # Create schedule model
        schedule = Schedule(user_id, datetime.combine(today, datetime.min.time()), "daily")
        schedule.version = 1
        
        total_minutes = 0
        created_tasks = []
        all_reminders = []
        
        # Process each task
        for task_data in tasks:
            # Create time slot info
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
            
            # Create the actual task
            scheduled_date = datetime.combine(today, datetime.min.time())
            task_id = self.task_service.create_scheduled_task(
                task_data, user_id, scheduled_date, "auto-scheduled"
            )
            
            time_slot_dict["taskId"] = task_id
            created_tasks.append(task_id)
            
            # Create reminders for scheduled task
            reminders = self.reminder_service.create_schedule_reminders(
                task_id, task_data, user_id, today
            )
            all_reminders.extend(reminders)
            
            schedule.time_slots.append(time_slot_dict)
            total_minutes += int(task_data.get("duration", 60))
        
        schedule.total_workload = total_minutes
        
        # Detect and handle conflicts
        conflicts = self.conflict_detector.detect_time_conflicts(schedule.time_slots)
        schedule.conflicts = len(conflicts)
        
        # Validate schedule
        validation_result = self.conflict_detector.validate_schedule(schedule.time_slots)
        
        # Convert to database format and save
        schedule_doc = self._convert_schedule_to_db_format(schedule)
        schedule_id = self.schedule_repo.create(schedule_doc)
        
        return {
            "schedule_id": schedule_id,
            "date": today.isoformat(),
            "tasks_count": len(tasks),
            "total_workload": total_minutes,
            "conflicts_detected": len(conflicts),
            "created_tasks": created_tasks,
            "created_reminders": all_reminders,
            "validation": validation_result,
            "recommendations": validation_result.get("recommendations", [])
        }
    
    def create_weekly_schedule(self, scheduling_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Create weekly schedule with tasks and reminders"""
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())  # Monday
        
        schedule = Schedule(user_id, start_of_week, "weekly")
        schedule.end_date = start_of_week + timedelta(days=6)
        schedule.weekly_goals = []
        
        all_reminders = []
        created_tasks = []
        daily_schedules = []
        
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
                # Create task using task service
                task_id = self.task_service.create_scheduled_task(
                    task_data, user_id, current_date, "weekly-planning"
                )
                created_tasks.append(task_id)
                
                # Create reminders for weekly tasks
                reminders = self.reminder_service.create_schedule_reminders(
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
            
            daily_schedules.append(daily_schedule)
            schedule.total_workload += daily_schedule["workload"]
        
        schedule.daily_schedules = daily_schedules
        
        # Save weekly schedule
        schedule_doc = self._convert_schedule_to_db_format(schedule)
        schedule_doc["endDate"] = schedule.end_date
        schedule_doc["weeklyGoals"] = schedule.weekly_goals
        schedule_doc["dailySchedules"] = schedule.daily_schedules
        
        schedule_id = self.schedule_repo.create(schedule_doc)
        
        return {
            "schedule_id": schedule_id,
            "type": "weekly_planning",
            "week_start": start_of_week.isoformat(),
            "total_workload": schedule.total_workload,
            "created_tasks": created_tasks,
            "created_reminders": all_reminders,
            "daily_schedules": len(daily_schedules)
        }
    
    def reschedule_tasks(self, scheduling_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Handle rescheduling requests"""
        # Extract rescheduling details
        task_ids = scheduling_data.get("taskIds", [])
        new_time_slots = scheduling_data.get("newTimeSlots", [])
        reason = scheduling_data.get("reason", "user_request")
        
        if not task_ids or not new_time_slots:
            return {
                "success": False,
                "error": "Task IDs and new time slots are required"
            }
        
        rescheduled_tasks = []
        failed_reschedules = []
        
        for i, task_id in enumerate(task_ids):
            if i < len(new_time_slots):
                new_slot = new_time_slots[i]
                
                # Update task with new schedule
                update_result = self.task_service.update_task(
                    task_id,
                    {
                        "dueTime": new_slot.get("startTime"),
                        "scheduledSlot": new_slot
                    },
                    user_id
                )
                
                if update_result.get("success"):
                    rescheduled_tasks.append(task_id)
                else:
                    failed_reschedules.append({
                        "task_id": task_id,
                        "error": update_result.get("error")
                    })
        
        return {
            "success": True,
            "type": "rescheduling", 
            "rescheduled_count": len(rescheduled_tasks),
            "failed_count": len(failed_reschedules),
            "rescheduled_tasks": rescheduled_tasks,
            "failures": failed_reschedules,
            "reason": reason
        }
    
    def get_user_schedule_summary(self, user_id: str, days_ahead: int = 7) -> Dict[str, Any]:
        """Get schedule summary for user"""
        try:
            start_date = datetime.now()
            end_date = start_date + timedelta(days=days_ahead)
            
            schedule_query = {
                "userId": user_id,
                "date": {"$gte": start_date, "$lte": end_date}
            }
            
            schedules = self.schedule_repo.find_by_query(schedule_query, limit=50)
            
            total_workload = sum([s.get("totalWorkload", 0) for s in schedules])
            total_conflicts = sum([s.get("conflicts", 0) for s in schedules])
            
            return {
                "success": True,
                "schedules_count": len(schedules),
                "total_workload": total_workload,
                "total_conflicts": total_conflicts,
                "period": f"{start_date.date()} to {end_date.date()}"
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _convert_schedule_to_db_format(self, schedule: Schedule) -> Dict[str, Any]:
        """Convert Schedule model to database format"""
        schedule_doc = schedule.to_dict()
        schedule_doc["userId"] = schedule_doc.pop("user_id")
        schedule_doc["timeSlots"] = schedule.time_slots
        schedule_doc["totalWorkload"] = schedule_doc.pop("total_workload")
        schedule_doc["createdAt"] = schedule_doc.pop("created_at")
        schedule_doc["updatedAt"] = schedule_doc.pop("updated_at")
        return schedule_doc
    
    def _generate_weekly_tasks(self, day_offset: int, scheduling_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate sample tasks for weekly planning"""
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        current_day = day_names[day_offset]
        
        # Use custom tasks from scheduling_data if provided
        custom_tasks = scheduling_data.get("weeklyTasks", {})
        if custom_tasks.get(current_day.lower()):
            return custom_tasks[current_day.lower()]
        
        # Generate default tasks based on day type
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