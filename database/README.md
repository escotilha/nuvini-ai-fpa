# AI FP&A Monthly Close Automation - Database Documentation

**Version:** 1.0.0
**Created:** 2026-02-07
**Database:** PostgreSQL 15+

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Schema Design](#schema-design)
4. [Installation](#installation)
5. [Multi-Tenant Security](#multi-tenant-security)
6. [Performance Optimization](#performance-optimization)
7. [Partitioning Strategy](#partitioning-strategy)
8. [Data Model](#data-model)
9. [Usage Examples](#usage-examples)
10. [Maintenance](#maintenance)
11. [Scaling to 66+ Companies](#scaling-to-66-companies)

---

## Overview

This database schema supports multi-tenant IFRS/US GAAP compliant financial consolidation for AI-powered monthly close automation. The design supports:

- **7 initial portfolio companies** (Effecti, Mercos, Datahub, OnClick, Ipê Digital, Munddi, Leadlovers)
- **Scalable to 66+ entities** with optimal performance
- **7-year audit trail retention** with partitioning
- **Row-Level Security (RLS)** for multi-tenant data isolation
- **IFRS 16 and ASC 842** lease accounting
- **Multi-currency** support with automated FX translation
- **AI-generated journal entries** with confidence scoring

---

## Architecture

### Technology Stack

- **Database:** PostgreSQL 15+
- **Extensions:**
  - `uuid-ossp` - UUID generation
  - `btree_gist` - Advanced indexing
  - `pg_trgm` - Fuzzy text search
- **Partitioning:** Range partitioning by year (trial balances, audit logs)
- **Security:** Row-Level Security (RLS) policies
- **Performance:** 80+ optimized indexes, covering indexes for index-only scans

### Design Principles

1. **Multi-tenant isolation** - RLS ensures users only access authorized entities
2. **Audit trail completeness** - All changes tracked with 7-year retention
3. **Performance at scale** - Partitioned tables, optimized indexes for 66+ entities
4. **Data integrity** - Constraints, triggers, and validation functions
5. **IFRS/GAAP compliance** - Standard chart of accounts with taxonomy mappings
6. **AI-ready** - Confidence scores, AI action logs, automated journal entries

---

## Schema Design

### Core Tables

| Table | Purpose | Partitioned | RLS Enabled |
|-------|---------|-------------|-------------|
| `portfolio_entities` | Portfolio companies and consolidation hierarchy | No | Yes |
| `users` | User accounts and authentication | No | No |
| `user_entity_access` | Multi-tenant access control | No | No |
| `standard_chart_of_accounts` | Master COA template (IFRS/GAAP) | No | No |
| `entity_chart_of_accounts` | Entity-specific COA mapping | No | Yes |
| `trial_balances` | Monthly trial balances by entity | Yes (by year) | Yes |
| `subledger_entries` | Detail transactions requiring drill-down | No | Yes |
| `fx_rates` | Daily FX rates | No | No |
| `fx_rates_monthly` | Monthly average FX rates | No | No |
| `journal_entries` | Manual adjustments, AI-generated entries | No | Yes |
| `journal_entry_lines` | Journal entry line items | No | Yes |
| `consolidated_balances` | Final consolidated output | No | Yes |
| `intercompany_balances` | IC reconciliation tracking | No | Yes |
| `etl_batches` | ETL job tracking | No | Yes |
| `validation_results` | Data quality validation results | No | Yes |
| `agent_actions` | AI agent audit log | Yes (by year) | No |
| `credential_access_log` | Security audit log | No | No |
| `period_locks` | Period locking for closed months | No | No |

### Entity Relationship Summary

```
portfolio_entities (1) ──< (N) entity_chart_of_accounts
                   ↓
                   ├── (N) trial_balances
                   ├── (N) journal_entries
                   ├── (N) consolidated_balances
                   └── (N) intercompany_balances

standard_chart_of_accounts (1) ──< (N) entity_chart_of_accounts
                            ↓
                            ├── (N) journal_entry_lines
                            └── (N) consolidated_balances

users (1) ──< (N) user_entity_access >── (N) portfolio_entities
```

---

## Installation

### Prerequisites

- PostgreSQL 15 or higher
- Superuser access (for extension creation)
- Minimum 8GB RAM (16GB recommended for 66+ entities)
- SSD storage (minimum 100GB)

### Step 1: Create Database

```bash
createdb ai_fpna_db
```

### Step 2: Run Migrations

```bash
psql -d ai_fpna_db -f migrations/001_initial_schema.sql
psql -d ai_fpna_db -f migrations/002_rls_policies.sql
psql -d ai_fpna_db -f migrations/003_indexes.sql
```

### Step 3: Seed Data

```bash
psql -d ai_fpna_db -f seeds/001_portfolio_entities.sql
psql -d ai_fpna_db -f seeds/002_standard_coa.sql
```

### Step 4: Configure PostgreSQL

Add to `postgresql.conf`:

```ini
# Performance tuning for 66+ entities
shared_buffers = 8GB
effective_cache_size = 24GB
work_mem = 256MB
maintenance_work_mem = 2GB
max_worker_processes = 8
max_parallel_workers_per_gather = 4
max_parallel_workers = 8

# Enable query optimization
random_page_cost = 1.1  # For SSD
effective_io_concurrency = 200

# Partitioning
enable_partition_pruning = on
constraint_exclusion = partition

# Statistics
default_statistics_target = 100
```

### Step 5: Create Application User

```sql
-- Create application role
CREATE ROLE fpna_app WITH LOGIN PASSWORD 'secure_password_here';

-- Grant permissions
GRANT CONNECT ON DATABASE ai_fpna_db TO fpna_app;
GRANT USAGE ON SCHEMA public TO fpna_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO fpna_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO fpna_app;

-- Grant RLS bypass for ETL service account
GRANT rls_bypass TO fpna_app;  -- Only if this is the ETL service account
```

---

## Multi-Tenant Security

### Row-Level Security (RLS)

All sensitive tables use RLS policies to enforce data isolation:

```sql
-- Example: Set current user context
SELECT set_current_user('user-uuid-here');

-- User will only see entities they have access to
SELECT * FROM trial_balances;  -- Automatically filtered by RLS
```

### Access Control Matrix

| Role | Read All Entities | Write | Approve Journals | Lock Periods |
|------|-------------------|-------|------------------|--------------|
| `admin` | ✓ | ✓ | ✓ | ✓ |
| `finance_manager` | ✓ | ✓ | ✓ | ✓ |
| `controller` | ✓ | ✓ | ✓ | ✗ |
| `analyst` | Assigned only | Assigned only | ✗ | ✗ |
| `auditor` | ✓ (read-only) | ✗ | ✗ | ✗ |
| `read_only` | Assigned only | ✗ | ✗ | ✗ |

### Granting Entity Access

```sql
-- Grant read/write access to an entity
INSERT INTO user_entity_access (user_id, entity_id, can_read, can_write, can_approve)
VALUES (
    'user-uuid',
    (SELECT entity_id FROM portfolio_entities WHERE entity_code = 'EFFECTI'),
    true,  -- can_read
    true,  -- can_write
    false  -- can_approve
);
```

### RLS Helper Functions

```sql
-- Check current user's access
SELECT * FROM current_rls_context();

-- Returns:
-- current_user_id | is_admin | accessible_entities
-- uuid            | false    | {entity1-uuid, entity2-uuid, ...}
```

---

## Performance Optimization

### Indexing Strategy

The schema includes **80+ indexes** optimized for common query patterns:

#### Trial Balance Queries

```sql
-- Entity + period + account lookups
idx_trial_balances_entity_period_account
idx_trial_balances_period_account
idx_trial_balances_nonzero  -- Partial index for non-zero balances only
```

#### Consolidation Queries

```sql
idx_consolidated_period_account
idx_consolidated_entity_period
idx_ic_balances_entities_period
```

#### Journal Entry Queries

```sql
idx_journal_entries_pending_approval
idx_journal_entries_ai_generated
idx_journal_lines_account_period
```

### Covering Indexes

Covering indexes enable index-only scans (no table access):

```sql
-- Trial balance summary (index-only scan)
CREATE INDEX idx_trial_balances_summary
    ON trial_balances(entity_id, period_year, period_month)
    INCLUDE (entity_account_id, ending_balance, currency);
```

### Query Performance Benchmarks

Expected query times with 66 entities, 7 years of data:

| Query Type | Expected Time | Data Volume |
|------------|---------------|-------------|
| Single entity trial balance | < 10ms | ~200 rows |
| All entities current period | < 100ms | ~13,200 rows |
| Consolidated balances (month) | < 50ms | ~100-150 rows |
| Intercompany reconciliation | < 200ms | ~500 pairs |
| Pending journal approvals | < 20ms | ~50 journals |
| Account hierarchy traversal | < 15ms | ~100 accounts |

**Assumptions:**
- PostgreSQL 15+ with 8GB shared_buffers, 256MB work_mem
- SSD storage (< 1ms random read latency)
- Proper vacuum and analyze maintenance

---

## Partitioning Strategy

### Trial Balances (Range Partitioning by Year)

Partitioning reduces query time by pruning irrelevant partitions:

```sql
-- Partitions created for 2020-2026
trial_balances_2020  -- 2020-01-01 to 2020-12-31
trial_balances_2021  -- 2021-01-01 to 2021-12-31
...
trial_balances_2026  -- 2026-01-01 to 2026-12-31
```

**Query with partition pruning:**

```sql
-- Automatically uses only trial_balances_2024 partition
SELECT * FROM trial_balances
WHERE period_year = 2024 AND period_month = 12;
```

### Agent Actions (Audit Log Partitioning)

7-year retention with automatic partition pruning:

```sql
agent_actions_2020  -- 2020-01-01 to 2020-12-31
agent_actions_2021  -- 2021-01-01 to 2021-12-31
...
agent_actions_2026  -- 2026-01-01 to 2026-12-31
```

### Adding New Partitions

```sql
-- Add partition for 2027 (run at year-end)
CREATE TABLE trial_balances_2027 PARTITION OF trial_balances
    FOR VALUES FROM (2027) TO (2028);

CREATE TABLE agent_actions_2027 PARTITION OF agent_actions
    FOR VALUES FROM ('2027-01-01') TO ('2028-01-01');
```

### Partition Maintenance

```sql
-- Drop old partitions (after 7-year retention)
DROP TABLE trial_balances_2020;
DROP TABLE agent_actions_2020;
```

---

## Data Model

### Chart of Accounts Mapping

```
Standard COA (Master)
    ↓ mapping
Entity COA (Local)
    ↓ used in
Trial Balances → Consolidation → Consolidated Balances
```

**Example:**

```sql
-- Standard account
account_code: '1210'
account_name: 'Accounts Receivable - Trade'

-- Entity mapping (Effecti)
local_account_code: '1.01.01.001'
local_account_name: 'Contas a Receber - Clientes'
mapping_confidence: 0.95

-- Trial balance uses entity account
entity_account_id: effecti-ar-uuid
ending_balance: 1,250,000.00 BRL

-- Consolidation uses standard account
standard_account_id: ar-trade-uuid
ending_balance: 234,567.89 USD (after FX translation)
```

### Journal Entry Workflow

```
Draft → Pending Review → Approved → Posted
  ↓          ↓              ↓         ↓
Edit     Review/Edit    Lock      Immutable
```

**Status transitions:**

- `draft` - User can edit/delete
- `pending_review` - User can edit, approver can reject
- `approved` - Locked for editing, ready to post
- `posted` - Immutable, affects balances
- `reversed` - Posted with offsetting reversal entry

### Consolidation Flow

```
1. Load Trial Balances (BRL, entity COA)
2. Map to Standard COA
3. Translate to USD (FX rates)
4. Eliminate Intercompany Balances
5. Apply Consolidation Journals
6. Calculate Consolidated Balances (USD, standard COA)
```

---

## Usage Examples

### 1. Query Entity Trial Balance

```sql
SELECT
    e.entity_code,
    sca.account_code,
    sca.account_name,
    tb.ending_balance,
    tb.currency,
    tb.period_year,
    tb.period_month
FROM trial_balances tb
JOIN entity_chart_of_accounts eca ON tb.entity_account_id = eca.entity_account_id
JOIN standard_chart_of_accounts sca ON eca.standard_account_id = sca.account_id
JOIN portfolio_entities e ON tb.entity_id = e.entity_id
WHERE e.entity_code = 'EFFECTI'
  AND tb.period_year = 2024
  AND tb.period_month = 12
ORDER BY sca.account_code;
```

### 2. Check Intercompany Reconciliation

```sql
SELECT
    ic.period_year,
    ic.period_month,
    ef.entity_code AS from_entity,
    et.entity_code AS to_entity,
    sca.account_code,
    sca.account_name,
    ic.amount_entity_from,
    ic.amount_entity_to,
    ic.variance,
    CASE
        WHEN ABS(ic.variance) <= 0.01 THEN 'Matched'
        WHEN ABS(ic.variance) <= 100 THEN 'Minor Variance'
        ELSE 'Significant Variance'
    END AS status
FROM intercompany_balances ic
JOIN portfolio_entities ef ON ic.entity_from_id = ef.entity_id
JOIN portfolio_entities et ON ic.entity_to_id = et.entity_id
JOIN standard_chart_of_accounts sca ON ic.standard_account_id = sca.account_id
WHERE ic.period_year = 2024
  AND ic.period_month = 12
  AND ABS(ic.variance) > 0.01
ORDER BY ABS(ic.variance) DESC;
```

### 3. Create AI-Generated Journal Entry

```sql
-- Insert journal entry header
INSERT INTO journal_entries (
    entry_number,
    entity_id,
    period_year,
    period_month,
    entry_date,
    entry_source,
    status,
    description,
    ai_confidence,
    ai_explanation
) VALUES (
    'JE-2024-12-AI-001',
    (SELECT entity_id FROM portfolio_entities WHERE entity_code = 'EFFECTI'),
    2024,
    12,
    '2024-12-31',
    'ai_generated',
    'pending_review',
    'Accrued hosting expense based on usage pattern analysis',
    0.87,
    'AI detected 15% increase in cloud usage vs. prior month. Accrual calculated based on usage meters and historical pricing.'
) RETURNING entry_id;

-- Insert debit line (expense)
INSERT INTO journal_entry_lines (
    entry_id,
    line_number,
    standard_account_id,
    debit_amount,
    credit_amount,
    currency,
    description
) VALUES (
    'entry-id-from-above',
    1,
    (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '5100'),
    12500.00,
    0,
    'BRL',
    'Accrued hosting expense - December 2024'
);

-- Insert credit line (accrued liability)
INSERT INTO journal_entry_lines (
    entry_id,
    line_number,
    standard_account_id,
    debit_amount,
    credit_amount,
    currency,
    description
) VALUES (
    'entry-id-from-above',
    2,
    (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2120'),
    0,
    12500.00,
    'BRL',
    'Accrued hosting liability'
);
```

### 4. Lock Period

```sql
-- Soft lock (allow approvers to make changes)
INSERT INTO period_locks (entity_id, period_year, period_month, lock_status, locked_by)
VALUES (
    (SELECT entity_id FROM portfolio_entities WHERE entity_code = 'EFFECTI'),
    2024,
    12,
    'soft_locked',
    current_user_id()
);

-- Hard lock (immutable, only admin can unlock)
UPDATE period_locks
SET lock_status = 'hard_locked'
WHERE entity_id = (SELECT entity_id FROM portfolio_entities WHERE entity_code = 'EFFECTI')
  AND period_year = 2024
  AND period_month = 12;
```

### 5. Query Consolidated Balance Sheet

```sql
SELECT
    sca.account_code,
    sca.account_name,
    sca.account_type,
    SUM(cb.ending_balance) AS consolidated_balance,
    cb.currency
FROM consolidated_balances cb
JOIN standard_chart_of_accounts sca ON cb.standard_account_id = sca.account_id
WHERE cb.period_year = 2024
  AND cb.period_month = 12
  AND cb.entity_id IS NULL  -- Group-level consolidation
  AND sca.account_type IN ('asset', 'liability', 'equity')
GROUP BY sca.account_code, sca.account_name, sca.account_type, cb.currency, sca.level
ORDER BY sca.account_code;
```

---

## Maintenance

### Daily Tasks

```sql
-- Update statistics on critical tables
ANALYZE trial_balances;
ANALYZE journal_entries;
ANALYZE consolidated_balances;
```

### Weekly Tasks

```sql
-- Vacuum to reclaim space
VACUUM ANALYZE trial_balances;
VACUUM ANALYZE journal_entries;

-- Check for bloated indexes
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 20;
```

### Monthly Tasks

```sql
-- Reindex partitioned tables (during maintenance window)
REINDEX TABLE CONCURRENTLY trial_balances;
REINDEX TABLE CONCURRENTLY agent_actions;

-- Check for unused indexes
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Annual Tasks

```sql
-- Add new partition for upcoming year
CREATE TABLE trial_balances_2027 PARTITION OF trial_balances
    FOR VALUES FROM (2027) TO (2028);

CREATE TABLE agent_actions_2027 PARTITION OF agent_actions
    FOR VALUES FROM ('2027-01-01') TO ('2028-01-01');

-- Archive and drop partitions older than 7 years
-- (First backup to cold storage)
pg_dump -t trial_balances_2020 ai_fpna_db > trial_balances_2020_archive.sql
DROP TABLE trial_balances_2020;
```

---

## Scaling to 66+ Companies

### Capacity Planning

**Current Configuration (7 entities):**

- Trial balances: ~10,000 rows/year
- Consolidated balances: ~1,500 rows/year
- Journal entries: ~500 entries/year
- Total database size: ~2GB

**Projected at 66 entities (10x scale):**

- Trial balances: ~100,000 rows/year
- Consolidated balances: ~15,000 rows/year
- Journal entries: ~5,000 entries/year
- Total database size: ~20GB (7 years)

### Performance at Scale

Query performance remains optimal due to:

1. **Partitioning** - Reduces scan size by 7x (only current year)
2. **Covering indexes** - Enable index-only scans
3. **Partial indexes** - Index only active/relevant data
4. **Parallel query execution** - Configured for 4 workers per query

**Example: Query 66 entities at once**

```sql
-- Aggregates 66 entities in < 100ms
SELECT
    period_year,
    period_month,
    SUM(ending_balance) AS total_consolidated
FROM trial_balances
WHERE period_year = 2024
  AND period_month = 12
GROUP BY period_year, period_month;
```

### Horizontal Scaling Options

For > 100 entities, consider:

1. **Citus (PostgreSQL extension)** - Distributed PostgreSQL
2. **Read replicas** - Offload reporting queries
3. **Partitioning by entity** - Further reduce query scope
4. **Materialized views** - Pre-aggregate consolidation results

---

## Schema Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-07 | Initial schema with 7 entities |

---

## Support and Contact

For questions or issues:

- **Database Schema Issues:** Review migration files in `/database/migrations/`
- **Performance Tuning:** Check `/database/migrations/003_indexes.sql`
- **Security Configuration:** Review `/database/migrations/002_rls_policies.sql`

---

## License

Proprietary - AI FP&A Holdings Ltd.
