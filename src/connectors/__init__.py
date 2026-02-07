"""
ERP Connector Framework

A reusable framework for connecting to Brazilian ERP systems used by FPA portfolio companies.

Supported ERP Systems:
- TOTVS Protheus (Effecti, OnClick)
- ContaAzul (Mercos, Munddi)
- Omie (Datahub)
- Bling (Ipê Digital, Leadlovers)

Quick Start:
    from connectors import create_connector, ERPType, AuthType

    # Create a connector
    connector = create_connector(
        erp_type="totvs_protheus",
        auth_type="oauth2",
        credentials={
            "client_id": "your_client_id",
            "client_secret": "your_client_secret"
        },
        config={
            "tenant": "your_tenant"
        }
    )

    # Use async context manager
    async with connector:
        # Get trial balance
        trial_balance = await connector.get_trial_balance(
            company_id="01",
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 12, 31)
        )

        # Get subledger details
        entries = await connector.get_subledger_details(
            company_id="01",
            account_code="1.01.001",
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 12, 31)
        )
"""

from .base import (
    ERPConnector,
    ERPType,
    AuthType,
    ConnectionStatus,
    ERPCredentials,
    TrialBalance,
    AccountBalance,
    SubledgerEntry,
    HealthCheckResult,
)

from .factory import (
    ConnectorFactory,
    create_connector,
    get_erp_for_company,
    PORTFOLIO_COMPANY_ERP_MAPPING,
)

from .totvs_connector import TOTVSProtheusConnector
from .contaazul_connector import ContaAzulConnector
from .omie_connector import OmieConnector
from .bling_connector import BlingConnector

from .auth import (
    AuthHandler,
    OAuth2Handler,
    APIKeyHandler,
    BasicAuthHandler,
    BearerTokenHandler,
    create_auth_handler,
)

from .retry import (
    RetryConfig,
    RetryStrategy,
    RateLimiter,
    CircuitBreaker,
    retry_async,
    with_retry,
    RetryExhaustedError,
    CircuitBreakerOpenError,
)

from .validation import (
    ValidationError,
    AccountTypeValidator,
    AccountCodeValidator,
    AmountValidator,
    DateValidator,
    CurrencyValidator,
    TrialBalanceValidator,
    SubledgerValidator,
)


__version__ = "1.0.0"

__all__ = [
    # Base classes and enums
    "ERPConnector",
    "ERPType",
    "AuthType",
    "ConnectionStatus",
    "ERPCredentials",
    "TrialBalance",
    "AccountBalance",
    "SubledgerEntry",
    "HealthCheckResult",

    # Factory
    "ConnectorFactory",
    "create_connector",
    "get_erp_for_company",
    "PORTFOLIO_COMPANY_ERP_MAPPING",

    # Connectors
    "TOTVSProtheusConnector",
    "ContaAzulConnector",
    "OmieConnector",
    "BlingConnector",

    # Auth
    "AuthHandler",
    "OAuth2Handler",
    "APIKeyHandler",
    "BasicAuthHandler",
    "BearerTokenHandler",
    "create_auth_handler",

    # Retry
    "RetryConfig",
    "RetryStrategy",
    "RateLimiter",
    "CircuitBreaker",
    "retry_async",
    "with_retry",
    "RetryExhaustedError",
    "CircuitBreakerOpenError",

    # Validation
    "ValidationError",
    "AccountTypeValidator",
    "AccountCodeValidator",
    "AmountValidator",
    "DateValidator",
    "CurrencyValidator",
    "TrialBalanceValidator",
    "SubledgerValidator",
]
