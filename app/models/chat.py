# app/models/chat.py
# Chat-related data models

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

class ConversationState(str, Enum):
    """Conversation state enumeration"""
    INITIAL = "initial"
    CLARIFYING = "clarifying"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"

class ClarificationQuestion(BaseModel):
    """Clarification question model"""
    question: str = Field(..., description="Clarification question to ask user")
    context: str = Field(..., description="Context for why this question is needed")
    options: Optional[List[str]] = Field(None, description="Optional predefined answer options")
    is_required: bool = Field(True, description="Whether this clarification is required")
    question_type: str = Field(..., description="Type of clarification: 'file_structure', 'data_format', 'goal', 'constraints'")

class ConversationContext(BaseModel):
    """Conversation context for multi-turn dialogue"""
    state: ConversationState = Field(ConversationState.INITIAL, description="Current conversation state")
    clarification_count: int = Field(0, description="Number of clarification questions asked")
    max_clarifications: int = Field(5, description="Maximum number of clarifications allowed")
    pending_clarifications: List[ClarificationQuestion] = Field(default_factory=list, description="Pending clarification questions")
    gathered_info: Dict[str, Any] = Field(default_factory=dict, description="Information gathered from clarifications")
    original_question: str = Field(..., description="User's original question")
    current_understanding: str = Field("", description="AI's current understanding of the problem")

class Message(BaseModel):
    """Chat message model"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)
    message_type: str = Field("normal", description="Message type: 'normal', 'clarification', 'plan', 'solution'")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Message metadata")

class ChatSession(BaseModel):
    """Chat session model"""
    session_id: str = Field(..., description="Unique session identifier")
    messages: List[Message] = Field(default_factory=list, description="Chat messages")
    plan: Optional[str] = Field(None, description="Current AI plan")
    temp_file_content: Optional[bytes] = Field(None, description="Temporary file content")
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session metadata")
    conversation_context: Optional[ConversationContext] = Field(None, description="Multi-turn conversation context")
    
    class Config:
        arbitrary_types_allowed = True

class QuestionClassification(BaseModel):
    """Question classification result"""
    classification: str = Field(..., description="'simple', 'complex', 'creative', 'analytical', or 'debugging'")
    confidence: float = Field(..., description="Classification confidence score")
    reasoning: Optional[str] = Field(None, description="Classification reasoning")
    recommended_model: Optional[str] = Field(None, description="Recommended AI model: 'openai', 'gemini', or 'gemini_flash'")
    estimated_tokens: Optional[int] = Field(None, description="Estimated token usage")
    needs_clarification: bool = Field(False, description="Whether the question needs clarification")
    clarification_reasons: List[str] = Field(default_factory=list, description="Reasons why clarification is needed")

class UserIntent(BaseModel):
    """User intent analysis result"""
    intent: str = Field(..., description="'agreement', 'modification', 'clarification', 'rejection', or 'other'")
    confidence: float = Field(..., description="Intent confidence score")
    reasoning: Optional[str] = Field(None, description="Intent analysis reasoning")

class AIResponse(BaseModel):
    """AI response model"""
    answer: str = Field(..., description="AI generated answer")
    session_id: str = Field(..., description="Session identifier")
    model_used: Optional[str] = Field(None, description="AI model used")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    response_type: str = Field("normal", description="Response type: 'normal', 'clarification', 'plan', 'solution'")
    next_action: Optional[str] = Field(None, description="Next action to take")
    conversation_state: Optional[ConversationState] = Field(None, description="Updated conversation state")

class FeedbackRequest(BaseModel):
    """User feedback request model"""
    session_id: str = Field(..., description="Session identifier")
    question: str = Field(..., description="Feedback question")
    is_feedback: bool = Field(True, description="Whether this is a feedback request")
    image_data: Optional[bytes] = Field(None, description="Attached image data")

class ClarificationResponse(BaseModel):
    """User response to clarification question"""
    session_id: str = Field(..., description="Session identifier")
    clarification_answer: str = Field(..., description="User's answer to clarification")
    question_id: Optional[str] = Field(None, description="ID of the clarification question being answered")
