import asyncio
import httpx
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

async def verify_devils_advocate_advanced():
    base_url = "http://localhost:8001/api"
    case_id = "default_case"
    
    print("Verifying Devil's Advocate Advanced Endpoints...")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Test Motion to Dismiss
        print("\n1. Testing Motion to Dismiss...")
        try:
            resp_motion = await client.post(f"{base_url}/devils-advocate/{case_id}/motion_to_dismiss", json={
                "grounds": ["Lack of Evidence", "Procedural Error"]
            })
            
            if resp_motion.status_code == 200:
                print(f"Motion Draft: {resp_motion.json()}")
            else:
                print(f"Failed to generate motion: {resp_motion.text}")
                
        except Exception as e:
            print(f"Error testing motion to dismiss: {e}")

if __name__ == "__main__":
    asyncio.run(verify_devils_advocate_advanced())
