"""
New dependency injection setup using the refactored service architecture
This replaces the old dependencies.py with clean separation of concerns
"""

from app.core.database import get_database
from app.repositories.conversation import ConversationRepository
from app.repositories.task import TaskRepository
from app.repositories.reminder import ReminderRepository
from app.repositories.schedule import ScheduleRepository
from app.repositories.user import UserRepository
from app.services.service_factory import ServiceFactory, create_service_factory
from app.services.database_manager import DatabaseManagerService
from app.services.domain.task_service import TaskService
from app.services.domain.reminder_service import ReminderService
from app.services.domain.schedule_service import ScheduleService
from app.services.domain.conversation_service import ConversationService
from app.services.domain.user_analytics_service import UserAnalyticsService
from app.services.domain.user_service import UserService
from app.services.scheduling.conflict_detector import ConflictDetectionService

# Singleton service factory instance
_service_factory: ServiceFactory = None


def get_service_factory() -> ServiceFactory:
    """Get or create the service factory singleton"""
    global _service_factory
    
    if _service_factory is None:
        # Create repositories
        conversation_repo = ConversationRepository(get_database())
        task_repo = TaskRepository(get_database())
        reminder_repo = ReminderRepository(get_database())
        schedule_repo = ScheduleRepository(get_database())
        user_repo = UserRepository(get_database())
        
        # Create service factory with all dependencies wired up
        _service_factory = create_service_factory(
            conversation_repo, task_repo, reminder_repo, schedule_repo, user_repo
        )
    
    return _service_factory


# Main service dependencies (backward compatibility)
def get_database_manager() -> DatabaseManagerService:
    """Get the main database manager service (orchestrator)"""
    return get_service_factory().get_database_manager()


# Individual service dependencies (for when you need specific services)
def get_task_service() -> TaskService:
    """Get task service directly"""
    return get_service_factory().get_task_service()


def get_reminder_service() -> ReminderService:
    """Get reminder service directly"""
    return get_service_factory().get_reminder_service()


def get_schedule_service() -> ScheduleService:
    """Get schedule service directly"""
    return get_service_factory().get_schedule_service()


def get_conversation_service() -> ConversationService:
    """Get conversation service directly"""
    return get_service_factory().get_conversation_service()


def get_user_analytics_service() -> UserAnalyticsService:
    """Get user analytics service directly"""
    return get_service_factory().get_user_analytics_service()


def get_conflict_detector() -> ConflictDetectionService:
    """Get conflict detection service directly"""
    return get_service_factory().get_conflict_detector()


# Repository dependencies (if needed directly)
def get_conversation_repository() -> ConversationRepository:
    """Get conversation repository directly"""
    return ConversationRepository(get_database())


def get_task_repository() -> TaskRepository:
    """Get task repository directly"""
    return TaskRepository(get_database())


def get_reminder_repository() -> ReminderRepository:
    """Get reminder repository directly"""
    return ReminderRepository(get_database())


def get_schedule_repository() -> ScheduleRepository:
    """Get schedule repository directly"""
    return ScheduleRepository(get_database())


def get_user_repository() -> UserRepository:
    """Get user repository directly"""
    return UserRepository(get_database())


def get_user_service() -> UserService:
    """Get user service directly"""
    return get_service_factory().get_user_service()