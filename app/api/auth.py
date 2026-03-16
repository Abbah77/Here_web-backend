# app/api/auth.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, EmailStr
from datetime import datetime
import uuid

from app.database import db
from app.utils.auth import create_access_token

router = APIRouter()

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    username: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister, background_tasks: BackgroundTasks):
    """Register a new user"""
    
    # Check if user exists
    existing = db.supabase.table("profiles").select("*").eq("email", user_data.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    existing_username = db.supabase.table("profiles").select("*").eq("username", user_data.username).execute()
    if existing_username.data:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Create user in Supabase Auth
    auth_response = db.supabase.auth.sign_up({
        "email": user_data.email,
        "password": user_data.password,
    })
    
    if not auth_response.user:
        raise HTTPException(status_code=400, detail="Registration failed")
    
    # Create profile
    user_id = auth_response.user.id
    profile_data = {
        "id": user_id,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "username": user_data.username,
        "avatar_url": "https://your-storage/avatars/default.png",
        "created_at": datetime.utcnow().isoformat()
    }
    
    db.supabase.table("profiles").insert(profile_data).execute()
    
    # Create access token
    access_token = create_access_token(data={"sub": user_id})
    
    # Remove sensitive data
    profile_data.pop("id", None)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": profile_data
    }

@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    """Login user"""
    
    try:
        # Authenticate with Supabase
        auth_response = db.supabase.auth.sign_in_with_password({
            "email": login_data.email,
            "password": login_data.password,
        })
        
        # Get user profile
        profile = db.supabase.table("profiles").select("*").eq("id", auth_response.user.id).execute()
        
        if not profile.data:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        user_data = profile.data[0]
        
        # Update last login
        db.supabase.table("profiles").update({
            "last_seen": datetime.utcnow().isoformat(),
            "is_online": True
        }).eq("id", auth_response.user.id).execute()
        
        # Create access token (long expiry for "forever login")
        access_token = create_access_token(
            data={"sub": auth_response.user.id},
            expires_delta=timedelta(days=30)  # 30 days "forever login"
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    """Logout user"""
    
    # Update online status
    db.supabase.table("profiles").update({
        "is_online": False,
        "last_seen": datetime.utcnow().isoformat()
    }).eq("id", user["id"]).execute()
    
    # Invalidate token (client should discard it)
    return {"message": "Logged out successfully"}

@router.post("/refresh")
async def refresh_token(user: dict = Depends(get_current_user)):
    """Refresh access token"""
    
    new_token = create_access_token(data={"sub": user["id"]})
    
    return {
        "access_token": new_token,
        "token_type": "bearer"
    }
