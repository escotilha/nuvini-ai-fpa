"""
Unit tests for ERP Connector Framework
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

# Import from parent src directory
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from connectors import (
    ERPType, AuthType, ERPCredentials, ConnectionStatus,
    create_connector, ConnectorFactory, get_erp_for_company,
    ValidationError, RetryExhaustedError,
)
from connectors.base import AccountBalance, SubledgerEntry
from connectors.auth import OAuth2Handler, APIKeyHandler, TokenInfo
from connectors.retry import RetryConfig, RateLimiter, calculate_delay, RetryStrategy
from connectors.validation import (
    AccountTypeValidator, AccountCodeValidator,
    AmountValidator, DateValidator, CurrencyValidator,
    TrialBalanceValidator, SubledgerValidator
)


# Test Fixtures

@pytest.fixture
def oauth2_credentials():
    return ERPCredentials(
        auth_type=AuthType.OAUTH2,
        credentials={
            "client_id": "test_client_id",
            "client_secret": "test_client_secret"
        }
    )


@pytest.fixture
def api_key_credentials():
    return ERPCredentials(
        auth_type=AuthType.API_KEY,
        credentials={"api_key": "test_api_key"}
    )


@pytest.fixture
def totvs_config():
    return {
        "base_url": "https://api.totvs.com.br",
        "tenant": "test_tenant"
    }


# Base Tests

class TestERPCredentials:
    """Test credential validation"""

    def test_oauth2_credentials_valid(self):
        creds = ERPCredentials(
            auth_type=AuthType.OAUTH2,
            credentials={
                "client_id": "test_id",
                "client_secret": "test_secret"
            }
        )
        assert creds.validate() is True

    def test_oauth2_credentials_missing_fields(self):
        creds = ERPCredentials(
            auth_type=AuthType.OAUTH2,
            credentials={"client_id": "test_id"}
        )
        assert creds.validate() is False

    def test_api_key_credentials_valid(self):
        creds = ERPCredentials(
            auth_type=AuthType.API_KEY,
            credentials={"api_key": "test_key"}
        )
        assert creds.validate() is True

    def test_basic_auth_credentials_valid(self):
        creds = ERPCredentials(
            auth_type=AuthType.BASIC_AUTH,
            credentials={
                "username": "test_user",
                "password": "test_pass"
            }
        )
        assert creds.validate() is True


# Validation Tests

class TestAccountTypeValidator:
    """Test account type validation and normalization"""

    def test_validate_standard_types(self):
        assert AccountTypeValidator.validate("ASSET") == "ASSET"
        assert AccountTypeValidator.validate("LIABILITY") == "LIABILITY"
        assert AccountTypeValidator.validate("EQUITY") == "EQUITY"
        assert AccountTypeValidator.validate("REVENUE") == "REVENUE"
        assert AccountTypeValidator.validate("EXPENSE") == "EXPENSE"

    def test_validate_portuguese_types(self):
        assert AccountTypeValidator.validate("ATIVO") == "ASSET"
        assert AccountTypeValidator.validate("PASSIVO") == "LIABILITY"
        assert AccountTypeValidator.validate("PATRIMÔNIO") == "EQUITY"
        assert AccountTypeValidator.validate("RECEITA") == "REVENUE"
        assert AccountTypeValidator.validate("DESPESA") == "EXPENSE"

    def test_validate_invalid_type(self):
        with pytest.raises(ValidationError):
            AccountTypeValidator.validate("INVALID")

    def test_validate_empty_type(self):
        with pytest.raises(ValidationError):
            AccountTypeValidator.validate("")


class TestAccountCodeValidator:
    """Test account code validation"""

    def test_validate_numeric_code(self):
        assert AccountCodeValidator.validate("1.01.001") == "1.01.001"

    def test_validate_alphanumeric_code(self):
        assert AccountCodeValidator.validate("A1.01.001") == "A1.01.001"

    def test_validate_empty_code(self):
        with pytest.raises(ValidationError):
            AccountCodeValidator.validate("")


class TestAmountValidator:
    """Test amount validation and conversion"""

    def test_validate_integer(self):
        result = AmountValidator.validate(100)
        assert result == Decimal("100.00")

    def test_validate_float(self):
        result = AmountValidator.validate(123.45)
        assert result == Decimal("123.45")

    def test_validate_string(self):
        result = AmountValidator.validate("123.45")
        assert result == Decimal("123.45")

    def test_validate_negative(self):
        result = AmountValidator.validate(-50.00, allow_negative=True)
        assert result == Decimal("-50.00")

    def test_validate_negative_disallowed(self):
        with pytest.raises(ValidationError):
            AmountValidator.validate(-50.00, allow_negative=False)

    def test_validate_none(self):
        with pytest.raises(ValidationError):
            AmountValidator.validate(None)


class TestDateValidator:
    """Test date validation and conversion"""

    def test_validate_datetime(self):
        dt = datetime(2024, 1, 31)
        result = DateValidator.validate(dt)
        assert result == dt

    def test_validate_iso_string(self):
        result = DateValidator.validate("2024-01-31")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 31

    def test_validate_brazilian_format(self):
        result = DateValidator.validate("31/01/2024")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 31

    def test_validate_invalid_format(self):
        with pytest.raises(ValidationError):
            DateValidator.validate("invalid-date")


class TestTrialBalanceValidator:
    """Test trial balance validation"""

    def test_validate_valid_trial_balance(self):
        data = {
            "company_id": "01",
            "company_name": "Test Company",
            "period_start": datetime(2024, 1, 1),
            "period_end": datetime(2024, 12, 31),
            "currency": "BRL",
            "accounts": [
                {
                    "account_code": "1.01.001",
                    "account_name": "Cash",
                    "account_type": "ASSET",
                    "level": 1,
                    "opening_balance": 0,
                    "debit_amount": 1000,
                    "credit_amount": 500,
                    "closing_balance": 500,
                }
            ]
        }

        result = TrialBalanceValidator.validate(data)
        assert result["company_id"] == "01"
        assert len(result["accounts"]) == 1

    def test_validate_missing_required_fields(self):
        data = {"company_id": "01"}
        with pytest.raises(ValidationError):
            TrialBalanceValidator.validate(data)

    def test_validate_invalid_period(self):
        data = {
            "company_id": "01",
            "company_name": "Test",
            "period_start": datetime(2024, 12, 31),
            "period_end": datetime(2024, 1, 1),
            "currency": "BRL",
            "accounts": []
        }
        with pytest.raises(ValidationError):
            TrialBalanceValidator.validate(data)


# Auth Tests

class TestOAuth2Handler:
    """Test OAuth2 authentication handler"""

    @pytest.mark.asyncio
    async def test_get_headers_with_valid_token(self):
        handler = OAuth2Handler(
            credentials={
                "client_id": "test_id",
                "client_secret": "test_secret"
            },
            config={"token_url": "https://api.example.com/token"}
        )

        # Mock token
        handler._token_info = TokenInfo(
            access_token="test_token",
            token_type="Bearer",
            expires_in=3600
        )

        headers = await handler.get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_token"

    @pytest.mark.asyncio
    async def test_token_expiry_check(self):
        token = TokenInfo(
            access_token="test_token",
            expires_in=300,
            issued_at=datetime.now(timezone.utc) - timedelta(seconds=400)
        )

        # Should be expired
        assert token.is_expired(buffer_seconds=0) is True

        # Fresh token
        fresh_token = TokenInfo(
            access_token="fresh_token",
            expires_in=3600
        )
        assert fresh_token.is_expired() is False


class TestAPIKeyHandler:
    """Test API Key authentication handler"""

    @pytest.mark.asyncio
    async def test_get_headers_default(self):
        handler = APIKeyHandler(
            credentials={"api_key": "test_key"}
        )

        headers = await handler.get_headers()
        assert "X-API-Key" in headers
        assert headers["X-API-Key"] == "test_key"

    @pytest.mark.asyncio
    async def test_get_headers_custom_header(self):
        handler = APIKeyHandler(
            credentials={"api_key": "test_key"},
            config={"key_header": "Authorization"}
        )

        headers = await handler.get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "test_key"


# Retry Tests

class TestRetryLogic:
    """Test retry logic and exponential backoff"""

    def test_calculate_exponential_delay(self):
        config = RetryConfig(
            initial_delay=1.0,
            exponential_base=2.0,
            strategy=RetryStrategy.EXPONENTIAL,
            jitter=False
        )

        assert calculate_delay(0, config) == 1.0
        assert calculate_delay(1, config) == 2.0
        assert calculate_delay(2, config) == 4.0

    def test_calculate_linear_delay(self):
        config = RetryConfig(
            initial_delay=1.0,
            strategy=RetryStrategy.LINEAR,
            jitter=False
        )

        assert calculate_delay(0, config) == 1.0
        assert calculate_delay(1, config) == 2.0
        assert calculate_delay(2, config) == 3.0

    def test_calculate_fixed_delay(self):
        config = RetryConfig(
            initial_delay=5.0,
            strategy=RetryStrategy.FIXED,
            jitter=False
        )

        assert calculate_delay(0, config) == 5.0
        assert calculate_delay(1, config) == 5.0
        assert calculate_delay(2, config) == 5.0

    def test_max_delay_cap(self):
        config = RetryConfig(
            initial_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0,
            strategy=RetryStrategy.EXPONENTIAL,
            jitter=False
        )

        # 2^10 = 1024, but should be capped at 10.0
        assert calculate_delay(10, config) == 10.0


class TestRateLimiter:
    """Test rate limiter"""

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests(self):
        limiter = RateLimiter(rate=10, per=1.0)

        # Should allow first request immediately
        await limiter.acquire(1)
        assert limiter._tokens < 10

    @pytest.mark.asyncio
    async def test_rate_limiter_burst(self):
        limiter = RateLimiter(rate=10, per=1.0, burst=5)
        assert limiter._tokens == 5.0


# Factory Tests

class TestConnectorFactory:
    """Test connector factory"""

    def test_create_totvs_connector(self, oauth2_credentials, totvs_config):
        connector = ConnectorFactory.create_connector(
            ERPType.TOTVS_PROTHEUS,
            oauth2_credentials,
            totvs_config
        )

        assert connector.erp_type == ERPType.TOTVS_PROTHEUS
        assert not connector.is_connected()

    def test_create_omie_connector(self, api_key_credentials):
        config = {"base_url": "https://app.omie.com.br/api/v1"}
        api_key_credentials.credentials["app_secret"] = "test_secret"

        connector = ConnectorFactory.create_connector(
            ERPType.OMIE,
            api_key_credentials,
            config
        )

        assert connector.erp_type == ERPType.OMIE

    def test_create_from_config(self):
        config = {
            "erp_type": "omie",
            "auth_type": "api_key",
            "credentials": {
                "api_key": "test_key",
                "app_secret": "test_secret"
            },
            "config": {}
        }

        connector = ConnectorFactory.create_from_config(config)
        assert connector.erp_type == ERPType.OMIE

    def test_create_invalid_erp_type(self, oauth2_credentials):
        with pytest.raises(ValueError):
            ConnectorFactory.create_from_config({
                "erp_type": "invalid_erp",
                "auth_type": "oauth2",
                "credentials": {}
            })

    def test_get_supported_erp_types(self):
        types = ConnectorFactory.get_supported_erp_types()
        assert ERPType.TOTVS_PROTHEUS in types
        assert ERPType.CONTAAZUL in types
        assert ERPType.OMIE in types
        assert ERPType.BLING in types


class TestPortfolioMapping:
    """Test portfolio company to ERP mapping"""

    def test_get_erp_for_effecti(self):
        assert get_erp_for_company("effecti") == ERPType.TOTVS_PROTHEUS

    def test_get_erp_for_mercos(self):
        assert get_erp_for_company("mercos") == ERPType.CONTAAZUL

    def test_get_erp_for_datahub(self):
        assert get_erp_for_company("datahub") == ERPType.OMIE

    def test_get_erp_for_leadlovers(self):
        assert get_erp_for_company("leadlovers") == ERPType.BLING

    def test_get_erp_for_unknown_company(self):
        assert get_erp_for_company("unknown") is None


# Integration-style tests (mocked)

class TestTOTVSConnector:
    """Test TOTVS Protheus connector (mocked)"""

    @pytest.mark.asyncio
    async def test_connect(self, oauth2_credentials, totvs_config):
        connector = ConnectorFactory.create_connector(
            ERPType.TOTVS_PROTHEUS,
            oauth2_credentials,
            totvs_config
        )

        # Mock the HTTP client
        with patch.object(connector, 'health_check', new_callable=AsyncMock) as mock_health:
            mock_health.return_value = MagicMock(
                status=ConnectionStatus.HEALTHY
            )

            result = await connector.connect()
            assert result is True
            assert connector.is_connected()

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_get_trial_balance(self, oauth2_credentials, totvs_config):
        connector = ConnectorFactory.create_connector(
            ERPType.TOTVS_PROTHEUS,
            oauth2_credentials,
            totvs_config
        )

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {
                    "accountCode": "1.01.001",
                    "accountName": "Cash",
                    "accountType": "1",
                    "level": 1,
                    "openingBalance": 0,
                    "debitAmount": 1000,
                    "creditAmount": 500,
                    "closingBalance": 500
                }
            ],
            "company": {"name": "Test Company"}
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(connector, 'client', create=True) as mock_client:
            mock_client.get = AsyncMock(return_value=mock_response)

            # Mock auth handler
            connector.auth_handler.get_headers = AsyncMock(
                return_value={"Authorization": "Bearer test_token"}
            )

            # Mock rate limiter
            connector.rate_limiter.acquire = AsyncMock()

            trial_balance = await connector.get_trial_balance(
                company_id="01",
                period_start=datetime(2024, 1, 1),
                period_end=datetime(2024, 12, 31)
            )

            assert trial_balance.company_id == "01"
            assert len(trial_balance.accounts) == 1
            # Accounts are returned as dataclass objects
            first_account = trial_balance.accounts[0]
            assert first_account.account_code == "1.01.001"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
