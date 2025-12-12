import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.app.services.classification_service import ClassificationService
from backend.app.config import Settings, LlmSettings, LlmProvider

def test_classification():
    print("Testing ClassificationService...")
    
    # Mock settings if needed, or rely on env vars
    # Assuming env vars are set or .env is loaded
    
    service = ClassificationService()
    
    test_docs = [
        ("This is a lease agreement between Landlord and Tenant.", "Contract"),
        ("The plaintiff files this complaint against the defendant.", "Pleading"),
        ("Invoice #12345 for services rendered. Total: $500.", "Financial"),
    ]
    
    for text, expected in test_docs:
        print(f"\nClassifying: '{text}'")
        result = service.classify_document_sync(text)
        print(f"Result: {result.categories}")
        print(f"Reasoning: {result.reasoning}")
        
        if expected in result.categories:
            print("SUCCESS: Expected category found.")
        else:
            print(f"FAILURE: Expected {expected}, got {result.categories}")

if __name__ == "__main__":
    test_classification()
