# Security Best Practices

Security guidelines and best practices for the Co-Counsel application.

---

## Overview

Co-Counsel handles sensitive legal data and must maintain the highest security standards. This document outlines security best practices for deployment, operation, and development.

---

## Authentication & Authorization

### API Keys
- **Never commit API keys** to version control
- **Rotate keys every 90 days** minimum
- **Use separate keys** for dev/staging/production
- **Monitor API usage** for anomalies
- **Revoke immediately** if compromised

### Passwords
- **Minimum 16 characters** for all passwords
- **Use password manager** for generation and storage
- **Change default passwords** immediately
- **Never reuse passwords** across services
- **Rotate passwords quarterly**

### JWT Tokens
- **Short expiration** (15 minutes for access tokens)
- **Secure refresh tokens** (httpOnly cookies)
- **Validate signatures** on every request
- **Revoke on logout** and suspicious activity

---

## Data Protection

### Encryption

**At Rest**:
- Database encryption enabled
- Encrypted file storage
- Encrypted backups

**In Transit**:
- HTTPS/TLS 1.3 only
- Certificate pinning for APIs
- Secure WebSocket connections

### Sensitive Data Handling
- **PII encryption** before storage
- **Audit logging** for access
- **Data minimization** - collect only what's needed
- **Secure deletion** when no longer needed
- **Access controls** - principle of least privilege

---

## Network Security

### Firewall Rules
```bash
# Allow only necessary ports
- 8001 (API) - internal only
- 8088 (Frontend) - public
- 7474, 7687 (Neo4j) - internal only
- 6333 (Qdrant) - internal only
- 5432 (PostgreSQL) - internal only
```

### Rate Limiting
- **100 requests/minute** per IP
- **1000 requests/hour** per IP
- **Exponential backoff** for repeated violations
- **IP blocking** for severe abuse

### DDoS Protection
- Use CDN (Cloudflare, AWS CloudFront)
- Enable rate limiting
- Monitor traffic patterns
- Have incident response plan

---

## Application Security

### Input Validation
- **Validate all inputs** on server side
- **Sanitize user data** before processing
- **Reject malformed requests** immediately
- **Use parameterized queries** for databases
- **Escape output** to prevent XSS

### Security Headers
```python
# Already implemented in main.py
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000
Referrer-Policy: strict-origin-when-cross-origin
```

### Request Size Limits
- **10MB maximum** request body
- **Configurable** per endpoint
- **Reject large requests** early
- **Monitor** for abuse patterns

---

## Secrets Management

### Environment Variables
- **Never commit .env** to git
- **Use .env.example** for templates
- **Validate required vars** on startup
- **Fail fast** if secrets missing

### Production Secrets
Consider using:
- **HashiCorp Vault**
- **AWS Secrets Manager**
- **Azure Key Vault**
- **Google Secret Manager**

### Secret Rotation
```bash
# Quarterly rotation schedule
Q1: January 1
Q2: April 1
Q3: July 1
Q4: October 1
```

---

## Monitoring & Auditing

### Audit Logging
Log all:
- Authentication attempts (success/failure)
- Authorization decisions
- Data access (especially PII)
- Configuration changes
- Administrative actions

### Security Monitoring
- **Failed login attempts** (>5 in 10 minutes)
- **Unusual API usage** patterns
- **Large data exports**
- **Configuration changes**
- **New user accounts**

### Incident Response
1. **Detect** - Automated alerts
2. **Contain** - Isolate affected systems
3. **Investigate** - Root cause analysis
4. **Remediate** - Fix vulnerabilities
5. **Document** - Post-mortem report

---

## Dependency Security

### Regular Updates
```bash
# Check for vulnerabilities weekly
pip list --outdated
npm audit

# Update dependencies monthly
pip install --upgrade -r requirements.txt
npm update
```

### Vulnerability Scanning
```bash
# Scan Docker images
docker scan co-counsel-api:latest

# Scan Python dependencies
safety check

# Scan npm dependencies
npm audit
```

---

## Compliance

### GDPR
- **Data minimization**
- **Right to erasure**
- **Data portability**
- **Consent management**
- **Privacy by design**

### HIPAA (if applicable)
- **Encryption** at rest and in transit
- **Access controls** and audit logs
- **Business associate agreements**
- **Breach notification** procedures

### SOC 2
- **Security policies** documented
- **Access controls** implemented
- **Change management** process
- **Incident response** plan
- **Regular audits**

---

## Development Security

### Code Review
- **Security review** for all changes
- **No hardcoded secrets**
- **Input validation** checked
- **Error handling** reviewed
- **Dependencies** verified

### Testing
- **Security tests** in CI/CD
- **Penetration testing** quarterly
- **Vulnerability scanning** automated
- **Code analysis** (SAST/DAST)

### Git Security
```bash
# Pre-commit hooks
- Detect secrets
- Check for large files
- Validate commit messages
- Run linters

# Branch protection
- Require reviews
- Require status checks
- No force pushes
- Signed commits
```

---

## Backup Security

### Backup Encryption
- **Encrypt all backups**
- **Separate encryption keys**
- **Test restoration** monthly
- **Offsite storage**

### Backup Access
- **Restricted access** to backups
- **Audit all access**
- **MFA required**
- **Time-limited access**

---

## Incident Response Plan

### Preparation
- [ ] Incident response team identified
- [ ] Contact list maintained
- [ ] Runbooks documented
- [ ] Tools and access ready

### Detection
- [ ] Monitoring alerts configured
- [ ] Log aggregation enabled
- [ ] Anomaly detection active
- [ ] User reporting channel

### Response
1. **Assess severity** (Critical/High/Medium/Low)
2. **Contain threat** (isolate, block, disable)
3. **Investigate** (logs, forensics, timeline)
4. **Remediate** (patch, update, reconfigure)
5. **Recover** (restore, verify, monitor)
6. **Document** (timeline, actions, lessons)

### Communication
- **Internal**: Incident response team
- **External**: Affected users (if data breach)
- **Regulatory**: As required by law
- **Public**: If appropriate

---

## Security Checklist

### Daily
- [ ] Review security alerts
- [ ] Check failed login attempts
- [ ] Monitor API usage
- [ ] Review error logs

### Weekly
- [ ] Scan for vulnerabilities
- [ ] Review access logs
- [ ] Check backup status
- [ ] Update threat intelligence

### Monthly
- [ ] Update dependencies
- [ ] Review user access
- [ ] Test incident response
- [ ] Security training

### Quarterly
- [ ] Rotate API keys
- [ ] Rotate passwords
- [ ] Penetration testing
- [ ] Security audit
- [ ] Review policies

---

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

---

## Contact

**Security Team**: security@yourcompany.com  
**Bug Bounty**: bugbounty@yourcompany.com  
**Emergency**: +1-XXX-XXX-XXXX (24/7)
