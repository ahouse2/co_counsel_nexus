import requests
import json
import sys
import time

BASE_URL = "http://localhost:8001"
CASE_ID = "default_case"

def print_pass(message):
    print(f"PASS: {message}")

def print_fail(message, error=None):
    print(f"FAIL: {message}")
    if error:
        print(f"   Error: {error}")

def test_timeline():
    print("\n--- Testing Timeline Module ---")
    try:
        # 1. Get Timeline
        res = requests.get(f"{BASE_URL}/api/timeline/{CASE_ID}")
        if res.status_code == 200:
            events = res.json()
            if isinstance(events, list):
                print_pass(f"Get Timeline (Events: {len(events)})")
            else:
                print_pass(f"Get Timeline (Events: {len(events.get('events', []))})")
        else:
            print_fail(f"Get Timeline (Status: {res.status_code})", res.text)

    except Exception as e:
        print_fail("Timeline Exception", str(e))

def test_evidence_map():
    print("\n--- Testing Evidence Map Module ---")
    try:
        # 1. Get Map
        res = requests.get(f"{BASE_URL}/api/evidence-map/{CASE_ID}")
        if res.status_code == 200:
            data = res.json()
            print_pass(f"Get Evidence Map (Nodes: {len(data.get('mapping', {}))})")
        else:
            print_fail(f"Get Evidence Map (Status: {res.status_code})", res.text)

    except Exception as e:
        print_fail("Evidence Map Exception", str(e))

def test_legal_theory():
    print("\n--- Testing Legal Theory Module ---")
    try:
        # 1. Get Suggestions
        res = requests.get(f"{BASE_URL}/api/legal_theory/suggestions?case_id={CASE_ID}")
        if res.status_code == 200:
            theories = res.json()
            print_pass(f"Get Suggestions (Count: {len(theories)})")
            
            if theories:
                cause = theories[0]['cause']
                # 2. Get Subgraph
                res_sub = requests.get(f"{BASE_URL}/api/legal_theory/{cause}/subgraph")
                if res_sub.status_code == 200:
                    print_pass(f"Get Subgraph for '{cause}'")
                else:
                    print_fail(f"Get Subgraph (Status: {res_sub.status_code})", res_sub.text)
        else:
            print_fail(f"Get Suggestions (Status: {res.status_code})", res.text)

    except Exception as e:
        print_fail("Legal Theory Exception", str(e))

def test_jury_sentiment():
    print("\n--- Testing Jury Sentiment Module ---")
    try:
        # 1. Analyze Argument
        arg_payload = {"text": "The defendant was negligent because they ignored safety protocols."}
        res = requests.post(f"{BASE_URL}/api/jury-sentiment/analyze-argument", json=arg_payload)
        if res.status_code == 200:
            print_pass("Analyze Argument")
        else:
            print_fail(f"Analyze Argument (Status: {res.status_code})", res.text)

        # 2. Simulate Individuals
        jurors = [
            {"id": "j1", "name": "Juror 1", "demographics": "Age 30", "occupation": "Engineer", "bias": "Logical", "temperament": "Calm"}
        ]
        sim_payload = {
            "argument": "The evidence is irrefutable.",
            "jurors": jurors
        }
        res_sim = requests.post(f"{BASE_URL}/api/jury-sentiment/simulate-individuals", json=sim_payload)
        if res_sim.status_code == 200:
            print_pass("Simulate Individual Jurors")
        else:
            print_fail(f"Simulate Individual Jurors (Status: {res_sim.status_code})", res_sim.text)

    except Exception as e:
        print_fail("Jury Sentiment Exception", str(e))

if __name__ == "__main__":
    print("Starting Phase 3 & 4 Verification...")
    
    # Ensure API is up
    try:
        requests.get(f"{BASE_URL}/health", timeout=10)
    except:
        print("API seems down. Please ensure backend is running on port 8001.")
        sys.exit(1)

    test_timeline()
    test_evidence_map()
    test_legal_theory()
    test_jury_sentiment()
    
    print("\nVerification Complete.")
