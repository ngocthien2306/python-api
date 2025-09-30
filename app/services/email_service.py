import aiosmtplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
from typing import List, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME

    async def send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send email using aiosmtplib for async operation."""
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = ", ".join(to_emails)

            # Add text part if provided
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)

            # Add HTML part
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                start_tls=True,
                username=self.smtp_username,
                password=self.smtp_password,
            )
            
            logger.info(f"Email sent successfully to {to_emails}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_emails}: {str(e)}")
            return False

    async def send_verification_email(self, email: str, username: str, verification_token: str) -> bool:
        """Send account verification email."""
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Verify Your Account</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #4f46e5; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background-color: #f9f9f9; }
                .button { 
                    display: inline-block; 
                    padding: 12px 24px; 
                    background-color: #4f46e5; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 5px; 
                    margin: 20px 0; 
                }
                .footer { padding: 20px; text-align: center; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Task Management!</h1>
                </div>
                <div class="content">
                    <h2>Hi {{ username }}!</h2>
                    <p>Thank you for registering with Task Management. To complete your registration and verify your email address, please click the button below:</p>
                    
                    <div style="text-align: center;">
                        <a href="{{ verification_url }}" class="button">Verify Your Email</a>
                    </div>
                    
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #4f46e5;">{{ verification_url }}</p>
                    
                    <p><strong>This verification link will expire in 24 hours.</strong></p>
                    
                    <p>If you didn't create an account with us, you can safely ignore this email.</p>
                </div>
                <div class="footer">
                    <p>This email was sent by Task Management System</p>
                    <p>If you have any questions, please contact our support team.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hi {username}!
        
        Thank you for registering with Task Management. To complete your registration and verify your email address, please visit:
        
        {verification_url}
        
        This verification link will expire in 24 hours.
        
        If you didn't create an account with us, you can safely ignore this email.
        """
        
        template = Template(html_template)
        html_content = template.render(
            username=username,
            verification_url=verification_url
        )
        
        return await self.send_email(
            to_emails=[email],
            subject="Verify Your Email Address - Task Management",
            html_content=html_content,
            text_content=text_content
        )

    async def send_password_reset_email(self, email: str, username: str, reset_token: str) -> bool:
        """Send password reset email."""
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Reset Your Password</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #dc2626; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background-color: #f9f9f9; }
                .button { 
                    display: inline-block; 
                    padding: 12px 24px; 
                    background-color: #dc2626; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 5px; 
                    margin: 20px 0; 
                }
                .footer { padding: 20px; text-align: center; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset Request</h1>
                </div>
                <div class="content">
                    <h2>Hi {{ username }}!</h2>
                    <p>We received a request to reset your password for your Task Management account. Click the button below to reset your password:</p>
                    
                    <div style="text-align: center;">
                        <a href="{{ reset_url }}" class="button">Reset Password</a>
                    </div>
                    
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #dc2626;">{{ reset_url }}</p>
                    
                    <p><strong>This reset link will expire in 1 hour.</strong></p>
                    
                    <p>If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.</p>
                </div>
                <div class="footer">
                    <p>This email was sent by Task Management System</p>
                    <p>If you have any questions, please contact our support team.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hi {username}!
        
        We received a request to reset your password for your Task Management account. To reset your password, please visit:
        
        {reset_url}
        
        This reset link will expire in 1 hour.
        
        If you didn't request a password reset, you can safely ignore this email.
        """
        
        template = Template(html_template)
        html_content = template.render(
            username=username,
            reset_url=reset_url
        )
        
        return await self.send_email(
            to_emails=[email],
            subject="Reset Your Password - Task Management",
            html_content=html_content,
            text_content=text_content
        )