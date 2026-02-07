-- ============================================================================
-- AI FP&A Monthly Close Automation - Initial Schema
-- ============================================================================
-- Version: 1.0.0
-- Created: 2026-02-07
-- Description: Core database schema for multi-tenant IFRS/US GAAP consolidation
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gist";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================================
-- ENUMS AND TYPES
-- ============================================================================

CREATE TYPE entity_status AS ENUM ('active', 'inactive', 'pending_closure', 'closed');
CREATE TYPE user_role AS ENUM ('admin', 'finance_manager', 'controller', 'analyst', 'auditor', 'read_only');
CREATE TYPE accounting_standard AS ENUM ('IFRS', 'US_GAAP', 'BR_GAAP');
CREATE TYPE account_type AS ENUM ('asset', 'liability', 'equity', 'revenue', 'expense');
CREATE TYPE account_subtype AS ENUM (
    'current_asset', 'non_current_asset', 'current_liability', 'non_current_liability',
    'contributed_capital', 'retained_earnings', 'other_equity',
    'operating_revenue', 'non_operating_revenue',
    'operating_expense', 'non_operating_expense', 'cost_of_goods_sold'
);
CREATE TYPE balance_type AS ENUM ('debit', 'credit');
CREATE TYPE entry_status AS ENUM ('draft', 'pending_review', 'approved', 'posted', 'reversed');
CREATE TYPE entry_source AS ENUM ('trial_balance', 'manual_journal', 'consolidation_adjustment', 'fx_revaluation', 'intercompany_elimination', 'ai_generated');
CREATE TYPE validation_severity AS ENUM ('error', 'warning', 'info');
CREATE TYPE etl_status AS ENUM ('running', 'completed', 'failed', 'partial');
CREATE TYPE period_lock_status AS ENUM ('open', 'soft_locked', 'hard_locked');
CREATE TYPE currency_code AS ENUM ('USD', 'BRL', 'EUR', 'GBP', 'JPY', 'CNY', 'MXN', 'ARS');

-- ============================================================================
-- CORE ENTITIES
-- ============================================================================

