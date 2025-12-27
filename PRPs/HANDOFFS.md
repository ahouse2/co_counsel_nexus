
@2025/12/27 12:15:00 PM
Case Management & Pro Mode Unification
- Unified pipeline to pro mode - removed all community/pro conditionals
- Always write to Neo4j knowledge graph during ingestion
- Always use LLM-based classification for all documents
- Added Create Case modal to `DashboardModule.tsx` (opens on "New Case" click)
- Made CaseSelector prominent with amber animated border/glow when no case selected
- Updated `ChatModule.tsx` to use caseId from `useHalo()` for context-aware chat
- Updated `AssetHunterModule.tsx` to use caseId from `useHalo()` for asset scans
- Updated `api.ts` chat endpoint to accept caseId parameter
- Fixed `user_role_association` table UUID type mismatch
- Added `env_file: .env` directive to `docker-compose.yml` for proper env loading
- Pushed all changes to GitHub main branch

