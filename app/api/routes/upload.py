import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from app.core.auth import get_current_user_token
from app.models.user import TokenData
from pathlib import Path
import shutil
from typing import Optional

router = APIRouter()

# Create upload directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
AVATAR_DIR = UPLOAD_DIR / "avatars"
AVATAR_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user_token: TokenData = Depends(get_current_user_token)
):
    """Upload user avatar image."""
    try:
        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Check file size
        file_content = await file.read()
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail="File size too large. Maximum size is 5MB"
            )
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = f"{file_id}{file_ext}"
        file_path = AVATAR_DIR / filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # Return the full URL to access the file
        from app.core.config import settings
        
        # Get base URL - use environment or construct from host info
        base_url = getattr(settings, 'BASE_URL', None)
        if not base_url:
            # Fallback: construct from API settings
            api_host = settings.API_HOST_UPLOAD if settings.API_HOST_UPLOAD != "0.0.0.0" else "localhost"
            api_port = settings.API_PORT
            base_url = f"http://{api_host}:{api_port}"
        
        # avatar_url = f"http://26.208.148.9:8000/api/v1/upload/avatar/{filename}"
        avatar_url = f"{base_url}/api/v1/upload/avatar/{filename}"
        return {
            "success": True,
            "avatar_url": avatar_url,
            "filename": filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file: {str(e)}"
        )

@router.get("/avatar/{filename}")
async def get_avatar(filename: str):
    """Serve avatar image file."""
    try:
        file_path = AVATAR_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=file_path,
            media_type="image/*",
            headers={"Cache-Control": "public, max-age=3600"}  # Cache for 1 hour
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to serve file: {str(e)}"
        )

@router.delete("/avatar/{filename}")
async def delete_avatar(
    filename: str,
    current_user_token: TokenData = Depends(get_current_user_token)
):
    """Delete avatar file."""
    try:
        file_path = AVATAR_DIR / filename
        
        if file_path.exists():
            os.remove(file_path)
        
        return {"success": True, "message": "File deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete file: {str(e)}"
        )