# Quick Start Tutorial

This tutorial walks you through running your first monthly consolidation using the AI FP&A system.

## Prerequisites

Ensure you have completed:

1. ✅ [Installation](installation.md) - System installed and verified
2. ✅ Database seeded with portfolio entities and standard CoA
3. ✅ ERP credentials configured in `.env`
4. ✅ Application and Celery worker running

## Tutorial Overview

In this tutorial, you will:

1. Extract trial balances from Effecti's ERP (TOTVS Protheus)
2. Run a simple consolidation for a single entity
3. View the consolidated financial statements
4. Export results to Excel
5. Run a full 7-entity consolidation

**Estimated time**: 15-20 minutes

---

## Part 1: Extract Trial Balance from One Entity

### Step 1: Start Python Interactive Shell

```bash
# Activate virtual environment
source .venv/bin/activate

# Start Python shell
python
```

### Step 2: Extract Trial Balance

```python
from datetime import datetime, date
from src.connectors import create_connector

# Create TOTVS connector for Effecti
connector = create_connector(
    erp_type="totvs_protheus",
    auth_type="oauth2",
    credentials={
        "client_id": "your_totvs_client_id",
        "client_secret": "your_totvs_client_secret"
    },
    config={
        "base_url": "https://api.totvs.com.br",
        "tenant": "your_tenant_id"
    }
)

# Extract trial balance for January 2026
async def extract_trial_balance():
    async with connector:
        # Check connection health
        health = await connector.health_check()
        print(f"Connection status: {health.status}")
        print(f"Latency: {health.latency_ms}ms")

        # Get trial balance
        trial_balance = await connector.get_trial_balance(
            company_id="01",
            period_start=datetime(2026, 1, 1),
            period_end=datetime(2026, 1, 31)
        )

        return trial_balance

# Run extraction
import asyncio
trial_balance = asyncio.run(extract_trial_balance())

# Display summary
print(f"\nTrial Balance Extracted:")
print(f"Company: {trial_balance.company_name}")
print(f"Period: {trial_balance.period_start} to {trial_balance.period_end}")
print(f"Currency: {trial_balance.currency}")
print(f"Number of accounts: {len(trial_balance.accounts)}")
print(f"\nSample accounts:")
for account in trial_balance.accounts[:5]:
    print(f"  {account.account_code} - {account.account_name}: {account.closing_balance:,.2f}")
```

**Expected output:**

```
Connection status: healthy
Latency: 45ms

Trial Balance Extracted:
Company: Effecti
Period: 2026-01-01 00:00:00 to 2026-01-31 00:00:00
Currency: BRL
Number of accounts: 187

Sample accounts:
  1.01.001 - Caixa: 125,430.50
  1.01.002 - Bancos: 2,340,567.89
  1.02.001 - Contas a Receber: 1,890,234.12
  1.03.001 - Estoque: 456,789.00
  2.01.001 - Fornecedores: -890,456.78
```

### Step 3: Save Trial Balance to Database

```python
from src.database import SessionLocal
from src.models import TrialBalanceEntry, AccountType
from decimal import Decimal

# Create database session
db = SessionLocal()

# Map trial balance to database format
for account in trial_balance.accounts:
    entry = TrialBalanceEntry(
        entity_id="effecti-entity-id",  # From portfolio_entities table
        period_year=2026,
        period_month=1,
        period_end_date=date(2026, 1, 31),
        entity_account_id=account.account_code,
        account_type=account.account_type,
        opening_balance=Decimal(str(account.opening_balance)),
        debit_amount=Decimal(str(account.debit_amount)),
        credit_amount=Decimal(str(account.credit_amount)),
        ending_balance=Decimal(str(account.closing_balance)),
        currency=trial_balance.currency
    )
    db.add(entry)

# Commit to database
db.commit()
print(f"✓ Saved {len(trial_balance.accounts)} accounts to database")

# Close session
db.close()
```

**Expected output:**

```
✓ Saved 187 accounts to database
```

---

## Part 2: Run Simple Consolidation

### Step 4: Run Single-Entity Consolidation

