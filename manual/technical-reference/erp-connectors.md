# ERP Connectors Technical Reference

**Version:** 1.0.0
**Last Updated:** 2026-02-07
**Implementation:** `/Volumes/AI/Code/FPA/src/connectors/`

## Overview

The ERP Connector Framework provides a unified interface for extracting financial data from 4 different Brazilian ERP systems. The framework implements authentication, retry logic, rate limiting, data validation, and normalization to ensure reliable data ingestion.

## Architecture

### Design Patterns

| Pattern | Purpose | Implementation |
|---------|---------|----------------|
| **Abstract Factory** | Create connector instances | `ConnectorFactory` |
| **Strategy** | Multiple auth/retry strategies | `OAuth2Handler`, `APIKeyHandler` |
| **Decorator** | Automatic retry logic | `@with_retry` decorator |
| **Template Method** | Common connector interface | `ERPConnector` base class |
| **Circuit Breaker** | Prevent cascading failures | `CircuitBreaker` class |

### Component Structure

```
connectors/
├── base.py                    # Abstract base class
├── auth.py                    # Authentication handlers
├── retry.py                   # Retry logic & circuit breaker
├── validation.py              # Data validation
├── factory.py                 # Connector factory
├── totvs_connector.py         # TOTVS Protheus
├── contaazul_connector.py     # ContaAzul
├── omie_connector.py          # Omie
├── bling_connector.py         # Bling
└── __init__.py                # Public API
```

## Base Classes and Models

### ERPConnector (Abstract Base Class)

All ERP connectors inherit from `ERPConnector` and must implement:

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

class ERPConnector(ABC):
    """Abstract base class for all ERP connectors."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection and authenticate."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection and cleanup."""
        pass

    @abstractmethod
    async def health_check(self) -> HealthCheckResult:
        """Check API health and connectivity."""
        pass

    @abstractmethod
    async def get_trial_balance(
        self,
        company_id: str,
        period_start: datetime,
        period_end: datetime,
        filters: Optional[dict] = None
    ) -> TrialBalance:
        """Extract trial balance for a period."""
        pass

    @abstractmethod
    async def get_subledger_details(
        self,
        company_id: str,
        account_code: str,
        period_start: datetime,
        period_end: datetime,
        filters: Optional[dict] = None
    ) -> List[SubledgerEntry]:
        """Extract subledger detail for an account."""
        pass
```

### Data Models

#### TrialBalance

```python
@dataclass
class TrialBalance:
    """Trial balance for an entity and period."""
    company_id: str
    company_name: str
    period_start: datetime
    period_end: datetime
    currency: str
    accounts: List[AccountBalance]
    extracted_at: datetime
    metadata: dict = field(default_factory=dict)
```

#### AccountBalance

```python
@dataclass
class AccountBalance:
    """Balance for a single account."""
    account_code: str
    account_name: str
    account_type: str  # ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE
    parent_account_code: Optional[str]
    level: int
    opening_balance: float
    debit_amount: float
    credit_amount: float
    closing_balance: float
    is_summary: bool = False
```

#### SubledgerEntry

```python
@dataclass
class SubledgerEntry:
    """Detail transaction for an account."""
    entry_id: str
    transaction_date: datetime
    posting_date: datetime
    account_code: str
    account_name: str
    debit_amount: float
    credit_amount: float
    description: str
    document_number: Optional[str] = None
    document_type: Optional[str] = None
    cost_center: Optional[str] = None
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    metadata: dict = field(default_factory=dict)
```

## Authentication

### Authentication Types

```python
from enum import Enum

class AuthType(Enum):
    """Supported authentication types."""
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    BASIC_AUTH = "basic_auth"
    BEARER_TOKEN = "bearer_token"
```

### OAuth2Handler

OAuth 2.0 authentication with automatic token refresh.

```python
from connectors.auth import OAuth2Handler

# Initialize
auth_handler = OAuth2Handler(
    client_id="your_client_id",
    client_secret="your_client_secret",
    token_url="https://api.example.com/oauth/token",
    scope="read:financials"
)

# Get authenticated session
async with auth_handler.get_session() as session:
    response = await session.get("https://api.example.com/data")
