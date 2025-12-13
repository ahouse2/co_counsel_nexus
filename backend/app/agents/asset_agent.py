from typing import List, Dict, Any
import json
from backend.app.config import get_settings
from backend.ingestion.llama_index_factory import create_llm_service
from backend.ingestion.settings import build_runtime_config
from backend.app.services.timeline import get_timeline_service

class AssetAgent:
    def __init__(self):
        settings = get_settings()
        runtime_config = build_runtime_config(settings)
        self.llm_service = create_llm_service(runtime_config.llm)
        self.timeline_service = get_timeline_service()

    def scan_for_assets(self, case_id: str) -> Dict[str, Any]:
        """
        Scans case documents/timeline for hidden asset indicators.
        """
        # 1. Get Context (Timeline + recent docs)
        try:
            timeline_result = self.timeline_service.list_events(case_id)
            events = timeline_result.events if timeline_result else []
        except Exception:
            events = []
            
        # Filter for financial keywords
        financial_keywords = ["bank", "transfer", "trust", "llc", "offshore", "cayman", "panama", "crypto", "bitcoin", "wire", "asset", "purchase"]
        relevant_events = [
            e for e in events 
            if any(k in e.summary.lower() for k in financial_keywords)
        ]
        
        context_text = "\n".join([
            f"- {e.ts}: {e.summary}" for e in relevant_events[-30:]
        ])

        if not context_text:
            return {"assets": [], "risk_score": 0.0, "summary": "No financial indicators found in timeline."}

        # 2. Prompt LLM
        prompt = f"""
        You are a Forensic Accountant and Asset Hunter.
        Analyze the following timeline of financial events to identify POTENTIAL HIDDEN ASSETS.
        
        Look for:
        - Transfers to Trusts, LLCs, or unknown entities.
        - Offshore jurisdictions (Cayman, Panama, Swiss, etc.).
        - Large unexplained wire transfers.
        - Purchases of non-cash assets (Art, Real Estate, Crypto).
        
        TIMELINE:
        {context_text}
        
        Return ONLY a JSON object with:
        - "assets": List of objects {{ "type": str, "entity": str, "value": str, "suspicion_level": "High/Medium/Low", "reason": str }}
        - "risk_score": float (0.0 - 1.0)
        - "summary": str (Executive summary of findings)
        """

        try:
            response = self.llm_service.complete(prompt)
            text = response.text
            
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
                
            return json.loads(text.strip())
            
        except Exception as e:
            print(f"Asset Agent Error: {e}")
            return {"assets": [], "risk_score": 0.0, "summary": "Analysis failed."}
