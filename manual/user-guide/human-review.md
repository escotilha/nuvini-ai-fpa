# Human Review & Oversight Guide

## Overview

The AI FP&A system uses a **risk-based human oversight framework** to ensure accuracy and compliance while maximizing automation efficiency. Not all transactions require human review—only those identified as medium or high risk through confidence scoring.

**Review Philosophy:**
- 🟢 **Green (High Confidence ≥80%):** Auto-approved with 5% sampling
- 🟡 **Yellow (Medium Confidence 50-79%):** Mandatory pre-review
- 🔴 **Red (Low Confidence <50%):** Escalated multi-person review

**Target:** Review only 10-15% of transactions while maintaining 99.9% accuracy

## Confidence Scoring System

### How Confidence Scores Work

Every AI-generated transaction receives a **confidence score (0-100%)** based on weighted risk factors:

| Risk Factor | Weight | Description |
|-------------|--------|-------------|
| **Materiality** | 30% | Transaction amount vs. threshold |
| **Pattern Deviation** | 25% | Deviation from historical patterns |
| **Data Quality** | 20% | Completeness and accuracy of source data |
| **Complexity** | 15% | Transaction type complexity |
| **Variance** | 10% | Budget/forecast variance |

### Risk Level Determination

```python
# Confidence score calculation
raw_score = 1.0 - (weighted_sum_of_risks)

if raw_score >= 0.80:
    risk_level = GREEN    # High confidence - auto-approve
elif raw_score >= 0.50:
    risk_level = YELLOW   # Medium confidence - review required
else:
    risk_level = RED      # Low confidence - escalate
```

### Example Confidence Calculation

**Transaction:** Intercompany revenue elimination

```python
Risk Factors:
  Materiality:       USD 1,500,000 (above USD 500k threshold)
                     Risk Score: 0.8 (high)
                     Weighted: 0.8 × 30% = 0.24

  Pattern Deviation: 12% deviation from historical average
                     Risk Score: 0.3 (low)
                     Weighted: 0.3 × 25% = 0.075

  Data Quality:      98.5% quality score
                     Risk Score: 0.015 (very low)
                     Weighted: 0.015 × 20% = 0.003

  Complexity:        First-time intercompany transaction
                     Risk Score: 0.7 (high)
                     Weighted: 0.7 × 15% = 0.105

  Variance:          5% variance from budget
                     Risk Score: 0.2 (low)
                     Weighted: 0.2 × 10% = 0.02

Total Weighted Risk: 0.24 + 0.075 + 0.003 + 0.105 + 0.02 = 0.443
Confidence Score:    1.0 - 0.443 = 0.557 = 55.7%

Risk Level: 🟡 YELLOW (requires review)
```

## Review Workflow

### Review Dashboard Access

Access the review dashboard:

```bash
# Start review dashboard
python -m src.dashboard.review_app \
  --period "2026-01-31" \
  --port 8080

# Open in browser
open http://localhost:8080/review
```

### Dashboard Overview

The dashboard displays:

1. **Summary Statistics**
   - Total transactions
   - Pending reviews by risk level
   - Average confidence score
   - Review completion percentage

2. **Review Queue**
   - List of transactions requiring review
   - Priority sorted (red → yellow → green sampling)
   - Filter by risk level, category, amount

3. **Transaction Details**
   - Full transaction information
   - Confidence score breakdown
   - Supporting documentation
   - Historical context

### Review Process

#### Step 1: Review Assignment

Reviews are automatically assigned based on escalation level:

| Escalation Level | Role | SLA | Typical Cases |
|------------------|------|-----|---------------|
| **Level 0** | None (auto-approved) | - | Green risk items |
| **Level 1** | FP&A Analyst | 24 hours | Yellow risk, routine |
| **Level 2** | FP&A Manager | 12 hours | Red risk, period close |
| **Level 3** | CFO | 6 hours | Regulatory, material |
| **Level 4** | Audit Committee | 48 hours | Critical issues |

#### Step 2: Review Transaction

**In the dashboard:**

1. **Click on transaction** to view details
2. **Review information:**
   - Transaction type and amount
   - Source system and entity
   - Confidence score breakdown
   - Supporting documentation
   - Similar historical transactions
3. **Assess accuracy:**
   - Verify amounts
   - Check account codes
   - Validate business logic
   - Review supporting documents

**Example transaction detail view:**

