from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from app.repositories.subscription import SubscriptionRepository
from app.models.subscription import (
    Subscription, UsageLog, PlanType, SubscriptionStatus, PaymentStatus,
    SUBSCRIPTION_PLANS
)

logger = logging.getLogger(__name__)

class SubscriptionService:
    def __init__(self):
        self.subscription_repo = SubscriptionRepository()
    
    async def create_subscription(self, user_id: str, plan_type: str, payment_method: str = "manual") -> Dict[str, Any]:
        """Create new subscription for user"""
        try:
            # Validate plan type
            if plan_type not in [plan.value for plan in PlanType]:
                return {
                    "success": False,
                    "error": f"Invalid plan type: {plan_type}",
                    "available_plans": [plan.value for plan in PlanType]
                }
            
            # Check if user already has active subscription
            existing_subscription = await self.subscription_repo.get_user_subscription(user_id)
            if existing_subscription and existing_subscription.get("status") == "active":
                return {
                    "success": False,
                    "error": "User already has active subscription",
                    "current_subscription": existing_subscription
                }
            
            # Get plan details
            plan = SUBSCRIPTION_PLANS[PlanType(plan_type)]
            
            # Create subscription data
            subscription_data = {
                "user_id": user_id,
                "plan_type": plan_type,
                "tokens_used": 0,
                "tokens_limit": plan.tokens_limit,
                "requests_used": 0,
                "requests_limit": plan.requests_limit,
                "status": SubscriptionStatus.ACTIVE.value,
                "start_date": datetime.utcnow(),
                "price": plan.price,
                "payment_status": PaymentStatus.PAID.value if plan.price == 0 else PaymentStatus.PENDING.value
            }
            
            # Set cost per 1k tokens for pay-as-you-go
            if plan_type == PlanType.PAY_AS_YOU_GO.value:
                subscription_data["cost_per_1k_tokens"] = 1000.0  # 1000 VND per 1k tokens
                subscription_data["total_cost"] = 0.0
            
            subscription_id = await self.subscription_repo.create_subscription(subscription_data)
            
            if subscription_id:
                created_subscription = await self.subscription_repo.get_user_subscription(user_id)
                return {
                    "success": True,
                    "subscription_id": subscription_id,
                    "subscription": created_subscription,
                    "message": f"Created {plan.name} subscription successfully"
                }
            
            return {"success": False, "error": "Failed to create subscription"}
            
        except Exception as e:
            logger.error(f"Error creating subscription: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_subscription(self, user_id: str) -> Dict[str, Any]:
        """Get user's current subscription"""
        try:
            subscription = await self.subscription_repo.get_user_subscription(user_id)
            
            if not subscription:
                # Auto-create free subscription for new users
                result = await self.create_subscription(user_id, PlanType.FREE.value)
                if result["success"]:
                    subscription = result["subscription"]
                else:
                    return {"success": False, "error": "No subscription found and failed to create free plan"}
            
            # Calculate remaining quotas
            tokens_remaining = max(0, subscription.get("tokens_limit", 0) - subscription.get("tokens_used", 0))
            requests_remaining = max(0, subscription.get("requests_limit", 0) - subscription.get("requests_used", 0))
            
            # Check if expired
            is_expired = False
            if subscription.get("end_date"):
                is_expired = datetime.utcnow() > subscription["end_date"]
            
            return {
                "success": True,
                "subscription": subscription,
                "quotas": {
                    "tokens_used": subscription.get("tokens_used", 0),
                    "tokens_limit": subscription.get("tokens_limit", 0),
                    "tokens_remaining": tokens_remaining,
                    "requests_used": subscription.get("requests_used", 0), 
                    "requests_limit": subscription.get("requests_limit", 0),
                    "requests_remaining": requests_remaining
                },
                "status": {
                    "is_active": subscription.get("status") == "active" and not is_expired,
                    "is_expired": is_expired,
                    "payment_status": subscription.get("payment_status", "pending")
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting subscription: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def check_can_proceed(self, user_id: str, estimated_tokens: int = 1000) -> Dict[str, Any]:
        """Check if user can make a request based on their subscription limits"""
        try:
            check_result = await self.subscription_repo.check_usage_limits(user_id)
            
            if not check_result["can_proceed"]:
                return {
                    "can_proceed": False,
                    "reason": check_result["reason"],
                    "subscription": check_result["subscription"],
                    "suggested_action": self._get_suggested_action(check_result["reason"])
                }
            
            subscription = check_result["subscription"]
            
            # Additional check for estimated tokens
            if subscription["plan_type"] != "pay_as_you_go":
                tokens_remaining = subscription.get("tokens_limit", 0) - subscription.get("tokens_used", 0)
                if estimated_tokens > tokens_remaining:
                    return {
                        "can_proceed": False,
                        "reason": f"Estimated tokens ({estimated_tokens}) exceeds remaining quota ({tokens_remaining})",
                        "subscription": subscription,
                        "suggested_action": "upgrade_plan"
                    }
            
            return {
                "can_proceed": True,
                "subscription": subscription,
                "estimated_cost": self._calculate_estimated_cost(subscription, estimated_tokens)
            }
            
        except Exception as e:
            logger.error(f"Error checking can proceed: {str(e)}")
            return {"can_proceed": False, "reason": f"System error: {str(e)}"}
    
    async def track_usage(self, user_id: str, usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track token usage and update subscription"""
        try:
            tokens_consumed = usage_data.get("tokens_consumed", 0)
            session_id = usage_data.get("session_id")
            request_type = usage_data.get("request_type", "chat")
            model_used = usage_data.get("model_used", "gpt-3.5-turbo")
            
            # Update subscription usage
            usage_result = await self.subscription_repo.increment_usage(user_id, tokens_consumed)
            
            if not usage_result["success"]:
                return usage_result
            
            # Log detailed usage
            detailed_usage = {
                "user_id": user_id,
                "session_id": session_id,
                "tokens_consumed": tokens_consumed,
                "input_tokens": usage_data.get("input_tokens", 0),
                "output_tokens": usage_data.get("output_tokens", 0),
                "request_type": request_type,
                "model_used": model_used,
                "endpoint": usage_data.get("endpoint", "/chat"),
                "cost_vnd": self._calculate_usage_cost(user_id, tokens_consumed),
                "ip_address": usage_data.get("ip_address"),
                "user_agent": usage_data.get("user_agent")
            }
            
            usage_log_id = await self.subscription_repo.log_usage(detailed_usage)
            
            return {
                "success": True,
                "usage_updated": usage_result,
                "usage_log_id": usage_log_id,
                "cost_vnd": detailed_usage["cost_vnd"]
            }
            
        except Exception as e:
            logger.error(f"Error tracking usage: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def upgrade_subscription(self, user_id: str, new_plan_type: str) -> Dict[str, Any]:
        """Upgrade user's subscription plan"""
        try:
            # Validate new plan
            if new_plan_type not in [plan.value for plan in PlanType]:
                return {"success": False, "error": f"Invalid plan type: {new_plan_type}"}
            
            result = await self.subscription_repo.upgrade_subscription(user_id, new_plan_type)
            
            if result["success"]:
                new_plan = SUBSCRIPTION_PLANS[PlanType(new_plan_type)]
                result["plan_details"] = {
                    "name": new_plan.name,
                    "description": new_plan.description,
                    "features": new_plan.features,
                    "price": new_plan.price
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error upgrading subscription: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_usage_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get detailed usage statistics"""
        try:
            stats = await self.subscription_repo.get_usage_stats(user_id, days)
            
            if "error" in stats:
                return {"success": False, "error": stats["error"]}
            
            return {"success": True, "stats": stats}
            
        except Exception as e:
            logger.error(f"Error getting usage stats: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def cancel_subscription(self, user_id: str, reason: str = "") -> Dict[str, Any]:
        """Cancel user's subscription"""
        try:
            subscription = await self.subscription_repo.get_user_subscription(user_id)
            if not subscription:
                return {"success": False, "error": "No subscription found"}
            
            # Update status to cancelled
            success = await self.subscription_repo.update_subscription_status(
                subscription["_id"], 
                SubscriptionStatus.CANCELLED
            )
            
            if success:
                return {
                    "success": True,
                    "message": "Subscription cancelled successfully",
                    "cancelled_at": datetime.utcnow().isoformat(),
                    "reason": reason
                }
            
            return {"success": False, "error": "Failed to cancel subscription"}
            
        except Exception as e:
            logger.error(f"Error cancelling subscription: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_available_plans(self) -> Dict[str, Any]:
        """Get all available subscription plans"""
        plans = []
        for plan_type, plan in SUBSCRIPTION_PLANS.items():
            plan_info = {
                "plan_type": plan_type.value,
                "name": plan.name,
                "description": plan.description,
                "tokens_limit": plan.tokens_limit,
                "requests_limit": plan.requests_limit,
                "price": plan.price,
                "duration_days": plan.duration_days,
                "features": plan.features,
                "recommended": plan_type == PlanType.MONTH  # Mark monthly as recommended
            }
            
            # Add cost per token for pay-as-you-go
            if plan_type == PlanType.PAY_AS_YOU_GO:
                plan_info["cost_per_1k_tokens"] = 1000
            
            plans.append(plan_info)
        
        return {"success": True, "plans": plans}
    
    def _get_suggested_action(self, reason: str) -> str:
        """Get suggested action based on limit reason"""
        if "token limit" in reason.lower():
            return "upgrade_plan"
        elif "request limit" in reason.lower():
            return "upgrade_plan"
        elif "expired" in reason.lower():
            return "renew_subscription"
        elif "cancelled" in reason.lower():
            return "reactivate_subscription"
        else:
            return "contact_support"
    
    def _calculate_estimated_cost(self, subscription: Dict[str, Any], estimated_tokens: int) -> float:
        """Calculate estimated cost for usage"""
        if subscription["plan_type"] == "pay_as_you_go":
            return (estimated_tokens / 1000) * 1000.0  # 1000 VND per 1k tokens
        return 0.0  # Fixed price plans
    
    def _calculate_usage_cost(self, user_id: str, tokens_consumed: int) -> float:
        """Calculate cost for actual usage"""
        # For now, simple calculation - in reality you'd get subscription details
        return (tokens_consumed / 1000) * 1000.0  # 1000 VND per 1k tokens
    
    async def get_admin_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data for admin"""
        try:
            # This would be expanded for admin dashboard
            all_subs = await self.subscription_repo.get_all_subscriptions(limit=1000)
            
            if "error" in all_subs:
                return {"success": False, "error": all_subs["error"]}
            
            # Calculate some basic stats
            subscriptions = all_subs["subscriptions"]
            stats = {
                "total_subscriptions": len(subscriptions),
                "active_subscriptions": len([s for s in subscriptions if s.get("status") == "active"]),
                "plan_distribution": {},
                "total_revenue": 0
            }
            
            for sub in subscriptions:
                plan_type = sub.get("plan_type", "unknown")
                stats["plan_distribution"][plan_type] = stats["plan_distribution"].get(plan_type, 0) + 1
                if sub.get("payment_status") == "paid":
                    stats["total_revenue"] += sub.get("price", 0)
            
            return {
                "success": True,
                "stats": stats,
                "recent_subscriptions": subscriptions[:10]  # Last 10 subscriptions
            }
            
        except Exception as e:
            logger.error(f"Error getting admin dashboard data: {str(e)}")
            return {"success": False, "error": str(e)}