```python
from src.consolidation import QuickConsolidator, Entity, Currency
from decimal import Decimal

# Create consolidator
consolidator = QuickConsolidator()

# Define Effecti entity
effecti = Entity(
    entity_id="effecti-entity-id",
    name="Effecti",
    functional_currency=Currency.BRL,
    ownership_percentage=Decimal("100"),
    country_code="BR",
    acquisition_date=date(2024, 3, 15)
)

# Load trial balance from database
from src.database import SessionLocal
db = SessionLocal()

trial_balances = {
    "effecti": db.query(TrialBalanceEntry).filter(
        TrialBalanceEntry.entity_id == effecti.entity_id,
        TrialBalanceEntry.period_year == 2026,
        TrialBalanceEntry.period_month == 1
    ).all()
}

# Run consolidation
result = consolidator.quick_consolidate(
    entities=[effecti],
    trial_balances=trial_balances,
    period_end_date=date(2026, 1, 31),
    period_start_date=date(2026, 1, 1),
    presentation_currency=Currency.USD
)

print(f"\n✓ Consolidation complete")
print(f"Consolidation ID: {result.consolidation_id}")
print(f"Status: {result.status}")
```

**Expected output:**

```
✓ Consolidation complete
Consolidation ID: cons-20260131-effecti
Status: completed
```

### Step 5: View Consolidated Balance Sheet

```python
# Extract Balance Sheet
from src.models import AccountType

balance_sheet = result.consolidated_balances[
    result.consolidated_balances['account_type'].isin([
        AccountType.BALANCE_SHEET_ASSET,
        AccountType.BALANCE_SHEET_LIABILITY,
        AccountType.BALANCE_SHEET_EQUITY
    ])
]

# Calculate totals
assets = balance_sheet[
    balance_sheet['account_type'] == AccountType.BALANCE_SHEET_ASSET
]['ending_balance'].sum()

liabilities = balance_sheet[
    balance_sheet['account_type'] == AccountType.BALANCE_SHEET_LIABILITY
]['ending_balance'].sum()

equity = balance_sheet[
    balance_sheet['account_type'] == AccountType.BALANCE_SHEET_EQUITY
]['ending_balance'].sum()

print(f"\n{'='*50}")
print(f"BALANCE SHEET - Effecti")
print(f"As of January 31, 2026")
print(f"(in USD)")
print(f"{'='*50}\n")
print(f"Total Assets:              ${assets:,.2f}")
print(f"Total Liabilities:         ${liabilities:,.2f}")
print(f"Total Equity:              ${equity:,.2f}")
print(f"{'-'*50}")
print(f"Liabilities + Equity:      ${liabilities + equity:,.2f}")
print(f"\nBalance Check: {'✓ PASSED' if abs(assets - (liabilities + equity)) < 0.01 else '✗ FAILED'}")
```

**Expected output:**

```
==================================================
BALANCE SHEET - Effecti
As of January 31, 2026
(in USD)
==================================================

Total Assets:              $1,234,567.89
Total Liabilities:         $456,789.12
Total Equity:              $777,778.77
--------------------------------------------------
Liabilities + Equity:      $1,234,567.89

Balance Check: ✓ PASSED
```

### Step 6: View Consolidated P&L

```python
# Extract P&L
pl_statement = result.consolidated_balances[
    result.consolidated_balances['account_type'].isin([
        AccountType.PL_REVENUE,
        AccountType.PL_COGS,
        AccountType.PL_OPERATING_EXPENSE,
        AccountType.PL_OTHER_INCOME,
        AccountType.PL_OTHER_EXPENSE
    ])
]

# Calculate totals
revenue = pl_statement[
    pl_statement['account_type'] == AccountType.PL_REVENUE
]['ending_balance'].sum()

cogs = pl_statement[
    pl_statement['account_type'] == AccountType.PL_COGS
]['ending_balance'].sum()

opex = pl_statement[
    pl_statement['account_type'] == AccountType.PL_OPERATING_EXPENSE
]['ending_balance'].sum()

gross_profit = revenue + cogs  # COGS is negative
operating_income = gross_profit + opex  # OPEX is negative

print(f"\n{'='*50}")
print(f"PROFIT & LOSS - Effecti")
print(f"For the month ended January 31, 2026")
print(f"(in USD)")
print(f"{'='*50}\n")
print(f"Revenue:                   ${revenue:,.2f}")
print(f"Cost of Goods Sold:        ${cogs:,.2f}")
print(f"{'-'*50}")
print(f"Gross Profit:              ${gross_profit:,.2f}")
print(f"Gross Margin:              {(gross_profit/revenue)*100:.1f}%\n")
print(f"Operating Expenses:        ${opex:,.2f}")
print(f"{'-'*50}")
print(f"Operating Income:          ${operating_income:,.2f}")
print(f"Operating Margin:          {(operating_income/revenue)*100:.1f}%")
```

