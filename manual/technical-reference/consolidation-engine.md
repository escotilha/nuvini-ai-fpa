# Consolidation Engine Technical Reference

**Version:** 1.0.0
**Last Updated:** 2026-02-07
**Implementation:** `/Volumes/AI/Code/FPA/src/consolidation/`
**Standards:** IFRS 10, IFRS 3, IAS 21, ASC 810, ASC 805, ASC 830

## Overview

The Consolidation Engine is a production-ready IFRS/US GAAP-compliant system that performs multi-entity financial consolidation with FX conversion, intercompany elimination, purchase price allocation (PPA), and GAAP reconciliation.

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                  ConsolidationEngine                         │
│                  (Main Orchestrator)                         │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │  FXRateManager   │  │  FXConverter     │                 │
│  │  - Rate storage  │  │  - IFRS 21 logic │                 │
│  │  - BCB/ECB API   │  │  - CTA tracking  │                 │
│  └──────────────────┘  └──────────────────┘                 │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │ IC Matcher       │  │ EliminationEng   │                 │
│  │ - AR/AP match    │  │  - JE creation   │                 │
│  │ - Rev/Exp match  │  │  - FX adjustment │                 │
│  └──────────────────┘  └──────────────────┘                 │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │ PPAManager       │  │ GAAPReconEngine  │                 │
│  │ - Goodwill calc  │  │  - IFRS→US GAAP  │                 │
│  │ - Amortization   │  │  - Dual reporting│                 │
│  │ - Impairment     │  │  - Disclosure fmt│                 │
│  └──────────────────┘  └──────────────────┘                 │
│                                                              │
│  ┌──────────────────┐                                       │
│  │ Validator        │                                       │
│  │ - 7 core rules   │                                       │
│  │ - Accuracy calc  │                                       │
│  │ - Compliance chk │                                       │
│  └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
```

### Module Structure

```
consolidation/
├── __init__.py                   # Package exports
├── models.py                     # Data models and enums
├── fx_converter.py               # FX rate management & conversion
├── eliminations.py               # Intercompany elimination
├── ppa.py                        # Purchase price allocation
├── gaap_reconciliation.py        # IFRS/US GAAP reconciliation
├── consolidator.py               # Main consolidation engine
├── validation.py                 # Validation framework
├── example_usage.py              # Working examples
└── README.md                     # User documentation
```

## Core Models

### Entity

Represents a portfolio company.

```python
from consolidation import Entity, Currency

entity = Entity(
    entity_id="effecti",
    entity_name="Effecti",
    functional_currency=Currency.BRL,
    ownership_percentage=Decimal("100.0"),
    country_code="BR",
    parent_entity_id=None,
    is_active=True
)
```

**Fields:**
- `entity_id` - Unique identifier
- `entity_name` - Company name
- `functional_currency` - Entity's functional currency
- `ownership_percentage` - Ownership stake (0-100)
- `country_code` - ISO country code
- `parent_entity_id` - Parent entity for hierarchy
- `is_active` - Whether entity is active

### TrialBalanceEntry

Represents a single account balance.

```python
from consolidation import TrialBalanceEntry, AccountType

entry = TrialBalanceEntry(
    entity_id="effecti",
    account_code="1.01.001",
    account_name="Caixa",
    account_type=AccountType.ASSET,
    opening_balance=Decimal("100000.00"),
    debit_amount=Decimal("50000.00"),
    credit_amount=Decimal("30000.00"),
    ending_balance=Decimal("120000.00"),
    currency=Currency.BRL,
    standard_account_code="1010"
)
```

**Fields:**
- `entity_id` - Entity identifier
- `account_code` - Local account code
- `account_name` - Local account name
- `account_type` - ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE
- `opening_balance` - Period opening balance
- `debit_amount` - Period debits
- `credit_amount` - Period credits
- `ending_balance` - Period ending balance
- `currency` - Currency code
- `standard_account_code` - Mapped standard COA code

### ConsolidatedBalance

Represents a consolidated account balance.

```python
from consolidation import ConsolidatedBalance

balance = ConsolidatedBalance(
    account_code="1010",
    account_name="Cash",
    account_type=AccountType.ASSET,
    opening_balance=Decimal("1500000.00"),
    period_activity=Decimal("250000.00"),
    ending_balance=Decimal("1750000.00"),
    currency=Currency.USD,
    entity_contributions={
        "effecti": Decimal("850000.00"),
        "leadlovers": Decimal("900000.00")
    }
)
```

## Foreign Exchange (FX) Conversion

### IFRS 21 / ASC 830 Compliance

The FX converter implements IFRS 21 (IAS 21) and ASC 830 standards:

- **Balance Sheet Accounts** → Closing rate (spot rate at period end)
- **P&L Accounts** → Average rate (period average)
- **Equity Accounts** → Historical rate (rate at acquisition/transaction)
- **CTA Calculation** → Cumulative Translation Adjustment tracking

### FXRateManager

Manages exchange rates from multiple sources.

```python
from consolidation import FXRateManager, Currency, FXRateSource

