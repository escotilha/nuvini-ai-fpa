"""
Example usage of the IFRS-Compliant Consolidation Engine.

This script demonstrates a complete consolidation workflow for Nuvini Group Limited
with multiple portfolio companies.
"""

from datetime import date
from decimal import Decimal

from consolidation import (
    # Core models
    Entity,
    Currency,
    AccountingStandard,
    TrialBalanceEntry,
    AccountType,

    # Main consolidator
    QuickConsolidator,

    # FX management
    FXRate,
    FXRateType,
    create_sample_rates,

    # Validation
    ConsolidationValidator,
)


def create_nuvini_entities():
    """Create Nuvini's portfolio entities."""
    return [
        Entity(
            entity_id="effecti",
            name="Effecti",
            functional_currency=Currency.BRL,
            ownership_percentage=Decimal("100"),
            country_code="BR",
            acquisition_date=date(2024, 3, 15),
            accounting_standard=AccountingStandard.BR_GAAP
        ),
        Entity(
            entity_id="leadlovers",
            name="LeadLovers",
            functional_currency=Currency.BRL,
            ownership_percentage=Decimal("100"),
            country_code="BR",
            acquisition_date=date(2023, 8, 1),
            accounting_standard=AccountingStandard.BR_GAAP
        ),
        Entity(
            entity_id="ipe_digital",
            name="Ipê Digital",
            functional_currency=Currency.BRL,
            ownership_percentage=Decimal("100"),
            country_code="BR",
            acquisition_date=date(2024, 6, 1),
            accounting_standard=AccountingStandard.BR_GAAP
        ),
        Entity(
            entity_id="onclick",
            name="OnClick",
            functional_currency=Currency.BRL,
            ownership_percentage=Decimal("100"),
            country_code="BR",
            acquisition_date=date(2024, 9, 15),
            accounting_standard=AccountingStandard.BR_GAAP
        ),
        Entity(
            entity_id="dataminer",
            name="Dataminer",
            functional_currency=Currency.BRL,
            ownership_percentage=Decimal("100"),
            country_code="BR",
            acquisition_date=date(2024, 11, 1),
            accounting_standard=AccountingStandard.BR_GAAP
        ),
        Entity(
            entity_id="smart_nx",
            name="Smart NX",
            functional_currency=Currency.BRL,
            ownership_percentage=Decimal("100"),
            country_code="BR",
            acquisition_date=date(2025, 2, 1),
            accounting_standard=AccountingStandard.BR_GAAP
        ),
        Entity(
            entity_id="mk_solutions",
            name="MK Solutions",
            functional_currency=Currency.BRL,
            ownership_percentage=Decimal("100"),
            country_code="BR",
            acquisition_date=date(2025, 12, 1),
            accounting_standard=AccountingStandard.BR_GAAP
        ),
    ]


def create_sample_trial_balance(entity_id: str, scale: Decimal = Decimal("1.0")):
    """Create sample trial balance for an entity."""
    period_end = date(2026, 1, 31)

    return [
        # Assets
        TrialBalanceEntry(
            entity_id=entity_id,
            period_end_date=period_end,
            account_code="1000",
            account_name="Cash and Cash Equivalents",
            account_type=AccountType.BALANCE_SHEET_ASSET,
            debit_amount=Decimal("500000") * scale,
            credit_amount=Decimal("0"),
            currency=Currency.BRL
        ),
        TrialBalanceEntry(
            entity_id=entity_id,
            period_end_date=period_end,
            account_code="1100",
            account_name="Accounts Receivable",
            account_type=AccountType.BALANCE_SHEET_ASSET,
            debit_amount=Decimal("300000") * scale,
            credit_amount=Decimal("0"),
            currency=Currency.BRL
        ),
        TrialBalanceEntry(
            entity_id=entity_id,
            period_end_date=period_end,
            account_code="1500",
            account_name="Property and Equipment",
            account_type=AccountType.BALANCE_SHEET_ASSET,
            debit_amount=Decimal("200000") * scale,
            credit_amount=Decimal("0"),
            currency=Currency.BRL
        ),

        # Liabilities
        TrialBalanceEntry(
            entity_id=entity_id,
            period_end_date=period_end,
            account_code="2000",
            account_name="Accounts Payable",
            account_type=AccountType.BALANCE_SHEET_LIABILITY,
            debit_amount=Decimal("0"),
            credit_amount=Decimal("150000") * scale,
            currency=Currency.BRL
        ),
        TrialBalanceEntry(
            entity_id=entity_id,
            period_end_date=period_end,
            account_code="2500",
            account_name="Long-term Debt",
            account_type=AccountType.BALANCE_SHEET_LIABILITY,
            debit_amount=Decimal("0"),
            credit_amount=Decimal("400000") * scale,
            currency=Currency.BRL
        ),

        # Equity
        TrialBalanceEntry(
            entity_id=entity_id,
            period_end_date=period_end,
            account_code="3000",
            account_name="Share Capital",
            account_type=AccountType.BALANCE_SHEET_EQUITY,
            debit_amount=Decimal("0"),
            credit_amount=Decimal("300000") * scale,
            currency=Currency.BRL
        ),
        TrialBalanceEntry(
            entity_id=entity_id,
            period_end_date=period_end,
            account_code="3100",
            account_name="Retained Earnings",
            account_type=AccountType.BALANCE_SHEET_EQUITY,
            debit_amount=Decimal("0"),
            credit_amount=Decimal("150000") * scale,
            currency=Currency.BRL
        ),

        # Revenue
        TrialBalanceEntry(
            entity_id=entity_id,
            period_end_date=period_end,
            account_code="4000",
            account_name="SaaS Revenue",
            account_type=AccountType.INCOME,
            debit_amount=Decimal("0"),
            credit_amount=Decimal("800000") * scale,
            currency=Currency.BRL
        ),

        # Expenses
        TrialBalanceEntry(
            entity_id=entity_id,
            period_end_date=period_end,
            account_code="5000",
            account_name="Cost of Revenue",
            account_type=AccountType.EXPENSE,
            debit_amount=Decimal("200000") * scale,
            credit_amount=Decimal("0"),
            currency=Currency.BRL
        ),
        TrialBalanceEntry(
            entity_id=entity_id,
            period_end_date=period_end,
            account_code="5100",
            account_name="Sales and Marketing",
            account_type=AccountType.EXPENSE,
            debit_amount=Decimal("300000") * scale,
            credit_amount=Decimal("0"),
            currency=Currency.BRL
        ),
        TrialBalanceEntry(
            entity_id=entity_id,
            period_end_date=period_end,
            account_code="5200",
            account_name="General and Administrative",
            account_type=AccountType.EXPENSE,
            debit_amount=Decimal("150000") * scale,
            credit_amount=Decimal("0"),
            currency=Currency.BRL
        ),
    ]


