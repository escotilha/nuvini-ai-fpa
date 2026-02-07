"""
Data models for multi-entity financial consolidation.
Supports IFRS and US GAAP compliance with full audit trail.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4


class Currency(str, Enum):
    """Supported currencies for FX conversion."""
    USD = "USD"
    BRL = "BRL"
    EUR = "EUR"
    GBP = "GBP"


class AccountingStandard(str, Enum):
    """Supported accounting standards."""
    IFRS = "IFRS"
    US_GAAP = "US_GAAP"
    BR_GAAP = "BR_GAAP"


class AccountType(str, Enum):
    """Account types for FX rate application."""
    BALANCE_SHEET_ASSET = "BS_ASSET"
    BALANCE_SHEET_LIABILITY = "BS_LIABILITY"
    BALANCE_SHEET_EQUITY = "BS_EQUITY"
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    EQUITY_TRANSACTION = "EQUITY_TXN"


class FXRateType(str, Enum):
    """FX rate types per IFRS 21."""
    CLOSING = "CLOSING"  # Balance sheet items
    AVERAGE = "AVERAGE"  # P&L items
    HISTORICAL = "HISTORICAL"  # Equity items


class EliminationType(str, Enum):
    """Types of intercompany eliminations."""
    RECEIVABLE_PAYABLE = "AR_AP"
    REVENUE_EXPENSE = "REV_EXP"
    DIVIDEND = "DIVIDEND"
    LOAN = "LOAN"
    EQUITY_INVESTMENT = "EQUITY_INV"


@dataclass
class Entity:
    """Represents a legal entity in the consolidation structure."""
    entity_id: str
    name: str
    functional_currency: Currency
    country_code: str
    ownership_percentage: Decimal  # 0-100
    acquisition_date: Optional[date] = None
    parent_entity_id: Optional[str] = None
    accounting_standard: AccountingStandard = AccountingStandard.IFRS
    is_active: bool = True

    def __post_init__(self):
        if not 0 <= self.ownership_percentage <= 100:
            raise ValueError("Ownership percentage must be between 0 and 100")


@dataclass
class FXRate:
    """Exchange rate for currency conversion."""
    rate_id: str = field(default_factory=lambda: str(uuid4()))
    from_currency: Currency = Currency.USD
    to_currency: Currency = Currency.USD
    rate_date: date = field(default_factory=date.today)
    rate_type: FXRateType = FXRateType.CLOSING
    rate: Decimal = Decimal("1.0")
    source: str = "Manual"
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if self.rate <= 0:
            raise ValueError("Exchange rate must be positive")

    def invert(self) -> "FXRate":
        """Returns the inverse rate (e.g., USD/BRL -> BRL/USD)."""
        return FXRate(
            from_currency=self.to_currency,
            to_currency=self.from_currency,
            rate_date=self.rate_date,
            rate_type=self.rate_type,
            rate=Decimal("1") / self.rate,
            source=f"Inverse of {self.source}",
            created_at=self.created_at
        )


@dataclass
class TrialBalanceEntry:
    """Single trial balance entry for an entity."""
    entry_id: str = field(default_factory=lambda: str(uuid4()))
    entity_id: str = ""
    period_end_date: date = field(default_factory=date.today)
    account_code: str = ""
    account_name: str = ""
    account_type: AccountType = AccountType.BALANCE_SHEET_ASSET
    debit_amount: Decimal = Decimal("0")
    credit_amount: Decimal = Decimal("0")
    currency: Currency = Currency.USD
    description: Optional[str] = None

    @property
    def net_amount(self) -> Decimal:
        """Net amount (debit - credit)."""
        return self.debit_amount - self.credit_amount

    @property
    def amount_functional(self) -> Decimal:
        """Amount in functional currency (for presentation)."""
        return abs(self.net_amount)


@dataclass
class ConvertedEntry:
    """Trial balance entry converted to presentation currency."""
    original_entry: TrialBalanceEntry
    presentation_currency: Currency
    fx_rate: FXRate
    converted_amount: Decimal
    cta_amount: Decimal = Decimal("0")  # Cumulative Translation Adjustment
    conversion_method: str = "Standard"

    def __post_init__(self):
        if self.original_entry.currency == self.presentation_currency:
            self.converted_amount = self.original_entry.net_amount


@dataclass
class IntercompanyTransaction:
    """Represents an intercompany transaction requiring elimination."""
    transaction_id: str = field(default_factory=lambda: str(uuid4()))
    entity_a_id: str = ""
    entity_b_id: str = ""
    elimination_type: EliminationType = EliminationType.RECEIVABLE_PAYABLE
    amount_entity_a: Decimal = Decimal("0")
    amount_entity_b: Decimal = Decimal("0")
    currency_a: Currency = Currency.USD
    currency_b: Currency = Currency.USD
    transaction_date: date = field(default_factory=date.today)
    reference_number: Optional[str] = None
    description: Optional[str] = None
    is_eliminated: bool = False
    fx_gain_loss: Decimal = Decimal("0")

    @property
    def requires_fx_adjustment(self) -> bool:
        """Check if FX adjustment is needed for elimination."""
        return self.currency_a != self.currency_b


@dataclass
class EliminationEntry:
    """Journal entry for intercompany elimination."""
    intercompany_transaction: IntercompanyTransaction
    elimination_id: str = field(default_factory=lambda: str(uuid4()))
    period_end_date: date = field(default_factory=date.today)
    debit_account: str = ""
    credit_account: str = ""
    elimination_amount: Decimal = Decimal("0")
    currency: Currency = Currency.USD
    fx_gain_loss_account: Optional[str] = None
    fx_gain_loss_amount: Decimal = Decimal("0")
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "System"


@dataclass
class PurchasePriceAllocation:
    """Purchase price allocation for an acquisition."""
    ppa_id: str = field(default_factory=lambda: str(uuid4()))
    entity_id: str = ""
    acquisition_date: date = field(default_factory=date.today)
    purchase_price: Decimal = Decimal("0")
    fair_value_net_assets: Decimal = Decimal("0")
    goodwill: Decimal = Decimal("0")
    intangible_assets: Dict[str, Decimal] = field(default_factory=dict)
    amortization_schedule: Dict[str, int] = field(default_factory=dict)  # asset: years
    currency: Currency = Currency.USD

    def __post_init__(self):
        if self.goodwill == Decimal("0"):
            self.goodwill = self.purchase_price - self.fair_value_net_assets

    @property
    def total_intangibles(self) -> Decimal:
        """Total identified intangible assets."""
        return sum(self.intangible_assets.values())


@dataclass
class AmortizationEntry:
    """Monthly amortization entry for PPA intangibles."""
    amortization_id: str = field(default_factory=lambda: str(uuid4()))
    ppa_id: str = ""
    period_end_date: date = field(default_factory=date.today)
    asset_name: str = ""
    monthly_amortization: Decimal = Decimal("0")
    accumulated_amortization: Decimal = Decimal("0")
    remaining_value: Decimal = Decimal("0")
    debit_account: str = "Amortization Expense"
    credit_account: str = "Accumulated Amortization"


@dataclass
class ConsolidatedFinancials:
    """Complete consolidated financial statements."""
    consolidation_id: str = field(default_factory=lambda: str(uuid4()))
    period_end_date: date = field(default_factory=date.today)
    presentation_currency: Currency = Currency.USD
    accounting_standard: AccountingStandard = AccountingStandard.IFRS
    entities_included: List[str] = field(default_factory=list)

    # Financial statements
    trial_balance: List[ConvertedEntry] = field(default_factory=list)
    eliminations: List[EliminationEntry] = field(default_factory=list)
    ppa_adjustments: List[AmortizationEntry] = field(default_factory=list)

    # Summary totals
    total_assets: Decimal = Decimal("0")
    total_liabilities: Decimal = Decimal("0")
    total_equity: Decimal = Decimal("0")
    total_revenue: Decimal = Decimal("0")
    total_expenses: Decimal = Decimal("0")
    net_income: Decimal = Decimal("0")

    # CTA tracking
    total_cta: Decimal = Decimal("0")  # Cumulative Translation Adjustment

    # Validation
    is_balanced: bool = False
    validation_errors: List[str] = field(default_factory=list)

    # Audit trail
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "System"
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

    def validate_balance(self, tolerance: Decimal = Decimal("0.01")) -> bool:
        """Validates that Assets = Liabilities + Equity within tolerance."""
        balance_difference = abs(
            self.total_assets - (self.total_liabilities + self.total_equity)
        )
        self.is_balanced = balance_difference <= tolerance

        if not self.is_balanced:
            self.validation_errors.append(
                f"Balance sheet does not balance: "
                f"Assets={self.total_assets}, L+E={self.total_liabilities + self.total_equity}, "
                f"Difference={balance_difference}"
            )

        return self.is_balanced


@dataclass
class GAAPReconciliation:
    """Reconciliation between IFRS and US GAAP."""
    reconciliation_id: str = field(default_factory=lambda: str(uuid4()))
    period_end_date: date = field(default_factory=date.today)
    ifrs_net_income: Decimal = Decimal("0")
    us_gaap_net_income: Decimal = Decimal("0")

    # Reconciling items
    adjustments: Dict[str, Decimal] = field(default_factory=dict)

    # Common IFRS to US GAAP differences
    development_costs_capitalization: Decimal = Decimal("0")
    lease_classification: Decimal = Decimal("0")
    revenue_recognition: Decimal = Decimal("0")
    goodwill_impairment: Decimal = Decimal("0")
    other_adjustments: Decimal = Decimal("0")

    @property
    def total_adjustments(self) -> Decimal:
        """Sum of all reconciling adjustments."""
        return sum(self.adjustments.values())

    def validate_reconciliation(self, tolerance: Decimal = Decimal("0.01")) -> bool:
        """Validates IFRS + adjustments = US GAAP."""
        calculated_us_gaap = self.ifrs_net_income + self.total_adjustments
        difference = abs(calculated_us_gaap - self.us_gaap_net_income)
        return difference <= tolerance


@dataclass
class AuditLogEntry:
    """Audit trail for all consolidation activities."""
    log_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    user: str = "System"
    action: str = ""
    entity_id: Optional[str] = None
    consolidation_id: Optional[str] = None
    description: str = ""
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    ip_address: Optional[str] = None
