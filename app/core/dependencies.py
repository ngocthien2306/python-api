from app.core.database import get_database
from app.services.database_manager import DatabaseManagerService
from app.repositories.conversation import ConversationRepository
from app.repositories.task import TaskRepository
from app.repositories.reminder import ReminderRepository
from app.repositories.schedule import ScheduleRepository

def get_conversation_repository():
    return ConversationRepository(get_database())

def get_task_repository():
    return TaskRepository(get_database())

def get_reminder_repository():
    return ReminderRepository(get_database())

def get_schedule_repository():
    return ScheduleRepository(get_database())

def get_database_manager():
    return DatabaseManagerService(
        conversation_repo=get_conversation_repository(),
        task_repo=get_task_repository(),
        reminder_repo=get_reminder_repository(),
        schedule_repo=get_schedule_repository()
    )
