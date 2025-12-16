import asyncio
import httpx
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

async def verify_mock_trial():
    base_url = "http://localhost:8001/api"
    
    print("Verifying Mock Trial Arena Endpoints...")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Test Juror Chat
        print("\n1. Testing Juror Chat...")
        juror_profile = {
            "education": "College Graduate",
            "age": "30-50",
            "bias": "Skeptical",
            "occupation": "Engineer"
        }
        chat_history = []
        user_message = "The defendant had no motive to commit this crime."
        case_context = "The defendant is accused of corporate espionage. The prosecution claims he stole trade secrets for a rival company."
        
        try:
            resp_chat = await client.post(f"{base_url}/simulation/juror_chat", json={
                "juror_profile": juror_profile,
                "chat_history": chat_history,
                "user_message": user_message,
                "case_context": case_context
            })
            
            if resp_chat.status_code == 200:
                print(f"Juror Response: {resp_chat.json().get('response')}")
            else:
                print(f"Failed to chat with juror: {resp_chat.text}")
                
        except Exception as e:
            print(f"Error testing juror chat: {e}")

if __name__ == "__main__":
    asyncio.run(verify_mock_trial())
