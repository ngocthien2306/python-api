"""
Notification Models for persistent storage and WebSocket notifications
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class NotificationType(str, Enum):
    TASK_REMINDER = "task_reminder"
    TASK_DUE = "task_due"
    TASK_OVERDUE = "task_overdue"
    SYSTEM_ALERT = "system_alert"
    GENERAL = "general"

class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class NotificationStatus(str, Enum):
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"
    DISMISSED = "dismissed"

class NotificationAction(BaseModel):
    """Action that can be taken on notification"""
    type: str = Field(..., description="Action type (navigate, api_call, etc.)")
    url: Optional[str] = Field(None, description="URL to navigate to")
    method: Optional[str] = Field(None, description="HTTP method for API calls")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional action data")

class TaskInfo(BaseModel):
    """Task information embedded in notification"""
    id: str
    title: str
    priority: str
    status: str
    due_date: Optional[str] = None
    due_time: Optional[str] = None
    category: Optional[str] = None

class NotificationData(BaseModel):
    """Additional notification data"""
    task: Optional[TaskInfo] = None
    extra: Optional[Dict[str, Any]] = None

class NotificationBase(BaseModel):
    """Base notification model"""
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body/message")
    type: NotificationType = Field(default=NotificationType.GENERAL)
    priority: NotificationPriority = Field(default=NotificationPriority.MEDIUM)
    status: NotificationStatus = Field(default=NotificationStatus.UNREAD)
    action: Optional[NotificationAction] = None
    data: Optional[NotificationData] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class NotificationCreate(NotificationBase):
    """Model for creating notifications"""
    user_id: str = Field(..., description="User ID to send notification to")
    scheduled_for: Optional[datetime] = Field(None, description="Schedule notification for future")
    expires_at: Optional[datetime] = Field(None, description="Notification expiration")
    created_at: Optional[datetime] = Field(None, description="Custom creation timestamp (in user timezone)")
    updated_at: Optional[datetime] = Field(None, description="Custom update timestamp (in user timezone)")

class NotificationUpdate(BaseModel):
    """Model for updating notifications"""
    status: Optional[NotificationStatus] = None
    read_at: Optional[datetime] = None

class StoredNotification(NotificationBase):
    """Full notification model with timestamps"""
    id: str = Field(..., description="Notification ID")
    user_id: str = Field(..., description="User ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    read_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    scheduled_for: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # Delivery tracking
    delivery_attempts: int = Field(default=0)
    last_delivery_attempt: Optional[datetime] = None
    delivered_via: Optional[str] = None  # websocket, email, push, etc.
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class NotificationList(BaseModel):
    """Paginated notification list"""
    notifications: list[StoredNotification]
    total: int
    page: int
    limit: int
    has_next: bool
    has_prev: bool
    unread_count: int

class NotificationStats(BaseModel):
    """Notification statistics"""
    total: int
    unread: int
    read: int
    archived: int
    dismissed: int
    by_type: Dict[str, int]
    by_priority: Dict[str, int]
    recent_count: int  # Last 24 hours