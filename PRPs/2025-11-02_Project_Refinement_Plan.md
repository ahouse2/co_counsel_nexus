# Implementation Plan: Project Refinement and Hardening

## Overview
This plan addresses the key findings from the code review conducted on 2025-11-02. The goal is to improve project structure, code quality, testing, and overall robustness to elevate the "Co-Counsel" platform to an enterprise-grade standard.

## Requirements Summary
- **Requirement 1:** Resolve the duplicated `NinthOctopusMitten` directory to create a single source of truth.
- **Requirement 2:** Standardize the project's name to "Co-Counsel" across the entire codebase.
- **Requirement 3:** Introduce automated security vulnerability scanning into the CI/CD pipeline.
- **Requirement 4:** Refactor large, monolithic files into smaller, more focused modules.
- **Requirement 5:** Increase test coverage for complex UI workflows and backend agentic systems.
- **Requirement 6:** Replace hardcoded data in frontend components with live data from the backend.
- **Requirement 7:** Formalize and audit the chain of custody for all evidence.
- **Requirement 8:** Establish performance baselines and conduct load testing.

## Research Findings
### Best Practices
- **Single Source of Truth:** A repository should not contain duplicated code or project structures. This is critical for maintainability and avoiding confusion.
- **Consistent Naming:** A consistent project name is essential for clear communication and branding.
- **Automated Security:** Integrating security scanning into CI/CD is a best practice for preventing vulnerabilities.
- **Modularity:** Large files should be broken down into smaller modules to improve readability and testability.

### Reference Implementations
- **Backend Routers:** The FastAPI documentation provides clear patterns for using `APIRouter` to structure larger applications.
- **Frontend State Management:** The existing use of React Context (`QueryContext`, `SettingsContext`) is a good pattern to follow for managing shared state.
- **Infrastructure as Code:** The project's use of Docker and Helm is already strong and should be continued.

### Technology Decisions
- **File System Operations:** Standard shell commands (`mv`, `rm`, `sed`) will be used for the cleanup phase.
- **CI/CD Integration:** Security scanning will be integrated using a tool compatible with the existing GitHub Actions workflows (e.g., Snyk, Trivy).
- **Testing:** We will continue to use `pytest` for the backend and `vitest` with Playwright/Cypress for frontend end-to-end testing.

## Implementation Tasks

### Phase 1: Foundational Cleanup (Immediate Priority)

1.  **Task: Resolve Code Duplication**
    -   **Description:** The duplicated `NinthOctopusMitten` directory will be removed, and its contents will be merged into the root project structure if necessary. This will establish a single source of truth.
    -   **Files to modify/create:** The entire project structure.
    -   **Dependencies:** None.
    -   **Estimated effort:** 1 hour.

2.  **Task: Unify Project Naming**
    -   **Description:** Perform a global search-and-replace to standardize the project name to "Co-Counsel" and remove references to "NinthOctopusMitten".
    -   **Files to modify/create:** Numerous files across the codebase.
    -   **Dependencies:** Task 1.
    -   **Estimated effort:** 2 hours.

3.  **Task: Implement Dependency Vulnerability Scanning**
    -   **Description:** Integrate a security scanning tool into the `.github/workflows/backend_ci.yml` and a new frontend CI workflow.
    -   **Files to modify/create:** `.github/workflows/backend_ci.yml`, `.github/workflows/frontend_ci.yml`.
    -   **Dependencies:** None.
    -   **Estimated effort:** 3 hours.

### Phase 2: Hardening and Refinement

4.  **Task: Refactor Backend Routers**
    -   **Description:** Break down `backend/app/main.py` into smaller, domain-specific routers using `fastapi.APIRouter`.
    -   **Files to modify/create:** `backend/app/main.py`, `backend/app/api/ingestion.py`, `backend/app/api/agents.py`, etc.
    -   **Dependencies:** Task 1.
    -   **Estimated effort:** 4 hours.

