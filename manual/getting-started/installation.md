# Installation Guide

This guide walks through installing the AI FP&A Monthly Close Automation system on your local machine or server.

## Prerequisites

Before starting, ensure you have completed the [System Requirements](requirements.md) checklist:

- ✅ Python 3.13+ installed
- ✅ PostgreSQL 15+ installed and running
- ✅ Redis 7.0+ installed and running
- ✅ API credentials for all ERP systems
- ✅ Anthropic API key

## Installation Methods

Choose the installation method that best fits your needs:

- **[Local Development](#local-development-installation)** - For development and testing
- **[Production Deployment](#production-deployment)** - For production on AWS

---

## Local Development Installation

### Step 1: Clone the Repository

```bash
# Clone the repository
git clone https://github.com/nuvini/ai-fpna.git
cd ai-fpna

# Verify you're in the correct directory
pwd
# Expected output: /path/to/ai-fpna
```

### Step 2: Create Python Virtual Environment

Using `venv` (built-in):

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On Linux/macOS:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate

# Verify activation
which python
# Expected output: /path/to/ai-fpna/.venv/bin/python
```

Using `uv` (recommended, faster):

```bash
# Install uv if not already installed
pip install uv

# Create virtual environment with uv
uv venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

### Step 3: Install Python Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep fastapi
# Expected output: fastapi 0.110.x or later
```

**Expected installation time**: 2-5 minutes (depending on network speed)

### Step 4: Set Up PostgreSQL Database

#### Create Database

```bash
# Connect to PostgreSQL as superuser
psql -U postgres

# Create database
CREATE DATABASE ai_fpna_db;

# Create application user
CREATE USER fpna_app WITH PASSWORD 'your_secure_password_here';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ai_fpna_db TO fpna_app;

# Exit psql
\q
```

#### Run Database Migrations

```bash
# Navigate to database directory
cd database

# Run migration scripts in order
psql -U fpna_app -d ai_fpna_db -f migrations/001_initial_schema.sql
psql -U fpna_app -d ai_fpna_db -f migrations/002_rls_policies.sql
psql -U fpna_app -d ai_fpna_db -f migrations/003_indexes.sql

# Verify tables were created
psql -U fpna_app -d ai_fpna_db -c "\dt"
# Expected output: List of tables (portfolio_entities, trial_balances, etc.)

# Return to project root
cd ..
```

#### Load Seed Data

```bash
# Load portfolio entities
psql -U fpna_app -d ai_fpna_db -f database/seeds/001_portfolio_entities.sql

# Load standard chart of accounts
psql -U fpna_app -d ai_fpna_db -f database/seeds/002_standard_coa.sql

# Verify seed data
psql -U fpna_app -d ai_fpna_db -c "SELECT entity_code, entity_name FROM portfolio_entities;"
# Expected output: 7 portfolio companies
```

### Step 5: Configure Redis

#### Start Redis Server

```bash
# On Linux/macOS with Homebrew
brew services start redis

# On Linux with systemd
sudo systemctl start redis

# On Windows (WSL2)
sudo service redis-server start

# Verify Redis is running
redis-cli ping
# Expected output: PONG
```

#### Test Redis Connection

```bash
# Connect to Redis
redis-cli

# Set test key
SET test_key "Hello FP&A"

# Get test key
GET test_key
# Expected output: "Hello FP&A"

# Delete test key
DEL test_key

# Exit Redis CLI
EXIT
```

### Step 6: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Copy example environment file
cp .env.example .env

# Edit with your favorite editor
nano .env  # or vim, code, etc.
```

**Required environment variables:**

```bash
# Database Configuration
DATABASE_URL=postgresql://fpna_app:your_secure_password_here@localhost:5432/ai_fpna_db
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-your-api-key-here

# ERP Credentials - TOTVS Protheus
TOTVS_CLIENT_ID=your_totvs_client_id
TOTVS_CLIENT_SECRET=your_totvs_client_secret
TOTVS_TENANT=your_tenant_id
TOTVS_BASE_URL=https://api.totvs.com.br

# ERP Credentials - ContaAzul
CONTAAZUL_CLIENT_ID=your_contaazul_client_id
CONTAAZUL_CLIENT_SECRET=your_contaazul_client_secret
CONTAAZUL_BASE_URL=https://api.contaazul.com

# ERP Credentials - Omie
OMIE_APP_KEY=your_omie_app_key
OMIE_APP_SECRET=your_omie_app_secret
OMIE_BASE_URL=https://app.omie.com.br/api/v1

# ERP Credentials - Bling
BLING_API_KEY=your_bling_api_key
BLING_BASE_URL=https://api.bling.com.br/Api/v3

# Application Settings
ENVIRONMENT=development
LOG_LEVEL=INFO
SECRET_KEY=your-secret-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1

# Email Configuration (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_email_password
```

**Security Note**: Never commit `.env` to version control. The `.gitignore` file already excludes it.

### Step 7: Verify Installation

Run the verification script:

```bash
# Make verification script executable
chmod +x scripts/verify_installation.sh

# Run verification
./scripts/verify_installation.sh
```

**Expected output:**

```
✓ Python version: 3.13.2
✓ PostgreSQL connection: OK
✓ Redis connection: OK
✓ Database tables: 24 tables found
✓ Seed data: 7 entities, 150 standard accounts
✓ Environment variables: All required variables set
✓ ERP connections: 4/4 accessible
✓ Anthropic API: OK

Installation verification: PASSED
```

### Step 8: Run Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

**Expected output:**

```
============================= test session starts ==============================
collected 127 items

tests/test_connectors.py ...................... [ 17%]
tests/test_consolidation.py ...................... [ 33%]
tests/test_fx_converter.py ............ [ 42%]
tests/test_validation.py ................ [ 54%]
tests/integration/test_full_close.py .................... [ 70%]
...

============================= 127 passed in 45.2s ==============================
```

### Step 9: Start Application

#### Start Celery Worker (Terminal 1)

```bash
# Activate virtual environment
source .venv/bin/activate

# Start Celery worker
celery -A src.orchestration.celery_app worker --loglevel=info
```

**Expected output:**

```
[2026-02-07 10:00:00,000: INFO/MainProcess] Connected to redis://localhost:6379/0
[2026-02-07 10:00:00,050: INFO/MainProcess] celery@hostname ready.
```

#### Start FastAPI Application (Terminal 2)

```bash
# Activate virtual environment
source .venv/bin/activate

# Start FastAPI development server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using WatchFiles
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

#### Verify API is Running

Open a web browser and navigate to:

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

Expected health check response:

```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "version": "1.0.0"
}
```

---

## Production Deployment

For production deployment on AWS, follow these steps:

### Step 1: AWS Infrastructure Setup

#### Create RDS PostgreSQL Instance

```bash
# Using AWS CLI
aws rds create-db-instance \
  --db-instance-identifier fpna-postgres \
  --db-instance-class db.r6g.xlarge \
  --engine postgres \
  --engine-version 15.5 \
  --master-username fpna_admin \
  --master-user-password "your_secure_password" \
  --allocated-storage 100 \
  --storage-type gp3 \
  --storage-encrypted \
  --backup-retention-period 7 \
  --multi-az \
  --vpc-security-group-ids sg-xxxxxxxxx \
  --db-subnet-group-name fpna-db-subnet-group
```

#### Create ElastiCache Redis

```bash
# Using AWS CLI
aws elasticache create-cache-cluster \
  --cache-cluster-id fpna-redis \
  --cache-node-type cache.t3.medium \
  --engine redis \
  --engine-version 7.0 \
  --num-cache-nodes 1 \
  --security-group-ids sg-xxxxxxxxx \
  --cache-subnet-group-name fpna-redis-subnet-group
```

#### Create S3 Buckets

```bash
# Create bucket for reports
aws s3 mb s3://fpna-reports-prod --region us-east-1

# Create bucket for archival
aws s3 mb s3://fpna-archive-prod --region us-east-1

# Enable versioning on reports bucket
aws s3api put-bucket-versioning \
  --bucket fpna-reports-prod \
  --versioning-configuration Status=Enabled
```

### Step 2: Store Secrets in AWS Secrets Manager

```bash
# Store database credentials
aws secretsmanager create-secret \
  --name fpna/prod/database \
  --secret-string '{
    "username": "fpna_admin",
    "password": "your_secure_password",
    "host": "fpna-postgres.xxxxxxxx.us-east-1.rds.amazonaws.com",
    "port": "5432",
    "database": "ai_fpna_db"
  }'

