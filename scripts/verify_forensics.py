import requests
import os
import sys
import time
import json

# Configuration
API_URL = "http://127.0.0.1:8001/api"
DOC_ID = "test_forensic_doc"
CASE_ID = "default_case"

def print_step(step):
    print(f"\n{'='*50}")
    print(f"STEP: {step}")
    print(f"{'='*50}")

def verify_forensics():
    print_step("Checking API Health")
    try:
        # Health endpoint is at root /health, not /api/health
        base_url = API_URL.replace("/api", "")
        resp = requests.get(f"{base_url}/health")
        if resp.status_code == 200:
            print("[OK] API is healthy")
        else:
            print(f"[FAIL] API is unhealthy: {resp.status_code}")
            return
    except Exception as e:
        print(f"[FAIL] Could not connect to API: {e}")
        return

    # 1. Upload a test document (if not exists)
    # For simplicity, we'll try to use an existing one or just skip upload if we can find one
    # Let's list documents first
    print_step("Listing Documents")
    try:
        resp = requests.get(f"{API_URL}/documents/?case_id={CASE_ID}")
        if resp.status_code == 200:
            docs = resp.json()
            if not docs:
                print("[WARN] No documents found. Uploading a test document...")
                # Create a dummy document
                dummy_filename = "test_forensic.txt"
                with open(dummy_filename, "w") as f:
                    f.write("This is a test document for forensic verification.")
                
                # Upload
                upload_url = f"{API_URL}/documents/upload"
                files = None
                try:
                    with open(dummy_filename, 'rb') as f:
                        files = {'file': (dummy_filename, f, 'text/plain')}
                        params = {'case_id': CASE_ID, 'doc_type': 'my_documents'}
                        resp = requests.post(upload_url, files=files, params=params)
                    
                    if resp.status_code == 200:
                        result = resp.json()
                        doc_id = result['data']['doc_id']
                        print(f"[OK] Uploaded test document: {doc_id}")
                        # Wait a bit for processing if needed
                        time.sleep(2)
                    else:
                        print(f"[FAIL] Failed to upload document: {resp.status_code} - {resp.text}")
                        return
                except Exception as e:
                    print(f"[FAIL] Error uploading document: {e}")
                    return
                finally:
                    # Clean up dummy file
                    if os.path.exists(dummy_filename):
                        try:
                            os.remove(dummy_filename)
                        except Exception as e:
                            print(f"[WARN] Could not remove dummy file: {e}")
            else:
                target_doc = docs[0]
                doc_id = target_doc['id']
                print(f"[OK] Found document: {doc_id} ({target_doc.get('name')})")
        else:
            print(f"[FAIL] Failed to list documents: {resp.status_code}")
            return
    except Exception as e:
        print(f"[FAIL] Error listing/uploading documents: {e}")
        return

    # 2. Check Forensic Metadata (Hash)
    print_step(f"Checking Forensic Metadata for {doc_id}")
    try:
        resp = requests.get(f"{API_URL}/forensics/{doc_id}?case_id={CASE_ID}")
        if resp.status_code == 200:
            meta = resp.json()
            print(f"Metadata: {json.dumps(meta, indent=2)}")
            if "hash_sha256" in meta:
                print(f"[OK] SHA-256 Hash found: {meta['hash_sha256']}")
            else:
                print("[WARN] SHA-256 Hash NOT found (might be pending or old doc)")
        else:
            print(f"[FAIL] Failed to get metadata: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"[FAIL] Error getting metadata: {e}")

    # 3. Check Hex View
    print_step(f"Checking Hex View for {doc_id}")
    try:
        resp = requests.get(f"{API_URL}/forensics/{doc_id}/hex?case_id={CASE_ID}")
        if resp.status_code == 200:
            hex_data = resp.json()
            print(f"Hex Data Keys: {hex_data.keys()}")
            if "head" in hex_data and "tail" in hex_data:
                print(f"[OK] Hex Data received. Head length: {len(hex_data['head'])}")
            else:
                print("[FAIL] Invalid Hex Data structure")
        else:
            print(f"[FAIL] Failed to get hex view: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"[FAIL] Error getting hex view: {e}")

    # 4. Trigger Deep Analysis
    print_step(f"Triggering Deep Analysis for {doc_id}")
    try:
        # This might take time, so we just trigger it and check the response structure
        resp = requests.post(f"{API_URL}/forensics/{doc_id}/analyze?case_id={CASE_ID}")
        if resp.status_code == 200:
            analysis = resp.json()
            print(f"Analysis Result: {json.dumps(analysis, indent=2)}")
            
            # Verify structure matches ForensicAnalysisResult
            required_keys = ["tamper_score", "overall_verdict"]
            if all(k in analysis for k in required_keys):
                print("[OK] Analysis Result structure is valid")
                print(f"Verdict: {analysis['overall_verdict']}")
                print(f"Tamper Score: {analysis['tamper_score']['score']}")
            else:
                print(f"[FAIL] Invalid Analysis Result structure. Missing keys. Got: {analysis.keys()}")
        else:
            print(f"[FAIL] Failed to trigger analysis: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"[FAIL] Error triggering analysis: {e}")

if __name__ == "__main__":
    verify_forensics()
