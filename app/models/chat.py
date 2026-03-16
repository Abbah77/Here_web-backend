# app/models/chat.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.user import UserProfile

class ChatBase(BaseModel):
    """Base chat model"""
    type: str  # private, group
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = None
    privacy: str = "public"  # public, private

class ChatCreate(ChatBase):
    """Chat creation model"""
    participant_ids: List[str] = Field(..., min_items=1)

class ChatUpdate(BaseModel):
    """Chat update model"""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = None
    privacy: Optional[str] = None

class ChatInDB(ChatBase):
    """Chat as stored in DB"""
    id: str
    created_by: str
    last_message_id: Optional[str] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class ChatParticipant(BaseModel):
    """Chat participant model"""
    id: str
    chat_id: str
    user_id: str
    user: UserProfile
    role: str  # admin, member
    joined_at: datetime
    last_read_at: datetime
    is_muted: bool = False

class Chat(ChatInDB):
    """Chat model with participants and last message"""
    participants: List[ChatParticipant]
    last_message: Optional['Message'] = None
    unread_count: int = 0
    other_user: Optional[UserProfile] = None  # For private chats
    
    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    """Base message model"""
    content: Optional[str] = Field(None, max_length=5000)
    type: str = "text"  # text, image, video, file, audio
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    media_size: Optional[int] = None

class MessageCreate(MessageBase):
    """Message creation model"""
    chat_id: str
    reply_to_id: Optional[str] = None

class MessageUpdate(BaseModel):
    """Message update model"""
    delivered_to: Optional[List[str]] = None
    read_by: Optional[List[str]] = None

class Message(MessageBase):
    """Message model"""
    id: str
    chat_id: str
    user_id: str
    user: UserProfile
    reply_to_id: Optional[str] = None
    reply_to: Optional['Message'] = None
    delivered_to: List[str] = []
    read_by: List[str] = []
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class MessageStatus(BaseModel):
    """Message status update model"""
    message_id: str
    status: str  # sent, delivered, seen
    timestamp: datetime

class TypingIndicator(BaseModel):
    """Typing indicator model"""
    chat_id: str
    user_id: str
    is_typing: bool

class ReadReceipt(BaseModel):
    """Read receipt model"""
    chat_id: str
    user_id: str
    message_ids: List[str]
    timestamp: datetime