rate_manager = FXRateManager()

# Add rate
rate_manager.add_rate(
    from_currency=Currency.BRL,
    to_currency=Currency.USD,
    rate=Decimal("0.187453"),
    rate_date=date(2024, 12, 31),
    source=FXRateSource.BCB
)

# Get rate (with fallback)
rate = rate_manager.get_rate(
    from_currency=Currency.BRL,
    to_currency=Currency.USD,
    rate_date=date(2024, 12, 31)
)

# Get average rate for period
avg_rate = rate_manager.get_average_rate(
    from_currency=Currency.BRL,
    to_currency=Currency.USD,
    start_date=date(2024, 1, 1),
    end_date=date(2024, 12, 31)
)
```

**Rate Sources:**
- `BCB` - Brazilian Central Bank (Banco Central do Brasil)
- `ECB` - European Central Bank
- `MANUAL` - Manually entered rates
- `SYSTEM` - System calculated rates

**Fallback Logic:**
1. Try exact date match
2. Try previous business day (up to 5 days)
3. Interpolate between nearest dates
4. Raise exception if no rates found

### FXConverter

Converts trial balance entries according to IFRS 21.

```python
from consolidation import FXConverter

fx_converter = FXConverter(rate_manager)

# Convert single entry
converted_entry = fx_converter.convert_trial_balance_entry(
    entry=trial_balance_entry,
    target_currency=Currency.USD,
    closing_rate=Decimal("0.187453"),
    average_rate=Decimal("0.185234"),
    historical_rate=Decimal("0.180000")
)
```

**Conversion Rules:**

| Account Type | Rate Used | IFRS 21 Reference |
|--------------|-----------|-------------------|
| Asset | Closing | IAS 21.23(a) |
| Liability | Closing | IAS 21.23(a) |
| Equity | Historical | IAS 21.23(b) |
| Revenue | Average | IAS 21.40 |
| Expense | Average | IAS 21.40 |

**CTA Calculation:**

```python
# Cumulative Translation Adjustment
CTA = (Assets - Liabilities - Equity) translated
    - ((Assets - Liabilities - Equity) at closing rate)
```

## Intercompany Elimination

### Matching Algorithm

The elimination engine automatically matches intercompany transactions:

1. **Reference Number Matching** - Match by transaction reference
2. **Amount Matching** - Match within tolerance (default 1%)
3. **Entity Relationship** - Validate entity pair
4. **FX Adjustment** - Handle cross-currency transactions

### IntercompanyMatcher

```python
from consolidation import IntercompanyMatcher

matcher = IntercompanyMatcher(tolerance=Decimal("0.01"))

# Match receivables and payables
ar_ap_matches = matcher.match_receivables_payables(
    trial_balances={"effecti": [...], "leadlovers": [...]},
    entities=[effecti_entity, leadlovers_entity]
)

# Match revenues and expenses
rev_exp_matches = matcher.match_revenues_expenses(
    trial_balances={"effecti": [...], "leadlovers": [...]},
    entities=[effecti_entity, leadlovers_entity]
)
```

**Matching Criteria:**

```python
def is_matching_pair(amount1, amount2, tolerance):
    """Check if two amounts match within tolerance."""
    if amount2 == 0:
        return False
    variance = abs((amount1 + amount2) / amount2)
    return variance <= tolerance
```

### EliminationEngine

Creates elimination journal entries.

```python
from consolidation import EliminationEngine, EliminationType

elimination_engine = EliminationEngine()

# Create single elimination
entry = elimination_engine.create_elimination_entry(
    match=ic_match,
    elimination_type=EliminationType.RECEIVABLES_PAYABLES,
    period_year=2024,
    period_month=12
)

