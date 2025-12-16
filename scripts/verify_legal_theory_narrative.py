#!/usr/bin/env python3
"""
Verification script for Phase 2.3.2: Legal Theory & Narrative (Swarm Analysis)
Tests that all mock endpoints have been replaced with real LLM implementations.
"""

import requests
import json

BASE_URL = "http://localhost:8001/api"

def test_narrative_branching():
    """Test the branching narrative endpoint."""
    print("\n--- Testing Narrative Branching ---")
    url = f"{BASE_URL}/narrative/test_case/branching"
    payload = {
        "pivot_point": "Witness testimony on 2023-06-15",
        "alternative_fact": "The witness was abroad on vacation during the incident"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            # Check if it's NOT the hardcoded response
            if "The defendant's alibi becomes credible" not in data.get("narrative", ""):
                print(f"[PASS] Got dynamic narrative (not hardcoded)")
                print(f"   Scenario ID: {data.get('scenario_id')}")
                print(f"   Narrative preview: {data.get('narrative', '')[:100]}...")
                print(f"   Implications: {len(data.get('implications', []))} items")
                return True
            else:
                print(f"[FAIL] Got hardcoded mock response")
                return False
        else:
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_narrative_story_arc():
    """Test the story arc endpoint."""
    print("\n--- Testing Narrative Story Arc ---")
    url = f"{BASE_URL}/narrative/test_case/story_arc"
    
    try:
        response = requests.get(url, timeout=60)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            points = data.get("points", [])
            
            # Check if it's NOT the hardcoded 5-point response
            hardcoded_events = ["Initial Meeting", "Contract Signed", "First Breach", "Confrontation", "Lawsuit Filed"]
            actual_events = [p.get("event") for p in points]
            
            if actual_events != hardcoded_events:
                print(f"[PASS] Got dynamic story arc (not hardcoded)")
                print(f"   Points: {len(points)}")
                for p in points[:3]:
                    print(f"   - {p.get('timestamp')}: {p.get('event')} (tension: {p.get('tension_level')})")
                return True
            else:
                # Empty is OK if there's no timeline data
                if len(points) == 0:
                    print(f"[PASS] Got empty story arc (no timeline data)")
                    return True
                print(f"[FAIL] Got hardcoded mock response")
                return False
        else:
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_match_precedents():
    """Test the match_precedents endpoint."""
    print("\n--- Testing Match Precedents ---")
    url = f"{BASE_URL}/legal_theory/match_precedents"
    payload = {
        "case_facts": "Plaintiff alleges that defendant breached a contract for software development services by failing to deliver the promised features within the agreed timeline. Defendant claims force majeure due to COVID-19.",
        "jurisdiction": "federal"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if it's NOT the hardcoded response
            hardcoded_cases = ["Smith v. Jones", "State v. Doe"]
            actual_cases = [p.get("case_name") for p in data]
            
            if not any(c in actual_cases for c in hardcoded_cases):
                print(f"[PASS] Got dynamic precedents (not hardcoded)")
                print(f"   Found {len(data)} precedents:")
                for p in data[:3]:
                    print(f"   - {p.get('case_name')} ({p.get('citation')}): {p.get('similarity_score')}")
                return True
            else:
                print(f"[FAIL] Got hardcoded mock response")
                print(f"   Cases: {actual_cases}")
                return False
        else:
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_jury_resonance():
    """Test the jury_resonance endpoint."""
    print("\n--- Testing Jury Resonance ---")
    url = f"{BASE_URL}/legal_theory/jury_resonance"
    payload = {
        "argument": "The defendant acted with reckless disregard for public safety when they ignored repeated warnings about the structural defects in the building.",
        "jury_demographics": {
            "age_group": "30-50",
            "education": "college-educated",
            "profession": "mixed"
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if it's NOT the hardcoded response
            hardcoded_feedback = "The argument appeals strongly to logic but may alienate younger jurors"
            
            if hardcoded_feedback not in data.get("feedback", ""):
                print(f"[PASS] Got dynamic jury resonance (not hardcoded)")
                print(f"   Score: {data.get('score')}")
                print(f"   Feedback: {data.get('feedback', '')[:100]}...")
                print(f"   Demographics: {data.get('demographic_breakdown')}")
                return True
            else:
                print(f"[FAIL] Got hardcoded mock response")
                return False
        else:
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Phase 2.3.2 Verification: Legal Theory & Narrative")
    print("=" * 60)
    
    results = {
        "narrative_branching": test_narrative_branching(),
        "narrative_story_arc": test_narrative_story_arc(),
        "match_precedents": test_match_precedents(),
        "jury_resonance": test_jury_resonance(),
    }
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + ("ALL TESTS PASSED!" if all_passed else "SOME TESTS FAILED"))
