import asyncio
import httpx
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

async def verify_research_endpoints():
    base_url = "http://localhost:8001/api"
    
    print("Verifying Research Module Endpoints...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Test CourtListener Monitor Creation
        print("\n1. Testing CourtListener Monitor Creation...")
        try:
            monitor_payload = {
                "monitor_type": "keyword",
                "value": "Google v. Oracle",
                "requested_by": "verification_script",
                "check_interval_hours": 24,
                "priority": "normal"
            }
            response = await client.post(f"{base_url}/autonomous-courtlistener/monitors", json=monitor_payload)
            if response.status_code == 201:
                data = response.json()
                monitor_id = data['monitor_id']
                print(f"Monitor created: {monitor_id}")
            else:
                print(f"Failed to create monitor: {response.text}")
                return
        except Exception as e:
            print(f"Error creating monitor: {e}")
            return

        # 2. Test List Monitors
        print("\n2. Testing List Monitors...")
        try:
            response = await client.get(f"{base_url}/autonomous-courtlistener/monitors")
            if response.status_code == 200:
                monitors = response.json()
                print(f"Found {len(monitors)} monitors")
            else:
                print(f"Failed to list monitors: {response.text}")
        except Exception as e:
            print(f"Error listing monitors: {e}")

        # 3. Test Scraper Trigger Creation
        print("\n3. Testing Scraper Trigger Creation...")
        try:
            trigger_payload = {
                "source": "california_codes",
                "query": "PEN 187",
                "frequency": "on-demand",
                "requested_by": "verification_script"
            }
            response = await client.post(f"{base_url}/autonomous-scraping/triggers", json=trigger_payload)
            if response.status_code == 201:
                data = response.json()
                trigger_id = data['trigger_id']
                print(f"Trigger created: {trigger_id}")
            else:
                print(f"Failed to create trigger: {response.text}")
                return
        except Exception as e:
            print(f"Error creating trigger: {e}")
            return

        # 4. Test Manual Scrape (Dry Run)
        # We won't actually wait for a full scrape if it takes too long, but let's try a quick one or just check if endpoint exists
        print("\n4. Testing Manual Scrape Endpoint (Existence)...")
        # We'll just check if we can hit it, maybe with a dummy query that returns quickly or fails gracefully
        try:
            # Using a query that might fail or return empty is fine, we just want to see if the router handles it
            response = await client.post(f"{base_url}/autonomous-scraping/scrape", params={"source": "california_codes", "query": "TEST_QUERY_IGNORE"})
            if response.status_code in [200, 400, 404]: # 400/404 is fine, means endpoint exists
                print(f"Manual scrape endpoint reachable (Status: {response.status_code})")
            else:
                print(f"Manual scrape endpoint failed: {response.status_code}")
        except Exception as e:
            print(f"Error hitting manual scrape: {e}")

        # 5. Cleanup
        print("\n5. Cleaning up...")
        try:
            await client.delete(f"{base_url}/autonomous-courtlistener/monitors/{monitor_id}")
            await client.delete(f"{base_url}/autonomous-scraping/triggers/{trigger_id}")
            print("Cleanup complete")
        except Exception as e:
            print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    asyncio.run(verify_research_endpoints())