# Create all eliminations
all_entries = elimination_engine.create_all_eliminations(
    ar_ap_matches=ar_ap_matches,
    rev_exp_matches=rev_exp_matches,
    period_year=2024,
    period_month=12
)
```

**Elimination Types:**

| Type | Debit | Credit | Purpose |
|------|-------|--------|---------|
| AR/AP | IC Payable | IC Receivable | Eliminate intercompany AR/AP |
| Revenue/Expense | IC Revenue | IC Expense | Eliminate intercompany revenue |
| Dividend | Dividend Income | Dividend Payable | Eliminate intercompany dividends |
| Investment | Investment Elimination | Equity | Eliminate investment in subsidiary |

**FX Gain/Loss Recognition:**

```python
# When IC balances don't match due to FX differences
fx_variance = amount_from + amount_to
if abs(fx_variance) > tolerance:
    # Recognize FX gain/loss
    if fx_variance > 0:
        debit("FX Loss", fx_variance)
        credit("IC Payable", fx_variance)
    else:
        debit("IC Receivable", abs(fx_variance))
        credit("FX Gain", abs(fx_variance))
```

## Purchase Price Allocation (PPA)

### Goodwill Calculation

```python
from consolidation import PPACalculator

ppa_calculator = PPACalculator()

ppa = ppa_calculator.calculate_ppa(
    purchase_price=Decimal("10000000"),
    fair_value_net_assets=Decimal("6000000"),
    identified_intangibles={
        "Customer Relationships": Decimal("2000000"),
        "Brand": Decimal("1000000"),
        "Technology": Decimal("500000")
    }
)

# Goodwill = Purchase Price - FV Net Assets - Identified Intangibles
# Goodwill = $10M - $6M - $3.5M = $500K
```

**Calculation:**

```
Purchase Price                     $10,000,000
Less: Fair Value of Net Assets     ($6,000,000)
Less: Identified Intangibles       ($3,500,000)
                                   ────────────
Goodwill                           $   500,000
```

### Amortization Schedule

```python
from consolidation import AmortizationScheduler

scheduler = AmortizationScheduler()

# Create monthly amortization schedule
schedule = scheduler.create_monthly_schedule(
    ppa=ppa,
    start_date=date(2020, 1, 1),
    amortization_periods={
        "Customer Relationships": 10,  # years
        "Brand": 15,
        "Technology": 5
    }
)

# Get amortization for specific period
period_amortization = scheduler.get_amortization_for_period(
    schedule=schedule,
    period_year=2024,
    period_month=12
)
```

**Amortization Calculation (Straight-Line):**

```python
monthly_amortization = intangible_value / (useful_life_years * 12)
```

**Example:**
```
Customer Relationships: $2,000,000 / (10 years * 12 months) = $16,667/month
Brand: $1,000,000 / (15 years * 12 months) = $5,556/month
Technology: $500,000 / (5 years * 12 months) = $8,333/month
```

### Goodwill Impairment Testing

```python
from consolidation import GoodwillImpairmentTester

tester = GoodwillImpairmentTester()

# Step 0: Qualitative assessment (US GAAP)
qualitative_result = tester.test_impairment_qualitative(
    acquisition=acquisition,
    qualitative_factors={
        "macro_economic_decline": False,
        "industry_decline": False,
        "increased_competition": True,
        "regulatory_changes": False,
        "loss_of_key_personnel": False,
        "decline_in_share_price": False
    }
)

# Step 1 & 2: Quantitative test
quantitative_result = tester.test_impairment_quantitative(
    acquisition=acquisition,
    carrying_value=Decimal("8000000"),
    fair_value=Decimal("7500000"),
    date_of_test=date(2024, 12, 31)
)

if quantitative_result.impairment_required:
    impairment_loss = quantitative_result.impairment_amount
    # Record impairment loss
    debit("Goodwill Impairment Loss", impairment_loss)
    credit("Goodwill", impairment_loss)
```

**IFRS vs US GAAP:**

| Aspect | IFRS (IAS 36) | US GAAP (ASC 350) |
|--------|---------------|-------------------|
| Test Frequency | Annual or when triggered | Annual |
| Steps | Single-step (recoverable amount) | Two-step or qualitative |
| Reversal | Permitted | Prohibited |
| Unit | Cash-generating unit (CGU) | Reporting unit |

## IFRS/US GAAP Reconciliation

### Key Differences

| Topic | IFRS | US GAAP | Impact |
|-------|------|---------|--------|
| Development Costs | Capitalize if criteria met | Expense as incurred | Equity increase under IFRS |
| Goodwill Impairment | Single-step test | Two-step test | Timing difference |
| Lease Classification | Single model (IFRS 16) | Dual model (ASC 842) | Presentation difference |
| Revenue Recognition | IFRS 15 | ASC 606 | Generally aligned |
| Financial Instruments | IFRS 9 | ASC 320/321/815 | Classification differences |

### GAAPDifferenceHandler

```python
from consolidation import GAAPDifferenceHandler

handler = GAAPDifferenceHandler()

# Calculate development costs adjustment
dev_costs_adj = handler.calculate_development_costs_adjustment(
    capitalized_amount=Decimal("500000"),  # IFRS
    expensed_amount=Decimal("500000")       # US GAAP
)

# Calculate goodwill impairment adjustment
goodwill_adj = handler.calculate_goodwill_impairment_adjustment(
    ifrs_impairment=Decimal("100000"),
    us_gaap_impairment=Decimal("150000")
)

# Calculate revenue recognition adjustment
revenue_adj = handler.calculate_revenue_recognition_adjustment(
    ifrs_revenue=Decimal("10000000"),
    us_gaap_revenue=Decimal("9850000")
)
```

### ReconciliationEngine

```python
from consolidation import ReconciliationEngine

recon_engine = ReconciliationEngine()

# Create reconciliation
reconciliation = recon_engine.create_reconciliation(
    ifrs_result=ifrs_consolidated_result,
    us_gaap_result=us_gaap_consolidated_result,
    period_year=2024,
    period_month=12
)

# Generate reconciliation table
table = recon_engine.generate_reconciliation_table(reconciliation)

# Format for disclosure
disclosure = recon_engine.format_reconciliation_disclosure(
    reconciliation,
    format="sec_filing"
)
```

**Reconciliation Format:**

```
Net Income Reconciliation (IFRS to US GAAP)

Net income under IFRS                              $3,000,000

Adjustments to conform to US GAAP:
  Development costs capitalized under IFRS           (500,000)
  Goodwill impairment (US GAAP higher)                (50,000)
  Revenue recognition timing difference               (150,000)
                                                   ───────────
Net income under US GAAP                           $2,300,000
                                                   ═══════════
```

### DualReportingEngine

Prepare financial statements under both standards simultaneously.

```python
from consolidation import DualReportingEngine

dual_engine = DualReportingEngine()

# Prepare dual reporting
dual_result = dual_engine.prepare_dual_reporting(
    entities=entities,
    trial_balances=trial_balances,
    period_end_date=date(2024, 12, 31),
    period_start_date=date(2024, 1, 1),
    presentation_currency=Currency.USD
)

# Access results
ifrs_statements = dual_result.ifrs_statements
us_gaap_statements = dual_result.us_gaap_statements
reconciliation = dual_result.reconciliation
```

## Main Consolidation Engine

### ConsolidationEngine

Orchestrates the complete consolidation process.

```python
from consolidation import ConsolidationEngine

engine = ConsolidationEngine()

# Perform consolidation
result = engine.consolidate(
    entities=entities,
    trial_balances=trial_balances,
    period_end_date=date(2024, 12, 31),
    period_start_date=date(2024, 1, 1),
    presentation_currency=Currency.USD,
    options={
        "perform_eliminations": True,
        "apply_ppa_amortization": True,
        "calculate_cta": True,
        "validate_results": True
    }
)
```

**Consolidation Steps:**

1. **Load Trial Balances** - Load entity trial balances
2. **FX Conversion** - Convert to presentation currency
3. **Intercompany Matching** - Identify IC transactions
4. **Elimination Entries** - Create elimination JEs
5. **PPA Amortization** - Apply monthly amortization
6. **Aggregation** - Sum across entities
7. **CTA Calculation** - Calculate translation adjustment
8. **Validation** - Run validation rules

### QuickConsolidator

Simplified API for common use cases.

```python
from consolidation import QuickConsolidator

consolidator = QuickConsolidator()

result = consolidator.quick_consolidate(
    entities=entities,
    trial_balances=trial_balances,
    period_end_date=date(2024, 12, 31),
    period_start_date=date(2024, 1, 1),
    presentation_currency=Currency.USD
)
```

## Validation Framework

### Validation Rules

The validator runs 7 core validation rules:

1. **Balance Sheet Balance** - Assets = Liabilities + Equity
2. **Debit/Credit Balance** - Total debits = Total credits
3. **Net Income Reconciliation** - Revenue - Expenses = Net Income
4. **Entity Ownership** - Ownership percentages valid
5. **Elimination Completeness** - All IC balances eliminated
6. **FX Rate Consistency** - Valid FX rates used
7. **Financial Reasonableness** - Ratios within expected ranges

### ConsolidationValidator

```python
from consolidation import ConsolidationValidator

validator = ConsolidationValidator()

# Validate all rules
is_valid, results = validator.validate_all(consolidated_result)

# Calculate accuracy score
accuracy = validator.calculate_accuracy_score(consolidated_result)
print(f"Accuracy: {accuracy * 100:.2f}%")

