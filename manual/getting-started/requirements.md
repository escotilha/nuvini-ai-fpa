# System Requirements

## Hardware Requirements

### Minimum Requirements

| Component | Specification |
|-----------|--------------|
| **CPU** | 4 cores @ 2.5 GHz |
| **RAM** | 8 GB |
| **Storage** | 100 GB SSD |
| **Network** | 10 Mbps download, 5 Mbps upload |

### Recommended Requirements

| Component | Specification |
|-----------|--------------|
| **CPU** | 8+ cores @ 3.0 GHz |
| **RAM** | 16 GB (32 GB for production) |
| **Storage** | 500 GB NVMe SSD |
| **Network** | 100 Mbps download, 20 Mbps upload |

### Production Environment (AWS)

For production deployment on AWS:

| Service | Specification |
|---------|--------------|
| **Database** | RDS PostgreSQL 15+ (db.r6g.xlarge or larger) |
| **Application Server** | ECS Fargate (2 vCPU, 4 GB RAM minimum) |
| **Task Queue** | ElastiCache Redis (cache.t3.medium) |
| **Storage** | S3 Standard for reports, Glacier for archival |

## Software Requirements

### Operating System

The system supports the following operating systems:

- **Linux**: Ubuntu 22.04+ / Debian 11+ / RHEL 8+
- **macOS**: macOS 12 (Monterey) or later
- **Windows**: Windows 11 with WSL2

**Recommended**: Ubuntu 22.04 LTS for production deployments.

### Python

- **Required Version**: Python 3.13 or later
- **Package Manager**: pip 24.0+ or uv (recommended)
- **Virtual Environment**: venv or conda

To check your Python version:

```bash
python3 --version
# Expected output: Python 3.13.x or later
```

### PostgreSQL Database

- **Required Version**: PostgreSQL 15 or later
- **Required Extensions**:
  - `uuid-ossp` - UUID generation
  - `btree_gist` - Advanced indexing
  - `pg_trgm` - Fuzzy text search
- **Minimum Disk Space**: 100 GB (500 GB recommended for production)
- **Memory**: 4 GB shared_buffers (8 GB recommended)

To check your PostgreSQL version:

```bash
psql --version
# Expected output: psql (PostgreSQL) 15.x or later
```

### Redis

- **Required Version**: Redis 7.0 or later
- **Memory**: 1 GB minimum (4 GB recommended)
- **Persistence**: RDB snapshots enabled

To check your Redis version:

```bash
redis-server --version
# Expected output: Redis server v=7.x or later
```

## Cloud Services

### AWS Services (Production)

Required AWS services for production deployment:

| Service | Purpose | Estimated Cost |
|---------|---------|---------------|
| **RDS PostgreSQL** | Primary database | $200-500/month |
| **ElastiCache Redis** | Task queue backend | $50-100/month |
| **ECS Fargate** | Application containers | $100-300/month |
| **S3** | Report storage | $20-50/month |
| **Secrets Manager** | Credential storage | $10-20/month |
| **CloudWatch** | Monitoring & logging | $30-80/month |
| **Lambda** | Scheduled triggers | $5-15/month |

**Total Estimated Cost**: $415-1,065/month for 7 entities

### AWS Permissions

The IAM user or role requires these permissions:

- `rds:*` - Database management
- `elasticache:*` - Redis management
- `ecs:*` - Container orchestration
- `s3:*` - Object storage
- `secretsmanager:*` - Secrets access
- `cloudwatch:*` - Monitoring
- `lambda:*` - Function execution
- `logs:*` - CloudWatch Logs

### Anthropic API

- **API Key**: Required for Claude AI features
- **Model Access**: Claude Sonnet 4.5 or Opus 4.6
- **Estimated Usage**: 500K-1M tokens/month ($2.50-$5.00 for Sonnet 4.5)
- **Rate Limits**: Standard tier (1000 requests/minute)

To obtain an API key: https://console.anthropic.com/

## External API Access

### ERP Systems

The system requires API access to the following ERP systems:

#### TOTVS Protheus

