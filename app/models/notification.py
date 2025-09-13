from pydantic import BaseModel
from typing import Dict, Optional, List

class PushSubscription(BaseModel):
    endpoint: str
    keys: Dict[str, str]

class SubscribeRequest(BaseModel):
    subscription: PushSubscription
    device_info: Optional[Dict[str, str]] = {}

class UnsubscribeRequest(BaseModel):
    endpoint: str

class TestNotificationRequest(BaseModel):
    title: Optional[str] = "Test Notification"
    body: Optional[str] = "This is a test push notification"
    icon: Optional[str] = "/icon-192x192.png"
    badge: Optional[str] = "/badge-72x72.png"
    data: Optional[Dict] = {}