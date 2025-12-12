"""Opposing Counsel agent for adversarial simulation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..services.errors import WorkflowAbort, WorkflowComponent, WorkflowError, WorkflowSeverity
from .context import AgentContext

@dataclass
class CounterArgument:
    original_point: str
    counter_point: str
    weakness_exposed: str
    citations: List[str]
    risk_score: float

@dataclass
class CrossExamQuestion:
    question: str
    intent: str
    difficulty: str
    expected_answer_type: str

class OpposingCounselAgent:
    """
    Agent that simulates an adversarial opposing counsel.
    It challenges user arguments, simulates cross-examination, and evaluates risk.
    """

    def __init__(self, llm_service: Any) -> None:
        self.llm_service = llm_service

    def generate_counter_arguments(
        self, 
        argument: str, 
        context: AgentContext,
        evidence_context: Optional[str] = None
    ) -> List[CounterArgument]:
        """
        Generates counter-arguments to a given legal argument.
        """
        prompt = f"""
        You are a ruthless and highly skilled Opposing Counsel.
        Your goal is to dismantle the following argument made by the plaintiff/defendant.
        
        ARGUMENT:
        "{argument}"
        
        EVIDENCE CONTEXT:
        {evidence_context or "No specific evidence provided."}
        
        TASK:
        1. Identify logical fallacies, weak assumptions, or lack of evidence.
        2. Formulate strong counter-arguments.
        3. Assign a risk score (0.0 to 1.0) indicating how damaging this counter-argument is.
        
        OUTPUT FORMAT (JSON):
        {{
            "counter_arguments": [
                {{
                    "original_point": "The specific part of the argument you are attacking",
                    "counter_point": "Your counter-argument",
                    "weakness_exposed": "The flaw you found",
                    "citations": ["Case X", "Exhibit Y"],
                    "risk_score": 0.8
                }}
            ]
        }}
        """
        
        try:
            response = self.llm_service.complete(prompt)
            data = self._parse_json(response.text)
            results = []
            for item in data.get("counter_arguments", []):
                results.append(CounterArgument(
                    original_point=item.get("original_point", ""),
                    counter_point=item.get("counter_point", ""),
                    weakness_exposed=item.get("weakness_exposed", ""),
                    citations=item.get("citations", []),
                    risk_score=item.get("risk_score", 0.5)
                ))
            return results
        except Exception as e:
            print(f"Error generating counter-arguments: {e}")
            return []

    def simulate_cross_exam(
        self, 
        witness_statement: str, 
        context: AgentContext
    ) -> List[CrossExamQuestion]:
        """
        Generates cross-examination questions to impeach a witness or challenge a statement.
        """
        prompt = f"""
        You are conducting a cross-examination.
        
        WITNESS STATEMENT:
        "{witness_statement}"
        
        TASK:
        Generate a series of leading questions designed to:
        1. Impeach the witness's credibility.
        2. Highlight inconsistencies.
        3. Force the witness into a trap.
        
        OUTPUT FORMAT (JSON):
        {{
            "questions": [
                {{
                    "question": "Isn't it true that...?",
                    "intent": "To show bias",
                    "difficulty": "Hard",
                    "expected_answer_type": "Yes/No"
                }}
            ]
        }}
        """
        
        try:
            response = self.llm_service.complete(prompt)
            data = self._parse_json(response.text)
            results = []
            for item in data.get("questions", []):
                results.append(CrossExamQuestion(
                    question=item.get("question", ""),
                    intent=item.get("intent", ""),
                    difficulty=item.get("difficulty", "Medium"),
                    expected_answer_type=item.get("expected_answer_type", "Open")
                ))
            return results
        except Exception as e:
            print(f"Error simulating cross-exam: {e}")
            return []

    def evaluate_risk(self, evidence: str, context: AgentContext) -> float:
        """
        Evaluates the legal risk associated with a piece of evidence or argument.
        Returns a score from 0.0 (Safe) to 1.0 (Critical Risk).
        """
        prompt = f"""
        Evaluate the legal risk of this evidence/argument for our case.
        
        INPUT:
        "{evidence}"
        
        Return ONLY a JSON object: {{"risk_score": 0.5, "reasoning": "..."}}
        """
        try:
            response = self.llm_service.complete(prompt)
            data = self._parse_json(response.text)
            return float(data.get("risk_score", 0.5))
        except Exception:
            return 0.5

    def _parse_json(self, text: str) -> Dict[str, Any]:
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text)
