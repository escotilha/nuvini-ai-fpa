# Monthly Close Process

## Overview

The monthly close process is the core workflow of the AI FP&A system. This guide walks you through the step-by-step process of completing a monthly financial close across all portfolio companies.

**Timeline:** 3-5 business days (vs. 10-15 days manual)
**Automation Rate:** 85-90%
**Human Review:** 10-15% of transactions

## Prerequisites

Before starting the monthly close:

- [ ] All portfolio company ERPs are accessible
- [ ] Month-end dates are confirmed (typically last day of month)
- [ ] FX rates are available for period-end and average
- [ ] Prior period close is complete and approved
- [ ] Reviewers are available for approval workflow

## Monthly Close Timeline

```
Day 1: Data Extraction
  → ERP connectors pull trial balances
  → Data quality validation
  → Initial load to raw_data tables

Day 2: Consolidation
  → FX conversion (BRL → USD)
  → Intercompany elimination matching
  → PPA amortization entries
  → Consolidated trial balance generation

Day 3: Review & Validation
  → Human review of yellow/red risk items
  → Variance analysis vs. budget/prior period
  → Adjustment entries (if needed)

Day 4: Final Approval
  → CFO review of consolidated financials
  → Four-eyes sign-off on material items
  → Period close lock

Day 5: Reporting
  → Generate board reports
  → Export to Excel/PDF
  → Archive in S3 with Object Lock
```

## Step-by-Step Process

### Step 1: Initiate Monthly Close

**Run the orchestrator:**

```bash
cd /Volumes/AI/Code/FPA
python -m src.orchestrator.monthly_close \
  --period-end "2026-01-31" \
  --period-start "2026-01-01" \
  --presentation-currency USD
```

**What happens:**
- Orchestrator agent coordinates all sub-agents
- Creates close period in database
- Sets status to `in_progress`
- Generates workflow tasks

**Expected output:**
```
✓ Close period created: CLOSE-2026-01
✓ Orchestrator initialized
✓ 7 portfolio companies identified
→ Starting data extraction...
```

### Step 2: Data Extraction

**Automated by:** `data_ingestion` agent
**Duration:** 30-60 minutes
**Manual intervention:** Only if ERP connection fails

The system automatically:

1. **Connects to each ERP system** using stored credentials
2. **Extracts trial balances** for the period
3. **Validates data quality:**
   - Balance sheet balances (Assets = Liabilities + Equity)
   - Debit/credit equality
   - Account code completeness
   - No duplicate transactions
4. **Loads into `raw_data` table** with encryption

**Monitor progress:**

```bash
# Check extraction status
python -m src.cli.status --period "2026-01"

# View extraction logs
tail -f logs/data_ingestion.log
```

**Example output:**
```
Company: Effecti
  Status: ✓ Complete
  Entries: 1,248
  Quality Score: 98.5%

Company: Mercos
  Status: ✓ Complete
  Entries: 1,089
  Quality Score: 99.1%

Company: Datahub
  Status: → In Progress (45%)
  Entries: 543 / ~1200
```

**Troubleshooting:**

If extraction fails for a company:

```bash
# Retry specific company
python -m src.connectors.retry \
  --company effecti \
  --period "2026-01-31"

# Check connector health
python -m src.connectors.health_check \
  --erp totvs_protheus
```

