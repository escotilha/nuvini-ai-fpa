-- ============================================================================
-- AI FP&A Monthly Close Automation - Row-Level Security Policies
-- ============================================================================
-- Version: 1.0.0
-- Created: 2026-02-07
-- Description: Multi-tenant data isolation using PostgreSQL RLS
-- ============================================================================

-- Enable Row-Level Security on sensitive tables
ALTER TABLE portfolio_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE trial_balances ENABLE ROW LEVEL SECURITY;
ALTER TABLE subledger_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE entity_chart_of_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_entry_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE consolidated_balances ENABLE ROW LEVEL SECURITY;
ALTER TABLE intercompany_balances ENABLE ROW LEVEL SECURITY;
ALTER TABLE etl_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE validation_results ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Get current user's UUID from session
CREATE OR REPLACE FUNCTION current_user_id()
RETURNS UUID AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_user_id', TRUE), '')::UUID;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

COMMENT ON FUNCTION current_user_id() IS 'Returns current user UUID from session variable app.current_user_id';

-- Check if current user has access to entity
CREATE OR REPLACE FUNCTION user_has_entity_access(p_entity_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM user_entity_access uea
        JOIN users u ON uea.user_id = u.user_id
        WHERE u.user_id = current_user_id()
          AND uea.entity_id = p_entity_id
          AND uea.can_read = TRUE
          AND u.is_active = TRUE
    );
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

COMMENT ON FUNCTION user_has_entity_access(UUID) IS 'Check if current user has read access to specified entity';

-- Check if current user can write to entity
CREATE OR REPLACE FUNCTION user_can_write_entity(p_entity_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM user_entity_access uea
        JOIN users u ON uea.user_id = u.user_id
        WHERE u.user_id = current_user_id()
          AND uea.entity_id = p_entity_id
          AND uea.can_write = TRUE
          AND u.is_active = TRUE
    );
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Check if current user is admin
CREATE OR REPLACE FUNCTION user_is_admin()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM users
        WHERE user_id = current_user_id()
          AND role = 'admin'
          AND is_active = TRUE
    );
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Check if current user can approve journals
CREATE OR REPLACE FUNCTION user_can_approve(p_entity_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM user_entity_access uea
        JOIN users u ON uea.user_id = u.user_id
        WHERE u.user_id = current_user_id()
          AND uea.entity_id = p_entity_id
          AND uea.can_approve = TRUE
          AND u.is_active = TRUE
          AND u.role IN ('admin', 'finance_manager', 'controller')
    );
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- ============================================================================
-- RLS POLICIES - PORTFOLIO ENTITIES
-- ============================================================================

-- Admins can see all entities
CREATE POLICY admin_all_entities ON portfolio_entities
    FOR ALL
    TO PUBLIC
    USING (user_is_admin());

-- Users can read entities they have access to
CREATE POLICY user_read_entities ON portfolio_entities
    FOR SELECT
    TO PUBLIC
    USING (user_has_entity_access(entity_id));

-- Only admins can create/update entities
CREATE POLICY admin_write_entities ON portfolio_entities
    FOR INSERT
    TO PUBLIC
    WITH CHECK (user_is_admin());

CREATE POLICY admin_update_entities ON portfolio_entities
    FOR UPDATE
    TO PUBLIC
    USING (user_is_admin())
    WITH CHECK (user_is_admin());

-- ============================================================================
-- RLS POLICIES - TRIAL BALANCES
-- ============================================================================

-- Admins can see all trial balances
CREATE POLICY admin_all_trial_balances ON trial_balances
    FOR ALL
    TO PUBLIC
    USING (user_is_admin());

-- Users can read trial balances for entities they have access to
CREATE POLICY user_read_trial_balances ON trial_balances
    FOR SELECT
    TO PUBLIC
    USING (user_has_entity_access(entity_id));

-- Users with write access can insert trial balances
CREATE POLICY user_insert_trial_balances ON trial_balances
    FOR INSERT
    TO PUBLIC
    WITH CHECK (user_can_write_entity(entity_id));

