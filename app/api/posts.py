# app/api/posts.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

from app.database import db
from app.utils.auth import get_current_user
from app.services.storage import upload_file

router = APIRouter()

class PostCreate(BaseModel):
    content: str
    privacy: str = "public"

class PostResponse(BaseModel):
    id: str
    user_id: str
    content: str
    media_urls: List[str]
    likes_count: int
    comments_count: int
    created_at: str
    user: dict

@router.post("/", response_model=PostResponse)
async def create_post(
    post_data: PostCreate,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Create a new post"""
    
    post_id = str(uuid.uuid4())
    
    post = {
        "id": post_id,
        "user_id": user["id"],
        "content": post_data.content,
        "privacy": post_data.privacy,
        "media_urls": [],
        "likes_count": 0,
        "comments_count": 0,
        "created_at": datetime.utcnow().isoformat()
    }
    
    db.supabase.table("posts").insert(post).execute()
    
    # Extract hashtags
    hashtags = [word[1:] for word in post_data.content.split() if word.startswith('#')]
    if hashtags:
        background_tasks.add_task(process_hashtags, post_id, hashtags)
    
    # Get user data
    post["user"] = user
    
    return post

@router.post("/{post_id}/media")
async def upload_post_media(
    post_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """Upload media for a post"""
    
    # Verify post ownership
    post = db.supabase.table("posts").select("*").eq("id", post_id).eq("user_id", user["id"]).execute()
    if not post.data:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Upload file
    file_url = await upload_file(file, folder="posts")
    
    # Update post with media
    current_media = post.data[0].get("media_urls", [])
    current_media.append(file_url)
    
    db.supabase.table("posts").update({
        "media_urls": current_media
    }).eq("id", post_id).execute()
    
    return {"url": file_url}

@router.get("/feed")
async def get_feed(
    page: int = 1,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """Get user's feed"""
    
    offset = (page - 1) * limit
    
    # Get posts from user and friends
    # This is a simplified version - you'd want a more sophisticated algorithm
    posts = db.supabase.table("posts")\
        .select("*, user:profiles!inner(*)")\
        .eq("privacy", "public")\
        .order("created_at", desc=True)\
        .range(offset, offset + limit - 1)\
        .execute()
    
    # Check if user liked each post
    for post in posts.data:
        like = db.supabase.table("post_likes")\
            .select("*")\
            .eq("post_id", post["id"])\
            .eq("user_id", user["id"])\
            .execute()
        post["liked_by_user"] = len(like.data) > 0
    
    return {
        "posts": posts.data,
        "page": page,
        "has_more": len(posts.data) == limit
    }

@router.get("/{post_id}")
async def get_post(
    post_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a single post"""
    
    post = db.supabase.table("posts")\
        .select("*, user:profiles(*), comments:comments(*, user:profiles(*))")\
        .eq("id", post_id)\
        .execute()
    
    if not post.data:
        raise HTTPException(status_code=404, detail="Post not found")
    
    post_data = post.data[0]
    
    # Check if user liked
    like = db.supabase.table("post_likes")\
        .select("*")\
        .eq("post_id", post_id)\
        .eq("user_id", user["id"])\
        .execute()
    post_data["liked_by_user"] = len(like.data) > 0
    
    return post_data

@router.post("/{post_id}/like")
async def like_post(
    post_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Like a post"""
    
    # Check if already liked
    existing = db.supabase.table("post_likes")\
        .select("*")\
        .eq("post_id", post_id)\
        .eq("user_id", user["id"])\
        .execute()
    
    if existing.data:
        # Unlike
        db.supabase.table("post_likes")\
            .delete()\
            .eq("post_id", post_id)\
            .eq("user_id", user["id"])\
            .execute()
        return {"liked": False}
    else:
        # Like
        db.supabase.table("post_likes").insert({
            "post_id": post_id,
            "user_id": user["id"]
        }).execute()
        
        # Create notification
        post = db.supabase.table("posts").select("user_id").eq("id", post_id).execute()
        if post.data and post.data[0]["user_id"] != user["id"]:
            background_tasks.add_task(
                create_notification,
                user_id=post.data[0]["user_id"],
                type="post_like",
                actor_id=user["id"],
                post_id=post_id
            )
        
        return {"liked": True}

# Helper functions
async def process_hashtags(post_id: str, hashtags: List[str]):
    """Process hashtags for a post"""
    for tag in hashtags:
        # Get or create hashtag
        hashtag = db.supabase.table("hashtags")\
            .select("*")\
            .eq("name", tag.lower())\
            .execute()
        
        if hashtag.data:
            hashtag_id = hashtag.data[0]["id"]
            # Update count
            db.supabase.table("hashtags").update({
                "post_count": hashtag.data[0]["post_count"] + 1,
                "last_used_at": datetime.utcnow().isoformat()
            }).eq("id", hashtag_id).execute()
        else:
            # Create new hashtag
            new = db.supabase.table("hashtags").insert({
                "name": tag.lower(),
                "post_count": 1
            }).execute()
            hashtag_id = new.data[0]["id"]
        
        # Link to post
        db.supabase.table("post_hashtags").insert({
            "post_id": post_id,
            "hashtag_id": hashtag_id
        }).execute()

async def create_notification(user_id: str, type: str, **kwargs):
    """Create a notification"""
    notification = {
        "user_id": user_id,
        "type": type,
        "created_at": datetime.utcnow().isoformat(),
        "is_read": False,
        **kwargs
    }
    db.supabase.table("notifications").insert(notification).execute()