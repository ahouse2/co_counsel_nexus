from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import json
import os
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

    async def get_case_context(self, case_id: str) -> Dict[str, Any]:
        """
        Retrieves comprehensive context for a given case from the knowledge graph.
        """
        driver = await self._get_driver()
        async with driver.session() as session:
            context = {"case_id": case_id}

            # Get case summary
            summary_query = """
                MATCH (c:Case {id: $case_id})
                RETURN c.summary AS summary
            """
            summary_result = await session.run(summary_query, case_id=case_id)
            summary_record = await summary_result.single()
            context["summary"] = summary_record["summary"] if summary_record else "No summary found."

            # Get related documents
            documents_query = """
                MATCH (c:Case {id: $case_id})-[:RELATES_TO]->(d:Document)
                RETURN d.id AS document_id, d.title AS document_title, d.type AS document_type
            """
            documents_result = await session.run(documents_query, case_id=case_id)
            context["documents"] = [record.data() for record in await documents_result.data()]

            # Get involved parties
            parties_query = """
                MATCH (c:Case {id: $case_id})-[:INVOLVES]->(p:Party)
                RETURN p.id AS party_id, p.name AS party_name, p.role AS party_role
            """
            parties_result = await session.run(parties_query, case_id=case_id)
            context["parties"] = [record.data() for record in await parties_result.data()]

            # Get key legal theories
            theories_query = """
                MATCH (c:Case {id: $case_id})-[:BASED_ON]->(t:LegalTheory)
                RETURN t.id AS theory_id, t.name AS theory_name, t.description AS theory_description
            """
            theories_result = await session.run(theories_query, case_id=case_id)
            context["legal_theories"] = [record.data() for record in await theories_result.data()]

            # Get relevant precedents
            precedents_query = """
                MATCH (c:Case {id: $case_id})-[:CITES]->(p:Precedent)
                RETURN p.id AS precedent_id, p.title AS precedent_title, p.citation AS precedent_citation
            """
            precedents_result = await session.run(precedents_query, case_id=case_id)
            context["precedents"] = [record.data() for record in await precedents_result.data()]

            return context

    async def run_cypher_query(self, query: str, params: Optional[Dict[str, Any]] = None, cache: bool = True) -> List[Dict[str, Any]]:
        """
        Executes a raw Cypher query.
        """
        driver = await self._get_driver()
        async with driver.session() as session:
            result = await session.run(query, params)
            return [record.data() for record in await result.data()]

    async def query_graph(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Alias for run_cypher_query.
        """
        return await self.run_cypher_query(query, params)

    async def search_legal_references(self, query: str) -> List[Dict[str, Any]]:
        """
        Searches for legal references (LegalTheory, Precedent) matching the query.
        """
        driver = await self._get_driver()
        async with driver.session() as session:
            cypher = """
                MATCH (n)
                WHERE (n:LegalTheory OR n:Precedent) AND 
                      (toLower(n.name) CONTAINS toLower($query) OR 
                       toLower(n.description) CONTAINS toLower($query) OR
                       toLower(n.title) CONTAINS toLower($query) OR
                       toLower(n.citation) CONTAINS toLower($query))
                RETURN n.id AS id, labels(n) AS type, properties(n) AS properties
            """
            result = await session.run(cypher, query=query)
            return [record.data() for record in await result.data()]

    async def get_node(self, node_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves a node by its internal ID (or property ID if that's what's intended).
        Assuming 'id' property for now as per other methods.
        """
        driver = await self._get_driver()
        async with driver.session() as session:
            # Try matching by property 'id' first (string/int), then internal id() if needed.
            # Based on other methods, 'id' is a property.
            cypher = "MATCH (n {id: $node_id}) RETURN properties(n) as properties, labels(n) as labels"
            result = await session.run(cypher, node_id=node_id)
            record = await result.single()
            if record:
                data = dict(record["properties"])
                data["labels"] = record["labels"]
                return data
            return None

    async def get_relationships(self, node_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves all relationships for a given node ID.
        """
        driver = await self._get_driver()
        async with driver.session() as session:
            cypher = """
                MATCH (n {id: $node_id})-[r]-(m)
                RETURN type(r) as type, properties(r) as properties, 
                       startNode(r).id as start_node, endNode(r).id as end_node,
                       labels(m) as other_node_labels, m.id as other_node_id
            """
            result = await session.run(cypher, node_id=node_id)
            return [record.data() for record in await result.data()]

    async def export_graph(self, output_path: str) -> str:
        """
        Exports the entire graph to a JSON file.
        """
        driver = await self._get_driver()
        async with driver.session() as session:
            cypher_nodes = "MATCH (n) RETURN n"
            cypher_rels = "MATCH ()-[r]->() RETURN r"
            
            nodes_result = await session.run(cypher_nodes)
            rels_result = await session.run(cypher_rels)
            
            nodes = [record["n"].data() for record in await nodes_result.data()]
            # Relationships in neo4j driver result might need processing
            rels_data = await rels_result.data()
            rels = []
            for r in rels_data:
                rel = r['r']
                # rel is a Relationship object
                rels.append({
                    "id": rel.id,
                    "type": rel.type,
                    "start_node": rel.start_node.id, # Internal ID, might need property id mapping if consistent
                    "end_node": rel.end_node.id,
                    "properties": dict(rel)
                })
            
            export_data = {"nodes": nodes, "relationships": rels}
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2)
                
            return os.path.abspath(output_path)

    async def get_cause_subgraph(self, cause: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Retrieves the subgraph related to a specific cause of action.
        """
        driver = await self._get_driver()
        async with driver.session() as session:
            # Assuming 'CauseOfAction' label or property. Adjusting to search for a node with that name/type.
            cypher = """
                MATCH (c:CauseOfAction {name: $cause})
                CALL apoc.path.subgraphAll(c, {maxLevel: 2})
                YIELD nodes, relationships
                RETURN nodes, relationships
            """
            # Fallback if APOC is not available: simple 1-hop or 2-hop expansion
            # Using standard Cypher for broader compatibility if APOC isn't guaranteed
            cypher_fallback = """
                MATCH (c:CauseOfAction {name: $cause})-[r*1..2]-(m)
                RETURN c, r, m
            """
            
            # Let's try a standard expansion that returns paths and we parse them
            cypher_standard = """
                MATCH p=(c:CauseOfAction {name: $cause})-[*1..2]-(m)
                RETURN nodes(p) as nodes, relationships(p) as rels
            """
            
            result = await session.run(cypher_standard, cause=cause)
            
            nodes_map = {}
            rels_map = {}
            
            for record in await result.data():
                for node in record['nodes']:
                    # node is a Node object
                    # We need to handle if it uses internal IDs or property IDs. 
                    # The schema seems to use 'id' property.
                    n_props = dict(node)
                    n_id = n_props.get('id', node.id) # Fallback to internal ID if 'id' prop missing
                    nodes_map[n_id] = {"id": n_id, "labels": list(node.labels), "properties": n_props}
                    
                for rel in record['rels']:
                    r_props = dict(rel)
                    r_id = rel.id
                    rels_map[r_id] = {
                        "id": r_id, 
                        "type": rel.type, 
                        "start": rel.start_node.get('id', rel.start_node.id),
                        "end": rel.end_node.get('id', rel.end_node.id),
                        "properties": r_props
                    }
                    
            return list(nodes_map.values()), list(rels_map.values())

    async def cause_support_scores(self) -> List[Dict[str, Any]]:
        """
        Calculates support scores for causes of action based on evidence/facts.
        """
        driver = await self._get_driver()
        async with driver.session() as session:
            # Hypothetical scoring: count of supporting Evidence nodes linked to CauseOfAction
            cypher = """
                MATCH (c:CauseOfAction)
                OPTIONAL MATCH (c)<-[:SUPPORTS]-(e:Evidence)
                RETURN c.name as cause, count(e) as support_score, collect(e.id) as evidence_ids
            """
            result = await session.run(cypher)
            return [record.data() for record in await result.data()]

    async def get_subgraph(self, label: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Retrieves all nodes with a given label and their relationships.
        """
        driver = await self._get_driver()
        async with driver.session() as session:
            cypher = f"""
                MATCH (n:{label})-[r]-(m)
                RETURN n, r, m
            """
            # Note: This could be large. Limiting might be wise, but following spec.
            result = await session.run(cypher)
            
            nodes_map = {}
            rels_map = {}
            
            for record in await result.data():
                n = record['n']
                m = record['m']
                r = record['r']
                
                for node in [n, m]:
                    n_props = dict(node)
                    n_id = n_props.get('id', node.id)
                    nodes_map[n_id] = {"id": n_id, "labels": list(node.labels), "properties": n_props}
                
                r_props = dict(r)
                r_id = r.id
                rels_map[r_id] = {
                    "id": r_id,
                    "type": r.type,
                    "start": r.start_node.get('id', r.start_node.id),
                    "end": r.end_node.get('id', r.end_node.id),
                    "properties": r_props
                }
                
            return list(nodes_map.values()), list(rels_map.values())

    def build_graph_index(self, documents: List[Any], case_id: str):
        """
        Builds a Knowledge Graph index from documents using LlamaIndex.
        This is a synchronous method as LlamaIndex construction is typically sync.
        """
        try:
            from llama_index.graph_stores.neo4j import Neo4jGraphStore
            from llama_index.core import StorageContext, KnowledgeGraphIndex
            from backend.ingestion.llama_index_factory import create_llm_service, create_embedding_model
            from backend.app.config import get_settings
            
            settings = get_settings()
            
            # Initialize LlamaIndex components
            # We need to recreate the LLM and Embedding models here or pass them in.
            # Using factory for consistency.
            llm_service = create_llm_service(settings.llm)
            # We need the underlying LlamaIndex LLM object
            # Re-using the logic from classification_service/llama_index_factory
            # Ideally this should be a shared utility.
            from backend.app.services.classification_service import ClassificationService
            # Hack: instantiate ClassificationService just to get the LLM if we don't want to duplicate code
            # Or just duplicate the small snippet for now.
            # Let's duplicate for safety and independence.
            
            llm = None
            from backend.app.models.settings import LlmProvider
            config = settings.llm
            if config.provider == LlmProvider.OPENAI:
                from llama_index.llms.openai import OpenAI
                llm = OpenAI(model=config.model, api_key=config.api_key, api_base=config.api_base)
            elif config.provider == LlmProvider.GEMINI:
                from llama_index.llms.gemini import Gemini
                llm = Gemini(model=config.model, api_key=config.api_key)
            # ... add others as needed
            
            if not llm:
                print("Warning: No valid LLM found for Graph Indexing.")
                return

            embed_model = create_embedding_model(settings.embedding)

            graph_store = Neo4jGraphStore(
                username=self.user,
                password=self.password,
                url=self.uri,
                database="neo4j", # Default
            )
            
            storage_context = StorageContext.from_defaults(graph_store=graph_store)
            
            # Filter documents for this case if needed, or assume passed documents are relevant.
            # The `documents` arg should be a list of LlamaIndex Document objects.
            
            # Create the index
            # This extracts triplets and stores them in Neo4j
            index = KnowledgeGraphIndex.from_documents(
                documents,
                storage_context=storage_context,
                max_triplets_per_chunk=2,
                llm=llm,
                embed_model=embed_model,
                include_embeddings=True, # Useful for GraphRAG
            )
            
            print(f"Successfully built Knowledge Graph index for {len(documents)} documents.")
            return index
            
        except Exception as e:
            print(f"Failed to build graph index: {e}")
            raise e


def get_knowledge_graph_service() -> KnowledgeGraphService:
    """
    Dependency function to provide a KnowledgeGraphService instance.
    """
    return KnowledgeGraphService()