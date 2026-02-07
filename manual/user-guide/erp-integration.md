# ERP Integration Guide

## Overview

The AI FP&A system connects to four different Brazilian ERP systems used across the portfolio companies. This guide covers configuration, authentication, data extraction, and troubleshooting for each ERP connector.

## Supported ERP Systems

| ERP System | Companies | Auth Type | Rate Limit | API Version |
|------------|-----------|-----------|------------|-------------|
| **TOTVS Protheus** | Effecti, OnClick | OAuth 2.0 | 100/min | REST API |
| **ContaAzul** | Mercos, Munddi | OAuth 2.0 | 60/min | v1 |
| **Omie** | Datahub | API Key | 300/min | v1 |
| **Bling** | Ipê Digital, Leadlovers | API Key / OAuth 2.0 | 100/min | v3 (JSON) |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  ERP Connector Framework                 │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Base Class   │  │ Auth Handler │  │ Rate Limiter │  │
│  │ ERPConnector │  │ - OAuth 2.0  │  │ - Token      │  │
│  │              │  │ - API Key    │  │   Bucket     │  │
│  │ - connect()  │  │ - Bearer     │  │ - Circuit    │  │
│  │ - get_tb()   │  │              │  │   Breaker    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         ↑                                                │
│         │                                                │
│  ┌──────┴───────────────────────────────────────────┐  │
│  │   TOTVS   │  ContaAzul  │   Omie   │   Bling    │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### Install Dependencies

```bash
cd /Volumes/AI/Code/FPA
pip install httpx pydantic python-dotenv
```

### Configure Credentials

Create a `.env` file:

```bash
# TOTVS Protheus (Effecti)
TOTVS_EFFECTI_CLIENT_ID=your_client_id
TOTVS_EFFECTI_CLIENT_SECRET=your_client_secret
TOTVS_EFFECTI_TENANT=effecti_tenant_id
TOTVS_EFFECTI_BASE_URL=https://api.totvs.com.br

# ContaAzul (Mercos)
CONTAAZUL_MERCOS_CLIENT_ID=your_client_id
CONTAAZUL_MERCOS_CLIENT_SECRET=your_client_secret
CONTAAZUL_MERCOS_BASE_URL=https://api.contaazul.com

# Omie (Datahub)
OMIE_DATAHUB_APP_KEY=your_app_key
OMIE_DATAHUB_APP_SECRET=your_app_secret
OMIE_DATAHUB_BASE_URL=https://app.omie.com.br/api/v1

# Bling (Leadlovers)
BLING_LEADLOVERS_API_KEY=your_api_key
BLING_LEADLOVERS_BASE_URL=https://api.bling.com.br/Api/v3
```

**Security:** Never commit `.env` file to git. Use AWS Secrets Manager in production.

### Test Connection

```bash
# Test TOTVS connection
python -m src.connectors.test \
  --erp totvs_protheus \
  --company effecti

# Test all connections
python -m src.connectors.health_check --all
```

## ERP-Specific Configuration

### TOTVS Protheus

**Used by:** Effecti, OnClick

#### Authentication Setup

1. **Register OAuth Application** in TOTVS Developer Portal
2. **Configure Redirect URI:** `https://your-app.com/callback/totvs`
3. **Copy Client ID and Secret** to `.env`

#### Configuration

```python
from src.connectors import create_connector

connector = create_connector(
    erp_type="totvs_protheus",
    auth_type="oauth2",
    credentials={
        "client_id": "your_client_id",
        "client_secret": "your_client_secret"
    },
    config={
        "base_url": "https://api.totvs.com.br",
        "tenant": "your_tenant_id",
        "environment": "PRODUCAO",  # or "HOMOLOGACAO"
        "timeout": 60.0,
        "retry_attempts": 3
    }
)

# Use async context manager
async with connector:
    # Get companies
    companies = await connector.get_companies()

    # Get trial balance
    trial_balance = await connector.get_trial_balance(
        company_id="01",
        period_start=datetime(2026, 1, 1),
        period_end=datetime(2026, 1, 31)
    )
```

#### API Endpoints Used