```

**Features:**
- Automatic token refresh when expired
- Token caching to reduce auth overhead
- Thread-safe token management
- Configurable token expiration

**Configuration:**

```python
{
    "client_id": "abc123",
    "client_secret": "secret456",
    "token_url": "https://api.erp.com/oauth/token",
    "scope": "read:financials write:data",
    "grant_type": "client_credentials"
}
```

### APIKeyHandler

API key authentication (app key + app secret).

```python
from connectors.auth import APIKeyHandler

auth_handler = APIKeyHandler(
    api_key="your_app_key",
    api_secret="your_app_secret",
    key_location="header"  # or "query"
)
```

**Header-based:**
```http
GET /api/data
X-App-Key: your_app_key
X-App-Secret: your_app_secret
```

**Query-based:**
```http
GET /api/data?app_key=your_app_key&app_secret=your_app_secret
```

### BasicAuthHandler

HTTP Basic authentication.

```python
from connectors.auth import BasicAuthHandler

auth_handler = BasicAuthHandler(
    username="api_user",
    password="api_password"
)
```

### BearerTokenHandler

Bearer token authentication.

```python
from connectors.auth import BearerTokenHandler

auth_handler = BearerTokenHandler(
    token="your_bearer_token",
    token_expiration=3600  # Optional: seconds until expiration
)
```

## Retry Logic and Resilience

### Retry Strategies

```python
from enum import Enum

class RetryStrategy(Enum):
    """Retry backoff strategies."""
    EXPONENTIAL = "exponential"  # 1s, 2s, 4s, 8s
    LINEAR = "linear"            # 1s, 2s, 3s, 4s
    FIXED = "fixed"              # 1s, 1s, 1s, 1s
```

### Exponential Backoff

```python
from connectors.retry import with_retry, RetryStrategy

@with_retry(
    max_attempts=3,
    strategy=RetryStrategy.EXPONENTIAL,
    base_delay=1.0,
    max_delay=30.0,
    jitter=True
)
async def fetch_data():
    # Your API call here
    pass
```

**Backoff calculation:**
```python
delay = min(base_delay * (2 ** attempt), max_delay)
if jitter:
    delay = delay * (0.5 + random.random() * 0.5)
```

### Circuit Breaker

Prevents cascading failures by stopping requests after repeated failures.

```python
from connectors.retry import CircuitBreaker

circuit_breaker = CircuitBreaker(
    failure_threshold=5,      # Open after 5 failures
    recovery_timeout=60,      # Try recovery after 60 seconds
    expected_exception=APIError
)

async with circuit_breaker:
    response = await api_call()
```

**States:**
- `CLOSED` - Normal operation
- `OPEN` - Blocking requests (failures exceeded threshold)
- `HALF_OPEN` - Testing recovery

### Rate Limiting

Token bucket algorithm for rate limiting.

```python
from connectors.retry import TokenBucketRateLimiter

rate_limiter = TokenBucketRateLimiter(
    rate=100,        # 100 requests
    interval=60,     # per 60 seconds
    burst=10         # allow bursts up to 10
)

async with rate_limiter:
    response = await api_call()
```

## Data Validation

### Validation Functions

```python
from connectors.validation import (
    validate_account_type,
    validate_account_code,
    validate_amount,
    validate_date,
    validate_trial_balance
)

# Validate account type (Portuguese or English)
account_type = validate_account_type("Ativo")  # Returns "ASSET"
account_type = validate_account_type("Asset")  # Returns "ASSET"

# Validate account code
validate_account_code("1.01.001")  # Valid
validate_account_code("")          # Raises ValidationError

# Validate amount (converts to Decimal)
amount = validate_amount(1234.56)  # Returns Decimal("1234.56")
amount = validate_amount("1234.56")  # Returns Decimal("1234.56")

# Validate date (multiple formats)
date = validate_date("2024-12-31")           # Returns datetime
date = validate_date("31/12/2024")           # Returns datetime
date = validate_date("2024-12-31T10:30:00")  # Returns datetime
```

### Trial Balance Validation

```python
from connectors.validation import validate_trial_balance

trial_balance = TrialBalance(...)

# Validate trial balance
is_valid, errors = validate_trial_balance(trial_balance)

if not is_valid:
    for error in errors:
        print(f"Validation error: {error}")
```

**Validation checks:**
- Debit/credit balance (total debits = total credits)
- Account hierarchy consistency
- Account type validity
- Required fields present
- Data type correctness

## ERP-Specific Implementations

### TOTVS Protheus Connector

**Used by:** Effecti, OnClick

```python
from connectors import create_connector

