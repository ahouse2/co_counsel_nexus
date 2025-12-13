from typing import Any, Dict, List
import json
from backend.app.config import get_settings
from backend.ingestion.llama_index_factory import create_llm_service
from backend.ingestion.settings import build_runtime_config
from backend.app.services.timeline import get_timeline_service

class AdversarialAgent:
    def __init__(self):
        settings = get_settings()
        runtime_config = build_runtime_config(settings)
        self.llm_service = create_llm_service(runtime_config.llm)
        self.timeline_service = get_timeline_service()

    def generate_challenge(self, case_id: str, case_theory: str) -> Dict[str, Any]:
        """
        Analyzes the case theory against the known timeline and generates a hostile critique.
        """
        # 1. Gather Context
        try:
            timeline_result = self.timeline_service.list_events(case_id)
            events = timeline_result.events if timeline_result else []
        except Exception:
            events = []
            
        # Sort and take recent/relevant events to fit in context
        sorted_events = sorted(events, key=lambda e: e.ts)
        # Use last 50 events as context
        context_text = "\n".join([
            f"- {e.ts.strftime('%Y-%m-%d %H:%M')}: {e.title} ({e.summary})" 
            for e in sorted_events[-50:]
        ])

        # 2. Construct Prompt
        prompt = f"""
        You are The Devil's Advocate, a ruthless and highly skilled opposing counsel.
        Your job is to destroy the user's case theory.

        CASE CONTEXT (Timeline):
        {context_text}

        USER'S CASE THEORY:
        "{case_theory}"

        TASK:
        1. Identify logical gaps or inconsistencies in the theory compared to the timeline.
        2. Formulate the strongest possible counter-arguments.
        3. Draft 3-5 devastating cross-examination questions for the user's key witness (implied).

        OUTPUT FORMAT (JSON):
        {{
            "weaknesses": [
                {{"point": "Short headline", "explanation": "Detailed explanation of the flaw"}}
            ],
            "counter_arguments": [
                {{"argument": "The counter-argument", "evidence_cited": "Reference to specific timeline event if applicable"}}
            ],
            "cross_examination": [
                "Question 1...",
                "Question 2..."
            ],
            "overall_assessment": "Brief ruthless summary of why the theory fails."
        }}
        
        Return ONLY the JSON object.
        """

        # 3. Call LLM
        try:
            response = self.llm_service.complete(prompt)
            text = response.text
            
            # 4. Parse JSON
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
                
            return json.loads(text.strip())
            
        except Exception as e:
            print(f"Adversarial Agent Error: {e}")
            # Fallback for demo/error
            return {
                "weaknesses": [{"point": "Analysis Failed", "explanation": f"Could not generate challenge: {str(e)}"}],
                "counter_arguments": [],
                "cross_examination": [],
                "overall_assessment": "The system encountered an error while trying to dismantle your theory."
            }
