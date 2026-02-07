# Database Schema Reference

**Version:** 1.0.0
**Database:** PostgreSQL 15+
**Last Updated:** 2026-02-07

## Overview

The AI FP&A system uses a PostgreSQL database designed for multi-tenant IFRS/US GAAP compliant financial consolidation. The schema supports 7+ portfolio companies with scalability to 66+ entities while maintaining optimal performance through partitioning, indexing, and row-level security.

## Technology Stack

### Core Components

- **Database Engine:** PostgreSQL 15 or higher
- **Required Extensions:**
  - `uuid-ossp` - UUID generation for primary keys
  - `btree_gist` - Advanced indexing capabilities
  - `pg_trgm` - Fuzzy text search for account names
- **Partitioning Strategy:** Range partitioning by year
- **Security Model:** Row-Level Security (RLS) policies
- **Performance Optimization:** 80+ specialized indexes

### Design Principles

1. **Multi-Tenant Isolation** - RLS ensures users only access authorized entities
2. **Audit Trail Completeness** - All changes tracked with 7-year retention
3. **Performance at Scale** - Optimized for 66+ entities
4. **Data Integrity** - Comprehensive constraints, triggers, and validation
5. **Compliance** - IFRS/GAAP standard chart of accounts
6. **AI-Ready** - Confidence scores, AI action logs, automated entries

## Schema Architecture

### Core Tables

| Table | Purpose | Rows | Partitioned | RLS |
|-------|---------|------|-------------|-----|
| `portfolio_entities` | Portfolio companies and hierarchy | ~100 | No | Yes |
| `users` | User accounts and authentication | ~50 | No | No |
| `user_entity_access` | Multi-tenant access control | ~500 | No | No |
| `standard_chart_of_accounts` | Master COA (IFRS/GAAP) | ~200 | No | No |
| `entity_chart_of_accounts` | Entity-specific COA mapping | ~1,400 | No | Yes |
| `trial_balances` | Monthly trial balances by entity | ~100K/yr | Yes | Yes |
| `subledger_entries` | Detail transactions | ~1M/yr | No | Yes |
| `fx_rates` | Daily FX rates | ~10K/yr | No | No |
| `fx_rates_monthly` | Monthly average FX rates | ~1K/yr | No | No |
| `journal_entries` | Manual/AI-generated entries | ~5K/yr | No | Yes |
| `journal_entry_lines` | Journal entry line items | ~15K/yr | No | Yes |
| `consolidated_balances` | Final consolidated output | ~15K/yr | No | Yes |
| `intercompany_balances` | IC reconciliation tracking | ~5K/yr | No | Yes |
| `etl_batches` | ETL job tracking | ~500/yr | No | Yes |
| `validation_results` | Data quality validation | ~2K/yr | No | Yes |
| `agent_actions` | AI agent audit log | ~50K/yr | Yes | No |
| `credential_access_log` | Security audit log | ~10K/yr | No | No |
| `period_locks` | Period locking for closed months | ~1K | No | No |

## Table Definitions

### portfolio_entities

Portfolio companies and consolidation hierarchy.

```sql
CREATE TABLE portfolio_entities (
    entity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_code VARCHAR(20) NOT NULL UNIQUE,
    entity_name VARCHAR(200) NOT NULL,
    parent_entity_id UUID REFERENCES portfolio_entities(entity_id),
    functional_currency VARCHAR(3) NOT NULL,
    country_code VARCHAR(2) NOT NULL,
    ownership_percentage DECIMAL(5,2) NOT NULL DEFAULT 100.00,
    acquisition_date DATE,
    entity_type VARCHAR(50) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_portfolio_entities_parent ON portfolio_entities(parent_entity_id);
CREATE INDEX idx_portfolio_entities_active ON portfolio_entities(is_active) WHERE is_active = TRUE;
```

**Key Fields:**
- `entity_code` - Short code (e.g., "EFFECTI", "LEADLOVERS")
- `parent_entity_id` - For consolidation hierarchy
- `functional_currency` - Entity's functional currency (BRL, USD)
- `ownership_percentage` - Ownership stake for consolidation
- `entity_type` - subsidiary, parent, holding_company

### users

User accounts and authentication.

```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200),
    role VARCHAR(50) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = TRUE;
```

**Roles:**
- `admin` - Full system access
- `finance_manager` - Full financial access
- `controller` - Financial operations
- `analyst` - Read/write assigned entities
- `auditor` - Read-only all entities
- `read_only` - Read-only assigned entities

### user_entity_access