def main():
    """Run complete consolidation example."""
    print("=" * 70)
    print("NUVINI GROUP LIMITED - CONSOLIDATION EXAMPLE")
    print("=" * 70)
    print()

    # 1. Create entities
    print("Step 1: Creating portfolio entities...")
    entities = create_nuvini_entities()
    print(f"  ✓ Created {len(entities)} entities")
    print()

    # 2. Create trial balances
    print("Step 2: Generating trial balances...")
    trial_balances = {}

    # Different scales for different companies
    scales = {
        "effecti": Decimal("1.5"),
        "leadlovers": Decimal("2.0"),
        "ipe_digital": Decimal("1.0"),
        "onclick": Decimal("0.8"),
        "dataminer": Decimal("0.6"),
        "smart_nx": Decimal("0.5"),
        "mk_solutions": Decimal("1.2"),
    }

    for entity in entities:
        scale = scales.get(entity.entity_id, Decimal("1.0"))
        trial_balances[entity.entity_id] = create_sample_trial_balance(
            entity.entity_id, scale
        )
        entry_count = len(trial_balances[entity.entity_id])
        print(f"  ✓ {entity.name}: {entry_count} entries (scale: {scale}x)")

    print()

    # 3. Create consolidator
    print("Step 3: Initializing consolidation engine...")
    consolidator = QuickConsolidator()

    # Load FX rates
    create_sample_rates(
        consolidator.engine.fx_rate_manager,
        as_of_date=date(2026, 1, 31)
    )
    print("  ✓ FX rates loaded (BRL/USD, EUR/USD, GBP/USD)")
    print()

    # 4. Consolidate
    print("Step 4: Performing consolidation...")
    result = consolidator.quick_consolidate(
        entities=entities,
        trial_balances=trial_balances,
        period_end_date=date(2026, 1, 31),
        period_start_date=date(2026, 1, 1),
        presentation_currency=Currency.USD
    )
    print("  ✓ Consolidation complete")
    print()

    # 5. Display results
    print("Step 5: Consolidated Financial Summary")
    print("-" * 70)
    print(f"Period End Date:    {result.period_end_date}")
    print(f"Currency:           {result.presentation_currency.value}")
    print(f"Standard:           {result.accounting_standard.value}")
    print(f"Entities:           {len(result.entities_included)}")
    print()
    print("BALANCE SHEET:")
    print(f"  Total Assets:       ${result.total_assets:,.2f}")
    print(f"  Total Liabilities:  ${result.total_liabilities:,.2f}")
    print(f"  Total Equity:       ${result.total_equity:,.2f}")
    print()
    print("INCOME STATEMENT:")
    print(f"  Total Revenue:      ${result.total_revenue:,.2f}")
    print(f"  Total Expenses:     ${result.total_expenses:,.2f}")
    print(f"  Net Income:         ${result.net_income:,.2f}")
    print()

    # 6. Validate
    print("Step 6: Validation")
    print("-" * 70)

    validator = ConsolidationValidator()
    is_valid, results = validator.validate_all(result)

    print(f"Status: {'✓ PASS' if is_valid else '✗ FAIL'}")

    accuracy = validator.calculate_accuracy_score(result)
    print(f"Accuracy Score: {accuracy * 100:.4f}%")

    if accuracy >= validator.accuracy_target:
        print(f"  ✓ Target met ({validator.accuracy_target * 100:.2f}%)")
    else:
        print(f"  ✗ Target not met ({validator.accuracy_target * 100:.2f}%)")

    print()

    # Show errors if any
    if results["ERROR"]:
        print("ERRORS:")
        for error in results["ERROR"]:
            print(f"  ✗ {error}")
        print()

    # Show warnings if any
    if results["WARNING"]:
        print("WARNINGS:")
        for warning in results["WARNING"]:
            print(f"  ! {warning}")
        print()

    # 7. Full validation report
    print("\n" + "=" * 70)
    print("DETAILED VALIDATION REPORT")
    print("=" * 70)
    print(validator.generate_validation_report(result))

    # 8. Audit trail
    print("\n" + "=" * 70)
    print("AUDIT TRAIL (Last 10 entries)")
    print("=" * 70)

    audit_log = consolidator.engine.get_consolidation_audit_trail()
    for entry in audit_log[-10:]:
        print(f"{entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')} | "
              f"{entry.action:25s} | {entry.description}")

    print()
    print("=" * 70)
    print("CONSOLIDATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
