// Neo4j schema bootstrap for Co-Counsel knowledge graph

CREATE CONSTRAINT document_id_unique IF NOT EXISTS
FOR (d:Document)
REQUIRE d.document_id IS UNIQUE;

CREATE INDEX document_source_type IF NOT EXISTS
FOR (d:Document)
ON (d.source_type);

CREATE INDEX document_ingested_at IF NOT EXISTS
FOR (d:Document)
ON (d.ingested_at);

CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
FOR (c:Chunk)
REQUIRE c.chunk_id IS UNIQUE;

CREATE INDEX chunk_document_ordinal IF NOT EXISTS
FOR (c:Chunk)
ON (c.document_id, c.ordinal);

CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (e:Entity)
REQUIRE e.entity_id IS UNIQUE;

CREATE INDEX entity_canonical_type IF NOT EXISTS
FOR (e:Entity)
ON (e.canonical_name, e.type);

CREATE CONSTRAINT relation_identity_unique IF NOT EXISTS
FOR ()-[r:RELATION]-()
REQUIRE r.relation_id IS UNIQUE;

CREATE CONSTRAINT artifact_id_unique IF NOT EXISTS
FOR (f:ForensicsArtifact)
REQUIRE f.artifact_id IS UNIQUE;

CREATE INDEX artifact_document_type IF NOT EXISTS
FOR (f:ForensicsArtifact)
ON (f.document_id, f.artifact_type);

// Relationship existence constraints ensure referential integrity metadata is present
CREATE CONSTRAINT has_chunk_ordinal_exists IF NOT EXISTS
FOR ()-[rel:HAS_CHUNK]-()
REQUIRE rel.ordinal IS NOT NULL;

CREATE CONSTRAINT has_artifact_type_exists IF NOT EXISTS
FOR ()-[rel:HAS_ARTIFACT]-()
REQUIRE rel.artifact_type IS NOT NULL;

CREATE CONSTRAINT mentions_document_ref_exists IF NOT EXISTS
FOR ()-[rel:MENTIONS]-()
REQUIRE rel.document_id IS NOT NULL;

CREATE CONSTRAINT mentions_chunk_ref_exists IF NOT EXISTS
FOR ()-[rel:MENTIONS]-()
REQUIRE rel.chunk_id IS NOT NULL;

CREATE CONSTRAINT mentions_offsets_exist IF NOT EXISTS
FOR ()-[rel:MENTIONS]-()
REQUIRE rel.offset_start IS NOT NULL;

CREATE CONSTRAINT mentions_offsets_end_exist IF NOT EXISTS
FOR ()-[rel:MENTIONS]-()
REQUIRE rel.offset_end IS NOT NULL;