Multi-tenant access control mapping.

```sql
CREATE TABLE user_entity_access (
    access_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    entity_id UUID NOT NULL REFERENCES portfolio_entities(entity_id),
    can_read BOOLEAN NOT NULL DEFAULT TRUE,
    can_write BOOLEAN NOT NULL DEFAULT FALSE,
    can_approve BOOLEAN NOT NULL DEFAULT FALSE,
    granted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    granted_by UUID REFERENCES users(user_id),
    UNIQUE(user_id, entity_id)
);

CREATE INDEX idx_user_entity_access_user ON user_entity_access(user_id);
CREATE INDEX idx_user_entity_access_entity ON user_entity_access(entity_id);
```

### standard_chart_of_accounts

Master chart of accounts template (IFRS/US GAAP).

```sql
CREATE TABLE standard_chart_of_accounts (
    account_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_code VARCHAR(20) NOT NULL UNIQUE,
    account_name VARCHAR(200) NOT NULL,
    parent_account_id UUID REFERENCES standard_chart_of_accounts(account_id),
    account_type VARCHAR(20) NOT NULL,
    account_subtype VARCHAR(50),
    level INTEGER NOT NULL,
    is_summary BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    ifrs_taxonomy VARCHAR(100),
    us_gaap_taxonomy VARCHAR(100),
    normal_balance VARCHAR(6) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_account_type CHECK (account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense')),
    CONSTRAINT chk_normal_balance CHECK (normal_balance IN ('debit', 'credit'))
);

CREATE INDEX idx_coa_code ON standard_chart_of_accounts(account_code);
CREATE INDEX idx_coa_parent ON standard_chart_of_accounts(parent_account_id);
CREATE INDEX idx_coa_type ON standard_chart_of_accounts(account_type);
CREATE INDEX idx_coa_active ON standard_chart_of_accounts(is_active) WHERE is_active = TRUE;
```

**Account Types:**
- `asset` - Assets (normal debit balance)
- `liability` - Liabilities (normal credit balance)
- `equity` - Equity (normal credit balance)
- `revenue` - Revenue (normal credit balance)
- `expense` - Expenses (normal debit balance)

### entity_chart_of_accounts

Entity-specific chart of accounts mapping to standard COA.

```sql
CREATE TABLE entity_chart_of_accounts (
    entity_account_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID NOT NULL REFERENCES portfolio_entities(entity_id),
    standard_account_id UUID NOT NULL REFERENCES standard_chart_of_accounts(account_id),
    local_account_code VARCHAR(50) NOT NULL,
    local_account_name VARCHAR(200) NOT NULL,
    mapping_confidence DECIMAL(3,2),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE(entity_id, local_account_code)
);

CREATE INDEX idx_entity_coa_entity ON entity_chart_of_accounts(entity_id);
CREATE INDEX idx_entity_coa_standard ON entity_chart_of_accounts(standard_account_id);
CREATE INDEX idx_entity_coa_local_code ON entity_chart_of_accounts(local_account_code);
```

**Fields:**
- `mapping_confidence` - AI confidence score (0.00-1.00)
- `local_account_code` - Entity's native account code
- `local_account_name` - Entity's native account name

### trial_balances (Partitioned)

Monthly trial balances by entity.

```sql
CREATE TABLE trial_balances (
    balance_id UUID DEFAULT uuid_generate_v4(),
    entity_id UUID NOT NULL REFERENCES portfolio_entities(entity_id),
    entity_account_id UUID NOT NULL REFERENCES entity_chart_of_accounts(entity_account_id),
    period_year INTEGER NOT NULL,
    period_month INTEGER NOT NULL,
    opening_balance DECIMAL(18,2) NOT NULL DEFAULT 0,
    debit_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    credit_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    ending_balance DECIMAL(18,2) NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL,
    source_system VARCHAR(50),
    batch_id UUID REFERENCES etl_batches(batch_id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    PRIMARY KEY (balance_id, period_year),
    CONSTRAINT chk_period_month CHECK (period_month BETWEEN 1 AND 12)
) PARTITION BY RANGE (period_year);

-- Partitions (2020-2026)
CREATE TABLE trial_balances_2020 PARTITION OF trial_balances
    FOR VALUES FROM (2020) TO (2021);
CREATE TABLE trial_balances_2021 PARTITION OF trial_balances
    FOR VALUES FROM (2021) TO (2022);
CREATE TABLE trial_balances_2022 PARTITION OF trial_balances
    FOR VALUES FROM (2022) TO (2023);
CREATE TABLE trial_balances_2023 PARTITION OF trial_balances
    FOR VALUES FROM (2023) TO (2024);
CREATE TABLE trial_balances_2024 PARTITION OF trial_balances
    FOR VALUES FROM (2024) TO (2025);
CREATE TABLE trial_balances_2025 PARTITION OF trial_balances
    FOR VALUES FROM (2025) TO (2026);
CREATE TABLE trial_balances_2026 PARTITION OF trial_balances
    FOR VALUES FROM (2026) TO (2027);

-- Indexes
CREATE INDEX idx_trial_balances_entity_period_account ON trial_balances(entity_id, period_year, period_month, entity_account_id);
CREATE INDEX idx_trial_balances_period_account ON trial_balances(period_year, period_month, entity_account_id);
CREATE INDEX idx_trial_balances_nonzero ON trial_balances(entity_id, period_year, period_month)
    WHERE ending_balance != 0;
```

