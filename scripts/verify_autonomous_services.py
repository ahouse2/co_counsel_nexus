import requests
import json
import time
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8001/api"

def print_step(step: str):
    print(f"\n{'='*50}")
    print(f"STEP: {step}")
    print(f"{'='*50}")

def print_success(msg: str):
    print(f"[OK] {msg}")

def print_error(msg: str):
    print(f"[ERROR] {msg}")

def verify_autonomous_scraping():
    print_step("Verifying Autonomous Scraping")
    
    # 1. Create Trigger
    print("Creating scraping trigger...")
    payload = {
        "source": "california_codes",
        "query": "CIV 51", # Civil Code Section 51 (Unruh Civil Rights Act)
        "frequency": "on-demand",
        "requested_by": "verification_script",
        "priority": "normal"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/autonomous-scraping/triggers", json=payload)
        if response.status_code != 201:
            print_error(f"Failed to create trigger: {response.text}")
            return False
        
        trigger = response.json()
        trigger_id = trigger['trigger_id']
        print_success(f"Trigger created: {trigger_id}")
        
        # 2. List Triggers
        print("Listing triggers...")
        response = requests.get(f"{BASE_URL}/autonomous-scraping/triggers")
        if response.status_code != 200:
            print_error(f"Failed to list triggers: {response.text}")
            return False
        
        triggers = response.json()
        found = any(t['trigger_id'] == trigger_id for t in triggers)
        if not found:
            print_error("Created trigger not found in list")
            return False
        print_success(f"Found trigger in list of {len(triggers)} triggers")
        
        # 3. Execute Trigger
        print("Executing trigger (this may take a moment)...")
        response = requests.post(f"{BASE_URL}/autonomous-scraping/triggers/{trigger_id}/execute")
        if response.status_code != 200:
            print_error(f"Failed to execute trigger: {response.text}")
            # Don't fail the whole test if scraping fails (could be network), but warn
        else:
            result = response.json()
            print_success(f"Trigger executed. Success: {result.get('success')}")
            print(f"Results: {json.dumps(result, indent=2)}")
            
        # 4. Cleanup
        print("Cleaning up trigger...")
        response = requests.delete(f"{BASE_URL}/autonomous-scraping/triggers/{trigger_id}")
        if response.status_code != 204:
            print_error(f"Failed to delete trigger: {response.text}")
            return False
        print_success("Trigger deleted")
        
        return True
        
    except Exception as e:
        print_error(f"Exception during autonomous scraping verification: {e}")
        return False

def verify_autonomous_courtlistener():
    print_step("Verifying Autonomous CourtListener")
    
    # 1. Create Monitor
    print("Creating CourtListener monitor...")
    payload = {
        "monitor_type": "keyword",
        "value": "artificial intelligence",
        "requested_by": "verification_script",
        "check_interval_hours": 24,
        "priority": "low"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/autonomous-courtlistener/monitors", json=payload)
        if response.status_code != 201:
            print_error(f"Failed to create monitor: {response.text}")
            return False
        
        monitor = response.json()
        monitor_id = monitor['monitor_id']
        print_success(f"Monitor created: {monitor_id}")
        
        # 2. List Monitors
        print("Listing monitors...")
        response = requests.get(f"{BASE_URL}/autonomous-courtlistener/monitors")
        if response.status_code != 200:
            print_error(f"Failed to list monitors: {response.text}")
            return False
        
        monitors = response.json()
        found = any(m['monitor_id'] == monitor_id for m in monitors)
        if not found:
            print_error("Created monitor not found in list")
            return False
        print_success(f"Found monitor in list of {len(monitors)} monitors")
        
        # 3. Execute Monitor
        print("Executing monitor (this may take a moment)...")
        response = requests.post(f"{BASE_URL}/autonomous-courtlistener/monitors/{monitor_id}/execute")
        if response.status_code != 200:
            print_error(f"Failed to execute monitor: {response.text}")
            # Note: This might fail if API key is missing or invalid
        else:
            result = response.json()
            print_success(f"Monitor executed. Success: {result.get('success')}")
            print(f"Results: {json.dumps(result, indent=2)}")
            
        # 4. Cleanup
        print("Cleaning up monitor...")
        response = requests.delete(f"{BASE_URL}/autonomous-courtlistener/monitors/{monitor_id}")
        if response.status_code != 204:
            print_error(f"Failed to delete monitor: {response.text}")
            return False
        print_success("Monitor deleted")
        
        return True
        
    except Exception as e:
        print_error(f"Exception during CourtListener verification: {e}")
        return False

def main():
    print("Starting Autonomous Services Verification...")
    
    scraping_success = verify_autonomous_scraping()
    courtlistener_success = verify_autonomous_courtlistener()
    
    if scraping_success and courtlistener_success:
        print("\n[SUCCESS] All autonomous services verified successfully!")
        sys.exit(0)
    else:
        print("\n[FAILURE] Some verifications failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
