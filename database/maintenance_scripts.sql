-- ============================================================================
-- AI FP&A Monthly Close Automation - Maintenance Scripts
-- ============================================================================
-- Version: 1.0.0
-- Created: 2026-02-07
-- Description: Database maintenance, monitoring, and utility scripts
-- ============================================================================

-- ============================================================================
-- MONITORING QUERIES
-- ============================================================================

-- 1. Database Size and Growth
SELECT
    pg_size_pretty(pg_database_size(current_database())) AS total_size,
    (SELECT COUNT(*) FROM portfolio_entities) AS total_entities,
    (SELECT COUNT(*) FROM trial_balances) AS total_trial_balance_records,
    (SELECT COUNT(*) FROM journal_entries) AS total_journal_entries;

-- 2. Table Sizes (with indexes)
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS indexes_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS data_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 20;

-- 3. Index Usage Statistics
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    CASE
        WHEN idx_scan = 0 THEN 'Never used'
        WHEN idx_scan < 100 THEN 'Rarely used'
        WHEN idx_scan < 1000 THEN 'Moderately used'
        ELSE 'Frequently used'
    END AS usage_category
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC
LIMIT 30;

-- 4. Unused Indexes (candidates for removal)
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) AS wasted_space
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND idx_scan = 0
  AND indexrelname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;

-- 5. Partition Information
SELECT
    parent.relname AS parent_table,
    child.relname AS partition_name,
    pg_get_expr(child.relpartbound, child.oid) AS partition_range,
    pg_size_pretty(pg_total_relation_size(child.oid)) AS partition_size
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
WHERE parent.relname IN ('trial_balances', 'agent_actions')
ORDER BY parent.relname, child.relname;

-- 6. Slow Queries (requires pg_stat_statements extension)
-- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
SELECT
    substring(query, 1, 100) AS short_query,
    calls,
    total_exec_time::numeric(10,2) AS total_time_ms,
    mean_exec_time::numeric(10,2) AS avg_time_ms,
    max_exec_time::numeric(10,2) AS max_time_ms,
    rows
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY mean_exec_time DESC
LIMIT 20;

