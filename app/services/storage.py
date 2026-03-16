# app/services/storage.py
from fastapi import UploadFile, HTTPException
import uuid
import os
from datetime import datetime
from PIL import Image
import io
from typing import Optional, Tuple
import logging

from app.config import settings
from app.services.supabase import supabase_client

logger = logging.getLogger(__name__)

# File type constants
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"}
ALLOWED_AUDIO_TYPES = {"audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4"}
ALLOWED_DOCUMENT_TYPES = {"application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}

# Size limits
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB
MAX_AUDIO_SIZE = 50 * 1024 * 1024   # 50MB
MAX_DOCUMENT_SIZE = 20 * 1024 * 1024 # 20MB

class StorageService:
    """File storage service"""
    
    def __init__(self):
        self.supabase = supabase_client

    async def validate_file(self, file: UploadFile) -> Tuple[bool, str]:
        """Validate file type and size"""
        
        # Get file size
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        
        content_type = file.content_type
        
        # Check by type
        if content_type in ALLOWED_IMAGE_TYPES:
            if size > MAX_IMAGE_SIZE:
                return False, f"Image too large. Max size: {MAX_IMAGE_SIZE/1024/1024}MB"
        elif content_type in ALLOWED_VIDEO_TYPES:
            if size > MAX_VIDEO_SIZE:
                return False, f"Video too large. Max size: {MAX_VIDEO_SIZE/1024/1024}MB"
        elif content_type in ALLOWED_AUDIO_TYPES:
            if size > MAX_AUDIO_SIZE:
                return False, f"Audio too large. Max size: {MAX_AUDIO_SIZE/1024/1024}MB"
        elif content_type in ALLOWED_DOCUMENT_TYPES:
            if size > MAX_DOCUMENT_SIZE:
                return False, f"Document too large. Max size: {MAX_DOCUMENT_SIZE/1024/1024}MB"
        else:
            return False, f"File type {content_type} not allowed"
        
        return True, ""

    async def compress_image(self, file: UploadFile, max_size: Tuple[int, int] = (1080, 1080)) -> bytes:
        """Compress image"""
        try:
            contents = await file.read()
            img = Image.open(io.BytesIO(contents))
            
            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img
            
            # Resize if larger than max_size
            if img.width > max_size[0] or img.height > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save compressed
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Image compression failed: {e}")
            # Return original if compression fails
            await file.seek(0)
            return await file.read()

    async def generate_thumbnail(self, file: UploadFile, size: Tuple[int, int] = (300, 300)) -> Optional[bytes]:
        """Generate thumbnail from image"""
        try:
            contents = await file.read()
            img = Image.open(io.BytesIO(contents))
            
            # Convert RGBA to RGB
            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img
            
            # Create thumbnail
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=70, optimize=True)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Thumbnail generation failed: {e}")
            return None

    # 🔴 THIS IS THE MISSING FUNCTION 🔴
    async def upload_file(
        self, 
        file: UploadFile, 
        folder: str = "general",
        compress: bool = True,
        generate_thumbnail: bool = False
    ) -> dict:
        """Upload file to storage"""
        
        # Validate
        valid, error = await self.validate_file(file)
        if not valid:
            raise HTTPException(status_code=400, detail=error)
        
        # Generate filename
        original_filename = file.filename
        ext = os.path.splitext(original_filename)[1]
        filename = f"{uuid.uuid4()}{ext}"
        
        # Create path with date folders
        date_path = datetime.now().strftime('%Y/%m/%d')
        path = f"{folder}/{date_path}/{filename}"
        
        # Read and process file
        contents = await file.read()
        
        # Compress if image and requested
        if file.content_type in ALLOWED_IMAGE_TYPES and compress:
            contents = await self.compress_image(file)
        
        # Upload to Supabase
        try:
            result = await self.supabase.upload_file(
                settings.STORAGE_BUCKET,
                path,
                contents,
                file.content_type
            )
            
            # Get public URL
            public_url = await self.supabase.get_public_url(settings.STORAGE_BUCKET, path)
            
            response = {
                "url": public_url,
                "path": path,
                "filename": original_filename,
                "size": len(contents),
                "mime_type": file.content_type
            }
            
            # Generate thumbnail if requested
            if generate_thumbnail and file.content_type in ALLOWED_IMAGE_TYPES:
                await file.seek(0)
                thumbnail_data = await self.generate_thumbnail(file)
                if thumbnail_data:
                    thumb_filename = f"thumb_{uuid.uuid4()}.jpg"
                    thumb_path = f"{folder}/{date_path}/thumbnails/{thumb_filename}"
                    
                    await self.supabase.upload_file(
                        settings.STORAGE_BUCKET,
                        thumb_path,
                        thumbnail_data,
                        "image/jpeg"
                    )
                    
                    thumb_url = await self.supabase.get_public_url(settings.STORAGE_BUCKET, thumb_path)
                    response["thumbnail_url"] = thumb_url
            
            return response
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    async def delete_file(self, file_url: str) -> bool:
        """Delete file from storage"""
        try:
            # Extract path from URL
            # URL format: https://{project}.supabase.co/storage/v1/object/public/{bucket}/{path}
            parts = file_url.split(f"{settings.STORAGE_BUCKET}/")
            if len(parts) < 2:
                return False
            
            path = parts[1]
            
            await self.supabase.delete_file(settings.STORAGE_BUCKET, path)
            return True
            
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False

    async def get_file_info(self, file_url: str) -> Optional[dict]:
        """Get file information"""
        try:
            # Extract path
            parts = file_url.split(f"{settings.STORAGE_BUCKET}/")
            if len(parts) < 2:
                return None
            
            path = parts[1]
            
            # Get file info from Supabase
            # Note: Supabase doesn't have a direct API for file info
            # This is a placeholder - you might need to store metadata in DB
            return {
                "url": file_url,
                "path": path,
                "bucket": settings.STORAGE_BUCKET
            }
            
        except Exception as e:
            logger.error(f"Get file info failed: {e}")
            return None

# Create global instance
storage_service = StorageService()

# 🔴 EXPOSE THE FUNCTION FOR DIRECT IMPORT 🔴
# This allows: from app.services.storage import upload_file
async def upload_file(file: UploadFile, folder: str = "general", compress: bool = True, generate_thumbnail: bool = False) -> dict:
    """Convenience function for uploading files"""
    return await storage_service.upload_file(file, folder, compress, generate_thumbnail)

async def delete_file(file_url: str) -> bool:
    """Convenience function for deleting files"""
    return await storage_service.delete_file(file_url)
