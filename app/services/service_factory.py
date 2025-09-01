from app.repositories.conversation import ConversationRepository
from app.repositories.task import TaskRepository
from app.repositories.reminder import ReminderRepository
from app.repositories.schedule import ScheduleRepository
from app.repositories.user import UserRepository

from app.services.domain.task_service import TaskService
from app.services.domain.reminder_service import ReminderService
from app.services.domain.schedule_service import ScheduleService
from app.services.domain.conversation_service import ConversationService
from app.services.domain.user_analytics_service import UserAnalyticsService
from app.services.domain.user_service import UserService
from app.services.scheduling.conflict_detector import ConflictDetectionService
from app.services.database_manager import DatabaseManagerService


class ServiceFactory:
    """
    Factory class for creating and wiring up all services with proper dependencies
    Implements Dependency Injection pattern
    """
    
    def __init__(self, 
                 conversation_repo: ConversationRepository,
                 task_repo: TaskRepository, 
                 reminder_repo: ReminderRepository,
                 schedule_repo: ScheduleRepository,
                 user_repo: UserRepository):
        self.conversation_repo = conversation_repo
        self.task_repo = task_repo
        self.reminder_repo = reminder_repo
        self.schedule_repo = schedule_repo
        self.user_repo = user_repo
        
        # Initialize services with proper dependencies
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize all services with proper dependency injection"""
        
        # Domain services (no cross-dependencies)
        self.task_service = TaskService(self.task_repo)
        self.reminder_service = ReminderService(self.reminder_repo, self.task_repo)
        self.conversation_service = ConversationService(self.conversation_repo)
        self.user_service = UserService(self.user_repo)
        
        # Specialized services
        self.conflict_detector = ConflictDetectionService()
        
        # Schedule service depends on task_service, reminder_service, and conflict_detector
        self.schedule_service = ScheduleService(
            self.schedule_repo,
            self.task_service,
            self.reminder_service, 
            self.conflict_detector
        )
        
        # Analytics service depends on all domain services
        self.user_analytics_service = UserAnalyticsService(
            self.task_service,
            self.reminder_service,
            self.conversation_service,
            self.schedule_service
        )
        
        # Main orchestrator service
        self.database_manager = DatabaseManagerService(
            self.task_service,
            self.reminder_service,
            self.schedule_service,
            self.conversation_service,
            self.user_analytics_service,
            self.user_service
        )
    
    def get_database_manager(self) -> DatabaseManagerService:
        """Get the main database manager service"""
        return self.database_manager
    
    def get_task_service(self) -> TaskService:
        """Get task service for direct access"""
        return self.task_service
    
    def get_reminder_service(self) -> ReminderService:
        """Get reminder service for direct access"""
        return self.reminder_service
    
    def get_schedule_service(self) -> ScheduleService:
        """Get schedule service for direct access"""
        return self.schedule_service
    
    def get_conversation_service(self) -> ConversationService:
        """Get conversation service for direct access"""
        return self.conversation_service
    
    def get_user_analytics_service(self) -> UserAnalyticsService:
        """Get user analytics service for direct access"""
        return self.user_analytics_service
    
    def get_conflict_detector(self) -> ConflictDetectionService:
        """Get conflict detection service for direct access"""
        return self.conflict_detector
    
    def get_user_service(self) -> UserService:
        """Get user service for direct access"""
        return self.user_service


# Convenience function for creating the factory
def create_service_factory(conversation_repo: ConversationRepository,
                          task_repo: TaskRepository,
                          reminder_repo: ReminderRepository,
                          schedule_repo: ScheduleRepository,
                          user_repo: UserRepository) -> ServiceFactory:
    """Create and configure service factory with repositories"""
    return ServiceFactory(conversation_repo, task_repo, reminder_repo, schedule_repo, user_repo)