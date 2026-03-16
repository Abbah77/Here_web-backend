# app/api/chat.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

from app.database import db
from app.utils.auth import get_current_user

router = APIRouter()

class ChatCreate(BaseModel):
    type: str  # 'private' or 'group'
    name: Optional[str] = None
    participant_ids: List[str]

class MessageSend(BaseModel):
    chat_id: str
    content: str
    type: str = "text"
    media_url: Optional[str] = None
    reply_to_id: Optional[str] = None

@router.post("/chats")
async def create_chat(
    chat_data: ChatCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new chat"""
    
    chat_id = str(uuid.uuid4())
    
    chat = {
        "id": chat_id,
        "type": chat_data.type,
        "name": chat_data.name,
        "created_by": user["id"],
        "created_at": datetime.utcnow().isoformat()
    }
    
    db.supabase.table("chats").insert(chat).execute()
    
    # Add participants
    participants = [user["id"]] + chat_data.participant_ids
    for participant_id in participants:
        db.supabase.table("chat_participants").insert({
            "chat_id": chat_id,
            "user_id": participant_id,
            "role": "admin" if participant_id == user["id"] else "member"
        }).execute()
    
    return {"id": chat_id, **chat}

@router.get("/chats")
async def get_chats(user: dict = Depends(get_current_user)):
    """Get user's chats"""
    
    chats = db.supabase.table("chat_participants")\
        .select("chat:chats(*, last_message:messages(*), participants:chat_participants(user:profiles(*)))")\
        .eq("user_id", user["id"])\
        .order("chat.last_message_at", desc=True)\
        .execute()
    
    # Format response
    result = []
    for item in chats.data:
        chat_data = item["chat"]
        
        # Get other participant for private chats
        if chat_data["type"] == "private":
            other = next(
                (p["user"] for p in chat_data["participants"] 
                 if p["user"]["id"] != user["id"]),
                None
            )
            chat_data["other_user"] = other
        
        # Get unread count
        unread = db.supabase.table("messages")\
            .select("*", count="exact")\
            .eq("chat_id", chat_data["id"])\
            .not_.contains("read_by", [user["id"]])\
            .execute()
        
        chat_data["unread_count"] = unread.count
        
        result.append(chat_data)
    
    return result

@router.get("/chats/{chat_id}/messages")
async def get_messages(
    chat_id: str,
    page: int = 1,
    limit: int = 50,
    user: dict = Depends(get_current_user)
):
    """Get messages from a chat"""
    
    # Check if user is participant
    participant = db.supabase.table("chat_participants")\
        .select("*")\
        .eq("chat_id", chat_id)\
        .eq("user_id", user["id"])\
        .execute()
    
    if not participant.data:
        raise HTTPException(status_code=403, detail="Not a participant in this chat")
    
    offset = (page - 1) * limit
    
    messages = db.supabase.table("messages")\
        .select("*, user:profiles(*)")\
        .eq("chat_id", chat_id)\
        .order("created_at", desc=True)\
        .range(offset, offset + limit - 1)\
        .execute()
    
    # Mark as delivered
    for msg in messages.data:
        if user["id"] not in msg.get("delivered_to", []):
            delivered = msg.get("delivered_to", [])
            delivered.append(user["id"])
            db.supabase.table("messages").update({
                "delivered_to": delivered
            }).eq("id", msg["id"]).execute()
    
    return {
        "messages": messages.data[::-1],  # Return in chronological order
        "page": page,
        "has_more": len(messages.data) == limit
    }

@router.post("/messages")
async def send_message(
    message_data: MessageSend,
    user: dict = Depends(get_current_user)
):
    """Send a message"""
    
    # Check if user is participant
    participant = db.supabase.table("chat_participants")\
        .select("*")\
        .eq("chat_id", message_data.chat_id)\
        .eq("user_id", user["id"])\
        .execute()
    
    if not participant.data:
        raise HTTPException(status_code=403, detail="Not a participant in this chat")
    
    message_id = str(uuid.uuid4())
    
    message = {
        "id": message_id,
        "chat_id": message_data.chat_id,
        "user_id": user["id"],
        "content": message_data.content,
        "type": message_data.type,
        "media_url": message_data.media_url,
        "reply_to_id": message_data.reply_to_id,
        "delivered_to": [user["id"]],  # Mark as delivered to sender
        "read_by": [],
        "created_at": datetime.utcnow().isoformat()
    }
    
    db.supabase.table("messages").insert(message).execute()
    
    # Add user data
    message["user"] = user
    
    return message

@router.post("/messages/{message_id}/read")
async def mark_as_read(
    message_id: str,
    user: dict = Depends(get_current_user)
):
    """Mark message as read"""
    
    # Get message
    message = db.supabase.table("messages").select("*").eq("id", message_id).execute()
    if not message.data:
        raise HTTPException(status_code=404, detail="Message not found")
    
    message_data = message.data[0]
    
    # Update read_by
    read_by = message_data.get("read_by", [])
    if user["id"] not in read_by:
        read_by.append(user["id"])
        db.supabase.table("messages").update({
            "read_by": read_by
        }).eq("id", message_id).execute()
    
    return {"status": "marked as read"}