### journal_entries

Manual adjustments and AI-generated journal entries.

```sql
CREATE TABLE journal_entries (
    entry_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entry_number VARCHAR(50) NOT NULL UNIQUE,
    entity_id UUID NOT NULL REFERENCES portfolio_entities(entity_id),
    period_year INTEGER NOT NULL,
    period_month INTEGER NOT NULL,
    entry_date DATE NOT NULL,
    entry_source VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    description TEXT,
    created_by UUID REFERENCES users(user_id),
    approved_by UUID REFERENCES users(user_id),
    posted_by UUID REFERENCES users(user_id),
    reversed_by UUID REFERENCES users(user_id),
    reversal_entry_id UUID REFERENCES journal_entries(entry_id),
    ai_confidence DECIMAL(3,2),
    ai_explanation TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMP,
    posted_at TIMESTAMP,
    reversed_at TIMESTAMP,

    CONSTRAINT chk_entry_source CHECK (entry_source IN ('manual', 'ai_generated', 'system', 'consolidation')),
    CONSTRAINT chk_status CHECK (status IN ('draft', 'pending_review', 'approved', 'posted', 'reversed'))
);

CREATE INDEX idx_journal_entries_entity_period ON journal_entries(entity_id, period_year, period_month);
CREATE INDEX idx_journal_entries_status ON journal_entries(status);
CREATE INDEX idx_journal_entries_pending_approval ON journal_entries(status)
    WHERE status = 'pending_review';
CREATE INDEX idx_journal_entries_ai_generated ON journal_entries(entry_source, ai_confidence)
    WHERE entry_source = 'ai_generated';
```

**Status Workflow:**
- `draft` → User can edit/delete
- `pending_review` → Awaiting approval
- `approved` → Locked, ready to post
- `posted` → Immutable, affects balances
- `reversed` → Posted with offsetting reversal

### journal_entry_lines

Journal entry line items (debits/credits).

```sql
CREATE TABLE journal_entry_lines (
    line_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entry_id UUID NOT NULL REFERENCES journal_entries(entry_id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    standard_account_id UUID NOT NULL REFERENCES standard_chart_of_accounts(account_id),
    debit_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    credit_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE(entry_id, line_number),
    CONSTRAINT chk_debit_or_credit CHECK (
        (debit_amount > 0 AND credit_amount = 0) OR
        (credit_amount > 0 AND debit_amount = 0)
    )
);

CREATE INDEX idx_journal_lines_entry ON journal_entry_lines(entry_id);
CREATE INDEX idx_journal_lines_account_period ON journal_entry_lines(standard_account_id);
```

### fx_rates

Daily foreign exchange rates.

```sql
CREATE TABLE fx_rates (
    rate_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_currency VARCHAR(3) NOT NULL,
    to_currency VARCHAR(3) NOT NULL,
    rate_date DATE NOT NULL,
    rate DECIMAL(12,6) NOT NULL,
    rate_source VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE(from_currency, to_currency, rate_date),
    CONSTRAINT chk_rate_positive CHECK (rate > 0),
    CONSTRAINT chk_rate_source CHECK (rate_source IN ('bcb', 'ecb', 'manual', 'system'))
);

CREATE INDEX idx_fx_rates_currencies_date ON fx_rates(from_currency, to_currency, rate_date DESC);
```

**Rate Sources:**
- `bcb` - Brazilian Central Bank (Banco Central do Brasil)
- `ecb` - European Central Bank
- `manual` - Manual entry
- `system` - System calculated

### fx_rates_monthly

Monthly average exchange rates.