-- 7. Table Bloat Estimation
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    n_live_tup AS live_tuples,
    n_dead_tup AS dead_tuples,
    ROUND(100 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_ratio_pct,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_dead_tup DESC
LIMIT 20;

-- 8. Active Connections
SELECT
    datname,
    usename,
    application_name,
    client_addr,
    state,
    query_start,
    state_change,
    wait_event_type,
    wait_event,
    substring(query, 1, 100) AS current_query
FROM pg_stat_activity
WHERE datname = current_database()
  AND pid != pg_backend_pid()
ORDER BY query_start;

-- 9. Long-Running Transactions
SELECT
    pid,
    usename,
    application_name,
    state,
    NOW() - xact_start AS duration,
    substring(query, 1, 100) AS query
FROM pg_stat_activity
WHERE state != 'idle'
  AND xact_start IS NOT NULL
  AND NOW() - xact_start > interval '5 minutes'
ORDER BY duration DESC;

-- 10. RLS Policy Effectiveness
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd AS command,
    CASE
        WHEN with_check IS NOT NULL THEN 'Insert/Update check enabled'
        WHEN qual IS NOT NULL THEN 'Select/Delete filter enabled'
        ELSE 'Policy exists'
    END AS policy_type
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- ============================================================================
-- DATA QUALITY CHECKS
-- ============================================================================

-- 11. Trial Balance Integrity (debits = credits)
SELECT
    entity_id,
    period_year,
    period_month,
    SUM(debit_amount) AS total_debits,
    SUM(credit_amount) AS total_credits,
    SUM(debit_amount) - SUM(credit_amount) AS variance
FROM trial_balances
GROUP BY entity_id, period_year, period_month
HAVING ABS(SUM(debit_amount) - SUM(credit_amount)) > 0.01
ORDER BY period_year DESC, period_month DESC;

-- 12. Journal Entry Balance Check
SELECT
    je.entry_id,
    je.entry_number,
    je.status,
    SUM(jel.debit_amount) AS total_debits,
    SUM(jel.credit_amount) AS total_credits,
    ABS(SUM(jel.debit_amount) - SUM(jel.credit_amount)) AS imbalance
FROM journal_entries je
JOIN journal_entry_lines jel ON je.entry_id = jel.entry_id
GROUP BY je.entry_id, je.entry_number, je.status
HAVING ABS(SUM(jel.debit_amount) - SUM(jel.credit_amount)) > 0.01
ORDER BY imbalance DESC;

-- 13. Orphaned Records (referential integrity check)
SELECT 'Orphaned trial balances' AS issue, COUNT(*) AS count
FROM trial_balances tb
LEFT JOIN entity_chart_of_accounts eca ON tb.entity_account_id = eca.entity_account_id
WHERE eca.entity_account_id IS NULL

UNION ALL

SELECT 'Orphaned journal lines', COUNT(*)
FROM journal_entry_lines jel
LEFT JOIN journal_entries je ON jel.entry_id = je.entry_id
WHERE je.entry_id IS NULL

UNION ALL

SELECT 'Orphaned user entity access', COUNT(*)
FROM user_entity_access uea
LEFT JOIN users u ON uea.user_id = u.user_id
WHERE u.user_id IS NULL;

-- 14. Missing FX Rates
SELECT DISTINCT
    tb.period_year,
    tb.period_month,
    tb.currency,
    'USD' AS target_currency
FROM trial_balances tb
WHERE tb.currency != 'USD'
  AND NOT EXISTS (
      SELECT 1
      FROM fx_rates_monthly fxm
      WHERE fxm.period_year = tb.period_year
        AND fxm.period_month = tb.period_month
        AND fxm.from_currency = tb.currency
        AND fxm.to_currency = 'USD'
  )
ORDER BY period_year DESC, period_month DESC;

-- 15. Duplicate Entity Codes
SELECT
    entity_code,
    COUNT(*) AS duplicate_count
FROM portfolio_entities
GROUP BY entity_code
HAVING COUNT(*) > 1;

-- 16. Intercompany Reconciliation Issues
SELECT
    period_year,
    period_month,
    COUNT(*) AS total_ic_pairs,
    COUNT(*) FILTER (WHERE ABS(variance) <= 0.01) AS matched,
    COUNT(*) FILTER (WHERE ABS(variance) > 0.01 AND ABS(variance) <= 100) AS minor_variance,
    COUNT(*) FILTER (WHERE ABS(variance) > 100) AS significant_variance,
    COUNT(*) FILTER (WHERE reconciled_at IS NOT NULL) AS reconciled
FROM intercompany_balances
GROUP BY period_year, period_month
ORDER BY period_year DESC, period_month DESC;

-- ============================================================================
-- MAINTENANCE OPERATIONS
-- ============================================================================

-- 17. Vacuum and Analyze (manual trigger)
VACUUM ANALYZE trial_balances;
VACUUM ANALYZE journal_entries;
VACUUM ANALYZE journal_entry_lines;
VACUUM ANALYZE consolidated_balances;
VACUUM ANALYZE etl_batches;

-- 18. Reindex (run during maintenance window)
-- REINDEX TABLE CONCURRENTLY trial_balances;
-- REINDEX TABLE CONCURRENTLY journal_entries;
-- REINDEX TABLE CONCURRENTLY agent_actions;

-- 19. Update Table Statistics
ANALYZE portfolio_entities;
ANALYZE standard_chart_of_accounts;
ANALYZE entity_chart_of_accounts;
ANALYZE trial_balances;
ANALYZE journal_entries;
ANALYZE consolidated_balances;

-- 20. Reset Statistics (for testing)
-- SELECT pg_stat_reset();
-- SELECT pg_stat_reset_shared('bgwriter');

-- ============================================================================
-- BACKUP AND RECOVERY
-- ============================================================================

-- 21. Export Entity Data (backup single entity)
-- Run from command line:
-- pg_dump -d ai_fpna_db -t trial_balances -t journal_entries \
--   --where "entity_id = 'entity-uuid-here'" -f entity_backup.sql

-- 22. Point-in-Time Recovery Setup
-- Ensure WAL archiving is enabled in postgresql.conf:
-- wal_level = replica
-- archive_mode = on
-- archive_command = 'cp %p /path/to/archive/%f'

-- 23. Create Base Backup
-- Run from command line:
-- pg_basebackup -D /path/to/backup -Ft -z -P

-- ============================================================================
-- PARTITION MANAGEMENT
-- ============================================================================

-- 24. Add New Year Partition (run at year-end)
DO $$
DECLARE
    next_year INTEGER := EXTRACT(YEAR FROM CURRENT_DATE) + 1;
BEGIN
    -- Add trial_balances partition
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS trial_balances_%s PARTITION OF trial_balances FOR VALUES FROM (%s) TO (%s)',
        next_year, next_year, next_year + 1
    );

    -- Add agent_actions partition
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS agent_actions_%s PARTITION OF agent_actions FOR VALUES FROM (''%s-01-01'') TO (''%s-01-01'')',
        next_year, next_year, next_year + 1
    );

    RAISE NOTICE 'Created partitions for year %', next_year;
END $$;

-- 25. Archive Old Partition (7-year retention)
DO $$
DECLARE
    archive_year INTEGER := EXTRACT(YEAR FROM CURRENT_DATE) - 7;
    partition_name TEXT;
BEGIN
    partition_name := 'trial_balances_' || archive_year;

    -- First, backup to file (manual step)
    RAISE NOTICE 'Backup % before dropping', partition_name;
    -- Command: pg_dump -t trial_balances_YYYY ai_fpna_db > backup.sql

    -- Then drop partition (uncomment to execute)
    -- EXECUTE format('DROP TABLE IF EXISTS %I', partition_name);

    RAISE NOTICE 'Ready to archive partition: %', partition_name;
END $$;

-- ============================================================================
-- USER MANAGEMENT
-- ============================================================================

