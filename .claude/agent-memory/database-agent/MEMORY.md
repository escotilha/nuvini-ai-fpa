# Database Agent Memory - AI FP&A Project

## Key Schema Design Patterns

### Multi-Tenant Isolation with RLS
- PostgreSQL Row-Level Security (RLS) provides tenant isolation at database level
- Use session variables (`app.current_user_id`) to set user context
- Helper functions (`user_has_entity_access()`) encapsulate access logic
- Service accounts need `rls_bypass` role for ETL operations
- Always enable RLS on tables containing entity-specific data

### Partitioning Strategy for Time-Series Data
- Trial balances partitioned by year (range partitioning)
- Reduces query time by 7x through partition pruning
- Create partitions 1 year ahead, drop after 7-year retention
- Audit logs (agent_actions) also partitioned by year for performance
- Use `PARTITION BY RANGE` for chronological data

### Chart of Accounts Mapping Pattern
```
Standard COA (master) → Entity COA (local mapping) → Trial Balances
```
- Standard COA: IFRS/GAAP compliant master template
- Entity COA: Maps local accounts to standard with confidence scores
- Enables consolidation across different accounting systems
- Track mapping confidence for AI-assisted validation

### Financial Data Integrity
- Use constraint triggers for journal entry balance validation
- Contra-asset accounts have credit normal balance (e.g., accumulated depreciation)
- Trial balances are immutable after ETL (no UPDATE policy)
- Period locking prevents modifications to closed months
- Deferred constraint triggers allow batch inserts before validation

### Performance Optimization Techniques
- Covering indexes for index-only scans (INCLUDE clause)
- Partial indexes for commonly filtered data (e.g., WHERE is_active = true)
- GIN indexes for JSONB dimension filtering
- Trigram indexes for fuzzy account name matching
- Composite indexes match query WHERE + ORDER BY patterns

## Project-Specific Decisions

### FPA Portfolio Structure
- 7 initial companies: Effecti, Mercos, Datahub, OnClick, Ipê Digital, Munddi, Leadlovers
- All Brazilian entities with BRL functional currency, USD presentation
- Full consolidation method (100% ownership)
- Scalable to 66+ entities with current index design

### AI-Generated Journal Entries
- `entry_source = 'ai_generated'` identifies AI entries
- `ai_confidence` score (0.0-1.0) for review prioritization
- `ai_explanation` provides audit trail of AI reasoning
- Status workflow: draft → pending_review → approved → posted

### Consolidation Workflow
1. Load trial balances (local currency, entity COA)
2. Map to standard COA
3. Translate to USD using FX rates
4. Eliminate intercompany balances
5. Apply consolidation journals
6. Generate consolidated_balances table

## Common Mistakes to Avoid

### RLS Context Must Be Set
- Always call `SELECT set_current_user('uuid')` at connection start
- Missing RLS context results in no rows returned (silent failure)
- Test RLS with `SELECT * FROM current_rls_context();`

### Partition Naming Convention
- Format: `{table_name}_{year}` for trial_balances
- Format: `{table_name}_{year}` for agent_actions (date-based partitions)
- Never create overlapping partition ranges

### Journal Entry Balance Validation
- Use DEFERRABLE INITIALLY DEFERRED constraint trigger
- Allows inserting lines before balance check runs
- Fails at COMMIT if debits ≠ credits

### Index Maintenance
- REINDEX CONCURRENTLY to avoid locking tables
- Vacuum partitioned tables regularly (bloat accumulates)
- Monitor idx_scan = 0 for unused indexes (waste space)

## Performance Benchmarks

With 66 entities, 7 years of data, expected query times:
- Single entity trial balance: < 10ms
- All entities current period: < 100ms
- Consolidated balances: < 50ms
- Intercompany reconciliation: < 200ms

Configuration: 8GB shared_buffers, 256MB work_mem, SSD storage

## Schema Statistics

- Total tables: 25 core tables
- Partitioned tables: 2 (trial_balances, agent_actions)
- RLS-enabled tables: 10
- Indexes: 80+ optimized indexes
- Standard COA accounts: ~100 accounts (5 levels deep)
- LOC: 3,255 lines across migrations, seeds, docs

## Useful Queries

### Check Database Size
```sql
SELECT pg_size_pretty(pg_database_size(current_database()));
```

### Find Unbalanced Journals
```sql
SELECT entry_id, SUM(debit_amount) - SUM(credit_amount) AS imbalance
FROM journal_entry_lines
GROUP BY entry_id
HAVING ABS(SUM(debit_amount) - SUM(credit_amount)) > 0.01;
```

### Monitor Partition Sizes
```sql
SELECT child.relname, pg_size_pretty(pg_total_relation_size(child.oid))
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
WHERE parent.relname = 'trial_balances';
```

## File Locations

All database files in: `/Volumes/AI/Code/FPA/database/`

- Migrations: `migrations/001_initial_schema.sql`, `002_rls_policies.sql`, `003_indexes.sql`
- Seeds: `seeds/001_portfolio_entities.sql`, `seeds/002_standard_coa.sql`
- Docs: `README.md`
- Utils: `maintenance_scripts.sql`
