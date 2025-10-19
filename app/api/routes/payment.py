import traceback
from fastapi import APIRouter, HTTPException, Depends, Request, Header
from typing import Optional
from pydantic import BaseModel

from app.services.payment_service import PaymentService
from app.models.payment import PaymentGateway
from app.core.database import get_database

router = APIRouter()

def get_payment_service():
    db = get_database()
    return PaymentService(db)

# Request models
class CreateCheckoutRequest(BaseModel):
    user_id: str
    plan_type: str
    gateway: PaymentGateway = PaymentGateway.STRIPE
    success_url: str
    cancel_url: str

class VerifyPaymentRequest(BaseModel):
    payment_id: str
    gateway: PaymentGateway

# Config endpoint (must be before {payment_id} route)
@router.get("/payment/config")
def get_payment_config(
    payment_service: PaymentService = Depends(get_payment_service)
):
    """Get payment configuration (publishable keys, etc.)"""
    try:
        return {
            "stripe": {
                "publishable_key": payment_service.stripe.publishable_key
            },
            "supported_gateways": [g.value for g in PaymentGateway]
        }
    except:
        traceback.print_exc()
        raise

# Success/Cancel callbacks (MUST be before {payment_id} route)
@router.get("/payment/success")
def payment_success(
    session_id: str,
    payment_service: PaymentService = Depends(get_payment_service)
):
    """Handle successful payment callback"""
    try:
        # Find payment by checkout_session_id
        payment = payment_service.payments_collection.find_one({'checkout_session_id': session_id})

        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        return {
            "success": True,
            "message": "Payment successful",
            "session_id": session_id,
            "payment_id": str(payment['_id']),
            "payment_status": payment.get('status', 'pending')
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process success: {str(e)}")

@router.get("/payment/cancel")
def payment_cancel(session_id: Optional[str] = None):
    """Handle cancelled payment callback"""
    return {
        "success": False,
        "message": "Payment cancelled",
        "session_id": session_id
    }

# Payment endpoints
@router.post("/payment/checkout")
def create_checkout(
    request: CreateCheckoutRequest,
    payment_service: PaymentService = Depends(get_payment_service)
):
    """Create checkout session for payment"""
    try:
        session = payment_service.create_checkout_session(
            user_id=request.user_id,
            plan_type=request.plan_type,
            gateway=request.gateway,
            success_url=request.success_url,
            cancel_url=request.cancel_url
        )

        return {
            "success": True,
            "session_id": session.session_id,
            "checkout_url": session.checkout_url,
            "payment_id": session.payment_id
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create checkout: {str(e)}")

@router.get("/payment/{payment_id}")
def get_payment(
    payment_id: str,
    payment_service: PaymentService = Depends(get_payment_service)
):
    """Get payment details"""
    try:
        payment = payment_service.get_payment(payment_id)

        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        return {
            "success": True,
            "payment": payment.dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get payment: {str(e)}")

@router.get("/payment/user/{user_id}")
def get_user_payments(
    user_id: str,
    limit: int = 10,
    payment_service: PaymentService = Depends(get_payment_service)
):
    """Get user's payment history"""
    try:
        payments = payment_service.get_user_payments(user_id, limit)

        return {
            "success": True,
            "payments": [p.dict() for p in payments],
            "count": len(payments)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get payments: {str(e)}")

@router.post("/payment/verify")
async def verify_payment(
    request: VerifyPaymentRequest,
    payment_service: PaymentService = Depends(get_payment_service)
):
    """Verify payment status with gateway"""
    try:
        payment = await payment_service.verify_payment(
            payment_id=request.payment_id,
            gateway=request.gateway
        )

        return {
            "success": True,
            "payment": payment.dict(),
            "status": payment.status
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to verify payment: {str(e)}")

# Webhook endpoints
@router.post("/payment/webhook/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
    payment_service: PaymentService = Depends(get_payment_service)
):
    """Handle Stripe webhook"""
    try:
        if not stripe_signature:
            raise HTTPException(status_code=400, detail="Missing stripe-signature header")

        payload = await request.body()

        result = payment_service.handle_webhook(
            gateway=PaymentGateway.STRIPE,
            payload=payload,
            signature=stripe_signature
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook error: {str(e)}")
