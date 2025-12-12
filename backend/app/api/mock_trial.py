from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Literal
import json
import random # Keep for fallback or simple ID generation
from backend.app.services.llm_service import get_llm_service
from backend.app.services.legal_theory_engine import LegalTheoryEngine

router = APIRouter(prefix="/mock-trial", tags=["Mock Trial Arena"])

GamePhase = Literal['idle', 'openingStatement', 'playerTurn', 'opponentTurn', 'closingStatement', 'gameOver']
PlayerAction = Literal['presentEvidence', 'object', 'crossExamine', 'rest', 'startTrial']

class GameState(BaseModel):
    phase: GamePhase
    playerHealth: int
    opponentHealth: int
    currentEvidence: Optional[str]
    log: List[str]
    score: int
    message: str
    availableActions: List[PlayerAction]

class GameActionRequest(BaseModel):
    action: PlayerAction
    payload: Optional[Dict[str, Any]] = None

# In-memory game state
current_game_state: GameState = GameState(
    phase='idle',
    playerHealth=100,
    opponentHealth=100,
    currentEvidence=None,
    log=[],
    score=0,
    message='Welcome to the Mock Trial Arena! Press Enter to Start.',
    availableActions=['startTrial'],
)

@router.post("/start", response_model=GameState)
async def start_mock_trial():
    """
    Initializes a new mock trial simulation.
    """
    global current_game_state
    current_game_state = GameState(
        phase='openingStatement',
        playerHealth=100,
        opponentHealth=100,
        currentEvidence=None,
        log=['Trial started. Opening statements begin!'],
        score=0,
        message='Opening statements begin!',
        availableActions=['presentEvidence', 'object'],
    )
    return current_game_state

async def simulate_turn(state: GameState, player_action: str, payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    from backend.app.agents.swarms_runner import get_swarms_runner
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    runner = get_swarms_runner()
    
    # Construct a prompt that encapsulates the game state for the Swarm
    prompt = f"""
    Context: Mock Trial Simulation.
    Role: You are the Orchestrator for the Litigation Support Crew.
    
    Current Game State:
    - Phase: {state.phase}
    - Player Health: {state.playerHealth}
    - Opponent Health: {state.opponentHealth}
    - Last Event: {state.log[-1] if state.log else "Start of Trial"}
    
    Player Action: {player_action}
    Player Payload: {payload}
    
    Task:
    1. Analyze the player's action.
    2. Determine the Opposing Counsel's counter-move (using the LitigationSupportCrew).
    3. Calculate damage/impact.
    4. Return a JSON object with:
       - player_damage_dealt: int (0-25)
       - opponent_damage_dealt: int (0-25)
       - log_entry: str (Narrative of what happened)
       - message: str (Short UI message)
       - opponent_action: str
    """
    
    # Run the synchronous Swarms runner in a thread to avoid blocking the async event loop
    loop = asyncio.get_event_loop()
    try:
        # We route to 'litigation_support' implicitly via the prompt keywords or we could force it.
        # The runner.route_and_run uses keywords. "Mock Trial" is in the prompt.
        response_text = await loop.run_in_executor(None, runner.route_and_run, prompt)
        
        # Parse the response
        # The Swarm should return the JSON string as requested.
        import json
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
            
        return json.loads(response_text.strip())
        
    except Exception as e:
        print(f"Swarms Execution Failed: {e}")
        # Fallback
        return {
            "player_damage_dealt": 0,
            "opponent_damage_dealt": 0,
            "log_entry": f"The court is in recess due to a technical difficulty: {e}",
            "message": "Agent Error",
            "opponent_action": "rest"
        }

@router.post("/action", response_model=GameState)
async def perform_game_action(request: GameActionRequest):
    """
    Processes a player action and returns the updated game state, including opponent's response.
    """
    global current_game_state

    if current_game_state.phase == 'gameOver':
        raise HTTPException(status_code=400, detail="Game is over. Start a new trial.")
    if request.action not in current_game_state.availableActions:
        raise HTTPException(status_code=400, detail=f"Action '{request.action}' not available in current phase.")

    # Simulate the turn using LLM
    simulation_result = await simulate_turn(current_game_state, request.action, request.payload)
    
    # Update state based on simulation
    player_dmg = simulation_result.get("player_damage_dealt", 0)
    opponent_dmg = simulation_result.get("opponent_damage_dealt", 0)
    
    current_game_state.opponentHealth = max(0, current_game_state.opponentHealth - player_dmg)
    current_game_state.playerHealth = max(0, current_game_state.playerHealth - opponent_dmg)
    
    current_game_state.score += player_dmg - (opponent_dmg // 2)
    current_game_state.log.append(simulation_result.get("log_entry", ""))
    current_game_state.message = simulation_result.get("message", "")
    
    # Determine next phase
    if current_game_state.playerHealth <= 0 or current_game_state.opponentHealth <= 0:
        current_game_state.phase = 'gameOver'
        current_game_state.message = "You Lost the Case!" if current_game_state.playerHealth <= 0 else "You Won the Case!"
        current_game_state.availableActions = []
    else:
        # For simplicity in this turn-based model, we assume one exchange per request
        current_game_state.phase = 'playerTurn'
        current_game_state.availableActions = ['presentEvidence', 'object', 'rest']

    return current_game_state

@router.get("/state", response_model=GameState)
async def get_game_state():
    """
    Retrieves the current state of the mock trial simulation.
    """
    return current_game_state

@router.post("/evaluate", response_model=Dict[str, Any])
async def evaluate_game_state(payload: Dict[str, Any]):
    """
    Evaluates the current game state or a specific action against legal theories.
    """
    engine = LegalTheoryEngine()
    try:
        # Use the engine to evaluate (we can reuse suggest_theories or add a specific evaluate method)
        # For now, let's ask for suggestions based on the payload as context
        suggestions = await engine.suggest_theories()
        return {
            "evaluation_result": "Evaluation complete.",
            "theories": suggestions,
            "context_analysis": f"Analyzed payload: {payload}" 
        }
    except Exception as e:
        return {"evaluation_result": f"Error during evaluation: {str(e)}"}
