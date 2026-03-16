# app/models/notification.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.user import UserProfile

class NotificationBase(BaseModel):
    """Base notification model"""
    type: str = Field(..., pattern="^(friend_request|friend_accept|new_message|post_like|post_comment|comment_like|mention)$")
    content: Optional[str] = Field(None, max_length=500)

class NotificationCreate(NotificationBase):
    """Notification creation model"""
    user_id: str
    actor_id: Optional[str] = None
    post_id: Optional[str] = None
    comment_id: Optional[str] = None
    chat_id: Optional[str] = None
    message_id: Optional[str] = None

class Notification(NotificationBase):
    """Notification model"""
    id: str
    user_id: str
    actor: Optional[UserProfile] = None
    post_id: Optional[str] = None
    comment_id: Optional[str] = None
    chat_id: Optional[str] = None
    message_id: Optional[str] = None
    is_read: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True

class NotificationList(BaseModel):
    """Notification list response"""
    notifications: List[Notification]
    page: int
    has_more: bool
    unread_count: int

class NotificationCount(BaseModel):
    """Unread notification count"""
    count: int