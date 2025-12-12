import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from backend.app.agents.swarms.ingestion_swarm import IngestionSwarm
from backend.app.services.classification_service import ClassificationService
from backend.app.services.document_service import DocumentService # Mock this if needed

# Mock LLM for Swarms
class MockLLM:
    def __init__(self):
        pass
    def __call__(self, prompt):
        return "Mock LLM Response"
    def generate(self, prompt):
        return "Mock LLM Response"

def test_swarms():
    print("Testing IngestionSwarm...")
    
    # Setup dependencies
    llm = MockLLM()
    # We can mock services too if we don't want full DB connection
    class MockDocService: pass
    
    classification_service = ClassificationService() # This might need real LLM or we mock it
    
    swarm = IngestionSwarm(llm, MockDocService(), classification_service)
    
    text = "This is a contract for the sale of goods."
    
    try:
        print(f"Running swarm on: '{text}'")
        # Note: If swarms is not installed, this will use our mock classes which might not do much.
        # But it verifies the structure.
        result = swarm.run(text)
        print(f"Swarm Result: {result}")
        print("SUCCESS: Swarm ran without error.")
    except Exception as e:
        print(f"FAILURE: Swarm failed: {e}")

if __name__ == "__main__":
    test_swarms()
