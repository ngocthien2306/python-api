from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class PaymentGateway(ABC):
    """Base class for payment gateway integrations"""

    @abstractmethod
    async def create_checkout_session(
        self,
        amount: float,
        currency: str,
        user_id: str,
        plan_type: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a checkout session
        Returns: {
            'session_id': str,
            'checkout_url': str,
            'payment_id': str
        }
        """
        pass

    @abstractmethod
    async def create_payment_intent(
        self,
        amount: float,
        currency: str,
        user_id: str,
        plan_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a payment intent
        Returns: {
            'payment_intent_id': str,
            'client_secret': str,
            'amount': float,
            'currency': str
        }
        """
        pass

    @abstractmethod
    async def verify_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """
        Verify and parse webhook data
        Returns parsed event data
        """
        pass

    @abstractmethod
    async def get_payment_status(self, payment_id: str) -> str:
        """
        Get payment status from gateway
        Returns: 'pending' | 'completed' | 'failed' | 'cancelled'
        """
        pass

    @abstractmethod
    async def refund_payment(self, payment_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        """
        Refund a payment
        Returns refund details
        """
        pass
