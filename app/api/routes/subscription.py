from fastapi import APIRouter, HTTPException, Depends, Query, Request
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.services.subscription_service import SubscriptionService
from app.models.subscription import PlanType

router = APIRouter()

def get_subscription_service():
    return SubscriptionService()

# Request/Response models
class CreateSubscriptionRequest(BaseModel):
    user_id: str
    plan_type: str
    payment_method: Optional[str] = "manual"

class UpgradeSubscriptionRequest(BaseModel):
    user_id: str
    new_plan_type: str

class TrackUsageRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    tokens_consumed: int
    input_tokens: Optional[int] = 0
    output_tokens: Optional[int] = 0
    request_type: Optional[str] = "chat"
    model_used: Optional[str] = "gpt-3.5-turbo"
    endpoint: Optional[str] = "/chat"

class CheckLimitRequest(BaseModel):
    user_id: str
    estimated_tokens: Optional[int] = 1000

# Subscription Management Endpoints
@router.post("/subscription/create")
async def create_subscription(
    request: CreateSubscriptionRequest,
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """Create new subscription for user"""
    try:
        result = await subscription_service.create_subscription(
            user_id=request.user_id,
            plan_type=request.plan_type,
            payment_method=request.payment_method
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "subscription": result["subscription"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/subscription/{user_id}")
async def get_subscription(
    user_id: str,
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """Get user's current subscription"""
    try:
        result = await subscription_service.get_subscription(user_id)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=404, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/subscription/{user_id}/upgrade")
async def upgrade_subscription(
    user_id: str, 
    request: UpgradeSubscriptionRequest,
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """Upgrade user's subscription plan"""
    try:
        result = await subscription_service.upgrade_subscription(
            user_id=user_id,
            new_plan_type=request.new_plan_type
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/subscription/{user_id}")
async def cancel_subscription(
    user_id: str, 
    reason: Optional[str] = Query(None),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """Cancel user's subscription"""
    try:
        result = await subscription_service.cancel_subscription(user_id, reason or "")
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Usage Tracking Endpoints
@router.post("/usage/check-limit")
async def check_usage_limit(
    request: CheckLimitRequest,
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """Check if user can proceed with request based on limits"""
    try:
        result = await subscription_service.check_can_proceed(
            user_id=request.user_id,
            estimated_tokens=request.estimated_tokens
        )
        
        return {
            "can_proceed": result["can_proceed"],
            "reason": result.get("reason"),
            "subscription": result.get("subscription"),
            "suggested_action": result.get("suggested_action"),
            "estimated_cost": result.get("estimated_cost", 0)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/usage/track")
async def track_usage(
    request: TrackUsageRequest, 
    http_request: Request,
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """Track token usage after successful request"""
    try:
        # Extract client info from request
        client_info = {
            "ip_address": http_request.client.host if http_request.client else None,
            "user_agent": http_request.headers.get("user-agent")
        }
        
        usage_data = {
            "tokens_consumed": request.tokens_consumed,
            "session_id": request.session_id,
            "input_tokens": request.input_tokens,
            "output_tokens": request.output_tokens,
            "request_type": request.request_type,
            "model_used": request.model_used,
            "endpoint": request.endpoint,
            **client_info
        }
        
        result = await subscription_service.track_usage(request.user_id, usage_data)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Usage tracked successfully",
                "usage_summary": result["usage_updated"],
                "cost_vnd": result.get("cost_vnd", 0)
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/usage/{user_id}/stats")
async def get_usage_stats(
    user_id: str, 
    days: Optional[int] = Query(default=30, ge=1, le=365),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """Get usage statistics for user"""
    try:
        result = await subscription_service.get_usage_stats(user_id, days)
        
        if result["success"]:
            return result["stats"]
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Plan Information Endpoints
@router.get("/plans")
async def get_available_plans(
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """Get all available subscription plans"""
    try:
        result = subscription_service.get_available_plans()
        return result["plans"]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Admin Endpoints
# @router.get("/admin/subscriptions") - DEPRECATED: Use /api/v1/admin/subscriptions instead
# This endpoint has been moved to admin.py with proper authentication
# async def get_all_subscriptions(
#     skip: int = Query(default=0, ge=0),
#     limit: int = Query(default=50, ge=1, le=1000)
# ):
#     """Get all subscriptions (admin only)"""
#     try:
#         # TODO: Add admin authentication
#         from app.repositories.subscription import SubscriptionRepository
#         repo = SubscriptionRepository()
#         result = await repo.get_all_subscriptions(skip, limit)
#         
#         if "error" in result:
#             raise HTTPException(status_code=500, detail=result["error"])
#             
#         return result
#         
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/admin/dashboard")
async def get_admin_dashboard(
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """Get admin dashboard data"""
    try:
        # TODO: Add admin authentication
        result = await subscription_service.get_admin_dashboard_data()
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Health check endpoint
@router.get("/subscription/health")
async def health_check():
    """Health check for subscription service"""
    return {
        "status": "healthy",
        "service": "subscription_service",
        "timestamp": "2024-10-07T00:00:00Z"
    }