import sys
import os
from pathlib import Path
import asyncio
import json

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.app.api.mock_trial import simulate_turn, GameState
from backend.app.api.legal_theory import get_legal_theory_suggestions
from backend.app.api.forensics import trigger_deep_analysis
from backend.app.api.agents import run_agent_task, AgentRunRequest
from backend.app.storage.document_store import DocumentStore

# Mock Dependencies
class MockPrincipal:
    pass

class MockStore:
    def list_document_versions(self, *args): return ["v1"]
    def _get_storage_path(self, *args, **kwargs): return Path("/tmp/mock_doc.pdf")

async def test_grand_unification():
    print("=== GRAND UNIFICATION VERIFICATION ===")
    
    # 1. Test Mock Trial Swarm
    print("\n[1] Testing Mock Trial Swarm...")
    try:
        state = GameState(
            phase='playerTurn', playerHealth=100, opponentHealth=100, 
            currentEvidence=None, log=['Start'], score=0, message='Go', availableActions=['presentEvidence']
        )
        res = await simulate_turn(state, "presentEvidence", {"evidence": "Exhibit A"})
        print(f"PASS: Mock Trial Response: {json.dumps(res)[:100]}...")
    except Exception as e:
        print(f"FAIL: Mock Trial: {e}")

    # 2. Test Legal Research Swarm
    print("\n[2] Testing Legal Research Swarm...")
    try:
        res = await get_legal_theory_suggestions(case_id="test_case", _principal=MockPrincipal())
        print(f"PASS: Legal Theory Response: {json.dumps(res)[:100]}...")
    except Exception as e:
        print(f"FAIL: Legal Research: {e}")

    # 3. Test Forensics Swarm
    print("\n[3] Testing Forensics Swarm...")
    try:
        # We need to mock the store dependency
        res = await trigger_deep_analysis(doc_id="test_doc", case_id="test_case", store=MockStore())
        print(f"PASS: Forensics Response: {json.dumps(res)[:100]}...")
    except Exception as e:
        print(f"FAIL: Forensics: {e}")

    # 4. Test Master Orchestrator
    print("\n[4] Testing Master Orchestrator...")
    try:
        req = AgentRunRequest(task="Analyze the case strategy", case_id="test_case")
        res = await run_agent_task(req)
        print(f"PASS: Master Response: {str(res)[:100]}...")
    except Exception as e:
        print(f"FAIL: Master Orchestrator: {e}")

if __name__ == "__main__":
    asyncio.run(test_grand_unification())