connector = create_connector(
    erp_type="totvs_protheus",
    auth_type="oauth2",
    credentials={
        "client_id": "your_client_id",
        "client_secret": "your_client_secret",
        "token_url": "https://api.totvs.com.br/oauth/token"
    },
    config={
        "base_url": "https://api.totvs.com.br/protheus",
        "tenant": "your_tenant_id",
        "environment": "production"
    }
)
```

**Features:**
- OAuth 2.0 authentication
- REST API integration
- Trial balance extraction via `/balancete` endpoint
- Subledger detail via `/movimentacao` endpoint
- Rate limit: 100 requests/minute

**API Endpoints:**

```python
# Trial balance
GET /protheus/rest/CTBR020/balancete
    ?empresa={company_id}
    &dataInicial={YYYYMMDD}
    &dataFinal={YYYYMMDD}

# Subledger entries
GET /protheus/rest/CTBR020/movimentacao
    ?empresa={company_id}
    &conta={account_code}
    &dataInicial={YYYYMMDD}
    &dataFinal={YYYYMMDD}
```

**Data Mapping:**

| TOTVS Field | Standard Field | Notes |
|-------------|---------------|-------|
| `CT1_CONTA` | `account_code` | Account code |
| `CT1_DESC01` | `account_name` | Account name |
| `CTI_CLASSE` | `account_type` | 1=Analytic, 2=Synthetic |
| `CTI_NORMAL` | `normal_balance` | D=Debit, C=Credit |
| `CTI_SALDOI` | `opening_balance` | Opening balance |
| `CTI_DEBITO` | `debit_amount` | Period debits |
| `CTI_CREDITO` | `credit_amount` | Period credits |
| `CTI_SALDOF` | `closing_balance` | Closing balance |

### ContaAzul Connector

**Used by:** Mercos, Munddi

```python
connector = create_connector(
    erp_type="contaazul",
    auth_type="oauth2",
    credentials={
        "client_id": "your_client_id",
        "client_secret": "your_client_secret",
        "token_url": "https://api.contaazul.com/oauth/token"
    },
    config={
        "base_url": "https://api.contaazul.com/v1"
    }
)
```

**Features:**
- OAuth 2.0 authentication
- REST API integration
- Trial balance via transaction aggregation
- Rate limit: 60 requests/minute

**API Endpoints:**

```python
# Chart of accounts
GET /v1/chart-of-accounts

# Transactions
GET /v1/transactions
    ?start_date={YYYY-MM-DD}
    &end_date={YYYY-MM-DD}
    &page={page}
    &per_page={per_page}
```

**Trial Balance Construction:**

ContaAzul doesn't provide a direct trial balance endpoint. The connector:
1. Fetches chart of accounts
2. Fetches all transactions for period
3. Aggregates transactions by account
4. Constructs trial balance

```python
# Pseudocode
accounts = await fetch_chart_of_accounts()
transactions = await fetch_transactions(period_start, period_end)

trial_balance = {}
for transaction in transactions:
    for line in transaction.lines:
        account = trial_balance.get(line.account_code, {
            'opening_balance': 0,
            'debit_amount': 0,
            'credit_amount': 0
        })
        account['debit_amount'] += line.debit_amount
        account['credit_amount'] += line.credit_amount
        trial_balance[line.account_code] = account
```

### Omie Connector

**Used by:** Datahub

```python
connector = create_connector(
    erp_type="omie",
    auth_type="api_key",
    credentials={
        "app_key": "your_app_key",
        "app_secret": "your_app_secret"
    },
    config={
        "base_url": "https://app.omie.com.br/api/v1"
    }
)
```

**Features:**
- API Key authentication (app_key + app_secret)
- JSON-RPC API
- Direct balance extraction
- Rate limit: 300 requests/minute

**API Calls:**

```python
# Trial balance (Balancete)
POST /geral/balancete/
{
    "call": "ListarBalancete",
    "app_key": "your_app_key",
    "app_secret": "your_app_secret",
    "param": [{
        "dDataDe": "01/01/2024",
        "dDataAte": "31/12/2024",
        "nCodEmpresa": 123
    }]
}

