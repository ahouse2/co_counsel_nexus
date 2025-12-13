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

def generate_narrative():
    print_step("Generating Narrative")
    url = f"{BASE_URL}/api/narrative/{CASE_ID}/generate"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            narrative = data.get("narrative")
            if narrative:
                print(f"[OK] Narrative generated successfully. Length: {len(narrative)}")
                print(f"Preview: {narrative[:100]}...")
                return True
            else:
                print("[FAIL] Narrative field missing or empty")
                return False
        else:
            print(f"[FAIL] Failed to generate narrative: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[FAIL] Exception during narrative generation: {e}")
        return False

def detect_contradictions():
    print_step("Detecting Contradictions")
    url = f"{BASE_URL}/api/narrative/{CASE_ID}/contradictions"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Contradictions detected. Count: {len(data)}")
            if len(data) > 0:
                print(f"First contradiction: {data[0]}")
            return True
        else:
            print(f"[FAIL] Failed to detect contradictions: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[FAIL] Exception during contradiction detection: {e}")
        return False

if __name__ == "__main__":
    if not check_health():
        sys.exit(1)
    
    if not generate_narrative():
        sys.exit(1)
        
    if not detect_contradictions():
        sys.exit(1)
        
    print("\n[SUCCESS] Narrative Weaver verification passed!")
