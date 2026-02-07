"""
Bling ERP Connector

Implementation for Bling API integration.
Used by: Ipê Digital, Leadlovers
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
import xml.etree.ElementTree as ET

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


class BlingConnector(ERPConnector):
    """
    Connector for Bling ERP system.

    API Documentation: https://manualdoapi.bling.com.br/
    Note: Bling API uses XML format for most endpoints.
    """

    def __init__(
        self,
        credentials: ERPCredentials,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(credentials, config)

        # Bling has different API versions
        self.api_version = config.get("api_version", "3")  # v3 is JSON, v2 is XML

        if self.api_version == "3":
            self.base_url = config.get("base_url", "https://api.bling.com.br/Api/v3")
        else:
            self.base_url = config.get("base_url", "https://bling.com.br/Api/v2")

        # Bling uses API key
        self.api_key = credentials.credentials.get("api_key")

        if not self.api_key:
            raise ValueError("api_key is required for Bling")

        # Rate limiter: Bling allows 100 requests per minute
        self.rate_limiter = RateLimiter(rate=100, per=60.0)

        self.client: Optional[httpx.AsyncClient] = None

    @property
    def erp_type(self) -> ERPType:
        return ERPType.BLING

    @property
    def supported_auth_types(self) -> List[AuthType]:
        return [AuthType.API_KEY, AuthType.OAUTH2]

    async def connect(self) -> bool:
        """Establish connection to Bling"""
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
                self.logger.info(f"Connected to Bling (API v{self.api_version})")

            return self._is_connected

        except Exception as e:
            self.logger.error(f"Failed to connect to Bling: {e}")
            self._is_connected = False
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Bling"""
        if self.client:
            await self.client.aclose()
            self.client = None

        self._is_connected = False
        self.logger.info("Disconnected from Bling")
        return True

    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET"
    ) -> Any:
        """Make authenticated request to Bling API"""
        await self.rate_limiter.acquire()

        request_params = params or {}
        request_params["apikey"] = self.api_key

        if method == "GET":
            response = await self.client.get(endpoint, params=request_params)
        elif method == "POST":
            response = await self.client.post(endpoint, params=request_params)
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status()

        # API v3 returns JSON, v2 returns XML
        if self.api_version == "3":
            return response.json()
        else:
            return ET.fromstring(response.content)

    @with_retry(RetryConfig(max_attempts=3))
    async def health_check(self) -> HealthCheckResult:
        """Check Bling API health"""
        import time
        start_time = time.time()

        try:
            # Use company info as health check
            if self.api_version == "3":
                await self._make_request("/empresas")
            else:
                await self._make_request("/empresa")

            latency_ms = (time.time() - start_time) * 1000

            return HealthCheckResult(
                status=ConnectionStatus.HEALTHY,
                timestamp=datetime.now(timezone.utc),
                latency_ms=latency_ms,
                message="Bling API is healthy",
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
        """Get company information"""
        if self.api_version == "3":
            data = await self._make_request("/empresas")
            companies = []
            for company in data.get("data", []):
                companies.append({
                    "id": str(company.get("id")),
                    "name": company.get("nome"),
                    "document": company.get("cnpj"),
                })
            return companies
        else:
            root = await self._make_request("/empresa")
            empresa = root.find(".//empresa")
            return [{
                "id": "1",  # Bling v2 typically has single company
                "name": empresa.findtext("nome", ""),
                "document": empresa.findtext("cnpj", ""),
            }]

    async def get_chart_of_accounts(
        self,
        company_id: str
    ) -> List[Dict[str, Any]]:
        """Get chart of accounts"""
        if self.api_version == "3":
            data = await self._make_request("/contabeis/plano-contas")
            return data.get("data", [])
        else:
            # Bling v2 doesn't have a direct chart of accounts endpoint
            # Need to extract from financial transactions
            self.logger.warning("Chart of accounts not available in Bling v2")
            return []

    @with_retry(RetryConfig(max_attempts=3))
    async def get_trial_balance(
        self,
        company_id: str,
        period_start: datetime,
        period_end: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> TrialBalance:
        """Extract trial balance from Bling"""
        if self.api_version == "3":
            return await self._get_trial_balance_v3(
                company_id, period_start, period_end, filters
            )
        else:
            return await self._get_trial_balance_v2(
                company_id, period_start, period_end, filters
            )

    async def _get_trial_balance_v3(
        self,
        company_id: str,
        period_start: datetime,
        period_end: datetime,
        filters: Optional[Dict[str, Any]]
    ) -> TrialBalance:
        """Get trial balance using API v3"""
        params = {
            "dataInicial": period_start.strftime("%Y-%m-%d"),
            "dataFinal": period_end.strftime("%Y-%m-%d"),
        }

        data = await self._make_request("/contabeis/balancete", params)

        # Transform to standard format
        accounts = []
        for item in data.get("data", []):
            account = {
                "account_code": item.get("codigo"),
                "account_name": item.get("descricao"),
                "account_type": self._map_account_type_v3(item.get("tipo")),
                "parent_account_code": item.get("contaPai"),
                "level": item.get("nivel", 1),
                "opening_balance": item.get("saldoInicial", 0),
                "debit_amount": item.get("debito", 0),
                "credit_amount": item.get("credito", 0),
                "closing_balance": item.get("saldoFinal", 0),
                "is_summary": item.get("analitica", True) == False,
            }
            accounts.append(account)

        companies = await self.get_companies()
        company = next(
            (c for c in companies if c["id"] == company_id),
            {"name": company_id}
        )

        trial_balance_data = {
            "company_id": company_id,
            "company_name": company.get("name", company_id),
            "period_start": period_start,
            "period_end": period_end,
            "currency": "BRL",
            "accounts": accounts,
            "metadata": {
                "source": "Bling v3",
            }
        }

        validated_data = TrialBalanceValidator.validate(trial_balance_data)

        # Convert account dicts to AccountBalance objects
        account_objects = [AccountBalance(**acc) for acc in validated_data["accounts"]]
        validated_data["accounts"] = account_objects
        return TrialBalance(**validated_data)

    async def _get_trial_balance_v2(
        self,
        company_id: str,
        period_start: datetime,
        period_end: datetime,
        filters: Optional[Dict[str, Any]]
    ) -> TrialBalance:
        """Get trial balance using API v2 (aggregate from transactions)"""
        # Bling v2 doesn't have direct balancete endpoint
        # Need to aggregate from contas a receber and contas a pagar
        from collections import defaultdict
        from decimal import Decimal

        balances = defaultdict(lambda: {
            "debit": Decimal("0"),
            "credit": Decimal("0"),
        })

        # Get receivables
        params = {
            "filters": f"dataEmissao[{period_start.strftime('%d/%m/%Y')} TO {period_end.strftime('%d/%m/%Y')}]"
        }
        receivables_root = await self._make_request("/contasreceber/json", params)

        if receivables_root.findtext(".//erro") is None:
            for item in receivables_root.findall(".//contareceber"):
                valor = float(item.findtext("valor", "0").replace(",", "."))
                balances["RECEIVABLES"]["debit"] += Decimal(str(valor))

        # Get payables
        payables_root = await self._make_request("/contaspagar/json", params)

        if payables_root.findtext(".//erro") is None:
            for item in payables_root.findall(".//contapagar"):
                valor = float(item.findtext("valor", "0").replace(",", "."))
                balances["PAYABLES"]["credit"] += Decimal(str(valor))

        # Convert to account format
        accounts = []
        account_names = {
            "RECEIVABLES": "Contas a Receber",
            "PAYABLES": "Contas a Pagar",
        }
        account_types = {
            "RECEIVABLES": "ASSET",
            "PAYABLES": "LIABILITY",
        }

        for code, balance in balances.items():
            closing = balance["debit"] - balance["credit"]
            accounts.append({
                "account_code": code,
                "account_name": account_names[code],
                "account_type": account_types[code],
                "parent_account_code": None,
                "level": 1,
                "opening_balance": 0,
                "debit_amount": float(balance["debit"]),
                "credit_amount": float(balance["credit"]),
                "closing_balance": float(closing),
                "is_summary": False,
            })

        companies = await self.get_companies()
        company = companies[0] if companies else {"name": company_id}

        trial_balance_data = {
            "company_id": company_id,
            "company_name": company.get("name", company_id),
            "period_start": period_start,
            "period_end": period_end,
            "currency": "BRL",
            "accounts": accounts,
            "metadata": {
                "source": "Bling v2",
                "aggregated_from_transactions": True,
            }
        }

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
        """Extract subledger details from Bling"""
        if self.api_version == "3":
            return await self._get_subledger_v3(
                company_id, account_code, period_start, period_end, filters
            )
        else:
            return await self._get_subledger_v2(
                company_id, account_code, period_start, period_end, filters
            )

    async def _get_subledger_v3(
        self,
        company_id: str,
        account_code: str,
        period_start: datetime,
        period_end: datetime,
        filters: Optional[Dict[str, Any]]
    ) -> List[SubledgerEntry]:
        """Get subledger using API v3"""
        params = {
            "contaContabil": account_code,
            "dataInicial": period_start.strftime("%Y-%m-%d"),
            "dataFinal": period_end.strftime("%Y-%m-%d"),
        }

        data = await self._make_request("/contabeis/lancamentos", params)

        entries = []
        for item in data.get("data", []):
            entry = {
                "entry_id": str(item.get("id")),
                "transaction_date": item.get("data"),
                "posting_date": item.get("data"),
                "account_code": account_code,
                "account_name": item.get("contaContabil", {}).get("descricao", ""),
                "debit_amount": item.get("valorDebito", 0),
                "credit_amount": item.get("valorCredito", 0),
                "description": item.get("historico", ""),
                "document_number": item.get("numeroDocumento"),
                "document_type": item.get("tipoDocumento"),
                "cost_center": None,
                "entity_id": None,
                "entity_name": None,
                "metadata": {}
            }

            validated_entry = SubledgerValidator.validate(entry)
            entries.append(SubledgerEntry(**validated_entry))

        return entries

    async def _get_subledger_v2(
        self,
        company_id: str,
        account_code: str,
        period_start: datetime,
        period_end: datetime,
        filters: Optional[Dict[str, Any]]
    ) -> List[SubledgerEntry]:
        """Get subledger using API v2"""
        # Limited subledger support in v2
        self.logger.warning("Limited subledger support in Bling v2")
        return []

    def _map_account_type_v3(self, bling_type: str) -> str:
        """Map Bling v3 account type to standard type"""
        mapping = {
            "ATIVO": "ASSET",
            "PASSIVO": "LIABILITY",
            "PATRIMONIO_LIQUIDO": "EQUITY",
            "RECEITA": "REVENUE",
            "DESPESA": "EXPENSE",
            "CUSTO": "EXPENSE",
        }
        return mapping.get(bling_type, "ASSET")