# Account movements
POST /geral/contacorrente/
{
    "call": "ListarMovimentos",
    "app_key": "your_app_key",
    "app_secret": "your_app_secret",
    "param": [{
        "cCodConta": "1.01.001",
        "dDataDe": "01/01/2024",
        "dDataAte": "31/12/2024"
    }]
}
```

**Data Mapping:**

| Omie Field | Standard Field |
|------------|---------------|
| `cCodConta` | `account_code` |
| `cDescConta` | `account_name` |
| `cTipoConta` | `account_type` |
| `nSaldoInicial` | `opening_balance` |
| `nDebitos` | `debit_amount` |
| `nCreditos` | `credit_amount` |
| `nSaldoFinal` | `closing_balance` |

### Bling Connector

**Used by:** Ipê Digital, Leadlovers

```python
connector = create_connector(
    erp_type="bling",
    auth_type="api_key",  # or "oauth2"
    credentials={
        "api_key": "your_api_key"
    },
    config={
        "base_url": "https://bling.com.br/Api/v3",
        "api_version": "v3"  # or "v2"
    }
)
```

**Features:**
- API Key or OAuth 2.0 authentication
- Supports both v2 (XML) and v3 (JSON) APIs
- Rate limit: 100 requests/minute

**API Endpoints (v3):**

```python
# Chart of accounts
GET /v3/contascontabeis
    ?pagina={page}
    &limite={limit}

# Account movements
GET /v3/contascontabeis/{account_id}/movimentacoes
    ?dataInicial={YYYY-MM-DD}
    &dataFinal={YYYY-MM-DD}
```

**XML vs JSON:**

| Version | Format | Authentication | Status |
|---------|--------|---------------|--------|
| v2 | XML | API Key | Legacy |
| v3 | JSON | OAuth 2.0 or API Key | Current |

## Connector Factory

### Creating Connectors

```python
from connectors import create_connector

# Create by ERP type
connector = create_connector(
    erp_type="totvs_protheus",
    auth_type="oauth2",
    credentials={...},
    config={...}
)

# Create by portfolio company
connector = create_connector_for_company(
    company_code="EFFECTI",
    credentials={...}
)
```

### Portfolio Company Mapping

```python
PORTFOLIO_COMPANY_ERP_MAPPING = {
    "EFFECTI": "totvs_protheus",
    "ONCLICK": "totvs_protheus",
    "MERCOS": "contaazul",
    "MUNDDI": "contaazul",
    "DATAHUB": "omie",
    "IPE_DIGITAL": "bling",
    "LEADLOVERS": "bling"
}
```

## Usage Examples

### Basic Usage

```python
from connectors import create_connector
from datetime import datetime

# Create connector
connector = create_connector(
    erp_type="totvs_protheus",
    auth_type="oauth2",
    credentials={
        "client_id": "your_client_id",
        "client_secret": "your_client_secret"
    },
    config={
        "tenant": "your_tenant_id"
    }
)

# Use async context manager
async with connector:
    # Health check
    health = await connector.health_check()
    print(f"Status: {health.status}")

    # Extract trial balance
    trial_balance = await connector.get_trial_balance(
        company_id="01",
        period_start=datetime(2024, 1, 1),
        period_end=datetime(2024, 12, 31)
    )

    print(f"Company: {trial_balance.company_name}")
    print(f"Currency: {trial_balance.currency}")
    print(f"Accounts: {len(trial_balance.accounts)}")

    for account in trial_balance.accounts:
        print(f"  {account.account_code}: {account.closing_balance}")

    # Extract subledger
    entries = await connector.get_subledger_details(
        company_id="01",
        account_code="1.01.001",
        period_start=datetime(2024, 1, 1),
        period_end=datetime(2024, 12, 31)
    )

    print(f"Subledger entries: {len(entries)}")
```

### Error Handling

```python
from connectors.exceptions import (
    ERPConnectionError,
    ERPAuthenticationError,
    ERPValidationError,
    ERPRateLimitError
)

try:
    trial_balance = await connector.get_trial_balance(...)
except ERPAuthenticationError as e:
    print(f"Authentication failed: {e}")
    # Refresh credentials
except ERPConnectionError as e:
    print(f"Connection failed: {e}")
    # Retry or alert
except ERPRateLimitError as e:
    print(f"Rate limit exceeded: {e}")
    # Wait and retry
