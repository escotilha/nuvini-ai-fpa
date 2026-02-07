"""
Data validation module for ERP connector responses.

Validates and normalizes data from different ERP systems into standard formats.
"""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Set
import logging
import re


logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when data validation fails"""
    pass


class AccountTypeValidator:
    """Validates and normalizes account types"""

    VALID_TYPES = {"ASSET", "LIABILITY", "EQUITY", "REVENUE", "EXPENSE"}

    # Mapping of common variations to standard types
    TYPE_MAPPINGS = {
        # Portuguese variations
        "ATIVO": "ASSET",
        "PASSIVO": "LIABILITY",
        "PATRIMÔNIO": "EQUITY",
        "PATRIMONIO": "EQUITY",
        "RECEITA": "REVENUE",
        "DESPESA": "EXPENSE",
        "CUSTO": "EXPENSE",

        # English variations
        "ASSETS": "ASSET",
        "LIABILITIES": "LIABILITY",
        "CAPITAL": "EQUITY",
        "INCOME": "REVENUE",
        "REVENUES": "REVENUE",
        "EXPENSES": "EXPENSE",
        "COSTS": "EXPENSE",

        # Common abbreviations
        "A": "ASSET",
        "P": "LIABILITY",
        "PL": "EQUITY",
        "R": "REVENUE",
        "D": "EXPENSE",
    }

    @classmethod
    def validate(cls, account_type: str) -> str:
        """
        Validate and normalize account type.

        Args:
            account_type: Account type string

        Returns:
            Normalized account type

        Raises:
            ValidationError: If account type is invalid
        """
        if not account_type:
            raise ValidationError("Account type is required")

        normalized = account_type.strip().upper()

        # Check if already valid
        if normalized in cls.VALID_TYPES:
            return normalized

        # Try mapping
        if normalized in cls.TYPE_MAPPINGS:
            return cls.TYPE_MAPPINGS[normalized]

        raise ValidationError(
            f"Invalid account type: {account_type}. "
            f"Must be one of: {', '.join(cls.VALID_TYPES)}"
        )


class AccountCodeValidator:
    """Validates account codes"""

    # Common patterns for Brazilian chart of accounts
    PATTERNS = {
        "numeric": r"^\d+(\.\d+)*$",  # 1.01.001
        "alphanumeric": r"^[A-Z0-9]+(\.[A-Z0-9]+)*$",  # A1.01.001
        "hierarchical": r"^\d{1,2}(\.\d{2}){0,4}$",  # 1.01.01.001
    }

    @classmethod
    def validate(cls, account_code: str) -> str:
        """
        Validate account code format.

        Args:
            account_code: Account code string

        Returns:
            Normalized account code

        Raises:
            ValidationError: If account code is invalid
        """
        if not account_code:
            raise ValidationError("Account code is required")

        # Remove extra whitespace
        normalized = account_code.strip()

        # Must have at least one character
        if not normalized:
            raise ValidationError("Account code cannot be empty")

        # Check against common patterns
        valid = any(
            re.match(pattern, normalized)
            for pattern in cls.PATTERNS.values()
        )

        if not valid:
            logger.warning(f"Account code {account_code} has non-standard format")

        return normalized


class AmountValidator:
    """Validates and normalizes monetary amounts"""

    @classmethod
    def validate(
        cls,
        amount: Any,
        field_name: str = "amount",
        allow_negative: bool = True
    ) -> Decimal:
        """
        Validate and convert amount to Decimal.

        Args:
            amount: Amount value (int, float, str, or Decimal)
            field_name: Name of field for error messages
            allow_negative: Whether negative values are allowed

        Returns:
            Decimal amount

        Raises:
            ValidationError: If amount is invalid
        """
        if amount is None:
            raise ValidationError(f"{field_name} is required")

        try:
            # Convert to Decimal for precise arithmetic
            if isinstance(amount, Decimal):
                decimal_amount = amount
            elif isinstance(amount, (int, float)):
                decimal_amount = Decimal(str(amount))
            elif isinstance(amount, str):
                # Remove common formatting
                cleaned = amount.replace(",", "").replace(" ", "")
                decimal_amount = Decimal(cleaned)
            else:
                raise ValidationError(f"Invalid {field_name} type: {type(amount)}")

            # Check for negative
            if not allow_negative and decimal_amount < 0:
                raise ValidationError(f"{field_name} cannot be negative")

            # Round to 2 decimal places (standard for BRL)
            return decimal_amount.quantize(Decimal("0.01"))

        except (InvalidOperation, ValueError) as e:
            raise ValidationError(f"Invalid {field_name}: {amount}") from e


class DateValidator:
    """Validates and normalizes dates"""

    @classmethod
    def validate(
        cls,
        date_value: Any,
        field_name: str = "date"
    ) -> datetime:
        """
        Validate and convert to datetime.

        Args:
            date_value: Date value (datetime, str, or timestamp)
            field_name: Name of field for error messages

        Returns:
            datetime object

        Raises:
            ValidationError: If date is invalid
        """
        if date_value is None:
            raise ValidationError(f"{field_name} is required")

        if isinstance(date_value, datetime):
            return date_value

        if isinstance(date_value, str):
            # Try common formats
            formats = [
                "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%d/%m/%Y",
                "%d/%m/%Y %H:%M:%S",
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(date_value, fmt)
                except ValueError:
                    continue

            raise ValidationError(f"Invalid {field_name} format: {date_value}")

        if isinstance(date_value, (int, float)):
            # Assume Unix timestamp
            try:
                return datetime.fromtimestamp(date_value)
            except (ValueError, OSError) as e:
                raise ValidationError(f"Invalid {field_name} timestamp: {date_value}") from e

        raise ValidationError(f"Invalid {field_name} type: {type(date_value)}")


class CurrencyValidator:
    """Validates currency codes"""

    VALID_CURRENCIES = {"BRL", "USD", "EUR", "GBP", "JPY", "CHF"}

    @classmethod
    def validate(cls, currency: str) -> str:
        """
        Validate currency code.

        Args:
            currency: Currency code (ISO 4217)

        Returns:
            Normalized currency code

        Raises:
            ValidationError: If currency is invalid
        """
        if not currency:
            raise ValidationError("Currency is required")

        normalized = currency.strip().upper()

        if normalized not in cls.VALID_CURRENCIES:
            logger.warning(f"Unusual currency code: {currency}")

        return normalized


class TrialBalanceValidator:
    """Validates trial balance data"""

    @classmethod
    def validate(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate trial balance data structure.

        Args:
            data: Trial balance data dictionary

        Returns:
            Validated and normalized data

        Raises:
            ValidationError: If data is invalid
        """
        # Required fields
        required_fields = {
            "company_id", "company_name", "period_start",
            "period_end", "currency", "accounts"
        }

        missing = required_fields - set(data.keys())
        if missing:
            raise ValidationError(f"Missing required fields: {missing}")

        # Validate dates
        period_start = DateValidator.validate(data["period_start"], "period_start")
        period_end = DateValidator.validate(data["period_end"], "period_end")

        if period_start >= period_end:
            raise ValidationError("period_start must be before period_end")

        # Validate currency
        currency = CurrencyValidator.validate(data["currency"])

        # Validate accounts
        accounts = data["accounts"]
        if not isinstance(accounts, list):
            raise ValidationError("accounts must be a list")

        if not accounts:
            raise ValidationError("accounts cannot be empty")

        validated_accounts = [
            cls._validate_account(account)
            for account in accounts
        ]

        # Check trial balance equation (debits = credits)
        total_debits = sum(acc["debit_amount"] for acc in validated_accounts)
        total_credits = sum(acc["credit_amount"] for acc in validated_accounts)

        if abs(total_debits - total_credits) > Decimal("0.01"):
            logger.warning(
                f"Trial balance out of balance: "
                f"debits={total_debits}, credits={total_credits}"
            )

        return {
            "company_id": str(data["company_id"]),
            "company_name": str(data["company_name"]),
            "period_start": period_start,
            "period_end": period_end,
            "currency": currency,
            "accounts": validated_accounts,
            "extracted_at": datetime.now(timezone.utc),
            "metadata": data.get("metadata", {}),
        }

    @classmethod
    def _validate_account(cls, account: Dict[str, Any]) -> Dict[str, Any]:
        """Validate individual account balance"""
        required = {"account_code", "account_name", "account_type"}
        missing = required - set(account.keys())
        if missing:
            raise ValidationError(f"Account missing fields: {missing}")

        return {
            "account_code": AccountCodeValidator.validate(account["account_code"]),
            "account_name": str(account["account_name"]).strip(),
            "account_type": AccountTypeValidator.validate(account["account_type"]),
            "parent_account_code": (
                AccountCodeValidator.validate(account["parent_account_code"])
                if account.get("parent_account_code")
                else None
            ),
            "level": int(account.get("level", 1)),
            "opening_balance": AmountValidator.validate(
                account.get("opening_balance", 0),
                "opening_balance"
            ),
            "debit_amount": AmountValidator.validate(
                account.get("debit_amount", 0),
                "debit_amount",
                allow_negative=False
            ),
            "credit_amount": AmountValidator.validate(
                account.get("credit_amount", 0),
                "credit_amount",
                allow_negative=False
            ),
            "closing_balance": AmountValidator.validate(
                account.get("closing_balance", 0),
                "closing_balance"
            ),
            "is_summary": bool(account.get("is_summary", False)),
        }


