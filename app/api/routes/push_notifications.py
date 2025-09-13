from fastapi import APIRouter, Depends, HTTPException, status

from datetime import datetime
from app.api.routes.auth import get_current_user
from app.repositories.user import UserRepository
from app.api.routes.auth import get_user_repository
from app.services.notifications.web_push_service import web_push_manager
from app.models.notification import SubscribeRequest, PushSubscription, UnsubscribeRequest, TestNotificationRequest
router = APIRouter()

@router.get("/public-key")
async def get_public_key():
    """Get VAPID public key for client subscription"""
    try:
        public_key = web_push_manager.get_public_key()
        return {
            "success": True,
            "public_key": public_key
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get public key: {str(e)}"
        )

@router.post("/subscribe")
async def subscribe_to_push(
    request: SubscribeRequest,
    current_user=Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Subscribe user to push notifications"""
    try:
        # Convert subscription to dict
        subscription_data = {
            "endpoint": request.subscription.endpoint,
            "keys": request.subscription.keys
        }
        
        # Add device info
        subscription_data["device_info"] = request.device_info
        subscription_data["created_at"] = datetime.now().isoformat()
        
        # Add subscription to database
        success = user_repo.add_push_subscription(
            str(current_user.id),
            subscription_data
        )
        
        # Also register with web push manager
        if success:
            await web_push_manager.subscribe_user(
                str(current_user.id), 
                subscription_data
            )
        
        if success:
            return {
                "success": True,
                "message": "Successfully subscribed to push notifications"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to subscribe to push notifications"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Subscription failed: {str(e)}"
        )

@router.post("/unsubscribe")
async def unsubscribe_from_push(
    request: UnsubscribeRequest,
    current_user=Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Unsubscribe user from push notifications"""
    try:
        # Remove from database
        success = user_repo.remove_push_subscription(
            str(current_user.id),
            request.endpoint
        )
        
        # Also remove from web push manager
        if success:
            await web_push_manager.unsubscribe_user(
                str(current_user.id),
                request.endpoint
            )
        
        if success:
            return {
                "success": True,
                "message": "Successfully unsubscribed from push notifications"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to unsubscribe from push notifications"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unsubscription failed: {str(e)}"
        )

@router.post("/test")
async def send_test_notification(
    request: TestNotificationRequest = TestNotificationRequest(),
    current_user=Depends(get_current_user)
):
    """Send test push notification to user"""
    try:
        # Prepare notification payload
        payload = {
            "title": request.title,
            "body": request.body,
            "icon": request.icon,
            "badge": request.badge,
            "data": {
                **request.data,
                "action_url": "/calendar",
                "notification_type": "test"
            },
            "actions": [
                {
                    "action": "view",
                    "title": "View"
                },
                {
                    "action": "dismiss", 
                    "title": "Dismiss"
                }
            ]
        }
        
        # Send notification
        success = await web_push_manager.send_to_user(
            str(current_user.id),
            payload
        )
        
        if success:
            return {
                "success": True,
                "message": "Test notification sent successfully"
            }
        else:
            return {
                "success": False,
                "error": "No active subscriptions found or notification failed"
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test notification: {str(e)}"
        )

@router.post("/test-no-auth")
async def send_test_notification_no_auth(
    request: TestNotificationRequest = TestNotificationRequest()
):
    """Send test push notification (no auth required for testing)"""
    try:
        # For testing, just return success without sending actual notification
        return {
            "success": True,
            "message": "Test notification endpoint working (no auth required)"
        }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test notification: {str(e)}"
        )

@router.get("/subscriptions")
async def get_user_subscriptions(
    current_user=Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Get user's push notification subscriptions"""
    try:
        # Get user subscriptions from repository
        subscriptions = user_repo.get_user_push_subscriptions(str(current_user.id))
        
        # Return sanitized subscription info (without auth keys)
        sanitized_subscriptions = []
        for sub in subscriptions:
            sanitized_subscriptions.append({
                "endpoint": sub.get("endpoint"),
                "created_at": sub.get("created_at"),
                "device_info": sub.get("device_info", {})
            })
        
        return {
            "success": True,
            "subscriptions": sanitized_subscriptions,
            "count": len(sanitized_subscriptions)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get subscriptions: {str(e)}"
        )

@router.post("/clear-subscriptions")
async def clear_all_subscriptions(
    current_user=Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Clear all push subscriptions for user (for debugging VAPID key mismatch)"""
    try:
        # Clear all subscriptions from database
        from bson import ObjectId
        result = user_repo.collection.update_one(
            {"_id": ObjectId(str(current_user.id))},
            {"$set": {"push_subscriptions": []}}
        )
        
        return {
            "success": True,
            "message": f"Cleared all push subscriptions for user",
            "cleared": result.modified_count > 0
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear subscriptions: {str(e)}"
        )

@router.post("/remind-user-task/{username}")
async def remind_user_task(username: str):
    """Send task reminder for a user (no auth required for CLI usage)"""
    try:
        from app.core.dependencies import get_user_repository
        user_repo = get_user_repository()
        
        # Get user by username
        user = user_repo.get_user_by_username(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )
        
        # Get user's tasks from task service
        from app.core.dependencies import get_task_service
        task_service = get_task_service()
        
        # Get pending tasks
        task_result = task_service.query_tasks(str(user.username), {
            "status": "pending",
            "limit": 10
        })
        
        if not task_result.get("success") or not task_result.get("tasks"):
            return {
                "success": False,
                "message": f"No pending tasks found for user '{username}'"
            }
        
        # Randomly select a task
        import random
        tasks = task_result["tasks"]
        selected_task = random.choice(tasks)
        
        # Create small notification payload for corner notification
        payload = {
            "title": "📋 Task Reminder",
            "body": f"{selected_task['title']}",
            "icon": "/icon-192x192.png",
            "badge": "/badge-72x72.png",
            "data": {
                "task_id": selected_task.get('id'),
                "task_title": selected_task['title'],
                "task_priority": selected_task.get('priority', 'medium'),
                "action_url": "/calendar",
                "notification_type": "task_reminder",
                "timestamp": datetime.now().isoformat()
            },
            "actions": [
                {
                    "action": "view",
                    "title": "View"
                }
            ],
            "silent": True,  # Quiet notification
            "tag": f"task-reminder-{selected_task.get('id', 'unknown')}"
        }
        
        # Send push notification
        success = await web_push_manager.send_to_user(
            str(user.id),
            payload
        )
        
        if success:
            return {
                "success": True,
                "message": f"Task reminder sent to '{username}' successfully! 📬",
                "user": username,
                "task": {
                    "id": selected_task.get('id'),
                    "title": selected_task['title'],
                    "priority": selected_task.get('priority'),
                    "status": selected_task.get('status')
                }
            }
        else:
            return {
                "success": False,
                "message": f"Failed to send reminder to '{username}' - no active subscriptions",
                "user": username,
                "task": selected_task
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send task reminder: {str(e)}"
        )
