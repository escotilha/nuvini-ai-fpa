"""
TOTVS Protheus ERP Connector

Implementation for TOTVS Protheus REST API integration.
Used by: Effecti, OnClick
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from .base import (
    ERPConnector, ERPType, ERPCredentials, AuthType,
    TrialBalance, AccountBalance, SubledgerEntry,
    HealthCheckResult, ConnectionStatus
)
from .auth import create_auth_handler, AuthHandler
from .retry import with_retry, RetryConfig, RateLimiter
from .validation import (
    TrialBalanceValidator, SubledgerValidator,
    AccountCodeValidator, DateValidator, AmountValidator
)


class TOTVSProtheusConnector(ERPConnector):
    """
    Connector for TOTVS Protheus ERP system.

    API Documentation: https://tdn.totvs.com/display/public/PROT/REST
    """

    def __init__(
        self,
        credentials: ERPCredentials,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(credentials, config)

        # TOTVS-specific configuration
        self.base_url = config.get("base_url", "https://api.totvs.com.br")
        self.tenant = config.get("tenant")
        self.environment = config.get("environment", "PRODUCAO")

        if not self.tenant:
            raise ValueError("tenant is required for TOTVS Protheus")

        # Initialize auth handler
        auth_config = {
            "token_url": f"{self.base_url}/api/oauth2/v1/token",
        }
        self.auth_handler: AuthHandler = create_auth_handler(
            credentials.auth_type.value,
            credentials.credentials,
            auth_config
        )

        # Rate limiter: TOTVS allows 100 requests per minute
        self.rate_limiter = RateLimiter(rate=100, per=60.0)

        self.client: Optional[httpx.AsyncClient] = None

    @property
    def erp_type(self) -> ERPType:
        return ERPType.TOTVS_PROTHEUS

    @property
    def supported_auth_types(self) -> List[AuthType]:
        return [AuthType.OAUTH2, AuthType.BEARER_TOKEN]

    async def connect(self) -> bool:
        """Establish connection to TOTVS Protheus"""
        try:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
            )

            # Test connection
            health = await self.health_check()
            self._is_connected = health.status in [
                ConnectionStatus.HEALTHY,
                ConnectionStatus.DEGRADED
            ]

            if self._is_connected:
                self.logger.info(f"Connected to TOTVS Protheus (tenant: {self.tenant})")

            return self._is_connected

        except Exception as e:
            self.logger.error(f"Failed to connect to TOTVS Protheus: {e}")
            self._is_connected = False
            return False

    async def disconnect(self) -> bool:
        """Disconnect from TOTVS Protheus"""
        if self.client:
            await self.client.aclose()
            self.client = None

        self._is_connected = False
        self.logger.info("Disconnected from TOTVS Protheus")
        return True

    @with_retry(RetryConfig(max_attempts=3))
    async def health_check(self) -> HealthCheckResult:
        """Check TOTVS Protheus API health"""
        import time
        start_time = time.time()

        try:
            headers = await self.auth_handler.get_headers()
            headers.update({
                "tenantId": self.tenant,
            })

            response = await self.client.get(
                "/api/framework/v1/health",
                headers=headers,
            )

            latency_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                return HealthCheckResult(
                    status=ConnectionStatus.HEALTHY,
                    timestamp=datetime.now(timezone.utc),
                    latency_ms=latency_ms,
                    message="TOTVS Protheus API is healthy",
                    details=response.json(),
                )
            else:
                return HealthCheckResult(
                    status=ConnectionStatus.DEGRADED,
                    timestamp=datetime.now(timezone.utc),
                    latency_ms=latency_ms,
                    message=f"TOTVS API returned status {response.status_code}",
                    details={"status_code": response.status_code},
                )

        except Exception as e:
            return HealthCheckResult(
                status=ConnectionStatus.UNHEALTHY,
                timestamp=datetime.now(timezone.utc),
                latency_ms=(time.time() - start_time) * 1000,
                message=f"Health check failed: {e}",
                details={"error": str(e)},
            )

    async def get_companies(self) -> List[Dict[str, Any]]:
        """Get list of companies/branches"""
        await self.rate_limiter.acquire()

        headers = await self.auth_handler.get_headers()
        headers.update({"tenantId": self.tenant})

        response = await self.client.get(
            "/api/ctb/v1/companies",
            headers=headers,
        )
        response.raise_for_status()

        data = response.json()
        return data.get("items", [])

    async def get_chart_of_accounts(
        self,
        company_id: str
    ) -> List[Dict[str, Any]]:
        """Get chart of accounts"""
        await self.rate_limiter.acquire()

        headers = await self.auth_handler.get_headers()
        headers.update({
            "tenantId": self.tenant,
            "companyId": company_id,
        })

        response = await self.client.get(
            "/api/ctb/v1/chartofaccounts",
            headers=headers,
        )
        response.raise_for_status()

        data = response.json()
        return data.get("items", [])

    @with_retry(RetryConfig(max_attempts=3))
    async def get_trial_balance(
        self,
        company_id: str,
        period_start: datetime,
        period_end: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> TrialBalance:
        """Extract trial balance from TOTVS Protheus"""
        await self.rate_limiter.acquire()

        headers = await self.auth_handler.get_headers()
        headers.update({
            "tenantId": self.tenant,
            "companyId": company_id,
        })

        params = {
            "startDate": period_start.strftime("%Y%m%d"),
            "endDate": period_end.strftime("%Y%m%d"),
        }

        if filters:
            if "account_range" in filters:
                params["accountFrom"] = filters["account_range"]["from"]
                params["accountTo"] = filters["account_range"]["to"]
            if "cost_center" in filters:
                params["costCenter"] = filters["cost_center"]

        response = await self.client.get(
            "/api/ctb/v1/trialbalance",
            headers=headers,
            params=params,
        )
        response.raise_for_status()

        raw_data = response.json()

        # Transform TOTVS format to standard format
        accounts = []
        for item in raw_data.get("items", []):
            account = {
                "account_code": item.get("accountCode"),
                "account_name": item.get("accountName"),
                "account_type": self._map_account_type(item.get("accountType")),
                "parent_account_code": item.get("parentAccount"),
                "level": item.get("level", 1),
                "opening_balance": item.get("openingBalance", 0),
                "debit_amount": item.get("debitAmount", 0),
                "credit_amount": item.get("creditAmount", 0),
                "closing_balance": item.get("closingBalance", 0),
                "is_summary": item.get("isSynthetic", False),
            }
            accounts.append(account)

        # Get company name
        company_info = raw_data.get("company", {})
        company_name = company_info.get("name", company_id)

        trial_balance_data = {
            "company_id": company_id,
            "company_name": company_name,
            "period_start": period_start,
            "period_end": period_end,
            "currency": "BRL",
            "accounts": accounts,
            "metadata": {
                "source": "TOTVS Protheus",
                "tenant": self.tenant,
                "environment": self.environment,
            }
        }

        # Validate
        validated_data = TrialBalanceValidator.validate(trial_balance_data)

        # Convert account dicts to AccountBalance objects
        account_objects = [AccountBalance(**acc) for acc in validated_data["accounts"]]
        validated_data["accounts"] = account_objects

        return TrialBalance(**validated_data)

    @with_retry(RetryConfig(max_attempts=3))
    async def get_subledger_details(
        self,
        company_id: str,
        account_code: str,
        period_start: datetime,
        period_end: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SubledgerEntry]:
        """Extract subledger details from TOTVS Protheus"""
        await self.rate_limiter.acquire()

        headers = await self.auth_handler.get_headers()
        headers.update({
            "tenantId": self.tenant,
            "companyId": company_id,
        })

        params = {
            "accountCode": account_code,
            "startDate": period_start.strftime("%Y%m%d"),
            "endDate": period_end.strftime("%Y%m%d"),
        }

        if filters:
            if "cost_center" in filters:
                params["costCenter"] = filters["cost_center"]
            if "document_type" in filters:
                params["documentType"] = filters["document_type"]

        response = await self.client.get(
            "/api/ctb/v1/ledgerentries",
            headers=headers,
            params=params,
        )
        response.raise_for_status()

        raw_data = response.json()

        # Transform to standard format
        entries = []
        for item in raw_data.get("items", []):
            entry = {
                "entry_id": item.get("id"),
                "transaction_date": item.get("transactionDate"),
                "posting_date": item.get("postingDate", item.get("transactionDate")),
                "account_code": item.get("accountCode"),
                "account_name": item.get("accountName"),
                "debit_amount": item.get("debitValue", 0),
                "credit_amount": item.get("creditValue", 0),
                "description": item.get("history", ""),
                "document_number": item.get("documentNumber"),
                "document_type": item.get("documentType"),
                "cost_center": item.get("costCenter"),
                "entity_id": item.get("entityCode"),
                "entity_name": item.get("entityName"),
                "metadata": {
                    "batch": item.get("batchNumber"),
                    "sequence": item.get("sequenceNumber"),
                }
            }

            validated_entry = SubledgerValidator.validate(entry)
            entries.append(SubledgerEntry(**validated_entry))

        return entries

    def _map_account_type(self, totvs_type: str) -> str:
        """Map TOTVS account type to standard type"""
        mapping = {
            "1": "ASSET",      # Ativo
            "2": "LIABILITY",  # Passivo
            "3": "EQUITY",     # Patrimônio Líquido
            "4": "REVENUE",    # Receita
            "5": "EXPENSE",    # Despesa/Custo
        }
        return mapping.get(totvs_type, "ASSET")