- **Authentication**: OAuth 2.0 or Bearer Token
- **Base URL**: `https://api.totvs.com.br`
- **Required Permissions**: Read access to:
  - Trial balance (`GET /api/fin/v1/trial-balance`)
  - Chart of accounts (`GET /api/fin/v1/accounts`)
  - Subledger details (`GET /api/fin/v1/transactions`)
- **Rate Limit**: 100 requests/minute
- **Documentation**: https://tdn.totvs.com/display/public/PROT/REST

#### ContaAzul

- **Authentication**: OAuth 2.0
- **Base URL**: `https://api.contaazul.com`
- **Required Permissions**: Read access to:
  - Financial transactions (`GET /v1/financial_accounts/transactions`)
  - Chart of accounts (`GET /v1/financial_accounts`)
- **Rate Limit**: 60 requests/minute
- **Documentation**: https://developers.contaazul.com/

#### Omie

- **Authentication**: API Key (app_key + app_secret)
- **Base URL**: `https://app.omie.com.br/api/v1`
- **Required Permissions**: Read access to:
  - Trial balance (`POST /financas/contacorrente/`)
  - Chart of accounts (`POST /geral/planocontas/`)
- **Rate Limit**: 300 requests/minute
- **Documentation**: https://developer.omie.com.br/

#### Bling

- **Authentication**: API Key or OAuth 2.0
- **Base URL**: `https://api.bling.com.br/Api/v3`
- **Required Permissions**: Read access to:
  - Financial accounts (`GET /financas/contas`)
  - Transactions (`GET /financas/movimentos`)
- **Rate Limit**: 100 requests/minute
- **API Version**: v3 (JSON) recommended
- **Documentation**: https://manualdoapi.bling.com.br/

### Foreign Exchange Rates

#### Brazilian Central Bank (BCB)

- **API**: BCB PTAX API
- **Base URL**: `https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1`
- **Authentication**: None (public API)
- **Purpose**: BRL/USD exchange rates
- **Rate Limit**: None specified
- **Documentation**: https://dadosabertos.bcb.gov.br/

#### European Central Bank (ECB)

- **API**: ECB Statistical Data Warehouse
- **Base URL**: `https://data-api.ecb.europa.eu/service/data/`
- **Authentication**: None (public API)
- **Purpose**: EUR/USD exchange rates
- **Rate Limit**: None specified
- **Documentation**: https://data.ecb.europa.eu/help/api

## Network Requirements

### Firewall Rules

#### Outbound (Application to External Services)

| Destination | Port | Protocol | Purpose |
|-------------|------|----------|---------|
| ERP APIs | 443 | HTTPS | Data extraction |
| BCB API | 443 | HTTPS | FX rates |
| Anthropic API | 443 | HTTPS | AI analysis |
| AWS Services | 443 | HTTPS | Cloud resources |

#### Inbound (for API access)

| Source | Port | Protocol | Purpose |
|--------|------|----------|---------|
| Internal network | 8000 | HTTP | FastAPI application |
| Internal network | 5432 | TCP | PostgreSQL (if not RDS) |
| Internal network | 6379 | TCP | Redis (if not ElastiCache) |

### DNS Requirements

Ensure DNS resolution for:

- `api.totvs.com.br`
- `api.contaazul.com`
- `app.omie.com.br`
- `api.bling.com.br`
- `olinda.bcb.gov.br`
- `data-api.ecb.europa.eu`
- `api.anthropic.com`
- AWS service endpoints (if using AWS)

### SSL/TLS Certificates

