import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.app.agents.swarms_runner import SwarmsRunner

# Mock LLM Service
class MockLLMService:
    def __init__(self):
        pass
    def __call__(self, prompt, **kwargs):
        return f"Mock Response to: {prompt[:50]}..."
    def generate_text(self, prompt):
        return f"Mock Response to: {prompt[:50]}..."

def test_swarms_runner():
    print("Testing SwarmsRunner...")
    
    llm = MockLLMService()
    runner = SwarmsRunner(llm)
    
    question = "Start a mock trial strategy for the breach of contract case."
    print(f"\nInput Question: {question}")
    
    try:
        # This will route to 'litigation_support' and run the swarm
        result = runner.route_and_run(question)
        print(f"\nResult: {result}")
        print("SUCCESS: SwarmsRunner executed successfully.")
    except Exception as e:
        print(f"FAILURE: SwarmsRunner failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_swarms_runner()
