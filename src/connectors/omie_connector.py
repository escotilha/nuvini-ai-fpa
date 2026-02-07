"""
Omie ERP Connector

Implementation for Omie API integration.
Used by: Datahub
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


class OmieConnector(ERPConnector):
    """
    Connector for Omie ERP system.

    API Documentation: https://developer.omie.com.br/
    """

    def __init__(
        self,
        credentials: ERPCredentials,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(credentials, config)

        self.base_url = config.get("base_url", "https://app.omie.com.br/api/v1")

        # Omie uses app_key and app_secret for authentication
        self.app_key = credentials.credentials.get("api_key") or credentials.credentials.get("app_key")
        self.app_secret = credentials.credentials.get("app_secret")

        if not self.app_key or not self.app_secret:
            raise ValueError("app_key and app_secret are required for Omie")

        # Rate limiter: Omie allows 300 requests per minute
        self.rate_limiter = RateLimiter(rate=300, per=60.0)

        self.client: Optional[httpx.AsyncClient] = None

    @property
    def erp_type(self) -> ERPType:
        return ERPType.OMIE

    @property
    def supported_auth_types(self) -> List[AuthType]:
        return [AuthType.API_KEY]

    async def connect(self) -> bool:
        """Establish connection to Omie"""
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
                self.logger.info("Connected to Omie")

            return self._is_connected

        except Exception as e:
            self.logger.error(f"Failed to connect to Omie: {e}")
            self._is_connected = False
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Omie"""
        if self.client:
            await self.client.aclose()
            self.client = None

        self._is_connected = False
        self.logger.info("Disconnected from Omie")
        return True

    async def _make_request(
        self,
        endpoint: str,
        call: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Omie API"""
        await self.rate_limiter.acquire()

        payload = {
            "call": call,
            "app_key": self.app_key,
            "app_secret": self.app_secret,
            "param": [params or {}]
        }

        response = await self.client.post(
            endpoint,
            json=payload,
        )
        response.raise_for_status()

        return response.json()

    @with_retry(RetryConfig(max_attempts=3))
    async def health_check(self) -> HealthCheckResult:
        """Check Omie API health"""
        import time
        start_time = time.time()

        try:
            # Use company info as health check
            await self._make_request(
                "/geral/empresas/",
                "ListarEmpresas",
                {}
            )

            latency_ms = (time.time() - start_time) * 1000

            return HealthCheckResult(
                status=ConnectionStatus.HEALTHY,
                timestamp=datetime.now(timezone.utc),
                latency_ms=latency_ms,
                message="Omie API is healthy",
                details={},
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
        """Get list of companies"""
        data = await self._make_request(
            "/geral/empresas/",
            "ListarEmpresas",
            {}
        )

        companies = []
        for company in data:
            companies.append({
                "id": str(company.get("codigo_empresa")),
                "name": company.get("razao_social"),
                "trading_name": company.get("nome_fantasia"),
                "document": company.get("cnpj"),
            })

        return companies

    async def get_chart_of_accounts(
        self,
        company_id: str
    ) -> List[Dict[str, Any]]:
        """Get chart of accounts"""
        data = await self._make_request(
            "/geral/contacorrente/",
            "ListarContasCorrentes",
            {"nCodEmpresa": int(company_id)}
        )

        accounts = []
        for account in data.get("conta_corrente_lista", []):
            accounts.append({
                "id": str(account.get("nCodCC")),
                "code": account.get("cCodigo"),
                "name": account.get("cDescricao"),
                "type": account.get("cTipo"),
            })

        return accounts

    @with_retry(RetryConfig(max_attempts=3))
    async def get_trial_balance(
        self,
        company_id: str,
        period_start: datetime,
        period_end: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> TrialBalance:
        """Extract trial balance from Omie"""
        # Omie uses a different endpoint for financial reports
        params = {
            "nCodEmpresa": int(company_id),
            "dDtIni": period_start.strftime("%d/%m/%Y"),
            "dDtFim": period_end.strftime("%d/%m/%Y"),
        }

        data = await self._make_request(
            "/geral/contacorrente/",
            "ListarSaldoContaCorrente",
            params
        )

        # Get chart of accounts for mapping
        chart = await self.get_chart_of_accounts(company_id)
        account_map = {acc["id"]: acc for acc in chart}

        # Transform to standard format
        accounts = []
        for item in data.get("lista_saldos", []):
            account_id = str(item.get("nCodCC"))
            account_info = account_map.get(account_id, {})

            # Omie provides balance information
            opening_balance = item.get("nSaldoInicial", 0)
            debit = item.get("nDebito", 0)
            credit = item.get("nCredito", 0)
            closing_balance = item.get("nSaldoFinal", 0)

            account = {
                "account_code": account_info.get("code", account_id),
                "account_name": account_info.get("name", ""),
                "account_type": self._map_account_type(account_info.get("type")),
                "parent_account_code": None,
                "level": 1,
                "opening_balance": opening_balance,
                "debit_amount": debit,
                "credit_amount": credit,
                "closing_balance": closing_balance,
                "is_summary": False,
            }
            accounts.append(account)

        # Get company name
        companies = await self.get_companies()
        company = next(
            (c for c in companies if c["id"] == company_id),
            {"name": company_id}
        )
        company_name = company.get("name", company_id)

        trial_balance_data = {
            "company_id": company_id,
            "company_name": company_name,
            "period_start": period_start,
            "period_end": period_end,
            "currency": "BRL",
            "accounts": accounts,
            "metadata": {
                "source": "Omie",
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
        """Extract subledger details from Omie"""
        # Get chart of accounts to find account ID
        chart = await self.get_chart_of_accounts(company_id)
        account = next(
            (acc for acc in chart if acc["code"] == account_code),
            None
        )

        if not account:
            raise ValueError(f"Account {account_code} not found")

        account_id = int(account["id"])

        params = {
            "nCodEmpresa": int(company_id),
            "nCodCC": account_id,
            "dDtIni": period_start.strftime("%d/%m/%Y"),
            "dDtFim": period_end.strftime("%d/%m/%Y"),
        }

        data = await self._make_request(
            "/geral/contacorrente/",
            "ListarExtrato",
            params
        )

        # Transform to standard format
        entries = []
        for item in data.get("extrato", []):
            entry = {
                "entry_id": str(item.get("nCodLanc")),
                "transaction_date": item.get("dDtLanc"),
                "posting_date": item.get("dDtLanc"),
                "account_code": account_code,
                "account_name": account.get("name", ""),
                "debit_amount": item.get("nDebito", 0),
                "credit_amount": item.get("nCredito", 0),
                "description": item.get("cHistorico", ""),
                "document_number": item.get("cNumDoc"),
                "document_type": item.get("cTipoDoc"),
                "cost_center": None,
                "entity_id": str(item.get("nCodTerceiro")) if item.get("nCodTerceiro") else None,
                "entity_name": item.get("cNomeTerceiro"),
                "metadata": {
                    "operation": item.get("cOperacao"),
                }
            }

            validated_entry = SubledgerValidator.validate(entry)
            entries.append(SubledgerEntry(**validated_entry))

        return entries

    def _map_account_type(self, omie_type: str) -> str:
        """Map Omie account type to standard type"""
        mapping = {
            "REC": "REVENUE",      # Receita
            "DES": "EXPENSE",      # Despesa
            "BAN": "ASSET",        # Banco
            "OUT": "ASSET",        # Outros ativos
        }
        return mapping.get(omie_type, "ASSET")