-- No updates allowed on trial balances (immutable after ETL)
CREATE POLICY no_update_trial_balances ON trial_balances
    FOR UPDATE
    TO PUBLIC
    USING (FALSE);

-- Only admins can delete trial balances
CREATE POLICY admin_delete_trial_balances ON trial_balances
    FOR DELETE
    TO PUBLIC
    USING (user_is_admin());

-- ============================================================================
-- RLS POLICIES - SUBLEDGER ENTRIES
-- ============================================================================

CREATE POLICY admin_all_subledger ON subledger_entries
    FOR ALL
    TO PUBLIC
    USING (user_is_admin());

CREATE POLICY user_read_subledger ON subledger_entries
    FOR SELECT
    TO PUBLIC
    USING (user_has_entity_access(entity_id));

CREATE POLICY user_insert_subledger ON subledger_entries
    FOR INSERT
    TO PUBLIC
    WITH CHECK (user_can_write_entity(entity_id));

-- ============================================================================
-- RLS POLICIES - ENTITY CHART OF ACCOUNTS
-- ============================================================================

CREATE POLICY admin_all_entity_coa ON entity_chart_of_accounts
    FOR ALL
    TO PUBLIC
    USING (user_is_admin());

CREATE POLICY user_read_entity_coa ON entity_chart_of_accounts
    FOR SELECT
    TO PUBLIC
    USING (user_has_entity_access(entity_id));

CREATE POLICY user_write_entity_coa ON entity_chart_of_accounts
    FOR INSERT
    TO PUBLIC
    WITH CHECK (user_can_write_entity(entity_id));

CREATE POLICY user_update_entity_coa ON entity_chart_of_accounts
    FOR UPDATE
    TO PUBLIC
    USING (user_can_write_entity(entity_id))
    WITH CHECK (user_can_write_entity(entity_id));

-- ============================================================================
-- RLS POLICIES - JOURNAL ENTRIES
-- ============================================================================

CREATE POLICY admin_all_journal_entries ON journal_entries
    FOR ALL
    TO PUBLIC
    USING (user_is_admin());

-- Users can read journal entries for their entities
CREATE POLICY user_read_journal_entries ON journal_entries
    FOR SELECT
    TO PUBLIC
    USING (
        entity_id IS NULL  -- Consolidation journals visible to all
        OR user_has_entity_access(entity_id)
    );

-- Users with write access can create draft journals
CREATE POLICY user_insert_journal_entries ON journal_entries
    FOR INSERT
    TO PUBLIC
    WITH CHECK (
        entity_id IS NULL AND user_is_admin()  -- Only admins create consolidation journals
        OR user_can_write_entity(entity_id)
    );

-- Users can update their own draft/pending journals
CREATE POLICY user_update_journal_entries ON journal_entries
    FOR UPDATE
    TO PUBLIC
    USING (
        user_can_write_entity(entity_id)
        AND status IN ('draft', 'pending_review')
    )
    WITH CHECK (
        user_can_write_entity(entity_id)
        AND status IN ('draft', 'pending_review', 'approved')
    );

-- Only approvers can delete journals
CREATE POLICY approver_delete_journal_entries ON journal_entries
    FOR DELETE
    TO PUBLIC
    USING (
        user_can_approve(entity_id)
        AND status = 'draft'
    );

-- ============================================================================
-- RLS POLICIES - JOURNAL ENTRY LINES
-- ============================================================================

CREATE POLICY admin_all_journal_lines ON journal_entry_lines
    FOR ALL
    TO PUBLIC
    USING (user_is_admin());

-- Users can read lines for journals they can access
CREATE POLICY user_read_journal_lines ON journal_entry_lines
    FOR SELECT
    TO PUBLIC
    USING (
        EXISTS (
            SELECT 1 FROM journal_entries je
            WHERE je.entry_id = journal_entry_lines.entry_id
              AND (je.entity_id IS NULL OR user_has_entity_access(je.entity_id))
        )
    );

