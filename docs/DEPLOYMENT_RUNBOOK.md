# Deployment Runbook

Step-by-step procedures for deploying and operating the Co-Counsel application.

---

## Pre-Deployment Checklist

### Security
- [ ] All API keys rotated and secured
- [ ] `.env` file not in version control
- [ ] Database passwords changed from defaults
- [ ] HTTPS/TLS certificates configured
- [ ] Security headers enabled
- [ ] Rate limiting configured

### Configuration
- [ ] Environment variables documented
- [ ] Database connection strings verified
- [ ] Storage paths configured
- [ ] Backup schedule set
- [ ] Monitoring enabled

### Testing
- [ ] All health checks passing
- [ ] Integration tests passed
- [ ] Load testing completed
- [ ] Backup/restore tested
- [ ] Rollback procedure tested

---

## Deployment Procedures

### Initial Deployment

**1. Prepare Environment**
```bash
# Clone repository
git clone https://github.com/your-org/co-counsel.git
cd co-counsel

# Create .env from template
cp .env.example .env

# Edit .env with production values
nano .env
```

**2. Configure Secrets**
```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Set database passwords
# Update NEO4J_PASSWORD
# Update POSTGRES_PASSWORD
```

**3. Build Images**
```bash
# Build all services
docker-compose build

# Verify images
docker images | grep co-counsel
```

**4. Start Services**
```bash
# Start in detached mode
docker-compose up -d

# Check status
docker-compose ps

# Verify health
curl http://localhost:8001/health
curl http://localhost:8001/health/ready
```

**5. Initialize Database**
```bash
# Database migrations run automatically on startup
# Verify with:
docker-compose logs api | grep migration
```

**6. Verify Deployment**
```bash
# Check all services healthy
docker-compose ps

# Test API
curl http://localhost:8001/health/ready

# Test frontend
curl http://localhost:8088

# Check logs for errors
docker-compose logs --tail=50
```

---

### Update Deployment

**1. Backup Current State**
```bash
# Backup databases
docker-compose exec neo4j neo4j-admin dump --to=/backups/neo4j-$(date +%Y%m%d).dump
docker-compose exec postgres pg_dump -U cocounsel > backup-$(date +%Y%m%d).sql

# Backup volumes
docker run --rm -v op_veritas_2_storage_documents:/data -v $(pwd)/backups:/backup alpine tar czf /backup/documents-$(date +%Y%m%d).tar.gz /data
```

**2. Pull Latest Changes**
```bash
# Fetch updates
git fetch origin

# Review changes
git log HEAD..origin/main

# Pull updates
git pull origin main
```

**3. Update Dependencies**
```bash
# Rebuild images
docker-compose build

# Pull new base images
docker-compose pull
```

**4. Rolling Update**
```bash
# Update one service at a time
docker-compose up -d --no-deps --build api
docker-compose up -d --no-deps --build frontend

# Verify each service
curl http://localhost:8001/health
```

**5. Verify Update**
```bash
# Check all services
docker-compose ps

# Review logs
docker-compose logs --tail=100

# Test critical endpoints
curl http://localhost:8001/health/ready
```

---

### Rollback Procedure

**1. Identify Issue**
```bash
# Check service status
docker-compose ps

# Review recent logs
docker-compose logs --tail=200

# Check error rates
curl http://localhost:8001/health/ready
```

**2. Stop Current Version**
```bash
# Stop all services
docker-compose down
```

**3. Revert Code**
```bash
# Find previous working commit
git log --oneline -10

# Checkout previous version
git checkout <commit-hash>
```

**4. Restore Backup (if needed)**
```bash
# Restore Neo4j
docker-compose exec neo4j neo4j-admin load --from=/backups/neo4j-YYYYMMDD.dump

# Restore PostgreSQL
docker-compose exec -T postgres psql -U cocounsel < backup-YYYYMMDD.sql
```

**5. Restart Services**
```bash
# Rebuild and start
docker-compose up -d --build

# Verify health
curl http://localhost:8001/health/ready
```

---

## Operational Procedures

### Daily Operations

**Morning Checks**
```bash
# Check service health
docker-compose ps
curl http://localhost:8001/health/ready

# Review overnight logs
docker-compose logs --since 24h | grep ERROR

# Check disk space
df -h
docker system df
```

**Evening Checks**
```bash
# Verify backups ran
ls -lht var/backups/ | head -5

# Check resource usage
docker stats --no-stream

# Review error rates
docker-compose logs --since 12h | grep ERROR | wc -l
```

