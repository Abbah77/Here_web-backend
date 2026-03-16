# app/models/post.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.user import UserProfile

class PostBase(BaseModel):
    """Base post model"""
    content: Optional[str] = Field(None, max_length=5000)
    privacy: str = "public"  # public, friends, private
    media_urls: List[str] = []

class PostCreate(PostBase):
    """Post creation model"""
    pass

class PostUpdate(BaseModel):
    """Post update model"""
    content: Optional[str] = Field(None, max_length=5000)
    privacy: Optional[str] = None

class PostInDB(PostBase):
    """Post as stored in DB"""
    id: str
    user_id: str
    likes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime

class Post(PostInDB):
    """Post model with user data"""
    user: UserProfile
    liked_by_user: bool = False
    
    class Config:
        from_attributes = True

class PostLike(BaseModel):
    """Post like model"""
    id: str
    post_id: str
    user_id: str
    created_at: datetime

class CommentBase(BaseModel):
    """Base comment model"""
    content: str = Field(..., min_length=1, max_length=1000)

class CommentCreate(CommentBase):
    """Comment creation model"""
    parent_id: Optional[str] = None

class Comment(CommentBase):
    """Comment model"""
    id: str
    post_id: str
    user_id: str
    user: UserProfile
    parent_id: Optional[str] = None
    likes_count: int = 0
    replies: List['Comment'] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CommentLike(BaseModel):
    """Comment like model"""
    id: str
    comment_id: str
    user_id: str
    created_at: datetime

class PostFeed(BaseModel):
    """Feed response model"""
    posts: List[Post]
    page: int
    has_more: bool
    total: Optional[int] = None