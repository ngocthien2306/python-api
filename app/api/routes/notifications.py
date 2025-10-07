"""
Notification Management API Routes
Provides CRUD operations for stored notifications
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import datetime
from app.utils.timezone_helper import local_now

from app.api.routes.auth import get_current_user
from app.repositories.notification import NotificationRepository
from app.models.notification import (
    StoredNotification,
    NotificationUpdate,
    NotificationList,
    NotificationStats,
    NotificationStatus,
    NotificationType,
    NotificationPriority
)
from app.models.user import User

router = APIRouter()

def get_notification_repository() -> NotificationRepository:
    """Get notification repository instance"""
    return NotificationRepository()

@router.get("/", response_model=NotificationList)
async def get_notifications(
    status: Optional[NotificationStatus] = Query(None, description="Filter by status"),
    notification_type: Optional[NotificationType] = Query(None, description="Filter by type"),
    priority: Optional[NotificationPriority] = Query(None, description="Filter by priority"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    include_expired: bool = Query(False, description="Include expired notifications"),
    current_user: User = Depends(get_current_user),
    notification_repo: NotificationRepository = Depends(get_notification_repository)
):
    """Get user notifications with filters and pagination"""
    try:
        return notification_repo.get_user_notifications(
            user_id=str(current_user.id),
            status=status,
            notification_type=notification_type,
            priority=priority,
            page=page,
            limit=limit,
            include_expired=include_expired
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get notifications: {str(e)}")

@router.get("/{notification_id}", response_model=StoredNotification)
async def get_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    notification_repo: NotificationRepository = Depends(get_notification_repository)
):
    """Get a specific notification"""
    notification = notification_repo.get_notification(notification_id, str(current_user.id))
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification

@router.patch("/{notification_id}", response_model=dict)
async def update_notification(
    notification_id: str,
    update_data: NotificationUpdate,
    current_user: User = Depends(get_current_user),
    notification_repo: NotificationRepository = Depends(get_notification_repository)
):
    """Update a notification"""
    success = notification_repo.update_notification(
        notification_id, 
        str(current_user.id), 
        update_data
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found or update failed")
    
    return {
        "success": True,
        "message": "Notification updated successfully",
        "notification_id": notification_id
    }

@router.post("/{notification_id}/read", response_model=dict)
async def mark_notification_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    notification_repo: NotificationRepository = Depends(get_notification_repository)
):
    """Mark a notification as read"""
    success = notification_repo.mark_as_read(notification_id, str(current_user.id))
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {
        "success": True,
        "message": "Notification marked as read",
        "notification_id": notification_id,
        "read_at": local_now().isoformat()
    }

@router.post("/mark-multiple-read", response_model=dict)
async def mark_multiple_notifications_as_read(
    notification_ids: List[str],
    current_user: User = Depends(get_current_user),
    notification_repo: NotificationRepository = Depends(get_notification_repository)
):
    """Mark multiple notifications as read"""
    if not notification_ids:
        raise HTTPException(status_code=400, detail="No notification IDs provided")
    
    if len(notification_ids) > 100:
        raise HTTPException(status_code=400, detail="Too many notification IDs (max 100)")
    
    count = notification_repo.mark_multiple_as_read(notification_ids, str(current_user.id))
    
    return {
        "success": True,
        "message": f"Marked {count} notifications as read",
        "updated_count": count
    }

@router.delete("/{notification_id}", response_model=dict)
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    notification_repo: NotificationRepository = Depends(get_notification_repository)
):
    """Delete a notification"""
    success = notification_repo.delete_notification(notification_id, str(current_user.id))
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {
        "success": True,
        "message": "Notification deleted successfully",
        "notification_id": notification_id
    }

@router.post("/delete-multiple", response_model=dict)
async def delete_multiple_notifications(
    notification_ids: List[str],
    current_user: User = Depends(get_current_user),
    notification_repo: NotificationRepository = Depends(get_notification_repository)
):
    """Delete multiple notifications"""
    if not notification_ids:
        raise HTTPException(status_code=400, detail="No notification IDs provided")
    
    if len(notification_ids) > 100:
        raise HTTPException(status_code=400, detail="Too many notification IDs (max 100)")
    
    count = notification_repo.delete_multiple_notifications(notification_ids, str(current_user.id))
    
    return {
        "success": True,
        "message": f"Deleted {count} notifications",
        "deleted_count": count
    }

@router.post("/clear", response_model=dict)
async def clear_old_notifications(
    older_than_days: int = Query(30, ge=1, le=365, description="Clear notifications older than X days"),
    current_user: User = Depends(get_current_user),
    notification_repo: NotificationRepository = Depends(get_notification_repository)
):
    """Clear old notifications for the user"""
    count = notification_repo.clear_user_notifications(str(current_user.id), older_than_days)
    
    return {
        "success": True,
        "message": f"Cleared {count} old notifications (older than {older_than_days} days)",
        "cleared_count": count
    }

@router.get("/stats/summary", response_model=NotificationStats)
async def get_notification_stats(
    current_user: User = Depends(get_current_user),
    notification_repo: NotificationRepository = Depends(get_notification_repository)
):
    """Get notification statistics for the user"""
    return notification_repo.get_notification_stats(str(current_user.id))

@router.get("/unread/count", response_model=dict)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    notification_repo: NotificationRepository = Depends(get_notification_repository)
):
    """Get unread notification count"""
    result = notification_repo.get_user_notifications(
        user_id=str(current_user.id),
        status=NotificationStatus.UNREAD,
        page=1,
        limit=1
    )
    
    return {
        "unread_count": result.unread_count,
        "user_id": str(current_user.id)
    }

@router.post("/sync", response_model=dict)
async def sync_notifications(
    since: Optional[datetime] = Query(None, description="Sync notifications since this timestamp"),
    current_user: User = Depends(get_current_user),
    notification_repo: NotificationRepository = Depends(get_notification_repository)
):
    """Sync notifications for frontend"""
    try:
        # Get recent notifications
        limit = 50 if since else 20
        
        notifications = notification_repo.get_user_notifications(
            user_id=str(current_user.id),
            page=1,
            limit=limit
        )
        
        # Filter by timestamp if provided
        if since:
            filtered_notifications = [
                n for n in notifications.notifications 
                if n.created_at > since or (n.updated_at and n.updated_at > since)
            ]
        else:
            filtered_notifications = notifications.notifications
        
        return {
            "success": True,
            "notifications": [n.dict() for n in filtered_notifications],
            "count": len(filtered_notifications),
            "unread_count": notifications.unread_count,
            "sync_timestamp": local_now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync notifications: {str(e)}")

# Admin/Debug endpoints (can be removed in production)
@router.post("/admin/cleanup-expired", response_model=dict)
async def cleanup_expired_notifications(
    notification_repo: NotificationRepository = Depends(get_notification_repository)
):
    """Clean up expired notifications (admin only)"""
    count = notification_repo.cleanup_expired_notifications()
    return {
        "success": True,
        "message": f"Cleaned up {count} expired notifications",
        "cleaned_count": count
    }