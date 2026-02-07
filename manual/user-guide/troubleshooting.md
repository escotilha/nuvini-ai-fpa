# Troubleshooting Guide

## Overview

This guide provides solutions to common issues encountered during monthly close operations. Issues are organized by system component and include diagnostic steps, solutions, and prevention strategies.

## Quick Diagnostic Commands

Before diving into specific issues, run these diagnostic commands:

```bash
# System health check
python -m src.cli.health_check --full

# Period status
python -m src.cli.status --period "2026-01-31"

# Validation report
python -m src.reporting.validation_report \
  --period "2026-01-31"

# View recent errors
tail -f logs/fpa_system.log | grep ERROR
```

## Data Extraction Issues

### Issue 1: ERP Connector Timeout

**Symptoms:**
- `httpx.ConnectTimeout` exception
- Connection hangs for 60+ seconds
- "Failed to connect to ERP" error

**Diagnostic:**

```bash
# Test network connectivity
curl -I https://api.totvs.com.br

# Check connector health
python -m src.connectors.health_check \
  --erp totvs_protheus \
  --company effecti

# View connector logs
tail -f logs/data_ingestion.log
```

**Solutions:**

1. **Increase timeout:**
   ```bash
   python -m src.connectors.extract \
     --company effecti \
     --timeout 300 \
     --retry 5
   ```

2. **Check ERP status:**
   - TOTVS: https://status.totvs.com.br
   - ContaAzul: https://status.contaazul.com
   - Check if maintenance window

3. **Retry with backoff:**
   ```bash
   python -m src.connectors.retry \
     --company effecti \
     --max-attempts 10 \
     --backoff exponential
   ```

4. **Manual extraction (last resort):**
   ```bash
   # Export from ERP manually and import
   python -m src.cli.import_trial_balance \
     --company effecti \
     --file effecti_tb_jan2026.csv \
     --period "2026-01-31"
   ```

**Prevention:**
- Schedule extractions during off-peak hours (e.g., 2 AM local time)
- Monitor ERP status pages for planned maintenance
- Increase default timeout in production config

---

### Issue 2: Rate Limit Exceeded

**Symptoms:**
- `429 Too Many Requests` HTTP error
- `503 Service Temporarily Unavailable`
- Extraction fails midway through

**Diagnostic:**

```bash
# Check rate limit status
python -m src.connectors.rate_limit_status \
  --erp contaazul

# View request count
python -m src.connectors.request_stats \
  --company mercos \
  --period "2026-01-31"
```

**Solutions:**

1. **Wait and retry:**
   ```bash
   # Wait 60 seconds, then retry
   sleep 60
   python -m src.connectors.retry --company mercos
   ```

2. **Use date-based chunking:**
   ```bash
   # Extract in smaller date ranges
   python -m src.connectors.extract \
     --company mercos \
     --period-start "2026-01-01" \
     --period-end "2026-01-15" \
     --chunk-days 7
   ```

3. **Schedule extraction over time:**
   ```bash
   # Extract one company per hour
   python -m src.orchestrator.schedule_extraction \
     --stagger 60  # minutes between companies
   ```

**Prevention:**
- Know your ERP rate limits (TOTVS: 100/min, ContaAzul: 60/min, Omie: 300/min)
- Use built-in rate limiter (automatic)
- Schedule extractions to avoid overlapping with other systems

---

### Issue 3: Authentication Failure

**Symptoms:**
- `401 Unauthorized` error
- "Invalid credentials" message
- OAuth token expired

**Diagnostic:**

```bash
# Verify credentials
python -m src.connectors.test_auth \
  --erp totvs_protheus \
  --company effecti

# Check token expiration
python -m src.connectors.token_info \
  --company effecti
```

**Solutions:**

1. **Refresh OAuth token:**
   ```bash
   python -m src.connectors.refresh_token \
     --erp totvs_protheus \
     --company effecti
   ```

2. **Verify credentials in .env:**
   ```bash
   cat .env | grep TOTVS_EFFECTI
   ```

3. **Re-authorize application:**
   - Log into ERP admin console
   - Revoke old token
   - Generate new token
   - Update `.env` file
   - Restart extraction