-- Portfolio companies and entities
CREATE TABLE portfolio_entities (
    entity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_code VARCHAR(20) UNIQUE NOT NULL,
    legal_name VARCHAR(255) NOT NULL,
    trade_name VARCHAR(255),
    tax_id VARCHAR(50) UNIQUE,
    functional_currency currency_code NOT NULL DEFAULT 'BRL',
    presentation_currency currency_code NOT NULL DEFAULT 'USD',
    accounting_standard accounting_standard NOT NULL DEFAULT 'IFRS',
    country_code CHAR(2) NOT NULL,
    status entity_status NOT NULL DEFAULT 'active',
    parent_entity_id UUID REFERENCES portfolio_entities(entity_id),
    ownership_percentage NUMERIC(5,2) CHECK (ownership_percentage >= 0 AND ownership_percentage <= 100),
    consolidation_method VARCHAR(50) CHECK (consolidation_method IN ('full', 'equity', 'proportional', 'none')),
    fiscal_year_end DATE NOT NULL DEFAULT '12-31',
    inception_date DATE NOT NULL,
    closure_date DATE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE INDEX idx_portfolio_entities_status ON portfolio_entities(status) WHERE status = 'active';
CREATE INDEX idx_portfolio_entities_parent ON portfolio_entities(parent_entity_id) WHERE parent_entity_id IS NOT NULL;
CREATE INDEX idx_portfolio_entities_code ON portfolio_entities(entity_code);

COMMENT ON TABLE portfolio_entities IS 'Portfolio companies with multi-level consolidation support';

-- Users and authentication
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'read_only',
    is_active BOOLEAN NOT NULL DEFAULT true,
    password_hash VARCHAR(255),
    last_login_at TIMESTAMPTZ,
    mfa_enabled BOOLEAN NOT NULL DEFAULT false,
    mfa_secret VARCHAR(255),
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = true;

-- User entity access (multi-tenant isolation)
CREATE TABLE user_entity_access (
    access_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    entity_id UUID NOT NULL REFERENCES portfolio_entities(entity_id) ON DELETE CASCADE,
    can_read BOOLEAN NOT NULL DEFAULT true,
    can_write BOOLEAN NOT NULL DEFAULT false,
    can_approve BOOLEAN NOT NULL DEFAULT false,
    can_lock_periods BOOLEAN NOT NULL DEFAULT false,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    granted_by UUID REFERENCES users(user_id),
    UNIQUE(user_id, entity_id)
);

CREATE INDEX idx_user_entity_access_user ON user_entity_access(user_id);
CREATE INDEX idx_user_entity_access_entity ON user_entity_access(entity_id);

-- ============================================================================
-- CHART OF ACCOUNTS
-- ============================================================================

-- Standard chart of accounts (master template)
CREATE TABLE standard_chart_of_accounts (
    account_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_code VARCHAR(50) UNIQUE NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    account_type account_type NOT NULL,
    account_subtype account_subtype NOT NULL,
    normal_balance balance_type NOT NULL,
    parent_account_id UUID REFERENCES standard_chart_of_accounts(account_id),
    level INTEGER NOT NULL CHECK (level >= 1 AND level <= 10),
    is_control_account BOOLEAN NOT NULL DEFAULT false,
    is_posting_account BOOLEAN NOT NULL DEFAULT true,
    requires_subledger BOOLEAN NOT NULL DEFAULT false,
    accounting_standard accounting_standard NOT NULL DEFAULT 'IFRS',
    ifrs_tag VARCHAR(100),
    us_gaap_tag VARCHAR(100),
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_standard_coa_code ON standard_chart_of_accounts(account_code);
CREATE INDEX idx_standard_coa_type ON standard_chart_of_accounts(account_type);
CREATE INDEX idx_standard_coa_parent ON standard_chart_of_accounts(parent_account_id) WHERE parent_account_id IS NOT NULL;
CREATE INDEX idx_standard_coa_active ON standard_chart_of_accounts(is_active) WHERE is_active = true;

-- Entity-specific chart of accounts mapping
CREATE TABLE entity_chart_of_accounts (
    entity_account_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID NOT NULL REFERENCES portfolio_entities(entity_id) ON DELETE CASCADE,
    standard_account_id UUID NOT NULL REFERENCES standard_chart_of_accounts(account_id),
    local_account_code VARCHAR(50) NOT NULL,
    local_account_name VARCHAR(255) NOT NULL,
    mapping_confidence NUMERIC(3,2) CHECK (mapping_confidence >= 0 AND mapping_confidence <= 1),
    mapping_notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    effective_from DATE NOT NULL,
    effective_to DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(entity_id, local_account_code, effective_from)
);

CREATE INDEX idx_entity_coa_entity ON entity_chart_of_accounts(entity_id);
CREATE INDEX idx_entity_coa_standard ON entity_chart_of_accounts(standard_account_id);
CREATE INDEX idx_entity_coa_local_code ON entity_chart_of_accounts(entity_id, local_account_code);
CREATE INDEX idx_entity_coa_active ON entity_chart_of_accounts(is_active) WHERE is_active = true;

-- ============================================================================
-- FINANCIAL DATA (PARTITIONED)
-- ============================================================================

-- Trial balances (partitioned by fiscal year)
CREATE TABLE trial_balances (
    balance_id UUID DEFAULT uuid_generate_v4(),
    entity_id UUID NOT NULL REFERENCES portfolio_entities(entity_id),
    period_year INTEGER NOT NULL CHECK (period_year >= 2020 AND period_year <= 2100),
    period_month INTEGER NOT NULL CHECK (period_month >= 1 AND period_month <= 12),
    period_end_date DATE NOT NULL,
    entity_account_id UUID NOT NULL REFERENCES entity_chart_of_accounts(entity_account_id),
    beginning_balance NUMERIC(20,2) NOT NULL DEFAULT 0,
    debit_amount NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (debit_amount >= 0),
    credit_amount NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (credit_amount >= 0),
    ending_balance NUMERIC(20,2) NOT NULL,
    currency currency_code NOT NULL,
    etl_batch_id UUID,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (entity_id, period_year, period_month, entity_account_id)
) PARTITION BY RANGE (period_year);

-- Create partitions for 7 years (2020-2026)
CREATE TABLE trial_balances_2020 PARTITION OF trial_balances FOR VALUES FROM (2020) TO (2021);
CREATE TABLE trial_balances_2021 PARTITION OF trial_balances FOR VALUES FROM (2021) TO (2022);
CREATE TABLE trial_balances_2022 PARTITION OF trial_balances FOR VALUES FROM (2022) TO (2023);
CREATE TABLE trial_balances_2023 PARTITION OF trial_balances FOR VALUES FROM (2023) TO (2024);
CREATE TABLE trial_balances_2024 PARTITION OF trial_balances FOR VALUES FROM (2024) TO (2025);
CREATE TABLE trial_balances_2025 PARTITION OF trial_balances FOR VALUES FROM (2025) TO (2026);
CREATE TABLE trial_balances_2026 PARTITION OF trial_balances FOR VALUES FROM (2026) TO (2027);

CREATE INDEX idx_trial_balances_entity_period ON trial_balances(entity_id, period_year, period_month);
CREATE INDEX idx_trial_balances_account ON trial_balances(entity_account_id);
CREATE INDEX idx_trial_balances_period_end ON trial_balances(period_end_date);

COMMENT ON TABLE trial_balances IS 'Entity trial balances partitioned by fiscal year for optimal query performance';

-- Subledger entries (for accounts requiring detail tracking)
CREATE TABLE subledger_entries (
    entry_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID NOT NULL REFERENCES portfolio_entities(entity_id),
    entity_account_id UUID NOT NULL REFERENCES entity_chart_of_accounts(entity_account_id),
    period_year INTEGER NOT NULL,
    period_month INTEGER NOT NULL,
    transaction_date DATE NOT NULL,
    reference_number VARCHAR(100),
    counterparty VARCHAR(255),
    description TEXT,
    debit_amount NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (debit_amount >= 0),
    credit_amount NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (credit_amount >= 0),
    currency currency_code NOT NULL,
    dimensions JSONB DEFAULT '{}', -- For cost center, department, project, etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_subledger_entity_period ON subledger_entries(entity_id, period_year, period_month);
CREATE INDEX idx_subledger_account ON subledger_entries(entity_account_id);
CREATE INDEX idx_subledger_date ON subledger_entries(transaction_date);
CREATE INDEX idx_subledger_dimensions ON subledger_entries USING gin(dimensions);

-- ============================================================================
-- FOREIGN EXCHANGE RATES
-- ============================================================================

-- Daily FX rates
CREATE TABLE fx_rates (
    rate_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rate_date DATE NOT NULL,
    from_currency currency_code NOT NULL,
    to_currency currency_code NOT NULL,
    rate NUMERIC(18,8) NOT NULL CHECK (rate > 0),
    source VARCHAR(100) NOT NULL, -- 'ECB', 'BCB', 'Manual', 'Bloomberg'
    is_official BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(rate_date, from_currency, to_currency)
);

CREATE INDEX idx_fx_rates_date ON fx_rates(rate_date DESC);
CREATE INDEX idx_fx_rates_currencies ON fx_rates(from_currency, to_currency, rate_date DESC);

-- Monthly average FX rates (for P&L translation)
CREATE TABLE fx_rates_monthly (
    rate_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    period_year INTEGER NOT NULL,
    period_month INTEGER NOT NULL,
    from_currency currency_code NOT NULL,
    to_currency currency_code NOT NULL,
    average_rate NUMERIC(18,8) NOT NULL CHECK (average_rate > 0),
    calculation_method VARCHAR(50) NOT NULL DEFAULT 'arithmetic_mean',
    source VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(period_year, period_month, from_currency, to_currency)
);

CREATE INDEX idx_fx_rates_monthly_period ON fx_rates_monthly(period_year, period_month);
CREATE INDEX idx_fx_rates_monthly_currencies ON fx_rates_monthly(from_currency, to_currency);

-- ============================================================================
-- CONSOLIDATION
-- ============================================================================

-- Journal entries (manual adjustments, eliminations, AI-generated)
CREATE TABLE journal_entries (
    entry_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entry_number VARCHAR(50) UNIQUE NOT NULL,
    entity_id UUID REFERENCES portfolio_entities(entity_id),
    period_year INTEGER NOT NULL,
    period_month INTEGER NOT NULL,
    entry_date DATE NOT NULL,
    entry_source entry_source NOT NULL,
    status entry_status NOT NULL DEFAULT 'draft',
    description TEXT NOT NULL,
    reverses_entry_id UUID REFERENCES journal_entries(entry_id),
    auto_reverse BOOLEAN NOT NULL DEFAULT false,
    reverse_period_year INTEGER,
    reverse_period_month INTEGER,
    created_by UUID REFERENCES users(user_id),
    approved_by UUID REFERENCES users(user_id),
    posted_by UUID REFERENCES users(user_id),
    approved_at TIMESTAMPTZ,
    posted_at TIMESTAMPTZ,
    ai_confidence NUMERIC(3,2) CHECK (ai_confidence >= 0 AND ai_confidence <= 1),
    ai_explanation TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_journal_entries_entity_period ON journal_entries(entity_id, period_year, period_month);
CREATE INDEX idx_journal_entries_status ON journal_entries(status);
CREATE INDEX idx_journal_entries_source ON journal_entries(entry_source);
CREATE INDEX idx_journal_entries_date ON journal_entries(entry_date);

-- Journal entry lines
CREATE TABLE journal_entry_lines (
    line_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entry_id UUID NOT NULL REFERENCES journal_entries(entry_id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    standard_account_id UUID NOT NULL REFERENCES standard_chart_of_accounts(account_id),
    entity_id UUID REFERENCES portfolio_entities(entity_id),
    debit_amount NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (debit_amount >= 0),
    credit_amount NUMERIC(20,2) NOT NULL DEFAULT 0 CHECK (credit_amount >= 0),
    currency currency_code NOT NULL,
    description TEXT,
    dimensions JSONB DEFAULT '{}',
    UNIQUE(entry_id, line_number),
    CHECK ((debit_amount > 0 AND credit_amount = 0) OR (credit_amount > 0 AND debit_amount = 0))
);

CREATE INDEX idx_journal_lines_entry ON journal_entry_lines(entry_id);
CREATE INDEX idx_journal_lines_account ON journal_entry_lines(standard_account_id);

-- Consolidated balances (final output)
CREATE TABLE consolidated_balances (
    balance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    period_year INTEGER NOT NULL,
    period_month INTEGER NOT NULL,
    period_end_date DATE NOT NULL,
    standard_account_id UUID NOT NULL REFERENCES standard_chart_of_accounts(account_id),
    entity_id UUID REFERENCES portfolio_entities(entity_id), -- NULL for full consolidation
    beginning_balance NUMERIC(20,2) NOT NULL DEFAULT 0,
    period_activity NUMERIC(20,2) NOT NULL DEFAULT 0,
    ending_balance NUMERIC(20,2) NOT NULL,
    currency currency_code NOT NULL DEFAULT 'USD',
    consolidation_level VARCHAR(50) NOT NULL DEFAULT 'group', -- 'entity', 'segment', 'group'
    calculation_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(period_year, period_month, standard_account_id, entity_id, consolidation_level)
);

CREATE INDEX idx_consolidated_balances_period ON consolidated_balances(period_year, period_month);
CREATE INDEX idx_consolidated_balances_account ON consolidated_balances(standard_account_id);
CREATE INDEX idx_consolidated_balances_entity ON consolidated_balances(entity_id) WHERE entity_id IS NOT NULL;

-- Intercompany balances tracking
CREATE TABLE intercompany_balances (
    ic_balance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    period_year INTEGER NOT NULL,
    period_month INTEGER NOT NULL,
    entity_from_id UUID NOT NULL REFERENCES portfolio_entities(entity_id),
    entity_to_id UUID NOT NULL REFERENCES portfolio_entities(entity_id),
    standard_account_id UUID NOT NULL REFERENCES standard_chart_of_accounts(account_id),
    amount_entity_from NUMERIC(20,2) NOT NULL,
    amount_entity_to NUMERIC(20,2) NOT NULL,
    currency currency_code NOT NULL,
    variance NUMERIC(20,2) GENERATED ALWAYS AS (amount_entity_from + amount_entity_to) STORED,
    variance_threshold_exceeded BOOLEAN GENERATED ALWAYS AS (ABS(amount_entity_from + amount_to) > 100) STORED,
    reconciliation_notes TEXT,
    reconciled_by UUID REFERENCES users(user_id),
    reconciled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (entity_from_id != entity_to_id)
);

CREATE INDEX idx_ic_balances_period ON intercompany_balances(period_year, period_month);
CREATE INDEX idx_ic_balances_entities ON intercompany_balances(entity_from_id, entity_to_id);
CREATE INDEX idx_ic_balances_variance ON intercompany_balances(variance) WHERE ABS(variance) > 100;

-- ============================================================================
-- ETL AND DATA QUALITY
-- ============================================================================

-- ETL batch tracking
CREATE TABLE etl_batches (
    batch_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID NOT NULL REFERENCES portfolio_entities(entity_id),
    period_year INTEGER NOT NULL,
    period_month INTEGER NOT NULL,
    batch_type VARCHAR(50) NOT NULL, -- 'trial_balance', 'subledger', 'fx_rates'
    status etl_status NOT NULL DEFAULT 'running',
    source_system VARCHAR(100) NOT NULL,
    source_file_path TEXT,
    source_file_hash VARCHAR(64),
    records_processed INTEGER NOT NULL DEFAULT 0,
    records_inserted INTEGER NOT NULL DEFAULT 0,
    records_updated INTEGER NOT NULL DEFAULT 0,
    records_failed INTEGER NOT NULL DEFAULT 0,
    error_log TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    started_by UUID REFERENCES users(user_id),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_etl_batches_entity_period ON etl_batches(entity_id, period_year, period_month);
CREATE INDEX idx_etl_batches_status ON etl_batches(status);
CREATE INDEX idx_etl_batches_started ON etl_batches(started_at DESC);

-- Validation results
CREATE TABLE validation_results (
    validation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID REFERENCES portfolio_entities(entity_id),
    period_year INTEGER NOT NULL,
    period_month INTEGER NOT NULL,
    validation_type VARCHAR(100) NOT NULL,
    severity validation_severity NOT NULL,
    rule_code VARCHAR(50) NOT NULL,
    rule_description TEXT NOT NULL,
    affected_records JSONB,
    expected_value NUMERIC(20,2),
    actual_value NUMERIC(20,2),
    variance NUMERIC(20,2),
    resolution_notes TEXT,
    resolved_by UUID REFERENCES users(user_id),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_validation_entity_period ON validation_results(entity_id, period_year, period_month);
CREATE INDEX idx_validation_severity ON validation_results(severity) WHERE resolved_at IS NULL;
CREATE INDEX idx_validation_unresolved ON validation_results(created_at DESC) WHERE resolved_at IS NULL;

-- ============================================================================
-- AUDIT TRAIL
-- ============================================================================

-- AI agent actions log (7-year retention)
CREATE TABLE agent_actions (
    action_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name VARCHAR(100) NOT NULL,
    action_type VARCHAR(100) NOT NULL,
    entity_id UUID REFERENCES portfolio_entities(entity_id),
    period_year INTEGER,
    period_month INTEGER,
    input_data JSONB,
    output_data JSONB,
    confidence_score NUMERIC(3,2),
    execution_time_ms INTEGER,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    user_id UUID REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Create partitions for 7 years
CREATE TABLE agent_actions_2020 PARTITION OF agent_actions FOR VALUES FROM ('2020-01-01') TO ('2021-01-01');
CREATE TABLE agent_actions_2021 PARTITION OF agent_actions FOR VALUES FROM ('2021-01-01') TO ('2022-01-01');
CREATE TABLE agent_actions_2022 PARTITION OF agent_actions FOR VALUES FROM ('2022-01-01') TO ('2023-01-01');
CREATE TABLE agent_actions_2023 PARTITION OF agent_actions FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');
CREATE TABLE agent_actions_2024 PARTITION OF agent_actions FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
CREATE TABLE agent_actions_2025 PARTITION OF agent_actions FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
CREATE TABLE agent_actions_2026 PARTITION OF agent_actions FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

CREATE INDEX idx_agent_actions_created ON agent_actions(created_at DESC);
CREATE INDEX idx_agent_actions_agent ON agent_actions(agent_name, created_at DESC);
CREATE INDEX idx_agent_actions_entity ON agent_actions(entity_id, created_at DESC) WHERE entity_id IS NOT NULL;

-- Credential access log (sensitive operations)
CREATE TABLE credential_access_log (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id),
    entity_id UUID REFERENCES portfolio_entities(entity_id),
    access_type VARCHAR(100) NOT NULL,
    resource_accessed VARCHAR(255) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN NOT NULL,
    failure_reason TEXT,
    accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_credential_log_user ON credential_access_log(user_id, accessed_at DESC);
CREATE INDEX idx_credential_log_entity ON credential_access_log(entity_id, accessed_at DESC);
CREATE INDEX idx_credential_log_failures ON credential_access_log(accessed_at DESC) WHERE success = false;

-- ============================================================================
-- PERIOD LOCKING
-- ============================================================================

CREATE TABLE period_locks (
    lock_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID NOT NULL REFERENCES portfolio_entities(entity_id),
    period_year INTEGER NOT NULL,
    period_month INTEGER NOT NULL,
    lock_status period_lock_status NOT NULL DEFAULT 'open',
    locked_by UUID REFERENCES users(user_id),
    locked_at TIMESTAMPTZ,
    unlock_reason TEXT,
    unlocked_by UUID REFERENCES users(user_id),
    unlocked_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    UNIQUE(entity_id, period_year, period_month)
);

CREATE INDEX idx_period_locks_entity ON period_locks(entity_id, period_year DESC, period_month DESC);
CREATE INDEX idx_period_locks_status ON period_locks(lock_status);

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_portfolio_entities_updated_at BEFORE UPDATE ON portfolio_entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_standard_coa_updated_at BEFORE UPDATE ON standard_chart_of_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_entity_coa_updated_at BEFORE UPDATE ON entity_chart_of_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_journal_entries_updated_at BEFORE UPDATE ON journal_entries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- CONSTRAINTS AND VALIDATION FUNCTIONS
-- ============================================================================

-- Ensure journal entries balance
CREATE OR REPLACE FUNCTION validate_journal_entry_balance()
RETURNS TRIGGER AS $$
DECLARE
    total_debits NUMERIC(20,2);
    total_credits NUMERIC(20,2);
BEGIN
    SELECT
        COALESCE(SUM(debit_amount), 0),
        COALESCE(SUM(credit_amount), 0)
    INTO total_debits, total_credits
    FROM journal_entry_lines
    WHERE entry_id = COALESCE(NEW.entry_id, OLD.entry_id);

    IF ABS(total_debits - total_credits) > 0.01 THEN
        RAISE EXCEPTION 'Journal entry does not balance: debits=%, credits=%', total_debits, total_credits;
    END IF;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER validate_journal_balance
    AFTER INSERT OR UPDATE OR DELETE ON journal_entry_lines
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION validate_journal_entry_balance();

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Active portfolio entities with hierarchy
CREATE VIEW v_active_entities AS
SELECT
    e.entity_id,
    e.entity_code,
    e.legal_name,
    e.functional_currency,
    e.presentation_currency,
    e.status,
    p.entity_code as parent_code,
    p.legal_name as parent_name,
    e.ownership_percentage,
    e.consolidation_method
FROM portfolio_entities e
LEFT JOIN portfolio_entities p ON e.parent_entity_id = p.entity_id
WHERE e.status = 'active';

-- Latest trial balance by entity and period
CREATE VIEW v_latest_trial_balances AS
WITH ranked_balances AS (
    SELECT
        tb.*,
        eca.local_account_code,
        eca.local_account_name,
        sca.account_code as standard_account_code,
        sca.account_name as standard_account_name,
        sca.account_type,
        ROW_NUMBER() OVER (PARTITION BY tb.entity_id ORDER BY tb.period_year DESC, tb.period_month DESC) as rn
    FROM trial_balances tb
    JOIN entity_chart_of_accounts eca ON tb.entity_account_id = eca.entity_account_id
    JOIN standard_chart_of_accounts sca ON eca.standard_account_id = sca.account_id
)
SELECT * FROM ranked_balances WHERE rn = 1;

-- Intercompany reconciliation variance report
CREATE VIEW v_ic_reconciliation_status AS
SELECT
    period_year,
    period_month,
    ef.entity_code as from_entity,
    et.entity_code as to_entity,
    sca.account_code,
    sca.account_name,
    amount_entity_from,
    amount_entity_to,
    variance,
    CASE
        WHEN ABS(variance) <= 0.01 THEN 'Matched'
        WHEN ABS(variance) <= 100 THEN 'Minor Variance'
        ELSE 'Significant Variance'
    END as reconciliation_status,
    reconciled_at IS NOT NULL as is_reconciled
FROM intercompany_balances ic
JOIN portfolio_entities ef ON ic.entity_from_id = ef.entity_id
JOIN portfolio_entities et ON ic.entity_to_id = et.entity_id
JOIN standard_chart_of_accounts sca ON ic.standard_account_id = sca.account_id;

-- ============================================================================
-- PERFORMANCE STATISTICS
-- ============================================================================

COMMENT ON DATABASE current_database() IS 'AI FP&A Monthly Close Automation - Multi-tenant IFRS/US GAAP consolidation with 7-year audit trail';

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO read_only_role;
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO analyst_role;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin_role;
