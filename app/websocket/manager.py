# app/websocket/manager.py
from fastapi import WebSocket
from typing import Dict, Set
import json
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_channels: Dict[str, str] = {}  # user_id -> channel
        self.user_status: Dict[str, bool] = {}   # user_id -> online status

    async def initialize(self):
        """Initialize manager"""
        logger.info("WebSocket manager initialized")

    async def connect(self, websocket: WebSocket, user_id: str, channel: str):
        """Connect user to a channel"""
        await websocket.accept()
        
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        
        self.active_connections[channel].add(websocket)
        self.user_channels[user_id] = channel
        self.user_status[user_id] = True
        
        # Broadcast online status
        await self.broadcast_presence(user_id, True)
        
        logger.info(f"User {user_id} connected to {channel}")

    def disconnect(self, websocket: WebSocket, user_id: str, channel: str):
        """Disconnect user"""
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
        
        if user_id in self.user_channels:
            del self.user_channels[user_id]
        
        self.user_status[user_id] = False
        
        logger.info(f"User {user_id} disconnected")

    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to specific user"""
        channel = self.user_channels.get(user_id)
        if not channel:
            return
        
        for connection in self.active_connections.get(channel, set()):
            try:
                await connection.send_json(message)
            except:
                pass

    async def broadcast_to_channel(self, channel: str, message: dict):
        """Broadcast to all users in a channel"""
        if channel not in self.active_connections:
            return
        
        disconnected = set()
        for connection in self.active_connections[channel]:
            try:
                await connection.send_json(message)
            except:
                disconnected.add(connection)
        
        # Clean up disconnected
        for conn in disconnected:
            self.active_connections[channel].discard(conn)

    async def broadcast_presence(self, user_id: str, is_online: bool):
        """Broadcast user presence to friends"""
        # Get user's friends
        # This would query the database
        message = {
            "type": "presence",
            "user_id": user_id,
            "status": "online" if is_online else "offline",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Broadcast to friends' channels
        # Simplified - you'd need to get friends' channels
        for channel in self.active_connections:
            await self.broadcast_to_channel(channel, message)

    async def send_typing_indicator(self, chat_id: str, user_id: str, is_typing: bool):
        """Send typing indicator"""
        message = {
            "type": "typing",
            "chat_id": chat_id,
            "user_id": user_id,
            "is_typing": is_typing
        }
        await self.broadcast_to_channel(f"chat_{chat_id}", message)

    async def send_new_message(self, chat_id: str, message: dict):
        """Send new message notification"""
        await self.broadcast_to_channel(f"chat_{chat_id}", {
            "type": "new_message",
            "chat_id": chat_id,
            "message": message
        })

    async def close(self):
        """Close all connections"""
        for channel in self.active_connections:
            for connection in self.active_connections[channel]:
                await connection.close()
        self.active_connections.clear()
        self.user_channels.clear()
        self.user_status.clear()

# Global instance
websocket_manager = ConnectionManager()
