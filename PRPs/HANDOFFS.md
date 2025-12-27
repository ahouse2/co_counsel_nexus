
@2025/12/27 11:50:00 AM
Unified Pro Mode & Case Management Fixes
- Removed community/pro mode distinction in `pipeline.py` - everything now runs as "pro" mode
- Always write documents to Neo4j knowledge graph during ingestion (removed conditional)
- Always use LLM-based classification for all documents
- Added Create Case modal to `DashboardModule.tsx`:
  - Opens on "New Case" button click
  - Form with case name and description fields
  - Auto-generates case number (CC-YYYY-NNN format)
  - Navigates to Documents module after creation
- Fixed `user_role_association` table UUID type mismatch in `backend/app/models/user_role.py`
- Added `env_file: .env` directive to `docker-compose.yml` api service for proper env loading
- Fixed indentation issues in `pipeline.py` after removing mode conditionals
- Pushed all changes to GitHub main branch
- .env audit: All key variables (GEMINI_API_KEY, NEO4J_*, POSTGRES_*, QDRANT_URL, INGESTION_COST_MODE) are properly loaded via pydantic-settings in `config.py`

