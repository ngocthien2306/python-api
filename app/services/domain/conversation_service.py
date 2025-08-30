from typing import Dict, Any, List
from datetime import datetime, timedelta
from app.repositories.conversation import ConversationRepository
from app.models.conversation import Conversation, Message
from app.schemas.ai_response import AIResponse


class ConversationService:
    """Service responsible for all conversation-related operations"""
    
    def __init__(self, conversation_repo: ConversationRepository):
        self.conversation_repo = conversation_repo
    
    def save_conversation(self, parsed_response: AIResponse, user_input: str, 
                         user_id: str, session_id: str) -> Dict[str, Any]:
        """Save conversation to database"""
        conversation = Conversation(user_id, session_id)
        conversation.active_topics = self._extract_topics(user_input)
        conversation.user_mood = self._detect_mood(user_input)
        
        # Add user message
        conversation.messages.append(Message(
            timestamp=datetime.now(),
            role="user",
            content=user_input,
            intent=parsed_response.intent,
            confidence=parsed_response.confidence,
            mode=parsed_response.mode
        ))
        
        # Add assistant messages
        for msg in parsed_response.messages:
            conversation.messages.append(Message(
                timestamp=datetime.now(),
                role="assistant",
                content=msg.text,
                facialExpression=msg.facialExpression,
                animation=msg.animation
            ))
        
        # Convert to database format and save
        conv_doc = self._convert_conversation_to_db_format(conversation)
        conv_id = self.conversation_repo.create(conv_doc)
        
        return {
            "conversation_id": conv_id, 
            "messages_count": len(conversation.messages),
            "session_id": session_id,
            "user_mood": conversation.user_mood,
            "topics": conversation.active_topics
        }
    
    def get_conversation_history(self, user_id: str, limit: int = 10, 
                               session_id: str = None) -> List[Dict[str, Any]]:
        """Get conversation history for user"""
        try:
            query = {"userId": user_id}
            if session_id:
                query["sessionId"] = session_id
            
            conversations = self.conversation_repo.find_by_query(
                query, 
                limit=limit, 
                sort=[("createdAt", -1)]
            )
            
            return [
                {
                    "conversation_id": str(conv.get("_id", conv.get("id"))),
                    "session_id": conv.get("sessionId"),
                    "created_at": conv.get("createdAt"),
                    "message_count": len(conv.get("messages", [])),
                    "topics": conv.get("activeTopics", []),
                    "mood": conv.get("userMood", "neutral")
                }
                for conv in conversations
            ]
        
        except Exception as e:
            print(f"Error fetching conversation history: {e}")
            return []
    
    def get_conversation_details(self, conversation_id: str, user_id: str) -> Dict[str, Any]:
        """Get detailed conversation with all messages"""
        try:
            conversation = self.conversation_repo.find_by_id(conversation_id)
            
            if not conversation or conversation.get("userId") != user_id:
                return {"success": False, "error": "Conversation not found"}
            
            return {
                "success": True,
                "conversation_id": conversation_id,
                "session_id": conversation.get("sessionId"),
                "created_at": conversation.get("createdAt"),
                "updated_at": conversation.get("updatedAt"),
                "topics": conversation.get("activeTopics", []),
                "mood": conversation.get("userMood", "neutral"),
                "messages": [
                    {
                        "timestamp": msg.get("timestamp"),
                        "role": msg.get("role"),
                        "content": msg.get("content"),
                        "intent": msg.get("intent"),
                        "confidence": msg.get("confidence"),
                        "mode": msg.get("mode"),
                        "facial_expression": msg.get("facialExpression"),
                        "animation": msg.get("animation")
                    }
                    for msg in conversation.get("messages", [])
                ]
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def analyze_conversation_patterns(self, user_id: str, days_back: int = 30) -> Dict[str, Any]:
        """Analyze user's conversation patterns and preferences"""
        try:
            start_date = datetime.now() - timedelta(days=days_back)
            query = {
                "userId": user_id,
                "createdAt": {"$gte": start_date}
            }
            
            conversations = self.conversation_repo.find_by_query(query, limit=100)
            
            # Analyze patterns
            total_conversations = len(conversations)
            topics_frequency = {}
            mood_distribution = {}
            intent_patterns = {}
            
            for conv in conversations:
                # Count topics
                for topic in conv.get("activeTopics", []):
                    topics_frequency[topic] = topics_frequency.get(topic, 0) + 1
                
                # Count moods
                mood = conv.get("userMood", "neutral")
                mood_distribution[mood] = mood_distribution.get(mood, 0) + 1
                
                # Count intents from messages
                for msg in conv.get("messages", []):
                    if msg.get("role") == "user" and msg.get("intent"):
                        intent = msg.get("intent")
                        intent_patterns[intent] = intent_patterns.get(intent, 0) + 1
            
            # Calculate averages and insights
            avg_messages_per_conversation = (
                sum(len(conv.get("messages", [])) for conv in conversations) / total_conversations
                if total_conversations > 0 else 0
            )
            
            most_common_topics = sorted(topics_frequency.items(), key=lambda x: x[1], reverse=True)[:5]
            most_common_mood = max(mood_distribution.items(), key=lambda x: x[1])[0] if mood_distribution else "neutral"
            
            return {
                "success": True,
                "analysis_period": f"Last {days_back} days",
                "total_conversations": total_conversations,
                "avg_messages_per_conversation": round(avg_messages_per_conversation, 2),
                "most_common_topics": most_common_topics,
                "most_common_mood": most_common_mood,
                "mood_distribution": mood_distribution,
                "intent_patterns": intent_patterns,
                "insights": self._generate_conversation_insights(
                    most_common_topics, most_common_mood, mood_distribution, intent_patterns
                )
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_user_conversations_summary(self, user_id: str) -> Dict[str, Any]:
        """Get conversation summary for user"""
        try:
            conversation_query = {"userId": user_id}
            conversation_count = len(self.conversation_repo.find_by_query(conversation_query, limit=1000))
            
            return {
                "success": True,
                "total_conversations": conversation_count
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _convert_conversation_to_db_format(self, conversation: Conversation) -> Dict[str, Any]:
        """Convert Conversation model to database format"""
        conv_doc = conversation.to_dict()
        conv_doc["userId"] = conv_doc.pop("user_id")
        conv_doc["sessionId"] = conv_doc.pop("session_id")
        conv_doc["activeTopics"] = conv_doc.pop("active_topics")
        conv_doc["userMood"] = conv_doc.pop("user_mood")
        conv_doc["createdAt"] = conv_doc.pop("created_at")
        conv_doc["updatedAt"] = conv_doc.pop("updated_at")
        
        conv_doc["messages"] = [
            {
                "timestamp": msg.timestamp,
                "role": msg.role,
                "content": msg.content,
                **{k: v for k, v in msg.__dict__.items() if k not in ["timestamp", "role", "content"]}
            }
            for msg in conversation.messages
        ]
        
        return conv_doc
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from user input"""
        keywords = [
            "meeting", "deadline", "project", "client", "report", "call",
            "task", "schedule", "reminder", "work", "personal", "health"
        ]
        text_lower = text.lower()
        return [kw for kw in keywords if kw in text_lower]
    
    def _detect_mood(self, text: str) -> str:
        """Detect user mood from input"""
        stress_words = ["stress", "panic", "overwhelmed", "chaos", "deadline", "urgent", "emergency"]
        happy_words = ["great", "excited", "good", "awesome", "perfect", "excellent", "wonderful"]
        frustrated_words = ["frustrated", "annoyed", "angry", "difficult", "problem", "issue"]
        calm_words = ["calm", "peaceful", "relaxed", "easy", "simple", "comfortable"]
        
        text_lower = text.lower()
        
        if any(word in text_lower for word in stress_words):
            return "stressed"
        elif any(word in text_lower for word in happy_words):
            return "positive"
        elif any(word in text_lower for word in frustrated_words):
            return "frustrated"
        elif any(word in text_lower for word in calm_words):
            return "calm"
        else:
            return "neutral"
    
    def _generate_conversation_insights(self, topics, mood, mood_dist, intents) -> List[str]:
        """Generate insights based on conversation patterns"""
        insights = []
        
        if topics:
            top_topic = topics[0][0]
            insights.append(f"Most discussed topic: {top_topic} ({topics[0][1]} times)")
        
        if mood == "stressed" and mood_dist.get("stressed", 0) > mood_dist.get("positive", 0):
            insights.append("User frequently appears stressed - consider stress management suggestions")
        
        if "task_creation" in intents and intents["task_creation"] > 5:
            insights.append("User frequently creates tasks - efficient task management user")
        
        if "scheduling" in intents and intents["scheduling"] > 3:
            insights.append("User often needs scheduling help - consider proactive schedule optimization")
        
        return insights