| Endpoint | Purpose | Method |
|----------|---------|--------|
| `/api/v1/companies` | List companies | GET |
| `/api/v1/financials/trial-balance` | Get trial balance | GET |
| `/api/v1/financials/subledger` | Get subledger details | GET |
| `/api/v1/health` | Health check | GET |

#### Data Mapping

TOTVS uses standard Brazilian COA:

| TOTVS Account Type | FPA Account Type | Example |
|-------------------|------------------|---------|
| ATIVO | ASSET | 1.01.001 - Caixa |
| PASSIVO | LIABILITY | 2.01.001 - Fornecedores |
| PATRIMONIO | EQUITY | 3.01.001 - Capital Social |
| RECEITA | REVENUE | 4.01.001 - Receita de Serviços |
| DESPESA | EXPENSE | 5.01.001 - Salários |

#### Rate Limits

- **Limit:** 100 requests per minute
- **Handling:** Automatic retry with exponential backoff
- **Circuit Breaker:** Opens after 5 consecutive failures

#### Troubleshooting

**Issue: OAuth token expired**

```bash
# Force token refresh
python -m src.connectors.refresh_token \
  --erp totvs_protheus \
  --company effecti
```

**Issue: Timeout during trial balance extraction**

```bash
# Increase timeout
python -m src.connectors.extract \
  --company effecti \
  --timeout 300 \
  --retry 5
```

**Issue: API returns 500 Internal Server Error**

Common cause: TOTVS server maintenance window

Solution:
1. Check TOTVS status page: https://status.totvs.com.br
2. Retry after maintenance window
3. If persistent, contact TOTVS support

### ContaAzul

**Used by:** Mercos, Munddi

#### Authentication Setup

1. **Create Developer Account** at https://developers.contaazul.com
2. **Create App** and get Client ID/Secret
3. **Configure OAuth Redirect:** `https://your-app.com/callback/contaazul`
4. **Request Scopes:** `sales`, `financials`, `companies`

#### Configuration

```python
connector = create_connector(
    erp_type="contaazul",
    auth_type="oauth2",
    credentials={
        "client_id": "your_client_id",
        "client_secret": "your_client_secret"
    },
    config={
        "base_url": "https://api.contaazul.com",
        "api_version": "v1",
        "timeout": 60.0
    }
)

async with connector:
    # ContaAzul doesn't have direct trial balance endpoint
    # Connector aggregates from transactions
    trial_balance = await connector.get_trial_balance(
        company_id="mercos_001",
        period_start=datetime(2026, 1, 1),
        period_end=datetime(2026, 1, 31)
    )
```

#### API Endpoints Used

| Endpoint | Purpose | Method |
|----------|---------|--------|
| `/v1/companies` | List companies | GET |
| `/v1/transactions` | Get financial transactions | GET |
| `/v1/accounts` | Get chart of accounts | GET |
| `/v1/categories` | Get transaction categories | GET |

#### Data Aggregation

ContaAzul doesn't provide trial balance directly. The connector:

1. **Fetches all transactions** for the period
2. **Groups by account code** from chart of accounts
3. **Calculates opening/closing balances** from transaction history
4. **Generates trial balance** in standard format

**Note:** First-time extraction may take longer due to historical data aggregation.

#### Rate Limits

- **Limit:** 60 requests per minute
- **Pagination:** 100 transactions per request
- **Recommended:** Schedule extractions during off-peak hours

#### Troubleshooting

**Issue: Missing account codes**

ContaAzul allows users to categorize without account codes.

Solution:
```python
# Map categories to account codes
from src.connectors.contaazul_connector import CategoryMapper

mapper = CategoryMapper()
mapper.map_category("Salários e Encargos", "5.01.001")
mapper.map_category("Receita de Assinaturas", "4.01.001")
```

**Issue: Transaction pagination timeout**

For companies with high transaction volume:

```python
# Use date-based chunking
from datetime import timedelta

async def extract_in_chunks(connector, company_id, period_start, period_end):
    current = period_start
    all_data = []

    while current < period_end:
        chunk_end = min(current + timedelta(days=7), period_end)
        chunk_data = await connector.get_transactions(
            company_id,
            current,
            chunk_end
        )
        all_data.extend(chunk_data)
        current = chunk_end

    return all_data
```

