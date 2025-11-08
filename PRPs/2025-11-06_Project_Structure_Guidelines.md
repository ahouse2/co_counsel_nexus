# 2025-11-06_Project_Structure_Guidelines.md

## Project Structure Guidelines for Co-Counsel Platform

### 1. Overview

This document outlines the standardized project structure for the Co-Counsel AI Legal Discovery Platform. The goal of this structure is to ensure clarity, modularity, maintainability, and scalability, facilitating collaborative development and adherence to the "one application" principle. This structure is derived from the project's Product Requirements Documents (PRDs) and Implementation Plans (PRPs), emphasizing a clear separation of concerns between frontend, backend, and infrastructure components, with a strong focus on the multi-agent architecture within the backend.

### 2. High-Level Project Structure

The project is organized into the following top-level directories:

```
E:\projects\op_veritas_2\
├───.git/                   # Git repository metadata
├───.github/                # GitHub Actions workflows and CI/CD configurations
├───docs/                   # Comprehensive project documentation (architecture, design, etc.)
├───frontend/               # All frontend application code (React/TypeScript)
├───backend/                # All backend application code (FastAPI/Python)
├───infra/                  # Infrastructure as Code (Docker, Helm, migrations)
├───scripts/                # Utility scripts for development, deployment, and maintenance
├───tools/                  # Development tools, QA scripts, monitoring utilities
├───venv/                   # Python virtual environment (local development)
└───PRPs/                   # Project Refinement Plans and other strategic documents
```

### 3. Backend Structure (`backend/`)

The `backend/` directory encapsulates all server-side logic and services.

```
backend/
├───app/                    # Core FastAPI application logic
│   ├───api/			    # FastAPI routers and API endpoints, organized by domain
│   │   ├───agents/         # API endpoints for interacting with agent teams
│   │   ├───auth.py         # Authentication and authorization API routes
│   │   ├───cases.py        # Case management API routes
│   │   ├───documents.py    # Document management API routes
│   │   └───...             # Other domain-specific routers (e.g., retrieval, graph, billing)
│   ├───agents/             # Multi-agent architecture components
│   │   ├───core/           # Core agent framework components (e.g., Planner, Executor, Facade blueprints)
│   │   ├───teams/          # Specific agent teams (e.g., legal_research, evidence_analysis)
│   │   │   ├───legal_research/
│   │   │   │   ├───agent.py
│   │   │   │   ├───executor.py
│   │   │   │   ├───models.py
│   │   │   │   └───planner.py
│   │   │   └───...         # Other agent teams
│   │   └───GraphBuilderAgent.py # Example of a specific agent implementation
│   ├───auth/               # Authentication and authorization logic (e.g., password hashing, token management)
│   ├───case_management/    # Business logic for managing legal cases
│   ├───config.py           # Application configuration and settings
│   ├───database.py         # Database connection and session management
│   ├───document_ingestion/ # Logic for document upload, parsing, and metadata extraction
│   ├───forensics/          # Forensics suite logic (e.g., tamper detection, crypto tracing)
│   ├───graph/              # Neo4j data models, Cypher queries, and graph interaction services
│   ├───models/             # Pydantic models for API, SQLAlchemy/ORM models for database
│   ├───services/           # Shared business logic services and utilities
│   ├───storage/            # Data storage interfaces (e.g., document store, knowledge graph store)
│   ├───main.py             # Main FastAPI application entry point (minimal, includes routers)
│   └───...                 # Other domain-specific application modules
├───runtime/                # Local LLM models and runtime configurations
│   ├───gguf/               # GGUF format models
│   ├───llama_cpp/          # Llama.cpp related files
│   ├───ollama/             # Ollama related files
│   └───...
├───tests/                  # Backend unit, integration, and performance tests
├───requirements.txt        # Python dependencies
├───Dockerfile              # Dockerfile for backend service containerization
└───...                     # Other backend-specific configuration files
```

### 4. Frontend Structure (`frontend/`)

The `frontend/` directory contains the entire client-side application.

