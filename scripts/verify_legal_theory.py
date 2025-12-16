import asyncio
import httpx
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

async def verify_legal_theory():
    base_url = "http://localhost:8001/api"
    
    print("Verifying Legal Theory Endpoints...")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Test Precedent Matcher
        print("\n1. Testing Precedent Matcher...")
        try:
            resp_match = await client.post(f"{base_url}/legal_theory/match_precedents", json={
                "case_facts": "The defendant is accused of insider trading involving a pharmaceutical merger.",
                "jurisdiction": "federal"
            })
            
            if resp_match.status_code == 200:
                print(f"Precedents: {resp_match.json()}")
            else:
                print(f"Failed to match precedents: {resp_match.text}")
                
        except Exception as e:
            print(f"Error testing precedent matcher: {e}")
            
        # 2. Test Jury Resonance
        print("\n2. Testing Jury Resonance...")
        try:
            resp_res = await client.post(f"{base_url}/legal_theory/jury_resonance", json={
                "argument": "The defendant had no knowledge of the merger prior to the trade.",
                "jury_demographics": {"education": "Mixed"}
            })
            
            if resp_res.status_code == 200:
                print(f"Resonance: {resp_res.json()}")
            else:
                print(f"Failed to test resonance: {resp_res.text}")
                
        except Exception as e:
            print(f"Error testing jury resonance: {e}")

if __name__ == "__main__":
    asyncio.run(verify_legal_theory())
