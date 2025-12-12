from typing import List, Dict, Any, Tuple
import json
from backend.app.services.llm_service import get_llm_service
from backend.app.services.knowledge_graph_service import get_knowledge_graph_service

class LegalTheoryEngine:
    def __init__(self):
        self.llm_service = get_llm_service()
        self.kg_service = get_knowledge_graph_service()

    async def suggest_theories(self, case_id: str = None) -> List[Dict[str, Any]]:
        """
        Generates legal theory suggestions based on case facts from the Knowledge Graph.
        """
        context_str = "Hypothetical civil litigation case involving breach of contract and negligence."
        
        if case_id:
            # Fetch facts from the Knowledge Graph
            try:
                # Get all entities and relationships for the case (simplified query)
                # In a real scenario, we'd use a more targeted RAG approach
                query = f"""
                MATCH (n)-[r]->(m)
                WHERE n.case_id = '{case_id}' OR m.case_id = '{case_id}'
                RETURN n, r, m LIMIT 50
                """
                graph_data = await self.kg_service.query_graph(query)
                if graph_data:
                    context_str = f"Case Facts from Knowledge Graph: {json.dumps(graph_data, default=str)}"
            except Exception as e:
                print(f"Error fetching graph data: {e}")

        prompt = f"""
        Context: {context_str}
        
        Generate 3 potential legal theories for this case.
        Return the result as a JSON list of objects with the following keys:
        - cause: str (Name of the legal theory)
        - score: float (Confidence score 0.0-1.0)
        - elements: list of objects {{name: str, description: str}}
        - defenses: list of strings
        - indicators: list of strings (Facts that support this theory)
        - missing_elements: list of strings
        
        Ensure the output is valid JSON.
        """
        response_text = await self.llm_service.generate_text(prompt)
        try:
            # Clean up potential markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            theories = json.loads(response_text.strip())
            return theories
        except json.JSONDecodeError:
            print(f"Failed to parse LLM response: {response_text}")
            return []

    async def get_theory_subgraph(self, cause: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Generates a graph representation of a legal theory.
        """
        prompt = f"""
        Generate a graph representation for the legal theory: "{cause}".
        Return the result as a JSON object with two keys:
        - nodes: list of objects {{id: str, label: str, type: str}}
        - edges: list of objects {{source: str, target: str, label: str}}
        
        Include nodes for elements, defenses, and key concepts.
        Ensure the output is valid JSON.
        """
        response_text = await self.llm_service.generate_text(prompt)
        try:
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
                
            graph_data = json.loads(response_text.strip())
            return graph_data.get("nodes", []), graph_data.get("edges", [])
        except json.JSONDecodeError:
            print(f"Failed to parse LLM response: {response_text}")
            return [], []

    def close(self):
        pass
