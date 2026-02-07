# Environment Configuration

## Environment Variables

Create `.env` file:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/fpa_db
DATABASE_POOL_SIZE=20

# AWS
AWS_REGION=us-east-1
S3_AUDIT_BUCKET=nuvini-fpa-audit-logs
AWS_KMS_KEY_ID=alias/fpa-master-key

# Claude API
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Redis/Celery
REDIS_URL=redis://localhost:6379/0

# Security
ENCRYPTION_KEY_ID=alias/fpa-master-key
JWT_SECRET_KEY=<generate-secure-key>

# Environment
ENVIRONMENT=production
DEBUG=false
