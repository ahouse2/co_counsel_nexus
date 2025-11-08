from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# --- Base Models for Nodes and Relationships ---

class BaseNode(BaseModel):
    label: str = Field(..., description="The primary label of the node (e.g., 'Document', 'Person').")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Key-value pairs of node properties.")
    identity: Optional[str] = Field(None, description="Unique identifier for the node within its label, if applicable.")

class BaseRelationship(BaseModel):
    type: str = Field(..., description="The type of the relationship (e.g., 'MENTIONS', 'AUTHORED_BY').")
    source_node_label: str = Field(..., description="Label of the source node.")
    source_node_identity: str = Field(..., description="Identity of the source node.")
    target_node_label: str = Field(..., description="Label of the target node.")
    target_node_identity: str = Field(..., description="Identity of the target node.")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Key-value pairs of relationship properties.")

# --- System Knowledge Graph Models ---

class SystemNode(BaseNode):
    # Example System Node Labels: 'Concept', 'LegalPrinciple', 'Statute', 'CaseLaw', 'Jurisdiction'
    pass

class SystemRelationship(BaseRelationship):
    # Example System Relationship Types: 'DEFINES', 'RELATES_TO', 'CITED_BY', 'GOVERNS'
    pass

# --- User Knowledge Graph Models ---

class UserNode(BaseNode):
    # Example User Node Labels: 'Case', 'Document', 'Party', 'Evidence', 'Argument'
    pass

class UserRelationship(BaseRelationship):
    # Example User Relationship Types: 'CONTAINS', 'REFERENCES', 'INVOLVES', 'SUPPORTS'
    pass

# --- Combined Data Model for API/Service Layer ---

class KnowledgeGraphData(BaseModel):
    nodes: List[BaseNode] = Field(default_factory=list)
    relationships: List[BaseRelationship] = Field(default_factory=list)

# --- Specific Node and Relationship Examples (can be expanded) ---

# System Graph Examples
class ConceptNode(SystemNode):
    label: str = "Concept"
    name: str
    definition: Optional[str] = None

class LegalPrincipleNode(SystemNode):
    label: str = "LegalPrinciple"
    name: str
    description: Optional[str] = None

# User Graph Examples
class CaseNode(UserNode):
    label: str = "Case"
    case_id: str
    title: str
    jurisdiction: Optional[str] = None

class DocumentNode(UserNode):
    label: str = "Document"
    document_id: str
    title: str
    document_type: str

class MentionsRelationship(UserRelationship):
    type: str = "MENTIONS"
    context: Optional[str] = None # e.g., "paragraph 3"

class ReferencesRelationship(UserRelationship):
    type: str = "REFERENCES"
    page_number: Optional[int] = None
    citation: Optional[str] = None