4. **Check API key permissions:**
   ```bash
   # Test API key has required permissions
   python -m src.connectors.test_permissions \
     --erp omie \
     --company datahub
   ```

**Prevention:**
- Use long-lived OAuth refresh tokens
- Set up token expiration alerts
- Document credential rotation process
- Store credentials in AWS Secrets Manager (production)

---

### Issue 4: Data Quality Errors

**Symptoms:**
- Trial balance doesn't balance
- Missing account codes
- Duplicate transactions
- Negative balances in unexpected accounts

**Diagnostic:**

```bash
# Run data quality report
python -m src.validation.data_quality \
  --company effecti \
  --period "2026-01-31"

# Check specific issues
python -m src.validation.check_balance \
  --company effecti

python -m src.validation.find_duplicates \
  --company effecti
```

**Solutions:**

1. **Balance sheet doesn't balance:**
   ```bash
   # Check for missing accounts
   python -m src.validation.missing_accounts \
     --company effecti

   # Review ERP extraction log
   tail -f logs/data_ingestion.log | grep effecti
   ```

   **Fix:** Re-extract from ERP or create manual adjustment

2. **Duplicate transactions:**
   ```bash
   # Find duplicates
   python -m src.validation.find_duplicates \
     --company effecti \
     --threshold 0.99  # 99% similarity

   # Remove duplicates
   python -m src.cli.remove_duplicates \
     --company effecti \
     --dry-run  # Preview first
   ```

3. **Missing account codes:**
   ```bash
   # Map missing accounts
   python -m src.cli.map_accounts \
     --company mercos \
     --category "Salários" \
     --account-code "5.01.001"
   ```

4. **Negative cash balance:**
   ```bash
   # Investigate transactions
   python -m src.reporting.account_detail \
     --company effecti \
     --account "1.01.001" \
     --period "2026-01-31"
   ```

   **Common causes:**
   - Timing difference (deposits not yet cleared)
   - Overdraft facility
   - ERP data error

**Prevention:**
- Enable validation during extraction
- Set up data quality alerts
- Review ERP data integrity monthly
- Train ERP users on proper data entry

---

## Consolidation Issues

### Issue 5: Balance Sheet Doesn't Balance

**Symptoms:**
- Validation error: "Assets ≠ Liabilities + Equity"
- Difference is material (>$0.01)

**Diagnostic:**

```bash
# Run balance sheet diagnostic
python -m src.consolidation.diagnose \
  --period "2026-01-31" \
  --issue balance_sheet

# Check component balances
python -m src.cli.component_balances \
  --period "2026-01-31"
```

**Solutions:**

1. **Check if all entities extracted:**
   ```bash
   python -m src.cli.extraction_status \
     --period "2026-01-31"
   ```

   **Fix:** Re-extract missing entities

2. **Verify FX conversion:**
   ```bash
   python -m src.consolidation.verify_fx \
     --period "2026-01-31"
   ```

   **Fix:** Reload FX rates and re-run conversion

3. **Review elimination entries:**
   ```bash
   python -m src.cli.consolidation_journal \
     --period "2026-01-31" \
     --type eliminations
   ```

   **Fix:** Correct elimination entries with errors

4. **Check PPA entries:**
   ```bash
   python -m src.ppa.verify \
     --period "2026-01-31"
   ```

   **Fix:** Re-run PPA amortization

5. **Trace the imbalance:**
   ```bash
   # Calculate difference
   python -m src.consolidation.trace_imbalance \
     --period "2026-01-31"
   ```

   **Example output:**
   ```
   Balance Sheet Imbalance: USD 12,500

   Tracing source:
   ✓ Entity extractions: All balanced
   ✓ FX conversion: All balanced
   ✓ Eliminations: All balanced
   ✗ PPA entries: Imbalance found

   Issue: Leadlovers PPA amortization missing
   Amortization expected: USD 79,167
   Amortization recorded: USD 66,667
   Difference: USD 12,500 ← Source of imbalance

   Fix: Re-run PPA amortization for Leadlovers
   ```

**Prevention:**
- Run validation after each consolidation step
- Set up balance checks as blocking controls
- Archive balanced trial balances before modifications

---

### Issue 6: Large Unmatched Intercompany Transactions

