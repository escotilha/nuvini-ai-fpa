"""
Base ERP Connector Framework

Provides abstract base classes and interfaces for connecting to various Brazilian ERP systems.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import logging


logger = logging.getLogger(__name__)


class ERPType(Enum):
    """Supported ERP types"""
    TOTVS_PROTHEUS = "totvs_protheus"
    CONTAAZUL = "contaazul"
    OMIE = "omie"
    BLING = "bling"


class AuthType(Enum):
    """Supported authentication methods"""
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    BASIC_AUTH = "basic_auth"
    BEARER_TOKEN = "bearer_token"


class ConnectionStatus(Enum):
    """Connection health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DISCONNECTED = "disconnected"


@dataclass
class ERPCredentials:
    """Base credentials structure"""
    auth_type: AuthType
    credentials: Dict[str, str]
    environment: str = "production"  # production or sandbox

    def validate(self) -> bool:
        """Validate that required credential fields are present"""
        required_fields = {
            AuthType.OAUTH2: ["client_id", "client_secret"],
            AuthType.API_KEY: ["api_key"],
            AuthType.BASIC_AUTH: ["username", "password"],
            AuthType.BEARER_TOKEN: ["token"],
        }

        required = required_fields.get(self.auth_type, [])
        return all(field in self.credentials for field in required)


@dataclass
class TrialBalance:
    """Standard trial balance format"""
    company_id: str
    company_name: str
    period_start: datetime
    period_end: datetime
    currency: str
    accounts: List['AccountBalance']
    extracted_at: datetime
    metadata: Dict[str, Any]


@dataclass
class AccountBalance:
    """Individual account balance"""
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


@dataclass
class SubledgerEntry:
    """Subledger transaction detail"""
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
    entity_id: Optional[str]  # customer/vendor ID
    entity_name: Optional[str]
    metadata: Dict[str, Any]


@dataclass
class HealthCheckResult:
    """Connection health check result"""
    status: ConnectionStatus
    timestamp: datetime
    latency_ms: float
    message: str
    details: Dict[str, Any]


class ERPConnector(ABC):
    """
    Abstract base class for all ERP connectors.

    Each ERP-specific implementation must override these methods.
    """

    def __init__(self, credentials: ERPCredentials, config: Optional[Dict[str, Any]] = None):
        """
        Initialize connector with credentials and optional configuration.

        Args:
            credentials: Authentication credentials
            config: Additional configuration (rate limits, timeouts, etc.)
        """
        if not credentials.validate():
            raise ValueError(f"Invalid credentials for {credentials.auth_type}")

        self.credentials = credentials
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._is_connected = False

    @property
    @abstractmethod
    def erp_type(self) -> ERPType:
        """Return the ERP type this connector handles"""
        pass

    @property
    @abstractmethod
    def supported_auth_types(self) -> List[AuthType]:
        """Return list of supported authentication methods"""
        pass

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the ERP system.

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Gracefully disconnect from the ERP system.

        Returns:
            True if disconnection successful, False otherwise
        """
        pass

    @abstractmethod
    async def health_check(self) -> HealthCheckResult:
        """
        Check connection health and API availability.

        Returns:
            HealthCheckResult with status and metrics
        """
        pass

    @abstractmethod
    async def get_trial_balance(
        self,
        company_id: str,
        period_start: datetime,
        period_end: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> TrialBalance:
        """
        Extract trial balance for specified period.

        Args:
            company_id: Company/branch identifier
            period_start: Start of accounting period
            period_end: End of accounting period
            filters: Optional filters (account ranges, cost centers, etc.)

        Returns:
            TrialBalance object with standardized format
        """
        pass

    @abstractmethod
    async def get_subledger_details(
        self,
        company_id: str,
        account_code: str,
        period_start: datetime,
        period_end: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SubledgerEntry]:
        """
        Extract detailed subledger entries for an account.

        Args:
            company_id: Company/branch identifier
            account_code: Specific account to extract
            period_start: Start of period
            period_end: End of period
            filters: Optional filters (document types, entities, etc.)

        Returns:
            List of SubledgerEntry objects
        """
        pass

    @abstractmethod
    async def get_companies(self) -> List[Dict[str, Any]]:
        """
        Get list of companies/branches accessible with current credentials.

        Returns:
            List of company dictionaries with id, name, etc.
        """
        pass

    @abstractmethod
    async def get_chart_of_accounts(
        self,
        company_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get chart of accounts structure.

        Args:
            company_id: Company identifier

        Returns:
            List of account dictionaries with code, name, type, level, etc.
        """
        pass

    def is_connected(self) -> bool:
        """Check if connector is currently connected"""
        return self._is_connected

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
        return False