```sql
CREATE TABLE fx_rates_monthly (
    rate_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_currency VARCHAR(3) NOT NULL,
    to_currency VARCHAR(3) NOT NULL,
    period_year INTEGER NOT NULL,
    period_month INTEGER NOT NULL,
    average_rate DECIMAL(12,6) NOT NULL,
    rate_source VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE(from_currency, to_currency, period_year, period_month),
    CONSTRAINT chk_period_month CHECK (period_month BETWEEN 1 AND 12)
);

CREATE INDEX idx_fx_rates_monthly_currencies_period ON fx_rates_monthly(from_currency, to_currency, period_year, period_month);
```

### consolidated_balances

Final consolidated financial statement balances.

```sql
CREATE TABLE consolidated_balances (
    balance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID REFERENCES portfolio_entities(entity_id),
    standard_account_id UUID NOT NULL REFERENCES standard_chart_of_accounts(account_id),
    period_year INTEGER NOT NULL,
    period_month INTEGER NOT NULL,
    opening_balance DECIMAL(18,2) NOT NULL DEFAULT 0,
    period_activity DECIMAL(18,2) NOT NULL DEFAULT 0,
    ending_balance DECIMAL(18,2) NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL,
    consolidation_level VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_consolidation_level CHECK (consolidation_level IN ('entity', 'group'))
);

CREATE INDEX idx_consolidated_period_account ON consolidated_balances(period_year, period_month, standard_account_id);
CREATE INDEX idx_consolidated_entity_period ON consolidated_balances(entity_id, period_year, period_month);
```

**Consolidation Levels:**
- `entity` - Entity-level (after FX translation)
- `group` - Group-level (after IC eliminations)

### intercompany_balances

Intercompany balance reconciliation tracking.

```sql
CREATE TABLE intercompany_balances (
    ic_balance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_from_id UUID NOT NULL REFERENCES portfolio_entities(entity_id),
    entity_to_id UUID NOT NULL REFERENCES portfolio_entities(entity_id),
    standard_account_id UUID NOT NULL REFERENCES standard_chart_of_accounts(account_id),
    period_year INTEGER NOT NULL,
    period_month INTEGER NOT NULL,
    amount_entity_from DECIMAL(18,2) NOT NULL,
    amount_entity_to DECIMAL(18,2) NOT NULL,
    variance DECIMAL(18,2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    is_eliminated BOOLEAN NOT NULL DEFAULT FALSE,
    elimination_entry_id UUID REFERENCES journal_entries(entry_id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_different_entities CHECK (entity_from_id != entity_to_id)
);

CREATE INDEX idx_ic_balances_entities_period ON intercompany_balances(entity_from_id, entity_to_id, period_year, period_month);
CREATE INDEX idx_ic_balances_uneliminated ON intercompany_balances(is_eliminated)
    WHERE is_eliminated = FALSE;
```

### agent_actions (Partitioned)

AI agent audit log with 7-year retention.

```sql
CREATE TABLE agent_actions (
    action_id UUID DEFAULT uuid_generate_v4(),
    action_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    agent_id VARCHAR(100) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    entity_id UUID REFERENCES portfolio_entities(entity_id),
    description TEXT,
    input_data JSONB,
    output_data JSONB,
    confidence_score DECIMAL(3,2),
    execution_time_ms INTEGER,

    PRIMARY KEY (action_id, action_timestamp)
) PARTITION BY RANGE (action_timestamp);

-- Partitions (2020-2026)
CREATE TABLE agent_actions_2020 PARTITION OF agent_actions
    FOR VALUES FROM ('2020-01-01') TO ('2021-01-01');
CREATE TABLE agent_actions_2021 PARTITION OF agent_actions
    FOR VALUES FROM ('2021-01-01') TO ('2022-01-01');
CREATE TABLE agent_actions_2022 PARTITION OF agent_actions
    FOR VALUES FROM ('2022-01-01') TO ('2023-01-01');
CREATE TABLE agent_actions_2023 PARTITION OF agent_actions
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');
CREATE TABLE agent_actions_2024 PARTITION OF agent_actions
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
CREATE TABLE agent_actions_2025 PARTITION OF agent_actions
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
CREATE TABLE agent_actions_2026 PARTITION OF agent_actions
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

CREATE INDEX idx_agent_actions_agent_timestamp ON agent_actions(agent_id, action_timestamp DESC);
CREATE INDEX idx_agent_actions_type ON agent_actions(action_type);
```

## Row-Level Security (RLS)

### Setting User Context

