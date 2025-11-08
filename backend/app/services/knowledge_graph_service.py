from __future__ import annotations
from typing import Any, Dict, List, Optional
from neo4j import AsyncGraphDatabase, AsyncSession
from fastapi import Depends

from backend.app.config import get_settings
from backend.app.knowledge_graph.schema import KnowledgeGraphData, BaseNode, BaseRelationship

class KnowledgeGraphService:
    """
    A service for interacting with the Neo4j Knowledge Graph.
    """

    def __init__(self):
        settings = get_settings()
        self.uri = settings.neo4j_uri
        self.user = settings.neo4j_user
        self.password = settings.neo4j_password
        self.driver = None

    async def _get_driver(self):
        if self.driver is None:
            self.driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))
            await self.driver.verify_connectivity()
        return self.driver

    async def _close_driver(self):
        if self.driver is not None:
            await self.driver.close()
            self.driver = None

    async def ingest_data(self, graph_data: KnowledgeGraphData):
        """
        Ingests nodes and relationships into the knowledge graph.
        """
        driver = await self._get_driver()
        async with driver.session() as session:
            for node in graph_data.nodes:
                await session.run(
                    f"MERGE (n:{node.label} {{id: $id}}) SET n += $properties",
                    id=node.id, properties=node.properties
                )
            for relationship in graph_data.relationships:
                await session.run(
                    f"""
                    MATCH (a:{relationship.source_node_label} {{id: $source_id}})
                    MATCH (b:{relationship.target_node_label} {{id: $target_id}})
                    MERGE (a)-[r:{relationship.type}]->(b) SET r += $properties
                    """,
                    source_id=relationship.source_id,
                    target_id=relationship.target_id,
                    properties=relationship.properties
                )

    async def get_graph_data(self, cypher_query: str, parameters: Optional[Dict[str, Any]] = None) -> KnowledgeGraphData:
        """
        Executes a Cypher query and returns structured graph data.
        """
        driver = await self._get_driver()
        async with driver.session() as session:
            result = await session.run(cypher_query, parameters)
            nodes = {}
            relationships = []

            for record in await result.data():
                for value in record.values():
                    if isinstance(value, dict): # Handle maps returned by Cypher
                        if 'id' in value and 'labels' in value: # Likely a node
                            node_id = value['id']
                            if node_id not in nodes:
                                nodes[node_id] = BaseNode(
                                    id=node_id,
                                    label=value['labels'][0] if value['labels'] else 'Node',
                                    properties={k: v for k, v in value.items() if k not in ['id', 'labels']}
                                )
                        elif 'type' in value and 'start' in value and 'end' in value: # Likely a relationship
                            relationships.append(BaseRelationship(
                                id=value['id'],
                                type=value['type'],
                                source_id=value['start']['id'],
                                target_id=value['end']['id'],
                                source_node_label=value['start']['labels'][0] if value['start']['labels'] else 'Node',
                                target_node_label=value['end']['labels'][0] if value['end']['labels'] else 'Node',
                                properties={k: v for k, v in value.items() if k not in ['id', 'type', 'start', 'end']}
                            ))
                    elif hasattr(value, 'id') and hasattr(value, 'labels'): # Neo4j Node object
                        node_id = value.id
                        if node_id not in nodes:
                            nodes[node_id] = BaseNode(
                                id=node_id,
                                label=value.labels[0] if value.labels else 'Node',
                                properties=dict(value)
                            )
                    elif hasattr(value, 'id') and hasattr(value, 'type') and hasattr(value, 'start_node') and hasattr(value, 'end_node'): # Neo4j Relationship object
                        relationships.append(BaseRelationship(
                            id=value.id,
                            type=value.type,
                            source_id=value.start_node.id,
                            target_id=value.end_node.id,
                            source_node_label=value.start_node.labels[0] if value.start_node.labels else 'Node',
                            target_node_label=value.end_node.labels[0] if value.end_node.labels else 'Node',
                            properties=dict(value)
                        ))

            return KnowledgeGraphData(nodes=list(nodes.values()), relationships=relationships)

    async def get_mermaid_graph(self, cypher_query: str, parameters: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Executes a Cypher query and returns a Mermaid graph definition string.
        """
        graph_data = await self.get_graph_data(cypher_query, parameters)
        if not graph_data.nodes and not graph_data.relationships:
            return None

        mermaid_definition = "graph TD\n"
        node_map = {} # To map node IDs to Mermaid-friendly IDs

        for i, node in enumerate(graph_data.nodes):
            mermaid_id = f"N{i}"
            node_map[node.id] = mermaid_id
            properties_str = ", ".join([f"{k}: {v}" for k, v in node.properties.items()])
            mermaid_definition += f'  {mermaid_id}["{node.label}<br>{node.id}<br>{properties_str}"]\n'

        for rel in graph_data.relationships:
            source_mermaid_id = node_map.get(rel.source_id)
            target_mermaid_id = node_map.get(rel.target_id)
            if source_mermaid_id and target_mermaid_id:
                properties_str = ", ".join([f"{k}: {v}" for k, v in rel.properties.items()])
                mermaid_definition += f'  {source_mermaid_id} -- "{rel.type}<br>{properties_str}" --> {target_mermaid_id}\n'
        
        return mermaid_definition

    async def get_case_summary(self, case_id: str) -> str:
        """
        Retrieves a summary of a case from the knowledge graph.
        """
        driver = await self._get_driver()
        async with driver.session() as session:
            query = """
                MATCH (c:Case {id: $case_id})
                RETURN c.summary AS summary
            """
            result = await session.run(query, case_id=case_id)
            record = await result.single()
            return record["summary"] if record else "No summary found for this case."

    async def add_entity(self, entity_type: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adds a new entity (node) to the Knowledge Graph.
        """
        driver = await self._get_driver()
        async with driver.session() as session:
            # Use MERGE to prevent duplicate nodes if called multiple times with the same ID
            query = (
                f"MERGE (n:{entity_type} {{id: $id}}) "
                "SET n += $properties "
                "RETURN properties(n) AS properties"
            )
            # Ensure 'id' is always present in properties for MERGE
            if 'id' not in properties:
                raise ValueError("Node properties must contain an 'id' field for MERGE operation.")
            
            result = await session.run(query, id=properties['id'], properties=properties)
            record = await result.single()
            return record["properties"] if record else {}

    async def add_relationship(self, 
                               from_entity_id: str, 
                               from_entity_type: str,
                               to_entity_id: str, 
                               to_entity_type: str,
                               relationship_type: str, 
                               properties: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Adds a relationship between two entities in the Knowledge Graph.
        Assumes 'id' is a unique property for entities.
        """
        driver = await self._get_driver()
        async with driver.session() as session:
            query = (
                f"MATCH (a:{from_entity_type} {{id: $from_entity_id}}), "
                f"(b:{to_entity_type} {{id: $to_entity_id}}) "
                f"MERGE (a)-[r:{relationship_type}]->(b) "
                "SET r += $properties "
                "RETURN properties(r) AS properties"
            )
            params = {
                "from_entity_id": from_entity_id,
                "to_entity_id": to_entity_id,
                "properties": properties or {}
            }
            result = await session.run(query, params)
            record = await result.single()
            return record["properties"] if record else {}

def get_knowledge_graph_service() -> KnowledgeGraphService:
    """
    Dependency function to provide a KnowledgeGraphService instance.
    """
    return KnowledgeGraphService()