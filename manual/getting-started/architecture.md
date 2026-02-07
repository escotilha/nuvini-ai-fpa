# System Architecture

This document provides a detailed technical overview of the AI FP&A Monthly Close Automation system architecture.

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [Technology Stack](#technology-stack)
5. [Security Architecture](#security-architecture)
6. [Scalability & Performance](#scalability--performance)
7. [Deployment Architecture](#deployment-architecture)

---

## High-Level Architecture

The system follows a layered microservices architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                           │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Excel      │  │  PowerPoint  │  │     PDF      │              │
│  │   Reports    │  │   Reports    │  │   Reports    │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────────────┐
│                         API & ORCHESTRATION LAYER                    │
│                                                                       │
│  ┌──────────────────────────────────────────────────────┐           │
│  │            FastAPI REST API                           │           │
│  │  /health, /consolidate, /reports, /entities, etc.    │           │
│  └──────────────────────────────────────────────────────┘           │
│                              ↓                                        │
│  ┌──────────────────────────────────────────────────────┐           │
│  │         Monthly Close Orchestrator                    │           │
│  │  Workflow: Extract → Consolidate → Validate → Report │           │
│  └──────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         BUSINESS LOGIC LAYER                         │
│                                                                       │
│  ┌───────────────┐  ┌──────────────┐  ┌─────────────┐              │
│  │  Connectors   │  │ Consolidation│  │  Analysis   │              │
│  │               │  │   Engine     │  │   Engine    │              │
│  │  - TOTVS      │  │              │  │             │              │
│  │  - ContaAzul  │  │  - FX Conv.  │  │  - Variance │              │
│  │  - Omie       │  │  - IC Elim.  │  │  - KPIs     │              │
│  │  - Bling      │  │  - PPA       │  │  - AI/Claude│              │
│  └───────────────┘  └──────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                   │
│                                                                       │
│  ┌──────────────────────────────────────────────────────┐           │
│  │           PostgreSQL 15+ Database                     │           │
│  │                                                        │           │
│  │  - Trial Balances (Partitioned by Year)              │           │
│  │  - Consolidated Financials                           │           │
│  │  - Chart of Accounts                                 │           │
│  │  - Audit Trail (7-Year Retention)                    │           │
│  │  - Row-Level Security (Multi-Tenant)                 │           │
│  └──────────────────────────────────────────────────────┘           │
│                                                                       │
│  ┌──────────────────────────────────────────────────────┐           │
│  │           Redis 7+ (Task Queue & Cache)               │           │
│  └──────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL SERVICES                            │
│                                                                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐   │
│  │  ERP APIs  │  │  FX Rates  │  │ Claude AI  │  │    AWS     │   │
│  │  (4 types) │  │  BCB/ECB   │  │ Anthropic  │  │  Services  │   │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Architectural Principles

1. **Separation of Concerns**: Each layer has a single, well-defined responsibility
2. **Loose Coupling**: Components communicate through well-defined interfaces
3. **High Cohesion**: Related functionality grouped together
4. **Scalability**: Horizontal scaling at each layer
5. **Observability**: Comprehensive logging, monitoring, and tracing
6. **Security**: Defense-in-depth with multiple security layers

---

## Component Architecture

### 1. Data Ingestion Layer (Connectors)

```
┌─────────────────────────────────────────────────────────┐
│              ERP Connector Framework                     │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │         ERPConnector (Abstract Base)            │    │
│  │                                                  │    │
│  │  + connect()                                    │    │
│  │  + disconnect()                                 │    │
│  │  + get_trial_balance()                          │    │
│  │  + get_subledger_details()                      │    │
│  │  + get_companies()                              │    │
│  │  + health_check()                               │    │
│  └────────────────────────────────────────────────┘    │
│             ↑          ↑          ↑          ↑           │
│             │          │          │          │           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│
│  │  TOTVS   │  │ContaAzul │  │   Omie   │  │  Bling   ││
│  │Connector │  │Connector │  │Connector │  │Connector ││
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘│
│                                                          │
│  Shared Components:                                     │
│  - AuthHandler (OAuth2, API Key, Bearer Token)         │
│  - RetryManager (Exponential Backoff)                  │
│  - RateLimiter (Token Bucket Algorithm)                │
│  - CircuitBreaker (Prevent Cascading Failures)         │
│  - DataValidator (Schema Validation, Normalization)    │
└─────────────────────────────────────────────────────────┘
```

#### Key Features

- **Authentication**: Multi-protocol support (OAuth 2.0, API Key, Bearer Token)
- **Resilience**: Automatic retry with exponential backoff, circuit breaker
- **Rate Limiting**: Per-provider token bucket rate limiting
- **Validation**: Comprehensive data validation and normalization
- **Observability**: Structured logging, health checks, metrics

#### Data Flow

```
ERP API → HTTP Client → Auth Handler → Rate Limiter →
Circuit Breaker → Response Parser → Data Validator →
Normalized Data → Database
```

### 2. Consolidation Engine

```
┌─────────────────────────────────────────────────────────┐
│              Consolidation Engine                        │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │           ConsolidationEngine                   │    │
│  │                                                  │    │
│  │  + register_entity()                            │    │
│  │  + load_trial_balance()                         │    │
│  │  + consolidate()                                │    │
│  │  + get_audit_trail()                            │    │
│  └────────────────────────────────────────────────┘    │
│             │          │          │          │           │
│             ↓          ↓          ↓          ↓           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│
│  │    FX    │  │   IC     │  │   PPA    │  │   GAAP   ││
│  │Converter │  │Eliminator│  │ Manager  │  │   Recon  ││
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘│
│                                                          │
│  Components:                                            │
│  - FXRateManager: Load and manage FX rates             │
│  - FXConverter: Apply rates to accounts                │
│  - IntercompanyMatcher: Identify IC pairs              │
│  - EliminationGenerator: Create elimination entries    │
│  - PPAScheduler: Track goodwill & amortization         │
│  - GAAPrec: IFRS to US GAAP adjustments                │
└─────────────────────────────────────────────────────────┘
```

#### Consolidation Process

```
Step 1: FX Conversion
  Input:  Trial Balances (BRL)
  Output: Translated Balances (USD)

  Algorithm:
  - Load FX rates (closing, average, historical)
  - Apply closing rate to BS accounts
  - Apply average rate to P&L accounts
  - Calculate Cumulative Translation Adjustment (CTA)

Step 2: Intercompany Elimination
  Input:  Translated Balances (USD)
  Output: Elimination Entries

  Algorithm:
  - Identify IC relationships (entity pairs)
  - Match AR/AP pairs (by reference, amount ±1%)
  - Match Revenue/Expense pairs (by entity relationship)
  - Generate elimination journal entries
  - Calculate FX gains/losses on IC balances

Step 3: PPA Amortization
  Input:  Active PPA Schedules
  Output: Amortization Entries

  Algorithm:
  - Retrieve PPA schedules for all entities
  - Calculate monthly amortization (straight-line)
  - Generate journal entries
  - Update goodwill carrying amount

Step 4: Aggregation
  Input:  Translated Balances, Eliminations, PPA Entries
  Output: Consolidated Balances

  Algorithm:
  - Sum all entries by standard account
  - Apply elimination entries
  - Apply PPA entries
  - Calculate totals by account type

Step 5: Validation
  Input:  Consolidated Balances
  Output: Validation Report, Accuracy Score

  Checks:
  - Balance Sheet Balance (Assets = Liabilities + Equity)
  - Debit/Credit Balance
  - Net Income Reconciliation
  - FX Rate Consistency
  - Reasonableness Checks
```

### 3. Analysis Engine

```
┌─────────────────────────────────────────────────────────┐
│              Analysis Engine                             │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │         VarianceAnalyzer                        │    │
│  │                                                  │    │
│  │  + analyze_budget_vs_actual()                   │    │
│  │  + analyze_month_over_month()                   │    │
│  │  + identify_anomalies()                         │    │
│  │  + generate_commentary()                        │    │
│  └────────────────────────────────────────────────┘    │
│                          │                               │
│                          ↓                               │
│  ┌────────────────────────────────────────────────┐    │
│  │         Claude AI Integration                   │    │
│  │                                                  │    │
│  │  Prompt Engineering:                            │    │
│  │  "Analyze variance in account X:                │    │
│  │   - Current: $Y                                 │    │
│  │   - Budget: $Z                                  │    │
│  │   - Variance: $(Y-Z) / Z% increase             │    │
│  │   - Historical trend: [data]                    │    │
│  │   Explain why this variance occurred."          │    │
│  └────────────────────────────────────────────────┘    │
│                          │                               │
│                          ↓                               │
│  ┌────────────────────────────────────────────────┐    │
│  │         KPI Calculator                          │    │
│  │                                                  │    │
│  │  SaaS Metrics:                                  │    │
│  │  - ARR, MRR, NRR                                │    │
│  │  - Logo Churn, Revenue Churn                    │    │
│  │  - ARPU, LTV/CAC                                │    │
│  │  - Rule of 40                                   │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

#### AI Variance Analysis Flow

```
1. Detect Material Variances
   - Budget vs Actual > $10K or 10%
   - Month-over-Month > $5K or 5%

2. Gather Context
   - Account name and type
   - Current vs prior period/budget
   - Historical trend (12 months)
   - Related accounts (e.g., Revenue + COGS)

3. Generate Prompt for Claude
   Template:
   """
   You are a financial analyst reviewing monthly close results.

   Account: {account_name}
   Current Period: ${current:,.2f}
   Prior Period: ${prior:,.2f}
   Variance: ${variance:,.2f} ({variance_pct}%)
   Trend: {trend_description}

   Explain the variance in 2-3 sentences suitable for
   CFO review. Focus on likely business drivers.
   """

4. Call Claude API
   Model: claude-sonnet-4-5
   Temperature: 0.3 (consistent, factual)
   Max Tokens: 300

5. Format Response
   - Remove markdown
   - Capitalize properly
   - Add to variance analysis report

6. Confidence Scoring
   Factors:
   - Data completeness (100%)
   - Variance explainability (AI confidence)
   - Pattern consistency (historical)

   Score: 0-100%
   - Green (95-100%): Auto-approve
   - Yellow (80-94%): Review recommended
   - Red (<80%): Manual validation required
```

### 4. Reporting Layer

```
┌─────────────────────────────────────────────────────────┐
│              Report Generation                           │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │       ExcelReportGenerator                      │    │
│  │                                                  │    │
│  │  Sheets:                                        │    │
│  │  - Summary (Key metrics, KPIs)                  │    │
│  │  - Balance Sheet (Assets, Liabilities, Equity)  │    │
│  │  - P&L Statement (Revenue, Expenses, Net Inc.)  │    │
│  │  - Trial Balance (Account detail)               │    │
│  │  - FX Rates (Exchange rates used)               │    │
│  │  - Audit Log (Consolidation steps)              │    │
│  │                                                  │    │
│  │  Library: OpenPyXL                              │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │       PowerPointGenerator                       │    │
│  │                                                  │    │
│  │  Slides:                                        │    │
│  │  - Executive Summary (Key highlights)           │    │
│  │  - Financial Performance (Charts)               │    │
│  │  - Variance Analysis (Waterfall charts)         │    │
│  │  - KPI Trends (Time series)                     │    │
│  │  - Per-Company Highlights                       │    │
│  │                                                  │    │
│  │  Library: python-pptx                           │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │       PDFExporter                               │    │
│  │                                                  │    │
│  │  - Board Package (All financials)               │    │
│  │  - Executive Summary (1-pager)                  │    │
│  │  - Audit Trail (Complete log)                   │    │
│  │                                                  │    │
│  │  Library: ReportLab / WeasyPrint                │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### 5. Orchestration Layer

```
┌─────────────────────────────────────────────────────────┐
│           Monthly Close Orchestrator                     │
│                                                          │
│  State Machine:                                         │
│                                                          │
│  ┌──────────┐  Extract   ┌──────────┐  Consolidate     │
│  │  IDLE    │ ────────→  │EXTRACTING│ ────────→        │
│  └──────────┘            └──────────┘                   │
│                                                          │
│  ┌─────────────┐  Validate  ┌──────────┐  Report       │
│  │CONSOLIDATING│ ────────→  │VALIDATING│ ────────→      │
│  └─────────────┘            └──────────┘                │
│                                                          │
│  ┌──────────┐  Distribute  ┌──────────┐                │
│  │REPORTING │ ────────→    │COMPLETED │                │
│  └──────────┘              └──────────┘                │
│                                 │                        │
│                                 │ Error                  │
│                                 ↓                        │
│                            ┌──────────┐                │
│                            │  FAILED  │                │
│                            └──────────┘                │
│                                                          │
│  Celery Tasks:                                          │
│  - extract_trial_balances_task()                        │
│  - consolidate_financials_task()                        │
│  - validate_results_task()                              │
│  - generate_reports_task()                              │
│  - distribute_reports_task()                            │
│                                                          │
│  Error Handling:                                        │
│  - Retry failed tasks (max 3 attempts)                  │
│  - Send alerts to Slack/Email                           │
│  - Log detailed error trace                             │
│  - Allow manual resume from checkpoint                  │
└─────────────────────────────────────────────────────────┘
```

---

## Data Flow

### End-to-End Monthly Close Flow

```
1. TRIGGER (1st of month, 6 AM UTC)
   │
   ├─→ Lambda/EventBridge scheduled event
   │   POST /api/v1/consolidation/run
   │
2. EXTRACT (5-10 minutes)
   │
   ├─→ For each entity (parallel):
   │   │
   │   ├─→ Create ERP connector
   │   ├─→ Authenticate
   │   ├─→ Extract trial balance
   │   ├─→ Validate data
   │   └─→ Store in database
   │
   └─→ Wait for all entities
   │
3. MAP (2-3 minutes)
   │
   ├─→ Load entity Chart of Accounts
   ├─→ Map to Standard CoA
   └─→ Store mappings
   │
4. CONSOLIDATE (3-5 minutes)
   │
   ├─→ Load FX rates (BCB API)
   ├─→ Apply FX conversion
   ├─→ Identify intercompany transactions
   ├─→ Generate elimination entries
   ├─→ Apply PPA amortization
   ├─→ Aggregate to consolidated balances
   └─→ Store consolidated result
   │
5. VALIDATE (1-2 minutes)
   │
   ├─→ Balance sheet balance check
   ├─→ Debit/credit balance check
   ├─→ Net income reconciliation
   ├─→ Reasonableness checks
   ├─→ Calculate accuracy score
   └─→ Store validation report
   │
6. ANALYZE (3-5 minutes)
   │
   ├─→ Calculate budget vs actual variances
   ├─→ Identify material variances
   ├─→ Call Claude API for explanations
   ├─→ Calculate SaaS KPIs
   └─→ Store analysis results
   │
7. REPORT (5-7 minutes)
   │
   ├─→ Generate Excel (consolidated financials)
   ├─→ Generate PowerPoint (executive summary)
   ├─→ Generate PDF (board package)
   ├─→ Upload to S3
   └─→ Store report metadata
   │
8. DISTRIBUTE (2-3 minutes)
   │
   ├─→ Send email notifications
   ├─→ Post to Slack channel
   └─→ Update dashboard
   │
9. COMPLETE
   │
   └─→ Total time: 20-35 minutes (target: <2 hours)
```

### Database Schema Relationships

```
portfolio_entities
  │
  ├─→ entity_chart_of_accounts
  │     │
  │     └─→ standard_chart_of_accounts
  │
  ├─→ trial_balances (partitioned by year)
  │
  ├─→ consolidated_balances
  │
  ├─→ intercompany_balances
  │
  ├─→ journal_entries
  │     │
  │     └─→ journal_entry_lines
  │
  └─→ etl_batches
        │
        └─→ validation_results

users
  │
  └─→ user_entity_access
        │
        └─→ portfolio_entities

fx_rates (daily)
fx_rates_monthly (average)

agent_actions (partitioned by year)
credential_access_log
period_locks
```

---

## Technology Stack

### Backend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Language** | Python | 3.13+ | Core application |
| **Web Framework** | FastAPI | 0.110+ | REST API |
| **ORM** | SQLAlchemy | 2.0+ | Database access |
| **DB Driver** | asyncpg | 0.29+ | Async PostgreSQL |
| **Task Queue** | Celery | 5.3+ | Background tasks |
| **HTTP Client** | httpx | 0.27+ | Async HTTP |
| **Data Validation** | Pydantic | 2.6+ | Schema validation |

### Database & Cache

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Primary DB** | PostgreSQL | 15+ | Transactional data |
| **Cache** | Redis | 7.0+ | Task queue, caching |
| **Extensions** | uuid-ossp, btree_gist, pg_trgm | - | UUID, indexing, search |

### External Services

| Service | Provider | Purpose |
|---------|----------|---------|
| **AI Model** | Claude Sonnet 4.5 / Opus 4.6 | Variance analysis, commentary |
| **ERP APIs** | TOTVS, ContaAzul, Omie, Bling | Trial balance extraction |
| **FX Rates** | BCB (Brazil), ECB (Europe) | Exchange rates |
| **Cloud** | AWS (RDS, ECS, S3, Lambda) | Infrastructure |

### Libraries & Tools

| Library | Purpose |
|---------|---------|
| **openpyxl** | Excel file generation |
| **python-pptx** | PowerPoint generation |
| **reportlab** | PDF generation |
| **pandas** | Data manipulation |
| **pytest** | Testing framework |
| **black** | Code formatting |
| **mypy** | Type checking |

---

## Security Architecture

### Multi-Layer Security

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Network Security                               │
│                                                          │
│ - VPC with private subnets                              │
│ - Security groups (least privilege)                     │
│ - NACLs                                                  │
│ - TLS 1.3 for all connections                           │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 2: Authentication & Authorization                 │
│                                                          │
│ - JWT tokens for API authentication                     │
│ - Row-Level Security in PostgreSQL                      │
│ - RBAC (admin, manager, analyst, read-only)             │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 3: Data Protection                                │
│                                                          │
│ - Encryption at rest (AES-256)                          │
│ - Encryption in transit (TLS 1.3)                       │
│ - AWS Secrets Manager for credentials                   │
│ - No secrets in code or logs                            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 4: Audit & Compliance                             │
│                                                          │
│ - Immutable audit logs (7-year retention)               │
│ - Credential access logging                             │
│ - Agent action tracking                                 │
│ - S3 Object Lock for archival                           │
└─────────────────────────────────────────────────────────┘
```

### Row-Level Security (RLS)

PostgreSQL RLS ensures users only access authorized data:

```sql
-- RLS Policy for trial_balances
CREATE POLICY trial_balances_rls ON trial_balances
USING (
  entity_id IN (
    SELECT entity_id
    FROM user_entity_access
    WHERE user_id = current_user_id()
      AND can_read = true
  )
);

-- Enable RLS
ALTER TABLE trial_balances ENABLE ROW LEVEL SECURITY;
```

Users can only query entities they have explicit access to, enforced at the database level.

---

## Scalability & Performance

### Current Capacity (7 Entities)

| Metric | Value |
|--------|-------|
| **Consolidation Time** | <5 seconds |
| **Database Size** | ~2 GB (current year) |
| **Query Response Time** | <100ms (p95) |
| **API Throughput** | 1000 requests/min |
| **Concurrent Users** | 50 |

### Target Capacity (66 Entities)

| Metric | Value |
|--------|-------|
| **Consolidation Time** | <60 seconds |
| **Database Size** | ~20 GB (7 years) |
| **Query Response Time** | <200ms (p95) |
| **API Throughput** | 5000 requests/min |
| **Concurrent Users** | 200 |

### Scaling Strategies

#### Vertical Scaling (to 66 entities)

- **Database**: db.r6g.2xlarge (8 vCPU, 64 GB RAM)
- **Application**: ECS Fargate (8 vCPU, 16 GB RAM)
- **Redis**: cache.r6g.large (2 vCPU, 13 GB RAM)

#### Horizontal Scaling (beyond 100 entities)

- **Database**: Citus extension (distributed PostgreSQL)
- **Application**: Auto-scaling ECS tasks (2-10 instances)
- **Cache**: Redis cluster mode (3-5 nodes)
- **Task Queue**: Celery workers (5-20 workers)

### Performance Optimizations

1. **Database Partitioning**: Range partitioning by year (trial_balances, agent_actions)
2. **Covering Indexes**: 80+ optimized indexes for common queries
3. **Connection Pooling**: SQLAlchemy pool (10-20 connections)
4. **Query Optimization**: Parallel query execution, index-only scans
5. **Caching**: Redis caching for FX rates, CoA mappings
6. **Async I/O**: httpx for ERP API calls (concurrent extraction)

---

## Deployment Architecture

### AWS Production Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Internet                               │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ↓
            ┌───────────────────────┐
            │   Route 53 (DNS)      │
            └───────────┬───────────┘
                        │
                        ↓
            ┌───────────────────────┐
            │   ALB (Load Balancer) │
            └───────────┬───────────┘
                        │
        ┌───────────────┴───────────────┐
        │                                │
        ↓                                ↓
┌──────────────┐                ┌──────────────┐
│  ECS Task 1  │                │  ECS Task 2  │
│  (FastAPI)   │                │  (FastAPI)   │
└──────┬───────┘                └──────┬───────┘
       │                                │
       └────────────┬───────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
        ↓           ↓           ↓
┌──────────┐  ┌──────────┐  ┌──────────┐
│   RDS    │  │ElastiCache│ │    S3    │
│PostgreSQL│  │  Redis   │  │ Reports  │
└──────────┘  └──────────┘  └──────────┘
        │           │           │
        └───────────┴───────────┘
                    │
        ┌───────────┴───────────┐
        │                        │
        ↓                        ↓
┌──────────────┐        ┌──────────────┐
│  CloudWatch  │        │    Lambda    │
│  Monitoring  │        │   Triggers   │
└──────────────┘        └──────────────┘
```

### Environment Configuration

| Environment | Purpose | Infrastructure |
|-------------|---------|----------------|
| **Development** | Local dev | Docker Compose |
| **Staging** | Pre-prod testing | AWS ECS (1 task) |
| **Production** | Live system | AWS ECS (2+ tasks) |

---

## Summary

The AI FP&A system architecture is designed for:

- ✅ **Scalability**: Handle 7-66+ entities without redesign
- ✅ **Reliability**: 99%+ uptime, automatic retry, circuit breakers
- ✅ **Security**: Multi-layer security, RLS, encryption, audit logs
- ✅ **Performance**: <2 hour monthly close, <100ms query response
- ✅ **Maintainability**: Clear separation of concerns, comprehensive testing
- ✅ **Observability**: Structured logging, monitoring, tracing

**Next Steps**: Review [Quick Start](quick-start.md) to see the architecture in action.
