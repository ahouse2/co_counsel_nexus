from dataclasses import dataclass
from backend.app.services.knowledge_graph_service import KnowledgeGraphService
from backend.ingestion.llama_index_factory import BaseLlmService
from backend.app.knowledge_graph.schema import KnowledgeGraphData, BaseNode, BaseRelationship
from typing import List, Dict, Any, Optional
import json


@dataclass(slots=True)
class ReasoningEngine:
    llm_service: BaseLlmService
    knowledge_graph_service: KnowledgeGraphService

    def analyze_and_summarize_case(self, case_id: str) -> str:
        """
        Analyzes the case context from the knowledge graph, generates a summary using an LLM,
        and stores the summary back into the knowledge graph.
        """
        # 1. Load the case context from the knowledge graph.
        query = """
        MATCH (c:Case {identity: $case_id})
        CALL apoc.path.subgraphAll(c, {
            maxLevel: 5
        })
        YIELD nodes, relationships
        RETURN nodes, relationships
        """
        parameters = {"case_id": case_id}
        
        graph_data = self.knowledge_graph_service.get_graph_data(query, parameters)

        if not graph_data.nodes:
            return f"No data found for case {case_id}."

        # 2. Convert the graph data to a string representation for the LLM.
        graph_string = self._convert_graph_to_string(graph_data)

        # 3. Use an LLM to analyze the context and generate a summary.
        prompt = f"""
        Analyze the following case data from a knowledge graph and provide a concise summary.
        Focus on the key entities, relationships, and events.

        Case Data:
        {graph_string}
        """
        summary_text = self.llm_service.generate_text(prompt)

        # 4. Store the summary back into the knowledge graph.
        summary_identity = f"summary_{case_id}"
        summary_node = BaseNode(
            label="Summary",
            identity=summary_identity,
            properties={"text": summary_text, "case_id": case_id}
        )
        
        # Create a relationship between the Case and the Summary
        summary_relationship = BaseRelationship(
            source_node_label="Case",
            source_node_identity=case_id,
            target_node_label="Summary",
            target_node_identity=summary_identity,
            type="HAS_SUMMARY",
            properties={}
        )

        ingestion_data = KnowledgeGraphData(nodes=[summary_node], relationships=[summary_relationship])
        self.knowledge_graph_service.ingest_data(ingestion_data)

        return summary_text

    def _convert_graph_to_string(self, graph_data: KnowledgeGraphData) -> str:
        """Converts a KnowledgeGraphData object to a string representation."""
        nodes_str = "\n".join([f"Node: {node.label} - {json.dumps(node.properties)}" for node in graph_data.nodes])
        rels_str = "\n".join([f"Relationship: ({rel.source_node_identity})-[{rel.type}]->({rel.target_node_identity})" for rel in graph_data.relationships])
        return f"Nodes:\n{nodes_str}\n\nRelationships:\n{rels_str}"