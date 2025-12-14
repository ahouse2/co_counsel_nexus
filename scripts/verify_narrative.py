import asyncio
import httpx
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

async def verify_narrative_endpoints():
    base_url = "http://localhost:8001/api"
    case_id = "default_case" # Ensure this case exists or use a known one
    
    print("Verifying Narrative Weaver Endpoints...")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Test Generate Narrative
        print("\n1. Testing Generate Narrative...")
        try:
            response = await client.get(f"{base_url}/narrative/{case_id}/generate")
            if response.status_code == 200:
                data = response.json()
                narrative = data.get('narrative', '')
                print(f"Narrative generated (Length: {len(narrative)} chars)")
                print(f"Preview: {narrative[:100]}...")
            else:
                print(f"Failed to generate narrative: {response.text}")
        except Exception as e:
            print(f"Error generating narrative: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

        # 2. Test Detect Contradictions
        print("\n2. Testing Detect Contradictions...")
        try:
            response = await client.get(f"{base_url}/narrative/{case_id}/contradictions")
            if response.status_code == 200:
                contradictions = response.json()
                print(f"Found {len(contradictions)} contradictions")
                if contradictions:
                    print(f"First contradiction: {contradictions[0]['description']}")
            else:
                print(f"Failed to detect contradictions: {response.text}")
        except Exception as e:
            print(f"Error detecting contradictions: {e}")

if __name__ == "__main__":
    asyncio.run(verify_narrative_endpoints())
