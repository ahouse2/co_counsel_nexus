from typing import List, Optional
from pydantic import BaseModel
from backend.app.services.llm_service import get_llm_service

class DraftingRequest(BaseModel):
    current_text: str
    cursor_position: int
    context: str = "" # Case context or specific instructions

class ToneCheckRequest(BaseModel):
    text: str
    target_tone: str # e.g., "formal", "aggressive", "conciliatory"

class ToneCheckResult(BaseModel):
    original_text: str
    revised_text: str
    critique: str
    score: float # 0-1 match to target tone

class DocumentDraftingService:
    def __init__(self):
        self.llm_service = get_llm_service()

    async def autocomplete(self, request: DraftingRequest) -> str:
        """
        Provides context-aware autocomplete suggestions.
        """
        # Split text at cursor
        before_cursor = request.current_text[:request.cursor_position]
        after_cursor = request.current_text[request.cursor_position:]
        
        # Take last 1000 chars for context
        context_window = before_cursor[-1000:]
        
        prompt = f"""
        You are an expert legal drafting assistant. Complete the following legal text.
        
        CONTEXT:
        {request.context}
        
        TEXT SO FAR:
        {context_window}
        
        [CURSOR IS HERE]
        
        INSTRUCTIONS:
        - Provide a natural continuation of the text.
        - Maintain the legal style and tone.
        - Do not repeat text that is already there.
        - Return ONLY the completion text.
        """
        
        return await self.llm_service.generate_text(prompt)

    async def check_tone(self, request: ToneCheckRequest) -> ToneCheckResult:
        """
        Analyzes and adjusts the tone of the text.
        """
        prompt = f"""
        You are a legal editor. Analyze the following text and rewrite it to match the target tone: "{request.target_tone}".
        
        TEXT:
        {request.text}
        
        INSTRUCTIONS:
        1. Rewrite the text to strictly match the target tone.
        2. Provide a brief critique of why the original didn't match.
        3. Rate the original text's match to the target tone (0.0 to 1.0).
        
        OUTPUT FORMAT:
        Return a JSON object with keys: "revised_text", "critique", "score".
        """
        
        response = await self.llm_service.generate_text(prompt)
        
        # Basic parsing (robustness improvements needed for prod)
        import json
        try:
            # Clean markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            data = json.loads(cleaned)
            return ToneCheckResult(
                original_text=request.text,
                revised_text=data.get("revised_text", ""),
                critique=data.get("critique", ""),
                score=data.get("score", 0.0)
            )
        except Exception as e:
            # Fallback
            return ToneCheckResult(
                original_text=request.text,
                revised_text=response,
                critique="Failed to parse structured response.",
                score=0.0
            )

_service = None
def get_document_drafting_service():
    global _service
    if _service is None:
        _service = DocumentDraftingService()
    return _service