except ERPValidationError as e:
    print(f"Validation error: {e}")
    # Fix data and retry
```

### Filtering

```python
# Filter by account type
trial_balance = await connector.get_trial_balance(
    company_id="01",
    period_start=datetime(2024, 1, 1),
    period_end=datetime(2024, 12, 31),
    filters={
        "account_types": ["ASSET", "LIABILITY"],
        "include_zero_balances": False,
        "level": 3  # Detail accounts only
    }
)

# Filter subledger by document type
entries = await connector.get_subledger_details(
    company_id="01",
    account_code="1.01.001",
    period_start=datetime(2024, 1, 1),
    period_end=datetime(2024, 12, 31),
    filters={
        "document_types": ["invoice", "payment"],
        "cost_center": "CC001"
    }
)
```

## Performance Characteristics

### Rate Limits

| ERP | Requests/Minute | Burst | Notes |
|-----|----------------|-------|-------|
| TOTVS Protheus | 100 | 10 | Per tenant |
| ContaAzul | 60 | 5 | Per OAuth app |
| Omie | 300 | 20 | Per app_key |
| Bling | 100 | 10 | Per API key |

### Timeouts

- **Default:** 30 seconds per request
- **Health check:** 10 seconds
- **Large data extracts:** 120 seconds

### Memory Usage

- **Streaming:** Used where possible to minimize memory
- **Pagination:** Large datasets retrieved in chunks
- **Token caching:** Reduces auth overhead

## Testing

### Unit Tests

```bash
cd /Volumes/AI/Code/FPA
python -m pytest src/connectors/tests/test_connectors.py -v
```

**Test coverage:**
- Credentials validation: 4 tests
- Account validation: 7 tests
- Amount validation: 6 tests
- Date validation: 4 tests
- Trial balance validation: 3 tests
- OAuth2 handler: 2 tests
- API key handler: 2 tests
- Retry logic: 4 tests
- Rate limiter: 2 tests
- Factory pattern: 5 tests
- Portfolio mapping: 5 tests
- Integration tests: 2 tests

### Mock Testing

```python
from unittest.mock import AsyncMock, patch

@patch('connectors.totvs_connector.TOTVSProtheusConnector._make_request')
async def test_get_trial_balance(mock_request):
    mock_request.return_value = {
        "balancete": [
            {
                "CT1_CONTA": "1.01.001",
                "CT1_DESC01": "Caixa",
                "CTI_SALDOF": 100000.00
            }
        ]
    }

    connector = create_connector(...)
    trial_balance = await connector.get_trial_balance(...)

    assert len(trial_balance.accounts) == 1
    assert trial_balance.accounts[0].account_code == "1.01.001"
```

## Security

### Credential Storage

**Never hardcode credentials:**

```python
# ❌ Bad
connector = create_connector(
    credentials={"client_id": "abc123"}
)

# ✅ Good
import os
connector = create_connector(
    credentials={
        "client_id": os.environ["TOTVS_CLIENT_ID"],
        "client_secret": os.environ["TOTVS_CLIENT_SECRET"]
    }
)
```

### HTTPS Enforcement

All connectors enforce HTTPS:

```python
if not config["base_url"].startswith("https://"):
    raise ValueError("HTTPS required for API connections")
```

### Token Security

- Tokens stored in memory only
- Automatic expiration handling
- No token logging
- Secure token transmission

## Troubleshooting

### Common Issues

**Authentication failures:**
```python
# Check credentials
health = await connector.health_check()
if health.status != ConnectionStatus.CONNECTED:
    print(f"Auth error: {health.error_message}")
```

**Rate limit exceeded:**
```python
# Reduce request rate or implement backoff
from connectors.retry import TokenBucketRateLimiter
rate_limiter = TokenBucketRateLimiter(rate=50, interval=60)
```

**Connection timeouts:**
```python
# Increase timeout
config = {
    "timeout": 60,  # seconds
    "retry_on_timeout": True
}
```

### Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable connector debug logs
connector = create_connector(..., config={"debug": True})
```

## See Also

- [Database Schema](/Volumes/AI/Code/FPA/manual/technical-reference/database.md)
- [API Reference](/Volumes/AI/Code/FPA/manual/technical-reference/api-reference.md)
- [Configuration Reference](/Volumes/AI/Code/FPA/manual/technical-reference/configuration.md)