### Omie

**Used by:** Datahub

#### Authentication Setup

1. **Login to Omie** as administrator
2. **Navigate to:** Configurações → Integrações → Aplicações
3. **Create New App** and get App Key + App Secret
4. **Copy credentials** to `.env`

#### Configuration

```python
connector = create_connector(
    erp_type="omie",
    auth_type="api_key",
    credentials={
        "app_key": "your_app_key",
        "app_secret": "your_app_secret"
    },
    config={
        "base_url": "https://app.omie.com.br/api/v1",
        "timeout": 60.0
    }
)

async with connector:
    trial_balance = await connector.get_trial_balance(
        company_id="datahub_001",
        period_start=datetime(2026, 1, 1),
        period_end=datetime(2026, 1, 31)
    )
```

#### API Endpoints Used

Omie uses JSON-RPC style API:

| Method | Purpose | Endpoint |
|--------|---------|----------|
| `ListarPlanoConta` | List chart of accounts | `/produtos/contacorrente/` |
| `ListarContaCorrDet` | Get account details | `/produtos/contacorrente/` |
| `ConsultarBalancete` | Get trial balance | `/produtos/contabilidade/` |
| `ListarLancamentos` | Get subledger entries | `/produtos/contabilidade/` |

#### Request Format

Omie uses JSON-RPC format:

```json
{
  "call": "ConsultarBalancete",
  "app_key": "your_app_key",
  "app_secret": "your_app_secret",
  "param": [{
    "dDataDe": "01/01/2026",
    "dDataAte": "31/01/2026",
    "nCodConta": "1.01.001"
  }]
}
```

#### Rate Limits

- **Limit:** 300 requests per minute (most generous)
- **Burst:** Up to 500/min for short periods
- **Best practice:** Batch requests when possible

#### Troubleshooting

**Issue: Date format errors**

Omie requires Brazilian date format (DD/MM/YYYY):

```python
# Correct date formatting
from datetime import datetime

def format_omie_date(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y")

# Usage
param = {
    "dDataDe": format_omie_date(period_start),
    "dDataAte": format_omie_date(period_end)
}
```

**Issue: Account hierarchy not returned**

Omie may not include parent account relationships.

Solution: Use account code prefixes to infer hierarchy:
- `1.01.001` → Parent: `1.01` → Root: `1`

### Bling

**Used by:** Ipê Digital, Leadlovers

#### Authentication Setup

**Option 1: API Key (v3)**

1. **Login to Bling** → Configurações → API
2. **Generate API Key**
3. **Copy to `.env`**

**Option 2: OAuth 2.0 (recommended for production)**

1. **Register app** at https://developer.bling.com.br
2. **Get Client ID/Secret**
3. **Configure OAuth flow**

#### Configuration

```python
# API Key authentication
connector = create_connector(
    erp_type="bling",
    auth_type="api_key",
    credentials={
        "api_key": "your_api_key"
    },
    config={
        "base_url": "https://api.bling.com.br/Api/v3",
        "api_version": "3",  # v3 uses JSON, v2 uses XML
        "timeout": 60.0
    }
)

# OAuth 2.0 authentication
connector = create_connector(
    erp_type="bling",
    auth_type="oauth2",
    credentials={
        "client_id": "your_client_id",
        "client_secret": "your_client_secret"
    },
    config={
        "base_url": "https://api.bling.com.br/Api/v3",
        "api_version": "3"
    }
)

async with connector:
    trial_balance = await connector.get_trial_balance(
        company_id="leadlovers_001",
        period_start=datetime(2026, 1, 1),
        period_end=datetime(2026, 1, 31)
    )
```

#### API Endpoints Used

| Endpoint | Purpose | Method |
|----------|---------|--------|
| `/contas` | Chart of accounts | GET |
| `/contasreceber` | Accounts receivable | GET |
| `/contaspagar` | Accounts payable | GET |
| `/contabancaria/extrato` | Bank transactions | GET |
| `/notasfiscais` | Invoices | GET |

#### API Version Comparison

