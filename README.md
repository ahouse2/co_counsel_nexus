# Co-Counsel: An Advanced Agentic Legal Platform

Co-Counsel is a sophisticated legal technology platform leveraging a modular agentic architecture to automate and assist with complex legal tasks. Built on the Microsoft Agents Framework SDK, it integrates specialized AI agent teams, each equipped with a suite of tools, to provide robust and reliable support across various legal domains.

## Features

Co-Counsel's core strength lies in its diverse and intelligent agent teams, designed for redundancy and rigorous quality assurance:

*   **Document Ingestion Crew:** Automates the processing, indexing, and knowledge graph integration of legal documents.
*   **Forensic Analysis Crew:** Performs deep forensic examination of digital evidence, including PDFs, images, financial data, and cryptocurrency transactions.
*   **Legal Research Crew:** Conducts comprehensive legal research across case law, statutes, regulations, and court rules using specialized APIs and web scraping.
*   **Litigation Support Crew:** Formulates case theories, drafts legal motions, and prepares for litigation through strategic analysis and simulation.
*   **Software Development Crew:** An internal team of agents dedicated to maintaining, extending, and improving the Co-Counsel application itself.
*   **AI QA Oversight Committee:** A meta-level, asynchronous committee that audits the entire agentic system for behavior, prompt engineering, memory, and safety.

Each team operates with built-in redundancy (primary/backup agents) and a three-step QA process (Validation, Critique, Refinement) to ensure high-quality, reliable outputs.

## Architecture

The platform is built around a modular agentic architecture:

*   **MicrosoftAgentsOrchestrator:** The central component responsible for managing agent sessions, routing user requests to the appropriate agent team, and overseeing workflow execution.
*   **Agent Teams:** Collections of specialized agents working collaboratively to achieve complex goals. Each team has a Supervisor agent, primary and backup functional agents, and dedicated QA agents.
*   **Agents:** Individual AI entities with specific roles, descriptions, and access to specialized tools.
*   **Tools:** Wrappers around dedicated services that enable agents to interact with external systems, perform computations, and access data (e.g., `KnowledgeGraphService`, `BlockchainService`, `DocumentProcessingService`).
*   **Services:** Backend components providing core functionalities like document processing, knowledge graph management, blockchain interaction, and LLM integration.

This architecture ensures a clear separation of concerns, promoting modularity, scalability, and maintainability.

## Getting Started

To set up and run the Co-Counsel project locally:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-repo/co-counsel.git
    cd co-counsel
    ```

2.  **Set up Python Environment:**
    ```bash
    python -m venv venv
    ./venv/Scripts/activate # On Windows
    source venv/bin/activate # On macOS/Linux
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r backend/requirements.txt
    ```
    *Note: Some tools like `pytesseract` require external installations (e.g., Tesseract OCR engine).*

4.  **Configuration:**
    Create a `.env` file in the `backend/app` directory (or the project root, depending on `SettingsConfigDict` configuration) and populate it with necessary API keys and settings. Refer to `backend/app/config.py` for a list of configurable parameters. Key settings include:
    *   `GEMINI_API_KEY` or `OPENAI_API_KEY`
    *   `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
    *   `QDRANT_URL` or `VECTOR_DIR`
    *   `COURTLISTENER_TOKEN`, `CASELAW_API_KEY`, `GOVINFO_API_KEY`
    *   `VERIFY_PDF_ENDPOINT`, `VERIFY_PDF_API_KEY`
    *   `BLOCKCHAIN_API_KEY_ETHEREUM`, `BLOCKCHAIN_API_KEY_BITCOIN`
    *   `SQL_DATABASE_URI`

5.  **Run the Application:**
    ```bash
    uvicorn backend.app.main:app --reload
    ```
    The API will be available at `http://127.0.0.1:8000`.

## Usage

Interact with the agentic system primarily through the FastAPI endpoints. The `MicrosoftAgentsOrchestrator` will route your requests to the appropriate agent team.

*   **API Documentation:** Access the interactive API documentation at `http://127.0.0.1:8000/docs` for available endpoints and models.
*   **Example Interaction:**
    *   To initiate a forensic analysis: Send a request to the agent endpoint with a question like "Perform forensic analysis on this PDF document for tampering."
    *   To conduct legal research: Ask "Research case law related to contract disputes in California."

## Contributing

We welcome contributions! Please refer to our `CONTRIBUTING.md` (if available) for guidelines.

## License

This project is licensed under the MIT License.
