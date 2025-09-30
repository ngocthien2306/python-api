import asyncio
import sys
import os
sys.path.append('.')
from app.services.email_service import EmailService

async def test_email():
    email_service = EmailService()
    print('Testing email service...')
    success = await email_service.send_verification_email(
        email='ngocthien.dev23@gmail.com',
        username='testuser',
        verification_token='test_token_123'
    )
    print(f'Email sent successfully: {success}')

asyncio.run(test_email())
