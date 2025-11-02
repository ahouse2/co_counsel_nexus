# Co-Counsel Backend

The backend for the NinthOctopusMitten legal tech platform, built with FastAPI and Python 3.11+.

## Getting Started

### Prerequisites
- Python 3.11+
- Optional: [`uv`](https://github.com/astral-sh/uv) for Python dependency management

### Installation
```bash
# Bootstrap backend dependencies
./scripts/bootstrap_backend.sh
```

Or manually install dependencies:
```bash
pip install -r requirements.txt
```

### Development Server
```bash
uvicorn app.main:app --port 8000 --reload
```

## Project Structure
```
backend/
├── app/                 # Main FastAPI application
│   ├── main.py         # Application entry point
│   ├── api/            # API routes and endpoints
│   ├── models/         # Data models and schemas
│   ├── providers/      # AI provider integrations
│   └── services/       # Business logic services
├── ingestion/          # Document ingestion pipeline
├── tools/              # Utility functions and helpers
├── tests/              # Unit and integration tests
├── runtime/            # Runtime configuration and utilities
└── docs/               # Backend documentation
```

## Working with the Backend

### Development Workflow

1. **Start the development server:**
   ```bash
   uvicorn app.main:app --port 8000 --reload
   ```
   This will start the FastAPI server with hot reloading enabled.

2. **API Documentation:**
   - Interactive API docs: http://localhost:8000/docs
   - Alternative API docs: http://localhost:8000/redoc

3. **Environment Configuration:**
   - Environment variables are configured through Docker Compose
   - For local development, create a `.env` file in the project root

4. **Database Services:**
   - Neo4j (graph database): http://localhost:7474
   - Qdrant (vector search): http://localhost:6333/dashboard

### Key Components

1. **Provider Management:**
   - Multi-provider AI model support (Gemini, OpenAI, Azure OpenAI, etc.)
   - Encrypted settings service for API keys and credentials
   - Dynamic provider switching via API

2. **Knowledge Ingestion:**
   - Document parsing and processing pipeline
   - Knowledge graph construction with Neo4j
   - Vector embeddings storage with Qdrant

3. **API Endpoints:**
   - `/query` - Legal research and question answering
   - `/timeline` - Case timeline construction
   - `/settings` - Provider and credential management
   - `/evidence` - Document upload and management

### Testing

Run backend tests:
```bash
python -m pytest backend/tests -q
```

Run specific test categories:
```bash
# Unit tests
python -m pytest backend/tests/unit -q

# Integration tests
python -m pytest backend/tests/integration -q

# API tests
python -m pytest backend/tests/api -q
```

### Code Quality

Run linting and type checking:
```bash
ruff check backend/
mypy backend/
```

Format code:
```bash
ruff format backend/
```

## Deployment

The backend is deployed as part of the Docker Compose stack:
```bash
docker compose --project-directory infra up -d
```

For production deployments, use the Helm charts in `infra/helm/`.

## Troubleshooting

- **Import errors** — Ensure all dependencies are installed with `pip install -r requirements.txt`
- **Database connection issues** — Verify Neo4j and Qdrant services are running
- **Provider configuration** — Check that API keys are properly configured in settings
- **Performance issues** — Monitor resource usage and consider enabling GPU acceleration