**Expected output:**

```
==================================================
PROFIT & LOSS - Effecti
For the month ended January 31, 2026
(in USD)
==================================================

Revenue:                   $890,456.78
Cost of Goods Sold:        $-234,567.89
--------------------------------------------------
Gross Profit:              $655,888.89
Gross Margin:              73.7%

Operating Expenses:        $-345,678.90
--------------------------------------------------
Operating Income:          $310,209.99
Operating Margin:          34.8%
```

---

## Part 3: Export to Excel

### Step 7: Generate Excel Report

```python
from src.reporting import ExcelReportGenerator

# Create report generator
report_gen = ExcelReportGenerator()

# Generate Excel file
output_file = report_gen.generate_consolidated_report(
    consolidation_result=result,
    output_path="./reports/effecti_jan2026.xlsx",
    include_variance_analysis=False  # No prior period for comparison yet
)

print(f"\n✓ Excel report generated: {output_file}")
print(f"File size: {os.path.getsize(output_file) / 1024:.1f} KB")
```

**Expected output:**

```
✓ Excel report generated: ./reports/effecti_jan2026.xlsx
File size: 127.3 KB
```

### Step 8: Open and Review Report

```bash
# Open Excel file (macOS)
open ./reports/effecti_jan2026.xlsx

# Open Excel file (Linux)
xdg-open ./reports/effecti_jan2026.xlsx

# Open Excel file (Windows)
start ./reports/effecti_jan2026.xlsx
```

The Excel file contains these sheets:

1. **Summary** - Key financial metrics
2. **Balance Sheet** - Consolidated balance sheet
3. **P&L Statement** - Consolidated income statement
4. **Trial Balance** - Detailed account balances
5. **FX Rates** - Exchange rates used
6. **Audit Log** - Consolidation steps taken

---

## Part 4: Full 7-Entity Consolidation

### Step 9: Extract All 7 Trial Balances

```python
from src.connectors import get_erp_for_company

# Portfolio companies
companies = [
    "effecti", "mercos", "datahub", "onclick",
    "ipe_digital", "munddi", "leadlovers"
]

# Extract trial balances for all companies
async def extract_all_trial_balances():
    all_trial_balances = {}

    for company in companies:
        print(f"Extracting {company}...")

        # Get ERP type for company
        erp_type = get_erp_for_company(company)

        # Create connector (credentials from environment)
        connector = create_connector(
            erp_type=erp_type.value,
            auth_type="oauth2",  # or appropriate auth type
            credentials={...},  # From environment
            config={...}
        )

        # Extract trial balance
        async with connector:
            trial_balance = await connector.get_trial_balance(
                company_id="01",
                period_start=datetime(2026, 1, 1),
                period_end=datetime(2026, 1, 31)
            )

            all_trial_balances[company] = trial_balance
            print(f"  ✓ {len(trial_balance.accounts)} accounts extracted")

    return all_trial_balances

# Run extraction
all_trial_balances = asyncio.run(extract_all_trial_balances())
print(f"\n✓ Extracted trial balances for {len(all_trial_balances)} companies")
```

**Expected output:**

```
Extracting effecti...
  ✓ 187 accounts extracted
Extracting mercos...
  ✓ 156 accounts extracted
Extracting datahub...
  ✓ 142 accounts extracted
Extracting onclick...
  ✓ 198 accounts extracted
Extracting ipe_digital...
  ✓ 134 accounts extracted
Extracting munddi...
  ✓ 167 accounts extracted
Extracting leadlovers...
  ✓ 179 accounts extracted

✓ Extracted trial balances for 7 companies
```

