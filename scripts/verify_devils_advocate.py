import requests
import sys
import time
import json

BASE_URL = "http://127.0.0.1:8001"
CASE_ID = "default_case"

def print_step(step_name):
    print(f"\n{'='*50}")
    print(f"STEP: {step_name}")
    print(f"{'='*50}")

def check_health():
    print_step("Checking API Health")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("[OK] API is healthy")
            return True
        else:
            print(f"[FAIL] API returned {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Could not connect to API: {e}")
        return False

def review_case():
    print_step("Reviewing Case (Devil's Advocate)")
    url = f"{BASE_URL}/api/devils-advocate/{CASE_ID}/review"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Weaknesses detected: {len(data)}")
            if len(data) > 0:
                print(f"First weakness: {data[0]['title']}")
            return True
        else:
            print(f"[FAIL] Failed to review case: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[FAIL] Exception during case review: {e}")
        return False

def generate_cross_exam():
    print_step("Simulating Cross-Examination")
    url = f"{BASE_URL}/api/devils-advocate/cross-examine"
    payload = {
        "witness_statement": "I saw the defendant enter the building at 10 PM.",
        "witness_profile": "Security Guard, 50 years old, wears glasses."
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Questions generated: {len(data)}")
            if len(data) > 0:
                print(f"First question: {data[0]['question']}")
            return True
        else:
            print(f"[FAIL] Failed to generate cross-exam: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[FAIL] Exception during cross-exam generation: {e}")
        return False

if __name__ == "__main__":
    if not check_health():
        sys.exit(1)
    
    if not review_case():
        sys.exit(1)
        
    if not generate_cross_exam():
        sys.exit(1)
        
    print("\n[SUCCESS] Devil's Advocate verification passed!")