**Symptoms:**
- Many IC transactions not eliminated
- Material unmatched IC amounts (>USD 100k)
- Warning in validation report

**Diagnostic:**

```bash
# View unmatched IC items
python -m src.cli.unmatched_ic \
  --period "2026-01-31" \
  --minimum-amount 10000

# IC reconciliation report
python -m src.reporting.ic_reconciliation \
  --period "2026-01-31"
```

**Solutions:**

1. **Increase FX tolerance:**
   ```bash
   # Default is 1%, try 2%
   python -m src.consolidation.eliminate \
     --period "2026-01-31" \
     --tolerance 0.02
   ```

2. **Check reference number matching:**
   ```bash
   # View IC items by reference
   python -m src.cli.ic_by_reference \
     --period "2026-01-31"
   ```

   **Common issues:**
   - Different invoice formats (INV-001 vs. INV001)
   - Missing reference numbers
   - Typos in reference numbers

3. **Manual matching:**
   ```bash
   # Manually match two IC items
   python -m src.cli.match_ic \
     --item1 "IC-RECV-001" \
     --item2 "IC-PAY-001" \
     --create-elimination
   ```

4. **Timing differences:**
   - One entity recorded in Jan, other in Feb
   - Accrual basis vs. cash basis

   **Fix:** Accept as unmatched, will reconcile next period

5. **Create manual elimination:**
   ```bash
   python -m src.journal.create_entry \
     --type ic_elimination \
     --debit "2.02.003:18500" \
     --credit "1.02.005:18500" \
     --memo "Manual IC elimination - timing difference"
   ```

**Prevention:**
- Standardize IC invoice numbering across entities
- Document IC transactions in shared ledger
- Set up monthly IC reconciliation process
- Use tighter FX tolerance for large transactions

---

### Issue 7: Incorrect CTA Calculation

**Symptoms:**
- CTA amount significantly different from expected
- Large unexpected FX gain/loss
- CTA variance vs. prior period

**Diagnostic:**

```bash
# CTA reconciliation
python -m src.fx.cta_reconciliation \
  --period "2026-01-31"

# Compare to prior period
python -m src.fx.cta_variance \
  --current "2026-01-31" \
  --prior "2025-12-31"
```

**Solutions:**

1. **Verify historical rates:**
   ```bash
   # Check if historical rates loaded
   python -m src.fx.list_rates \
     --type historical \
     --from "2023-08-01" \
     --to "2026-01-31"
   ```

   **Fix:** Load missing historical rates

2. **Check retained earnings:**
   ```bash
   # Verify retained earnings balance
   python -m src.cli.account_detail \
     --account "3.05.001" \
     --period "2026-01-31"
   ```

   **Fix:** Correct retained earnings if incorrect

3. **Review prior period CTA:**
   ```bash
   # Compare CTA trend
   python -m src.fx.cta_trend \
     --from "2025-01-01" \
     --to "2026-01-31"
   ```

4. **Recalculate CTA:**
   ```bash
   # Force CTA recalculation
   python -m src.consolidation.recalculate_cta \
     --period "2026-01-31" \
     --verify
   ```

**Prevention:**
- Document historical rates for all acquisitions
- Archive CTA calculations monthly
- Review CTA variance analysis quarterly

---

### Issue 8: Missing FX Rates

**Symptoms:**
- "FX rate not found" error
- Consolidation fails at FX conversion step

**Diagnostic:**

```bash
# Check available FX rates
python -m src.fx.list_rates \
  --period "2026-01-31"

# Check missing rates
python -m src.fx.missing_rates \
  --period "2026-01-31"
```

**Solutions:**

1. **Load FX rates automatically:**
   ```bash
   # Load from BCB PTAX
   python -m src.fx.load_rates \
     --source bcb_ptax \
     --date "2026-01-31" \
     --rate-type closing

   python -m src.fx.load_rates \
     --source bcb_ptax \
     --period "2026-01-01:2026-01-31" \
     --rate-type average
   ```

