# app/api/friends.py
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
import uuid

from app.database import db
from app.utils.auth import get_current_user
from app.api.notifications import create_notification

router = APIRouter()

class FriendRequest(BaseModel):
    friend_id: str

@router.post("/requests")
async def send_friend_request(
    request_data: FriendRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Send friend request"""
    
    if user["id"] == request_data.friend_id:
        return {"error": "Cannot add yourself"}, 400
    
    # Check if already friends or pending
    existing = db.supabase.table("friendships")\
        .select("*")\
        .or_(
            f"and(user_id.eq.{user['id']},friend_id.eq.{request_data.friend_id}),"
            f"and(user_id.eq.{request_data.friend_id},friend_id.eq.{user['id']})"
        )\
        .execute()
    
    if existing.data:
        return {"error": "Friend request already exists"}, 400
    
    # Create request
    friendship = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "friend_id": request_data.friend_id,
        "status": "pending",
        "action_user_id": user["id"],
        "created_at": datetime.utcnow().isoformat()
    }
    
    db.supabase.table("friendships").insert(friendship).execute()
    
    # Create notification
    background_tasks.add_task(
        create_notification,
        user_id=request_data.friend_id,
        type="friend_request",
        actor_id=user["id"]
    )
    
    return {"message": "Friend request sent"}

@router.put("/requests/{request_id}/accept")
async def accept_friend_request(
    request_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Accept friend request"""
    
    # Get request
    request = db.supabase.table("friendships")\
        .select("*")\
        .eq("id", request_id)\
        .eq("friend_id", user["id"])\
        .eq("status", "pending")\
        .execute()
    
    if not request.data:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Update status
    db.supabase.table("friendships")\
        .update({"status": "accepted", "updated_at": datetime.utcnow().isoformat()})\
        .eq("id", request_id)\
        .execute()
    
    # Create notification for requester
    background_tasks.add_task(
        create_notification,
        user_id=request.data[0]["user_id"],
        type="friend_accept",
        actor_id=user["id"]
    )
    
    return {"message": "Friend request accepted"}

@router.delete("/requests/{request_id}")
async def decline_friend_request(
    request_id: str,
    user: dict = Depends(get_current_user)
):
    """Decline or cancel friend request"""
    
    # Check if user is involved
    request = db.supabase.table("friendships")\
        .select("*")\
        .eq("id", request_id)\
        .or_(f"user_id.eq.{user['id']},friend_id.eq.{user['id']}")\
        .execute()
    
    if not request.data:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Delete
    db.supabase.table("friendships").delete().eq("id", request_id).execute()
    
    return {"message": "Request declined"}

@router.delete("/{friend_id}")
async def remove_friend(
    friend_id: str,
    user: dict = Depends(get_current_user)
):
    """Remove friend"""
    
    # Delete friendship in both directions
    db.supabase.table("friendships")\
        .delete()\
        .or_(
            f"and(user_id.eq.{user['id']},friend_id.eq.{friend_id}),"
            f"and(user_id.eq.{friend_id},friend_id.eq.{user['id']})"
        )\
        .execute()
    
    return {"message": "Friend removed"}