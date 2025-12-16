import asyncio
import httpx
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

async def verify_narrative_advanced():
    base_url = "http://localhost:8001/api"
    case_id = "default_case"
    
    print("Verifying Narrative Weaver Advanced Endpoints...")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Test Branching Narratives
        print("\n1. Testing Branching Narratives...")
        try:
            resp_branch = await client.post(f"{base_url}/narrative/{case_id}/branching", json={
                "pivot_point": "The witness testimony",
                "alternative_fact": "The witness was out of town"
            })
            
            if resp_branch.status_code == 200:
                print(f"Branching Scenario: {resp_branch.json()}")
            else:
                print(f"Failed to generate branching narrative: {resp_branch.text}")
                
        except Exception as e:
            print(f"Error testing branching narrative: {e}")
            
        # 2. Test Story Arc
        print("\n2. Testing Story Arc...")
        try:
            resp_arc = await client.get(f"{base_url}/narrative/{case_id}/story_arc")
            
            if resp_arc.status_code == 200:
                print(f"Story Arc: {resp_arc.json()}")
            else:
                print(f"Failed to fetch story arc: {resp_arc.text}")
                
        except Exception as e:
            print(f"Error testing story arc: {e}")

if __name__ == "__main__":
    asyncio.run(verify_narrative_advanced())