2. **Add FX rates manually:**
   ```bash
   # Add closing rate
   python -m src.fx.add_rate \
     --from BRL \
     --to USD \
     --date "2026-01-31" \
     --type closing \
     --rate 0.1895 \
     --source "BCB PTAX"

   # Add average rate
   python -m src.fx.add_rate \
     --from BRL \
     --to USD \
     --date "2026-01-31" \
     --type average \
     --rate 0.1872 \
     --source "BCB PTAX Jan 2026 Avg"
   ```

3. **Use sample rates (testing only):**
   ```bash
   python -m src.fx.create_sample_rates \
     --date "2026-01-31"
   ```

**Prevention:**
- Automate FX rate loading (daily job)
- Set up FX rate alerts when rates not available
- Document FX rate sources

---

## Human Review Issues

### Issue 9: Too Many Reviews Pending

**Symptoms:**
- Review queue has 500+ pending items
- Reviews not completed within SLA
- Bottleneck in review workflow

**Diagnostic:**

```bash
# Check review workload
python -m src.cli.review_workload \
  --period "2026-01-31"

# Reviewer statistics
python -m src.cli.reviewer_stats \
  --period "2026-01-31"
```

**Solutions:**

1. **Adjust confidence thresholds:**
   ```python
   # Reduce review volume by 20-30%
   python -m src.oversight.adjust_thresholds \
     --green-threshold 0.85 \
     --yellow-threshold 0.55
   ```

2. **Reduce sampling rate:**
   ```bash
   # Sample 2% instead of 5%
   python -m src.oversight.set_sampling_rate \
     --green-rate 0.02
   ```

3. **Delegate reviews:**
   ```bash
   # Reassign to additional reviewers
   python -m src.cli.reassign_reviews \
     --from "john_analyst" \
     --to "mary_analyst" \
     --count 100
   ```

4. **Batch approve low-risk items:**
   ```bash
   # Batch approve green samples
   python -m src.cli.batch_approve \
     --risk-level green \
     --confidence-min 0.90 \
     --max-count 50 \
     --reviewer "john_analyst"
   ```

**Prevention:**
- Monitor review queue daily during close
- Adjust thresholds based on review capacity
- Train additional reviewers

---

### Issue 10: High Rejection Rate

**Symptoms:**
- >10% of reviewed transactions rejected
- Frequent AI misclassifications
- Low approval rate

**Diagnostic:**

```bash
# Rejection analysis
python -m src.reporting.rejection_analysis \
  --period "2026-01-31"

# Common rejection reasons
python -m src.cli.rejection_reasons \
  --period "2026-01-31" \
  --top 10
```

**Solutions:**

1. **Analyze rejection patterns:**
   ```bash
   python -m src.analysis.rejection_patterns \
     --period "2026-01-31"
   ```

   **Example output:**
   ```
   Top Rejection Reasons:
   1. Wrong account code (35%)
   2. Should be capitalized (22%)
   3. Duplicate transaction (18%)
   4. Wrong amount (15%)
   5. Missing supporting docs (10%)
   ```

2. **Improve validation rules:**
   ```bash
   # Add validation for common errors
   python -m src.validation.add_rule \
     --name "check_capitalization" \
     --condition "amount > 50000 and account in ['5.01.*']" \
     --action "flag_for_review" \
     --message "Large R&D expense, check if should be capitalized"
   ```

3. **Retrain AI model:**
   ```bash
   # Flag rejected transactions for training
   python -m src.ml.retrain \
     --period "2026-01-31" \
     --include-rejections
   ```

4. **Update confidence scoring:**
   ```python
   # Adjust weights based on rejection analysis
   python -m src.oversight.adjust_weights \
     --materiality 0.35 \
     --complexity 0.20 \
     --data-quality 0.20 \
     --pattern-deviation 0.15 \
     --variance 0.10
   ```

**Prevention:**
- Review rejection patterns monthly
- Continuously improve AI model
- Document common errors in training data
- Add validation rules for frequent errors

---

## Reporting Issues

### Issue 11: Report Generation Fails

**Symptoms:**
- Report command returns error
- Excel file corrupted
- Missing data in report

**Diagnostic:**

```bash
# Check if period closed
python -m src.cli.status --period "2026-01-31"

# Verify data completeness
python -m src.reporting.validation_report \
  --period "2026-01-31"

# Check report logs
tail -f logs/reporting.log
```

**Solutions:**

