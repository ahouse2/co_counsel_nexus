import urllib.request
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(name, method, url, payload=None):
    print(f"Testing {name} ({method} {url})...")
    full_url = f"{BASE_URL}{url}"
    try:
        data = None
        headers = {}
        if payload:
            data = json.dumps(payload).encode('utf-8')
            headers = {'Content-Type': 'application/json'}
        
        req = urllib.request.Request(full_url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req) as response:
            print(f"Status: {response.status}")
            if 200 <= response.status < 400:
                print("SUCCESS")
                return True
            else:
                print(f"FAILURE: {response.read().decode()}")
                return False
    except urllib.request.HTTPError as e:
        print(f"HTTP ERROR: {e.code} - {e.read().decode()}")
        return False
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return False

def main():
    results = {}
    
    # 1. Graph Query
    results["Graph"] = test_endpoint(
        "Graph Query", 
        "POST", 
        "/api/graph/query", 
        {"query": "MATCH (n) RETURN n LIMIT 1"}
    )
    
    # 2. Context Retrieval
    results["Context"] = test_endpoint(
        "Context Retrieval", 
        "POST", 
        "/api/retrieval", 
        {"query": "test query", "mode": "hybrid"}
    )
    
    # 3. Agents Invoke (Fixed path)
    results["Agents"] = test_endpoint(
        "Agents Invoke", 
        "POST", 
        "/agents/invoke", 
        {"session_id": "test", "agent_name": "qa_agent", "prompt": "hello"}
    )

    print("\n--- SUMMARY ---")
    all_pass = True
    for name, success in results.items():
        print(f"{name}: {'PASS' if success else 'FAIL'}")
        if not success:
            all_pass = False

    if all_pass:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
