# Operations Runbook (MVP)

Services
- api: FastAPI (uvicorn); health at /health
- neo4j: bolt at 7687; browser 7474
- qdrant: HTTP 6333

Health Checks
- curl http://localhost:8000/health → {"status":"ok"}
- Check Docker logs: docker compose -f infra/docker-compose.yml logs -f

Env Vars
- NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, QDRANT_URL, VECTOR_DIR

Common Tasks
- Restart service: docker compose -f infra/docker-compose.yml restart api
- Rebuild API: docker compose -f infra/docker-compose.yml up -d --build api