1. **Ensure period is closed:**
   ```bash
   # Close period first
   python -m src.orchestrator.close_period \
     --period "2026-01-31" \
     --approver "cfo_pierre" \
     --action approve
   ```

2. **Verify consolidation complete:**
   ```bash
   python -m src.cli.consolidation_status \
     --period "2026-01-31"
   ```

3. **Regenerate report:**
   ```bash
   # Force regeneration
   python -m src.reporting.board_package \
     --period "2026-01-31" \
     --force \
     --output board_package_jan2026.pdf
   ```

4. **Try alternative format:**
   ```bash
   # If Excel fails, try CSV
   python -m src.reporting.trial_balance \
     --period "2026-01-31" \
     --format csv
   ```

5. **Check template version:**
   ```bash
   # Update report templates
   python -m src.reporting.update_templates
   ```

**Prevention:**
- Always close period before generating reports
- Keep report templates up to date
- Test reports on non-production data first

---

## Performance Issues

### Issue 12: Slow Consolidation

**Symptoms:**
- Consolidation takes >30 minutes
- System appears hung
- High CPU/memory usage

**Diagnostic:**

```bash
# Check system resources
top -p $(pgrep -f "python.*consolidation")

# Profile consolidation
python -m src.consolidation.run \
  --period "2026-01-31" \
  --profile

# Check database performance
python -m src.cli.db_stats
```

**Solutions:**

1. **Optimize database queries:**
   ```bash
   # Analyze slow queries
   python -m src.cli.slow_queries \
     --threshold 1000  # >1s

   # Update indexes
   python -m src.database.optimize_indexes
   ```

2. **Increase parallelization:**
   ```bash
   # Use more workers
   python -m src.consolidation.run \
     --period "2026-01-31" \
     --workers 8  # Default: 4
   ```

3. **Batch processing:**
   ```bash
   # Process entities in batches
   python -m src.consolidation.run \
     --period "2026-01-31" \
     --batch-size 2  # 2 entities at a time
   ```

4. **Check data volume:**
   ```bash
   # Count entries per entity
   python -m src.cli.entry_count \
     --period "2026-01-31"
   ```

   If one entity has unusually high entry count, investigate source

**Prevention:**
- Monitor consolidation performance monthly
- Optimize database indexes quarterly
- Archive old data (>7 years)

---

## Database Issues

### Issue 13: Database Connection Errors

**Symptoms:**
- "Connection refused" error
- "Too many connections" error
- Database timeout

**Diagnostic:**

```bash
# Test database connection
psql -h localhost -U fpa_user -d fpa_prod -c "SELECT 1"

# Check connection pool
python -m src.cli.db_connections

# Check database logs
tail -f /var/log/postgresql/postgresql.log
```

**Solutions:**

1. **Verify PostgreSQL is running:**
   ```bash
   sudo systemctl status postgresql

   # If not running
   sudo systemctl start postgresql
   ```

2. **Check connection string:**
   ```bash
   # Verify DATABASE_URL in .env
   echo $DATABASE_URL
   ```

3. **Increase connection pool:**
   ```python
   # In config
   DATABASE_POOL_SIZE = 20  # Increase from 10
   DATABASE_MAX_OVERFLOW = 40  # Increase from 20
   ```

4. **Close idle connections:**
   ```bash
   # Kill idle connections
   python -m src.cli.close_idle_connections \
     --idle-time 300  # >5 minutes
   ```

**Prevention:**
- Monitor connection pool usage
- Set connection timeout limits
- Use connection pooling (pgBouncer)

---

### Issue 14: Database Locks

**Symptoms:**
- Query hangs indefinitely
- "Deadlock detected" error
- Multiple processes waiting

**Diagnostic:**

```bash
# Check for locks
psql -d fpa_prod -c "
  SELECT pid, usename, pg_blocking_pids(pid), query
  FROM pg_stat_activity
  WHERE pg_blocking_pids(pid)::text != '{}'
"

# View long-running queries
python -m src.cli.long_running_queries \
  --threshold 60  # >60 seconds
```

**Solutions:**

1. **Kill blocking query:**
   ```bash
   # Get PID from diagnostic above
   psql -d fpa_prod -c "SELECT pg_terminate_backend(12345)"
   ```