### Weekly Maintenance

**Every Monday**
```bash
# Update dependencies
pip list --outdated
npm outdated

# Review security advisories
docker scan co-counsel-api:latest

# Check certificate expiry
openssl s_client -connect localhost:443 -servername localhost 2>/dev/null | openssl x509 -noout -dates

# Clean up old images
docker image prune -a --filter "until=168h"
```

### Monthly Tasks

**First of Month**
```bash
# Rotate API keys (if policy requires)
# Update .env with new keys

# Review and archive old logs
tar czf logs-$(date +%Y%m).tar.gz var/logs/
mv logs-*.tar.gz var/archives/

# Test disaster recovery
# Perform full backup and restore test

# Update documentation
# Review and update runbooks
```

---

## Monitoring & Alerts

### Health Check Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `/health` | Basic liveness | `{"status": "healthy"}` |
| `/health/ready` | Readiness check | `{"status": "healthy", "resources": {...}}` |
| `/health/live` | Kubernetes liveness | `{"status": "alive"}` |

### Key Metrics to Monitor

**Application**
- Request rate (requests/second)
- Response time (p50, p95, p99)
- Error rate (%)
- Active connections

**Infrastructure**
- CPU usage (%)
- Memory usage (%)
- Disk usage (%)
- Network I/O

**Database**
- Connection pool usage
- Query latency
- Slow queries
- Replication lag

### Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| CPU Usage | >70% | >90% |
| Memory Usage | >75% | >90% |
| Disk Usage | >80% | >95% |
| Error Rate | >1% | >5% |
| Response Time | >1s | >3s |

---

## Backup & Recovery

### Automated Backups

Backups run daily at 3 AM (configurable via `BACKUP_CRON_SCHEDULE`).

**Backup Contents**:
- Neo4j database dump
- PostgreSQL database dump
- Document storage
- Graph snapshots
- Configuration files

**Retention**: 7 days (configurable via `BACKUP_RETENTION_DAYS`)

### Manual Backup

```bash
# Full backup
./scripts/backup.sh

# Backup specific service
docker-compose exec neo4j neo4j-admin dump --to=/backups/manual-$(date +%Y%m%d).dump
```

### Recovery Procedures

**Full System Recovery**:
1. Stop all services
2. Restore database dumps
3. Restore file volumes
4. Restart services
5. Verify health checks

**Partial Recovery**:
1. Identify affected component
2. Stop specific service
3. Restore component data
4. Restart service
5. Verify functionality

---

## Scaling Procedures

### Vertical Scaling

**Increase Resources**:
```yaml
# In docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '4'  # Increase from 2
      memory: 8G  # Increase from 4G
```

### Horizontal Scaling

**Add API Replicas**:
```bash
# Scale API service
docker-compose up -d --scale api=3

# Verify load balancing
for i in {1..10}; do curl http://localhost:8001/health; done
```

---

## Security Procedures

### Incident Response

**1. Detect**
- Monitor alerts
- Review logs
- Check anomalies

**2. Contain**
- Isolate affected services
- Block suspicious IPs
- Revoke compromised keys

**3. Investigate**
- Collect logs
- Analyze traffic
- Identify root cause

**4. Remediate**
- Patch vulnerabilities
- Update configurations
- Rotate credentials

**5. Document**
- Record timeline
- Document actions
- Update procedures

### Regular Security Tasks

**Weekly**:
- Review access logs
- Check for failed auth attempts
- Scan for vulnerabilities

**Monthly**:
- Rotate API keys
- Update dependencies
- Review permissions

---

## Emergency Contacts

| Role | Contact | Availability |
|------|---------|--------------|
| On-Call Engineer | [Phone/Email] | 24/7 |
| Database Admin | [Phone/Email] | Business hours |
| Security Team | [Phone/Email] | 24/7 |
| Management | [Phone/Email] | Business hours |

---

## Appendix

### Useful Commands

```bash
# View all logs
docker-compose logs -f

# Restart specific service
docker-compose restart api

# Execute command in container
docker-compose exec api bash

# View resource usage
docker stats

# Clean up system
docker system prune -a
```

### Configuration Files

- `.env` - Environment variables
- `docker-compose.yml` - Service definitions
- `backend/app/config.py` - Application configuration
- `docs/ENVIRONMENT_VARIABLES.md` - Variable reference
