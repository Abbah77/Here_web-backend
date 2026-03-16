# app/models/user.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, List
from datetime import datetime
import uuid

class UserBase(BaseModel):
    """Base user model"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=30, pattern="^[a-zA-Z0-9_]+$")
    full_name: str = Field(..., min_length=1, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = None
    cover_url: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    birthday: Optional[str] = None

class UserCreate(UserBase):
    """User creation model"""
    password: str = Field(..., min_length=6)

class UserUpdate(BaseModel):
    """User update model"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    username: Optional[str] = Field(None, min_length=3, max_length=30, pattern="^[a-zA-Z0-9_]+$")
    bio: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    birthday: Optional[str] = None
    privacy_settings: Optional[Dict] = None
    notification_settings: Optional[Dict] = None

class UserProfile(UserBase):
    """User profile model (response)"""
    id: str
    last_seen: datetime
    is_online: bool
    friends_count: int = 0
    posts_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UserInDB(UserProfile):
    """User as stored in DB (includes settings)"""
    privacy_settings: Dict = {
        "profile_visibility": "public",
        "online_status": True,
        "read_receipts": True
    }
    notification_settings: Dict = {
        "messages": True,
        "friend_requests": True,
        "likes": True,
        "comments": True,
        "mentions": True
    }
    hashed_password: str

class UserFriend(BaseModel):
    """Friend relationship model"""
    friendship_id: str
    user: UserProfile
    friend: UserProfile
    status: str  # pending, accepted, blocked
    created_at: datetime
    updated_at: datetime

class UserSearchResult(BaseModel):
    """User search result"""
    id: str
    username: str
    full_name: str
    avatar_url: Optional[str]
    bio: Optional[str]
    is_friend: bool = False
    has_pending_request: bool = False