| Feature | v2 (XML) | v3 (JSON) |
|---------|----------|-----------|
| Data Format | XML | JSON |
| Trial Balance | ❌ Not available | ✓ Via aggregation |
| Subledger | Limited | ✓ Full access |
| Rate Limit | 100/min | 100/min |
| Recommendation | Deprecated | **Use this** |

#### Rate Limits

- **Limit:** 100 requests per minute
- **Throttling:** 503 error if exceeded
- **Recommendation:** Use pagination and rate limiter

#### Troubleshooting

**Issue: v2 API returns XML instead of JSON**

Ensure using v3 API endpoint:
```python
config = {
    "base_url": "https://api.bling.com.br/Api/v3",  # Note: /v3
    "api_version": "3"
}
```

**Issue: Trial balance not available**

Bling v3 doesn't have native trial balance endpoint.

Solution: Connector aggregates from:
- Accounts Receivable (`/contasreceber`)
- Accounts Payable (`/contaspagar`)
- Bank Transactions (`/contabancaria/extrato`)
- Invoices (`/notasfiscais`)

## Advanced Configuration

### Retry Configuration

Customize retry behavior per connector:

```python
from src.connectors import RetryConfig, RetryStrategy

connector = create_connector(
    erp_type="totvs_protheus",
    auth_type="oauth2",
    credentials={...},
    config={
        "retry_config": RetryConfig(
            max_attempts=5,          # Max 5 retries
            initial_delay=2.0,       # Start with 2s delay
            max_delay=120.0,         # Cap at 120s
            strategy=RetryStrategy.EXPONENTIAL,  # Exponential backoff
            jitter=True              # Add randomness to prevent thundering herd
        )
    }
)
```

### Circuit Breaker

Protect against cascading failures:

```python
from src.connectors.retry import CircuitBreaker

circuit_breaker = CircuitBreaker(
    failure_threshold=5,     # Open circuit after 5 failures
    recovery_timeout=60.0,   # Test recovery after 60s
    half_open_attempts=3     # Try 3 requests when half-open
)

# Circuit breaker states:
# CLOSED → Normal operation
# OPEN → Fail fast, don't attempt requests
# HALF_OPEN → Testing recovery
```

### Rate Limiting

Manual rate limit control:

```python
from src.connectors.retry import RateLimiter

# Create rate limiter
limiter = RateLimiter(
    rate=100,      # 100 requests
    per=60.0       # Per 60 seconds
)

# Acquire tokens before request
async def make_request():
    await limiter.acquire(tokens=1)
    response = await connector.get_trial_balance(...)
    return response
```

### Data Validation

Enable strict validation:

```python
from src.connectors.validation import ValidationConfig

connector = create_connector(
    erp_type="omie",
    auth_type="api_key",
    credentials={...},
    config={
        "validation": ValidationConfig(
            validate_account_codes=True,
            validate_amounts=True,
            validate_dates=True,
            validate_balances=True,  # Check Assets = Liabilities + Equity
            fail_on_validation_error=False  # Log warnings instead of failing
        )
    }
)
```

## Monitoring & Logging

### Enable Debug Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('connectors.log'),
        logging.StreamHandler()
    ]
)

# Now all connector operations are logged
```

### Health Checks

Monitor connector health:

```bash
# Check all connectors
python -m src.connectors.health_check --all

# Check specific connector
python -m src.connectors.health_check \
  --erp totvs_protheus \
  --company effecti
```

**Health check metrics:**
- Status: healthy, degraded, unhealthy
- Latency: API response time
- Last successful extraction
- Error rate (last 24h)

### Performance Metrics

Track connector performance:

```python
from src.connectors import ConnectorMetrics

metrics = ConnectorMetrics()

# Get metrics for connector
stats = metrics.get_stats("totvs_protheus")

