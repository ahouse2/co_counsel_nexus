import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Force memory mode for testing
os.environ["NEO4J_URI"] = "memory://"

from backend.app.services.graph import GraphService
from backend.app.config import get_settings

async def test_graph_agent():
    print("Initializing GraphService...")
    try:
        service = GraphService()
        print("GraphService initialized.")
    except Exception as e:
        print(f"Failed to initialize GraphService: {e}")
        return

    query = "Show me the most important entities."
    print(f"\nTesting text_to_cypher with query: '{query}'")
    
    try:
        # We might not have an LLM configured in this environment, so this might fail or return a fallback.
        # But we want to ensure the method exists and runs.
        result = service.text_to_cypher(query)
        print(f"Result type: {type(result)}")
        print(f"Generated Cypher: {result.cypher}")
        print(f"Warnings: {result.warnings}")
        
        if result.cypher:
            print("\nCypher generated successfully. Attempting execution (dry run)...")
            # We won't actually execute against a real DB if not connected, but let's try safely
            try:
                # Mock run_cypher if needed, but let's see if it handles it gracefully (memory mode)
                exec_result = service.execute_agent_cypher(query, result.cypher, sandbox=True)
                print("Execution successful.")
                print(f"Records found: {len(exec_result.records)}")
            except Exception as e:
                print(f"Execution failed (expected if no DB): {e}")
        else:
            print("\nNo Cypher generated (expected if no LLM key).")

    except Exception as e:
        print(f"text_to_cypher failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_graph_agent())
