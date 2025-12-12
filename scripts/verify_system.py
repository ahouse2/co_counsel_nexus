import requests
import sys
import os
import time

BASE_URL = "http://localhost:8001"
FRONTEND_URL = "http://localhost:8088"

def check_api_health():
    try:
        print(f"Checking API health at {BASE_URL}/health...")
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is healthy")
            return True
        else:
            print(f"❌ API returned status code {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API")
        return False

def check_frontend_health():
    try:
        print(f"Checking Frontend health at {FRONTEND_URL}...")
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            print("✅ Frontend is accessible")
            return True
        else:
            print(f"❌ Frontend returned status code {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Frontend")
        return False

def test_local_ingestion():
    print("\nTesting Local Ingestion...")
    case_id = "default_case"
    directory_path = "test_ingest"
    
    # Ensure test data exists (this script assumes it's running on the host where /data is mounted)
    # But the API container sees /data. 
    # We need to trigger the endpoint.
    
    url = f"{BASE_URL}/api/documents/ingestion/local"
    data = {
        "case_id": case_id,
        "directory_path": directory_path
    }
    
    try:
        print(f"Triggering local ingestion for path: {directory_path}")
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            print("✅ Local ingestion request successful")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"❌ Local ingestion failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error testing local ingestion: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting System Verification...")
    
    api_ok = check_api_health()
    frontend_ok = check_frontend_health()
    
    if api_ok:
        ingestion_ok = test_local_ingestion()
    else:
        print("Skipping ingestion test due to API failure")
        ingestion_ok = False
        
    if api_ok and frontend_ok and ingestion_ok:
        print("\n✅ System Verification Passed")
        sys.exit(0)
    else:
        print("\n❌ System Verification Failed")
        sys.exit(1)
