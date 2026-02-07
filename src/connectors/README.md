# ERP Connector Framework

A comprehensive, reusable framework for connecting to Brazilian ERP systems used by FPA portfolio companies.

## Overview

This framework provides a standardized interface to extract financial data from four different ERP systems:

1. **TOTVS Protheus** - Used by Effecti, OnClick
2. **ContaAzul** - Used by Mercos, Munddi
3. **Omie** - Used by Datahub
4. **Bling** - Used by Ipê Digital, Leadlovers

## Features

- ✅ **Abstract Base Class** - Consistent interface across all ERPs
- ✅ **Multiple Authentication Methods** - OAuth 2.0, API Key, Basic Auth, Bearer Token
- ✅ **Automatic Retry Logic** - Exponential backoff for transient failures
- ✅ **Rate Limiting** - Per-provider rate limiting with token bucket algorithm
- ✅ **Circuit Breaker** - Prevent cascading failures
- ✅ **Data Validation** - Comprehensive validation and normalization
- ✅ **Health Checks** - Connection validation and monitoring
- ✅ **Async/Await** - Full async support with httpx
- ✅ **Logging** - Structured logging for debugging and monitoring

## Installation

```bash
pip install httpx
```

## Quick Start

### Basic Usage

```python
from datetime import datetime
from connectors import create_connector

# Create a connector
connector = create_connector(
    erp_type="totvs_protheus",
    auth_type="oauth2",
    credentials={
        "client_id": "your_client_id",
        "client_secret": "your_client_secret"
    },
    config={
        "base_url": "https://api.totvs.com.br",
        "tenant": "your_tenant_id"
    }
)

# Use async context manager (automatically connects/disconnects)
async with connector:
    # Check connection health
    health = await connector.health_check()
    print(f"Status: {health.status}, Latency: {health.latency_ms}ms")

    # Get trial balance
    trial_balance = await connector.get_trial_balance(
        company_id="01",
        period_start=datetime(2024, 1, 1),
        period_end=datetime(2024, 12, 31)
    )

    print(f"Company: {trial_balance.company_name}")
    for account in trial_balance.accounts:
        print(f"{account.account_code} - {account.account_name}: {account.closing_balance}")

    # Get subledger details
    entries = await connector.get_subledger_details(
        company_id="01",
        account_code="1.01.001",
        period_start=datetime(2024, 1, 1),
        period_end=datetime(2024, 12, 31)
    )

    for entry in entries:
        print(f"{entry.transaction_date}: {entry.description} - Debit: {entry.debit_amount}, Credit: {entry.credit_amount}")
```

### Using Factory with Config

```python
from connectors import ConnectorFactory

config = {
    "erp_type": "omie",
    "auth_type": "api_key",
    "credentials": {
        "api_key": "your_app_key",
        "app_secret": "your_app_secret"
    },
    "config": {
        "base_url": "https://app.omie.com.br/api/v1"
    }
}

connector = ConnectorFactory.create_from_config(config)

async with connector:
    companies = await connector.get_companies()
    for company in companies:
        print(f"{company['id']}: {company['name']}")
```

### Portfolio Company Lookup

```python
from connectors import get_erp_for_company, create_connector

# Get ERP type for a portfolio company
erp_type = get_erp_for_company("effecti")
print(f"Effecti uses: {erp_type}")  # ERPType.TOTVS_PROTHEUS

# Create connector for the company
connector = create_connector(
    erp_type=erp_type.value,
    auth_type="oauth2",
    credentials={...},
    config={...}
)
```

## ERP-Specific Configuration

### TOTVS Protheus

```python
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
        "environment": "PRODUCAO"  # or "HOMOLOGACAO"
    }
)
```

**Authentication**: OAuth 2.0 or Bearer Token
**Rate Limit**: 100 requests/minute
**API Documentation**: https://tdn.totvs.com/display/public/PROT/REST

### ContaAzul

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
        "api_version": "v1"
    }
)
```

**Authentication**: OAuth 2.0
**Rate Limit**: 60 requests/minute
**API Documentation**: https://developers.contaazul.com/

**Note**: ContaAzul doesn't have a direct trial balance endpoint. The connector aggregates from financial transactions.

### Omie

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

**Authentication**: API Key (app_key + app_secret)
**Rate Limit**: 300 requests/minute
**API Documentation**: https://developer.omie.com.br/

### Bling

```python
connector = create_connector(
    erp_type="bling",
    auth_type="api_key",
    credentials={
        "api_key": "your_api_key"
    },
    config={
        "base_url": "https://api.bling.com.br/Api/v3",
        "api_version": "3"  # "3" for JSON API, "2" for XML API
    }
)
```

**Authentication**: API Key or OAuth 2.0
**Rate Limit**: 100 requests/minute
**API Documentation**: https://manualdoapi.bling.com.br/

**Note**: API v3 (JSON) is recommended. v2 (XML) has limited functionality.

## Advanced Features

### Custom Retry Configuration

```python
from connectors import create_connector, RetryConfig, RetryStrategy

connector = create_connector(
    erp_type="totvs_protheus",
    auth_type="oauth2",
    credentials={...},
    config={
        "retry_config": RetryConfig(
            max_attempts=5,
            initial_delay=2.0,
            max_delay=120.0,
            strategy=RetryStrategy.EXPONENTIAL,
            jitter=True
        )
    }
)
```

### Circuit Breaker

The framework includes a built-in circuit breaker to prevent cascading failures:

```python
from connectors.retry import CircuitBreaker

circuit_breaker = CircuitBreaker(
    failure_threshold=5,  # Open circuit after 5 failures
    recovery_timeout=60.0  # Wait 60s before testing recovery
)