- **Internal API**: Self-signed certificate acceptable for development
- **Production API**: Valid SSL certificate required (Let's Encrypt or commercial)
- **ERP connections**: All ERP APIs use TLS 1.2 or higher

## Dependencies

### Python Packages

Core dependencies (automatically installed via `requirements.txt`):

| Package | Version | Purpose |
|---------|---------|---------|
| **fastapi** | 0.110+ | Web API framework |
| **sqlalchemy** | 2.0+ | Database ORM |
| **asyncpg** | 0.29+ | Async PostgreSQL driver |
| **httpx** | 0.27+ | Async HTTP client |
| **pydantic** | 2.6+ | Data validation |
| **celery** | 5.3+ | Task queue |
| **redis** | 5.0+ | Redis client |
| **anthropic** | 0.18+ | Claude AI SDK |
| **openpyxl** | 3.1+ | Excel generation |
| **python-pptx** | 0.6+ | PowerPoint generation |
| **pandas** | 2.2+ | Data manipulation |
| **pytest** | 8.0+ | Testing framework |

Full list available in `/Volumes/AI/Code/FPA/requirements.txt`

### PostgreSQL Extensions

Required extensions (installed automatically):

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- UUID generation
CREATE EXTENSION IF NOT EXISTS "btree_gist";     -- Advanced indexing
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- Fuzzy text search
```

## Development Tools (Optional)

### Recommended IDE

- **VS Code** with Python extension
- **PyCharm Professional** (paid) or Community (free)
- **Cursor** (AI-powered IDE)

### Code Quality Tools

- **black** - Code formatting
- **flake8** - Linting
- **mypy** - Type checking
- **isort** - Import sorting

### Database Tools

- **pgAdmin 4** - PostgreSQL GUI
- **DBeaver** - Universal database tool
- **psql** - Command-line client

### API Testing

- **Postman** - API testing
- **httpie** - Command-line HTTP client
- **curl** - Basic HTTP testing

## User Requirements

### Technical Skills

**Minimum skills for installation:**

- Basic command-line experience (cd, ls, mkdir)
- Python virtual environment creation
- PostgreSQL database creation
- Environment variable configuration

**Recommended skills for operation:**

- SQL query writing
- Database backup/restore
- AWS service configuration
- Docker/container basics

### Access Credentials

**Required before installation:**

1. **ERP Credentials**: API keys/OAuth credentials for all 7 ERP systems
2. **AWS Credentials**: IAM user with required permissions
3. **Anthropic API Key**: Claude API access key
4. **Database Credentials**: PostgreSQL superuser password
5. **Email Credentials**: SMTP server for report distribution (optional)

### Licensing

**Required licenses:**

- **PostgreSQL**: Free (open-source)
- **Python**: Free (open-source)
- **Anthropic API**: Pay-per-use (estimate $2.50-$5.00/month)

**ERP Licenses**: Existing subscriptions (no additional cost)

## Pre-Installation Checklist

Before proceeding to installation, verify:

- [ ] Python 3.13+ installed and accessible
- [ ] PostgreSQL 15+ installed and running
- [ ] Redis 7.0+ installed and running
- [ ] 100+ GB free disk space
- [ ] API credentials for all 7 ERP systems
- [ ] AWS account with required permissions (for production)
- [ ] Anthropic API key
- [ ] Network access to all required external APIs
- [ ] Firewall rules configured for outbound HTTPS
- [ ] SSL certificate for production deployment (if applicable)

## Scaling Considerations

### Current Capacity (7 Entities)

- **Database Size**: ~2 GB (current year)
- **Processing Time**: <5 seconds per consolidation
- **Monthly Storage Growth**: ~300 MB
- **API Rate Limits**: Well within all provider limits

### Future Capacity (66 Entities)

- **Database Size**: ~20 GB (7 years of data)
- **Processing Time**: <60 seconds per consolidation
- **Monthly Storage Growth**: ~2.5 GB
- **Hardware**: Increase RAM to 32 GB, CPU to 16 cores
- **Database**: Consider read replicas, partitioning by entity

### Vertical Scaling Limits

The system can handle 66 entities on a single server with:

- **32 GB RAM**
- **16 CPU cores**
- **1 TB NVMe SSD**

Beyond 100 entities, consider horizontal scaling with Citus (distributed PostgreSQL).

## Support

For questions about requirements:

- **Hardware/Software**: Review [Installation Guide](installation.md)
- **AWS Setup**: See [Deployment Guide](../deployment/aws.md)
- **ERP Access**: Contact portfolio company IT teams

---

**Next Step**: Once requirements are verified, proceed to [Installation](installation.md).
