# app/api/notifications.py
from fastapi import APIRouter, Depends, BackgroundTasks
from datetime import datetime
import uuid

from app.database import db
from app.utils.auth import get_current_user

router = APIRouter()

async def create_notification(
    user_id: str,
    type: str,
    actor_id: str = None,
    post_id: str = None,
    comment_id: str = None,
    chat_id: str = None,
    message_id: str = None,
    content: str = None
):
    """Create a notification"""
    
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": type,
        "actor_id": actor_id,
        "post_id": post_id,
        "comment_id": comment_id,
        "chat_id": chat_id,
        "message_id": message_id,
        "content": content,
        "created_at": datetime.utcnow().isoformat(),
        "is_read": False
    }
    
    db.supabase.table("notifications").insert(notification).execute()

@router.get("/")
async def get_notifications(
    page: int = 1,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """Get user notifications"""
    
    offset = (page - 1) * limit
    
    notifications = db.supabase.table("notifications")\
        .select("*, actor:profiles!notifications_actor_id_fkey(*)")\
        .eq("user_id", user["id"])\
        .order("created_at", desc=True)\
        .range(offset, offset + limit - 1)\
        .execute()
    
    return {
        "notifications": notifications.data,
        "page": page,
        "has_more": len(notifications.data) == limit
    }

@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user: dict = Depends(get_current_user)
):
    """Mark notification as read"""
    
    db.supabase.table("notifications")\
        .update({"is_read": True})\
        .eq("id", notification_id)\
        .eq("user_id", user["id"])\
        .execute()
    
    return {"status": "marked as read"}

@router.put("/read-all")
async def mark_all_read(user: dict = Depends(get_current_user)):
    """Mark all notifications as read"""
    
    db.supabase.table("notifications")\
        .update({"is_read": True})\
        .eq("user_id", user["id"])\
        .eq("is_read", False)\
        .execute()
    
    return {"status": "all marked as read"}

@router.get("/unread-count")
async def get_unread_count(user: dict = Depends(get_current_user)):
    """Get unread notifications count"""
    
    result = db.supabase.table("notifications")\
        .select("*", count="exact")\
        .eq("user_id", user["id"])\
        .eq("is_read", False)\
        .execute()
    
    return {"count": result.count}