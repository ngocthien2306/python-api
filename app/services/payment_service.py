import traceback
from typing import Optional, Dict, Any
from app.models.payment import Payment, PaymentGateway as PaymentGatewayEnum, PaymentStatus, CheckoutSession
from app.models.subscription import PlanType, SUBSCRIPTION_PLANS, SubscriptionStatus, PaymentStatus as SubPaymentStatus
from app.services.payment import StripeGateway
from app.core.config import settings
from app.utils.payment_logger import (
    log_receipt_generation,
    log_receipt_email_sent,
    log_receipt_error,
    log_webhook_received,
    log_subscription_created
)
from app.services.email_service import EmailService
from app.services.pdf_service import PDFReceiptService

from datetime import datetime, timedelta, timezone
from bson import ObjectId
import logging
import asyncio

logger = logging.getLogger(__name__)

class PaymentService:
    """Main payment service using factory pattern"""

    def __init__(self, db):
        self.db = db
        self.payments_collection = db["payments"]
        self.subscriptions_collection = db["subscriptions"]

        # Initialize gateways
        self.stripe = StripeGateway(
            secret_key=settings.STRIPE_SECRET_KEY,
            publishable_key=settings.STRIPE_PUBLISHABLE_KEY,
            webhook_secret=settings.STRIPE_WEBHOOK_SECRET
        )


    def _get_gateway(self, gateway: PaymentGatewayEnum):
        """Get gateway instance"""
        if gateway == PaymentGatewayEnum.STRIPE:
            return self.stripe
        # Add more gateways here
        raise ValueError(f"Unsupported gateway: {gateway}")

    def create_checkout_session(
        self,
        user_id: str,
        plan_type: str,
        gateway: PaymentGatewayEnum,
        success_url: str,
        cancel_url: str
    ) -> CheckoutSession:
        """Create checkout session for payment"""

        # Get plan details
        try:
            plan = SUBSCRIPTION_PLANS[PlanType(plan_type)]
        except (KeyError, ValueError):
            raise ValueError(f"Invalid plan type: {plan_type}")

        # Create payment record
        payment = Payment(
            user_id=user_id,
            plan_type=plan_type,
            amount=plan.price,
            currency="VND",
            gateway=gateway,
            status=PaymentStatus.PENDING
        )

        # Insert to DB
        result = self.payments_collection.insert_one(payment.model_dump(by_alias=True, exclude={'id'}))
        payment_id = str(result.inserted_id)

        # Create checkout session with gateway
        gateway_client = self._get_gateway(gateway)

        try:
            session_data = gateway_client.create_checkout_session(
                amount=plan.price,
                currency="VND",
                user_id=user_id,
                plan_type=plan_type,
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'payment_id': payment_id,
                    'plan_name': plan.name
                }
            )

            # Update payment with session info
            self.payments_collection.update_one(
                {'_id': result.inserted_id},
                {
                    '$set': {
                        'checkout_session_id': session_data['session_id'],
                        'transaction_id': session_data['payment_id'],
                        'updated_at': datetime.now(timezone.utc)
                    }
                }
            )

            return CheckoutSession(
                session_id=session_data['session_id'],
                checkout_url=session_data['checkout_url'],
                payment_id=payment_id
            )

        except Exception as e:
            # Mark payment as failed
            self.payments_collection.update_one(
                {'_id': result.inserted_id},
                {
                    '$set': {
                        'status': PaymentStatus.FAILED,
                        'error_message': str(e),
                        'updated_at': datetime.now(timezone.utc)
                    }
                }
            )
            raise

    async def verify_payment(self, payment_id: str, gateway: PaymentGatewayEnum) -> Payment:
        """Verify payment status with gateway"""

        payment = await self.payments_collection.find_one({'_id': payment_id})
        if not payment:
            raise ValueError(f"Payment not found: {payment_id}")

        gateway_client = self._get_gateway(gateway)

        try:
            status = await gateway_client.get_payment_status(payment['transaction_id'])

            # Update payment status
            await self.payments_collection.update_one(
                {'_id': payment_id},
                {
                    '$set': {
                        'status': status,
                        'updated_at': datetime.now(timezone.utc),
                        'completed_at': datetime.now(timezone.utc) if status == 'completed' else None
                    }
                }
            )

            payment['status'] = status
            return Payment(**payment)

        except Exception as e:
            logger.error(f"Error verifying payment: {str(e)}")
            raise

    def handle_webhook(
        self,
        gateway: PaymentGatewayEnum,
        payload: bytes,
        signature: str
    ) -> Dict[str, Any]:
        """Handle webhook from payment gateway"""

        logger.info(f"Received webhook from {gateway}")

        gateway_client = self._get_gateway(gateway)

        # Verify webhook
        logger.info("Verifying webhook signature...")
        event = gateway_client.verify_webhook(payload, signature)
        logger.info(f"Webhook verified: {event.get('type')}")

        if gateway == PaymentGatewayEnum.STRIPE:
            return self._handle_stripe_webhook(event)

        return {'status': 'unhandled'}

    def _handle_stripe_webhook(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Stripe webhook events"""

        event_type = event['type']
        logger.info(f"Processing Stripe webhook: {event_type}")

        if event_type == 'checkout.session.completed':
            session = event['data']['object']
            payment_id = session['metadata'].get('payment_id')

            if payment_id:
                transaction_id = session.get('payment_intent', 'N/A')

                # Log webhook received
                log_webhook_received(event_type, payment_id, 'processing')

                self.payments_collection.update_one(
                    {'_id': ObjectId(payment_id)},
                    {
                        '$set': {
                            'status': PaymentStatus.COMPLETED,
                            'transaction_id': transaction_id,
                            'completed_at': datetime.now(timezone.utc),
                            'updated_at': datetime.now(timezone.utc)
                        }
                    }
                )

                # Activate subscription
                payment = self.payments_collection.find_one({'_id': ObjectId(payment_id)})
                if payment:
                    self._create_subscription_from_payment(payment)
                    # Send receipt email
                    self._send_payment_receipt_email(payment)

                # Log success
                log_webhook_received(event_type, payment_id, 'completed')

                return {'status': 'success', 'payment_id': payment_id}

        elif event_type == 'payment_intent.succeeded':
            # Handle payment intent success
            logger.info(f"Payment intent succeeded: {event['data']['object'].get('id')}")

        elif event_type == 'payment_intent.payment_failed':
            # Handle payment failure
            logger.info(f"Payment intent failed: {event['data']['object'].get('id')}")

        return {'status': 'processed', 'event_type': event_type}

    def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID"""
        payment = self.payments_collection.find_one({'_id': payment_id})
        return Payment(**payment) if payment else None

    def get_user_payments(self, user_id: str, limit: int = 10) -> list[Payment]:
        """Get user's payment history"""
        cursor = self.payments_collection.find({'user_id': user_id}).sort('created_at', -1).limit(limit)
        payments = list(cursor)
        return [Payment(**p) for p in payments]

    def _create_subscription_from_payment(self, payment: dict):
        """Create or update subscription after successful payment"""
        try:
            user_id = payment['user_id']
            plan_type = payment['plan_type']

            # Get plan details
            plan = SUBSCRIPTION_PLANS[PlanType(plan_type)]

            # Calculate end date
            start_date = datetime.now(timezone.utc)
            end_date = start_date + timedelta(days=plan.duration_days)

            # Check if user already has subscription
            existing_sub = self.subscriptions_collection.find_one({'user_id': user_id})

            subscription_data = {
                'user_id': user_id,
                'plan_type': plan_type,
                'tokens_used': 0,
                'tokens_limit': plan.tokens_limit,
                'requests_used': 0,
                'requests_limit': plan.requests_limit,
                'status': SubscriptionStatus.ACTIVE.value,
                'start_date': start_date,
                'end_date': end_date,
                'price': plan.price,
                'payment_status': SubPaymentStatus.PAID.value,
                'updated_at': start_date
            }

            if plan_type == PlanType.PAY_AS_YOU_GO.value:
                subscription_data['cost_per_1k_tokens'] = 1000.0
                subscription_data['total_cost'] = 0.0

            if existing_sub:
                # Update existing subscription
                self.subscriptions_collection.update_one(
                    {'user_id': user_id},
                    {'$set': subscription_data}
                )
                logger.info(f"Updated subscription for user {user_id} to {plan_type}")
                log_subscription_created(
                    str(payment['_id']),
                    user_id,
                    str(existing_sub['_id']),
                    plan_type
                )
            else:
                # Create new subscription
                subscription_data['created_at'] = start_date
                result = self.subscriptions_collection.insert_one(subscription_data)
                logger.info(f"Created subscription {result.inserted_id} for user {user_id}")

                # Link subscription to payment
                self.payments_collection.update_one(
                    {'_id': payment['_id']},
                    {'$set': {'subscription_id': str(result.inserted_id)}}
                )

                # Log subscription creation
                log_subscription_created(
                    str(payment['_id']),
                    user_id,
                    str(result.inserted_id),
                    plan_type
                )

        except Exception as e:
            logger.error(f"Error creating subscription from payment: {str(e)}")
            traceback.print_exc()

    def _send_payment_receipt_email(self, payment: dict):
        """Send payment receipt email with PDF attachment to user"""
        try:
            user_id = payment['user_id']

            # Get user email from database
            user = self.db['users'].find_one({'_id': ObjectId(user_id)})
            if not user or not user.get('email'):
                logger.warning(f"User {user_id} not found or no email")
                return

            user_email = user['email']
            plan = SUBSCRIPTION_PLANS[PlanType(payment['plan_type'])]

            # Generate PDF receipt
            pdf_service = PDFReceiptService()

            pdf_buffer = pdf_service.generate_receipt(
                payment_data=payment,
                user_data=user,
                plan_data=plan.model_dump()
            )
            logger.info("PDF receipt generated successfully")

            # Log PDF generation
            log_receipt_generation(
                str(payment.get('_id')),
                user_id,
                payment.get('transaction_id', 'N/A'),
                'success',
                f"PDF size: {len(pdf_buffer.getvalue())} bytes"
            )

            # Create email content
            subject = "Payment Confirmation - Your Subscription Receipt"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f3f4f6;">
                <table role="presentation" style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 40px 20px;">
                            <table role="presentation" style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                                <!-- Header -->
                                <tr>
                                    <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center;">
                                        <h1 style="margin: 0; color: white; font-size: 28px; font-weight: 700;">✓ Payment Successful!</h1>
                                        <p style="margin: 10px 0 0 0; color: rgba(255, 255, 255, 0.9); font-size: 16px;">Thank you for your subscription</p>
                                    </td>
                                </tr>

                                <!-- Content -->
                                <tr>
                                    <td style="padding: 40px 30px;">
                                        <p style="font-size: 18px; color: #111827; margin: 0 0 10px 0;">Hi <strong>{user.get('username', 'there')}</strong>,</p>

                                        <p style="font-size: 16px; color: #4b5563; line-height: 1.6; margin: 0 0 30px 0;">
                                            Your payment has been successfully processed! Your subscription is now active and ready to use.
                                        </p>

                                        <!-- Receipt Details -->
                                        <div style="background: #f9fafb; border-radius: 12px; padding: 24px; margin-bottom: 30px; border: 1px solid #e5e7eb;">
                                            <h2 style="margin: 0 0 20px 0; color: #667eea; font-size: 20px; font-weight: 600;">
                                                <span style="display: inline-block; margin-right: 8px;">📋</span>Receipt Details
                                            </h2>

                                            <table style="width: 100%; border-collapse: collapse;">
                                                <tr>
                                                    <td style="padding: 12px 0; border-bottom: 1px solid #e5e7eb; color: #6b7280; font-size: 14px;">Transaction ID</td>
                                                    <td style="padding: 12px 0; border-bottom: 1px solid #e5e7eb; text-align: right; color: #111827; font-weight: 500; font-size: 14px;">{payment.get('transaction_id', 'N/A')}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 12px 0; border-bottom: 1px solid #e5e7eb; color: #6b7280; font-size: 14px;">Subscription Plan</td>
                                                    <td style="padding: 12px 0; border-bottom: 1px solid #e5e7eb; text-align: right; color: #111827; font-weight: 500; font-size: 14px;">{plan.name}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 12px 0; border-bottom: 1px solid #e5e7eb; color: #6b7280; font-size: 14px;">Amount Paid</td>
                                                    <td style="padding: 12px 0; border-bottom: 1px solid #e5e7eb; text-align: right; color: #111827; font-weight: 600; font-size: 16px;">{payment['amount']:,.0f} {payment['currency']}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 12px 0; border-bottom: 1px solid #e5e7eb; color: #6b7280; font-size: 14px;">Payment Date</td>
                                                    <td style="padding: 12px 0; border-bottom: 1px solid #e5e7eb; text-align: right; color: #111827; font-weight: 500; font-size: 14px;">{payment.get('completed_at', datetime.now(timezone.utc)).strftime('%B %d, %Y at %H:%M UTC')}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 12px 0; color: #6b7280; font-size: 14px;">Status</td>
                                                    <td style="padding: 12px 0; text-align: right;">
                                                        <span style="background: #10b981; color: white; padding: 6px 16px; border-radius: 20px; font-size: 12px; font-weight: 600; display: inline-block;">PAID</span>
                                                    </td>
                                                </tr>
                                            </table>
                                        </div>

                                        <!-- Subscription Active -->
                                        <div style="background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border-radius: 12px; padding: 20px; margin-bottom: 30px; border-left: 4px solid #3b82f6;">
                                            <p style="margin: 0; color: #1e40af; font-size: 16px; font-weight: 600;">
                                                🎉 Your subscription is now active!
                                            </p>
                                            <p style="margin: 12px 0 0 0; color: #1e40af; font-size: 14px; line-height: 1.5;">
                                                Start using your plan with <strong>{plan.tokens_limit:,} tokens</strong> and <strong>{plan.requests_limit:,} requests</strong>.
                                            </p>
                                        </div>

                                        <!-- Support -->
                                        <p style="margin: 30px 0 0 0; color: #6b7280; font-size: 14px; line-height: 1.6;">
                                            If you have any questions or need assistance, feel free to contact us at
                                            <a href="mailto:{settings.SMTP_FROM_EMAIL}" style="color: #667eea; text-decoration: none;">{settings.SMTP_FROM_EMAIL}</a>
                                        </p>

                                        <p style="margin: 20px 0 0 0; color: #6b7280; font-size: 14px;">
                                            Best regards,<br>
                                            <strong style="color: #111827;">Task Management AI Team</strong>
                                        </p>
                                    </td>
                                </tr>

                                <!-- Footer -->
                                <tr>
                                    <td style="background: #f9fafb; padding: 20px 30px; text-align: center; border-top: 1px solid #e5e7eb;">
                                        <p style="margin: 0; color: #9ca3af; font-size: 12px; line-height: 1.5;">
                                            This is an automated email. Please do not reply to this message.<br>
                                            © 2025 Task Management AI. All rights reserved.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            """

            # Send email async
           
            email_service = EmailService()

            # Prepare PDF attachment
            pdf_filename = f"receipt_{payment.get('transaction_id', payment.get('_id'))}.pdf"
            attachments = [
                {
                    'filename': pdf_filename,
                    'content': pdf_buffer
                }
            ]

            # Run async email in background thread to avoid event loop conflict
            import threading

            def send_email_sync():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(email_service.send_email(
                        to_emails=[user_email],
                        subject=subject,
                        html_content=html_content,
                        attachments=attachments
                    ))
                finally:
                    loop.close()

            # Run in separate thread to avoid blocking
            email_thread = threading.Thread(target=send_email_sync)
            email_thread.start()
            email_thread.join(timeout=30)  # Wait max 30 seconds

            logger.info(f"Sent payment receipt email with PDF to {user_email}")

            # Log email sent
            log_receipt_email_sent(
                str(payment.get('_id')),
                user_id,
                user_email,
                'success',
                f"attachment={pdf_filename}"
            )

        except Exception as e:
            logger.error(f"Error sending payment receipt email: {str(e)}")

            # Log error
            log_receipt_error(
                str(payment.get('_id', 'unknown')),
                user_id,
                'email_send_failed',
                str(e)
            )

            traceback.print_exc()
