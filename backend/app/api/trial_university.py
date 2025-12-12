from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/trial-university", tags=["Trial University"])

class Lesson(BaseModel):
    id: str
    title: str
    summary: str
    progress: int
    icon: str
    video_url: Optional[str] = None # Added video_url for the video player

# In-memory lesson data (for demonstration purposes)
lessons_db: List[Lesson] = [
    {
        "id": '1',
        "title": 'Introduction to Legal Discovery',
        "summary": 'Understand the basics of evidence collection and its importance.',
        "progress": 75,
        "icon": 'fa-solid fa-magnifying-glass',
        "video_url": '/api/video-generation/slideshow/discovery_process'  # Custom generated video
    },
    {
        "id": '2',
        "title": 'Crafting Compelling Arguments',
        "summary": 'Develop persuasive legal arguments and presentation skills.',
        "progress": 50,
        "icon": 'fa-solid fa-gavel',
        "video_url": 'https://www.youtube.com/embed/dQw4w9WgXcQ'  # Curated YouTube content
    },
    {
        "id": '3',
        "title": 'Understanding Burden of Proof',
        "summary": 'Learn the different standards of proof in civil and criminal cases.',
        "progress": 25,
        "icon": 'fa-solid fa-scale-balanced',
        "video_url": '/api/video-generation/slideshow/burden_of_proof'  # Custom generated video
    },
    {
        "id": '4',
        "title": 'AI in Legal Research',
        "summary": 'Leverage AI tools for efficient and comprehensive legal research.',
        "progress": 90,
        "icon": 'fa-solid fa-robot',
        "video_url": 'https://www.youtube.com/embed/dQw4w9WgXcQ'
    },
    {
        "id": '5',
        "title": 'Hearsay Rule and Exceptions',
        "summary": 'Master the hearsay rule and its many exceptions.',
        "progress": 10,
        "icon": 'fa-solid fa-book',
        "video_url": '/api/video-generation/slideshow/hearsay_exceptions'  # Custom generated video
    },
]

@router.get("/lessons", response_model=List[Lesson])
async def get_all_lessons():
    """
    Retrieves a list of all available lessons in Trial University.
    """
    return lessons_db

@router.get("/lessons/{lesson_id}", response_model=Lesson)
async def get_lesson_by_id(lesson_id: str):
    """
    Retrieves a specific lesson by its ID.
    """
    lesson = next((lesson for lesson in lessons_db if lesson.id == lesson_id), None)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


@router.get("/slideshow/{concept}")
async def get_video_slideshow(concept: str):
    """
    Returns an HTML slideshow for a generated video concept.
    Serves the generated frames as an auto-advancing slideshow.
    """
    from fastapi.responses import HTMLResponse
    from ..services.video_generation_service import get_video_generation_service
    
    service = get_video_generation_service()
    videos = service.list_generated_videos()
    
    # Find video for this concept
    video = next((v for v in videos if v['concept'] == concept), None)
    
    if not video:
        # Generate on-demand if not exists
        result = await service.generate_concept_video(concept)
        if not result.get('success'):
            raise HTTPException(status_code=404, detail=f"Video not found for concept: {concept}")
        video = result
    
    # Build HTML slideshow
    frames = video.get('frames', [])
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{video.get('title', concept)}</title>
        <style>
            body {{
                margin: 0;
                padding: 0;
                background: #000;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                font-family: Arial, sans-serif;
            }}
            .slideshow {{
                width: 100%;
                max-width: 1920px;
                height: 100vh;
                position: relative;
                overflow: hidden;
            }}
            .slide {{
                display: none;
                width: 100%;
                height: 100%;
                object-fit: contain;
            }}
            .slide.active {{
                display: block;
                animation: fadeIn 0.5s;
            }}
            @keyframes fadeIn {{
                from {{ opacity: 0; }}
                to {{ opacity: 1; }}
            }}
            .controls {{
                position: absolute;
                bottom: 30px;
                left: 50%;
                transform: translateX(-50%);
                z-index: 100;
            }}
            button {{
                background: rgba(255, 255, 255, 0.8);
                border: none;
                padding: 10px 20px;
                margin: 0 5px;
                cursor: pointer;
                border-radius: 5px;
                font-size: 16px;
            }}
            button:hover {{
                background: rgba(255, 255, 255, 1);
            }}
        </style>
    </head>
    <body>
        <div class="slideshow" id="slideshow">
    """
    
    # Add frame images
    for idx, frame_path in enumerate(frames):
        frame_filename = frame_path.split('/')[-1]  # Get just the filename
        frame_url = f"/api/video-generation/frames/{concept}/{frame_filename}"
        active = "active" if idx == 0 else ""
        html_content += f'<img src="{frame_url}" class="slide {active}" id="slide-{idx}">\n'
    
    html_content += """
            <div class="controls">
                <button onclick="prevSlide()">← Previous</button>
                <button onclick="toggleAuto()" id="autoBtn">⏸ Pause</button>
                <button onclick="nextSlide()">Next →</button>
            </div>
        </div>
        <script>
            let currentSlide = 0;
            const slides = document.querySelectorAll('.slide');
            let autoPlay = true;
            let autoInterval;
            
            function showSlide(n) {
                slides[currentSlide].classList.remove('active');
                currentSlide = (n + slides.length) % slides.length;
                slides[currentSlide].classList.add('active');
            }
            
            function nextSlide() {
                showSlide(currentSlide + 1);
            }
            
            function prevSlide() {
                showSlide(currentSlide - 1);
            }
            
            function toggleAuto() {
                autoPlay = !autoPlay;
                document.getElementById('autoBtn').textContent = autoPlay ? '⏸ Pause' : '▶ Play';
                if (autoPlay) {
                    startAuto();
                } else {
                    clearInterval(autoInterval);
                }
            }
            
            function startAuto() {
                autoInterval = setInterval(() => {
                    if (autoPlay) {
                        nextSlide();
                    }
                }, 5000);  // 5 seconds per slide
            }
            
            // Start auto-play
            startAuto();
            
            // Keyboard navigation
            document.addEventListener('keydown', (e) => {
                if (e.key === 'ArrowLeft') prevSlide();
                if (e.key === 'ArrowRight') nextSlide();
                if (e.key === ' ') toggleAuto();
            });
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)