-- Users can insert lines for journals they can write
CREATE POLICY user_insert_journal_lines ON journal_entry_lines
    FOR INSERT
    TO PUBLIC
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM journal_entries je
            WHERE je.entry_id = journal_entry_lines.entry_id
              AND user_can_write_entity(je.entity_id)
              AND je.status IN ('draft', 'pending_review')
        )
    );

-- Users can update lines for draft journals
CREATE POLICY user_update_journal_lines ON journal_entry_lines
    FOR UPDATE
    TO PUBLIC
    USING (
        EXISTS (
            SELECT 1 FROM journal_entries je
            WHERE je.entry_id = journal_entry_lines.entry_id
              AND user_can_write_entity(je.entity_id)
              AND je.status IN ('draft', 'pending_review')
        )
    );

-- Users can delete lines from draft journals
CREATE POLICY user_delete_journal_lines ON journal_entry_lines
    FOR DELETE
    TO PUBLIC
    USING (
        EXISTS (
            SELECT 1 FROM journal_entries je
            WHERE je.entry_id = journal_entry_lines.entry_id
              AND user_can_write_entity(je.entity_id)
              AND je.status = 'draft'
        )
    );

-- ============================================================================
-- RLS POLICIES - CONSOLIDATED BALANCES
-- ============================================================================

CREATE POLICY admin_all_consolidated ON consolidated_balances
    FOR ALL
    TO PUBLIC
    USING (user_is_admin());

-- Users can read consolidated balances for entities they have access to
CREATE POLICY user_read_consolidated ON consolidated_balances
    FOR SELECT
    TO PUBLIC
    USING (
        entity_id IS NULL  -- Group-level consolidation visible to all authenticated users
        OR user_has_entity_access(entity_id)
    );

-- Only admins and system can write consolidated balances
CREATE POLICY admin_write_consolidated ON consolidated_balances
    FOR INSERT
    TO PUBLIC
    WITH CHECK (user_is_admin());

-- ============================================================================
-- RLS POLICIES - INTERCOMPANY BALANCES
-- ============================================================================

CREATE POLICY admin_all_intercompany ON intercompany_balances
    FOR ALL
    TO PUBLIC
    USING (user_is_admin());

-- Users can read IC balances if they have access to either entity
CREATE POLICY user_read_intercompany ON intercompany_balances
    FOR SELECT
    TO PUBLIC
    USING (
        user_has_entity_access(entity_from_id)
        OR user_has_entity_access(entity_to_id)
    );

-- Only admins can write intercompany balances
CREATE POLICY admin_write_intercompany ON intercompany_balances
    FOR INSERT
    TO PUBLIC
    WITH CHECK (user_is_admin());

-- ============================================================================
-- RLS POLICIES - ETL BATCHES
-- ============================================================================

CREATE POLICY admin_all_etl_batches ON etl_batches
    FOR ALL
    TO PUBLIC
    USING (user_is_admin());

CREATE POLICY user_read_etl_batches ON etl_batches
    FOR SELECT
    TO PUBLIC
    USING (user_has_entity_access(entity_id));

CREATE POLICY user_insert_etl_batches ON etl_batches
    FOR INSERT
    TO PUBLIC
    WITH CHECK (user_can_write_entity(entity_id));

-- ============================================================================
-- RLS POLICIES - VALIDATION RESULTS
-- ============================================================================

CREATE POLICY admin_all_validations ON validation_results
    FOR ALL
    TO PUBLIC
    USING (user_is_admin());

CREATE POLICY user_read_validations ON validation_results
    FOR SELECT
    TO PUBLIC
    USING (
        entity_id IS NULL  -- Global validations visible to all
        OR user_has_entity_access(entity_id)
    );

CREATE POLICY user_write_validations ON validation_results
    FOR INSERT
    TO PUBLIC
    WITH CHECK (
        entity_id IS NULL AND user_is_admin()
        OR user_can_write_entity(entity_id)
    );

-- ============================================================================
-- RLS BYPASS FOR SERVICE ACCOUNTS
-- ============================================================================

