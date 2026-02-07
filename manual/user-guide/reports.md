# Reports Guide

## Overview

The AI FP&A system generates comprehensive financial reports for various stakeholders including the board, investors, management, and auditors. All reports are automatically generated after period close and available in multiple formats.

**Report Categories:**
1. Financial Statements (IFRS & US GAAP)
2. Board Reports
3. Management Reports
4. Variance Analysis
5. KPI Dashboards
6. Audit Reports

## Available Reports

### Financial Statements

#### 1. Consolidated Balance Sheet

**Audience:** Board, Investors, Auditors
**Frequency:** Monthly
**Formats:** Excel, PDF
**Standards:** IFRS & US GAAP

**Contents:**
- Assets (Current & Non-Current)
- Liabilities (Current & Non-Current)
- Equity (including CTA)
- Comparative periods (current vs. prior month/year)

**Generate:**

```bash
python -m src.reporting.balance_sheet \
  --period "2026-01-31" \
  --comparison month_over_month \
  --format excel \
  --output balance_sheet_jan2026.xlsx
```

**Example output:**

```
NUVINI GROUP LIMITED
Consolidated Balance Sheet
As of January 31, 2026
(Amounts in USD thousands)

                                Jan 2026    Dec 2025    Change    Change%
ASSETS
Current Assets
  Cash and Cash Equivalents      2,450       2,320        130      5.6%
  Accounts Receivable            4,850       4,620        230      5.0%
  Prepaid Expenses                 320         310         10      3.2%
  Other Current Assets             180         165         15      9.1%
  ────────────────────────────────────────────────────────────────────
  Total Current Assets           7,800       7,415        385      5.2%

Non-Current Assets
  Property, Plant & Equipment    1,250       1,280        (30)    (2.3%)
  Intangible Assets              8,950       9,030        (80)    (0.9%)
  Goodwill                         500         500          -       0.0%
  Deferred Tax Assets              450         425         25      5.9%
  Other Non-Current Assets       9,500       9,320        180      1.9%
  ────────────────────────────────────────────────────────────────────
  Total Non-Current Assets      20,650      20,555         95      0.5%

TOTAL ASSETS                    28,450      27,970        480      1.7%
════════════════════════════════════════════════════════════════════

LIABILITIES & EQUITY
Current Liabilities
  Accounts Payable               3,120       2,980        140      4.7%
  Accrued Expenses               1,850       1,790         60      3.4%
  Deferred Revenue               2,450       2,320        130      5.6%
  Short-term Debt                1,200       1,200          -      0.0%
  Other Current Liabilities        680         640         40      6.3%
  ────────────────────────────────────────────────────────────────────
  Total Current Liabilities      9,300       8,930        370      4.1%

Non-Current Liabilities
  Long-term Debt                 4,500       4,500          -      0.0%
  Deferred Tax Liabilities         930         910         20      2.2%
  Other Non-Current Liabilities    500         490         10      2.0%
  ────────────────────────────────────────────────────────────────────
  Total Non-Current Liabilities  5,930       5,900         30      0.5%

TOTAL LIABILITIES               15,230      14,830        400      2.7%

Equity
  Share Capital                  8,500       8,500          -      0.0%
  Retained Earnings              4,580       4,500         80      1.8%
  Cumulative Translation Adj.      140         140          -      0.0%
  ────────────────────────────────────────────────────────────────────
  Total Equity                  13,220      13,140         80      0.6%

TOTAL LIABILITIES & EQUITY      28,450      27,970        480      1.7%
════════════════════════════════════════════════════════════════════
```

#### 2. Consolidated Income Statement

**Audience:** Board, Investors, Management
**Frequency:** Monthly
**Formats:** Excel, PDF

**Contents:**
- Revenue (by segment/company)
- Operating Expenses (by category)
- EBITDA, EBIT, Net Income
- Comparative periods
- Variance analysis

**Generate:**

```bash
python -m src.reporting.income_statement \
  --period "2026-01-31" \
  --comparison month_over_month \
  --format excel \
  --output income_statement_jan2026.xlsx
```

**Example output:**

