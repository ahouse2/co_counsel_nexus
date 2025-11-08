# Co-Counsel Deployment Guide

This guide outlines a "one-click" deployment procedure for the Co-Counsel application using Docker Compose. This method simplifies the setup of all necessary services (backend API, databases, etc.) into a single command.

## Prerequisites

Before you begin, ensure you have the following software installed on your deployment machine:

*   **Git:** For cloning the repository.
*   **Docker:** The containerization platform.
*   **Docker Compose:** For defining and running multi-container Docker applications.

## Configuration

The Co-Counsel application relies on environment variables for its configuration. These variables are typically stored in a `.env` file at the root of the project.

1.  **Create `.env` file:**
    Create a file named `.env` in the root directory of the cloned repository (e.g., `E:\projects\op_veritas_2\.env`).

2.  **Populate `.env`:**
    Refer to `backend/app/config.py` for a comprehensive list of all configurable parameters. At a minimum, you will need to provide:
    *   **LLM API Keys:** `GEMINI_API_KEY` or `OPENAI_API_KEY` (depending on your chosen provider).
    *   **Database Credentials:** `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, and `SQL_DATABASE_URI`.
    *   **External API Keys:** `COURTLISTENER_TOKEN`, `CASELAW_API_KEY`, `GOVINFO_API_KEY`, `BLOCKCHAIN_API_KEY_ETHEREUM`, `BLOCKCHAIN_API_KEY_BITCOIN`, `VERIFY_PDF_API_KEY`, etc.
    *   **Security Keys:** `ENCRYPTION_KEY`, `SECRET_KEY`.

    **Example `.env` content (minimal):**
    ```env
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    NEO4J_URI="bolt://neo4j:7687"
    NEO4J_USER="neo4j"
    NEO4J_PASSWORD="your_neo4j_password"
    SQL_DATABASE_URI="postgresql://user:password@postgres:5432/cocounsel_db"
    ENCRYPTION_KEY="a_very_secret_key_for_document_encryption_32_bytes_long"
    SECRET_KEY="super-secret-jwt-key-at-least-32-chars-long"
    # Add other necessary API keys and settings as per backend/app/config.py
    ```
    **Important:** Ensure `ENCRYPTION_KEY` and `SECRET_KEY` are strong, randomly generated strings of at least 32 characters.

## Deployment Steps

Follow these steps to deploy Co-Counsel:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-repo/co-counsel.git
    cd co-counsel
    ```
    *(Replace `https://github.com/your-repo/co-counsel.git` with the actual repository URL)*

2.  **Configure `.env`:**
    As described in the "Configuration" section above, create and populate your `.env` file.

3.  **Build and Run with Docker Compose:**
    Navigate to the root directory of the project (where `docker-compose.yml` and your `.env` file are located) and execute the following command:
    ```bash
    docker-compose up --build -d
    ```
    *   `up`: Starts the services defined in `docker-compose.yml`.
    *   `--build`: Builds (or rebuilds) images before starting containers. This ensures you're running the latest code.
    *   `-d`: Runs containers in detached mode (in the background).

    This command will:
    *   Build the Docker images for your backend and any other services defined (e.g., Neo4j, PostgreSQL).
    *   Create and start the containers.
    *   Set up network connections between services.

4.  **Verify Deployment:**
    *   **Check container status:**
        ```bash
        docker-compose ps
        ```
        All services should show `Up`.
    *   **View logs:**
        ```bash
        docker-compose logs -f backend
        ```
        Check for any errors or warnings from the backend service.
    *   **Access API Documentation:**
        Once the backend service is running, you should be able to access the interactive API documentation (Swagger UI) in your web browser, typically at `http://localhost:8000/docs`.

## Post-Deployment

*   **Initial Database Setup:** If your `docker-compose.yml` or application startup scripts do not automatically handle database migrations, you may need to run initial migration commands. (The `Base.metadata.create_all` in `main.py` handles table creation on startup).
*   **Accessing Services:**
    *   **Backend API:** `http://localhost:8000`
    *   **Neo4j Browser:** Typically `http://localhost:7474` (check your `docker-compose.yml` for exact port mapping).
    *   **Qdrant UI:** If Qdrant is deployed via Docker Compose, check its port mapping.

## Troubleshooting

*   **"Port already in use" error:** Ensure no other applications are using the ports required by Co-Counsel (e.g., 8000 for FastAPI, 7474/7687 for Neo4j).
*   **Container failed to start:** Use `docker-compose logs <service_name>` (e.g., `docker-compose logs backend`) to inspect the logs for specific error messages.
*   **Missing environment variables:** Double-check your `.env` file against `backend/app/config.py` to ensure all required variables are set.
*   **Network issues:** Verify Docker's network configuration if containers cannot communicate.

This "one-click" procedure provides a streamlined way to get Co-Counsel up and running in a production-like environment.