```
frontend/
├───public/                 # Static assets (e.g., index.html, manifest, images)
├───src/                    # Frontend source code (React/TypeScript)
│   ├───assets/             # Images, icons, fonts, and other static assets used by components
│   ├───components/         # Reusable UI components (e.g., buttons, cards, forms, Layout)
│   │   ├───Layout.tsx      # Main application layout (header, navigation, footer)
│   │   └───...             # Other shared components
│   ├───hooks/              # Custom React hooks for reusable logic
│   ├───pages/              # Top-level page components, corresponding to main application views
│   │   ├───DashboardPage.tsx
│   │   ├───UploadEvidencePage.tsx
│   │   ├───GraphExplorerPage.tsx
│   │   └───...             # Other page components
│   ├───services/           # Frontend services for API calls, state management, and external integrations
│   ├───styles/             # Global styles, TailwindCSS configuration, CSS modules
│   ├───types/              # TypeScript type definitions and interfaces
│   ├───App.tsx             # Main application component, responsible for routing and page rendering
│   ├───main.tsx            # Entry point for the React application (bootstrap)
│   └───...                 # Other utility files or global configurations
├───tests/                  # Frontend unit and end-to-end (E2E) tests (e.g., Playwright, Jest)
├───package.json            # Node.js project metadata and dependencies
├───tsconfig.json           # TypeScript configuration
├───tailwind.config.ts      # Tailwind CSS configuration
├───vite.config.ts          # Vite build tool configuration
└───...                     # Other frontend-specific configuration files
```

### 5. Infrastructure (`infra/`)

The `infra/` directory contains configurations and scripts for deploying and managing the application's infrastructure.

```
infra/
├───docker-compose.yml      # Docker Compose configurations for local development and deployment
├───migrations/             # Database migration scripts (e.g., PostgreSQL, Neo4j)
├───otel-collector-config.yaml # OpenTelemetry Collector configuration
├───helm/                   # Helm charts for Kubernetes deployment (future)
└───...                     # Other infrastructure-related files
```

### 6. Other Top-Level Directories

*   **`.git/`**: Contains all the information that Git needs to manage the project's version history.
*   **`.github/`**: Stores GitHub-specific configurations, primarily GitHub Actions workflows for CI/CD.
*   **`docs/`**: General project documentation, architectural diagrams, design documents, and other non-code related information.
*   **`scripts/`**: Various utility scripts (e.g., `bootstrap_backend.sh`, `orphan_scan.py`, performance testing scripts).
*   **`tools/`**: Contains specialized development tools, QA scripts, or monitoring utilities that are not part of the core application.
*   **`venv/`**: The Python virtual environment, used to manage project dependencies in isolation.
*   **`PRPs/`**: Project Refinement Plans, Product Requirements Documents, and other strategic planning documents.

### 7. Naming Conventions

Adherence to consistent naming conventions is crucial for readability and maintainability:

*   **Node Labels (Neo4j):** PascalCase (e.g., `LegalCase`, `Document`).
*   **Relationship Types (Neo4j):** SCREAMING_SNAKE_CASE (e.g., `HAS_EVIDENCE`, `RELATED_TO`).
*   **Properties (Neo4j):** camelCase (e.g., `uploadDate`, `tamperScore`).
*   **Python Modules/Files:** snake_case (e.g., `document_ingestion.py`).
*   **Python Classes:** PascalCase (e.g., `DocumentIngestionService`).
*   **Python Functions/Variables:** snake_case (e.g., `process_document`).
*   **TypeScript/React Components:** PascalCase (e.g., `DashboardPage.tsx`, `Layout.tsx`).
*   **TypeScript/React Hooks:** camelCase, prefixed with `use` (e.g., `useAppLayout`).
*   **TypeScript Files:** camelCase or PascalCase depending on content (e.g., `apiClient.ts`, `types.ts`).

### 8. Best Practices and Future Considerations

*   **Modularity:** Each module and component should have a single, well-defined responsibility.
*   **Reusability:** Promote the creation of reusable components and services across the application.
*   **Consistency:** Maintain consistent coding styles, patterns, and documentation across the entire codebase.
*   **Documentation:** Keep this document and other `docs/` and `PRPs/` up-to-date with any significant structural changes.
*   **Testing:** Ensure that unit, integration, and end-to-end tests are implemented and maintained for all components.

This structured approach will enable efficient development, easier onboarding for new collaborators, and a robust foundation for the Co-Counsel platform's continued evolution.
