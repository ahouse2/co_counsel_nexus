import asyncio
import json
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.app.services.simulation_service import SimulationService

async def verify():
    print("Initializing SimulationService...")
    service = SimulationService()
    
    scenario = {
        "agent_role": "prosecution",
        "case_brief": "The defendant is accused of stealing a cookie from the cookie jar. Witness saw crumbs on his face.",
        "objectives": ["Prove guilt", "Emphasize the crumbs"],
        "initial_statement": "Ladies and gentlemen, the evidence is clear.",
        "max_turns": 2
    }
    
    print("Running simulation...")
    try:
        result = await service.run_mock_court_simulation(scenario)
        log = result["simulation_log"]
        
        print(f"Simulation completed with {len(log)} steps.")
        
        has_jury_reactions = False
        has_objection_logic = False # Hard to force, but we can check structure
        
        for step in log:
            print(f"[{step['role']}] {step.get('type', 'statement')}: {step.get('statement', '')[:50]}...")
            if "jury_reactions" in step:
                print(f"  - Jury Reactions: {len(step['jury_reactions'])}")
                has_jury_reactions = True
                for r in step['jury_reactions']:
                    print(f"    - Juror {r.get('juror_id')}: {r.get('reaction')} (Score: {r.get('sentiment_score')})")
            
            if step.get("type") == "objection":
                print("  - Objection detected!")
                has_objection_logic = True
                
        if has_jury_reactions:
            print("\nSUCCESS: Jury reactions detected in simulation log.")
        else:
            print("\nFAILURE: No jury reactions found.")
            
    except Exception as e:
        print(f"\nFAILURE: Simulation failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify())
