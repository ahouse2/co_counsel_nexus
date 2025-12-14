import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from backend.app.services.llm_service import get_llm_service

async def test_llm():
    print("Testing LLM Service...")
    try:
        service = get_llm_service()
        prompt = "Say 'Hello, World!' and nothing else."
        print(f"Sending prompt: {prompt}")
        
        response = await service.generate_text(prompt)
        print(f"Response: {response}")
        
    except Exception as e:
        print(f"LLM Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_llm())