### Step 10: Run Full Consolidation

```python
from src.consolidation import ConsolidationEngine
from src.consolidation.fx_converter import create_sample_rates

# Create consolidation engine
engine = ConsolidationEngine(
    presentation_currency=Currency.USD,
    accounting_standard=AccountingStandard.IFRS
)

# Load FX rates
create_sample_rates(engine.fx_rate_manager, date(2026, 1, 31))

# Register all entities
for entity in all_entities:
    engine.register_entity(entity)

# Load all trial balances
for entity_id, trial_balance in all_trial_balances.items():
    engine.load_trial_balance(entity_id, trial_balance)

# Define chart of accounts for eliminations
coa = {
    "IC_RECEIVABLE": "1200",
    "IC_PAYABLE": "2100",
    "IC_REVENUE": "4100",
    "IC_EXPENSE": "5200",
    "FX_GAIN_LOSS": "7100"
}

# Run consolidation
print("Running full consolidation...")
consolidated = engine.consolidate(
    period_end_date=date(2026, 1, 31),
    period_start_date=date(2026, 1, 1),
    chart_of_accounts=coa,
    include_gaap_reconciliation=False
)

print(f"\n✓ Consolidation complete")
print(f"Entities consolidated: {len(all_entities)}")
print(f"Intercompany eliminations: {len(consolidated.eliminations)}")
print(f"Total assets (USD): ${consolidated.total_assets:,.2f}")
print(f"Total revenue (USD): ${consolidated.total_revenue:,.2f}")
```

**Expected output:**

```
Running full consolidation...
Processing entity: Effecti
Processing entity: Mercos
Processing entity: Datahub
Processing entity: OnClick
Processing entity: Ipê Digital
Processing entity: Munddi
Processing entity: Leadlovers

Performing FX conversion...
Identifying intercompany transactions...
  Found 23 intercompany pairs
  Eliminated $456,789.12 in intercompany balances

Applying PPA amortization...
  3 active PPA schedules
  Monthly amortization: $12,345.67

Calculating consolidated balances...

✓ Consolidation complete
Entities consolidated: 7
Intercompany eliminations: 23
Total assets (USD): $15,234,567.89
Total revenue (USD): $3,456,789.01
```

### Step 11: Validate Consolidation

```python
from src.consolidation.validation import ConsolidationValidator

# Create validator
validator = ConsolidationValidator()

# Run all validation checks
is_valid, results = validator.validate_all(consolidated)

# Display validation results
print(f"\n{'='*60}")
print(f"VALIDATION REPORT")
print(f"{'='*60}\n")

for check_name, check_result in results.items():
    status = "✓ PASS" if check_result['passed'] else "✗ FAIL"
    print(f"{status} - {check_name}")
    if not check_result['passed']:
        print(f"  Error: {check_result['message']}")

# Calculate accuracy score
accuracy = validator.calculate_accuracy_score(consolidated)
print(f"\n{'='*60}")
print(f"Overall Accuracy Score: {accuracy*100:.2f}%")
print(f"Target: 99.9%")
print(f"Status: {'✓ PASSED' if accuracy >= 0.999 else '✗ FAILED'}")
print(f"{'='*60}")
```

**Expected output:**

```
============================================================
VALIDATION REPORT
============================================================

✓ PASS - Balance Sheet Balance Check
✓ PASS - Debit/Credit Balance Check
✓ PASS - Net Income Reconciliation
✓ PASS - Entity Ownership Validation
✓ PASS - Elimination Completeness
✓ PASS - FX Rate Consistency
✓ PASS - Financial Reasonableness

============================================================
Overall Accuracy Score: 99.95%
Target: 99.9%
Status: ✓ PASSED
============================================================
```

### Step 12: Generate Full Report Package

