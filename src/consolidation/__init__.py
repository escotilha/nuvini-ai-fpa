"""
IFRS-Compliant Consolidation Engine for Multi-Entity Financial Consolidation.

This package provides comprehensive financial consolidation capabilities
supporting IFRS and US GAAP standards with:

- Multi-currency FX conversion (IFRS 21 / ASC 830)
- Intercompany elimination (receivables/payables, revenue/expense)
- Purchase Price Allocation (PPA) and amortization
- IFRS to US GAAP reconciliation
- Comprehensive validation (99.9% accuracy target)

Usage:
    from consolidation import QuickConsolidator, Entity, Currency
    from consolidation.models import TrialBalanceEntry

    # Create consolidator
    consolidator = QuickConsolidator()

    # Define entities
    entities = [
        Entity(
            entity_id="effecti",
            name="Effecti",
            functional_currency=Currency.BRL,
            ownership_percentage=Decimal("100"),
            country_code="BR"
        ),
        # ... more entities
    ]

    # Consolidate
    result = consolidator.quick_consolidate(
        entities=entities,
        trial_balances=trial_balance_data,
        period_end_date=date(2026, 1, 31),
        period_start_date=date(2026, 1, 1)
    )

    # Validate
    from consolidation.validation import ConsolidationValidator
    validator = ConsolidationValidator()
    is_valid, errors = validator.validate_all(result)
"""

__version__ = "1.0.0"
__author__ = "FPA Consolidation Team"

# Core models
from .models import (
    # Enums
    Currency,
    AccountingStandard,
    AccountType,
    FXRateType,
    EliminationType,

    # Entities
    Entity,
    FXRate,
    TrialBalanceEntry,
    ConvertedEntry,
    IntercompanyTransaction,
    EliminationEntry,
    PurchasePriceAllocation,
    AmortizationEntry,
    ConsolidatedFinancials,
    GAAPReconciliation,
    AuditLogEntry
)

# FX Conversion
from .fx_converter import (
    FXRateManager,
    FXConverter,
    load_bcb_rates,
    create_sample_rates
)

# Eliminations
from .eliminations import (
    IntercompanyMatcher,
    EliminationEngine,
    ConsolidationEliminator
)

# PPA
from .ppa import (
    PPACalculator,
    AmortizationScheduler,
    GoodwillImpairmentTester,
    PPAManager
)

# GAAP Reconciliation
from .gaap_reconciliation import (
    GAAPDifferenceHandler,
    ReconciliationEngine,
    DualReportingEngine
)

# Main consolidation engine
from .consolidator import (
    ConsolidationEngine,
    QuickConsolidator
)

# Validation
from .validation import (
    ValidationRule,
    BalanceSheetBalanceRule,
    DebitCreditBalanceRule,
    NetIncomeReconciliationRule,
    ConsolidationValidator,
    ComplianceChecker
)

__all__ = [
    # Enums
    "Currency",
    "AccountingStandard",
    "AccountType",
    "FXRateType",
    "EliminationType",

    # Models
    "Entity",
    "FXRate",
    "TrialBalanceEntry",
    "ConvertedEntry",
    "IntercompanyTransaction",
    "EliminationEntry",
    "PurchasePriceAllocation",
    "AmortizationEntry",
    "ConsolidatedFinancials",
    "GAAPReconciliation",
    "AuditLogEntry",

    # FX
    "FXRateManager",
    "FXConverter",
    "load_bcb_rates",
    "create_sample_rates",

    # Eliminations
    "IntercompanyMatcher",
    "EliminationEngine",
    "ConsolidationEliminator",

    # PPA
    "PPACalculator",
    "AmortizationScheduler",
    "GoodwillImpairmentTester",
    "PPAManager",

    # GAAP
    "GAAPDifferenceHandler",
    "ReconciliationEngine",
    "DualReportingEngine",

    # Consolidation
    "ConsolidationEngine",
    "QuickConsolidator",

    # Validation
    "ValidationRule",
    "BalanceSheetBalanceRule",
    "DebitCreditBalanceRule",
    "NetIncomeReconciliationRule",
    "ConsolidationValidator",
    "ComplianceChecker",
]