```
Transaction ID: TX-2026-01-0234
Status: Pending Review
Confidence: 55.7% (🟡 Yellow)

Details:
  Type: Intercompany Elimination
  Date: 2026-01-31
  Amount: USD 1,500,000
  From Entity: Effecti
  To Entity: Mercos
  Account: 4.02.001 - IC Revenue

Journal Entry:
  DR: IC Revenue (Effecti)      USD 1,500,000
  CR: IC Expense (Mercos)        USD 1,500,000
  Memo: Eliminate intercompany software license

Confidence Breakdown:
  Materiality (30%):       HIGH  - Amount exceeds threshold
  Pattern Deviation (25%): LOW   - 12% deviation is normal
  Data Quality (20%):      LOW   - 98.5% quality score
  Complexity (15%):        HIGH  - First-time transaction type
  Variance (10%):          LOW   - 5% budget variance

Risk Factors:
  ⚠ Amount exceeds materiality threshold (USD 500k)
  ⚠ First-time intercompany transaction type
  ✓ Data quality is high
  ✓ Pattern deviation is normal

Supporting Documents:
  📄 Invoice INV-2026-0045.pdf
  📄 Contract effecti_mercos_license.pdf
  📄 Email approval from CFO

Historical Context:
  Similar transactions: 0 (first-time)
  Average IC revenue: USD 125,000/month
  This transaction: 12x average (unusually large)

Reviewer Notes:
  - Verify with Effecti and Mercos finance teams
  - Confirm new licensing agreement is legitimate
  - Check if this should be capitalized instead of expensed
```

#### Step 3: Make Decision

**Available actions:**

1. **Approve**
   - Accept AI recommendation as-is
   - Transaction proceeds to consolidation
   - Review logged in audit trail

2. **Approve with Modifications**
   - Adjust amounts, account codes, or classifications
   - Provide explanation for changes
   - Modified entry proceeds to consolidation

3. **Reject**
   - Reject AI recommendation entirely
   - Provide detailed reason
   - Create manual adjustment entry

4. **Request More Information**
   - Flag for additional review
   - Request supporting documentation
   - Escalate to higher authority

**Example approval:**

```python
# In the dashboard, click "Approve" button and add comment

Comment: "Verified new licensing agreement effective Jan 1, 2026.
Invoice INV-2026-0045 confirms USD 1.5M annual license fee.
Contract reviewed by Legal. Approve as-is."

Reviewer: john_analyst (FP&A Analyst)
Decision: Approved
Timestamp: 2026-02-03 14:23:15 UTC
```

**Example rejection:**

```python
# Click "Reject" and provide reason

Reason: "This should be capitalized as an intangible asset, not
expensed immediately. The licensing agreement grants Mercos 5-year
right to use Effecti's platform. Per IFRS 38, this meets the
definition of an intangible asset.

Recommended entry:
  DR: Intangible Asset - Software License  USD 1,500,000
  CR: IC Payable                           USD 1,500,000

Escalating to CFO for approval."

Reviewer: sarah_manager (FP&A Manager)
Decision: Rejected
Escalation: Level 3 (CFO)
Timestamp: 2026-02-03 15:45:22 UTC
```

#### Step 4: Four-Eyes Principle (Red Risk Only)

For **red risk transactions**, a second reviewer must independently review:

**First Reviewer (FP&A Analyst):**

```python
Review 1:
  Reviewer: john_analyst
  Decision: Approved
  Comment: "Amounts verified, supporting docs attached. Approve."
  Timestamp: 2026-02-03 14:30:00 UTC

Status: Pending Second Review
Required: 1 additional reviewer
```

**Second Reviewer (FP&A Manager or CFO):**

```python
Review 2:
  Reviewer: sarah_manager
  Decision: Approved
  Comment: "Second review complete. Concur with first reviewer.
            Amounts reconcile, documentation adequate. Final approval."
  Timestamp: 2026-02-03 16:15:00 UTC

Status: ✓ Approved (Four-Eyes Complete)
Transaction proceeds to consolidation.
```

**Important:** Both reviewers must **independently** review—no discussion beforehand.

## Mandatory Review Categories

Certain transaction types **always require human review** regardless of confidence score:

| Category | Reason | Escalation Level |
|----------|--------|------------------|
| **Period Close** | Critical control point | Level 2 (Manager) |
| **Intercompany Eliminations** | Complex, material | Level 1 (Analyst) |
| **Regulatory Reports** | External compliance | Level 3 (CFO) |
| **External Communications** | Reputational risk | Level 3 (CFO) |
| **Manual Adjustments** | Override of automated entries | Level 2 (Manager) |
| **Variances >15%** | Unusual deviation | Level 1 (Analyst) |
| **First-Time Transactions** | No historical precedent | Level 2 (Manager) |
| **Amount > Materiality** | Financial statement impact | Level 2 (Manager) |

**Example: Period close always requires review**

