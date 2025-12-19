"""
Phase 6 Verification Script
Tests all Agent Console and swarm endpoints
"""

import requests

BASE_URL = "http://localhost:8001"

def test_endpoint(name, method, path, expected_status=200):
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            r = requests.get(url, timeout=10)
        else:
            r = requests.post(url, timeout=10)
        
        status = "[PASS]" if r.status_code == expected_status else "[FAIL]"
        print(f"{status} {name}: {r.status_code}")
        return r.json() if r.ok else None
    except Exception as e:
        print(f"[ERROR] {name}: {e}")
        return None

def main():
    print("=" * 60)
    print("PHASE 6: Enhanced Swarm Architecture Verification")
    print("=" * 60)
    print()
    
    # Test 1: Orchestrator Status
    print("[1] Orchestrator Status")
    data = test_endpoint("GET /api/agent-console/orchestrator", "GET", "/api/agent-console/orchestrator")
    if data:
        print(f"    Running: {data.get('running')}")
        print(f"    Handlers: {data.get('registered_handlers')}")
        print(f"    Events Processed: {data.get('processed_events')}")
    print()
    
    # Test 2: Swarm Status
    print("[2] Swarm Status")
    swarms = test_endpoint("GET /api/agent-console/swarms", "GET", "/api/agent-console/swarms")
    if swarms:
        print(f"    Swarm Count: {len(swarms)}")
        total = sum(s.get('agent_count', 0) for s in swarms)
        print(f"    Total Agents: {total}")
        for s in swarms[:5]:
            print(f"    - {s['name']}: {s['agent_count']} agents")
    print()
    
    # Test 3: Activity Feed
    print("[3] Activity Feed")
    data = test_endpoint("GET /api/agent-console/activity", "GET", "/api/agent-console/activity")
    if data is not None:
        print(f"    Activity Count: {len(data)}")
    print()
    
    # Test 4: Swarms Registry
    print("[4] Swarms Registry")
    data = test_endpoint("GET /api/swarms", "GET", "/api/swarms")
    if data:
        print(f"    Total Agents: {data.get('total_agents')}")
        print(f"    Swarms: {list(data.get('swarms', {}).keys())[:5]}")
    print()
    
    # Test 5: Pipeline Trigger
    print("[5] Pipeline Trigger")
    data = test_endpoint("POST /api/agent-console/trigger-pipeline/test_case", "POST", 
                        "/api/agent-console/trigger-pipeline/test_verification_case")
    if data:
        print(f"    Success: {data.get('success')}")
        print(f"    Message: {data.get('message')}")
    print()
    
    # Test 6: Messages Log
    print("[6] Messages Log")
    data = test_endpoint("GET /api/agent-console/messages", "GET", "/api/agent-console/messages")
    if data is not None:
        print(f"    Message Count: {len(data)}")
    print()
    
    print("=" * 60)
    print("Verification Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