```
NUVINI GROUP LIMITED
Consolidated Income Statement
For the Month Ended January 31, 2026
(Amounts in USD thousands)

                                Jan 2026    Dec 2025    Change    Change%
REVENUE
  SaaS Subscription Revenue      2,850       2,720        130      4.8%
  Professional Services            520         490         30      6.1%
  Other Revenue                    255         240         15      6.3%
  ────────────────────────────────────────────────────────────────────
  Total Revenue                  3,625       3,450        175      5.1%

COST OF REVENUE
  Direct Labor                     680         650         30      4.6%
  Infrastructure Costs             420         395         25      6.3%
  Other CoR                        145         135         10      7.4%
  ────────────────────────────────────────────────────────────────────
  Total Cost of Revenue          1,245       1,180         65      5.5%

GROSS PROFIT                     2,380       2,270        110      4.8%
Gross Margin %                   65.7%       65.8%      (0.1%)

OPERATING EXPENSES
  Sales & Marketing                850         810         40      4.9%
  Research & Development           520         485         35      7.2%
  General & Administrative         385         360         25      6.9%
  PPA Amortization                  80          80          -      0.0%
  ────────────────────────────────────────────────────────────────────
  Total Operating Expenses       1,835       1,735        100      5.8%

EBITDA                             625         615         10      1.6%
EBITDA Margin %                  17.2%       17.8%      (0.6%)

Depreciation & Amortization       160         160          -      0.0%

EBIT                               465         455         10      2.2%
EBIT Margin %                    12.8%       13.2%      (0.4%)

OTHER INCOME/(EXPENSE)
  Interest Income                   15          12          3     25.0%
  Interest Expense                 (45)        (45)         -      0.0%
  FX Gain/(Loss)                    25          18          7     38.9%
  Other, net                        (5)         (3)        (2)    66.7%
  ────────────────────────────────────────────────────────────────────
  Total Other Income/(Expense)     (10)        (18)         8    (44.4%)

INCOME BEFORE TAX                 455         437         18      4.1%

Income Tax Expense               (137)       (131)        (6)     4.6%
Effective Tax Rate %             30.1%       30.0%       0.1%

NET INCOME                         318         306         12      3.9%
Net Margin %                      8.8%        8.9%      (0.1%)
════════════════════════════════════════════════════════════════════
```

#### 3. Consolidated Cash Flow Statement

**Audience:** Board, CFO, Investors
**Frequency:** Monthly
**Formats:** Excel, PDF

**Contents:**
- Operating Cash Flow
- Investing Cash Flow
- Financing Cash Flow
- Free Cash Flow calculation

**Generate:**

```bash
python -m src.reporting.cash_flow \
  --period "2026-01-31" \
  --method indirect \
  --format excel \
  --output cash_flow_jan2026.xlsx
```

#### 4. Statement of Changes in Equity

**Audience:** Auditors, Board
**Frequency:** Quarterly, Annual
**Formats:** Excel, PDF

**Contents:**
- Share capital movements
- Retained earnings roll-forward
- CTA movements
- Comprehensive income

### Board Reports

#### 5. Board Package

**Audience:** Board of Directors
**Frequency:** Monthly
**Format:** PDF (print-ready)

**Contents:**
- Executive summary (1-page)
- Consolidated financial statements
- KPI dashboard
- Variance analysis
- Company-by-company highlights
- Key risks and opportunities

**Generate:**

```bash
python -m src.reporting.board_package \
  --period "2026-01-31" \
  --output board_package_jan2026.pdf
```

**Example structure:**

```
NUVINI GROUP LIMITED - Board Package
January 2026

────────────────────────────────────────
EXECUTIVE SUMMARY

Key Metrics:
• Total ARR: $43.6M (+5.1% MoM)
• MRR: $3.63M (+4.8% MoM)
• Net Income: $318K (8.8% margin)
• Cash: $2.45M (+5.6% MoM)
• Customer Count: 2,847 (+3.2% MoM)

Highlights:
✓ Strong revenue growth across all segments
✓ Gross margin stable at 65.7%
✓ Operating expenses well-controlled
✓ Cash generation positive

Risks:
⚠ Customer churn increased to 2.8% (target: 2.5%)
⚠ Sales cycle extended to 45 days (target: 35)

────────────────────────────────────────
[Detailed financial statements follow]
[KPI dashboard]
[Variance analysis]
[Company highlights]
────────────────────────────────────────
```

