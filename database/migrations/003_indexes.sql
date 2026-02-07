-- ============================================================================
-- AI FP&A Monthly Close Automation - Performance Indexes
-- ============================================================================
-- Version: 1.0.0
-- Created: 2026-02-07
-- Description: Optimized indexes for query performance at scale (66+ entities)
-- ============================================================================

-- ============================================================================
-- COMPOSITE INDEXES FOR COMMON QUERY PATTERNS
-- ============================================================================

-- Trial balance queries: entity + period + account lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trial_balances_entity_period_account
    ON trial_balances(entity_id, period_year DESC, period_month DESC, entity_account_id);

-- Trial balance aggregations by account type
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trial_balances_period_account
    ON trial_balances(period_year DESC, period_month DESC, entity_account_id)
    INCLUDE (ending_balance, currency);

-- Trial balance lookups for specific periods
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trial_balances_period_end
    ON trial_balances(period_end_date DESC, entity_id)
    INCLUDE (entity_account_id, ending_balance);

-- Non-zero balances only (reduce index size)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trial_balances_nonzero
    ON trial_balances(entity_id, period_year, period_month)
    WHERE ABS(ending_balance) > 0.01;

-- ============================================================================
-- SUBLEDGER INDEXES
-- ============================================================================

-- Subledger detail queries by entity and period
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_subledger_entity_period_date
    ON subledger_entries(entity_id, period_year DESC, period_month DESC, transaction_date DESC);

-- Subledger account reconciliation
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_subledger_account_period
    ON subledger_entries(entity_account_id, period_year, period_month)
    INCLUDE (debit_amount, credit_amount);

-- Subledger counterparty analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_subledger_counterparty
    ON subledger_entries(counterparty, transaction_date DESC)
    WHERE counterparty IS NOT NULL;

-- Subledger dimensions filtering (cost center, department, etc.)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_subledger_dimensions_gin
    ON subledger_entries USING gin(dimensions jsonb_path_ops);

-- ============================================================================
-- CHART OF ACCOUNTS INDEXES
-- ============================================================================

-- Standard COA hierarchy traversal
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_standard_coa_hierarchy
    ON standard_chart_of_accounts(parent_account_id, level, account_code)
    WHERE parent_account_id IS NOT NULL;

-- Standard COA by type and standard
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_standard_coa_type_standard
    ON standard_chart_of_accounts(accounting_standard, account_type, account_subtype)
    WHERE is_active = TRUE;

-- Entity COA lookups by local code
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entity_coa_entity_local
    ON entity_chart_of_accounts(entity_id, local_account_code, effective_from DESC)
    WHERE is_active = TRUE;

-- Entity COA reverse lookup (standard to local)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entity_coa_standard_entity
    ON entity_chart_of_accounts(standard_account_id, entity_id, effective_from DESC)
    WHERE is_active = TRUE;

-- Low confidence mappings for review
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entity_coa_low_confidence
    ON entity_chart_of_accounts(entity_id, mapping_confidence)
    WHERE mapping_confidence < 0.8 AND is_active = TRUE;

-- ============================================================================
-- JOURNAL ENTRY INDEXES
-- ============================================================================

-- Journal entries by entity and period
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_journal_entries_entity_period_status
    ON journal_entries(entity_id, period_year DESC, period_month DESC, status);

-- Pending approval journals
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_journal_entries_pending_approval
    ON journal_entries(status, entity_id, created_at DESC)
    WHERE status IN ('pending_review', 'approved');

-- AI-generated journals for review
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_journal_entries_ai_generated
    ON journal_entries(entry_source, ai_confidence, created_at DESC)
    WHERE entry_source = 'ai_generated';

-- Auto-reversing journals
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_journal_entries_auto_reverse
    ON journal_entries(auto_reverse, reverse_period_year, reverse_period_month)
    WHERE auto_reverse = TRUE AND posted_at IS NOT NULL;

-- Journal entry audit trail
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_journal_entries_audit
    ON journal_entries(created_by, created_at DESC)
    INCLUDE (entry_number, status, description);

-- Journal lines by account for rollup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_journal_lines_account_period
    ON journal_entry_lines(standard_account_id, entry_id)
    INCLUDE (debit_amount, credit_amount);

-- ============================================================================
-- CONSOLIDATION INDEXES
-- ============================================================================

-- Consolidated balances by period and account
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_consolidated_period_account
    ON consolidated_balances(period_year DESC, period_month DESC, standard_account_id)
    INCLUDE (ending_balance, currency);

-- Consolidated balances by entity
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_consolidated_entity_period
    ON consolidated_balances(entity_id, period_year DESC, period_month DESC)
    WHERE entity_id IS NOT NULL;

-- Latest consolidated balances
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_consolidated_latest
    ON consolidated_balances(period_end_date DESC, standard_account_id, consolidation_level);

-- Intercompany reconciliation queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ic_balances_entities_period
    ON intercompany_balances(entity_from_id, entity_to_id, period_year DESC, period_month DESC);