5.  **Task: Refactor Frontend App Component**
    -   **Description:** Decompose the `frontend/src/App.tsx` component, moving state and logic into more focused sub-components or custom hooks.
    -   **Files to modify/create:** `frontend/src/App.tsx`, and new files in `frontend/src/components` or `frontend/src/hooks`.
    -   **Dependencies:** Task 1.
    -   **Estimated effort:** 3 hours.

6.  **Task: Enhance Backend Test Coverage**
    -   **Description:** Add integration tests for the `MicrosoftAgentsOrchestrator` to validate different agent sequences and error conditions.
    -   **Files to modify/create:** New test files in `backend/tests/`.
    -   **Dependencies:** Task 1.
    -   **Estimated effort:** 5 hours.

7.  **Task: Implement Frontend E2E Tests**
    -   **Description:** Set up Playwright or Cypress and create end-to-end tests for the evidence upload workflow and the graph explorer.
    -   **Files to modify/create:** New files in `frontend/tests/e2e/`.
    -   **Dependencies:** Task 1.
    -   **Estimated effort:** 6 hours.

### Phase 3: Enterprise-Readiness

8.  **Task: Connect Graph Explorer to Backend**
    -   **Description:** Remove the hardcoded data in `GraphExplorerPanel.tsx` and connect it to the live `/graph/neighbor` API endpoint.
    -   **Files to modify/create:** `frontend/src/components/GraphExplorerPanel.tsx`.
    -   **Dependencies:** Task 5.
    -   **Estimated effort:** 3 hours.

9.  **Task: Formalize Evidence Chain of Custody**
    -   **Description:** Enhance the `ForensicsService` and `DocumentStore` to create an explicit, auditable chain of custody log for each piece of evidence.
    -   **Files to modify/create:** `backend/app/services/forensics.py`, `backend/app/storage/document_store.py`, and a new `storage/audit_log.py`.
    -   **Dependencies:** Task 4.
    -   **Estimated effort:** 8 hours.

10. **Task: Establish Performance Baselines**
    -   **Description:** Create scripts to benchmark API performance and frontend rendering times. Integrate these into a new CI workflow to track performance over time.
    -   **Files to modify/create:** New files in `scripts/performance/`.
    -   **Dependencies:** None.
    -   **Estimated effort:** 6 hours.

## Codebase Integration Points
### Files to Modify
-   The entire project structure during the initial cleanup.
-   `backend/app/main.py` (for refactoring).
-   `frontend/src/App.tsx` (for refactoring).
-   `.github/workflows/backend_ci.yml` (for security scanning).

### New Files to Create
-   `PRPs/2025-11-02_Project_Refinement_Plan.md` (this file).
-   `backend/app/api/` directory with new router files.
-   `frontend/tests/e2e/` directory with new end-to-end tests.
-   `scripts/performance/` directory with new benchmarking scripts.

### Existing Patterns to Follow
-   **Backend Services:** Continue the pattern of using FastAPI's dependency injection to provide services to the API layer.
-   **Frontend Hooks:** Encapsulate complex client-side logic in custom hooks, as seen in `useVoiceSession.ts`.
-   **CI/CD:** Extend the existing GitHub Actions workflows for new testing and security stages.

## Testing Strategy
-   **Unit Tests:** Continue to be written for individual functions and components.
-   **Integration Tests:** New integration tests will be added for the agent orchestrator.
-   **End-to-End Tests:** A new E2E test suite will be created for critical user workflows.

## Success Criteria
-   [ ] The `NinthOctopusMitten` directory is completely removed.
-   [ ] The project is consistently named "Co-Counsel" throughout the codebase.
-   [ ] The CI pipeline includes a failing step for high-severity security vulnerabilities.
-   [ ] The backend `main.py` and frontend `App.tsx` files are significantly smaller and more focused.
-   [ ] New integration and E2E tests are implemented and passing.
-   [ ] The Graph Explorer is populated with live data.
-   [ ] An auditable chain of custody log is generated for all evidence.
-   [ ] Performance benchmarks are established and tracked.

---
*This plan is ready for execution with `/archon:execute-plan`*