class SubledgerValidator:
    """Validates subledger entry data"""

    @classmethod
    def validate(cls, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate subledger entry.

        Args:
            entry: Subledger entry dictionary

        Returns:
            Validated and normalized entry

        Raises:
            ValidationError: If entry is invalid
        """
        required = {
            "entry_id", "transaction_date", "account_code",
            "account_name", "debit_amount", "credit_amount"
        }

        missing = required - set(entry.keys())
        if missing:
            raise ValidationError(f"Subledger entry missing fields: {missing}")

        # At least one of debit or credit must be non-zero
        debit = AmountValidator.validate(entry["debit_amount"], "debit_amount", allow_negative=False)
        credit = AmountValidator.validate(entry["credit_amount"], "credit_amount", allow_negative=False)

        if debit == 0 and credit == 0:
            raise ValidationError("Subledger entry must have either debit or credit")

        return {
            "entry_id": str(entry["entry_id"]),
            "transaction_date": DateValidator.validate(entry["transaction_date"], "transaction_date"),
            "posting_date": DateValidator.validate(
                entry.get("posting_date", entry["transaction_date"]),
                "posting_date"
            ),
            "account_code": AccountCodeValidator.validate(entry["account_code"]),
            "account_name": str(entry["account_name"]).strip(),
            "debit_amount": debit,
            "credit_amount": credit,
            "description": str(entry.get("description", "")).strip(),
            "document_number": str(entry["document_number"]) if entry.get("document_number") else None,
            "document_type": str(entry["document_type"]) if entry.get("document_type") else None,
            "cost_center": str(entry["cost_center"]) if entry.get("cost_center") else None,
            "entity_id": str(entry["entity_id"]) if entry.get("entity_id") else None,
            "entity_name": str(entry["entity_name"]) if entry.get("entity_name") else None,
            "metadata": entry.get("metadata", {}),
        }
