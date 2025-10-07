from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pymongo.collection import Collection
from pymongo import DESCENDING, ASCENDING
from bson import ObjectId
import logging

from app.core.database import get_database
from app.models.subscription import Subscription, UsageLog, PlanType, SubscriptionStatus, SUBSCRIPTION_PLANS
from app.repositories.base import BaseRepository

class SubscriptionRepository(BaseRepository):
    def __init__(self):
        from app.core.database import get_database
        self.db = get_database()
        super().__init__(self.db)
        self.collection: Collection = self.db.subscriptions
        self.usage_collection: Collection = self.db.usage_logs
        self.logger = logging.getLogger(__name__)
        
    def get_collection_name(self) -> str:
        return "subscriptions"
        
    async def create_subscription(self, subscription_data: Dict[str, Any]) -> Optional[str]:
        """Create new subscription"""
        try:
            subscription_data["created_at"] = datetime.utcnow()
            subscription_data["updated_at"] = datetime.utcnow()
            
            # Set default limits based on plan type
            plan_type = subscription_data.get("plan_type")
            if plan_type and plan_type in SUBSCRIPTION_PLANS:
                plan = SUBSCRIPTION_PLANS[PlanType(plan_type)]
                subscription_data["tokens_limit"] = plan.tokens_limit
                subscription_data["requests_limit"] = plan.requests_limit
                subscription_data["price"] = plan.price
                
                # Calculate end_date if not provided
                if "end_date" not in subscription_data:
                    start_date = subscription_data.get("start_date", datetime.utcnow())
                    if isinstance(start_date, str):
                        start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    subscription_data["end_date"] = start_date + timedelta(days=plan.duration_days)
            
            result = self.collection.insert_one(subscription_data)
            return str(result.inserted_id)
        except Exception as e:
            self.logger.error(f"Error creating subscription: {str(e)}")
            return None
    
    async def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get active subscription for user"""
        try:
            # Find the most recent active subscription
            subscription = self.collection.find_one(
                {
                    "user_id": user_id,
                    "status": {"$in": ["active", "expired"]}
                },
                sort=[("created_at", DESCENDING)]
            )
            
            if subscription:
                subscription["_id"] = str(subscription["_id"])
                # Check if expired and update status
                if subscription.get("end_date") and datetime.utcnow() > subscription["end_date"]:
                    if subscription["status"] == "active":
                        await self.update_subscription_status(str(subscription["_id"]), SubscriptionStatus.EXPIRED)
                        subscription["status"] = "expired"
                
            return subscription
        except Exception as e:
            self.logger.error(f"Error getting user subscription: {str(e)}")
            return None
    
    async def update_subscription_status(self, subscription_id: str, status: SubscriptionStatus) -> bool:
        """Update subscription status"""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(subscription_id)},
                {
                    "$set": {
                        "status": status.value,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            self.logger.error(f"Error updating subscription status: {str(e)}")
            return False
    
    async def increment_usage(self, user_id: str, tokens_consumed: int) -> Dict[str, Any]:
        """Increment token usage for user's active subscription"""
        try:
            subscription = await self.get_user_subscription(user_id)
            if not subscription:
                return {"success": False, "error": "No active subscription found"}
            
            # Update usage
            result = self.collection.update_one(
                {"_id": ObjectId(subscription["_id"])},
                {
                    "$inc": {
                        "tokens_used": tokens_consumed,
                        "requests_used": 1
                    },
                    "$set": {
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                # Get updated subscription
                updated_subscription = await self.get_user_subscription(user_id)
                return {
                    "success": True,
                    "tokens_used": updated_subscription.get("tokens_used", 0),
                    "tokens_remaining": max(0, updated_subscription.get("tokens_limit", 0) - updated_subscription.get("tokens_used", 0)),
                    "requests_used": updated_subscription.get("requests_used", 0),
                    "requests_remaining": max(0, updated_subscription.get("requests_limit", 0) - updated_subscription.get("requests_used", 0))
                }
            
            return {"success": False, "error": "Failed to update usage"}
        except Exception as e:
            self.logger.error(f"Error incrementing usage: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def check_usage_limits(self, user_id: str) -> Dict[str, Any]:
        """Check if user can make more requests"""
        try:
            subscription = await self.get_user_subscription(user_id)
            if not subscription:
                # Create free subscription for new users
                free_subscription_data = {
                    "user_id": user_id,
                    "plan_type": "free",
                    "status": "active",
                    "payment_status": "paid"  # Free is always paid
                }
                subscription_id = await self.create_subscription(free_subscription_data)
                subscription = await self.get_user_subscription(user_id)
            
            if not subscription:
                return {
                    "can_proceed": False,
                    "reason": "Cannot create subscription",
                    "subscription": None
                }
            
            # Check if subscription is active
            if subscription["status"] != "active":
                return {
                    "can_proceed": False,
                    "reason": f"Subscription is {subscription['status']}",
                    "subscription": subscription
                }
            
            # Check token limits (skip for pay-as-you-go)
            if subscription["plan_type"] != "pay_as_you_go":
                if subscription.get("tokens_used", 0) >= subscription.get("tokens_limit", 0):
                    return {
                        "can_proceed": False,
                        "reason": "Token limit exceeded",
                        "subscription": subscription
                    }
                
                if subscription.get("requests_used", 0) >= subscription.get("requests_limit", 0):
                    return {
                        "can_proceed": False,
                        "reason": "Request limit exceeded", 
                        "subscription": subscription
                    }
            
            return {
                "can_proceed": True,
                "reason": "Within limits",
                "subscription": subscription
            }
        except Exception as e:
            self.logger.error(f"Error checking usage limits: {str(e)}")
            return {
                "can_proceed": False,
                "reason": f"Error checking limits: {str(e)}",
                "subscription": None
            }
    
    async def upgrade_subscription(self, user_id: str, new_plan_type: str) -> Dict[str, Any]:
        """Upgrade user's subscription plan"""
        try:
            current_subscription = await self.get_user_subscription(user_id)
            if not current_subscription:
                return {"success": False, "error": "No subscription found"}
            
            # Validate new plan type
            if new_plan_type not in SUBSCRIPTION_PLANS:
                return {"success": False, "error": "Invalid plan type"}
            
            new_plan = SUBSCRIPTION_PLANS[PlanType(new_plan_type)]
            
            # Calculate new end date
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=new_plan.duration_days)
            
            # Update subscription
            result = self.collection.update_one(
                {"_id": ObjectId(current_subscription["_id"])},
                {
                    "$set": {
                        "plan_type": new_plan_type,
                        "tokens_limit": new_plan.tokens_limit,
                        "requests_limit": new_plan.requests_limit,
                        "price": new_plan.price,
                        "start_date": start_date,
                        "end_date": end_date,
                        "payment_status": "pending",
                        "updated_at": datetime.utcnow(),
                        # Reset usage for new plan
                        "tokens_used": 0,
                        "requests_used": 0
                    }
                }
            )
            
            if result.modified_count > 0:
                updated_subscription = await self.get_user_subscription(user_id)
                return {
                    "success": True,
                    "subscription": updated_subscription,
                    "message": f"Upgraded to {new_plan.name}"
                }
            
            return {"success": False, "error": "Failed to update subscription"}
        except Exception as e:
            self.logger.error(f"Error upgrading subscription: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def log_usage(self, usage_data: Dict[str, Any]) -> Optional[str]:
        """Log detailed usage information"""
        try:
            usage_data["timestamp"] = datetime.utcnow()
            result = self.usage_collection.insert_one(usage_data)
            return str(result.inserted_id)
        except Exception as e:
            self.logger.error(f"Error logging usage: {str(e)}")
            return None
    
    async def get_usage_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for user"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Aggregate usage logs
            pipeline = [
                {
                    "$match": {
                        "user_id": user_id,
                        "timestamp": {"$gte": start_date}
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "$dateToString": {
                                "format": "%Y-%m-%d",
                                "date": "$timestamp"
                            }
                        },
                        "total_tokens": {"$sum": "$tokens_consumed"},
                        "total_requests": {"$sum": 1},
                        "total_cost": {"$sum": "$cost_vnd"}
                    }
                },
                {"$sort": {"_id": 1}}
            ]
            
            daily_stats = list(self.usage_collection.aggregate(pipeline))
            
            # Get current subscription
            subscription = await self.get_user_subscription(user_id)
            
            # Calculate totals
            total_tokens = sum([day["total_tokens"] for day in daily_stats])
            total_requests = sum([day["total_requests"] for day in daily_stats])
            total_cost = sum([day["total_cost"] for day in daily_stats])
            
            return {
                "user_id": user_id,
                "period_days": days,
                "current_subscription": subscription,
                "daily_stats": daily_stats,
                "totals": {
                    "tokens": total_tokens,
                    "requests": total_requests,
                    "cost_vnd": total_cost
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting usage stats: {str(e)}")
            return {"error": str(e)}
    
    async def reset_monthly_usage(self, user_id: str) -> bool:
        """Reset usage counters for monthly plans"""
        try:
            result = self.collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "tokens_used": 0,
                        "requests_used": 0,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            self.logger.error(f"Error resetting monthly usage: {str(e)}")
            return False
    
    async def get_all_subscriptions(self, skip: int = 0, limit: int = 50) -> Dict[str, Any]:
        """Get all subscriptions (admin endpoint)"""
        try:
            total = self.collection.count_documents({})
            subscriptions = list(
                self.collection.find({})
                .sort("created_at", DESCENDING)
                .skip(skip)
                .limit(limit)
            )
            
            # Convert ObjectIds to strings
            for sub in subscriptions:
                sub["_id"] = str(sub["_id"])
            
            return {
                "subscriptions": subscriptions,
                "total": total,
                "skip": skip,
                "limit": limit
            }
        except Exception as e:
            self.logger.error(f"Error getting all subscriptions: {str(e)}")
            return {"error": str(e)}