```python
from src.reporting import ReportPackageGenerator

# Create report package
package_gen = ReportPackageGenerator()

# Generate all reports
output_dir = package_gen.generate_full_package(
    consolidation_result=consolidated,
    output_dir="./reports/jan2026_full/",
    include_excel=True,
    include_powerpoint=True,
    include_pdf=True
)

print(f"\n✓ Report package generated")
print(f"Output directory: {output_dir}")
print(f"\nGenerated files:")
for file in os.listdir(output_dir):
    size_kb = os.path.getsize(os.path.join(output_dir, file)) / 1024
    print(f"  - {file} ({size_kb:.1f} KB)")
```

**Expected output:**

```
✓ Report package generated
Output directory: ./reports/jan2026_full/

Generated files:
  - consolidated_financials.xlsx (234.5 KB)
  - executive_summary.pptx (1,567.8 KB)
  - board_package.pdf (2,345.6 KB)
  - variance_analysis.xlsx (156.7 KB)
  - audit_trail.xlsx (89.2 KB)
```

---

## Part 5: Automated Monthly Close

### Step 13: Schedule Automated Close

```python
from src.orchestration import MonthlyCloseOrchestrator

# Create orchestrator
orchestrator = MonthlyCloseOrchestrator()

# Schedule monthly close
job_id = orchestrator.schedule_monthly_close(
    entities=all_entities,
    period_year=2026,
    period_month=2,  # Schedule for next month (February)
    trigger_date=date(2026, 3, 1),  # Run on March 1st
    trigger_time="06:00:00"  # 6 AM UTC
)

print(f"✓ Monthly close scheduled")
print(f"Job ID: {job_id}")
print(f"Trigger: March 1, 2026 at 6:00 AM UTC")
print(f"Entities: {len(all_entities)}")
```

**Expected output:**

```
✓ Monthly close scheduled
Job ID: monthly-close-202602
Trigger: March 1, 2026 at 6:00 AM UTC
Entities: 7
```

---

## Next Steps

Congratulations! You've successfully:

- ✅ Extracted trial balances from an ERP system
- ✅ Run a single-entity consolidation
- ✅ Run a full 7-entity consolidation with intercompany eliminations
- ✅ Validated consolidation accuracy (99.95%)
- ✅ Generated Excel, PowerPoint, and PDF reports
- ✅ Scheduled automated monthly close

### Continue Learning

- **[User Guide](../user-guide/)** - Learn advanced features
- **[Architecture Deep Dive](architecture.md)** - Understand system internals
- **[API Documentation](../technical-reference/api.md)** - Integrate with other systems
- **[Troubleshooting](../user-guide/troubleshooting.md)** - Common issues and solutions

### Common Next Steps

1. **Configure email distribution**: Set up automatic report delivery
2. **Create custom reports**: Build entity-specific or executive dashboards
3. **Add new entities**: Onboard new portfolio companies
4. **Enable variance analysis**: Configure budget data for budget vs actual
5. **Set up monitoring**: Configure CloudWatch alarms and dashboards

---

## Troubleshooting

### Trial Balance Extraction Fails

**Problem**: ERP connection timeout or authentication error

```python
# Check connection health
health = await connector.health_check()
print(f"Status: {health.status}")
print(f"Message: {health.message}")

# Verify credentials
import os
print(f"Client ID: {os.getenv('TOTVS_CLIENT_ID')[:10]}...")
```

### Consolidation Balance Sheet Doesn't Balance

**Problem**: Assets ≠ Liabilities + Equity

```python
# Get detailed validation report
report = validator.generate_validation_report(consolidated)
print(report)

# Check for missing accounts
print(f"Total accounts: {len(consolidated.consolidated_balances)}")
print(f"Asset accounts: {len(consolidated.get_accounts_by_type('ASSET'))}")
print(f"Liability accounts: {len(consolidated.get_accounts_by_type('LIABILITY'))}")
```

### Excel Export Fails

**Problem**: Permission denied or file in use

```bash
# Check output directory exists
mkdir -p ./reports

# Verify write permissions
touch ./reports/test.txt && rm ./reports/test.txt

# Close Excel if file is open
```

---

## Support

For help with this tutorial:

- **Documentation**: Review [Installation](installation.md) and [Requirements](requirements.md)
- **API Documentation**: See [Technical Reference](../technical-reference/)
- **GitHub Issues**: File a bug report

---

**Time to completion**: Under 20 minutes ✨