# Store Anthropic API key
aws secretsmanager create-secret \
  --name fpna/prod/anthropic \
  --secret-string '{"api_key": "sk-ant-your-api-key-here"}'

# Store ERP credentials
aws secretsmanager create-secret \
  --name fpna/prod/erp-credentials \
  --secret-string '{
    "totvs": {
      "client_id": "...",
      "client_secret": "..."
    },
    "contaazul": {
      "client_id": "...",
      "client_secret": "..."
    },
    "omie": {
      "app_key": "...",
      "app_secret": "..."
    },
    "bling": {
      "api_key": "..."
    }
  }'
```

### Step 3: Build and Push Docker Image

```bash
# Build Docker image
docker build -t fpna-app:latest .

# Tag for ECR
docker tag fpna-app:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/fpna-app:latest

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com

# Push image
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/fpna-app:latest
```

### Step 4: Deploy to ECS

```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name fpna-prod-cluster

# Register task definition
aws ecs register-task-definition --cli-input-json file://ecs/task-definition.json

# Create ECS service
aws ecs create-service \
  --cluster fpna-prod-cluster \
  --service-name fpna-app \
  --task-definition fpna-app:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-zzz],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/fpna-tg/xxx,containerName=fpna-app,containerPort=8000"
```

### Step 5: Run Database Migrations

```bash
# Connect to RDS instance
psql -h fpna-postgres.xxxxxxxx.us-east-1.rds.amazonaws.com -U fpna_admin -d ai_fpna_db

