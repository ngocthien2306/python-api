# AI Assistant API with JWT Authentication & ChatGPT Integration

## Overview
This API provides user authentication, personality management, and ChatGPT integration for a 3D avatar AI assistant system.

## Authentication Flow

### 1. User Registration
```bash
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "securepassword123",
  "first_name": "John",
  "last_name": "Doe"
}
```

### 2. User Login
```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "johndoe",
  "password": "securepassword123"
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3. Get User Profile
```bash
GET /api/v1/auth/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 4. Update User Profile & Personality
```bash
PUT /api/v1/auth/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "first_name": "John",
  "last_name": "Doe Updated",
  "occupation": "Software Developer",
  "company": "Tech Corp",
  "personality": {
    "communication_style": "friendly",
    "preferred_tone": "helpful",
    "interaction_preference": "detailed",
    "work_style": "organized",
    "interests": ["programming", "AI", "3D graphics"],
    "timezone": "America/New_York",
    "language_preference": "en",
    "custom_instructions": "I prefer detailed explanations with code examples"
  }
}
```

## ChatGPT Integration Workflow

### Node.js API Integration Flow

1. **Node.js API receives user request**
2. **Node.js API calls Python API to get personality context**
3. **Node.js API sends context to ChatGPT**
4. **Node.js API receives ChatGPT response**
5. **Node.js API sends response to Python API for processing**

### 1. Get Personality Context for ChatGPT
```bash
GET /api/v1/chatgpt/personality-context
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Response:
```json
{
  "user_id": "6507d1234567890abcdef123",
  "username": "johndoe",
  "personality_context": {
    "communication_preferences": {
      "style": "friendly",
      "tone": "helpful",
      "interaction": "detailed",
      "work_style": "organized"
    },
    "user_info": {
      "timezone": "America/New_York",
      "language": "en",
      "interests": ["programming", "AI", "3D graphics"],
      "occupation": "Software Developer",
      "company": "Tech Corp"
    },
    "response_guidelines": {
      "recommended_tone": "warm and approachable",
      "response_style": "comprehensive and thorough",
      "custom_instructions": "User prefers friendly communication style | Respond with a helpful tone | User's work style is organized | User is in America/New_York timezone | User interests include: programming, AI, 3D graphics | User works as: Software Developer | I prefer detailed explanations with code examples"
    }
  },
  "conversation_history": [...],
  "recommended_tone": "warm and approachable",
  "response_style": "comprehensive and thorough",
  "custom_instructions": "User prefers friendly communication style | Respond with a helpful tone..."
}
```

### 2. Save ChatGPT Response
```bash
POST /api/v1/chatgpt/save-chatgpt-response
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "user_id": "6507d1234567890abcdef123",
  "chatgpt_response": "Based on your programming background and preference for detailed explanations...",
  "conversation_id": "chat_20240830_143022",
  "task_data": {
    "title": "Review code architecture",
    "description": "Review the new microservice architecture",
    "priority": "high",
    "category": "development",
    "dueDate": "2024-08-31",
    "status": "pending"
  },
  "schedule_data": {
    "title": "Code Review Meeting",
    "startTime": "2024-08-31T10:00:00Z",
    "duration": 60,
    "category": "meeting"
  }
}
```

### 3. Update Personality from Interaction
```bash
PUT /api/v1/chatgpt/update-personality-from-interaction
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "communication_style": "friendly",
  "interaction_preference": "interactive",
  "learned_preferences": {
    "prefers_code_examples": true,
    "likes_detailed_explanations": true
  }
}
```

## Process Conversation (Protected)
```bash
POST /api/v1/process-conversation
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "parsed_response": {
    "mode": "conversation",
    "intent": "task_management",
    "confidence": 0.95,
    "messages": [{
      "text": "I've created a new task for you to review the code architecture.",
      "facialExpression": "friendly",
      "animation": "talking"
    }],
    "taskAction": {
      "action": "create",
      "task": {
        "title": "Review code architecture",
        "priority": "high",
        "category": "development"
      }
    },
    "schedulingAction": {
      "type": "none"
    }
  },
  "user_input": "Create a task to review the new architecture",
  "user_id": "6507d1234567890abcdef123",
  "session_id": "session_20240830_143022",
  "timestamp": "2024-08-30T14:30:22Z",
  "source": "chatgpt"
}
```

## Node.js Integration Example

```javascript
// Example Node.js code for ChatGPT integration

class PythonAPIClient {
  constructor(apiUrl, token) {
    this.apiUrl = apiUrl;
    this.token = token;
  }

  async getPersonalityContext() {
    const response = await fetch(`${this.apiUrl}/api/v1/chatgpt/personality-context`, {
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      }
    });
    return response.json();
  }

  async saveChatGPTResponse(data) {
    const response = await fetch(`${this.apiUrl}/api/v1/chatgpt/save-chatgpt-response`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });
    return response.json();
  }
}

// Usage in Node.js API
async function handleUserRequest(userMessage, userToken) {
  const pythonAPI = new PythonAPIClient('http://localhost:8000', userToken);
  
  // 1. Get personality context
  const personalityContext = await pythonAPI.getPersonalityContext();
  
  // 2. Prepare ChatGPT prompt with personality
  const chatGPTPrompt = `
    User Context: ${JSON.stringify(personalityContext.personality_context)}
    Response Style: ${personalityContext.response_style}
    Custom Instructions: ${personalityContext.custom_instructions}
    
    User Message: ${userMessage}
  `;
  
  // 3. Call ChatGPT API
  const chatGPTResponse = await callChatGPTAPI(chatGPTPrompt);
  
  // 4. Save response to Python API
  const saveResult = await pythonAPI.saveChatGPTResponse({
    user_id: personalityContext.user_id,
    chatgpt_response: chatGPTResponse.content,
    conversation_id: generateConversationId(),
    metadata: {
      model: chatGPTResponse.model,
      tokens_used: chatGPTResponse.usage
    }
  });
  
  return {
    response: chatGPTResponse.content,
    conversation_id: saveResult.conversation_id
  };
}
```

## Protected Endpoints

All user-specific endpoints now require JWT authentication:

- `/api/v1/process-conversation` - Process AI conversations
- `/api/v1/stats/{user_id}` - Get user statistics
- `/api/v1/tasks/{user_id}` - Get user tasks
- `/api/v1/reminders/{user_id}` - Get user reminders
- `/api/v1/schedules/{user_id}` - Get user schedules
- `/api/v1/conversations/{user_id}` - Get conversation history

## Personality Fields for ChatGPT

The system supports these personality customizations:

- `communication_style`: friendly, formal, casual, professional
- `preferred_tone`: helpful, assertive, encouraging, direct
- `interaction_preference`: brief, detailed, interactive
- `work_style`: organized, flexible, deadline-driven, creative
- `interests`: Array of user interests
- `timezone`: User's timezone
- `language_preference`: Preferred language code
- `custom_instructions`: Free-text instructions for ChatGPT

## Environment Variables

Add to your `.env` file:
```
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=ai_assistant
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True
SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc