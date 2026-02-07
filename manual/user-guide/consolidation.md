# Consolidation Workflow

## Overview

The consolidation process transforms trial balances from 7 portfolio companies (in BRL) into a single consolidated financial statement (in USD) compliant with IFRS and US GAAP standards.

**Consolidation Components:**
1. Multi-currency FX conversion
2. Intercompany elimination
3. Purchase Price Allocation (PPA) amortization
4. IFRS/US GAAP reconciliation
5. Comprehensive validation

**Target Accuracy:** 99.9%
**Processing Time:** 10-15 minutes for 7 companies

## Consolidation Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  CONSOLIDATION ENGINE                        │
│                                                               │
│  INPUT                                                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Effecti  │  │  Mercos  │  │ Datahub  │  │  Others  │    │
│  │  (BRL)   │  │  (BRL)   │  │  (BRL)   │  │  (BRL)   │    │
│  │ 1,248 LE │  │ 1,089 LE │  │ 1,201 LE │  │ 3,479 LE │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       │             │              │             │           │
│       └─────────────┴──────────────┴─────────────┘           │
│                          │                                    │
│  ┌───────────────────────▼─────────────────────────┐         │
│  │  STEP 1: FX CONVERSION (IFRS 21 / ASC 830)      │         │
│  │  - Balance Sheet: Closing rate (0.1895)         │         │
│  │  - P&L: Average rate (0.1872)                   │         │
│  │  - Equity: Historical rate                      │         │
│  │  - CTA Calculation                              │         │
│  └───────────────────────┬─────────────────────────┘         │
│                          │                                    │
│  ┌───────────────────────▼─────────────────────────┐         │
│  │  STEP 2: INTERCOMPANY ELIMINATION               │         │
│  │  - Match IC Receivables/Payables                │         │
│  │  - Match IC Revenue/Expense                     │         │
│  │  - Eliminate dividends                          │         │
│  │  - FX Gain/Loss recognition                     │         │
│  └───────────────────────┬─────────────────────────┘         │
│                          │                                    │
│  ┌───────────────────────▼─────────────────────────┐         │
│  │  STEP 3: PPA AMORTIZATION                       │         │
│  │  - Goodwill tracking                            │         │
│  │  - Intangible amortization                      │         │
│  │  - Impairment testing                           │         │
│  └───────────────────────┬─────────────────────────┘         │
│                          │                                    │
│  ┌───────────────────────▼─────────────────────────┐         │
│  │  STEP 4: VALIDATION                             │         │
│  │  - Balance sheet balance                        │         │
│  │  - Debit/credit equality                        │         │
│  │  - Net income reconciliation                    │         │
│  │  - Reasonableness checks                        │         │
│  └───────────────────────┬─────────────────────────┘         │
│                          │                                    │
│  OUTPUT: Consolidated Financials (USD)                       │
│  ┌──────────────────────────────────────────────┐            │
│  │ Assets:       USD 28,450,000                 │            │
│  │ Liabilities:  USD 15,230,000                 │            │
│  │ Equity:       USD 13,220,000                 │            │
│  │ Revenue:      USD  3,625,000                 │            │
│  │ Expenses:     USD  2,810,000                 │            │
│  │ Net Income:   USD    815,000                 │            │
│  └──────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

## Step 1: FX Conversion

### Overview

All portfolio companies use Brazilian Real (BRL) as their functional currency. Consolidation requires conversion to USD presentation currency following IFRS 21 (IAS 21) and ASC 830.

### FX Rate Types

| Rate Type | Used For | Source | Example |
|-----------|----------|--------|---------|
| **Closing** | Balance sheet items | BCB PTAX end-of-period | 0.1895 |
| **Average** | P&L items | BCB PTAX monthly average | 0.1872 |
| **Historical** | Equity items, Acquired assets | BCB PTAX at transaction date | 0.1850 |

### FX Conversion Rules

#### Balance Sheet Items

**Assets and Liabilities** use **closing rate** at period end:

```python
# Example: Cash balance
cash_brl = Decimal("500000")          # BRL 500,000
closing_rate = Decimal("0.1895")      # 1 BRL = 0.1895 USD
cash_usd = cash_brl * closing_rate    # USD 94,750
```

**Equity Items** use **historical rate** at transaction date:

```python
# Example: Capital stock (issued Aug 1, 2023)
capital_brl = Decimal("10000000")     # BRL 10,000,000
historical_rate = Decimal("0.1850")   # Rate on Aug 1, 2023
capital_usd = capital_brl * historical_rate  # USD 1,850,000
```

#### P&L Items

**Revenue and Expenses** use **average rate** for the period:

```python
# Example: Monthly revenue
revenue_brl = Decimal("1500000")      # BRL 1,500,000
average_rate = Decimal("0.1872")      # Jan 2026 average
revenue_usd = revenue_brl * average_rate  # USD 280,800
```

### Cumulative Translation Adjustment (CTA)

The difference between closing rate translation and historical rate translation creates a **Cumulative Translation Adjustment** in equity.

**CTA Calculation:**

```python
# Balance sheet translated at closing rate
assets_closing = total_assets_brl * closing_rate
liabilities_closing = total_liabilities_brl * closing_rate
equity_closing = assets_closing - liabilities_closing

# Equity at historical rates + retained earnings
equity_historical = capital_stock_historical + retained_earnings_historical

# CTA is the plug
cta = equity_closing - equity_historical
```

**Example:**

```
Assets (BRL 50M × 0.1895):           USD 9,475,000
Liabilities (BRL 30M × 0.1895):      USD 5,685,000
Net Assets at Closing:               USD 3,790,000

Capital Stock (BRL 10M × 0.1850):    USD 1,850,000
Retained Earnings (historical):      USD 1,800,000
Total Historical Equity:             USD 3,650,000

CTA (plug):                          USD   140,000
```

The CTA of USD 140,000 represents unrealized FX gain from BRL appreciation.

### FX Rate Management

#### Loading FX Rates

```bash
# Load BCB PTAX rates automatically
python -m src.fx.load_rates \
  --source bcb_ptax \
  --date "2026-01-31" \
  --rate-type closing

python -m src.fx.load_rates \
  --source bcb_ptax \
  --period "2026-01-01:2026-01-31" \
  --rate-type average
```

#### Manual FX Rate Entry

If automatic loading fails:

```python
from src.consolidation import FXRateManager, FXRate, Currency, FXRateType
from datetime import date
from decimal import Decimal

fx_manager = FXRateManager()

# Add closing rate
fx_manager.add_rate(FXRate(
    from_currency=Currency.BRL,
    to_currency=Currency.USD,
    rate_date=date(2026, 1, 31),
    rate_type=FXRateType.CLOSING,
    rate=Decimal("0.1895"),
    source="BCB PTAX 31-Jan-2026"
))

# Add average rate
fx_manager.add_rate(FXRate(
    from_currency=Currency.BRL,
    to_currency=Currency.USD,
    rate_date=date(2026, 1, 31),
    rate_type=FXRateType.AVERAGE,
    rate=Decimal("0.1872"),
    source="BCB PTAX Jan 2026 Average"
))
```

#### Verify FX Rates

```bash
# List loaded rates
python -m src.fx.list_rates --period "2026-01"

# Expected output:
# Date       Type     From  To   Rate     Source
# 2026-01-31 CLOSING  BRL   USD  0.1895   BCB PTAX
# 2026-01-31 AVERAGE  BRL   USD  0.1872   BCB PTAX (avg)
```

## Step 2: Intercompany Elimination

### Overview

Intercompany (IC) transactions between portfolio companies must be eliminated to avoid double-counting in consolidated financials.

**Elimination Categories:**
1. IC Receivables/Payables
2. IC Revenue/Expense
3. IC Dividends
4. IC Equity Investments

### IC Receivables/Payables Elimination

**Matching Algorithm:**

1. **Identify IC accounts** using account code prefixes (e.g., 1.02.005 = IC Receivable)
2. **Match by reference number** (invoice number, transaction ID)
3. **Match by amount** within FX tolerance (default 1%)
4. **Verify entity relationship** (legal entity parent/subsidiary structure)

**Example:**

```
Company A (Effecti):
  Account: 1.02.005 - IC Receivable from Mercos
  Amount: BRL 100,000 (USD 18,950 @ 0.1895)
  Reference: INV-2026-0123
  Date: 2026-01-15

Company B (Mercos):
  Account: 2.02.003 - IC Payable to Effecti
  Amount: BRL 100,000 (USD 18,950 @ 0.1895)
  Reference: INV-2026-0123
  Date: 2026-01-15

Match: ✓ Reference matches, amounts match exactly

Elimination Journal Entry:
  DR: IC Payable (Mercos)         USD 18,950
  CR: IC Receivable (Effecti)     USD 18,950
  Memo: Eliminate IC invoice INV-2026-0123
```

### FX Tolerance Matching

Due to FX rate differences (transaction date vs. period end), amounts may not match exactly.

**Example with FX difference:**

```
Company A (Effecti):
  IC Receivable: BRL 100,000
  Booked at: 0.1880 (Jan 15 rate)
  Balance: USD 18,800

Company B (Mercos):
  IC Payable: BRL 100,000
  Booked at: 0.1885 (Jan 16 rate)
  Balance: USD 18,850

Difference: USD 50 (0.27% variance - within 1% tolerance)

Elimination Entry:
  DR: IC Payable (Mercos)         USD 18,850
  CR: IC Receivable (Effecti)     USD 18,800
  CR: FX Gain/Loss                USD     50
  Memo: Eliminate IC + recognize FX difference
```

### IC Revenue/Expense Elimination

**Example: Software License**

```
Company A (Effecti) - SaaS Provider:
  IC Revenue: BRL 50,000 (USD 9,360 @ avg rate 0.1872)
  Customer: Mercos (internal)
  Service: Platform License

Company B (Mercos):
  IC Expense: BRL 50,000 (USD 9,360 @ avg rate 0.1872)
  Vendor: Effecti (internal)
  Category: Software Expense

Elimination Entry:
  DR: IC Revenue (Effecti)        USD 9,360
  CR: IC Expense (Mercos)         USD 9,360
  Memo: Eliminate internal software license
```

### IC Dividend Elimination

Dividends paid between portfolio companies are eliminated:

```
Company A (Leadlovers):
  Dividend Paid: BRL 200,000 (USD 37,440 @ avg rate 0.1872)
  To: Nuvini Group Limited (parent)

Parent (Nuvini Group):
  Dividend Income: USD 37,440
  From: Leadlovers

Elimination Entry:
  DR: Dividend Income (Parent)    USD 37,440
  CR: Dividend Expense (Sub)      USD 37,440
  Memo: Eliminate intra-group dividend
```

### Viewing Elimination Report

```bash
# Generate IC elimination report
python -m src.reporting.eliminations \
  --period "2026-01-31" \
  --output eliminations_report.xlsx

# Summary statistics
python -m src.cli.eliminations_summary \
  --period "2026-01-31"
```

**Example output:**

```
Intercompany Elimination Summary - January 2026

Category              Matches   Amount (USD)   Unmatched
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Receivables/Payables     45      1,847,500        2
Revenue/Expense          38        485,000         1
Dividends                 3        125,000         0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total                    86      2,457,500         3

Unmatched Items Requiring Review:
1. Effecti IC Receivable USD 12,500 (no matching payable)
2. Mercos IC Expense USD 8,400 (no matching revenue)
3. Datahub IC Payable USD 5,200 (amount mismatch 8.5%)
```

### Handling Unmatched Items

**Scenario 1: Timing Difference**

IC transaction recorded in one entity but not the other (accrual vs. cash basis).

**Solution:** Accept as unmatched, will reconcile in next period.

**Scenario 2: Amount Mismatch > Tolerance**

FX difference exceeds 1% tolerance or incorrect amount.

**Solution:**
1. Investigate root cause
2. Create adjustment entry to reconcile
3. Escalate to CFO if material

**Scenario 3: Missing Transaction**

IC transaction recorded in one entity, no evidence in counterparty.

**Solution:**
1. Verify with entity finance teams
2. Create manual adjustment if confirmed error
3. Update ERP data if necessary

## Step 3: PPA Amortization

### Overview

For acquired portfolio companies, Purchase Price Allocation (PPA) amortization must be recorded monthly in consolidated financials.

### PPA Components

**Example: Leadlovers (acquired August 2023)**

```
Purchase Price:                      USD 15,000,000
Fair Value of Net Assets:            USD  8,000,000
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Excess Purchase Price:               USD  7,000,000

Allocation:
  Customer Relationships (8 years)   USD  4,000,000
  SaaS Platform Tech (5 years)       USD  2,000,000
  Brand (10 years)                   USD    500,000
  ─────────────────────────────────────────────────
  Identified Intangibles:            USD  6,500,000

  Goodwill (not amortized):          USD    500,000
```

### Monthly Amortization Calculation

**Customer Relationships:**
```
Cost: USD 4,000,000
Life: 8 years (96 months)
Monthly Amortization: USD 4,000,000 / 96 = USD 41,667
```

**SaaS Platform Technology:**
```
Cost: USD 2,000,000
Life: 5 years (60 months)
Monthly Amortization: USD 2,000,000 / 60 = USD 33,333
```

**Brand:**
```
Cost: USD 500,000
Life: 10 years (120 months)
Monthly Amortization: USD 500,000 / 120 = USD 4,167
```

**Total Monthly PPA Amortization:** USD 79,167

### PPA Journal Entry

```
Journal Entry: JE-PPA-LEADLOVERS-2026-01
Date: 2026-01-31
Type: PPA Amortization

DR: Amortization Expense - Customer Relationships   USD 41,667
DR: Amortization Expense - Technology               USD 33,333
DR: Amortization Expense - Brand                    USD  4,167
CR: Accumulated Amortization - Customer Rel.        USD 41,667
CR: Accumulated Amortization - Technology           USD 33,333
CR: Accumulated Amortization - Brand                USD  4,167

Memo: Monthly PPA amortization for Leadlovers acquisition
```

### Goodwill Impairment Testing

**Frequency:** Annual (December) or when impairment indicators exist

**Qualitative Indicators:**
- Significant adverse change in business climate
- Adverse financial performance
- Increased competition
- Loss of key personnel
- Legal or regulatory changes

**Quantitative Test:**

Compare carrying amount to recoverable amount:

```
Goodwill Carrying Amount:    USD 500,000
Recoverable Amount:          USD 450,000 (from valuation)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Impairment Loss:            USD  50,000

Impairment Journal Entry:
  DR: Goodwill Impairment Loss    USD 50,000
  CR: Goodwill                    USD 50,000
```

### View PPA Schedule

```bash
# View PPA amortization schedule
python -m src.ppa.schedule \
  --entity leadlovers \
  --output leadlovers_ppa.xlsx

# Get monthly PPA entries
python -m src.ppa.monthly_entries \
  --period "2026-01-31"
```

## Step 4: Validation

### Validation Rules

The consolidation engine runs comprehensive validation to ensure 99.9% accuracy:

#### 1. Balance Sheet Balance

**Rule:** Assets = Liabilities + Equity (±$0.01)

```python
assets = sum(accounts where account_type == ASSET)
liabilities = sum(accounts where account_type == LIABILITY)
equity = sum(accounts where account_type == EQUITY)

difference = assets - (liabilities + equity)

if abs(difference) > 0.01:
    FAIL: "Balance sheet doesn't balance: ${difference}"
```

#### 2. Debit/Credit Equality

**Rule:** Total Debits = Total Credits (±$0.01)

```python
total_debits = sum(entry.debit_amount for all entries)
total_credits = sum(entry.credit_amount for all entries)

difference = total_debits - total_credits

if abs(difference) > 0.01:
    FAIL: "Debits don't equal credits: ${difference}"
```

#### 3. Net Income Reconciliation

**Rule:** Net Income = Revenue - Expenses

```python
revenue = sum(accounts where account_type == REVENUE)
expenses = sum(accounts where account_type == EXPENSE)
net_income_calculated = revenue - expenses

net_income_reported = get_account("3.05.001")  # Retained Earnings change

difference = net_income_calculated - net_income_reported

if abs(difference) > 0.01:
    FAIL: "Net income doesn't reconcile: ${difference}"
```

#### 4. FX Rate Consistency

**Rule:** All entities use same FX rates for period

```python
for entity in entities:
    closing_rate = get_fx_rate(entity.currency, USD, CLOSING, period_end)
    if closing_rate != expected_closing_rate:
        WARN: "Entity {entity} using different closing rate"
```

#### 5. Elimination Completeness

**Rule:** All IC transactions matched (within tolerance)

```python
unmatched_ic = get_unmatched_intercompany_items()

if len(unmatched_ic) > 0:
    WARN: f"{len(unmatched_ic)} unmatched IC items"

if sum(unmatched_ic.amounts) > materiality_threshold:
    FAIL: "Material unmatched IC transactions"
```

#### 6. Reasonableness Checks

**Cash Balance:**
```python
if cash_balance < 0:
    ERROR: "Negative cash balance"

if cash_balance > total_assets * 0.50:
    WARN: "Cash > 50% of assets (unusual)"
```

**Revenue Growth:**
```python
revenue_growth = (current_revenue - prior_revenue) / prior_revenue

if revenue_growth > 0.50:
    WARN: "Revenue grew >50% MoM (verify)"

if revenue_growth < -0.30:
    WARN: "Revenue declined >30% MoM (verify)"
```

### Validation Report

```bash
# Generate validation report
python -m src.reporting.validation_report \
  --period "2026-01-31" \
  --output validation.html
```

**Example validation results:**

```
Consolidation Validation Report
Period: January 2026

PASS ✓  Balance Sheet Balance
        Assets: USD 28,450,123.45
        Liabilities + Equity: USD 28,450,123.45
        Difference: USD 0.00

PASS ✓  Debit/Credit Equality
        Total Debits: USD 35,678,234.56
        Total Credits: USD 35,678,234.56
        Difference: USD 0.00

PASS ✓  Net Income Reconciliation
        Revenue: USD 3,625,000.00
        Expenses: USD 2,810,000.00
        Net Income (calculated): USD 815,000.00
        Net Income (reported): USD 815,000.00
        Difference: USD 0.00

PASS ✓  FX Rate Consistency
        All entities using BRL/USD 0.1895 (closing)
        All entities using BRL/USD 0.1872 (average)

WARN ⚠  Elimination Completeness
        86 IC transactions matched
        3 IC transactions unmatched (USD 26,100)
        Below materiality threshold (USD 500,000)

PASS ✓  Reasonableness - Cash Balance
        Cash: USD 2,450,000 (8.6% of assets)
        Within normal range

WARN ⚠  Reasonableness - Revenue Growth
        Current: USD 3,625,000
        Prior: USD 3,450,000
        Growth: +5.1% (normal)

Overall Score: 99.94% (Target: 99.9%)
Status: ✓ PASS
```

## Consolidation Commands

### Quick Consolidation

```bash
# Run full consolidation
python -m src.consolidation.run \
  --period-end "2026-01-31" \
  --period-start "2026-01-01" \
  --presentation-currency USD \
  --output consolidated_jan2026.xlsx
```

### Step-by-Step Consolidation

```bash
# Step 1: FX Conversion
python -m src.consolidation.fx_convert \
  --period "2026-01-31" \
  --closing-rate 0.1895 \
  --average-rate 0.1872

# Step 2: Intercompany Elimination
python -m src.consolidation.eliminate \
  --period "2026-01-31" \
  --tolerance 0.01

# Step 3: PPA Amortization
python -m src.consolidation.ppa_amortize \
  --period "2026-01-31"

# Step 4: Aggregate & Validate
python -m src.consolidation.aggregate \
  --period "2026-01-31" \
  --validate
```

### View Consolidation Results

```bash
# Consolidated trial balance
python -m src.cli.consolidated_tb \
  --period "2026-01-31" \
  --format excel

# Consolidation journal entries
python -m src.cli.consolidation_journal \
  --period "2026-01-31" \
  --type all

# Audit trail
python -m src.cli.audit_trail \
  --period "2026-01-31" \
  --filter consolidation
```

## Troubleshooting

### Issue: Balance Sheet Doesn't Balance

**Symptom:** Validation fails with "Assets ≠ Liabilities + Equity"

**Diagnostic steps:**

1. Check if all entities extracted successfully
2. Verify FX conversion completed for all entities
3. Review elimination entries for errors
4. Check for missing PPA entries

```bash
# Run diagnostic
python -m src.consolidation.diagnose \
  --period "2026-01-31" \
  --issue balance_sheet
```

### Issue: Large Unmatched IC Transactions

**Symptom:** Many IC transactions not eliminated

**Solutions:**

1. **Check tolerance setting:**
   ```bash
   # Increase FX tolerance to 2%
   python -m src.consolidation.eliminate \
     --period "2026-01-31" \
     --tolerance 0.02
   ```

2. **Review matching logic:**
   ```bash
   # View unmatched IC items
   python -m src.cli.unmatched_ic \
     --period "2026-01-31"
   ```

3. **Manual reconciliation:**
   ```bash
   # Create manual elimination entry
   python -m src.journal.create_entry \
     --type ic_elimination \
     --debit "2.02.003:18500" \
     --credit "1.02.005:18500" \
     --memo "Manual IC elimination - timing difference"
   ```

### Issue: CTA Variance

**Symptom:** CTA amount different from expected

**Diagnostic:**

1. Verify historical rates loaded correctly
2. Check retained earnings balance
3. Review prior period CTA

```bash
# CTA reconciliation report
python -m src.fx.cta_reconciliation \
  --period "2026-01-31"
```

## Best Practices

1. **Load FX Rates Early:** Load rates immediately after month-end
2. **Validate Entity Data:** Ensure all trial balances balance before consolidation
3. **Review Eliminations:** Always review unmatched IC items
4. **Document Adjustments:** All manual entries need detailed memos
5. **Archive Results:** Save consolidated trial balance before making changes
6. **Run Validation:** Always run full validation before closing period

## Next Steps

- [Monthly Close Process](monthly-close.md) - Full monthly close workflow
- [Human Review Guide](human-review.md) - Review and approval process
- [Reports Guide](reports.md) - Generate consolidated reports

---

**Last Updated:** February 7, 2026
**Version:** 1.0.0