```python
Transaction: Period Close - January 2026
Type: Period Close
Confidence: 92% (🟢 Green)

Despite green risk level, this transaction requires mandatory review:
  Category: Period Close
  Escalation: Level 2 (FP&A Manager)
  Required Reviewers: 1
  SLA: 12 hours

Reason: Period close is a critical control point ensuring all entries
are finalized before financial statements are issued.
```

## Review Commands (CLI)

### Get Pending Reviews

```bash
# All pending reviews
python -m src.cli.pending_reviews \
  --period "2026-01-31"

# Filter by risk level
python -m src.cli.pending_reviews \
  --period "2026-01-31" \
  --risk-level red

# Filter by escalation level
python -m src.cli.pending_reviews \
  --period "2026-01-31" \
  --escalation-level 2
```

### Submit Review

```bash
# Approve transaction
python -m src.cli.submit_review \
  --request-id "REV-2026-01-0234" \
  --reviewer "john_analyst" \
  --decision approved \
  --comment "Verified and approved"

# Approve with modifications
python -m src.cli.submit_review \
  --request-id "REV-2026-01-0235" \
  --reviewer "john_analyst" \
  --decision approved \
  --modifications "amount:1450000,account:4.01.001" \
  --comment "Adjusted amount and account code"

# Reject transaction
python -m src.cli.submit_review \
  --request-id "REV-2026-01-0236" \
  --reviewer "sarah_manager" \
  --decision rejected \
  --comment "Should be capitalized, not expensed. Escalating to CFO."
```

### Review Statistics

```bash
# Get review statistics for period
python -m src.cli.review_stats \
  --period "2026-01-31"
```

**Example output:**

```
Review Statistics - January 2026

Total Transactions:        7,017
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Green (≥80%):             6,342 (90.4%)
  Auto-approved:          6,025 (95% skip review)
  Sampled for review:       317 (5% sampling)

Yellow (50-79%):            657 (9.4%)
  Requires review:          657 (100%)

Red (<50%):                  18 (0.3%)
  Requires review:           18 (100%)
  Four-eyes required:        18 (100%)

Review Workload:
  Total requiring review:   992 (14.1%)
  Completed:               950 (95.8%)
  Pending:                  42 (4.2%)
  Overdue (past SLA):        3 (0.3%)

Approval Rate:
  Approved as-is:          875 (92.1%)
  Approved with mods:       58 (6.1%)
  Rejected:                 17 (1.8%)

Average Review Time:
  Green sampling:         2.3 minutes
  Yellow reviews:         8.5 minutes
  Red reviews:           18.7 minutes

Reviewers:
  john_analyst:           342 reviews (36.0%)
  sarah_manager:          285 reviews (30.0%)
  pierre_cfo:              48 reviews (5.1%)
  [Others]:               275 reviews (28.9%)
```

## Review Best Practices

### 1. Prioritize by Risk Level

Always review in this order:

1. **Red risk** (highest priority)
2. **Yellow risk**
3. **Green sampling** (lowest priority)

### 2. Meet SLA Targets

Respect the SLA for each escalation level:

- **Level 1 (Analyst):** 24 hours
- **Level 2 (Manager):** 12 hours
- **Level 3 (CFO):** 6 hours

**Set up SLA alerts:**

```bash
# Get overdue reviews
python -m src.cli.overdue_reviews \
  --period "2026-01-31"

# Email alert
python -m src.cli.email_overdue_alert \
  --to "fpa-team@nuvini.ai"
```

### 3. Document Decisions

Always provide clear comments explaining your decision:

**Good comments:**
- "Verified invoice INV-2026-0045. Amounts reconcile. Approved."
- "Account code should be 5.01.002 (Salaries) not 5.01.001 (Consulting). Modified."
- "Transaction duplicates prior entry JE-2026-01-0123. Rejected to avoid double-counting."

**Poor comments:**
- "OK"
- "Approved"
- "Looks good"

### 4. Use Supporting Documentation

Always review supporting documents before approving:

- Invoices
- Contracts
- Email approvals
- Bank statements
- Reconciliations

**Attach documents to review:**

```bash
python -m src.cli.attach_document \
  --review-id "REV-2026-01-0234" \
  --file "supporting_docs/invoice_INV-2026-0045.pdf" \
  --description "Supporting invoice for IC transaction"
```

### 5. Escalate When Unsure

If uncertain, escalate to higher authority:

```bash
python -m src.cli.escalate_review \
  --review-id "REV-2026-01-0237" \
  --to-level 3 \
  --reason "Complex revenue recognition issue, need CFO guidance"
```

### 6. Maintain Independence (Four-Eyes)

For four-eyes reviews:

- **Do not discuss** with first reviewer before reviewing
- **Review independently** based on facts
- **Disagree if necessary**—better to debate than rubber-stamp