#### 6. Investor Update

**Audience:** Investors, Limited Partners
**Frequency:** Monthly, Quarterly
**Formats:** Excel, PDF

**Contents:**
- Portfolio performance summary
- ARR and MRR trends
- Unit economics (CAC, LTV, Payback)
- Company-level metrics
- Investment highlights

**Generate:**

```bash
python -m src.reporting.investor_update \
  --period "2026-01-31" \
  --format excel \
  --output investor_update_jan2026.xlsx
```

### Management Reports

#### 7. Variance Analysis Report

**Audience:** Management, FP&A Team
**Frequency:** Monthly
**Formats:** Excel, HTML

**Contents:**
- Actual vs. Budget variance
- Month-over-Month variance
- Year-over-Year variance
- Variance explanations (for >15% variances)

**Generate:**

```bash
python -m src.reporting.variance_analysis \
  --period "2026-01-31" \
  --comparison budget \
  --threshold 0.15 \
  --output variance_jan2026.xlsx
```

**Example output:**

```
Variance Analysis - January 2026
Actual vs. Budget

Account                  Actual    Budget    Variance   Var%    Status
──────────────────────────────────────────────────────────────────────
REVENUE
  SaaS Subscription     2,850,000  2,700,000  150,000   5.6%    🟢 Fav
  Professional Services   520,000    550,000  (30,000)  (5.5%)  🟢 Ok
  ────────────────────────────────────────────────────────────────────
  Total Revenue         3,370,000  3,250,000  120,000   3.7%    🟢 Fav

OPERATING EXPENSES
  Sales & Marketing       850,000    800,000   50,000   6.3%    🟡 Unfav
  R&D                     520,000    500,000   20,000   4.0%    🟢 Ok
  G&A                     385,000    375,000   10,000   2.7%    🟢 Ok
  ────────────────────────────────────────────────────────────────────
  Total OpEx            1,755,000  1,675,000   80,000   4.8%    🟡 Unfav

NET INCOME               318,000    320,000   (2,000)  (0.6%)  🟢 Ok

Material Variances (>15%):
None this period.
```

#### 8. Company Performance Report

**Audience:** Management, Company CEOs
**Frequency:** Monthly
**Formats:** Excel, PDF

**Contents:**
- Individual company P&L
- Company-level KPIs
- Trends and benchmarks
- Action items

**Generate:**

```bash
# All companies
python -m src.reporting.company_performance \
  --period "2026-01-31" \
  --output company_performance_jan2026.xlsx

# Single company
python -m src.reporting.company_performance \
  --period "2026-01-31" \
  --company effecti \
  --output effecti_performance_jan2026.pdf
```

### KPI Dashboards

#### 9. Executive KPI Dashboard

**Audience:** CEO, CFO, Management
**Frequency:** Real-time (web-based)
**Format:** Interactive HTML

**Contents:**
- Revenue metrics (ARR, MRR, Growth)
- Profitability metrics (EBITDA, Net Income, Margins)
- Cash metrics (Cash balance, Burn rate, Runway)
- Customer metrics (Count, Churn, NPS)
- Employee metrics (Headcount, Productivity)

**Access:**

```bash
# Start dashboard server
python -m src.dashboard.kpi_dashboard \
  --port 8080 \
  --period "2026-01-31"

# Open in browser
open http://localhost:8080
```

**Dashboard sections:**

1. **Revenue Overview**
   - ARR trend (12 months)
   - MRR waterfall chart
   - Revenue by segment
   - Revenue by company

2. **Profitability**
   - Gross margin trend
   - EBITDA margin trend
   - Net income trend
   - Operating leverage chart

3. **Cash & Runway**
   - Cash balance
   - Monthly burn rate
   - Runway months
   - Cash conversion cycle

4. **Unit Economics**
   - CAC (Customer Acquisition Cost)
   - LTV (Lifetime Value)
   - LTV:CAC ratio
   - Payback period

