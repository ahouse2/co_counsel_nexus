"""
API Endpoints for Video Generation

Provides REST API for generating and managing legal concept videos.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from pathlib import Path

from ..services.video_generation_service import (
    VideoGenerationService,
    get_video_generation_service
)
from ..security.dependencies import authorize_content_access
from ..security.authz import Principal


router = APIRouter(prefix="/video-generation", tags=["Video Generation"])


class GenerateVideoRequest(BaseModel):
    concept: str = Field(..., description="Legal concept (discovery_process, burden_of_proof, hearsay_exceptions)")
    script: Optional[List[Dict[str, str]]] = Field(default=None, description="Optional custom script")


class VideoResponse(BaseModel):
    success: bool
    video_id: Optional[str] = None
    concept: Optional[str] = None
    frames: Optional[List[str]] = None
    metadata_path: Optional[str] = None
    error: Optional[str] = None


@router.post("/generate", response_model=VideoResponse)
async def generate_video(
    request: GenerateVideoRequest,
    _principal: Principal = Depends(authorize_content_access),
    service: VideoGenerationService = Depends(get_video_generation_service)
):
    """
    Generate a legal concept video.
    
    Available concepts:
    - discovery_process
    - burden_of_proof
    - hearsay_exceptions
    
    Or provide custom script.
    """
    result = await service.generate_concept_video(
        concept=request.concept,
        script=request.script
    )
    
    if not result.get('success'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get('error', 'Video generation failed')
        )
    
    return VideoResponse(**result)


@router.get("/videos", response_model=List[Dict[str, Any]])
async def list_videos(
    _principal: Principal = Depends(authorize_content_access),
    service: VideoGenerationService = Depends(get_video_generation_service)
):
    """List all generated videos."""
    return service.list_generated_videos()


@router.get("/frames/{concept}/{frame_name}")
async def get_frame(
    concept: str,
    frame_name: str,
    _principal: Principal = Depends(authorize_content_access),
    service: VideoGenerationService = Depends(get_video_generation_service)
):
    """Get a specific video frame image."""
    frame_path = service.output_dir / concept / frame_name
    
    if not frame_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Frame not found: {frame_name}"
        )
    
    return FileResponse(frame_path, media_type="image/png")
