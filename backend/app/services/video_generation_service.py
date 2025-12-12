"""
Video Generation Service for Legal Concepts

Generates educational videos for legal concepts using text-to-video and animation.
Uses a pragmatic approach with static frames + voiceover for MVP.

For Phase 4, we'll generate simple, effective educational videos without
requiring complex animation libraries like Manim.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from ..config import get_settings
from ..utils.audit import AuditEvent, get_audit_trail


class VideoGenerationService:
    """
    Generates educational videos for legal concepts.
    
    Approach:
    - Generate static frames with text/diagrams
    - Combine frames into video slideshow
    - Add text-to-speech narration (future enhancement)
    
    For MVP: Creates image sequences that can be displayed as slideshows
    in Trial University.
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.settings = get_settings()
        self.output_dir = output_dir or Path("generated_videos")
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.audit = get_audit_trail()
    
    async def generate_concept_video(
        self,
        concept: str,
        script: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Generate a video for a legal concept.
        
        Args:
            concept: Legal concept name (e.g., "discovery_process", "burden_of_proof")
            script: Optional list of scenes with {"title": str, "content": str}
        
        Returns:
            Dict with video metadata and frame paths
        """
        if not PIL_AVAILABLE:
            return {
                'error': 'PIL not available - cannot generate videos',
                'success': False
            }
        
        # Use predefined scripts or custom script
        if script is None:
            script = self._get_default_script(concept)
        
        if not script:
            return {
                'error': f'No script found for concept: {concept}',
                'success': False
            }
        
        # Generate frames
        frames = []
        concept_dir = self.output_dir / concept
        concept_dir.mkdir(exist_ok=True)
        
        for idx, scene in enumerate(script):
            frame_path = await self._generate_frame(
                title=scene.get('title', ''),
                content=scene.get('content', ''),
                frame_number=idx + 1,
                total_frames=len(script),
                output_path=concept_dir / f"frame_{idx:03d}.png"
            )
            frames.append(str(frame_path))
        
        # Generate metadata
        video_id = self._generate_video_id(concept)
        metadata = {
            'video_id': video_id,
            'concept': concept,
            'title': self._format_title(concept),
            'frame_count': len(frames),
            'frames': frames,
            'duration_seconds': len(frames) * 5,  # 5 seconds per frame
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Save metadata
        metadata_path = concept_dir / 'metadata.json'
        import json
        metadata_path.write_text(json.dumps(metadata, indent=2))
        
        # Audit
        self._audit_video_generation(
            concept=concept,
            frames=len(frames),
            success=True
        )
        
        return {
            'success': True,
            'video_id': video_id,
            'concept': concept,
            'frames': frames,
            'metadata_path': str(metadata_path)
        }
    
    async def _generate_frame(
        self,
        title: str,
        content: str,
        frame_number: int,
        total_frames: int,
        output_path: Path
    ) -> Path:
        """Generate a single video frame as an image."""
        # Frame dimensions (16:9 aspect ratio)
        width, height = 1920, 1080
        
        # Create image with gradient background
        img = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(img)
        
        # Gradient background (dark blue to lighter blue)
        for y in range(height):
            ratio = y / height
            r = int(15 + (40 - 15) * ratio)
            g = int(30 + (60 - 30) * ratio)
            b = int(60 + (100 - 60) * ratio)
            draw.rectangle([(0, y), (width, y + 1)], fill=(r, g, b))
        
        # Try to load fonts (fallback to default if not available)
        try:
            title_font = ImageFont.truetype("arial.ttf", 80)
            content_font = ImageFont.truetype("arial.ttf", 40)
            footer_font = ImageFont.truetype("arial.ttf", 30)
        except:
            title_font = ImageFont.load_default()
            content_font = ImageFont.load_default()
            footer_font = ImageFont.load_default()
        
        # Draw title
        title_y = 150
        # Word wrap title if needed
        title_wrapped = self._wrap_text(title, width - 200, draw, title_font)
        for line in title_wrapped:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            text_width = bbox[2] - bbox[0]
            draw.text(
                ((width - text_width) / 2, title_y),
                line,
                fill=(255, 255, 255),
                font=title_font
            )
            title_y += bbox[3] - bbox[1] + 20
        
        # Draw content
        content_y = title_y + 100
        content_wrapped = self._wrap_text(content, width - 300, draw, content_font)
        for line in content_wrapped:
            bbox = draw.textbbox((0, 0), line, font=content_font)
            text_width = bbox[2] - bbox[0]
            draw.text(
                ((width - text_width) / 2, content_y),
                line,
                fill=(220, 220, 220),
                font=content_font
            )
            content_y += bbox[3] - bbox[1] + 15
        
        # Draw footer (frame counter)
        footer_text = f"Frame {frame_number} of {total_frames}"
        bbox = draw.textbbox((0, 0), footer_text, font=footer_font)
        text_width = bbox[2] - bbox[0]
        draw.text(
            ((width - text_width) / 2, height - 80),
            footer_text,
            fill=(150, 150, 150),
            font=footer_font
        )
        
        # Save frame
        img.save(output_path)
        return output_path
    
    def _wrap_text(
        self,
        text: str,
        max_width: int,
        draw: ImageDraw.ImageDraw,
        font: ImageFont.FreeTypeFont
    ) -> List[str]:
        """Wrap text to fit within max_width."""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def _get_default_script(self, concept: str) -> Optional[List[Dict[str, str]]]:
        """Get default script for a concept."""
        scripts = {
            'discovery_process': [
                {
                    'title': 'Legal Discovery Process',
                    'content': 'Discovery is the pre-trial phase where parties exchange information.'
                },
                {
                    'title': 'Types of Discovery',
                    'content': 'Interrogatories, Depositions, Requests for Production, Requests for Admission'
                },
                {
                    'title': 'Interrogatories',
                    'content': 'Written questions that must be answered under oath within 30 days.'
                },
                {
                    'title': 'Depositions',
                    'content': 'Oral testimony taken under oath, recorded by a court reporter.'
                },
                {
                    'title': 'Requests for Production',
                    'content': 'Requests for documents, electronically stored information, or tangible things.'
                },
                {
                    'title': 'Discovery Timeline',
                    'content': 'Discovery typically occurs after pleadings and before trial.'
                }
            ],
            'burden_of_proof': [
                {
                    'title': 'Burden of Proof',
                    'content': 'The obligation to prove allegations or defenses in a legal case.'
                },
                {
                    'title': 'Preponderance of Evidence',
                    'content': 'Civil standard: More likely than not (>50%)'
                },
                {
                    'title': 'Clear and Convincing',
                    'content': 'Higher civil standard: Substantially more likely than not (~75%)'
                },
                {
                    'title': 'Beyond Reasonable Doubt',
                    'content': 'Criminal standard: Highest burden, leaves no reasonable doubt (~95%+)'
                },
                {
                    'title': 'Burden Shifting',
                    'content': 'In some cases, burden shifts between parties during trial.'
                }
            ],
            'hearsay_exceptions': [
                {
                    'title': 'Hearsay Rule',
                    'content': 'Out-of-court statements offered for truth are generally inadmissible.'
                },
                {
                    'title': 'Present Sense Impression',
                    'content': 'Statement describing event made while or immediately after perceiving it.'
                },
                {
                    'title': 'Excited Utterance',
                    'content': 'Statement made under stress of excitement from startling event.'
                },
                {
                    'title': 'Then-Existing Mental/Emotional State',
                    'content': 'Statements of current mental, emotional, or physical condition.'
                },
                {
                    'title': 'Business Records',
                    'content': 'Records made in regular course of business if proper foundation laid.'
                }
            ]
        }
        
        return scripts.get(concept)
    
    def _format_title(self, concept: str) -> str:
        """Format concept name as title."""
        return ' '.join(word.capitalize() for word in concept.split('_'))
    
    def _generate_video_id(self, concept: str) -> str:
        """Generate unique video ID."""
        content = f"{concept}:{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def list_generated_videos(self) -> List[Dict[str, Any]]:
        """List all generated videos."""
        videos = []
        
        for concept_dir in self.output_dir.iterdir():
            if concept_dir.is_dir():
                metadata_path = concept_dir / 'metadata.json'
                if metadata_path.exists():
                    import json
                    metadata = json.loads(metadata_path.read_text())
                    videos.append(metadata)
        
        return videos
    
    def _audit_video_generation(
        self,
        concept: str,
        frames: int,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Audit video generation."""
        event = AuditEvent(
            category='video_generation',
            action='video.generate',
            actor={'id': 'system', 'type': 'video_service'},
            subject={'concept': concept},
            outcome='success' if success else 'error',
            severity='info' if success else 'warning',
            metadata={
                'frames': frames,
                'error': error
            }
        )
        self.audit.append(event)


# Singleton
_video_generation_service: Optional[VideoGenerationService] = None


def get_video_generation_service() -> VideoGenerationService:
    """Get or create video generation service."""
    global _video_generation_service
    if _video_generation_service is None:
        _video_generation_service = VideoGenerationService()
    return _video_generation_service
