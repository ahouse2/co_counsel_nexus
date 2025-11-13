import asyncio
import os
import time
import logging
import uuid # Import uuid for generating VIDs

from nebula3.gclient.net import ConnectionPool
from nebula3.common.ttypes import DataSet, Value
from nebula3.logger import logger as nebula_logger # Import NebulaGraph's logger
from neuro_san.interfaces.coded_tool import CodedTool
from pyvis.network import Network # Note: pyvis might need adaptation or replacement for NebulaGraph visualization, for now keeping as is.

# Configure NebulaGraph logger
nebula_logger.setLevel(logging.WARNING) # Adjust level as needed

class KnowledgeGraphManager(CodedTool):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        host = os.environ.get("NEBULA_GRAPH_HOST", "nebula-graphd")
        port = int(os.environ.get("NEBULA_GRAPH_PORT", "9669"))
        user = os.environ.get("NEBULA_GRAPH_USER", "root")
        pwd = os.environ.get("NEBULA_GRAPH_PASSWORD", "nebula")

        # Make connection timeouts and retries generous for local runs
        try:
            conn_timeout = int(os.environ.get("NEBULA_GRAPH_CONN_TIMEOUT", "30"))
        except Exception:
            conn_timeout = 30
        try:
            verify_attempts = int(os.environ.get("NEBULA_GRAPH_CONNECT_ATTEMPTS", "8"))
        except Exception:
            verify_attempts = 8
        try:
            verify_base_sleep = float(os.environ.get("NEBULA_GRAPH_CONNECT_BACKOFF", "1.0"))
        except Exception:
            verify_base_sleep = 1.0

        self.space_name = os.environ.get("NEBULA_GRAPH_SPACE", "cog_v2") # Default to 'cog_v2' space

        self.pool = ConnectionPool(user, pwd, max_connection_pool_size=50, idle_time=120)
        # Attempt to connect to NebulaGraph with retry logic
        logging.info(f"Attempting to connect to NebulaGraph at {host}:{port}...")
        self._nebula_verify_with_backoff(host, port, attempts=verify_attempts, base_sleep=verify_base_sleep)
        
        self._cache: dict[tuple, list[dict]] = {}

    def _nebula_verify_with_backoff(self, host: str, port: int, attempts: int = 5, base_sleep: float = 0.5) -> None:
        for i in range(attempts):
            try:
                # Test connection by ensuring we can connect and then disconnect
                if self.pool.ping([ (host, port) ]):
                    self.pool.init([(host, port)])
                    logging.info("NebulaGraph connection pool initialized.")
                    # After initialization, we can try to connect to a specific space
                    with self.pool.get_session() as session:
                        session.execute(f"USE {self.space_name}") # Try to use the space
                        logging.info(f"Successfully connected to NebulaGraph and used space '{self.space_name}'.")
                    return
                else:
                    raise RuntimeError("NebulaGraph ping failed.")
            except Exception as exc:
                if i == attempts - 1:
                    raise RuntimeError(f"NebulaGraph connectivity failed after {attempts} attempts: {exc}") from exc
                logging.warning(f"NebulaGraph connection attempt {i+1}/{attempts} failed: {exc}. Retrying in {base_sleep * (2**i)} seconds.")
                time.sleep(base_sleep * (2**i))

    def _invalidate_cache(self) -> None:
        self._cache.clear()

    def close(self):
        if self.pool:
            self.pool.close()

    def _format_nebula_value(self, value: Value) -> Any:
        # Helper function to convert NebulaGraph Value to Python native types
        if value.getType() == Value.Type.boolVal:
            return value.get_bool_val()
        elif value.getType() == Value.Type.intVal:
            return value.get_int_val()
        elif value.getType() == Value.Type.doubleVal:
            return value.get_double_val()
        elif value.getType() == Value.Type.stringVal:
            return value.get_string_val().decode('utf-8')
        elif value.getType() == Value.Type.listVal:
            return [self._format_nebula_value(v) for v in value.get_list_val().values]
        elif value.getType() == Value.Type.setVal:
            return {self._format_nebula_value(v) for v in value.get_set_val().values}
        elif value.getType() == Value.Type.mapVal:
            return {k.decode('utf-8'): self._format_nebula_value(v) for k, v in value.get_map_val().kvs.items()}
        elif value.getType() == Value.Type.vertex: # Handle Vertex as a map of properties
            vertex_data = value.get_vVal()
            properties = {}
            for tag in vertex_data.tags:
                for k, v in tag.props.items():
                    properties[k.decode('utf-8')] = self._format_nebula_value(v)
            return {"id": vertex_data.vid.get_str().decode('utf-8') if vertex_data.vid.is_set_str() else vertex_data.vid.get_iVal(), "tags": [t.name.decode('utf-8') for t in vertex_data.tags], "properties": properties}
        
        elif value.getType() == Value.Type.edge: # Handle Edge
            edge_data = value.get_eVal()
            return {"src": edge_data.src.get_str().decode('utf-8') if edge_data.src.is_set_str() else edge_data.src.get_iVal(), "dst": edge_data.dst.get_str().decode('utf-8') if edge_data.dst.is_set_str() else edge_data.dst.get_iVal(), "type": edge_data.name.decode('utf-8'), "ranking": edge_data.ranking, "properties": {k.decode('utf-8'): self._format_nebula_value(v) for k,v in edge_data.props.items()}}
        
        return None # or raise an error for unsupported types


    def run_query(self, query: str, params: dict | None = None, cache: bool = True) -> list[dict]:
        """Run an nGQL query and return all records as dictionaries."""
        if not self.pool or not self.pool.is_inited():
            raise RuntimeError("NebulaGraph connection pool not initialized.")
        
        key = (query, tuple(sorted(params.items())) if params else None)
        if cache and key in self._cache:
            return self._cache[key]
        
        try:
            with self.pool.get_session() as session:
                if self.space_name:
                    session.execute(f"USE {self.space_name}")
                # Important: nGQL does not support parameterized queries in the same way Cypher does.
                # Parameters must often be interpolated directly into the query string for simple cases.
                # For complex types or to prevent injection, careful escaping or query construction is needed.
                # For this implementation, we assume basic interpolation or direct query strings.
                final_query = query
                if params:
                    for k, v in params.items():
                        if isinstance(v, str):
                            final_query = final_query.replace(f"${k}", f"'{v}'")
                        else:
                            final_query = final_query.replace(f"${k}", str(v))

                resp = session.execute(final_query)

                if not resp.is_succeeded():
                    raise RuntimeError(f"NebulaGraph query failed: {resp.error_msg()}")

                data = []
                if resp.row_size() > 0:
                    for row in resp.rows():
                        record = {}
                        for i, column_name_bytes in enumerate(resp.column_names()):
                            column_name = column_name_bytes.decode('utf-8')
                            record[column_name] = self._format_nebula_value(row.values[i])
                        data.append(record)
        except Exception as exc:
            raise RuntimeError(f"NebulaGraph query failed: {exc}") from exc
        
        if cache:
            self._cache[key] = data
        else:
            self._invalidate_cache()
        return data

    async def arun_query(
        self, query: str, params: dict | None = None, cache: bool = True
    ) -> list[dict]:
        return await asyncio.to_thread(self.run_query, query, params, cache)



    def create_node(self, label: str, properties: dict) -> str:
        """
        Creates a new node (vertex) in the knowledge graph.
        NebulaGraph requires a Vertex ID (VID). We'll generate a UUID for this.
        Also, ensure the tag for the label exists.

        :param label: The label (tag) for the new node.
        :param properties: A dictionary of properties for the new node.
        :return: The VID of the newly created node.
        """
        vid = str(uuid.uuid4()) # Generate a unique VID

        # Ensure the tag exists (conceptual, in real Nebula you'd define schema first)
        # For simplicity, we'll assume tags are created dynamically or pre-exist.
        # In a real scenario, you'd run:
        # CREATE TAG IF NOT EXISTS `label` (prop1 string, prop2 int, ...)
        
        prop_keys = []
        prop_str_values = []
        for k, v in properties.items():
            prop_keys.append(f"`{k}`")
            prop_str_values.append(f"'{v}'" if isinstance(v, str) else str(v))

        query = f"INSERT VERTEX `{label}` ({', '.join(prop_keys)}) VALUES '{vid}':({', '.join(prop_str_values)})"
        self.run_query(query, cache=False)
        return vid

    def create_relationship(
        self, start_node_id: str, end_node_id: str, relationship_type: str, properties: dict = None
    ) -> None:
        """
        Creates a new relationship (edge) between two nodes in the knowledge graph.
        Ensure the edge type exists.

        :param start_node_id: The VID of the start node.
        :param end_node_id: The VID of the end node.
        :param relationship_type: The type of the new relationship (edge type).
        :param properties: A dictionary of properties for the new relationship.
        """
        # Ensure the edge type exists (conceptual, in real Nebula you'd define schema first)
        # For simplicity, we'll assume edge types are created dynamically or pre-exist.
        # In a real scenario, you'd run:
        # CREATE EDGE IF NOT EXISTS `relationship_type` (prop1 string, prop2 int, ...)

        properties = properties or {}
        prop_keys = []
        prop_str_values = []
        for k, v in properties.items():
            prop_keys.append(f"`{k}`")
            prop_str_values.append(f"'{v}'" if isinstance(v, str) else str(v))

        if prop_keys and prop_str_values:
            query = f"INSERT EDGE `{relationship_type}` ({', '.join(prop_keys)}) VALUES '{start_node_id}'->'{end_node_id}':({', '.join(prop_str_values)})"
        else:
            query = f"INSERT EDGE `{relationship_type}` VALUES '{start_node_id}'->'{end_node_id}':()"
        
        self.run_query(query, cache=False)

    def add_fact(self, case_node_id: str, document_node_id: str, fact: dict) -> str:
        """Create a Fact node and link it to case and document nodes."""
        fact_props = {
            "text": fact.get("text", ""),
            "parties": fact.get("parties", []),
            "dates": fact.get("dates", []),
            "actions": fact.get("actions", []),
        }
        fact_id = self.create_node("Fact", fact_props)
        if case_node_id is not None:
            self.create_relationship(case_node_id, fact_id, "HAS_FACT")
        if document_node_id is not None:
            self.create_relationship(document_node_id, fact_id, "HAS_FACT")
        return fact_id

    def _get_or_create_by_name(self, label: str, name: str) -> str:
        """Return the VID of a node with the given name, creating it if needed."""
        # nGQL to lookup vertex by property
        query = f"LOOKUP ON `{label}` WHERE `{label}`.name == '{name}' YIELD VERTEX AS v | RETURN id(v) AS id"
        result = self.run_query(query)
        if result and result[0].get("id") is not None:
            # NebulaGraph returns VID as a string or int, ensure consistency
            return str(result[0]["id"])
        
        # If not found, create it
        return self.create_node(label, {"name": name})

    def add_legal_reference(
        self,
        category: str,
        title: str,
        text: str,
        url: str,
        retrieved_at: str,
        theories: list[str] | None = None,
    ) -> str:
        """Create a ``LegalReference`` node and link to theories and timeline."""

        ref_props = {
            "category": category,
            "title": title,
            "text": text,
            "url": url,
            "retrieved_at": retrieved_at,
        }
        ref_id = self.create_node("LegalReference", ref_props)
        # Link to timeline
        timeline_id = self.create_node(
            "TimelineEvent", {"date": retrieved_at, "description": title}
        )
        self.create_relationship(ref_id, timeline_id, "OCCURRED_ON")
        # Link to legal theories
        for theory in theories or []:
            theory_id = self._get_or_create_by_name("LegalTheory", theory)
            self.create_relationship(ref_id, theory_id, "RELATES_TO")
        return ref_id

    def search_legal_references(self, query: str) -> list[dict]:
        """Simple full-text search over legal references."""
        # NebulaGraph does not have a direct equivalent to Cypher's `toLower() CONTAINS toLower()` for full-text search.
        # This would typically require a full-text index or a more complex UDF.
        # For now, we'll do a basic property match.
        # TODO: Implement full-text search for NebulaGraph if needed, possibly using a dedicated search index.
        
        # nGQL equivalent for basic property search
        # This assumes 'text' and 'title' are properties of the 'LegalReference' tag.
        # You might need to create a full-text index in NebulaGraph for efficient search.
        # Example: CREATE FULLTEXT INDEX legal_ref_index ON LegalReference(text, title);
        # Then use: LOOKUP ON LegalReference WHERE fulltext("legal_ref_index", "your query") YIELD VERTEX AS v | RETURN properties(v)
        
        # For now, a simple MATCH on properties
        # Note: NebulaGraph's MATCH is more restrictive than Cypher's.
        # This query will fetch all LegalReference nodes and filter in Python, which is inefficient.
        # A better nGQL query would be:
        # MATCH (r:LegalReference) WHERE r.text CONTAINS 'query' OR r.title CONTAINS 'query' RETURN r
        # However, `CONTAINS` is not directly supported for string properties in MATCH.
        # A more robust solution involves full-text indexes.
        
        # For demonstration, we'll fetch all and filter (inefficient but works for small graphs)
        # Or, if we assume a full-text index 'legal_ref_index' exists:
        # query = f"LOOKUP ON LegalReference WHERE fulltext('legal_ref_index', '{query}') YIELD VERTEX AS v | RETURN properties(v) AS r_props"
        
        # For now, a simple return of all LegalReference nodes, and filter in Python
        # This is a temporary workaround until a proper full-text search is implemented in NebulaGraph.
        # A more direct nGQL approach for filtering would be:
        # MATCH (r:LegalReference) WHERE r.text =~ '.*{query}.*' OR r.title =~ '.*{query}.*' RETURN r
        # But regex matching can be slow.
        
        # Let's try a basic MATCH with regex for now, assuming properties are indexed for speed.
        # Note: NebulaGraph's regex is `~=`.
        nqgl_query = (
            f"MATCH (r:LegalReference) "
            f"WHERE r.text =~ '.*{query}.*' OR r.title =~ '.*{query}.*' "
            f"RETURN properties(r) AS r_props"
        )
        
        results = self.run_query(nqgl_query, {"q": query})
        
        # The result will be a list of dictionaries, where each dict has a 'r_props' key
        # containing the properties of the LegalReference node.
        formatted_results = []
        for record in results:
            props = record.get("r_props", {})
            formatted_results.append({
                "category": props.get("category"),
                "title": props.get("title"),
                "text": props.get("text"),
                "url": props.get("url"),
                "retrieved_at": props.get("retrieved_at"),
            })
        return formatted_results

    def link_fact_to_element(
        self,
        fact_id: str,
        cause: str,
        element: str,
        weight: float | None = None,
        relation: str = "SUPPORTS",
    ) -> None:
        """Link an existing fact to an element and cause of action.

        Parameters
        ----------
        fact_id:
            VID of the ``Fact`` node.
        cause:
            Name of the cause of action.
        element:
            Name of the element to link.
        weight:
            Optional confidence weight stored on the relationship.
        relation:
            Relationship type, either ``SUPPORTS`` or ``CONTRADICTS``.

        The method ensures the ``Element`` is connected to the
        ``CauseOfAction`` via ``BELONGS_TO`` and then creates the specified
        relationship from the fact to the element with the provided weight.
        """

        relation = relation.upper()
        if relation not in {"SUPPORTS", "CONTRADICTS"}:
            raise ValueError("relation must be SUPPORTS or CONTRADICTS")

        cause_id = self._get_or_create_by_name("CauseOfAction", cause)
        element_id = self._get_or_create_by_name("Element", element)
        self.create_relationship(element_id, cause_id, "BELONGS_TO")
        props = {"weight": weight} if weight is not None else None
        self.create_relationship(fact_id, element_id, relation, props)

    def relate_facts(
        self,
        source_fact_id: str,
        target_fact_id: str,
        relation: str = "SUPPORTS",
        weight: float | None = None,
    ) -> None:
        """Create a relationship between two existing ``Fact`` nodes."""

        relation = relation.upper()
        if relation not in {"SUPPORTS", "CONTRADICTS"}:
            raise ValueError("relation must be SUPPORTS or CONTRADICTS")
        props = {"weight": weight} if weight is not None else None
        self.create_relationship(source_fact_id, target_fact_id, relation, props)

    def link_document_dispute(self, fact_id: str, document_node_id: str) -> None:
        """Link a fact to a document that disputes it."""
        self.create_relationship(fact_id, document_node_id, "DISPUTED_BY")

    def link_fact_origin(selfself, fact_id: str, origin_label: str, origin_name: str) -> None:
        """Link a fact to its origin source such as Deposition or Email."""
        origin_id = self._get_or_create_by_name(origin_label, origin_name)
        self.create_relationship(fact_id, origin_id, "ORIGINATED_IN")

    def relate_fact_to_element(self, fact_node_id: str, element_node_id: str) -> None:
        """Create a SUPPORTS relationship between an existing Fact and Element."""
        # nGQL equivalent for MERGE is UPSERT EDGE or INSERT EDGE if not exists.
        # For simplicity, we'll use INSERT EDGE, assuming it's idempotent or handled by schema.
        # A more robust solution would check for existence first.
        query = f"INSERT EDGE `SUPPORTS` VALUES '{fact_node_id}'->'{element_node_id}':()"
        self.run_query(query, cache=False)

    def get_node(self, node_id: str) -> dict:
        """
        Retrieves a node from the knowledge graph.

        :param node_id: The VID of the node to retrieve.
        :return: A dictionary representing the node.
        """
        # nGQL to fetch properties of a vertex by VID
        query = f"FETCH PROP ON * '{node_id}' YIELD VERTEX AS n | RETURN properties(n) AS n_props, tags(n) AS n_tags"
        result = self.run_query(query)
        if result and result[0].get("n_props"):
            node_props = result[0]["n_props"]
            node_tags = result[0]["n_tags"]
            return {"id": node_id, "labels": node_tags, "properties": node_props}
        return None

    def get_relationships(self, node_id: str) -> list:
        """
        Retrieves all relationships for a given node.

        :param node_id: The VID of the node.
        :return: A list of dictionaries representing the relationships.
        """
        # nGQL to get all outgoing edges from a vertex
        query = f"GO FROM '{node_id}' OVER * YIELD edge AS r | RETURN properties(r) AS r_props, type(r) AS r_type, src(r) AS r_src, dst(r) AS r_dst"
        result = self.run_query(query)
        
        formatted_relationships = []
        for record in result:
            props = record.get("r_props", {})
            formatted_relationships.append({
                "source": str(record.get("r_src")),
                "target": str(record.get("r_dst")),
                "type": record.get("r_type"),
                "properties": props,
            })
        return formatted_relationships

    def export_graph(self, output_path: str = "graph.html") -> str:
        """
        Exports the entire graph as an interactive HTML file.
        This method is highly dependent on the graph visualization library (pyvis).
        It will need significant adaptation or replacement for NebulaGraph.

        :param output_path: The path to save the HTML file to.
        :return: The path to the generated HTML file.
        """
        # TODO: This method needs a complete rewrite for NebulaGraph visualization.
        # pyvis is designed for Neo4j's output format and might not be directly compatible.
        # Consider using a NebulaGraph-specific visualization tool or adapting the data
        # to a generic graph visualization library.

        # For now, we will fetch all nodes and edges and return them in a format
        # that could be used by a visualization library.
        # This will not generate an HTML file directly.

        nqgl_nodes_query = "MATCH (n) RETURN id(n) AS id, tags(n) AS labels, properties(n) AS properties"
        nodes_result = self.run_query(nqgl_nodes_query)

        nqgl_edges_query = "MATCH (s)-[e]->(d) RETURN id(s) AS source, id(d) AS target, type(e) AS type, properties(e) AS properties"
        relationships_result = self.run_query(nqgl_edges_query)
        
        # For now, return the raw nodes and edges data
        return {"nodes": nodes_result, "edges": relationships_result}

    def get_cause_subgraph(self, cause: str):
        """Retrieve nodes and edges connected to a cause of action."""
        # This is a complex query with OPTIONAL MATCH and UNION.
        # Translating this directly to nGQL MATCH can be challenging due to differences in semantics.
        # A common approach in nGQL for complex traversals is to use GO statements.
        # For now, we'll provide a simplified nGQL equivalent and add a TODO for refinement.

        # Use GO statements for more efficient traversal in NebulaGraph
        # Get all nodes connected to the cause
        nqgl_nodes_query = (
            f"GO FROM (LOOKUP ON CauseOfAction WHERE CauseOfAction.name == '{cause}' YIELD VERTEX AS v | RETURN id(v)) "
            f"OVER * BIDIRECT YIELD VERTEX AS n | RETURN id(n) AS id, tags(n) AS labels, properties(n) AS properties"
        )
        nodes = [
            {
                "id": record["id"],
                "labels": record["labels"],
                "properties": record["properties"],
            }
            for record in self.run_query(nqgl_nodes_query)
        ]

        # Get all edges connected to the cause
        nqgl_edges_query = (
            f"GO FROM (LOOKUP ON CauseOfAction WHERE CauseOfAction.name == '{cause}' YIELD VERTEX AS v | RETURN id(v)) "
            f"OVER * BIDIRECT YIELD EDGE AS e | RETURN src(e) AS source, dst(e) AS target, type(e) AS type, properties(e) AS properties"
        )
        edges = [
            {
                "source": record["source"],
                "target": record["target"],
                "type": record["type"],
                "properties": record.get("properties", {}),
            }
            for record in self.run_query(nqgl_edges_query)
        ]

        return nodes, edges

    def cause_support_scores(self) -> list[dict]:
        """Return satisfaction counts and confidence for each cause of action."""
        # TODO: Translate this aggregation query to nGQL.
        # For now, a simplified query to count supporting facts for each cause of action.
        nqgl_query = (
            f"MATCH (c:CauseOfAction)<-[:BELONGS_TO]-(e:Element)<-[s:SUPPORTS]-(f:Fact) "
            f"RETURN c.name AS cause, count(s) AS supporting_facts"
        )
        result = self.run_query(nqgl_query)
        return result

    def get_subgraph(self, label: str):
        """Retrieve a subgraph for nodes with a given label."""
        nqgl_nodes_query = (
            f"MATCH (n:`{label}`) "
            f"RETURN id(n) AS id, tags(n) AS labels, properties(n) AS properties"
        )
        nodes = [
            {
                "id": record["id"],
                "labels": record["labels"],
                "properties": record["properties"],
            }
            for record in self.run_query(nqgl_nodes_query)
        ]

        nqgl_edges_query = (
            f"MATCH (n:`{label}`)-[e]->(m) "
            f"RETURN id(n) AS source, id(m) AS target, type(e) AS type, properties(e) AS properties"
        )
        edges = [
            {
                "source": record["source"],
                "target": record["target"],
                "type": record["type"],
                "properties": record.get("properties", {}),
            }
            for record in self.run_query(nqgl_edges_query)
        ]

        return nodes, edges

    def delete_node(self, node_id: str) -> None:
        """Delete a node and any attached relationships."""
        # nGQL to delete a vertex and its associated edges
        query = f"DELETE VERTEX '{node_id}'"
        self.run_query(query, cache=False)

    def delete_relationship(self, start_node_id: str, end_node_id: str, relationship_type: str) -> None:
        """Delete a specific relationship between two nodes."""
        # nGQL to delete an edge
        query = f"DELETE EDGE `{relationship_type}` FROM '{start_node_id}' TO '{end_node_id}'"
        self.run_query(query, cache=False)