# Generate detailed report
report = validator.generate_validation_report(consolidated_result)
```

**Validation Result:**

```python
{
    "is_valid": True,
    "accuracy_score": 0.998,
    "rules_passed": 7,
    "rules_failed": 0,
    "warnings": [
        "Minor rounding difference in trial balance: $0.02"
    ],
    "errors": [],
    "rule_results": [
        {
            "rule": "balance_sheet_balance",
            "passed": True,
            "total_assets": 50000000.00,
            "total_liabilities": 30000000.00,
            "total_equity": 20000000.00,
            "difference": 0.00
        },
        ...
    ]
}
```

### Individual Validation Rules

#### BalanceSheetBalanceRule

```python
from consolidation.validation import BalanceSheetBalanceRule

rule = BalanceSheetBalanceRule(tolerance=Decimal("0.01"))

result = rule.validate(consolidated_result)
```

**Check:** `Assets = Liabilities + Equity (within tolerance)`

#### DebitCreditBalanceRule

```python
from consolidation.validation import DebitCreditBalanceRule

rule = DebitCreditBalanceRule(tolerance=Decimal("0.01"))

result = rule.validate(trial_balances)
```

**Check:** `Total Debits = Total Credits (within tolerance)`

#### NetIncomeReconciliationRule

```python
from consolidation.validation import NetIncomeReconciliationRule

rule = NetIncomeReconciliationRule(tolerance=Decimal("0.01"))

result = rule.validate(consolidated_result)
```

**Check:** `Revenue - Expenses = Net Income (within tolerance)`

## Performance Characteristics

### Benchmarks

**Test Environment:**
- 7 entities
- 77 total trial balance entries
- Full consolidation with eliminations and PPA

**Results:**
- FX Conversion: <100ms
- Elimination Processing: <50ms
- PPA Amortization: <20ms
- Validation: <50ms
- **Total Consolidation: <200ms**

### Scalability

**Linear Complexity:** O(n) where n = number of entries

**Projected Performance:**

| Entities | Entries | Est. Time |
|----------|---------|-----------|
| 7 | 77 | 200ms |
| 25 | 275 | 700ms |
| 66 | 726 | 1.8s |

### Optimization Tips

1. **Pre-load FX Rates** - Load all rates before consolidation
2. **Batch Processing** - Process entities in parallel
3. **Cache Results** - Cache intermediate calculations
4. **Lazy Loading** - Only load required data
5. **Database Indexes** - Ensure proper indexing on source tables

## Audit Trail

Every consolidation action is logged:

```python
from consolidation import AuditLog

# Automatic logging
log_entry = AuditLog(
    timestamp=datetime.utcnow(),
    action_type="consolidation_started",
    entity_id=None,
    description="Consolidation for period 2024-12",
    previous_value=None,
    new_value=None,
    user_id="system"
)
```

**Logged Actions:**
- Consolidation started/completed
- FX rate applied
- Elimination entry created
- PPA amortization applied
- Validation rule executed
- GAAP adjustment made

## Error Handling

### Exception Hierarchy

```python
ConsolidationException
├── FXRateNotFoundException
├── InvalidTrialBalanceException
├── ValidationException
├── EliminationException
└── PPAException
```

### Example Error Handling

```python
from consolidation.exceptions import FXRateNotFoundException

try:
    result = engine.consolidate(...)
except FXRateNotFoundException as e:
    print(f"Missing FX rate: {e.from_currency} → {e.to_currency} on {e.rate_date}")
    # Load missing rate
except ValidationException as e:
    print(f"Validation failed: {e.rule_name}")
    print(f"Details: {e.details}")
    # Review and fix data
```

## Configuration

### Consolidation Options

```python
options = {
    # FX conversion
    "use_average_rate_for_pl": True,
    "use_closing_rate_for_bs": True,
    "use_historical_rate_for_equity": True,

    # Eliminations
    "perform_eliminations": True,
    "ic_matching_tolerance": Decimal("0.01"),  # 1%

    # PPA
    "apply_ppa_amortization": True,
    "test_goodwill_impairment": False,  # Typically annual

    # Validation
    "validate_results": True,
    "validation_tolerance": Decimal("0.01"),

    # Output
    "include_audit_trail": True,
    "calculate_ratios": True
}
```

## See Also

- [Database Schema](/Volumes/AI/Code/FPA/manual/technical-reference/database.md)
- [API Reference](/Volumes/AI/Code/FPA/manual/technical-reference/api-reference.md)
- [Configuration Reference](/Volumes/AI/Code/FPA/manual/technical-reference/configuration.md)
