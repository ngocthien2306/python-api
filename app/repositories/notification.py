"""
Notification Repository for persistent storage
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from bson import ObjectId
from pymongo.collection import Collection
from pymongo import DESCENDING

from app.core.database import get_database
from app.models.notification import (
    StoredNotification, 
    NotificationCreate, 
    NotificationUpdate,
    NotificationStatus,
    NotificationType,
    NotificationPriority,
    NotificationList,
    NotificationStats
)

logger = logging.getLogger(__name__)

class NotificationRepository:
    """Repository for notification operations"""
    
    def __init__(self):
        self.db = get_database()
        self.collection: Collection = self.db.notifications
        
        # Create indexes for better performance
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes"""
        try:
            # Index for user queries
            self.collection.create_index([("user_id", 1), ("created_at", -1)])
            
            # Index for status queries
            self.collection.create_index([("user_id", 1), ("status", 1), ("created_at", -1)])
            
            # Index for type queries
            self.collection.create_index([("user_id", 1), ("type", 1), ("created_at", -1)])
            
            # Index for expiration cleanup
            self.collection.create_index([("expires_at", 1)], sparse=True)
            
            # Index for scheduled notifications
            self.collection.create_index([("scheduled_for", 1)], sparse=True)
            
            # Index for reminder ID lookup
            self.collection.create_index([("metadata.reminder_id", 1)], sparse=True)
            
            logger.info("Notification indexes created successfully")
        except Exception as e:
            logger.error(f"Failed to create notification indexes: {e}")
    
    def create_notification(self, notification_data: NotificationCreate) -> StoredNotification:
        """Create a new notification"""
        try:
            # Prepare document
            doc = {
                "_id": ObjectId(),
                "user_id": notification_data.user_id,
                "title": notification_data.title,
                "body": notification_data.body,
                "type": notification_data.type,
                "priority": notification_data.priority,
                "status": notification_data.status,
                "action": notification_data.action.dict() if notification_data.action else None,
                "data": notification_data.data.dict() if notification_data.data else None,
                "metadata": notification_data.metadata or {},
                "created_at": getattr(notification_data, 'created_at', datetime.utcnow()),
                "updated_at": getattr(notification_data, 'updated_at', datetime.utcnow()),
                "scheduled_for": notification_data.scheduled_for,
                "expires_at": notification_data.expires_at,
                "delivery_attempts": 0,
                "read_at": None,
                "sent_at": None,
                "last_delivery_attempt": None,
                "delivered_via": None
            }
            
            # Insert into database
            result = self.collection.insert_one(doc)
            
            # Return created notification
            doc["id"] = str(result.inserted_id)
            return StoredNotification(**doc)
            
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            raise
    
    def get_notification(self, notification_id: str, user_id: str) -> Optional[StoredNotification]:
        """Get a specific notification"""
        try:
            doc = self.collection.find_one({
                "_id": ObjectId(notification_id),
                "user_id": user_id
            })
            
            if doc:
                doc["id"] = str(doc["_id"])
                return StoredNotification(**doc)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get notification {notification_id}: {e}")
            return None
    
    def get_user_notifications(
        self, 
        user_id: str, 
        status: Optional[NotificationStatus] = None,
        notification_type: Optional[NotificationType] = None,
        priority: Optional[NotificationPriority] = None,
        page: int = 1,
        limit: int = 20,
        include_expired: bool = False
    ) -> NotificationList:
        """Get paginated notifications for a user"""
        try:
            # Build query
            query = {"user_id": user_id}
            
            if status:
                query["status"] = status
            
            if notification_type:
                query["type"] = notification_type
                
            if priority:
                query["priority"] = priority
            
            # Exclude expired notifications unless requested
            if not include_expired:
                query["$or"] = [
                    {"expires_at": None},
                    {"expires_at": {"$gt": datetime.utcnow()}}
                ]
            
            # Count total
            total = self.collection.count_documents(query)
            
            # Count unread
            unread_query = {**query, "status": NotificationStatus.UNREAD}
            unread_count = self.collection.count_documents(unread_query)
            
            # Get paginated results
            skip = (page - 1) * limit
            cursor = self.collection.find(query) \
                .sort("created_at", DESCENDING) \
                .skip(skip) \
                .limit(limit)
            
            notifications = []
            for doc in cursor:
                doc["id"] = str(doc["_id"])
                notifications.append(StoredNotification(**doc))
            
            return NotificationList(
                notifications=notifications,
                total=total,
                page=page,
                limit=limit,
                has_next=skip + limit < total,
                has_prev=page > 1,
                unread_count=unread_count
            )
            
        except Exception as e:
            logger.error(f"Failed to get user notifications: {e}")
            return NotificationList(
                notifications=[],
                total=0,
                page=page,
                limit=limit,
                has_next=False,
                has_prev=False,
                unread_count=0
            )
    
    def update_notification(
        self, 
        notification_id: str, 
        user_id: str, 
        update_data: NotificationUpdate
    ) -> bool:
        """Update a notification"""
        try:
            update_doc = {"updated_at": datetime.utcnow()}
            
            if update_data.status:
                update_doc["status"] = update_data.status
                
                if update_data.status == NotificationStatus.READ and not update_data.read_at:
                    update_doc["read_at"] = datetime.utcnow()
            
            if update_data.read_at:
                update_doc["read_at"] = update_data.read_at
            
            result = self.collection.update_one(
                {"_id": ObjectId(notification_id), "user_id": user_id},
                {"$set": update_doc}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to update notification {notification_id}: {e}")
            return False
    
    def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """Mark notification as read"""
        return self.update_notification(
            notification_id, 
            user_id, 
            NotificationUpdate(
                status=NotificationStatus.READ,
                read_at=datetime.utcnow()
            )
        )
    
    def mark_multiple_as_read(self, notification_ids: List[str], user_id: str) -> int:
        """Mark multiple notifications as read"""
        try:
            object_ids = [ObjectId(nid) for nid in notification_ids]
            result = self.collection.update_many(
                {
                    "_id": {"$in": object_ids},
                    "user_id": user_id,
                    "status": NotificationStatus.UNREAD
                },
                {
                    "$set": {
                        "status": NotificationStatus.READ,
                        "read_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count
            
        except Exception as e:
            logger.error(f"Failed to mark multiple notifications as read: {e}")
            return 0
    
    def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """Delete a notification"""
        try:
            result = self.collection.delete_one({
                "_id": ObjectId(notification_id),
                "user_id": user_id
            })
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Failed to delete notification {notification_id}: {e}")
            return False
    
    def delete_multiple_notifications(self, notification_ids: List[str], user_id: str) -> int:
        """Delete multiple notifications"""
        try:
            object_ids = [ObjectId(nid) for nid in notification_ids]
            result = self.collection.delete_many({
                "_id": {"$in": object_ids},
                "user_id": user_id
            })
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete multiple notifications: {e}")
            return 0
    
    def clear_user_notifications(self, user_id: str, older_than_days: int = 30) -> int:
        """Clear old notifications for a user"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
            result = self.collection.delete_many({
                "user_id": user_id,
                "created_at": {"$lt": cutoff_date}
            })
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Failed to clear user notifications: {e}")
            return 0
    
    def get_notification_stats(self, user_id: str) -> NotificationStats:
        """Get notification statistics for a user"""
        try:
            # Get counts by status
            pipeline = [
                {"$match": {"user_id": user_id}},
                {"$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }}
            ]
            
            status_counts = {}
            total = 0
            for result in self.collection.aggregate(pipeline):
                status_counts[result["_id"]] = result["count"]
                total += result["count"]
            
            # Get counts by type
            type_pipeline = [
                {"$match": {"user_id": user_id}},
                {"$group": {
                    "_id": "$type",
                    "count": {"$sum": 1}
                }}
            ]
            
            type_counts = {}
            for result in self.collection.aggregate(type_pipeline):
                type_counts[result["_id"]] = result["count"]
            
            # Get counts by priority
            priority_pipeline = [
                {"$match": {"user_id": user_id}},
                {"$group": {
                    "_id": "$priority",
                    "count": {"$sum": 1}
                }}
            ]
            
            priority_counts = {}
            for result in self.collection.aggregate(priority_pipeline):
                priority_counts[result["_id"]] = result["count"]
            
            # Get recent count (last 24 hours)
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_count = self.collection.count_documents({
                "user_id": user_id,
                "created_at": {"$gte": recent_cutoff}
            })
            
            return NotificationStats(
                total=total,
                unread=status_counts.get("unread", 0),
                read=status_counts.get("read", 0),
                archived=status_counts.get("archived", 0),
                dismissed=status_counts.get("dismissed", 0),
                by_type=type_counts,
                by_priority=priority_counts,
                recent_count=recent_count
            )
            
        except Exception as e:
            logger.error(f"Failed to get notification stats: {e}")
            return NotificationStats(
                total=0, unread=0, read=0, archived=0, dismissed=0,
                by_type={}, by_priority={}, recent_count=0
            )
    
    def record_delivery(
        self, 
        notification_id: str, 
        delivery_method: str,
        success: bool = True
    ) -> bool:
        """Record notification delivery attempt"""
        try:
            update_doc = {
                "delivery_attempts": {"$inc": 1},
                "last_delivery_attempt": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            if success:
                update_doc.update({
                    "sent_at": datetime.utcnow(),
                    "delivered_via": delivery_method
                })
            
            result = self.collection.update_one(
                {"_id": ObjectId(notification_id)},
                {"$set": update_doc if success else {}, "$inc": {"delivery_attempts": 1}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to record delivery for {notification_id}: {e}")
            return False
    
    def cleanup_expired_notifications(self) -> int:
        """Remove expired notifications"""
        try:
            result = self.collection.delete_many({
                "expires_at": {"$lt": datetime.utcnow()}
            })
            
            if result.deleted_count > 0:
                logger.info(f"Cleaned up {result.deleted_count} expired notifications")
            
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired notifications: {e}")
            return 0

    def find_by_reminder_id(self, reminder_id: str) -> Optional[StoredNotification]:
        """Find notification by reminder ID"""
        try:
            doc = self.collection.find_one({
                "metadata.reminder_id": reminder_id
            })
            
            if doc:
                doc["id"] = str(doc["_id"])
                return StoredNotification(**doc)
            return None
            
        except Exception as e:
            logger.error(f"Failed to find notification by reminder ID {reminder_id}: {e}")
            return None