-- Intercompany balances by account
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ic_balances_account_period
    ON intercompany_balances(standard_account_id, period_year DESC, period_month DESC)
    INCLUDE (amount_entity_from, amount_entity_to, variance);

-- Unreconciled intercompany balances
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ic_balances_unreconciled
    ON intercompany_balances(period_year DESC, period_month DESC, variance)
    WHERE reconciled_at IS NULL AND ABS(variance) > 0.01;

-- ============================================================================
-- FX RATES INDEXES
-- ============================================================================

-- FX rates lookups by currency pair and date
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fx_rates_pair_date
    ON fx_rates(from_currency, to_currency, rate_date DESC)
    WHERE is_official = TRUE;

-- Monthly FX rates lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fx_rates_monthly_pair_period
    ON fx_rates_monthly(from_currency, to_currency, period_year DESC, period_month DESC);

-- Latest FX rates per currency pair
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fx_rates_latest
    ON fx_rates(from_currency, to_currency, rate_date DESC, source)
    INCLUDE (rate);

-- ============================================================================
-- ETL AND DATA QUALITY INDEXES
-- ============================================================================

-- ETL batches by entity and period
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_etl_batches_entity_period_type
    ON etl_batches(entity_id, period_year DESC, period_month DESC, batch_type, status);

-- Recent ETL batches
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_etl_batches_recent
    ON etl_batches(started_at DESC)
    INCLUDE (entity_id, batch_type, status, records_processed);

-- Failed ETL batches
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_etl_batches_failed
    ON etl_batches(status, started_at DESC)
    WHERE status IN ('failed', 'partial');

-- Validation results by entity and severity
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_validation_entity_severity
    ON validation_results(entity_id, severity, created_at DESC)
    WHERE resolved_at IS NULL;

-- Validation results by type and period
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_validation_type_period
    ON validation_results(validation_type, period_year DESC, period_month DESC)
    WHERE resolved_at IS NULL;

-- Critical unresolved validations
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_validation_critical_unresolved
    ON validation_results(severity, created_at DESC)
    WHERE severity = 'error' AND resolved_at IS NULL;

-- ============================================================================
-- AUDIT TRAIL INDEXES
-- ============================================================================

-- Agent actions by agent and time
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_agent_actions_agent_time
    ON agent_actions(agent_name, created_at DESC)
    INCLUDE (action_type, success, execution_time_ms);

-- Agent actions by entity
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_agent_actions_entity_time
    ON agent_actions(entity_id, created_at DESC)
    WHERE entity_id IS NOT NULL;

-- Failed agent actions
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_agent_actions_failed
    ON agent_actions(success, created_at DESC)
    WHERE success = FALSE;

-- Slow agent actions (performance monitoring)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_agent_actions_slow
    ON agent_actions(execution_time_ms DESC, created_at DESC)
    WHERE execution_time_ms > 5000;

-- Credential access by user and time
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_credential_log_user_time
    ON credential_access_log(user_id, accessed_at DESC)
    INCLUDE (access_type, success);

-- Failed credential access attempts
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_credential_log_failed
    ON credential_access_log(success, accessed_at DESC, user_id)
    WHERE success = FALSE;

-- Recent credential access by entity
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_credential_log_entity_time
    ON credential_access_log(entity_id, accessed_at DESC)
    WHERE entity_id IS NOT NULL;

-- ============================================================================
-- PERIOD LOCKING INDEXES
-- ============================================================================

-- Period locks by entity and period
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_period_locks_entity_period
    ON period_locks(entity_id, period_year DESC, period_month DESC)
    INCLUDE (lock_status, locked_at);

-- Locked periods (prevent modifications)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_period_locks_locked
    ON period_locks(entity_id, lock_status)
    WHERE lock_status IN ('soft_locked', 'hard_locked');

-- Recently unlocked periods (audit trail)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_period_locks_unlocked
    ON period_locks(unlocked_at DESC, entity_id)
    WHERE unlocked_at IS NOT NULL;

-- ============================================================================
-- USER AND ACCESS INDEXES
-- ============================================================================

-- User entity access lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_entity_access_permissions
    ON user_entity_access(user_id, entity_id)
    INCLUDE (can_read, can_write, can_approve, can_lock_periods);

-- Entities accessible by user
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_entity_access_user_entities
    ON user_entity_access(user_id, can_read)
    WHERE can_read = TRUE;

-- Users with access to entity
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_entity_access_entity_users
    ON user_entity_access(entity_id, can_write)
    WHERE can_write = TRUE;

-- ============================================================================
-- TEXT SEARCH INDEXES
-- ============================================================================

-- Full-text search on journal entry descriptions
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_journal_entries_description_fts
    ON journal_entries USING gin(to_tsvector('english', description));

-- Account name search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_standard_coa_name_fts
    ON standard_chart_of_accounts USING gin(to_tsvector('english', account_name));

-- Entity name search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_portfolio_entities_name_fts
    ON portfolio_entities USING gin(to_tsvector('english', legal_name || ' ' || COALESCE(trade_name, '')));

