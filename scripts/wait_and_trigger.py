import time
import requests
import sys

HEALTH_URL = "http://localhost:8001/health"
INGEST_URL = "http://localhost:8001/api/documents/ingestion/local"
TIMEOUT = 600

def wait_for_api():
    start_time = time.time()
    print(f"Waiting for API at {HEALTH_URL}...")
    
    while True:
        try:
            response = requests.get(HEALTH_URL)
            if response.status_code == 200:
                print("API is healthy!")
                return True
        except requests.exceptions.RequestException:
            pass
            
        if time.time() - start_time > TIMEOUT:
            print("Timeout waiting for API.")
            return False
            
        time.sleep(5)

def trigger_ingestion():
    print("Triggering ingestion...")
    try:
        payload = {
            "case_id": "default_case",
            "directory_path": "test_ingest"
        }
        # Note: requests.post with data=... sends form-encoded, json=... sends JSON
        # The endpoint expects form data for these fields based on the FastAPI definition
        response = requests.post(INGEST_URL, data=payload)
        response.raise_for_status()
        print("Ingestion triggered successfully.")
        print(response.json())
    except Exception as e:
        print(f"Failed to trigger ingestion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if wait_for_api():
        trigger_ingestion()
    else:
        sys.exit(1)
