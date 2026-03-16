# app/api/search.py
from fastapi import APIRouter, Depends
from typing import Optional

from app.database import db
from app.utils.auth import get_current_user

router = APIRouter()

@router.get("/")
async def search(
    q: str,
    type: Optional[str] = "all",  # all, users, posts, hashtags
    page: int = 1,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """Global search"""
    
    results = {}
    offset = (page - 1) * limit
    
    if type in ["all", "users"]:
        # Search users
        users = db.supabase.table("profiles")\
            .select("*")\
            .or_(f"full_name.ilike.%{q}%,username.ilike.%{q}%")\
            .range(offset, offset + limit - 1)\
            .execute()
        results["users"] = users.data
    
    if type in ["all", "posts"]:
        # Search posts
        posts = db.supabase.table("posts")\
            .select("*, user:profiles(*)")\
            .ilike("content", f"%{q}%")\
            .eq("privacy", "public")\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        # Add like status
        for post in posts.data:
            like = db.supabase.table("post_likes")\
                .select("*")\
                .eq("post_id", post["id"])\
                .eq("user_id", user["id"])\
                .execute()
            post["liked_by_user"] = len(like.data) > 0
        
        results["posts"] = posts.data
    
    if type in ["all", "hashtags"]:
        # Search hashtags
        hashtags = db.supabase.table("hashtags")\
            .select("*")\
            .ilike("name", f"%{q}%")\
            .order("post_count", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        results["hashtags"] = hashtags.data
    
    return results