# app/api/users.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

from app.database import db
from app.utils.auth import get_current_user
from app.services.storage import upload_file

router = APIRouter()

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    birthday: Optional[str] = None

@router.get("/profile")
async def get_my_profile(user: dict = Depends(get_current_user)):
    """Get current user's profile"""
    return user

@router.get("/{user_id}")
async def get_user_profile(user_id: str):
    """Get user profile by ID"""
    
    user = db.supabase.table("profiles")\
        .select("*")\
        .eq("id", user_id)\
        .execute()
    
    if not user.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user.data[0]

@router.put("/profile")
async def update_profile(
    profile_data: ProfileUpdate,
    user: dict = Depends(get_current_user)
):
    """Update user profile"""
    
    # Check username availability
    if profile_data.username and profile_data.username != user["username"]:
        existing = db.supabase.table("profiles")\
            .select("*")\
            .eq("username", profile_data.username)\
            .execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Username already taken")
    
    # Update only provided fields
    updates = {k: v for k, v in profile_data.dict().items() if v is not None}
    
    if updates:
        db.supabase.table("profiles")\
            .update(updates)\
            .eq("id", user["id"])\
            .execute()
    
    # Get updated profile
    updated = db.supabase.table("profiles")\
        .select("*")\
        .eq("id", user["id"])\
        .execute()
    
    return updated.data[0]

@router.post("/profile/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """Upload profile avatar"""
    
    # Upload file
    file_url = await upload_file(file, folder="avatars")
    
    # Update user profile
    db.supabase.table("profiles")\
        .update({"avatar_url": file_url})\
        .eq("id", user["id"])\
        .execute()
    
    return {"avatar_url": file_url}

@router.get("/search")
async def search_users(
    q: str,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """Search users by name or username"""
    
    results = db.supabase.table("profiles")\
        .select("*")\
        .or_(f"full_name.ilike.%{q}%,username.ilike.%{q}%")\
        .limit(limit)\
        .execute()
    
    return results.data

@router.get("/{user_id}/friends")
async def get_user_friends(
    user_id: str,
    status: str = "accepted",
    user: dict = Depends(get_current_user)
):
    """Get user's friends"""
    
    friends = db.supabase.table("friendships")\
        .select("friend:profiles!friendships_friend_id_fkey(*)")\
        .eq("user_id", user_id)\
        .eq("status", status)\
        .execute()
    
    return [f["friend"] for f in friends.data]