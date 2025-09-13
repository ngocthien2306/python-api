"""
WebSocket Real-time Notifications
Handles bidirectional real-time communication for task notifications
"""

import json
import asyncio
import logging
from typing import Dict, List, Set
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from app.core.dependencies import get_user_repository, get_task_service

# Setup logging
logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        # Store connections by user_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept WebSocket connection for a user"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        logger.info(f"📡 WebSocket connected for user {user_id}. Total connections: {len(self.active_connections[user_id])}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove WebSocket connection"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        logger.info(f"📡 WebSocket disconnected for user {user_id}")
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send message to all connections of a specific user"""
        if user_id not in self.active_connections:
            logger.warning(f"📡 No active connections for user {user_id}")
            return False
        
        # Send to all connections of this user (multiple tabs/devices)
        disconnected_connections = set()
        
        for websocket in self.active_connections[user_id]:
            try:
                # Ensure all datetime objects are converted to ISO format strings
                serializable_message = self._make_json_serializable(message)
                await websocket.send_text(json.dumps(serializable_message))
                logger.info(f"📡 Sent message to user {user_id}: {serializable_message}")
            except Exception as e:
                logger.error(f"📡 Failed to send to websocket: {e}")
                disconnected_connections.add(websocket)
        
        # Clean up disconnected connections
        for websocket in disconnected_connections:
            self.disconnect(websocket, user_id)
        
        return len(self.active_connections.get(user_id, [])) > 0
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast message to all connected users"""
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(user_id, message)
    
    def get_user_connection_count(self, user_id: str) -> int:
        """Get number of active connections for a user"""
        return len(self.active_connections.get(user_id, []))
    
    def get_total_connections(self) -> int:
        """Get total number of active connections"""
        return sum(len(connections) for connections in self.active_connections.values())
    
    def _make_json_serializable(self, obj):
        """Convert datetime objects and other non-serializable objects to JSON-serializable format"""
        if isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj

# Global connection manager instance
connection_manager = ConnectionManager()

@router.websocket("/ws/notifications/{user_id}")
async def websocket_notifications_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time notifications"""
    
    # TODO: Add authentication here if needed
    # For now, we trust the user_id parameter
    
    await connection_manager.connect(websocket, user_id)
    
    try:
        # Send welcome message
        welcome_message = {
            "type": "connection_established",
            "message": f"Connected to notifications for user {user_id}",
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id
        }
        await websocket.send_text(json.dumps(welcome_message))
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                await handle_client_message(websocket, user_id, message)
                
            except asyncio.TimeoutError:
                # Send heartbeat
                heartbeat = {
                    "type": "heartbeat",
                    "timestamp": datetime.now().isoformat()
                }
                await websocket.send_text(json.dumps(heartbeat))
                
    except WebSocketDisconnect:
        logger.info(f"📡 WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"📡 WebSocket error for user {user_id}: {e}")
    finally:
        connection_manager.disconnect(websocket, user_id)

async def handle_client_message(websocket: WebSocket, user_id: str, message: dict):
    """Handle messages received from client"""
    message_type = message.get("type")
    
    if message_type == "ping":
        # Respond to ping with pong
        pong_message = {
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send_text(json.dumps(pong_message))
        
    elif message_type == "mark_notification_read":
        # Handle notification read status
        notification_id = message.get("notification_id")
        logger.info(f"📡 User {user_id} marked notification {notification_id} as read")
        
        # Send acknowledgment
        ack_message = {
            "type": "notification_read_ack",
            "notification_id": notification_id,
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send_text(json.dumps(ack_message))
        
    elif message_type == "get_pending_tasks":
        # Send pending tasks to user
        await send_pending_tasks_to_user(user_id)
        
    else:
        logger.warning(f"📡 Unknown message type from user {user_id}: {message_type}")

@router.post("/send-notification/{user_id}")
async def send_notification_to_user(user_id: str, notification: dict):
    """API endpoint to send notification to specific user via WebSocket"""
    try:
        # Add metadata to notification
        enhanced_notification = {
            "type": "task_notification",
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            **notification
        }
        
        success = await connection_manager.send_to_user(user_id, enhanced_notification)
        
        if success:
            return {
                "success": True,
                "message": f"Notification sent to user {user_id}",
                "connections": connection_manager.get_user_connection_count(user_id)
            }
        else:
            return {
                "success": False,
                "message": f"No active connections for user {user_id}",
                "connections": 0
            }
            
    except Exception as e:
        logger.error(f"📡 Error sending notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send-task-reminder/{username}")
async def send_task_reminder_websocket(username: str):
    """Send task reminder via WebSocket (replaces curl endpoint)"""
    try:
        from app.core.dependencies import get_user_repository, get_task_service
        user_repo = get_user_repository()
        task_service = get_task_service()
        
        # Get user by username
        user = user_repo.get_user_by_username(username)
        if not user:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        
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
        
        # Create notification payload
        notification = {
            "title": "📋 Task Reminder",
            "body": selected_task['title'],
            "task": {
                "id": selected_task.get('id'),
                "title": selected_task['title'],
                "priority": selected_task.get('priority', 'medium'),
                "status": selected_task.get('status'),
                "due_date": selected_task.get('dueDate'),
                "due_time": selected_task.get('dueTime'),
            },
            "action": {
                "type": "navigate",
                "url": "/calendar"
            },
            "notification_type": "task_reminder"
        }
        
        # Send via WebSocket
        success = await connection_manager.send_to_user(str(user.id), notification)
        
        if success:
            return {
                "success": True,
                "message": f"Task reminder sent to '{username}' successfully! 📬",
                "user": username,
                "task": notification["task"],
                "connections": connection_manager.get_user_connection_count(str(user.id))
            }
        else:
            return {
                "success": False,
                "message": f"Failed to send reminder to '{username}' - no active WebSocket connections",
                "user": username,
                "task": notification["task"],
                "connections": 0
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"📡 Error sending task reminder: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send task reminder: {str(e)}")

async def send_pending_tasks_to_user(user_id: str):
    """Send user's pending tasks via WebSocket"""
    try:
        from app.core.dependencies import get_user_repository, get_task_service
        user_repo = get_user_repository()
        task_service = get_task_service()
        
        # Get user
        user = user_repo.get_user_by_id(user_id)
        if not user:
            return
        
        # Get pending tasks
        task_result = task_service.query_tasks(str(user.username), {
            "status": "pending",
            "limit": 20
        })
        
        if task_result.get("success") and task_result.get("tasks"):
            tasks_message = {
                "type": "pending_tasks",
                "tasks": task_result["tasks"],
                "count": len(task_result["tasks"]),
                "timestamp": datetime.now().isoformat()
            }
            
            await connection_manager.send_to_user(user_id, tasks_message)
            
    except Exception as e:
        logger.error(f"📡 Error sending pending tasks: {e}")

@router.get("/ws/status")
async def websocket_status():
    """Get WebSocket connection status"""
    return {
        "total_connections": connection_manager.get_total_connections(),
        "connected_users": list(connection_manager.active_connections.keys()),
        "connections_per_user": {
            user_id: len(connections) 
            for user_id, connections in connection_manager.active_connections.items()
        }
    }