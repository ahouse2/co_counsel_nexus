import asyncio
import httpx
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

async def verify_research_endpoints():
    base_url = "http://localhost:8001/api"
    
    print("Verifying Advanced Legal Research Endpoints...")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Test Shepardize
        print("\n1. Testing Shepardize...")
        try:
            payload = {"citation": "347 U.S. 483"} # Brown v. Board
            response = await client.post(f"{base_url}/shepardize", json=payload)
            if response.status_code == 200:
                data = response.json()
                print(f"Citation: {data.get('citation')}")
                print(f"Status: {data.get('status')}")
                print(f"Reasoning: {data.get('reasoning')[:100]}...")
            else:
                print(f"Failed to shepardize: {response.text}")
        except Exception as e:
            print(f"Error testing shepardize: {e}")

        # 2. Test Judge Profile
        print("\n2. Testing Judge Profile...")
        try:
            payload = {
                "judge_name": "Learned Hand",
                "jurisdiction": "Second Circuit"
            }
            response = await client.post(f"{base_url}/judge-profile", json=payload)
            if response.status_code == 200:
                data = response.json()
                print(f"Judge: {data.get('judge_name')}")
                print(f"Bio: {data.get('biography')[:100]}...")
                print(f"Tendencies: {data.get('ruling_tendencies')}")
            else:
                print(f"Failed to profile judge: {response.text}")
        except Exception as e:
            print(f"Error testing judge profile: {e}")

if __name__ == "__main__":
    asyncio.run(verify_research_endpoints())
