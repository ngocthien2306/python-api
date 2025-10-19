import stripe
from typing import Optional, Dict, Any
from .base import PaymentGateway
from app.models.payment import PaymentStatus
import logging

logger = logging.getLogger(__name__)

class StripeGateway(PaymentGateway):
    """Stripe payment gateway implementation"""

    def __init__(self, secret_key: str, publishable_key: str, webhook_secret: str):
        stripe.api_key = secret_key
        self.publishable_key = publishable_key
        self.webhook_secret = webhook_secret

    def create_checkout_session(
        self,
        amount: float,
        currency: str,
        user_id: str,
        plan_type: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create Stripe Checkout Session"""
        try:
            # Convert VND to smallest unit (already in đồng)
            # For USD/EUR, multiply by 100 (cents)
            if currency.upper() in ['USD', 'EUR', 'GBP']:
                unit_amount = int(amount * 100)
            else:
                unit_amount = int(amount)

            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': currency.lower(),
                        'unit_amount': unit_amount,
                        'product_data': {
                            'name': f'Subscription - {plan_type}',
                            'description': f'Subscription plan: {plan_type}',
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=cancel_url,
                metadata={
                    'user_id': user_id,
                    'plan_type': plan_type,
                    **(metadata or {})
                }
            )

            return {
                'session_id': session.id,
                'checkout_url': session.url,
                'payment_id': session.payment_intent if session.payment_intent else session.id
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe checkout error: {str(e)}")
            raise Exception(f"Failed to create checkout session: {str(e)}")

    def create_payment_intent(
        self,
        amount: float,
        currency: str,
        user_id: str,
        plan_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create Stripe Payment Intent"""
        try:
            # Convert to smallest currency unit
            if currency.upper() in ['USD', 'EUR', 'GBP']:
                unit_amount = int(amount * 100)
            else:
                unit_amount = int(amount)

            intent = stripe.PaymentIntent.create(
                amount=unit_amount,
                currency=currency.lower(),
                metadata={
                    'user_id': user_id,
                    'plan_type': plan_type,
                    **(metadata or {})
                }
            )

            return {
                'payment_intent_id': intent.id,
                'client_secret': intent.client_secret,
                'amount': amount,
                'currency': currency
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment intent error: {str(e)}")
            raise Exception(f"Failed to create payment intent: {str(e)}")

    def verify_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """Verify Stripe webhook signature and parse event"""
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            return event

        except ValueError as e:
            logger.error(f"Invalid webhook payload: {str(e)}")
            raise Exception("Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {str(e)}")
            raise Exception("Invalid signature")

    def get_payment_status(self, payment_id: str) -> str:
        """Get payment status from Stripe"""
        try:
            # Try as payment intent first
            try:
                intent = stripe.PaymentIntent.retrieve(payment_id)
                status_map = {
                    'succeeded': 'completed',
                    'processing': 'pending',
                    'requires_payment_method': 'pending',
                    'requires_confirmation': 'pending',
                    'requires_action': 'pending',
                    'canceled': 'cancelled',
                    'requires_capture': 'pending'
                }
                return status_map.get(intent.status, 'pending')

            except stripe.error.InvalidRequestError:
                # Try as checkout session
                session = stripe.checkout.Session.retrieve(payment_id)
                if session.payment_status == 'paid':
                    return 'completed'
                elif session.payment_status == 'unpaid':
                    return 'pending'
                else:
                    return 'failed'

        except stripe.error.StripeError as e:
            logger.error(f"Error getting payment status: {str(e)}")
            raise Exception(f"Failed to get payment status: {str(e)}")

    def refund_payment(self, payment_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        """Refund a Stripe payment"""
        try:
            refund_params = {'payment_intent': payment_id}

            if amount:
                # Convert to smallest unit
                refund_params['amount'] = int(amount * 100)

            refund = stripe.Refund.create(**refund_params)

            return {
                'refund_id': refund.id,
                'status': refund.status,
                'amount': refund.amount / 100 if refund.currency in ['usd', 'eur', 'gbp'] else refund.amount
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe refund error: {str(e)}")
            raise Exception(f"Failed to refund payment: {str(e)}")

    def retrieve_checkout_session(self, session_id: str) -> Dict[str, Any]:
        """Retrieve checkout session details"""
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            return {
                'id': session.id,
                'payment_status': session.payment_status,
                'payment_intent': session.payment_intent,
                'amount_total': session.amount_total,
                'currency': session.currency,
                'metadata': session.metadata
            }
        except stripe.error.StripeError as e:
            logger.error(f"Error retrieving session: {str(e)}")
            raise Exception(f"Failed to retrieve session: {str(e)}")