-- 26. Create New User with Entity Access
DO $$
DECLARE
    new_user_id UUID;
    entity_uuid UUID;
BEGIN
    -- Insert user
    INSERT INTO users (email, full_name, role, is_active)
    VALUES ('analyst@example.com', 'Jane Analyst', 'analyst', true)
    RETURNING user_id INTO new_user_id;

    -- Grant access to specific entity
    SELECT entity_id INTO entity_uuid
    FROM portfolio_entities
    WHERE entity_code = 'EFFECTI';

    INSERT INTO user_entity_access (user_id, entity_id, can_read, can_write, can_approve)
    VALUES (new_user_id, entity_uuid, true, false, false);

    RAISE NOTICE 'Created user % with access to EFFECTI', new_user_id;
END $$;

-- 27. Audit User Access
SELECT
    u.email,
    u.full_name,
    u.role,
    COUNT(uea.entity_id) AS entities_accessible,
    COUNT(*) FILTER (WHERE uea.can_write) AS write_access_count,
    COUNT(*) FILTER (WHERE uea.can_approve) AS approve_access_count
FROM users u
LEFT JOIN user_entity_access uea ON u.user_id = uea.user_id
WHERE u.is_active = true
GROUP BY u.user_id, u.email, u.full_name, u.role
ORDER BY u.email;

-- ============================================================================
-- SECURITY AUDITING
-- ============================================================================

-- 28. Failed Login Attempts (requires credential_access_log)
SELECT
    user_id,
    COUNT(*) AS failed_attempts,
    MAX(accessed_at) AS last_failed_attempt,
    array_agg(DISTINCT ip_address::TEXT) AS source_ips
FROM credential_access_log
WHERE success = false
  AND accessed_at > NOW() - INTERVAL '24 hours'
GROUP BY user_id
HAVING COUNT(*) >= 3
ORDER BY failed_attempts DESC;

-- 29. Sensitive Data Access Audit
SELECT
    u.email,
    cal.resource_accessed,
    COUNT(*) AS access_count,
    MAX(cal.accessed_at) AS last_access
FROM credential_access_log cal
JOIN users u ON cal.user_id = u.user_id
WHERE cal.accessed_at > NOW() - INTERVAL '7 days'
  AND cal.resource_accessed LIKE '%credential%'
GROUP BY u.email, cal.resource_accessed
ORDER BY access_count DESC;

-- 30. AI Agent Activity Summary
SELECT
    agent_name,
    action_type,
    COUNT(*) AS total_actions,
    COUNT(*) FILTER (WHERE success = true) AS successful,
    COUNT(*) FILTER (WHERE success = false) AS failed,
    ROUND(AVG(execution_time_ms)::numeric, 2) AS avg_execution_ms,
    MAX(created_at) AS last_run
FROM agent_actions
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY agent_name, action_type
ORDER BY agent_name, action_type;

-- ============================================================================
-- PERFORMANCE TUNING
-- ============================================================================

-- 31. Cache Hit Ratio (should be > 99%)
SELECT
    'Index Cache Hit Rate' AS metric,
    ROUND(100.0 * sum(idx_blks_hit) / NULLIF(sum(idx_blks_hit + idx_blks_read), 0), 2) AS hit_rate_pct
FROM pg_statio_user_indexes

UNION ALL

SELECT
    'Table Cache Hit Rate',
    ROUND(100.0 * sum(heap_blks_hit) / NULLIF(sum(heap_blks_hit + heap_blks_read), 0), 2)
FROM pg_statio_user_tables;

-- 32. Most Frequent Queries
SELECT
    substring(query, 1, 100) AS query_preview,
    calls,
    ROUND(total_exec_time::numeric / calls, 2) AS avg_time_ms,
    rows
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat%'
ORDER BY calls DESC
LIMIT 20;

-- 33. Lock Monitoring
SELECT
    l.locktype,
    l.database,
    l.relation::regclass AS relation,
    l.mode,
    l.granted,
    a.usename,
    a.query_start,
    substring(a.query, 1, 100) AS query
FROM pg_locks l
JOIN pg_stat_activity a ON l.pid = a.pid
WHERE l.database = (SELECT oid FROM pg_database WHERE datname = current_database())
ORDER BY l.granted, a.query_start;

-- ============================================================================
-- EMERGENCY PROCEDURES
-- ============================================================================

-- 34. Kill Long-Running Query
-- SELECT pg_cancel_backend(pid);  -- Graceful cancel
-- SELECT pg_terminate_backend(pid);  -- Force terminate

-- 35. Emergency Period Unlock
-- UPDATE period_locks
-- SET lock_status = 'open', unlocked_by = current_user_id(), unlocked_at = NOW(), unlock_reason = 'Emergency unlock'
-- WHERE entity_id = 'entity-uuid' AND period_year = 2024 AND period_month = 12;

-- 36. Disable RLS (emergency access only)
-- ALTER TABLE trial_balances DISABLE ROW LEVEL SECURITY;
-- -- Perform emergency operation
-- ALTER TABLE trial_balances ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- END OF MAINTENANCE SCRIPTS
-- ============================================================================