5. **Operational Metrics**
   - Customer count
   - Churn rate
   - Net Revenue Retention
   - ARPU (Average Revenue Per User)

#### 10. SaaS Metrics Dashboard

**Audience:** Management, Investors
**Frequency:** Monthly
**Format:** Excel, Interactive HTML

**Contents:**
- MRR movements (New, Expansion, Contraction, Churn)
- ARR by cohort
- Rule of 40 (Growth% + Margin%)
- Quick Ratio (Growth / Churn)
- Magic Number (ARR Growth / S&M Spend)

**Generate:**

```bash
python -m src.reporting.saas_metrics \
  --period "2026-01-31" \
  --format excel \
  --output saas_metrics_jan2026.xlsx
```

### Audit Reports

#### 11. Trial Balance Report

**Audience:** Auditors, Controllers
**Frequency:** Monthly
**Formats:** Excel, CSV

**Contents:**
- Complete chart of accounts
- Opening balance, debits, credits, closing balance
- Consolidated and entity-level views

**Generate:**

```bash
# Consolidated trial balance
python -m src.reporting.trial_balance \
  --period "2026-01-31" \
  --level consolidated \
  --output consolidated_tb_jan2026.xlsx

# Entity-level trial balances
python -m src.reporting.trial_balance \
  --period "2026-01-31" \
  --level entity \
  --company effecti \
  --output effecti_tb_jan2026.xlsx
```

#### 12. General Ledger Report

**Audience:** Auditors, Controllers
**Frequency:** As needed
**Formats:** Excel, CSV

**Contents:**
- All journal entries for period
- Entry details (date, account, amount, memo, source)
- Subledger details

**Generate:**

```bash
# All journal entries
python -m src.reporting.general_ledger \
  --period "2026-01-31" \
  --output gl_jan2026.xlsx

# Specific account
python -m src.reporting.general_ledger \
  --period "2026-01-31" \
  --account "4.01.001" \
  --output gl_revenue_jan2026.xlsx
```

#### 13. Audit Trail Report

**Audience:** Auditors, Compliance
**Frequency:** As needed
**Formats:** Excel, CSV

**Contents:**
- All system actions (who, what, when)
- Data changes (before/after)
- Access logs
- Review decisions

**Generate:**

```bash
# Full audit trail
python -m src.reporting.audit_trail \
  --period "2026-01-31" \
  --output audit_trail_jan2026.xlsx

# Filter by event type
python -m src.reporting.audit_trail \
  --period "2026-01-31" \
  --event-type human_review \
  --output review_audit_jan2026.xlsx
```

#### 14. Intercompany Elimination Report

**Audience:** Auditors, Controllers
**Frequency:** Monthly
**Formats:** Excel

**Contents:**
- All IC transactions identified
- Matched vs. unmatched IC items
- Elimination journal entries
- FX gain/loss on IC balances

**Generate:**

```bash
python -m src.reporting.ic_eliminations \
  --period "2026-01-31" \
  --output ic_eliminations_jan2026.xlsx
```

#### 15. PPA Amortization Report

**Audience:** Auditors, Tax
**Frequency:** Monthly
**Formats:** Excel

**Contents:**
- PPA schedule by acquisition
- Monthly amortization by asset type
- Cumulative amortization
- Remaining intangible asset balances
- Goodwill tracking

**Generate:**

```bash
# All PPAs
python -m src.reporting.ppa_schedule \
  --period "2026-01-31" \
  --output ppa_schedule_jan2026.xlsx

# Single acquisition
python -m src.reporting.ppa_schedule \
  --period "2026-01-31" \
  --entity leadlovers \
  --output leadlovers_ppa_jan2026.xlsx
```

## Report Customization

### Custom Report Templates

Create custom Excel templates:

```python
from src.reporting import ReportBuilder

# Define custom template
builder = ReportBuilder()
builder.load_template("templates/custom_board_report.xlsx")

# Add data sections
builder.add_section("financial_statements", period="2026-01-31")
builder.add_section("kpi_dashboard", period="2026-01-31")
builder.add_section("variance_analysis", comparison="budget")

# Generate report
builder.generate("custom_board_report_jan2026.xlsx")
```

