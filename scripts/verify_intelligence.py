import requests
import time
import sys
import os

API_URL = "http://localhost:8001/api"
CASE_ID = "intelligence_test_case"

def check_health():
    try:
        resp = requests.get("http://localhost:8001/health")
        if resp.status_code == 200:
            print("API is healthy")
            return True
    except Exception as e:
        print(f"API check failed: {e}")
    return False

def create_case():
    # Create case if not exists (or just use default)
    # Assuming case creation is not strictly required for upload if we pass case_id, 
    # but let's try to create it to be safe if there's a case endpoint.
    # For now, we skip explicit creation as upload usually handles it or we use a known ID.
    pass

def upload_document():
    print("Uploading test document...")
    content = """
    On January 15, 2023, John Doe signed the contract.
    On February 20, 2023, the shipment arrived damaged.
    On March 1, 2023, Jane Smith filed a complaint.
    """
    files = {
        'file': ('timeline_test.txt', content, 'text/plain')
    }
    params = {
        'case_id': CASE_ID,
        'doc_type': 'my_documents'
    }
    try:
        resp = requests.post(f"{API_URL}/documents/upload", params=params, files=files)
        if resp.status_code == 200:
            data = resp.json()
            doc_id = data['data']['doc_id']
            print(f"Document uploaded: {doc_id}")
            return doc_id
        else:
            print(f"Upload failed: {resp.text}")
            return None
    except Exception as e:
        print(f"Upload error: {e}")
        return None

def check_timeline(retries=10, delay=5):
    print("Checking timeline for extracted events...")
    for i in range(retries):
        try:
            resp = requests.get(f"{API_URL}/timeline/{CASE_ID}")
            if resp.status_code == 200:
                events = resp.json()
                if events:
                    print(f"Found {len(events)} timeline events!")
                    for event in events:
                        print(f"- {event.get('event_date')}: {event.get('title')}")
                    return True
                else:
                    print(f"No events yet... ({i+1}/{retries})")
            else:
                print(f"Timeline fetch failed: {resp.status_code}")
                print(f"Response: {resp.text}")
        except Exception as e:
            print(f"Timeline check error: {e}")
        
        time.sleep(delay)
    return False

def main():
    print("Waiting for API to be ready...")
    for _ in range(12):
        if check_health():
            break
        time.sleep(5)
    else:
        print("API did not become ready.")
        sys.exit(1)

    doc_id = upload_document()
    if not doc_id:
        sys.exit(1)

    # Trigger manual analysis just in case auto-trigger is slow or disabled
    # requests.post(f"{API_URL}/intelligence/{CASE_ID}/analyze")
    
    if check_timeline():
        print("SUCCESS: Intelligence Upgrade Verified!")
    else:
        print("FAILURE: No timeline events extracted.")
        sys.exit(1)

if __name__ == "__main__":
    main()
