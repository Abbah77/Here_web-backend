# app/websocket/ws_routes.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from jose import JWTError, jwt
from typing import Optional
import json

from app.config import settings
from app.websocket.manager import websocket_manager
from app.database import db

router = APIRouter()

async def get_user_from_token(token: str) -> Optional[str]:
    """Extract user ID from JWT token"""
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload.get("sub")
    except JWTError:
        return None

@router.websocket("/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str):
    """WebSocket endpoint for real-time communication"""
    
    # Get token from query params
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return
    
    # Authenticate user
    user_id = await get_user_from_token(token)
    if not user_id:
        await websocket.close(code=1008, reason="Invalid token")
        return
    
    # Connect
    await websocket_manager.connect(websocket, user_id, channel)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            msg_type = message.get("type")
            
            if msg_type == "message":
                # Handle chat message
                await handle_chat_message(user_id, message)
            elif msg_type == "typing":
                # Handle typing indicator
                await websocket_manager.send_typing_indicator(
                    message["chat_id"],
                    user_id,
                    message["is_typing"]
                )
            elif msg_type == "read":
                # Handle read receipt
                await handle_read_receipt(user_id, message)
            elif msg_type == "ping":
                # Keep alive
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, user_id, channel)
    except Exception as e:
        print(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket, user_id, channel)

async def handle_chat_message(user_id: str, message: dict):
    """Handle incoming chat message"""
    chat_id = message["chat_id"]
    content = message["content"]
    
    # Save to database
    msg_data = {
        "chat_id": chat_id,
        "user_id": user_id,
        "content": content,
        "type": message.get("media_type", "text"),
        "media_url": message.get("media_url"),
        "created_at": message.get("timestamp")
    }
    
    result = db.supabase.table("messages").insert(msg_data).execute()
    saved_message = result.data[0]
    
    # Send to all participants
    await websocket_manager.send_new_message(chat_id, saved_message)

async def handle_read_receipt(user_id: str, message: dict):
    """Handle read receipt"""
    chat_id = message["chat_id"]
    message_ids = message["message_ids"]
    
    # Update messages as read
    for msg_id in message_ids:
        # Get current read_by array
        msg = db.supabase.table("messages").select("read_by").eq("id", msg_id).execute()
        if msg.data:
            read_by = msg.data[0].get("read_by", [])
            if user_id not in read_by:
                read_by.append(user_id)
                db.supabase.table("messages").update({
                    "read_by": read_by
                }).eq("id", msg_id).execute()
    
    # Notify sender
    await websocket_manager.broadcast_to_channel(f"chat_{chat_id}", {
        "type": "read_receipt",
        "user_id": user_id,
        "message_ids": message_ids
    })