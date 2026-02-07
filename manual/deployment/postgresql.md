# PostgreSQL Database Setup

## Initialize Database

```bash
createdb fpa_db
psql fpa_db -f database/migrations/001_initial_schema.sql
psql fpa_db -f database/migrations/002_rls_policies.sql
psql fpa_db -f database/migrations/003_indexes.sql
psql fpa_db -f database/seeds/001_portfolio_entities.sql
psql fpa_db -f database/seeds/002_standard_coa.sql
```

## Performance Tuning

See database/README.md for complete tuning guide.

Key settings:
- shared_buffers = 8GB
- work_mem = 256MB
- effective_cache_size = 24GB
