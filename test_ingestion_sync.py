import requests
import os
import time

BASE_URL = "http://localhost:8001/api"
# Use the 'data' directory which is mounted to /data in the container
HOST_TEST_DIR = "data/test_ingest_sync"
CONTAINER_TEST_PATH = "/data/test_ingest_sync"

def create_dummy_files():
    if not os.path.exists(HOST_TEST_DIR):
        os.makedirs(HOST_TEST_DIR)
    
    with open(f"{HOST_TEST_DIR}/file1.txt", "w") as f:
        f.write("This is file 1 content.")
    
    with open(f"{HOST_TEST_DIR}/file2.txt", "w") as f:
        f.write("This is file 2 content.")

def test_ingestion_sync():
    print("Testing Ingestion Sync...")
    create_dummy_files()
    
    # 1. First Ingestion (Normal)
    print(f"1. Ingesting {CONTAINER_TEST_PATH} (First Run)...")
    response = requests.post(
        f"{BASE_URL}/ingestion/ingest_local_path", 
        data={"source_path": CONTAINER_TEST_PATH, "document_id": "sync_test", "recursive": True, "sync": False}
    )
    if response.status_code != 200:
        print(f"Failed to ingest: {response.text}")
        return
    job_id = response.json()["job_id"]
    print(f"   Job ID: {job_id}")
    
    # Wait for processing (mock wait)
    time.sleep(2)
    
    # 2. Second Ingestion (Sync=True, No Changes)
    print("2. Ingesting (Sync=True, No Changes)...")
    response = requests.post(
        f"{BASE_URL}/ingestion/ingest_local_path", 
        data={"source_path": CONTAINER_TEST_PATH, "document_id": "sync_test", "recursive": True, "sync": True}
    )
    if response.status_code != 200:
        print(f"Failed to ingest: {response.text}")
        return
    
    result = response.json()
    print(f"   Result: {result}")
    
    # Check if it says "skipped" or returns a job_id
    if result.get("job_id") == "skipped":
        print("   SUCCESS: All files skipped as expected.")
    else:
        print("   WARNING: Job created, check logs to see if files were actually skipped inside the job.")

    # 3. Modify a file and Ingest (Sync=True)
    print("3. Modifying file1.txt and Ingesting (Sync=True)...")
    with open(f"{HOST_TEST_DIR}/file1.txt", "w") as f:
        f.write("This is file 1 content MODIFIED.")
        
    response = requests.post(
        f"{BASE_URL}/ingestion/ingest_local_path", 
        data={"source_path": CONTAINER_TEST_PATH, "document_id": "sync_test", "recursive": True, "sync": True}
    )
    result = response.json()
    print(f"   Result: {result}")
    
    if result.get("job_id") != "skipped":
        print("   SUCCESS: Job created for modified file.")
    else:
        print("   FAILURE: Modified file was skipped!")

    print("Ingestion Sync Test Completed!")

if __name__ == "__main__":
    try:
        test_ingestion_sync()
    except Exception as e:
        print(f"Test failed with error: {e}")
