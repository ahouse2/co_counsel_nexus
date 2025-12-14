import asyncio
import httpx
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

async def verify_adversarial_endpoints():
    base_url = "http://localhost:8001/api"
    case_id = "default_case"
    
    print("Verifying Devil's Advocate Endpoints...")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Test Case Review (with Theory)
        print("\n1. Testing Case Review (with Theory)...")
        try:
            payload = {
                "case_theory": "The defendant was negligent in maintaining the vehicle, leading to the accident."
            }
            response = await client.post(f"{base_url}/devils-advocate/{case_id}/review", json=payload)
            if response.status_code == 200:
                weaknesses = response.json()
                print(f"Found {len(weaknesses)} weaknesses")
                if weaknesses:
                    print(f"First weakness: {weaknesses[0]['title']}")
            else:
                print(f"Failed to review case: {response.text}")
        except Exception as e:
            print(f"Error reviewing case: {e}")

        # 2. Test Cross-Examination
        print("\n2. Testing Cross-Examination...")
        try:
            payload = {
                "witness_statement": "I saw the defendant run the red light at approximately 8:05 PM.",
                "witness_profile": "Eyewitness, 45 years old, wearing glasses"
            }
            response = await client.post(f"{base_url}/devils-advocate/cross-examine", json=payload)
            if response.status_code == 200:
                questions = response.json()
                print(f"Generated {len(questions)} questions")
                if questions:
                    print(f"First question: {questions[0]['question']}")
            else:
                print(f"Failed to generate cross-exam: {response.text}")
        except Exception as e:
            print(f"Error generating cross-exam: {e}")

if __name__ == "__main__":
    asyncio.run(verify_adversarial_endpoints())
