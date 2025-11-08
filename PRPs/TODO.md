# Co-Counsel Legal Platform - Phase 1 TODO List

## 1. Foundational Services

### 1.1. User Authentication & Authorization
*   **Backend:**
    *   [DONE] Implement user registration API endpoint (`/api/auth/register`).
    *   [DONE] Implement user login API endpoint (`/api/auth/login`) with JWT token generation.
    *   [DONE] Implement JWT token validation middleware for protected API endpoints.
    *   [DONE] **CRITICAL:** Load `SECRET_KEY` from environment variable (e.g., `settings.SECRET_KEY`) for JWT.
    *   [DONE] Implement role-based access control (RBAC) logic:
        *   [DONE] Add `role` field to `DBUser` model in `backend/app/models/sql.py`.
        *   [DONE] Modify `register_user` to assign a default role.
        *   [DONE] Create a dependency to check user roles for protected endpoints.
    *   [DONE] Implement refresh token mechanism for persistent sessions.
    *   [DONE] Implement JWT token revocation mechanism (e.g., for logout or compromised tokens).
    *   [DONE] Implement password reset/forgot password functionality.
    *   [DONE] Implement email verification for new user registrations.
    *   [DONE] Implement rate limiting on `/register` and `/token` endpoints to prevent brute-force attacks.
    *   [DONE] Review and enhance error handling for authentication flows.
*   **Frontend:**
    *   [TODO] Develop `Login` and `Registration` UI components.
    *   [TODO] Integrate `Login` and `Registration` components with backend authentication APIs.
    *   [TODO] Implement client-side JWT token storage and management (e.g., using `localStorage` or `sessionStorage`).
    *   [TODO] Implement protected routes and UI elements based on user authentication status and roles.

### 1.2. Document Ingestion & Processing
*   **Backend:**
    *   [TODO] Create `backend/app/ingestion` module and implement document upload API endpoint (`/api/ingestion/upload`) supporting various document types (PDF, DOCX, TXT).
    *   [TODO] Develop document parsing logic to extract text content from uploaded files.
    *   [TODO] Implement metadata extraction (e.g., file name, upload date, original author) from documents.
    *   [TODO] Integrate with `backend/app/storage/document_store.py` to store *metadata* about raw and processed document content (e.g., file paths/URIs to raw documents).
    *   [TODO] Implement a separate mechanism for storing raw document binaries (e.g., local file system, S3-compatible storage).
    *   [TODO] Implement asynchronous processing for large documents to avoid blocking the API.
*   **Frontend:**
    *   [TODO] Enhance `EvidenceUploadZone` component to allow users to select and upload multiple files.
    *   [TODO] Display real-time progress and status updates during document uploads and processing.
    *   [TODO] Implement error handling and user feedback for failed uploads or processing.

### 1.3. Graph Database Integration
*   **Backend:**
    *   [TODO] **NEW MODULE:** Create `backend/app/graph` module and define Neo4j data models (nodes and relationships) for key legal entities (e.g., `Case`, `Document`, `Person`, `Organization`, `Concept`) and their relationships.
    *   [TODO] Implement API endpoints for creating, reading, updating, and deleting graph nodes and relationships via the new `backend/app/graph` module.
    *   [TODO] Develop Cypher queries for efficient graph data retrieval and manipulation.
*   **Frontend:**
    *   [TODO] Integrate `GraphExplorerPanel` with backend graph APIs to fetch and display graph data.
    *   [TODO] Implement basic interactive graph visualization (e.g., using a library like `react-force-graph` or `vis.js`).
    *   [TODO] Add functionality to `GraphExplorerPanel` for filtering, searching, and highlighting nodes/relationships.

## 2. Agentic Workflows

### 2.1. Legal Research Agent Team
*   **Backend:**
    *   [TODO] **NEW AGENT TEAM:** Define `LegalResearchRequest` and `LegalResearchContext` dataclasses in `backend/app/agents/legal_research/models.py`.
    *   [TODO] Implement `LegalResearchPlanner` (based on `DevTeamPlanner` blueprint) in `backend/app/agents/legal_research/planner.py` to triage legal research requests.
    *   [TODO] Implement `LegalResearchExecutor` (based on `DevTeamExecutor` blueprint) in `backend/app/agents/legal_research/executor.py` to execute research queries and generate research summaries/findings.
    *   [TODO] Integrate `LegalResearchExecutor` with external legal databases/APIs (e.g., LexisNexis, Westlaw - *placeholder for now, actual integration details will be defined later*).
    *   [TODO] Implement `LegalResearchAgentFacade` in `backend/app/agents/legal_research/agent.py` to provide a unified interface.
    *   [TODO] Create API endpoints (`/api/agents/legal_research/`) in `backend/app/api/routers/legal_research.py` to interact with the Legal Research Agent Team.
*   **Frontend:**
    *   [TODO] Develop UI components for initiating legal research requests (e.g., search bar, filters).
    *   [TODO] Display legal research results and summaries in a user-friendly format.