### Custom KPI Definitions

Define custom KPIs:

```python
from src.metrics import KPIDefinition

# Define custom KPI
custom_kpi = KPIDefinition(
    name="Net Revenue Retention",
    formula="(Beginning MRR + Expansion - Contraction - Churn) / Beginning MRR",
    category="SaaS Metrics",
    target=110.0,  # Target: 110%
    format="percentage"
)

# Calculate KPI
nrr = custom_kpi.calculate(period="2026-01-31")
print(f"NRR: {nrr:.1f}%")
```

### Scheduled Reports

Schedule automatic report generation:

```bash
# Schedule board package (1st of each month)
python -m src.reporting.schedule \
  --report board_package \
  --frequency monthly \
  --day 1 \
  --time "09:00" \
  --email "board@nuvini.ai" \
  --format pdf

# Schedule investor update (quarterly)
python -m src.reporting.schedule \
  --report investor_update \
  --frequency quarterly \
  --email "investors@nuvini.ai" \
  --format excel
```

## Report Distribution

### Email Reports

Email reports to stakeholders:

```bash
python -m src.reporting.email \
  --report board_package_jan2026.pdf \
  --to "board@nuvini.ai" \
  --subject "Board Package - January 2026" \
  --body "Please find attached the Board Package for January 2026."
```

### S3 Upload

Upload reports to S3:

```bash
python -m src.reporting.upload \
  --file board_package_jan2026.pdf \
  --bucket fpa-reports \
  --prefix "board/2026/01/" \
  --acl private
```

### Web Portal

Access reports via web portal:

```bash
# Start report portal
python -m src.dashboard.report_portal \
  --port 8080

# Open in browser
open http://localhost:8080/reports
```

Portal features:
- Browse all reports by period
- Search and filter reports
- Download in multiple formats
- Share reports with stakeholders
- View report generation history

## Report Best Practices

1. **Generate Immediately After Close:** Run reports as soon as period close is approved
2. **Review Before Distribution:** Always review key reports before sending to stakeholders
3. **Use Standard Templates:** Maintain consistent formatting across periods
4. **Archive Reports:** Keep copies of all reports for 7 years (compliance)
5. **Control Access:** Use role-based access for sensitive reports
6. **Automate Distribution:** Schedule recurring reports to reduce manual work
7. **Track Versions:** Version all report templates and log changes

## Troubleshooting

### Issue: Report Generation Fails

**Symptom:** Report command returns error

**Solutions:**

1. **Check if period is closed:**
   ```bash
   python -m src.cli.status --period "2026-01-31"
   ```

2. **Verify data completeness:**
   ```bash
   python -m src.reporting.validation_report \
     --period "2026-01-31"
   ```

3. **Check logs:**
   ```bash
   tail -f logs/reporting.log
   ```

### Issue: Missing Data in Report

**Symptom:** Report generated but data is missing or zero

**Solutions:**

1. **Verify consolidation completed:**
   ```bash
   python -m src.cli.consolidation_status \
     --period "2026-01-31"
   ```

2. **Check data filters:**
   - Ensure correct period specified
   - Verify company filter (if used)
   - Check account code filters

3. **Regenerate report:**
   ```bash
   # Force regeneration
   python -m src.reporting.board_package \
     --period "2026-01-31" \
     --force \
     --output board_package_jan2026.pdf
   ```

### Issue: Report Format Issues

**Symptom:** Excel formulas broken, PDF layout incorrect

**Solutions:**

1. **Update report templates:**
   ```bash
   python -m src.reporting.update_templates
   ```

2. **Use alternative format:**
   ```bash
   # Try CSV instead of Excel
   python -m src.reporting.trial_balance \
     --period "2026-01-31" \
     --format csv
   ```

## Next Steps

- [Monthly Close Process](monthly-close.md) - When reports are generated
- [Human Review Guide](human-review.md) - Review before distribution
- [Troubleshooting Guide](troubleshooting.md) - Detailed troubleshooting

---

**Last Updated:** February 7, 2026
**Version:** 1.0.0
