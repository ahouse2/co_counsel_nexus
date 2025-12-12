import requests
import sys

BASE_URL = "http://localhost:8001"

def trigger_ingestion():
    print("Triggering ingestion for 'user_upload'...")
    case_id = "default_case"
    directory_path = "user_upload"
    
    url = f"{BASE_URL}/api/documents/ingestion/local"
    data = {
        "case_id": case_id,
        "directory_path": directory_path
    }
    
    try:
        response = requests.post(url, data=data, timeout=300)
        
        if response.status_code == 200:
            print("✅ Ingestion successfully queued!")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"❌ Ingestion failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error triggering ingestion: {str(e)}")
        return False

if __name__ == "__main__":
    if trigger_ingestion():
        sys.exit(0)
    else:
        sys.exit(1)
