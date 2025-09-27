from typing import Dict, Any, List
from datetime import datetime
from app.schemas.ai_response import AIResponse
from app.services.domain.task_service import TaskService
from app.services.domain.reminder_service import ReminderService
from app.services.domain.schedule_service import ScheduleService
from app.services.domain.conversation_service import ConversationService
from app.services.domain.user_analytics_service import UserAnalyticsService
from app.services.domain.user_service import UserService
import traceback


class DatabaseManagerService:
    """
    Orchestrator service that coordinates between domain services
    Follows Single Responsibility Principle - only orchestrates, doesn't implement business logic
    """
    
    def __init__(self, 
                 task_service: TaskService,
                 reminder_service: ReminderService,
                 schedule_service: ScheduleService,
                 conversation_service: ConversationService,
                 user_analytics_service: UserAnalyticsService,
                 user_service: UserService):
        self.task_service = task_service
        self.reminder_service = reminder_service
        self.schedule_service = schedule_service
        self.conversation_service = conversation_service
        self.user_analytics_service = user_analytics_service
        self.user_service = user_service
    
    def process_ai_response(self, parsed_response: AIResponse, user_input: str, 
                          user_id: str) -> Dict[str, Any]:
        """
        Main orchestrator method - delegates to appropriate domain services
        This is now much cleaner and focused on coordination only
        """
        session_id = f"{user_id}_{int(datetime.now().timestamp())}"
        results = {"session_id": session_id, "operations": []}
        
        try:
            mode = parsed_response.mode
            
            # Always save conversation first (single responsibility)
            conv_result = self.conversation_service.save_conversation(
                parsed_response, user_input, user_id, session_id
            )
            results["operations"].append({"type": "conversation", "result": conv_result})
            
            # Delegate to appropriate service based on mode
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
    
    def _handle_simple_task(self, parsed_response: AIResponse, user_input: str, user_id: str) -> Dict[str, Any]:
        """Handle simple task operations by delegating to TaskService"""
        task_action = parsed_response.taskAction
        if not task_action:
            return {"action": "none", "message": "No task action provided"}
            
        action = task_action.action
        results = {"action": action}
        
        if action == "create" and task_action.task:
            # Create task using TaskService
            task_result = self.task_service.create_task(
                task_action.task.dict(), user_input, user_id
            )
            results.update(task_result)
            
            # Create reminders using ReminderService
            if task_result.get("task_id"):
                reminder_result = self.reminder_service.create_task_reminders(
                    task_result["task_id"], 
                    task_action.task.dict(), 
                    user_id
                )
                results["reminders"] = reminder_result
        
        elif action == "update":
            # Extract update data from task_action
            task_id = task_action.dict().get("taskId")
            updates = task_action.dict().get("updates", {})
            results.update(self.task_service.update_task(task_id, updates, user_id))
            
        elif action == "delete":
            # Delete task and associated reminders
            task_id = task_action.dict().get("taskId")
            # First delete reminders
            self.reminder_service.delete_reminders_by_task_id(task_id)
            # Then delete task
            results.update(self.task_service.delete_task(task_id, user_id))
            
        elif action == "query":
            # Query tasks
            filters = task_action.dict().get("filters", {})
            results.update(self.task_service.query_tasks(user_id, filters))
        
        return results
    
    def _handle_scheduling(self, parsed_response: AIResponse, user_input: str, user_id: str) -> Dict[str, Any]:
        """Handle scheduling operations by delegating to ScheduleService"""
        scheduling_action = parsed_response.schedulingAction
        if not scheduling_action:
            return {"type": "none", "message": "No scheduling action provided"}
            
        schedule_type = scheduling_action.type
        results = {"type": schedule_type}
        
        if schedule_type == "daily_planning":
            results.update(self.schedule_service.create_daily_schedule(
                scheduling_action.dict(), user_id
            ))
            
        elif schedule_type == "weekly_planning":
            results.update(self.schedule_service.create_weekly_schedule(
                scheduling_action.dict(), user_id
            ))
            
        elif schedule_type == "rescheduling":
            results.update(self.schedule_service.reschedule_tasks(
                scheduling_action.dict(), user_id
            ))
        
        return results
    
    # Public API methods for external access to domain services
    
    def get_user_summary(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user summary using UserAnalyticsService"""
        return self.user_analytics_service.get_comprehensive_user_summary(user_id)
    
    def get_upcoming_reminders(self, user_id: str, hours_ahead: int = 24) -> List[Dict[str, Any]]:
        """Get upcoming reminders using ReminderService"""
        return self.reminder_service.get_upcoming_reminders(user_id, hours_ahead)
    
    def mark_reminder_sent(self, reminder_id: str) -> bool:
        """Mark reminder as sent using ReminderService"""
        return self.reminder_service.mark_reminder_sent(reminder_id)
    
    def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history using ConversationService"""
        return self.conversation_service.get_conversation_history(user_id, limit)
    
    def analyze_user_patterns(self, user_id: str, days_back: int = 30) -> Dict[str, Any]:
        """Get user performance metrics using UserAnalyticsService"""
        return self.user_analytics_service.get_user_performance_metrics(user_id, days_back)
    
    def get_task_summary(self, user_id: str) -> Dict[str, Any]:
        """Get task summary using TaskService"""
        return self.task_service.get_user_tasks_summary(user_id)
    
    def get_schedule_summary(self, user_id: str, days_ahead: int = 7) -> Dict[str, Any]:
        """Get schedule summary using ScheduleService"""  
        return self.schedule_service.get_user_schedule_summary(user_id, days_ahead)
    
    # User Profile Management Methods for Onboarding
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile data using UserService"""
        return await self.user_service.get_user_profile(user_id)
    
    async def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update user profile using UserService"""
        return await self.user_service.update_user_profile(user_id, updates)
    