# Circuit breaker is used internally by connectors
```

### Manual Rate Limiting

```python
from connectors.retry import RateLimiter

# Create a rate limiter
limiter = RateLimiter(rate=100, per=60.0)  # 100 requests per 60 seconds

# Acquire tokens before making requests
await limiter.acquire(tokens=1)
```

### Data Validation

All data is automatically validated and normalized:

```python
from connectors.validation import (
    AccountTypeValidator,
    AccountCodeValidator,
    AmountValidator,
    DateValidator
)

# Validate account type
account_type = AccountTypeValidator.validate("ATIVO")  # Returns "ASSET"

# Validate account code
account_code = AccountCodeValidator.validate("1.01.001")

# Validate amount
amount = AmountValidator.validate("1,234.56")  # Returns Decimal("1234.56")

# Validate date
date = DateValidator.validate("2024-01-31")  # Returns datetime object
```

### Health Monitoring

```python
async with connector:
    health = await connector.health_check()

    print(f"Status: {health.status}")
    print(f"Latency: {health.latency_ms}ms")
    print(f"Message: {health.message}")
    print(f"Details: {health.details}")
```

## Data Models

### TrialBalance

```python
@dataclass
class TrialBalance:
    company_id: str
    company_name: str
    period_start: datetime
    period_end: datetime
    currency: str
    accounts: List[AccountBalance]
    extracted_at: datetime
    metadata: Dict[str, Any]
```

### AccountBalance

```python
@dataclass
class AccountBalance:
    account_code: str
    account_name: str
    account_type: str  # ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE
    parent_account_code: Optional[str]
    level: int
    opening_balance: float
    debit_amount: float
    credit_amount: float
    closing_balance: float
    is_summary: bool
```

### SubledgerEntry

```python
@dataclass
class SubledgerEntry:
    entry_id: str
    transaction_date: datetime
    posting_date: datetime
    account_code: str
    account_name: str
    debit_amount: float
    credit_amount: float
    description: str
    document_number: Optional[str]
    document_type: Optional[str]
    cost_center: Optional[str]
    entity_id: Optional[str]
    entity_name: Optional[str]
    metadata: Dict[str, Any]
```

## Error Handling

The framework provides comprehensive error handling:

```python
from connectors import (
    ValidationError,
    RetryExhaustedError,
    CircuitBreakerOpenError
)
import httpx

try:
    async with connector:
        trial_balance = await connector.get_trial_balance(...)
except ValidationError as e:
    print(f"Data validation failed: {e}")
except RetryExhaustedError as e:
    print(f"All retry attempts failed: {e}")
except CircuitBreakerOpenError as e:
    print(f"Circuit breaker is open: {e}")
except httpx.HTTPError as e:
    print(f"HTTP error: {e}")
```

## Logging

Enable detailed logging:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Now all connector operations will be logged
```

## Testing

### Unit Tests

```bash
pytest tests/test_connectors.py
```

### Integration Tests

```bash
# Set environment variables with test credentials
export TOTVS_CLIENT_ID="test_client_id"
export TOTVS_CLIENT_SECRET="test_client_secret"
export TOTVS_TENANT="test_tenant"

pytest tests/integration/test_totvs.py
```

## Architecture

```
src/connectors/
├── base.py              # Abstract base class and interfaces
├── auth.py              # Authentication handlers
├── retry.py             # Retry logic and rate limiting
├── validation.py        # Data validation
├── factory.py           # Factory pattern
├── totvs_connector.py   # TOTVS Protheus implementation
├── contaazul_connector.py   # ContaAzul implementation
├── omie_connector.py    # Omie implementation
├── bling_connector.py   # Bling implementation
└── README.md            # This file
```

## Portfolio Company Mapping

| Company | ERP System |
|---------|-----------|
| Effecti | TOTVS Protheus |
| OnClick | TOTVS Protheus |
| Mercos | ContaAzul |
| Munddi | ContaAzul |
| Datahub | Omie |
| Ipê Digital | Bling |
| Leadlovers | Bling |

## Best Practices

1. **Always use async context manager** - Ensures proper connection cleanup
2. **Handle errors gracefully** - All methods can raise exceptions
3. **Monitor rate limits** - Each ERP has different rate limits
4. **Validate data** - Use validation functions for custom data
5. **Enable logging** - Use logging for debugging and monitoring
6. **Use circuit breaker** - Prevents cascading failures
7. **Cache authentication tokens** - OAuth handlers cache tokens automatically
8. **Test with sandbox** - Use sandbox environments when available

## Troubleshooting

### Connection Timeouts

Increase timeout in config:

```python
connector = create_connector(
    ...,
    config={
        ...,
        "timeout": 60.0  # seconds
    }
)
```

### Rate Limit Errors

The framework automatically handles rate limiting, but if you're hitting limits:

1. Reduce concurrent requests
2. Increase delay between requests
3. Use batch operations when available
4. Check ERP-specific rate limits

### Authentication Failures

1. Verify credentials are correct
2. Check token expiration
3. Ensure correct auth type for ERP
4. Review API key permissions

### Data Validation Errors

If you receive validation errors:

1. Check the error message for specific field
2. Review ERP-specific data format
3. Use validation functions to test individual fields
4. Check for missing required fields

## Contributing

To add support for a new ERP:

1. Create a new connector class inheriting from `ERPConnector`
2. Implement all abstract methods
3. Add ERP type to `ERPType` enum
4. Register in `ConnectorFactory`
5. Add tests
6. Update documentation

## License

Internal use only - FPA portfolio companies.

## Support

For issues or questions, contact the FPA engineering team.
