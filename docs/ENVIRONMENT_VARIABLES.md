# Environment Variables Reference

This document provides a comprehensive reference for all environment variables used in the Co-Counsel application.

---

## Quick Start

1. Copy `.env.example` to `.env`
2. Fill in required API keys
3. Customize optional settings as needed
4. Never commit `.env` to version control

---

## Required Variables

### LLM Provider Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | ✅ Yes | - | Google Gemini API key for AI models |
| `GEMINI_API_KEY_1` | ❌ No | - | Backup Gemini API key |
| `GOOGLE_API_KEY` | ❌ No | `${GEMINI_API_KEY}` | Alternative Google API key |
| `OPENAI_API_KEY` | ❌ No | - | OpenAI API key (if using OpenAI) |

**How to get**: Visit [Google AI Studio](https://aistudio.google.com/app/apikey) or [OpenAI Platform](https://platform.openai.com/api-keys)

### Security

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | ✅ Yes | - | Secret key for JWT tokens and encryption |

**How to generate**: `openssl rand -hex 32`

### Database Passwords

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEO4J_PASSWORD` | ⚠️ Recommended | `change_this_strong_password_123!` | Neo4j database password |
| `POSTGRES_PASSWORD` | ⚠️ Recommended | `change_this_strong_pg_password_456!` | PostgreSQL database password |

**Security Note**: Change these before production deployment!

---

## Optional Variables

### Model Selection

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `GEMINI` | Primary LLM provider (`GEMINI` or `OPENAI`) |
| `MODEL_PROVIDERS_PRIMARY` | `gemini` | Primary model provider |
| `MODEL_PROVIDERS_SECONDARY` | `openai` | Fallback model provider |
| `DEFAULT_CHAT_MODEL` | `gemini-2.5-flash` | Default chat model |
| `DEFAULT_EMBEDDING_MODEL` | `text-embedding-004` | Default embedding model |
| `DEFAULT_VISION_MODEL` | `gemini-2.5-flash` | Default vision model |

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_URI` | `neo4j://neo4j:7687` | Neo4j connection URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `QDRANT_URL` | `http://qdrant:6333` | Qdrant vector database URL |
| `POSTGRES_DB` | `cocounsel` | PostgreSQL database name |
| `POSTGRES_USER` | `cocounsel` | PostgreSQL username |

### Storage Paths

| Variable | Default | Description |
|----------|---------|-------------|
| `VECTOR_DIR` | `./storage/vector` | Vector embeddings storage |
| `DOCUMENT_STORAGE_PATH` | `/var/cocounsel/documents` | Document storage path |
| `GRAPH_SNAPSHOT_PATH` | `/var/cocounsel/graphs` | Graph snapshots path |
| `TELEMETRY_BUFFER_PATH` | `/var/cocounsel/telemetry` | Telemetry data path |
| `VOICE_SESSIONS_DIR` | `/data/voice/sessions` | Voice session recordings |
| `VOICE_CACHE_DIR` | `/models` | Voice model cache |

### Telemetry & Monitoring

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEMETRY_ENABLED` | `false` | Enable OpenTelemetry |
| `TELEMETRY_OTLP_ENDPOINT` | `http://otel-collector:4317` | OTLP collector endpoint |
| `TELEMETRY_ENVIRONMENT` | `development` | Environment name for telemetry |

### Voice Services

| Variable | Default | Description |
|----------|---------|-------------|
| `STT_SERVICE_URL` | `http://stt:9000` | Speech-to-text service URL |
| `TTS_SERVICE_URL` | `http://tts:5002` | Text-to-speech service URL |
| `STT_MODEL_NAME` | `openai/whisper-small` | Whisper model for STT |
| `STT_DEVICE` | `cpu` | Device for STT (`cpu` or `cuda`) |
| `TTS_VOICE` | `en-us-blizzard_lessac` | TTS voice model |

### External APIs

| Variable | Required | Description |
|----------|----------|-------------|
| `COURTLISTENER_API_KEY` | ❌ No | CourtListener API key for case law research |

**How to get**: Visit [CourtListener API](https://www.courtlistener.com/api/)

### GPU Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GPU_DEVICE_COUNT` | `0` | Number of GPUs to use (0 for CPU-only) |

### Backup Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKUP_CRON_SCHEDULE` | `0 3 * * *` | Cron schedule for backups (3 AM daily) |
| `BACKUP_RETENTION_DAYS` | `7` | Days to retain backups |

---

## Environment-Specific Configurations

### Development

```bash
TELEMETRY_ENABLED=false
TELEMETRY_ENVIRONMENT=development
GPU_DEVICE_COUNT=0
```

### Production

```bash
TELEMETRY_ENABLED=true
TELEMETRY_ENVIRONMENT=production
GPU_DEVICE_COUNT=1
BACKUP_CRON_SCHEDULE=0 2 * * *
```

---

## Security Best Practices

1. **Never commit `.env` to version control**
2. **Use strong, unique passwords** for all database credentials
3. **Rotate API keys regularly** (every 90 days recommended)
4. **Use environment-specific keys** (separate dev/staging/prod keys)
5. **Limit API key permissions** to only what's needed
6. **Monitor API usage** for unusual activity

---

## Troubleshooting

### "API key not found" errors
- Verify the key is set in `.env`
- Check for typos in variable names
- Ensure no extra spaces around `=`
- Restart the application after changes

### Database connection failures
- Verify database passwords match between `.env` and `docker-compose.yml`
- Check database containers are running: `docker-compose ps`
- Review logs: `docker-compose logs neo4j` or `docker-compose logs postgres`

### Model loading errors
- Verify API keys are valid
- Check model names are correct
- Ensure sufficient disk space for model cache
- Review API quota limits

---

## Migration Guide

### From Previous Versions

If upgrading from an older version:

1. Compare your `.env` with `.env.example`
2. Add any new required variables
3. Update deprecated variable names
4. Test in development before production

### Changing Providers

To switch from Gemini to OpenAI:

```bash
LLM_PROVIDER=OPENAI
MODEL_PROVIDERS_PRIMARY=openai
OPENAI_API_KEY=your_openai_key_here
```

---

## Additional Resources

- [Google AI Studio](https://aistudio.google.com/)
- [OpenAI Platform](https://platform.openai.com/)
- [Neo4j Documentation](https://neo4j.com/docs/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
