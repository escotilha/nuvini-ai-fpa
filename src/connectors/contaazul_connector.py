"""
ContaAzul ERP Connector

Implementation for ContaAzul API integration.
Used by: Mercos, Munddi
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
    AccountTypeValidator
)


class ContaAzulConnector(ERPConnector):
    """
    Connector for ContaAzul ERP system.

    API Documentation: https://developers.contaazul.com/
    """

    def __init__(
        self,
        credentials: ERPCredentials,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(credentials, config)

        self.base_url = config.get("base_url", "https://api.contaazul.com")
        self.api_version = config.get("api_version", "v1")

        # Initialize auth handler
        auth_config = {
            "token_url": f"{self.base_url}/auth/authorize",
        }
        self.auth_handler: AuthHandler = create_auth_handler(
            credentials.auth_type.value,
            credentials.credentials,
            auth_config
        )

        # Rate limiter: ContaAzul allows 60 requests per minute
        self.rate_limiter = RateLimiter(rate=60, per=60.0)

        self.client: Optional[httpx.AsyncClient] = None

    @property
    def erp_type(self) -> ERPType:
        return ERPType.CONTAAZUL

    @property
    def supported_auth_types(self) -> List[AuthType]:
        return [AuthType.OAUTH2]

    async def connect(self) -> bool:
        """Establish connection to ContaAzul"""
        try:
            self.client = httpx.AsyncClient(
                base_url=f"{self.base_url}/{self.api_version}",
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
                self.logger.info("Connected to ContaAzul")

            return self._is_connected

        except Exception as e:
            self.logger.error(f"Failed to connect to ContaAzul: {e}")
            self._is_connected = False
            return False

    async def disconnect(self) -> bool:
        """Disconnect from ContaAzul"""
        if self.client:
            await self.client.aclose()
            self.client = None

        self._is_connected = False
        self.logger.info("Disconnected from ContaAzul")
        return True

    @with_retry(RetryConfig(max_attempts=3))
    async def health_check(self) -> HealthCheckResult:
        """Check ContaAzul API health"""
        import time
        start_time = time.time()

        try:
            headers = await self.auth_handler.get_headers()

            # ContaAzul doesn't have a dedicated health endpoint
            # Use company info as health check
            response = await self.client.get(
                "/company",
                headers=headers,
            )

            latency_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                return HealthCheckResult(
                    status=ConnectionStatus.HEALTHY,
                    timestamp=datetime.now(timezone.utc),
                    latency_ms=latency_ms,
                    message="ContaAzul API is healthy",
                    details={"company": response.json()},
                )
            else:
                return HealthCheckResult(
                    status=ConnectionStatus.DEGRADED,
                    timestamp=datetime.now(timezone.utc),
                    latency_ms=latency_ms,
                    message=f"ContaAzul API returned status {response.status_code}",
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
        """Get company information (ContaAzul typically has one company per account)"""
        await self.rate_limiter.acquire()

        headers = await self.auth_handler.get_headers()

        response = await self.client.get(
            "/company",
            headers=headers,
        )
        response.raise_for_status()

        company = response.json()
        return [{
            "id": company.get("id"),
            "name": company.get("name"),
            "document": company.get("cnpj"),
            "trading_name": company.get("tradingName"),
        }]

    async def get_chart_of_accounts(
        self,
        company_id: str
    ) -> List[Dict[str, Any]]:
        """Get chart of accounts"""
        await self.rate_limiter.acquire()

        headers = await self.auth_handler.get_headers()

        response = await self.client.get(
            "/accounts",
            headers=headers,
        )
        response.raise_for_status()

        accounts = response.json()
        return accounts

    @with_retry(RetryConfig(max_attempts=3))
    async def get_trial_balance(
        self,
        company_id: str,
        period_start: datetime,
        period_end: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> TrialBalance:
        """Extract trial balance from ContaAzul"""
        await self.rate_limiter.acquire()

        headers = await self.auth_handler.get_headers()

        # ContaAzul uses different format for dates
        params = {
            "start_date": period_start.strftime("%Y-%m-%d"),
            "end_date": period_end.strftime("%Y-%m-%d"),
        }

        # ContaAzul doesn't have a direct trial balance endpoint
        # We need to aggregate from transactions
        response = await self.client.get(
            "/financial/transactions",
            headers=headers,
            params=params,
        )
        response.raise_for_status()

        raw_data = response.json()

        # Get chart of accounts
        accounts_response = await self.client.get(
            "/accounts",
            headers=headers,
        )
        accounts_response.raise_for_status()
        chart = accounts_response.json()

        # Aggregate transactions by account
        account_balances = self._aggregate_transactions(
            raw_data,
            chart,
            period_start,
            period_end
        )

        # Get company info
        companies = await self.get_companies()
        company = companies[0] if companies else {}
        company_name = company.get("name", company_id)

        trial_balance_data = {
            "company_id": company_id,
            "company_name": company_name,
            "period_start": period_start,
            "period_end": period_end,
            "currency": "BRL",
            "accounts": account_balances,
            "metadata": {
                "source": "ContaAzul",
                "aggregated_from_transactions": True,
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
        """Extract subledger details from ContaAzul"""
        await self.rate_limiter.acquire()

        headers = await self.auth_handler.get_headers()

        params = {
            "start_date": period_start.strftime("%Y-%m-%d"),
            "end_date": period_end.strftime("%Y-%m-%d"),
            "account_id": account_code,
        }

        response = await self.client.get(
            "/financial/transactions",
            headers=headers,
            params=params,
        )
        response.raise_for_status()

        raw_data = response.json()

        # Transform to standard format
        entries = []
        for item in raw_data:
            # ContaAzul transactions can be payment, receipt, or transfer
            is_debit = item.get("type") in ["payment", "expense"]

            entry = {
                "entry_id": str(item.get("id")),
                "transaction_date": item.get("date"),
                "posting_date": item.get("payment_date", item.get("date")),
                "account_code": account_code,
                "account_name": item.get("category", {}).get("name", ""),
                "debit_amount": item.get("value", 0) if is_debit else 0,
                "credit_amount": item.get("value", 0) if not is_debit else 0,
                "description": item.get("description", ""),
                "document_number": item.get("document_number"),
                "document_type": item.get("type"),
                "cost_center": item.get("cost_center", {}).get("name") if item.get("cost_center") else None,
                "entity_id": item.get("customer_supplier", {}).get("id") if item.get("customer_supplier") else None,
                "entity_name": item.get("customer_supplier", {}).get("name") if item.get("customer_supplier") else None,
                "metadata": {
                    "status": item.get("status"),
                    "payment_method": item.get("payment_method"),
                }
            }

            validated_entry = SubledgerValidator.validate(entry)
            entries.append(SubledgerEntry(**validated_entry))

        return entries

    def _aggregate_transactions(
        self,
        transactions: List[Dict[str, Any]],
        chart: List[Dict[str, Any]],
        period_start: datetime,
        period_end: datetime
    ) -> List[Dict[str, Any]]:
        """Aggregate transactions into account balances"""
        from collections import defaultdict
        from decimal import Decimal

        # Build account map
        account_map = {acc["id"]: acc for acc in chart}

        # Aggregate by account
        balances = defaultdict(lambda: {
            "debit_amount": Decimal("0"),
            "credit_amount": Decimal("0"),
        })

        for txn in transactions:
            category = txn.get("category", {})
            account_id = category.get("id")

            if not account_id or account_id not in account_map:
                continue

            amount = Decimal(str(txn.get("value", 0)))
            is_debit = txn.get("type") in ["payment", "expense"]

            if is_debit:
                balances[account_id]["debit_amount"] += amount
            else:
                balances[account_id]["credit_amount"] += amount

        # Convert to account balance format
        result = []
        for account_id, balance in balances.items():
            account_info = account_map[account_id]

            account_type = self._map_account_type(account_info.get("type"))

            closing_balance = (
                balance["debit_amount"] - balance["credit_amount"]
                if account_type in ["ASSET", "EXPENSE"]
                else balance["credit_amount"] - balance["debit_amount"]
            )

            result.append({
                "account_code": str(account_id),
                "account_name": account_info.get("name", ""),
                "account_type": account_type,
                "parent_account_code": None,
                "level": 1,
                "opening_balance": 0,  # ContaAzul doesn't provide opening balance
                "debit_amount": float(balance["debit_amount"]),
                "credit_amount": float(balance["credit_amount"]),
                "closing_balance": float(closing_balance),
                "is_summary": False,
            })

        return result

    def _map_account_type(self, contaazul_type: str) -> str:
        """Map ContaAzul account type to standard type"""
        mapping = {
            "ASSET": "ASSET",
            "LIABILITY": "LIABILITY",
            "EQUITY": "EQUITY",
            "REVENUE": "REVENUE",
            "INCOME": "REVENUE",
            "EXPENSE": "EXPENSE",
            "COST": "EXPENSE",
        }
        normalized = (contaazul_type or "").upper()
        return mapping.get(normalized, "ASSET")