### 7. Track Review Metrics

Monitor your review performance:

```bash
# Your review statistics
python -m src.cli.reviewer_stats \
  --reviewer "john_analyst" \
  --period "2026-01"
```

**Example output:**

```
Reviewer Performance - john_analyst - January 2026

Reviews Completed:       342
Approval Rate:          94.2%
Rejection Rate:          5.8%
Average Review Time:    7.3 minutes
SLA Compliance:         98.5% (within SLA)
Overdue Reviews:         5 (1.5%)

Decision Breakdown:
  Approved as-is:       322 (94.2%)
  Approved with mods:    15 (4.4%)
  Rejected:              20 (5.8%)
  Escalated:              5 (1.5%)

Quality Score:          96.5/100
  (Based on CFO review of sample)
```

## Troubleshooting

### Issue: Too Many Reviews Pending

**Symptom:** Review queue is overwhelming

**Solutions:**

1. **Adjust confidence thresholds:**
   ```python
   # Increase green threshold (review fewer items)
   oversight_manager.scoring_engine.green_threshold = 0.85  # Was 0.80
   ```

2. **Increase sampling rate:**
   ```python
   # Reduce green sampling from 5% to 2%
   oversight_manager.sampling_config.green_sampling_rate = 0.02
   ```

3. **Delegate reviews:**
   ```bash
   # Reassign reviews to additional reviewers
   python -m src.cli.reassign_reviews \
     --from "john_analyst" \
     --to "mary_analyst" \
     --count 50
   ```

### Issue: High Rejection Rate

**Symptom:** Many transactions rejected during review

**Solutions:**

1. **Investigate root causes:**
   ```bash
   python -m src.reporting.rejection_analysis \
     --period "2026-01-31"
   ```

2. **Improve AI model:**
   - Retrain on rejected transactions
   - Adjust confidence scoring weights
   - Add validation rules

3. **Provide feedback:**
   ```bash
   # Flag transaction for model improvement
   python -m src.cli.flag_for_training \
     --transaction "TX-2026-01-0234" \
     --reason "AI misclassified account type"
   ```

### Issue: Review SLA Breaches

**Symptom:** Reviews not completed within SLA

**Solutions:**

1. **Check reviewer workload:**
   ```bash
   python -m src.cli.workload_balance \
     --period "2026-01-31"
   ```

2. **Adjust escalation levels:**
   - Reduce Level 3 (CFO) reviews
   - Increase Level 1 (Analyst) capacity

3. **Extend SLA (if justified):**
   ```python
   # Increase Level 1 SLA to 36 hours
   escalation_matrix[EscalationLevel.FPA_ANALYST].sla_hours = 36
   ```

## Oversight Reporting

### Monthly Oversight Report

```bash
# Generate oversight report
python -m src.reporting.oversight_report \
  --period "2026-01-31" \
  --output oversight_jan2026.pdf
```

**Report contents:**

```
Human Oversight Report - January 2026

Executive Summary:
  Total Transactions:     7,017
  Reviewed:                992 (14.1%)
  Auto-approved:         6,025 (85.9%)
  Overall Approval Rate:  92.1%
  Average Confidence:     87.3%

Risk Distribution:
  🟢 Green (≥80%):       6,342 (90.4%)
  🟡 Yellow (50-79%):      657 (9.4%)
  🔴 Red (<50%):            18 (0.3%)

Review Outcomes:
  Approved as-is:        875 (88.2%)
  Approved with mods:     58 (5.8%)
  Rejected:               17 (1.7%)
  Escalated:              42 (4.2%)

Four-Eyes Reviews:
  Required:               18
  Completed:              18 (100%)
  Average Time:       18.7 minutes

SLA Performance:
  Level 1 (24h):         98.5% on-time
  Level 2 (12h):         96.8% on-time
  Level 3 (6h):          91.7% on-time

Reviewer Performance:
  john_analyst:       342 reviews, 7.3 min avg
  sarah_manager:      285 reviews, 12.5 min avg
  pierre_cfo:          48 reviews, 22.1 min avg

Confidence Accuracy:
  Green transactions:  99.8% accurate (2 errors in 6,342)
  Yellow transactions: 98.5% accurate (10 errors in 657)
  Red transactions:    94.4% accurate (1 error in 18)

Overall System Accuracy: 99.92%
(Target: 99.9%) ✓ PASS
```

## Next Steps

- [Monthly Close Process](monthly-close.md) - When reviews occur in workflow
- [Consolidation Guide](consolidation.md) - What happens after review approval
- [Reports Guide](reports.md) - Reporting on review activity

---

**Last Updated:** February 7, 2026
**Version:** 1.0.0
