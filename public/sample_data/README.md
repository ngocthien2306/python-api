# Sample Data for Chat Endpoint Testing

## 📁 Files Created

### Authentication
- `login_request.json` - Login credentials to get JWT token

### Chat Requests
- `chat_basic.json` - Basic reminder/task creation
- `chat_task_creation.json` - Explicit task creation with priority
- `chat_conversation.json` - Conversational/emotional chat
- `chat_scheduling.json` - Complex scheduling with multiple tasks

### Audio Testing
- `audio_generation.json` - Direct audio generation test for Node.js service

### Commands
- `test_commands.txt` - Complete curl commands for testing

## 🚀 How to Test

### Step 1: Update Credentials
Edit `login_request.json` with your actual email/password:
```json
{
  "email": "your_actual_email@example.com",
  "password": "your_actual_password"
}
```

### Step 2: Get Authentication Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d @sample_data/login_request.json
```

Copy the `access_token` from the response.

### Step 3: Test Chat Endpoint
Replace `YOUR_TOKEN` with the actual token:

```bash
# Basic chat test
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d @sample_data/chat_basic.json
```

### Step 4: Test Audio Generation
```bash
curl -X POST http://localhost:3000/generate-audio \
  -H "Content-Type: application/json" \
  -d @sample_data/audio_generation.json
```

## 📊 Expected Responses

### Chat Response Format
```json
{
  "success": true,
  "messages": [
    {
      "text": "Được rồi! Tôi sẽ nhắc bạn họp team lúc 2h chiều mai nhé!",
      "facial_expression": "smile",
      "animation": "Talking_0",
      "audio": "base64_encoded_audio_data",
      "lipsync": {
        "mouthCues": [...]
      },
      "duration": 3.2
    }
  ],
  "metadata": {
    "mode": "simple_task",
    "intent": "create_meeting_reminder",
    "confidence": 0.96,
    "task_created": {
      "id": "task_abc123",
      "title": "Họp team"
    },
    "processing_time": 2.1
  }
}
```

### Audio Response Format
```json
{
  "success": true,
  "audio_data": [
    {
      "message_id": "test_001",
      "audio_base64": "UklGRnoGAAB...",
      "lipsync": {
        "mouthCues": [
          {"start": 0.0, "end": 0.1, "value": "A"},
          {"start": 0.1, "end": 0.2, "value": "B"}
        ]
      },
      "duration": 3.2,
      "success": true
    }
  ],
  "processing_time": 1500,
  "message_count": 1
}
```

## 🔧 Troubleshooting

### Common Issues
1. **401 Unauthorized**: Token expired or invalid - get new token
2. **500 Internal Server Error**: Check OpenAI API key in Python API
3. **Connection Refused**: Make sure both services are running

### Check Services
```bash
# Python API
curl http://localhost:8000/docs

# Node.js Audio Service  
curl http://localhost:3000/health

# Test simplified architecture
./test_simplified_architecture.sh
```

## 📝 Notes

- User ID `68b4c6d9318be756896bf562` is from the logs (update if needed)
- Session IDs should be unique for each test
- Timestamps are in ISO format
- All text is in Vietnamese as per the original system