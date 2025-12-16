import asyncio
import httpx
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

async def verify_drafting_endpoints():
    base_url = "http://localhost:8001/api"
    
    print("Verifying Document Drafting Endpoints...")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Test Autocomplete
        print("\n1. Testing Autocomplete...")
        try:
            payload = {
                "current_text": "The Party of the First Part agrees to indemnify the Party of the Second Part against all ",
                "cursor_position": 86,
                "context": "Standard commercial lease agreement indemnification clause."
            }
            response = await client.post(f"{base_url}/drafting/autocomplete", json=payload)
            if response.status_code == 200:
                data = response.json()
                print(f"Autocomplete Result: {data.get('completion')}")
            else:
                print(f"Failed to autocomplete: {response.text}")
        except Exception as e:
            print(f"Error testing autocomplete: {e}")

        # 2. Test Tone Check
        print("\n2. Testing Tone Check...")
        try:
            payload = {
                "text": "Hey buddy, you better pay up or we're gonna sue you big time.",
                "target_tone": "highly formal legal"
            }
            response = await client.post(f"{base_url}/drafting/tone-check", json=payload)
            if response.status_code == 200:
                data = response.json()
                print(f"Original: {data.get('original_text')}")
                print(f"Revised: {data.get('revised_text')}")
                print(f"Critique: {data.get('critique')}")
                print(f"Score: {data.get('score')}")
            else:
                print(f"Failed to check tone: {response.text}")
        except Exception as e:
            print(f"Error testing tone check: {e}")

if __name__ == "__main__":
    asyncio.run(verify_drafting_endpoints())
