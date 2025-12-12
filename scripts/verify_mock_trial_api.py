import sys
import os
from pathlib import Path
import asyncio

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.app.api.mock_trial import simulate_turn, GameState

# Mock Game State
state = GameState(
    phase='playerTurn',
    playerHealth=100,
    opponentHealth=100,
    currentEvidence=None,
    log=['Trial Started'],
    score=0,
    message='Your turn',
    availableActions=['presentEvidence']
)

async def test_api():
    print("Testing Mock Trial API -> Swarms Integration...")
    
    action = "presentEvidence"
    payload = {"evidence": "Contract Exhibit A"}
    
    try:
        print(f"Simulating turn with action: {action}")
        result = await simulate_turn(state, action, payload)
        print(f"Result: {result}")
        
        if "log_entry" in result:
            print("SUCCESS: API returned structured response.")
        else:
            print("FAILURE: API returned unexpected format.")
            
    except Exception as e:
        print(f"FAILURE: API call failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_api())