-- Trigram indexes for fuzzy matching
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_standard_coa_name_trgm
    ON standard_chart_of_accounts USING gin(account_name gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entity_coa_local_name_trgm
    ON entity_chart_of_accounts USING gin(local_account_name gin_trgm_ops);

-- ============================================================================
-- PARTIAL INDEXES FOR SPECIFIC USE CASES
-- ============================================================================

-- Active entities only (most queries filter on this)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_portfolio_entities_active
    ON portfolio_entities(entity_code, legal_name)
    WHERE status = 'active';

-- Posted journals only (final records)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_journal_entries_posted
    ON journal_entries(entity_id, period_year DESC, period_month DESC, posted_at DESC)
    WHERE status = 'posted';

-- Trial balances for current year (hot data)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trial_balances_current_year
    ON trial_balances(entity_id, period_month DESC, entity_account_id)
    WHERE period_year = EXTRACT(YEAR FROM CURRENT_DATE);

-- ============================================================================
-- COVERING INDEXES (INDEX-ONLY SCANS)
-- ============================================================================

-- Trial balance summary queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trial_balances_summary
    ON trial_balances(entity_id, period_year, period_month)
    INCLUDE (entity_account_id, ending_balance, currency);

-- Journal entry summary
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_journal_entries_summary
    ON journal_entries(entity_id, period_year, period_month, status)
    INCLUDE (entry_number, entry_date, description, entry_source);

-- Consolidated balance rollup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_consolidated_rollup
    ON consolidated_balances(period_year, period_month, standard_account_id)
    INCLUDE (ending_balance, currency, consolidation_level);

-- ============================================================================
-- STATISTICS UPDATES
-- ============================================================================

-- Update statistics for critical tables (run after bulk loads)
-- These are manual commands to run during maintenance windows

-- ANALYZE portfolio_entities;
-- ANALYZE trial_balances;
-- ANALYZE journal_entries;
-- ANALYZE consolidated_balances;
-- ANALYZE standard_chart_of_accounts;

-- ============================================================================
-- INDEX MAINTENANCE NOTES
-- ============================================================================

-- Monitor index bloat with:
-- SELECT schemaname, tablename, indexname,
--        pg_size_pretty(pg_relation_size(indexrelid)) as index_size
-- FROM pg_stat_user_indexes
-- WHERE schemaname = 'public'
-- ORDER BY pg_relation_size(indexrelid) DESC;

-- Identify unused indexes:
-- SELECT schemaname, tablename, indexname, idx_scan
-- FROM pg_stat_user_indexes
-- WHERE schemaname = 'public' AND idx_scan = 0
-- ORDER BY pg_relation_size(indexrelid) DESC;

-- Reindex partitioned tables (run during maintenance):
-- REINDEX TABLE CONCURRENTLY trial_balances;
-- REINDEX TABLE CONCURRENTLY agent_actions;

-- ============================================================================
-- PERFORMANCE BENCHMARKS (Expected with 66 entities, 7 years data)
-- ============================================================================

/*
Query Type                          | Expected Time | Index Used
------------------------------------|---------------|----------------------------------
Single entity trial balance         | < 10ms        | idx_trial_balances_entity_period
All entities current period         | < 100ms       | idx_trial_balances_period_account
Consolidated balances (month)       | < 50ms        | idx_consolidated_period_account
Intercompany reconciliation         | < 200ms       | idx_ic_balances_entities_period
Journal entry search by number      | < 5ms         | journal_entries_pkey
Pending approvals across entities   | < 20ms        | idx_journal_entries_pending_approval
Account hierarchy traversal         | < 15ms        | idx_standard_coa_hierarchy
Failed validation alerts            | < 10ms        | idx_validation_critical_unresolved
Agent action audit (user)           | < 30ms        | idx_agent_actions_agent_time
FX rate lookup (date, pair)         | < 5ms         | idx_fx_rates_pair_date

Assumptions:
- 66 entities
- 7 years of monthly data (66 * 12 * 7 = 5,544 entity-months)
- Average 200 accounts per entity trial balance
- ~1.1M trial balance records
- PostgreSQL 15+ with 8GB shared_buffers, work_mem 256MB
- SSDs with < 1ms random read latency
*/

-- ============================================================================
-- MONITORING QUERIES
-- ============================================================================

-- Index usage statistics
CREATE VIEW v_index_usage_stats AS
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
    CASE
        WHEN idx_scan = 0 THEN 'Never used'
        WHEN idx_scan < 100 THEN 'Rarely used'
        WHEN idx_scan < 1000 THEN 'Moderately used'
        ELSE 'Frequently used'
    END as usage_category
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

COMMENT ON VIEW v_index_usage_stats IS 'Monitor index usage to identify unused or underutilized indexes';

-- Table and index sizes
CREATE VIEW v_table_sizes AS
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS indexes_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

COMMENT ON VIEW v_table_sizes IS 'Monitor table and index storage usage';
