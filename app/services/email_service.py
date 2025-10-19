import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from jinja2 import Template
from typing import List, Optional
from io import BytesIO
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
        text_content: Optional[str] = None,
        attachments: Optional[List[dict]] = None
    ) -> bool:
        """
        Send email using aiosmtplib for async operation.

        Args:
            attachments: List of dicts with 'filename' and 'content' (BytesIO)
        """
        try:
            message = MIMEMultipart("mixed")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = ", ".join(to_emails)

            # Create alternative part for text/html
            msg_alternative = MIMEMultipart("alternative")
            message.attach(msg_alternative)

            # Add text part if provided
            if text_content:
                text_part = MIMEText(text_content, "plain")
                msg_alternative.attach(text_part)

            # Add HTML part
            html_part = MIMEText(html_content, "html")
            msg_alternative.attach(html_part)

            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    filename = attachment.get('filename', 'attachment.pdf')
                    content = attachment.get('content')  # BytesIO

                    if content:
                        part = MIMEApplication(content.getvalue(), _subtype="pdf")
                        part.add_header('Content-Disposition', 'attachment', filename=filename)
                        message.attach(part)

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

    async def send_task_reminder_email(self, email: str, username: str, tasks: list) -> bool:
        """Send task reminder email with upcoming/overdue tasks."""
        upcoming_tasks = [t for t in tasks if t.get('is_upcoming')]
        overdue_tasks = [t for t in tasks if t.get('is_overdue')]
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Task Reminder</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #2563eb; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background-color: #f9f9f9; }
                .task-section { margin-bottom: 30px; }
                .task-item { 
                    background: white; 
                    border-left: 4px solid #2563eb; 
                    padding: 15px; 
                    margin: 10px 0; 
                    border-radius: 5px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .overdue { border-left-color: #dc2626; }
                .upcoming { border-left-color: #f59e0b; }
                .task-title { font-weight: bold; color: #1f2937; margin-bottom: 5px; }
                .task-meta { font-size: 12px; color: #6b7280; }
                .priority-high { color: #dc2626; font-weight: bold; }
                .priority-urgent { color: #991b1b; font-weight: bold; background: #fee2e2; padding: 2px 6px; border-radius: 3px; }
                .footer { padding: 20px; text-align: center; color: #666; font-size: 12px; }
                .btn { 
                    display: inline-block; 
                    padding: 10px 20px; 
                    background-color: #2563eb; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 5px; 
                    margin: 10px 5px; 
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 Task Reminder</h1>
                    <p>Hi {{ username }}! You have tasks that need your attention.</p>
                </div>
                <div class="content">
                    {% if overdue_tasks %}
                    <div class="task-section">
                        <h2 style="color: #dc2626;">🚨 Overdue Tasks ({{ overdue_tasks|length }})</h2>
                        {% for task in overdue_tasks %}
                        <div class="task-item overdue">
                            <div class="task-title">{{ task.title }}</div>
                            {% if task.description %}
                            <div style="margin: 5px 0; color: #6b7280;">{{ task.description[:100] }}{% if task.description|length > 100 %}...{% endif %}</div>
                            {% endif %}
                            <div class="task-meta">
                                Due: {{ task.due_date_formatted }} 
                                {% if task.due_time %}at {{ task.due_time }}{% endif %}
                                | Priority: <span class="priority-{{ task.priority }}">{{ task.priority.title() }}</span>
                                | Category: {{ task.category.title() }}
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                    {% endif %}

                    {% if upcoming_tasks %}
                    <div class="task-section">
                        <h2 style="color: #f59e0b;">⏰ Upcoming Tasks ({{ upcoming_tasks|length }})</h2>
                        {% for task in upcoming_tasks %}
                        <div class="task-item upcoming">
                            <div class="task-title">{{ task.title }}</div>
                            {% if task.description %}
                            <div style="margin: 5px 0; color: #6b7280;">{{ task.description[:100] }}{% if task.description|length > 100 %}...{% endif %}</div>
                            {% endif %}
                            <div class="task-meta">
                                Due: {{ task.due_date_formatted }} 
                                {% if task.due_time %}at {{ task.due_time }}{% endif %}
                                | Priority: <span class="priority-{{ task.priority }}">{{ task.priority.title() }}</span>
                                | Category: {{ task.category.title() }}
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                    {% endif %}

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{{ app_url }}" class="btn">Open Task Management</a>
                        <a href="{{ app_url }}/tasks" class="btn" style="background-color: #059669;">View All Tasks</a>
                    </div>

                    <div style="background: #e0f2fe; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #0277bd;">💡 Productivity Tip</h3>
                        <p style="margin-bottom: 0;">Break large tasks into smaller subtasks and tackle the most important ones first. You've got this! 🚀</p>
                    </div>
                </div>
                <div class="footer">
                    <p>This email was sent by Task Management System</p>
                    <p>You can manage your notification preferences in your account settings.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hi {username}!
        
        You have tasks that need your attention:
        
        """
        
        if overdue_tasks:
            text_content += f"🚨 OVERDUE TASKS ({len(overdue_tasks)}):\n"
            for task in overdue_tasks:
                text_content += f"- {task['title']} (Due: {task['due_date_formatted']})\n"
            text_content += "\n"
        
        if upcoming_tasks:
            text_content += f"⏰ UPCOMING TASKS ({len(upcoming_tasks)}):\n"
            for task in upcoming_tasks:
                text_content += f"- {task['title']} (Due: {task['due_date_formatted']})\n"
            text_content += "\n"
        
        text_content += f"Open your task management: {settings.FRONTEND_URL}\n"
        text_content += "Stay organized and productive! 🚀"
        
        template = Template(html_template)
        html_content = template.render(
            username=username,
            overdue_tasks=overdue_tasks,
            upcoming_tasks=upcoming_tasks,
            app_url=settings.FRONTEND_URL
        )
        
        subject = "📋 Task Reminder"
        if overdue_tasks and upcoming_tasks:
            subject += f" - {len(overdue_tasks)} Overdue, {len(upcoming_tasks)} Upcoming"
        elif overdue_tasks:
            subject += f" - {len(overdue_tasks)} Overdue Tasks"
        elif upcoming_tasks:
            subject += f" - {len(upcoming_tasks)} Upcoming Tasks"
        
        return await self.send_email(
            to_emails=[email],
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )

    async def send_task_due_soon_email(self, email: str, username: str, task: dict) -> bool:
        """Send individual task due soon notification."""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Task Due Soon</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #f59e0b; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background-color: #f9f9f9; }
                .task-card { 
                    background: white; 
                    border: 2px solid #f59e0b; 
                    padding: 20px; 
                    border-radius: 10px;
                    margin: 20px 0;
                }
                .task-title { font-size: 18px; font-weight: bold; color: #1f2937; margin-bottom: 10px; }
                .task-meta { color: #6b7280; margin: 5px 0; }
                .priority-high { color: #dc2626; font-weight: bold; }
                .priority-urgent { color: #991b1b; font-weight: bold; }
                .btn { 
                    display: inline-block; 
                    padding: 12px 24px; 
                    background-color: #f59e0b; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 5px; 
                    margin: 15px 5px; 
                }
                .footer { padding: 20px; text-align: center; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⏰ Task Due Soon</h1>
                    <p>Hi {{ username }}! One of your tasks is due soon.</p>
                </div>
                <div class="content">
                    <div class="task-card">
                        <div class="task-title">{{ task.title }}</div>
                        {% if task.description %}
                        <div style="margin: 10px 0; color: #4b5563;">{{ task.description }}</div>
                        {% endif %}
                        <div class="task-meta">
                            <strong>Due:</strong> {{ task.due_date_formatted }}{% if task.due_time %} at {{ task.due_time }}{% endif %}
                        </div>
                        <div class="task-meta">
                            <strong>Priority:</strong> <span class="priority-{{ task.priority }}">{{ task.priority.title() }}</span>
                        </div>
                        <div class="task-meta">
                            <strong>Category:</strong> {{ task.category.title() }}
                        </div>
                        {% if task.estimated_duration %}
                        <div class="task-meta">
                            <strong>Estimated Time:</strong> {{ task.estimated_duration }} minutes
                        </div>
                        {% endif %}
                    </div>

                    <div style="text-align: center;">
                        <a href="{{ app_url }}/tasks/{{ task.id }}" class="btn">View Task</a>
                        <a href="{{ app_url }}/tasks" class="btn" style="background-color: #059669;">All Tasks</a>
                    </div>
                </div>
                <div class="footer">
                    <p>This email was sent by Task Management System</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hi {username}!
        
        Your task "{task['title']}" is due soon:
        
        Due: {task['due_date_formatted']} {task.get('due_time', '')}
        Priority: {task['priority'].title()}
        Category: {task['category'].title()}
        
        View task: {settings.FRONTEND_URL}/tasks/{task['id']}
        """
        
        template = Template(html_template)
        html_content = template.render(
            username=username,
            task=task,
            app_url=settings.FRONTEND_URL
        )
        
        return await self.send_email(
            to_emails=[email],
            subject=f"⏰ Task Due Soon: {task['title']}",
            html_content=html_content,
            text_content=text_content
        )

    async def send_task_reminder_notification_email(self, email: str, username: str, task: dict, reminder: dict) -> bool:
        """Send task reminder notification email based on reminder settings."""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Task Reminder</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #8b5cf6; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background-color: #f9f9f9; }
                .reminder-card { 
                    background: white; 
                    border: 2px solid #8b5cf6; 
                    padding: 20px; 
                    border-radius: 10px;
                    margin: 20px 0;
                }
                .task-title { font-size: 18px; font-weight: bold; color: #1f2937; margin-bottom: 10px; }
                .reminder-message { 
                    background: #f3f4f6; 
                    padding: 15px; 
                    border-radius: 5px; 
                    margin: 10px 0; 
                    border-left: 4px solid #8b5cf6;
                    font-style: italic;
                }
                .task-meta { color: #6b7280; margin: 5px 0; }
                .priority-high { color: #dc2626; font-weight: bold; }
                .priority-urgent { color: #991b1b; font-weight: bold; }
                .btn { 
                    display: inline-block; 
                    padding: 12px 24px; 
                    background-color: #8b5cf6; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 5px; 
                    margin: 15px 5px; 
                }
                .footer { padding: 20px; text-align: center; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔔 Task Reminder</h1>
                    <p>Hi {{ username }}! You have a scheduled reminder.</p>
                </div>
                <div class="content">
                    {% if reminder.reminder_message %}
                    <div class="reminder-message">
                        "{{ reminder.reminder_message }}"
                    </div>
                    {% endif %}
                    
                    <div class="reminder-card">
                        <div class="task-title">{{ task.title }}</div>
                        {% if task.description %}
                        <div style="margin: 10px 0; color: #4b5563;">{{ task.description }}</div>
                        {% endif %}
                        <div class="task-meta">
                            <strong>Due:</strong> {{ task.due_date_formatted }}{% if task.due_time %} at {{ task.due_time }}{% endif %}
                        </div>
                        <div class="task-meta">
                            <strong>Priority:</strong> <span class="priority-{{ task.priority }}">{{ task.priority.title() }}</span>
                        </div>
                        <div class="task-meta">
                            <strong>Category:</strong> {{ task.category.title() }}
                        </div>
                        {% if task.estimated_duration %}
                        <div class="task-meta">
                            <strong>Estimated Time:</strong> {{ task.estimated_duration }} minutes
                        </div>
                        {% endif %}
                        {% if reminder.before_due %}
                        <div class="task-meta">
                            <strong>Reminder:</strong> {{ reminder.before_due }} before due time
                        </div>
                        {% endif %}
                    </div>

                    <div style="text-align: center;">
                        <a href="{{ app_url }}/tasks/{{ task.id }}" class="btn">View Task</a>
                        <a href="{{ app_url }}/tasks" class="btn" style="background-color: #059669;">All Tasks</a>
                    </div>
                </div>
                <div class="footer">
                    <p>This email was sent by Task Management System</p>
                    <p>Reminder scheduled for {{ reminder.before_due }} before due time</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hi {username}!
        
        Reminder: {reminder.get('reminder_message', 'Task reminder')}
        
        Task: {task['title']}
        Due: {task['due_date_formatted']} {task.get('due_time', '')}
        Priority: {task['priority'].title()}
        Category: {task['category'].title()}
        
        View task: {settings.FRONTEND_URL}/tasks/{task['id']}
        """
        
        template = Template(html_template)
        html_content = template.render(
            username=username,
            task=task,
            reminder=reminder,
            app_url=settings.FRONTEND_URL
        )
        
        return await self.send_email(
            to_emails=[email],
            subject=f"🔔 Task Reminder: {task['title']}",
            html_content=html_content,
            text_content=text_content
        )