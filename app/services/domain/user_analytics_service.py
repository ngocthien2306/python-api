from typing import Dict, Any, List
from datetime import datetime
from app.services.domain.task_service import TaskService
from app.services.domain.reminder_service import ReminderService
from app.services.domain.conversation_service import ConversationService
from app.services.domain.schedule_service import ScheduleService


class UserAnalyticsService:
    """Service for user analytics and comprehensive summaries"""
    
    def __init__(self, task_service: TaskService, reminder_service: ReminderService,
                 conversation_service: ConversationService, schedule_service: ScheduleService):
        self.task_service = task_service
        self.reminder_service = reminder_service
        self.conversation_service = conversation_service
        self.schedule_service = schedule_service
    
    def get_comprehensive_user_summary(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive summary of user's data across all services"""
        try:
            # Get summaries from each service
            task_summary = self.task_service.get_user_tasks_summary(user_id)
            reminder_summary = self.reminder_service.get_user_reminders_summary(user_id)
            conversation_summary = self.conversation_service.get_user_conversations_summary(user_id)
            schedule_summary = self.schedule_service.get_user_schedule_summary(user_id)
            
            # Aggregate data
            total_active_items = (
                task_summary.get("task_counts", {}).get("pending", 0) +
                task_summary.get("task_counts", {}).get("in_progress", 0) +
                reminder_summary.get("pending_reminders", 0)
            )
            
            productivity_score = self._calculate_productivity_score(
                task_summary, reminder_summary, schedule_summary
            )
            
            return {
                "success": True,
                "user_id": user_id,
                "summary_generated_at": str(datetime.now()),
                
                # Task metrics
                "tasks": {
                    "total_counts": task_summary.get("task_counts", {}),
                    "recent_tasks": task_summary.get("recent_tasks", [])
                },
                
                # Reminder metrics
                "reminders": {
                    "pending_count": reminder_summary.get("pending_reminders", 0)
                },
                
                # Conversation metrics
                "conversations": {
                    "total_count": conversation_summary.get("total_conversations", 0)
                },
                
                # Schedule metrics
                "schedules": {
                    "upcoming_workload": schedule_summary.get("total_workload", 0),
                    "conflicts_detected": schedule_summary.get("total_conflicts", 0)
                },
                
                # Aggregate insights
                "insights": {
                    "total_active_items": total_active_items,
                    "productivity_score": productivity_score,
                    "recommendations": self._generate_user_recommendations(
                        task_summary, reminder_summary, schedule_summary, productivity_score
                    )
                }
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_user_performance_metrics(self, user_id: str, days_back: int = 30) -> Dict[str, Any]:
        """Get user performance metrics over time"""
        try:
            # This would ideally track metrics over time
            # For now, providing current state analysis
            
            task_summary = self.task_service.get_user_tasks_summary(user_id)
            conversation_analysis = self.conversation_service.analyze_conversation_patterns(user_id, days_back)
            
            completed_tasks = task_summary.get("task_counts", {}).get("completed", 0)
            total_tasks = sum(task_summary.get("task_counts", {}).values())
            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            return {
                "success": True,
                "analysis_period": f"Last {days_back} days",
                "task_completion_rate": round(completion_rate, 2),
                "total_conversations": conversation_analysis.get("total_conversations", 0),
                "most_common_mood": conversation_analysis.get("most_common_mood", "neutral"),
                "engagement_level": self._calculate_engagement_level(conversation_analysis),
                "efficiency_trends": self._analyze_efficiency_trends(task_summary, conversation_analysis)
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _calculate_productivity_score(self, task_summary: Dict, reminder_summary: Dict, 
                                    schedule_summary: Dict) -> float:
        """Calculate productivity score based on various metrics"""
        score = 0.0
        
        # Task completion factor (40% weight)
        task_counts = task_summary.get("task_counts", {})
        completed = task_counts.get("completed", 0)
        total = sum(task_counts.values())
        if total > 0:
            completion_rate = completed / total
            score += completion_rate * 40
        
        # Organization factor (30% weight) - having reminders and schedules
        pending_reminders = reminder_summary.get("pending_reminders", 0)
        if pending_reminders > 0:
            score += 15  # Having reminders shows planning
        
        upcoming_workload = schedule_summary.get("total_workload", 0)
        if upcoming_workload > 0:
            score += 15  # Having scheduled work shows organization
        
        # Conflict management factor (20% weight)
        conflicts = schedule_summary.get("total_conflicts", 0)
        if conflicts == 0:
            score += 20  # No conflicts is good
        elif conflicts <= 2:
            score += 10  # Few conflicts is acceptable
        
        # Engagement factor (10% weight)
        if len(task_summary.get("recent_tasks", [])) > 0:
            score += 10  # Recent activity shows engagement
        
        return min(100, round(score, 1))
    
    def _calculate_engagement_level(self, conversation_analysis: Dict) -> str:
        """Calculate user engagement level based on conversation patterns"""
        total_conversations = conversation_analysis.get("total_conversations", 0)
        avg_messages = conversation_analysis.get("avg_messages_per_conversation", 0)
        
        if total_conversations >= 10 and avg_messages >= 4:
            return "high"
        elif total_conversations >= 5 and avg_messages >= 2:
            return "medium"
        elif total_conversations > 0:
            return "low"
        else:
            return "inactive"
    
    def _analyze_efficiency_trends(self, task_summary: Dict, conversation_analysis: Dict) -> List[str]:
        """Analyze efficiency trends based on data patterns"""
        trends = []
        
        # Task efficiency
        task_counts = task_summary.get("task_counts", {})
        pending = task_counts.get("pending", 0)
        in_progress = task_counts.get("in_progress", 0)
        
        if pending > in_progress * 2:
            trends.append("High task backlog - consider prioritization")
        
        if in_progress > 5:
            trends.append("Many concurrent tasks - risk of context switching")
        
        # Communication efficiency
        intent_patterns = conversation_analysis.get("intent_patterns", {})
        if intent_patterns.get("task_creation", 0) > intent_patterns.get("task_completion", 0):
            trends.append("Creating more tasks than completing - review task scope")
        
        # Mood trends
        mood_dist = conversation_analysis.get("mood_distribution", {})
        if mood_dist.get("stressed", 0) > mood_dist.get("positive", 0):
            trends.append("Stress levels elevated - consider workload adjustment")
        
        return trends or ["No significant efficiency issues detected"]
    
    def _generate_user_recommendations(self, task_summary: Dict, reminder_summary: Dict,
                                     schedule_summary: Dict, productivity_score: float) -> List[str]:
        """Generate personalized recommendations based on user data"""
        recommendations = []
        
        # Task-based recommendations
        task_counts = task_summary.get("task_counts", {})
        pending = task_counts.get("pending", 0)
        
        if pending > 10:
            recommendations.append("Consider breaking down large tasks into smaller subtasks")
        
        if pending > 0 and reminder_summary.get("pending_reminders", 0) == 0:
            recommendations.append("Add reminders to your important tasks to stay on track")
        
        # Schedule-based recommendations
        conflicts = schedule_summary.get("total_conflicts", 0)
        if conflicts > 0:
            recommendations.append(f"Resolve {conflicts} scheduling conflicts for better time management")
        
        workload = schedule_summary.get("total_workload", 0)
        if workload > 600:  # More than 10 hours
            recommendations.append("Consider reducing daily workload to prevent burnout")
        
        # Productivity-based recommendations
        if productivity_score < 50:
            recommendations.append("Focus on completing existing tasks before creating new ones")
        elif productivity_score > 80:
            recommendations.append("Great productivity! Consider taking on new challenges")
        
        return recommendations or ["Keep up the great work!"]