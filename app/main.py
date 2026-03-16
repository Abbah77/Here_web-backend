# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import uvicorn

from app.config import settings
from app.database import db
from app.api import auth, users, posts, friends, chat, notifications, search
from app.websocket.manager import websocket_manager
from app.websocket import ws_routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="HERE Social API",
    description="Backend API for HERE Social Network",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(posts.router, prefix="/api/posts", tags=["Posts"])
app.include_router(friends.router, prefix="/api/friends", tags=["Friends"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(ws_routes.router, prefix="/ws", tags=["WebSocket"])

@app.on_event("startup")
async def startup():
    """Initialize database connections on startup"""
    logger.info("Starting up...")
    await db.initialize()
    await websocket_manager.initialize()
    logger.info("Database connections established")

@app.on_event("shutdown")
async def shutdown():
    """Clean up connections on shutdown"""
    logger.info("Shutting down...")
    await db.close()
    await websocket_manager.close()
    logger.info("Connections closed")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to HERE Social API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    return {
        "status": "healthy",
        "database": "connected" if db.pg_pool else "disconnected"
    }

# This is critical for Render to detect the port
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=False  # Set to False for production
    )