### 2.2. Evidence Analysis Agent Team
*   **Backend:**
    *   [TODO] Define `EvidenceAnalysisRequest` and `EvidenceAnalysisContext` dataclasses in `backend/app/agents/evidence_analysis/models.py`.
    *   [TODO] Implement `EvidenceAnalysisPlanner` (based on `DevTeamPlanner` blueprint) in `backend/app/agents/evidence_analysis/planner.py` to triage evidence analysis requests.
    *   [TODO] Implement `EvidenceAnalysisExecutor` (based on `DevTeamExecutor` blueprint) in `backend/app/agents/evidence_analysis/executor.py` to perform detailed analysis of ingested documents, identifying key facts and relationships.
    *   [TODO] Integrate `EvidenceAnalysisExecutor` with `backend/app/storage/document_store.py` and the new `backend/app/graph` module for data retrieval and storage.
    *   [TODO] Implement `EvidenceAnalysisAgentFacade` in `backend/app/agents/evidence_analysis/agent.py` to provide a unified interface.
    *   [TODO] Create API endpoints (`/api/agents/evidence_analysis/`) in `backend/app/api/routers/evidence_analysis.py` to interact with the Evidence Analysis Agent Team.
*   **Frontend:**
    *   [TODO] Develop UI components for initiating evidence analysis (e.g., selecting documents for analysis).
    *   [TODO] Visualize evidence analysis findings (e.g., document relationships, extracted entities, timelines) within the `GraphExplorerPanel` or a dedicated view.

## 3. User Interface (UI) Development

### 3.1. Dashboard
*   **Frontend:**
    *   [DONE] Develop dashboard components (`frontend/src/components/LegalDashboard/LegalDashboard.tsx`) with a basic layout and mock data.
    *   [TODO] Integrate dashboard with backend APIs (`/legal-theory/synthesize`, `/predictive-analytics/outcome`, `/strategic-recommendations/get`) to fetch real-time data, replacing mock data.
    *   [TODO] Enhance dashboard with dynamic content based on user roles and case context.
*   **Backend:**
    *   [TODO] Implement `/legal-theory/synthesize` API endpoint.
    *   [TODO] Implement `/predictive-analytics/outcome` API endpoint.
    *   [TODO] Implement `/strategic-recommendations/get` API endpoint.

### 3.2. Case Management
*   **Frontend:**
    *   [TODO] **NEW UI COMPONENT:** Develop UI components (`frontend/src/components/CaseManagement/`) for creating, viewing, editing, and deleting legal cases.
    *   [TODO] Integrate case management components with backend APIs for case data.
*   **Backend:**
    *   [TODO] Create `backend/app/case_management` module and implement API endpoints for CRUD operations on legal cases.

### 3.3. Document Viewer
*   **Frontend:**
    *   [DONE] Develop interactive document viewer component (`frontend/src/components/EvidenceViewer/EvidenceViewer.tsx`) with features like text highlighting, search, and annotation, using mock data.
    *   [TODO] Integrate document viewer with backend APIs (`/documents/{documentId}`, `/graph/entities?doc_id={documentId}`, `/annotations`) to fetch real document content, entities, and annotations, replacing mock data.
*   **Backend:**
    *   [TODO] Implement API endpoint (`/documents/{documentId}`) to retrieve document content.
    *   [TODO] Implement API endpoint (`/annotations`) for managing document annotations (CRUD operations).
    *   [TODO] Enhance `/graph/entities` endpoint to filter entities by document ID.

### 3.4. Graph Visualization
*   **Frontend:**
    *   [DONE] Develop 3D graph visualization components (`frontend/src/components/graph-explorer/Graph3DScene.tsx`, `frontend/src/components/graph-explorer/GraphExplorerPanel.tsx`) with interactive features and cinematic styling, using mock data and basic node positioning.
    *   [TODO] Integrate `GraphExplorerPanel` with backend graph APIs (`/graph/neighbor`, etc.) to fetch real graph data from Neo4j.
    *   [TODO] Implement graph layout algorithms (e.g., force-directed, hierarchical) to position nodes dynamically based on graph structure, rather than random or index-based positioning.
    *   [TODO] Implement advanced filtering, searching, and highlighting options within the `GraphExplorerPanel`.
    *   [TODO] Develop UI for node/edge property display and editing.
*   **Backend:**
    *   [TODO] Enhance `/graph/neighbor` API endpoint to return comprehensive graph data (nodes, edges, properties) from Neo4j.
    *   [TODO] Implement additional graph traversal and query API endpoints as needed for advanced visualization features.

## 4. Deployment & Infrastructure

### 4.1. One-Click Installer
*   [TODO] Create scripts for packaging the backend and frontend into self-contained executables for Windows (`.exe`), macOS (`.dmg`), and Linux (`.deb`).
    *   Consider using tools like PyInstaller for Python backend and Electron/Tauri for bundling the frontend with a web runtime.
*   [TODO] Ensure all required dependencies (Python runtime, Node.js runtime, database binaries, etc.) are bundled with the installer.
*   [TODO] Implement basic configuration options for the installer (e.g., installation path, port numbers, initial user setup).
*   [TODO] Develop an uninstaller for each platform.
*   [TODO] Implement digital signing for executables (Windows, macOS) for security and trust.

### 4.2. Local Development Environment
*   [TODO] Document clear, step-by-step instructions for setting up the local development environment for both backend and frontend, including prerequisites and common troubleshooting.
*   [TODO] Provide `docker-compose.yml` configurations for easy spin-up of all development services (backend, frontend, Neo4j, Qdrant, etc.).
*   [TODO] Ensure `docker-compose.yml` includes persistent volume configurations for data.
*   [TODO] Document how to run tests (unit, integration, E2E) in the local development environment.