See [ERP Integration Troubleshooting](erp-integration.md#troubleshooting) for common issues.

### Step 3: Data Quality Validation

**Automated by:** `validation` agent
**Duration:** 5-10 minutes

The system automatically validates:

1. **Completeness:** All companies extracted successfully
2. **Accuracy:** Trial balances match ERP source
3. **Consistency:** Account codes align with chart of accounts
4. **Reasonableness:** Balances within expected ranges

**Review validation report:**

```bash
# Generate validation report
python -m src.reporting.validation_report \
  --period "2026-01-31" \
  --output validation_report.html
```

**Example validation results:**

| Company | Entries | Balance Check | Quality Score | Issues |
|---------|---------|---------------|---------------|--------|
| Effecti | 1,248 | ✓ Pass | 98.5% | 2 warnings |
| Mercos | 1,089 | ✓ Pass | 99.1% | 0 |
| Datahub | 1,201 | ✓ Pass | 97.8% | 3 warnings |
| OnClick | 987 | ✓ Pass | 98.9% | 1 warning |
| Ipê Digital | 845 | ✓ Pass | 99.5% | 0 |
| Munddi | 756 | ✓ Pass | 98.2% | 2 warnings |
| Leadlovers | 891 | ✓ Pass | 99.0% | 1 warning |

**Investigate warnings:**

Warnings typically indicate:
- Unusual account balances (e.g., negative cash)
- Missing account descriptions
- Suspicious transactions (duplicate amounts/dates)

These are flagged for human review but don't block consolidation.

### Step 4: Consolidation

**Automated by:** `consolidation` agent
**Duration:** 10-15 minutes

The consolidation process executes:

#### 4.1 FX Conversion

All BRL balances are converted to USD using:
- **Balance sheet items:** Closing rate (Jan 31, 2026)
- **P&L items:** Average rate (Jan 1-31, 2026)
- **Equity items:** Historical rate (acquisition date)

**FX rates used:**
```
BRL/USD Closing: 0.1895 (BCB PTAX 31-Jan-2026)
BRL/USD Average: 0.1872 (Jan 2026 average)
```

**Cumulative Translation Adjustment (CTA)** is calculated for balance sheet translation differences.

#### 4.2 Intercompany Elimination

The system identifies and eliminates intercompany transactions:

**Elimination categories:**
1. **Receivables/Payables:** Invoice matching with 1% FX tolerance
2. **Revenue/Expense:** Entity relationship-based matching
3. **Dividends:** Intra-group dividend elimination
4. **Equity Investments:** Parent-subsidiary investment elimination

**Example elimination entry:**

```
Transaction: Effecti → Mercos software license
Reference: INV-2026-0045
Amount: BRL 50,000 (USD 9,475)

Elimination Journal Entry:
  DR: IC Revenue (Effecti)      USD 9,475
  CR: IC Expense (Mercos)        USD 9,475
  Memo: Eliminate intercompany software license
```

**Monitor eliminations:**

```bash
# View elimination summary
python -m src.cli.eliminations --period "2026-01-31"
```

#### 4.3 PPA Amortization

For acquired companies, Purchase Price Allocation (PPA) amortization is recorded:

**Example: Leadlovers (acquired Aug 2023)**

```
Goodwill: USD 500,000
Intangible Assets:
  - Customer Relationships: USD 4,000,000 (8 years)
  - Technology Platform: USD 2,000,000 (5 years)
  - Brand: USD 500,000 (10 years)

Monthly Amortization (Jan 2026):
  - Customer Relationships: USD 41,667
  - Technology Platform: USD 33,333
  - Brand: USD 4,167
  Total: USD 79,167
```

**Amortization schedule:**

```bash
# View PPA amortization schedule
python -m src.ppa.schedule --entity leadlovers
```

#### 4.4 Consolidated Output

The consolidation produces:

1. **Consolidated Trial Balance** - All entities combined in USD
2. **Elimination Entries** - Detailed IC elimination journal
3. **PPA Adjustments** - Monthly amortization entries
4. **Audit Trail** - Complete consolidation log

**View consolidated financials:**

```bash
# Generate consolidated trial balance
python -m src.reporting.consolidated_tb \
  --period "2026-01-31" \
  --output consolidated_tb.xlsx
```

### Step 5: Human Review Workflow

**Reviewers:** FP&A team, Manager, CFO
**Duration:** 1-2 days

The system automatically identifies transactions requiring human review based on **confidence scoring**.

#### 5.1 Review Dashboard

Access the review dashboard:

```bash
# Start review dashboard
python -m src.dashboard.review_app \
  --period "2026-01-31" \
  --port 8080

# Open in browser
open http://localhost:8080
```

Dashboard shows:

| Risk Level | Count | Requires Review |
|------------|-------|-----------------|
| 🟢 Green (≥80%) | 8,456 | 5% sampling (423) |
| 🟡 Yellow (50-79%) | 342 | 100% review (342) |
| 🔴 Red (<50%) | 18 | 100% + escalation (18) |

#### 5.2 Review Process

**For Yellow Risk Items:**

1. Click on transaction to view details
2. Review supporting documentation
3. Verify amounts and classifications
4. Choose action:
   - **Approve** - Accept AI recommendation
   - **Modify** - Edit entry and approve
   - **Reject** - Create manual adjustment

**For Red Risk Items:**

Requires **four-eyes principle** (minimum 2 reviewers):

1. First reviewer (FP&A Analyst) reviews and approves/rejects
2. Second reviewer (FP&A Manager or CFO) independently reviews
3. Both must approve before entry is accepted
4. If rejected, escalate to CFO for decision

**Example red risk transaction:**

```
Transaction ID: TX-2026-01-0234
Company: Effecti
Account: Intercompany Revenue
Amount: USD 1,500,000
Risk Factors:
  - Amount > materiality threshold (USD 500k)
  - First-time intercompany transaction type
  - Manual adjustment flag

Confidence Score: 42%
Recommended Action: Escalate to CFO
```

#### 5.3 Approval Actions

**In the dashboard:**

```python
# Approve transaction
review_manager.submit_review(
    review_id="REV-2026-01-0234",
    reviewer_id="analyst_001",
    decision="approved",
    comments="Verified with supporting invoice, amounts reconcile"
)

# Request changes
review_manager.submit_review(
    review_id="REV-2026-01-0235",
    reviewer_id="analyst_001",
    decision="changes_requested",
    comments="Account code should be 4110 (recurring revenue) not 4120"
)
```

See [Human Review Guide](human-review.md) for detailed workflow.

### Step 6: Variance Analysis

**Automated by:** `analysis` agent
**Duration:** 15-20 minutes

The system automatically generates variance analysis:

1. **Month-over-Month (MoM)** - Jan 2026 vs. Dec 2025
2. **Year-over-Year (YoY)** - Jan 2026 vs. Jan 2025
3. **Budget vs. Actual** - Jan 2026 vs. Budget

**View variance report:**

```bash
# Generate variance analysis
python -m src.reporting.variance_analysis \
  --period "2026-01-31" \
  --comparison month_over_month \
  --output variance_report.xlsx
```

**Example variance highlights:**

```
Revenue
  Actual: USD 3,625,000
  Prior Month: USD 3,450,000
  Variance: +USD 175,000 (+5.1%)
  Flag: 🟢 Positive, within expectations

Operating Expenses
  Actual: USD 2,810,000
  Prior Month: USD 2,650,000
  Variance: +USD 160,000 (+6.0%)
  Flag: 🟡 Above trend, investigate

Intercompany Revenue
  Actual: USD 485,000
  Prior Month: USD 520,000
  Variance: -USD 35,000 (-6.7%)
  Flag: 🟢 Normal fluctuation
```

**Investigate material variances:**

Any variance >15% or >USD 250,000 requires explanation:

```bash
# Drill down into specific account
python -m src.analysis.variance_detail \
  --account "5100" \
  --period "2026-01-31"
```

### Step 7: Adjusting Entries (if needed)

If review identifies errors or adjustments needed:

**Create manual journal entry:**

```bash
# Create adjustment
python -m src.journal.create_entry \
  --period "2026-01-31" \
  --type adjustment \
  --memo "Reclassify consulting expense to capitalized development"
```

**Example adjustment entry:**

```
Journal Entry: JE-2026-01-ADJ-001
Date: 2026-01-31
Type: Adjustment
Memo: Reclassify R&D costs per IFRS capitalization policy

DR: Intangible Assets (Development)    USD 125,000
CR: Operating Expenses (R&D)            USD 125,000

Approval: Requires CFO sign-off
Confidence: Manual entry (requires review)
```

**All adjustments:**
- Require detailed memo
- Require supporting documentation
- Require approver sign-off
- Are logged in audit trail

### Step 8: Final Approval & Period Close

**Approver:** CFO or FP&A Manager
**Duration:** 30 minutes

Once all reviews and adjustments are complete:

#### 8.1 Final Review Checklist

- [ ] All yellow/red risk items reviewed and approved
- [ ] Material variances explained
- [ ] Adjustment entries approved
- [ ] Balance sheet balances (Assets = Liabilities + Equity)
- [ ] Intercompany eliminations complete
- [ ] PPA amortization recorded correctly

#### 8.2 Approve Period Close

```bash
# Approve and close period
python -m src.orchestrator.close_period \
  --period "2026-01-31" \
  --approver "cfo_pierre" \
  --action approve
```

**This action:**
- Locks the period (no further changes)
- Marks all entries as `final`
- Triggers report generation
- Archives data to S3 with Object Lock
- Sends notifications to stakeholders

**Confirmation message:**
```
✓ Period CLOSE-2026-01 approved
✓ Status: Closed
✓ Approver: Pierre Schurmann (CFO)
✓ Approved at: 2026-02-05 14:32:18 UTC
✓ Archived to: s3://fpa-backups-prod/closes/2026-01/
✓ Notifications sent to: Board, Investors, FP&A Team
```

### Step 9: Report Generation

**Automated after period close:**

The system automatically generates:

1. **Consolidated Financial Statements** (IFRS & US GAAP)
2. **Board Report Package** (PDF)
3. **Investor Update** (Excel)
4. **Variance Analysis** (Excel)
5. **KPI Dashboard** (HTML)

**Download reports:**

```bash
# List available reports
python -m src.cli.reports --period "2026-01-31"

# Download specific report
python -m src.cli.reports \
  --period "2026-01-31" \
  --type board_package \
  --output board_report_jan2026.pdf
```

See [Reports Guide](reports.md) for report details.

### Step 10: Archive & Backup

**Automated after period close:**

1. **S3 Upload:** All data archived to S3
2. **Encryption:** AES-256-GCM + KMS encryption
3. **Object Lock:** 7-year retention with governance lock
4. **Versioning:** All changes tracked

**Verify backup:**

```bash
# Check S3 backup status
aws s3 ls s3://fpa-backups-prod/closes/2026-01/

# Verify encryption
aws s3api head-object \
  --bucket fpa-backups-prod \
  --key closes/2026-01/consolidated.json
```

## Common Scenarios

### Scenario 1: ERP Connection Failure

**Problem:** TOTVS connector times out during extraction

**Solution:**

1. Check ERP API status (may be down for maintenance)
2. Retry with increased timeout:
   ```bash
   python -m src.connectors.retry \
     --company effecti \
     --timeout 300
   ```
3. If still failing, extract manually and upload via CLI:
   ```bash
   python -m src.cli.import_trial_balance \
     --company effecti \
     --file effecti_tb_jan2026.csv
   ```

### Scenario 2: Material Variance Detected

**Problem:** Revenue variance >15% from prior month

**Solution:**

1. Run detailed variance drill-down
2. Compare to budget and forecast
3. Review supporting transactions
4. Document explanation in variance comments
5. Notify CFO for awareness

### Scenario 3: Intercompany Mismatch

**Problem:** Effecti shows USD 100k IC receivable, but Mercos shows USD 98k IC payable

**Solution:**

1. Check if timing difference (accrual in one entity, cash in other)
2. Check FX rate differences (different booking dates)
3. If true error, create adjustment entry to reconcile
4. Document root cause for process improvement

## Monthly Close Metrics

Track these KPIs for each close:

| Metric | Target | Jan 2026 Actual |
|--------|--------|-----------------|
| Close Duration | ≤5 days | 4 days |
| Automation Rate | ≥85% | 88% |
| Data Quality Score | ≥98% | 98.7% |
| Review Time | ≤16 hours | 14 hours |
| Adjustments | ≤5 entries | 3 entries |
| Accuracy | ≥99.9% | 99.92% |

## Best Practices

1. **Start Early:** Begin extraction on Day 1 after month-end
2. **Monitor Daily:** Check orchestrator status daily during close
3. **Review Proactively:** Don't wait for dashboard, review as items come in
4. **Document Decisions:** All review decisions should have clear comments
5. **Investigate Trends:** Look for patterns in variances month-over-month
6. **Continuous Improvement:** Update process docs based on lessons learned

## Next Steps

- [ERP Integration Guide](erp-integration.md) - Configure ERP connectors
- [Consolidation Workflow](consolidation.md) - Deep dive into consolidation
- [Human Review Guide](human-review.md) - Review workflow details
- [Reports Guide](reports.md) - Report generation and customization

---

**Need Help?**
Contact FP&A Team: [pschumacher@nuvini.ai](mailto:pschumacher@nuvini.ai)
