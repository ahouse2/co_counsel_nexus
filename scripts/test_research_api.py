import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8001/api"

def test_courtlistener():
    print("\n--- Testing CourtListener API ---")
    
    # 1. Add Monitor
    print("Adding monitor...")
    payload = {
        "monitor_type": "keyword",
        "value": "Google v. Oracle",
        "requested_by": "test_script",
        "check_interval_hours": 24,
        "priority": "normal"
    }
    try:
        res = requests.post(f"{BASE_URL}/autonomous-courtlistener/monitors", json=payload)
        if res.status_code != 201:
            print(f"FAILED to add monitor: {res.text}")
            return
        monitor = res.json()
        print(f"Monitor added: {monitor['monitor_id']}")
        monitor_id = monitor['monitor_id']
    except Exception as e:
        print(f"Error: {e}")
        return

    # 2. List Monitors
    print("Listing monitors...")
    res = requests.get(f"{BASE_URL}/autonomous-courtlistener/monitors")
    monitors = res.json()
    print(f"Found {len(monitors)} monitors")

    # 3. Execute Monitor
    print(f"Executing monitor {monitor_id}...")
    res = requests.post(f"{BASE_URL}/autonomous-courtlistener/monitors/{monitor_id}/execute")
    result = res.json()
    print(f"Execution result: {result}")

    # 4. Remove Monitor
    print(f"Removing monitor {monitor_id}...")
    requests.delete(f"{BASE_URL}/autonomous-courtlistener/monitors/{monitor_id}")
    print("Monitor removed.")

def test_scraper():
    print("\n--- Testing Scraper API ---")
    
    # 1. Add Trigger
    print("Adding trigger...")
    payload = {
        "source": "california_codes",
        "query": "PEN 187",
        "frequency": "daily",
        "requested_by": "test_script",
        "priority": "normal"
    }
    try:
        res = requests.post(f"{BASE_URL}/autonomous-scraping/triggers", json=payload)
        if res.status_code != 201:
            print(f"FAILED to add trigger: {res.text}")
            return
        trigger = res.json()
        print(f"Trigger added: {trigger['trigger_id']}")
        trigger_id = trigger['trigger_id']
    except Exception as e:
        print(f"Error: {e}")
        return

    # 2. Execute Trigger
    print(f"Executing trigger {trigger_id}...")
    res = requests.post(f"{BASE_URL}/autonomous-scraping/triggers/{trigger_id}/execute")
    result = res.json()
    print(f"Execution result: {result}")

    # 3. Manual Scrape
    print("Running manual scrape...")
    # Test with example.com which is reliable
    res = requests.post(f"{BASE_URL}/autonomous-scraping/scrape", params={"source": "generic", "query": "https://example.com"})
    print(f"Manual scrape result: {res.json()}")

if __name__ == "__main__":
    try:
        test_courtlistener()
        test_scraper()
    except Exception as e:
        print(f"Test failed: {e}")