2. **Reduce transaction scope:**
   - Break large transactions into smaller chunks
   - Commit more frequently

3. **Use advisory locks:**
   ```python
   # Prevent concurrent consolidations
   python -m src.consolidation.run \
     --period "2026-01-31" \
     --use-advisory-lock
   ```

**Prevention:**
- Keep transactions small and fast
- Use advisory locks for long operations
- Monitor for deadlocks

---

## System-Wide Issues

### Issue 15: Out of Memory

**Symptoms:**
- `MemoryError` exception
- System becomes unresponsive
- OOM killer terminates process

**Diagnostic:**

```bash
# Check memory usage
free -h

# Check Python process memory
ps aux | grep python | sort -k4 -r

# Memory profiling
python -m memory_profiler src/consolidation/consolidator.py
```

**Solutions:**

1. **Increase system memory:**
   - Upgrade server RAM
   - Use larger EC2 instance

2. **Process in chunks:**
   ```bash
   # Process entities one at a time
   python -m src.consolidation.run \
     --period "2026-01-31" \
     --entities "effecti" \
     --output effecti_consolidated.xlsx

   python -m src.consolidation.run \
     --period "2026-01-31" \
     --entities "mercos" \
     --output mercos_consolidated.xlsx

   # Merge results
   python -m src.consolidation.merge \
     --files "effecti_consolidated.xlsx,mercos_consolidated.xlsx" \
     --output final_consolidated.xlsx
   ```

3. **Optimize memory usage:**
   ```python
   # Use generators instead of lists
   # Process data in streams
   # Delete large objects after use
   ```

4. **Clear cache:**
   ```bash
   python -m src.cli.clear_cache
   ```

**Prevention:**
- Monitor memory usage
- Set memory limits in production
- Profile memory usage regularly

---

## Getting Help

### Support Channels

1. **Check Logs:**
   ```bash
   # System log
   tail -f logs/fpa_system.log

   # Component-specific logs
   tail -f logs/data_ingestion.log
   tail -f logs/consolidation.log
   tail -f logs/reporting.log
   ```

2. **Run Diagnostics:**
   ```bash
   python -m src.cli.diagnose \
     --period "2026-01-31" \
     --output diagnostic_report.txt
   ```

3. **Contact FP&A Team:**
   - Email: [pschumacher@nuvini.ai](mailto:pschumacher@nuvini.ai)
   - Slack: #fpa-support
   - Phone: +55 11 XXXX-XXXX (urgent only)

4. **Create GitHub Issue:**
   ```bash
   # Include diagnostic report
   gh issue create \
     --title "Consolidation fails for period 2026-01" \
     --body "$(cat diagnostic_report.txt)" \
     --label bug
   ```

### Escalation Path

1. **Level 1:** FP&A Analyst (john_analyst@nuvini.ai)
2. **Level 2:** FP&A Manager (sarah_manager@nuvini.ai)
3. **Level 3:** CFO (pierre_cfo@nuvini.ai)
4. **Level 4:** Engineering Team (engineering@nuvini.ai)

### Information to Provide

When reporting an issue, include:

- Period affected (e.g., "2026-01-31")
- Error message (full stack trace)
- Steps to reproduce
- Expected vs. actual behavior
- Diagnostic report output
- System logs (last 100 lines)

---

## Prevention Strategies

### Daily Monitoring

```bash
# Daily health check script
#!/bin/bash
python -m src.cli.health_check --full
python -m src.connectors.health_check --all
python -m src.cli.db_stats
python -m src.fx.check_rates --period "$(date +%Y-%m-01)"
```

### Weekly Maintenance

- Review error logs
- Update FX rates
- Check disk space
- Backup database
- Test ERP connections

### Monthly Best Practices

- Review rejection patterns
- Update AI model
- Optimize database indexes
- Archive old data
- Test disaster recovery

---

## Next Steps

- [Monthly Close Process](monthly-close.md) - Full workflow
- [ERP Integration Guide](erp-integration.md) - ERP-specific troubleshooting
- [Human Review Guide](human-review.md) - Review workflow issues

---

**Last Updated:** February 7, 2026
**Version:** 1.0.0
