# Troubleshooting Guide

Common issues and solutions for the Co-Counsel application.

---

## Quick Diagnostics

### Check System Health
```bash
# Check all services
docker-compose ps

# Check API health
curl http://localhost:8001/health

# Check frontend
curl http://localhost:8088
```

---

## Common Issues

### 1. Application Won't Start

**Symptoms**: Docker containers fail to start or crash immediately

**Solutions**:

1. **Check Docker is running**
   ```bash
   docker --version
   docker-compose --version
   ```

2. **Check for port conflicts**
   ```bash
   # Windows
   netstat -ano | findstr :8001
   netstat -ano | findstr :8088
   
   # Kill conflicting process
   taskkill /PID <process_id> /F
   ```

3. **Check environment variables**
   ```bash
   # Verify .env exists
   ls .env
   
   # Check for required variables
   grep GEMINI_API_KEY .env
   grep SECRET_KEY .env
   ```

4. **Review logs**
   ```bash
   docker-compose logs api
   docker-compose logs frontend
   ```

---

### 2. Database Connection Errors

**Symptoms**: "Connection refused" or "Authentication failed"

**Solutions**:

1. **Verify database containers are running**
   ```bash
   docker-compose ps neo4j postgres qdrant
   ```

2. **Check passwords match**
   - Compare `.env` with `docker-compose.yml`
   - Ensure `NEO4J_PASSWORD` and `POSTGRES_PASSWORD` are consistent

3. **Restart database containers**
   ```bash
   docker-compose restart neo4j postgres
   ```

4. **Check database logs**
   ```bash
   docker-compose logs neo4j
   docker-compose logs postgres
   ```

---

### 3. API Key Errors

**Symptoms**: "Invalid API key" or "Unauthorized"

**Solutions**:

1. **Verify API key is set**
   ```bash
   grep GEMINI_API_KEY .env
   ```

2. **Check for whitespace**
   ```bash
   # Should have no spaces around =
   GEMINI_API_KEY=your_key_here
   ```

3. **Validate key with provider**
   - Gemini: https://aistudio.google.com/app/apikey
   - OpenAI: https://platform.openai.com/api-keys

4. **Check API quota**
   - Review usage limits
   - Verify billing is active

---

### 4. Out of Memory Errors

**Symptoms**: Containers crash with OOM errors

**Solutions**:

1. **Increase Docker memory limit**
   - Docker Desktop → Settings → Resources
   - Increase to at least 8GB

2. **Check resource usage**
   ```bash
   docker stats
   ```

3. **Reduce concurrent requests**
   - Lower rate limits in `main.py`
   - Reduce batch sizes

4. **Clear cache**
   ```bash
   docker system prune -a
   ```

---

### 5. Slow Performance

**Symptoms**: Requests take too long, timeouts

**Solutions**:

1. **Check system resources**
   ```bash
   docker stats
   ```

2. **Review database indexes**
   ```cypher
   // Neo4j - Check indexes
   SHOW INDEXES
   ```

3. **Enable caching**
   - Verify Redis is configured
   - Check cache hit rates

4. **Optimize queries**
   - Review slow query logs
   - Add database indexes

---

### 6. Frontend Not Loading

**Symptoms**: Blank page or 404 errors

**Solutions**:

1. **Check frontend container**
   ```bash
   docker-compose logs frontend
   ```

2. **Verify API is accessible**
   ```bash
   curl http://localhost:8001/health
   ```

3. **Check CORS configuration**
   - Review `main.py` CORS settings
   - Ensure frontend URL is allowed

4. **Clear browser cache**
   - Hard refresh: Ctrl+Shift+R
   - Clear cookies and cache

---

### 7. File Upload Failures

**Symptoms**: "Request entity too large" or upload hangs

**Solutions**:

1. **Check file size limit**
   - Current limit: 10MB (configurable in `main.py`)
   - Increase if needed for large documents

2. **Verify storage space**
   ```bash
   df -h
   ```

3. **Check permissions**
   ```bash
   ls -la storage/
   ```

4. **Review upload logs**
   ```bash
   docker-compose logs api | grep upload
   ```

---

### 8. Voice Services Not Working

**Symptoms**: STT/TTS errors or no audio

**Solutions**:

1. **Check voice service containers**
   ```bash
   docker-compose ps stt tts
   ```

2. **Verify GPU availability** (if using)
   ```bash
   nvidia-smi
   ```

3. **Check model downloads**
   ```bash
   docker-compose logs stt
   docker-compose logs tts
   ```

4. **Test services directly**
   ```bash
   curl http://localhost:9000/health
   curl http://localhost:5002/health
   ```

---

## Advanced Troubleshooting

### Enable Debug Logging

Add to `.env`:
```bash
LOG_LEVEL=DEBUG
```

Restart services:
```bash
docker-compose restart
```

### Database Debugging

**Neo4j**:
```bash
# Access Neo4j browser
open http://localhost:7474

# Run diagnostic query
MATCH (n) RETURN count(n)
```

**PostgreSQL**:
```bash
# Connect to database
docker-compose exec postgres psql -U cocounsel

# Check tables
\dt

# Check connections
SELECT * FROM pg_stat_activity;
```

### Network Debugging

```bash
# Check container network
docker network inspect op_veritas_2_backend

# Test inter-container connectivity
docker-compose exec api ping neo4j
docker-compose exec api ping qdrant
```

---

## Getting Help

If issues persist:

1. **Collect diagnostics**
   ```bash
   docker-compose logs > logs.txt
   docker-compose ps > services.txt
   ```

2. **Check GitHub Issues**
   - Search existing issues
   - Create new issue with logs

3. **Review documentation**
   - README.md
   - DEPLOYMENT.md
   - ENVIRONMENT_VARIABLES.md

4. **Contact support**
   - Include error messages
   - Attach diagnostic files
   - Describe steps to reproduce

---

## Prevention

### Regular Maintenance

1. **Update dependencies monthly**
   ```bash
   pip list --outdated
   npm outdated
   ```

2. **Monitor disk space**
   ```bash
   df -h
   docker system df
   ```

3. **Review logs weekly**
   ```bash
   docker-compose logs --tail=100
   ```

4. **Test backups monthly**
   ```bash
   # Verify backup exists
   ls -lh var/backups/
   ```

### Health Monitoring

Set up monitoring for:
- API response times
- Database connections
- Disk usage
- Memory usage
- Error rates

---

## Emergency Procedures

### Complete Reset

⚠️ **Warning**: This will delete all data!

```bash
# Stop all services
docker-compose down

# Remove volumes
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Start fresh
docker-compose up -d
```

### Rollback Deployment

```bash
# Stop current version
docker-compose down

# Checkout previous version
git checkout <previous-commit>

# Rebuild and start
docker-compose up -d --build
```
