# Backup & Recovery

## Automated Backups

- **RDS Backups:** Daily automated snapshots, 7-day retention
- **S3 Audit Logs:** Immutable with 7-year retention
- **Configuration:** Version controlled in Git

## Recovery Procedures

### Database Recovery

```bash
# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier fpa-restored \
    --db-snapshot-identifier <snapshot-id>
```

### Disaster Recovery

RPO: 24 hours | RTO: 4 hours