```sql
-- Set current user for RLS filtering
SELECT set_current_user('user-uuid-here');
```

### RLS Policies

All sensitive tables have RLS policies that filter data based on `user_entity_access`.

**Example: trial_balances RLS policy**

```sql
ALTER TABLE trial_balances ENABLE ROW LEVEL SECURITY;

CREATE POLICY trial_balances_access_policy ON trial_balances
    FOR ALL
    USING (
        entity_id IN (
            SELECT entity_id
            FROM user_entity_access
            WHERE user_id = current_user_id()
              AND can_read = TRUE
        )
    )
    WITH CHECK (
        entity_id IN (
            SELECT entity_id
            FROM user_entity_access
            WHERE user_id = current_user_id()
              AND can_write = TRUE
        )
    );
```

## Performance Optimization

### Partitioning Strategy

**Trial Balances:**
- Partitioned by `period_year` (range partitioning)
- One partition per year (2020-2026)
- Query pruning reduces scan size by ~7x

**Agent Actions:**
- Partitioned by `action_timestamp` (range partitioning)
- One partition per year
- Automatic retention management (drop old partitions)

### Index Coverage

**80+ specialized indexes:**
- Covering indexes for index-only scans
- Partial indexes for common filters
- Composite indexes for frequent joins
- GIN indexes for JSONB fields

**Example covering index:**

```sql
CREATE INDEX idx_trial_balances_summary
    ON trial_balances(entity_id, period_year, period_month)
    INCLUDE (entity_account_id, ending_balance, currency);
```

### Query Performance Benchmarks

Expected query times (66 entities, 7 years data):

| Query Type | Time | Rows |
|-----------|------|------|
| Single entity trial balance | <10ms | ~200 |
| All entities current period | <100ms | ~13,200 |
| Consolidated balances (month) | <50ms | ~150 |
| Intercompany reconciliation | <200ms | ~500 |
| Pending approvals | <20ms | ~50 |
| Account hierarchy traversal | <15ms | ~100 |

## Maintenance Operations

### Daily

```sql
-- Update statistics
ANALYZE trial_balances;
ANALYZE journal_entries;
ANALYZE consolidated_balances;
```

### Weekly

```sql
-- Vacuum to reclaim space
VACUUM ANALYZE trial_balances;
VACUUM ANALYZE journal_entries;

-- Check index bloat
SELECT schemaname, tablename, indexname, pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 20;
```

### Monthly

```sql
-- Reindex partitioned tables (during maintenance window)
REINDEX TABLE CONCURRENTLY trial_balances;
REINDEX TABLE CONCURRENTLY agent_actions;
```

### Annual

```sql
-- Add partition for new year
CREATE TABLE trial_balances_2027 PARTITION OF trial_balances
    FOR VALUES FROM (2027) TO (2028);

CREATE TABLE agent_actions_2027 PARTITION OF agent_actions
    FOR VALUES FROM ('2027-01-01') TO ('2028-01-01');

-- Archive and drop old partitions (after 7 years)
pg_dump -t trial_balances_2020 ai_fpna_db > trial_balances_2020_archive.sql
DROP TABLE trial_balances_2020;
```

## Configuration

### PostgreSQL Settings

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

## Migration Files

Database migrations are located in `/database/migrations/`:

1. `001_initial_schema.sql` - Core tables and constraints
2. `002_rls_policies.sql` - Row-level security policies
3. `003_indexes.sql` - Performance indexes

## Capacity Planning

**Current (7 entities):**
- Trial balances: ~10,000 rows/year
- Database size: ~2GB

**Projected (66 entities):**
- Trial balances: ~100,000 rows/year
- Database size: ~20GB (7 years)

## Security

### Encryption

- **At Rest:** PostgreSQL TDE with pgcrypto extension
- **In Transit:** SSL/TLS required for all connections
- **Column-Level:** Sensitive fields encrypted with AES-256-GCM

### Access Control

- **RLS Policies:** Multi-tenant data isolation
- **Role-Based:** 11 predefined agent roles
- **API Keys:** Scoped by role and company

### Audit

- **Access Logging:** All data access logged
- **Retention:** 7 years for compliance
- **Immutable:** Audit logs cannot be modified

## See Also

- [API Reference](/Volumes/AI/Code/FPA/manual/technical-reference/api-reference.md)
- [Security Architecture](/Volumes/AI/Code/FPA/manual/technical-reference/security.md)
- [ERP Connectors](/Volumes/AI/Code/FPA/manual/technical-reference/erp-connectors.md)
