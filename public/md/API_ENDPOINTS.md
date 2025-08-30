# API Endpoints - Updated with Refactored Architecture

## 🔄 Existing Endpoints (Updated)

### POST `/process-conversation`
Process AI conversations using the new orchestrator architecture.
- **No changes to API** - Same request/response format
- **Internally**: Uses refactored services for better maintainability

### GET `/health`
Health check endpoint
- **Status**: Unchanged

### GET `/stats/{user_id}` 
Get comprehensive user statistics
- **Updated**: Now uses `UserAnalyticsService` instead of direct repo access
- **Enhanced**: Provides richer analytics data

## ✨ New Endpoints Using Refactored Services

### Tasks
#### GET `/tasks/{user_id}`
Get user tasks with advanced filtering
```
Query Parameters:
- status: pending|in_progress|completed
- category: work|personal|health|etc
- priority: urgent|high|medium|low
- limit: number (default: 20)

Response:
{
  "success": true,
  "tasks_found": 5,
  "tasks": [
    {
      "id": "task_id",
      "title": "Task Title",
      "status": "pending",
      "priority": "high",
      "category": "work",
      "dueDate": "2024-01-15",
      "dueTime": "14:00"
    }
  ]
}
```

### Reminders
#### GET `/reminders/{user_id}`
Get upcoming reminders
```
Query Parameters:
- hours_ahead: number (default: 24)

Response:
{
  "user_id": "user123",
  "hours_ahead": 24,
  "reminders": [
    {
      "reminder_id": "rem_id",
      "trigger_time": "2024-01-15T14:00:00",
      "message": "Meeting starts in 15 minutes",
      "task_title": "Team Meeting",
      "type": "schedule",
      "priority": "high"
    }
  ],
  "count": 3
}
```

#### POST `/reminders/{reminder_id}/mark-sent`
Mark reminder as sent
```
Response:
{
  "success": true,
  "reminder_id": "rem_123",
  "status": "sent"
}
```

### Schedules
#### GET `/schedules/{user_id}`
Get user schedule summary
```
Query Parameters:
- days_ahead: number (default: 7)

Response:
{
  "success": true,
  "schedules_count": 3,
  "total_workload": 480,
  "total_conflicts": 1,
  "period": "2024-01-15 to 2024-01-22"
}
```

### Conversations  
#### GET `/conversations/{user_id}`
Get conversation history
```
Query Parameters:
- limit: number (default: 10)
- session_id: string (optional)

Response:
{
  "user_id": "user123",
  "conversations": [
    {
      "conversation_id": "conv_id",
      "session_id": "session_123",
      "created_at": "2024-01-15T10:00:00",
      "message_count": 6,
      "topics": ["task", "meeting"],
      "mood": "positive"
    }
  ],
  "count": 5
}
```

#### GET `/conversations/{user_id}/analysis`
Get conversation pattern analysis
```
Query Parameters:
- days_back: number (default: 30)

Response:
{
  "success": true,
  "analysis_period": "Last 30 days",
  "total_conversations": 25,
  "avg_messages_per_conversation": 4.2,
  "most_common_topics": [
    ["task", 15],
    ["meeting", 12],
    ["deadline", 8]
  ],
  "most_common_mood": "positive",
  "mood_distribution": {
    "positive": 15,
    "neutral": 8,
    "stressed": 2
  },
  "insights": [
    "Most discussed topic: task (15 times)",
    "User frequently creates tasks - efficient task management user"
  ]
}
```

### Analytics
#### GET `/analytics/{user_id}/performance`
Get user performance metrics
```
Query Parameters:
- days_back: number (default: 30)

Response:
{
  "success": true,
  "analysis_period": "Last 30 days",
  "task_completion_rate": 85.5,
  "total_conversations": 25,
  "most_common_mood": "positive",
  "engagement_level": "high",
  "efficiency_trends": [
    "Great productivity! Consider taking on new challenges"
  ]
}
```

#### GET `/analytics/{user_id}/comprehensive`
Get comprehensive user analytics (orchestrator demo)
```
Response:
{
  "user_id": "user123",
  "summary": {
    "success": true,
    "tasks": {...},
    "reminders": {...},
    "conversations": {...},
    "schedules": {...},
    "insights": {
      "total_active_items": 15,
      "productivity_score": 87.5,
      "recommendations": [
        "Great productivity! Consider taking on new challenges"
      ]
    }
  },
  "upcoming_reminders": {
    "count": 3,
    "reminders": [...]
  },
  "recent_conversations": {
    "count": 5,
    "conversations": [...]
  },
  "performance": {...}
}
```

## 🎯 Benefits of New Architecture

### For Developers
- **Focused endpoints**: Each endpoint uses specific services
- **Easy testing**: Mock individual services instead of entire system
- **Clear responsibilities**: Each service handles one domain

### For Users  
- **Better performance**: Optimized queries per service
- **Rich data**: More detailed analytics and insights
- **Reliable**: Better error handling and validation

### API Usage Examples

```bash
# Get pending tasks only
GET /tasks/user123?status=pending&limit=10

# Get reminders for next 48 hours  
GET /reminders/user123?hours_ahead=48

# Get conversation analysis for last week
GET /conversations/user123/analysis?days_back=7

# Get performance metrics for last month
GET /analytics/user123/performance?days_back=30
```

## 🔧 Migration Notes

1. **Backward Compatibility**: All existing endpoints work unchanged
2. **Enhanced Data**: `/stats/{user_id}` now returns richer information
3. **New Features**: 8 new endpoints with specialized functionality
4. **Better Errors**: More specific error messages from individual services
5. **Performance**: Faster responses due to optimized service architecture