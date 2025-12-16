import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.services.dev_agent import get_dev_agent_service

async def main():
    print("Initializing Dev Agent Service...")
    service = get_dev_agent_service()
    
    print("Scanning for tasks in /src/repo/task.md...")
    # Note: This expects the task.md to be present in the repo root inside the container
    result = await service.scan_and_execute_next_task()
    
    print("Execution Result:")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
