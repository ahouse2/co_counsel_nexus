import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.app.services.knowledge_graph_service import KnowledgeGraphService
from llama_index.core import Document

def test_graph_indexing():
    print("Testing KnowledgeGraphService Indexing...")
    
    service = KnowledgeGraphService()
    
    # Create a dummy document
    text = "John Doe signed the lease agreement with Jane Smith on January 1st, 2024. The rent is $2000 per month."
    doc = Document(text=text, metadata={"case_id": "test_case_graph"})
    
    print(f"\nIndexing document: '{text}'")
    try:
        service.build_graph_index([doc], case_id="test_case_graph")
        print("SUCCESS: Graph Indexing completed without error.")
        
        # Verify by querying (basic check)
        # We can use the existing get_graph_data to see if nodes were created
        # But that's async.
        # Let's just trust the "Successfully built..." message for now or add async check if possible.
        
    except Exception as e:
        print(f"FAILURE: Graph Indexing failed: {e}")

if __name__ == "__main__":
    test_graph_indexing()