# Run migrations
\i migrations/001_initial_schema.sql
\i migrations/002_rls_policies.sql
\i migrations/003_indexes.sql

# Load seed data
\i seeds/001_portfolio_entities.sql
\i seeds/002_standard_coa.sql

# Exit psql
\q
```

### Step 6: Verify Production Deployment

```bash
# Check ECS service status
aws ecs describe-services --cluster fpna-prod-cluster --services fpna-app

# Check health endpoint
curl https://api.fpna.nuvini.ai/health

# Check CloudWatch logs
aws logs tail /ecs/fpna-app --follow
```

---

## Post-Installation Configuration

### Configure Scheduled Jobs

#### Monthly Close Trigger

```bash
# Create Lambda function for monthly trigger
aws lambda create-function \
  --function-name fpna-monthly-trigger \
  --runtime python3.13 \
  --handler lambda_function.lambda_handler \
  --role arn:aws:iam::123456789012:role/fpna-lambda-role \
  --code S3Bucket=fpna-deployments,S3Key=monthly-trigger.zip

# Create EventBridge rule (trigger on 1st of each month at 6 AM UTC)
aws events put-rule \
  --name fpna-monthly-close \
  --schedule-expression "cron(0 6 1 * ? *)" \
  --state ENABLED

# Add Lambda target to rule
aws events put-targets \
  --rule fpna-monthly-close \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:123456789012:function:fpna-monthly-trigger"
```

### Configure Monitoring

#### CloudWatch Alarms

```bash
# Database connection errors
aws cloudwatch put-metric-alarm \
  --alarm-name fpna-db-connection-errors \
  --alarm-description "Alert when DB connection errors exceed threshold" \
  --metric-name DatabaseConnectionErrors \
  --namespace FPNA \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:fpna-alerts

# Consolidation failures
aws cloudwatch put-metric-alarm \
  --alarm-name fpna-consolidation-failures \
  --alarm-description "Alert when consolidation fails" \
  --metric-name ConsolidationErrors \
  --namespace FPNA \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:fpna-alerts
```

### Create Admin User

```bash
# Connect to database
psql -h localhost -U fpna_app -d ai_fpna_db

# Create admin user
INSERT INTO users (user_id, email, full_name, role, is_active)
VALUES (
  gen_random_uuid(),
  'admin@nuvini.ai',
  'FP&A Administrator',
  'admin',
  true
);

# Grant access to all entities
INSERT INTO user_entity_access (user_id, entity_id, can_read, can_write, can_approve)
SELECT
  (SELECT user_id FROM users WHERE email = 'admin@nuvini.ai'),
  entity_id,
  true,
  true,
  true
FROM portfolio_entities;

# Exit psql
\q
```

---

## Troubleshooting

### Database Connection Issues

**Problem**: Cannot connect to PostgreSQL

```bash
# Check if PostgreSQL is running
pg_isready -h localhost -p 5432

# Check PostgreSQL logs
tail -f /usr/local/var/log/postgres.log  # macOS
sudo tail -f /var/log/postgresql/postgresql-15-main.log  # Linux

# Test connection with psql
psql -U fpna_app -d ai_fpna_db -h localhost
```

### Redis Connection Issues

**Problem**: Cannot connect to Redis

```bash
# Check if Redis is running
redis-cli ping

# Check Redis logs
tail -f /usr/local/var/log/redis.log  # macOS
sudo tail -f /var/log/redis/redis-server.log  # Linux

# Restart Redis
brew services restart redis  # macOS
sudo systemctl restart redis  # Linux
```

### Import Errors

**Problem**: `ModuleNotFoundError` when running the application

```bash
# Verify virtual environment is activated
which python
# Should show: /path/to/.venv/bin/python

# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Check installed packages
pip list
```

### Migration Errors

**Problem**: Database migration fails

```bash
# Check PostgreSQL version
psql --version

# Verify database exists
psql -U postgres -l | grep ai_fpna_db

# Check for existing tables
psql -U fpna_app -d ai_fpna_db -c "\dt"

# Drop and recreate database (CAUTION: destroys data)
dropdb ai_fpna_db
createdb ai_fpna_db
```

### Permission Denied Errors

**Problem**: Permission denied when running scripts

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Check file ownership
ls -la scripts/

# Fix ownership if needed
sudo chown $(whoami) scripts/*.sh
```

---

## Next Steps

After successful installation:

1. **[Quick Start](quick-start.md)** - Run your first consolidation
2. **[User Guide](../user-guide/)** - Learn how to use the system
3. **[API Documentation](../technical-reference/api.md)** - Integrate with other systems

---

## Support

For installation issues:

- **Documentation**: Review this guide and [Requirements](requirements.md)
- **GitHub Issues**: File a bug report
- **Email**: support@nuvini.ai
