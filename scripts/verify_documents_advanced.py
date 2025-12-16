import asyncio
import httpx
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

async def verify_document_endpoints():
    base_url = "http://localhost:8001/api"
    
    print("Verifying Advanced Document Endpoints...")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. List documents to get an ID
        print("\n1. Listing documents...")
        try:
            response = await client.get(f"{base_url}/documents/default_case/documents")
            if response.status_code == 200:
                docs = response.json()
                if not docs:
                    print("No documents found. Please upload a document first.")
                    return
                
                doc_id = docs[0]['id']
                print(f"Using document ID: {doc_id}")
                
                # 2. Test Get Entities
                print("\n2. Testing Get Entities...")
                resp_ent = await client.get(f"{base_url}/documents/{doc_id}/entities")
                if resp_ent.status_code == 200:
                    print(f"Entities: {resp_ent.json()}")
                else:
                    print(f"Failed to get entities: {resp_ent.text}")
                    
                # 3. Test Get OCR
                print("\n3. Testing Get OCR...")
                resp_ocr = await client.get(f"{base_url}/documents/{doc_id}/ocr")
                if resp_ocr.status_code == 200:
                    text = resp_ocr.json().get('text', '')
                    print(f"OCR Text Preview: {text[:100]}...")
                else:
                    print(f"Failed to get OCR: {resp_ocr.text}")
                    
                # 4. Test Trigger OCR
                print("\n4. Testing Trigger OCR...")
                resp_trig = await client.post(f"{base_url}/documents/{doc_id}/ocr")
                if resp_trig.status_code == 200:
                    print(f"Trigger Response: {resp_trig.json()}")
                else:
                    print(f"Failed to trigger OCR: {resp_trig.text}")
                    
            else:
                print(f"Failed to list documents: {response.text}")
        except Exception as e:
            print(f"Error testing documents: {e}")

if __name__ == "__main__":
    asyncio.run(verify_document_endpoints())