-- Create a bypass role for automated processes and AI agents
-- Grant this role to service accounts that need full access
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rls_bypass') THEN
        CREATE ROLE rls_bypass;
    END IF;
END
$$;

COMMENT ON ROLE rls_bypass IS 'Service accounts with this role bypass RLS policies for ETL and automation';

-- Admins and service accounts bypass RLS
CREATE POLICY bypass_rls_for_admins ON portfolio_entities
    FOR ALL
    TO rls_bypass
    USING (TRUE)
    WITH CHECK (TRUE);

-- Apply bypass to all RLS-enabled tables
DO $$
DECLARE
    tbl_name TEXT;
BEGIN
    FOR tbl_name IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename IN (
              'trial_balances', 'subledger_entries', 'entity_chart_of_accounts',
              'journal_entries', 'journal_entry_lines', 'consolidated_balances',
              'intercompany_balances', 'etl_batches', 'validation_results'
          )
    LOOP
        EXECUTE format('CREATE POLICY bypass_rls_for_service_%I ON %I FOR ALL TO rls_bypass USING (TRUE) WITH CHECK (TRUE)', tbl_name, tbl_name);
    END LOOP;
END
$$;

-- ============================================================================
-- AUDIT TRIGGER FOR RLS POLICY VIOLATIONS
-- ============================================================================

-- Log when RLS policies block access (for security monitoring)
CREATE TABLE rls_violation_log (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,
    table_name VARCHAR(100) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    entity_id UUID,
    ip_address INET,
    session_id TEXT,
    blocked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rls_violations_user ON rls_violation_log(user_id, blocked_at DESC);
CREATE INDEX idx_rls_violations_table ON rls_violation_log(table_name, blocked_at DESC);

COMMENT ON TABLE rls_violation_log IS 'Audit log for RLS policy violations and unauthorized access attempts';

-- ============================================================================
-- SESSION CONFIGURATION HELPER
-- ============================================================================

-- Function to set current user in session (call at connection start)
CREATE OR REPLACE FUNCTION set_current_user(p_user_id UUID)
RETURNS VOID AS $$
BEGIN
    PERFORM set_config('app.current_user_id', p_user_id::TEXT, FALSE);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION set_current_user(UUID) IS 'Set current user ID in session for RLS policies. Call at connection start.';

-- Example usage in application:
-- SELECT set_current_user('user-uuid-here');

-- ============================================================================
-- RLS TESTING HELPERS
-- ============================================================================

-- View current RLS context
CREATE OR REPLACE FUNCTION current_rls_context()
RETURNS TABLE (
    current_user_id UUID,
    is_admin BOOLEAN,
    accessible_entities UUID[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        current_user_id(),
        user_is_admin(),
        ARRAY(
            SELECT entity_id
            FROM user_entity_access uea
            WHERE uea.user_id = current_user_id()
              AND uea.can_read = TRUE
        );
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION current_rls_context() IS 'Show current RLS context for debugging: user, admin status, accessible entities';

-- ============================================================================
-- GRANTS
-- ============================================================================

-- Grant execute on RLS helper functions to all authenticated users
GRANT EXECUTE ON FUNCTION current_user_id() TO PUBLIC;
GRANT EXECUTE ON FUNCTION user_has_entity_access(UUID) TO PUBLIC;
GRANT EXECUTE ON FUNCTION user_can_write_entity(UUID) TO PUBLIC;
GRANT EXECUTE ON FUNCTION user_is_admin() TO PUBLIC;
GRANT EXECUTE ON FUNCTION user_can_approve(UUID) TO PUBLIC;
GRANT EXECUTE ON FUNCTION set_current_user(UUID) TO PUBLIC;
GRANT EXECUTE ON FUNCTION current_rls_context() TO PUBLIC;

-- ============================================================================
-- RLS POLICY VERIFICATION
-- ============================================================================

-- View to audit all RLS policies
CREATE VIEW v_rls_policies AS
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

COMMENT ON VIEW v_rls_policies IS 'Audit view showing all RLS policies configured in the database';