print(f"Total Requests: {stats.total_requests}")
print(f"Success Rate: {stats.success_rate:.1%}")
print(f"Avg Latency: {stats.avg_latency_ms}ms")
print(f"Error Rate: {stats.error_rate:.1%}")
```

## Common Issues & Solutions

### Issue: Connection Timeout

**Symptoms:**
- `httpx.ConnectTimeout` exception
- Connection hangs for 60s

**Solutions:**

1. **Check network connectivity:**
   ```bash
   # Test API reachability
   curl -I https://api.totvs.com.br
   ```

2. **Increase timeout:**
   ```python
   config = {"timeout": 120.0}  # Increase to 120s
   ```

3. **Use retry logic:**
   ```python
   config = {
       "retry_config": RetryConfig(max_attempts=5)
   }
   ```

### Issue: Rate Limit Exceeded

**Symptoms:**
- `429 Too Many Requests` response
- `503 Service Temporarily Unavailable`

**Solutions:**

1. **Reduce request rate:**
   ```python
   import asyncio

   async def extract_with_delay():
       for company in companies:
           await connector.get_trial_balance(company)
           await asyncio.sleep(1)  # 1s delay between requests
   ```

2. **Use built-in rate limiter:**
   ```python
   # Rate limiter handles this automatically
   connector = create_connector(
       erp_type="contaazul",
       ...,
       config={"rate_limit": 60}  # 60 requests/min
   )
   ```

### Issue: Authentication Failure

**Symptoms:**
- `401 Unauthorized` response
- `Invalid credentials` error

**Solutions:**

1. **Verify credentials:**
   ```bash
   # Check .env file
   cat .env | grep TOTVS
   ```

2. **Refresh OAuth token:**
   ```bash
   python -m src.connectors.refresh_token \
     --erp totvs_protheus \
     --company effecti
   ```

3. **Re-authorize application:**
   - Visit ERP admin console
   - Revoke old token
   - Generate new token
   - Update `.env`

### Issue: Data Quality Errors

**Symptoms:**
- Trial balance doesn't balance
- Missing account codes
- Duplicate transactions

**Solutions:**

1. **Enable validation:**
   ```python
   config = {
       "validation": ValidationConfig(
           validate_balances=True,
           fail_on_validation_error=True
       )
   }
   ```

2. **Review validation report:**
   ```bash
   python -m src.reporting.validation_report \
     --company effecti \
     --period "2026-01-31"
   ```

3. **Contact ERP support** if data quality issues persist

## Best Practices

1. **Use Environment Variables:** Never hardcode credentials
2. **Enable Logging:** Always log connector operations for debugging
3. **Monitor Health:** Set up daily health checks for all connectors
4. **Test in Sandbox:** Use sandbox/test environments when available
5. **Handle Errors Gracefully:** Don't fail entire close for one company
6. **Cache Tokens:** OAuth handlers cache tokens automatically
7. **Paginate Large Datasets:** Use pagination for companies with high transaction volume
8. **Schedule Off-Peak:** Run extractions during off-peak hours to avoid rate limits

## Testing

### Unit Tests

Test individual connector functions:

```bash
# Test TOTVS connector
python -m pytest tests/connectors/test_totvs.py

# Test with coverage
python -m pytest tests/connectors/ --cov=src.connectors
```

### Integration Tests

Test against live ERP APIs:

```bash
# Set test environment variables
export TEST_MODE=integration
export TOTVS_EFFECTI_CLIENT_ID=test_client_id

# Run integration tests
python -m pytest tests/integration/test_totvs_integration.py
```

**Note:** Integration tests require valid ERP credentials and may count against rate limits.

## Support

### ERP Support Contacts

| ERP | Support Portal | Phone |
|-----|---------------|-------|
| TOTVS | https://suporte.totvs.com | +55 11 2099-7000 |
| ContaAzul | https://ajuda.contaazul.com | +55 48 3413-8300 |
| Omie | https://ajuda.omie.com.br | +55 11 4200-2300 |
| Bling | https://ajuda.bling.com.br | +55 13 3010-5007 |

### FPA Team Contact

**Technical Support:** [pschumacher@nuvini.ai](mailto:pschumacher@nuvini.ai)

**Escalation:** If ERP connector is blocking monthly close, escalate to FPA team immediately.

## Next Steps

- [Monthly Close Process](monthly-close.md) - Use connectors in monthly close
- [Troubleshooting Guide](troubleshooting.md) - Detailed troubleshooting
- [Technical Reference](../technical-reference/api.md) - API documentation

---

**Last Updated:** February 7, 2026
**Version:** 1.0.0
