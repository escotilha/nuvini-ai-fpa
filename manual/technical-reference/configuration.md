# Configuration Reference

**Version:** 1.0.0
**Last Updated:** 2026-02-07
**Configuration File:** `/Volumes/AI/Code/FPA/config/security_policy.yaml`

## Overview

The AI FP&A system uses YAML-based configuration for security policies, RBAC rules, encryption settings, and human oversight parameters. This document provides a complete reference for all configuration options.

## Configuration Structure

```
config/
├── security_policy.yaml         # Main security configuration
├── database.yaml                # Database connection settings
├── erp_connectors.yaml          # ERP connector credentials
└── environments/
    ├── development.yaml
    ├── staging.yaml
    └── production.yaml
```

## Security Policy Configuration

### Encryption Settings

#### Standards

```yaml
encryption:
  standards:
    algorithm: "AES-256-GCM"      # Encryption algorithm
    key_size: 256                  # Key size in bits
    tls_version: "1.3"             # TLS version
    tls_fallback: "1.2"            # TLS fallback version
```

**Valid Values:**
- `algorithm`: `AES-256-GCM`, `AES-256-CBC`
- `key_size`: `128`, `192`, `256`
- `tls_version`: `1.2`, `1.3`

#### Key Rotation

```yaml
encryption:
  key_rotation:
    enabled: true                  # Enable automatic key rotation
    rotation_interval_days: 90     # Rotation frequency (days)
    notification_before_days: 14   # Warning before rotation
    auto_rotation: true            # Automatic vs manual rotation
```

**Valid Values:**
- `rotation_interval_days`: `30-365`
- `notification_before_days`: `7-30`

#### AWS KMS Configuration

```yaml
encryption:
  kms:
    enabled: true
    master_key_id: "${AWS_KMS_MASTER_KEY_ID}"
    s3_key_id: "${AWS_KMS_S3_KEY_ID}"
    key_alias: "alias/fpa-master-key"
    multi_region: true
```

**Environment Variables:**
- `AWS_KMS_MASTER_KEY_ID` - ARN of master KMS key
- `AWS_KMS_S3_KEY_ID` - ARN of S3 encryption key
- `AWS_REGION` - AWS region (default: us-east-1)

#### TLS Configuration

```yaml
encryption:
  tls:
    minimum_version: "TLSv1_2"
    preferred_version: "TLSv1_3"
    cipher_suites:
      - "ECDHE-ECDSA-AES256-GCM-SHA384"
      - "ECDHE-RSA-AES256-GCM-SHA384"
      - "ECDHE-ECDSA-CHACHA20-POLY1305"
      - "ECDHE-RSA-CHACHA20-POLY1305"
      - "ECDHE-ECDSA-AES128-GCM-SHA256"
      - "ECDHE-RSA-AES128-GCM-SHA256"
    verify_certificates: true
    check_hostname: true
```

**Cipher Suite Priority:**
1. ECDHE (Forward secrecy)
2. AES-256-GCM (Authenticated encryption)
3. ChaCha20-Poly1305 (Mobile optimization)

#### PostgreSQL Encryption

```yaml
encryption:
  postgresql:
    ssl_mode: "require"            # SSL connection mode
    ssl_cert_verification: true    # Verify server certificate
    connection_encryption: true    # Encrypt all connections
    enable_pgcrypto: true          # Enable pgcrypto extension

    tde:
      enabled: true
      method: "pgcrypto"

    encrypted_columns:
      - table: "financials"
        columns: ["revenue", "net_income", "ebitda"]
        field_type: "revenue"

      - table: "customers"
        columns: ["customer_name", "tax_id", "bank_account"]
        field_type: "customer_data"
```

**SSL Modes:**
- `disable` - No SSL (not recommended)
- `allow` - Use SSL if available
- `prefer` - Prefer SSL
- `require` - Require SSL
- `verify-ca` - Require SSL and verify CA
- `verify-full` - Require SSL and verify hostname

#### S3 Encryption

```yaml
encryption:
  s3:
    server_side_encryption: "aws:kms"
    bucket_key_enabled: true
    enforce_encryption: true

    backup_bucket:
      name: "${S3_BACKUP_BUCKET}"
      versioning: true
      object_lock: true
      lifecycle:
        transition_to_glacier_days: 90
        expiration_days: 2555        # 7 years

  backups:
    encryption_required: true
    double_encryption: true          # App-level + S3 KMS
    backup_key_rotation_days: 30
    retention_years: 7
    test_restoration_monthly: true
```

**S3 Encryption Options:**
- `AES256` - S3-managed keys
- `aws:kms` - KMS-managed keys (recommended)
- `aws:kms:dsse` - Dual-layer server-side encryption

### RBAC Configuration

#### Enable RBAC

```yaml
rbac:
  enabled: true
```

#### Role Definitions

```yaml
rbac:
  roles:
    orchestrator:
      description: "Master orchestrator with full operational access"
      permissions:
        - "read_raw_data"
        - "write_raw_data"
        - "read_consolidated_data"
        - "write_consolidated_data"
        - "create_journal_entry"
        - "run_variance_analysis"
        - "create_forecast"
        - "generate_report"
        - "execute_batch_job"
        - "access_api"
        - "view_audit_logs"
      data_access_level: "confidential"
      companies: null                 # All companies
```

**Data Access Levels:**
- `public` - No restrictions
- `internal` - Internal use only
- `confidential` - Confidential data
- `restricted` - Highly restricted (PII, financials)

**Permissions List:**

```yaml
permissions:
  # Data access
  - read_raw_data
  - write_raw_data
  - read_consolidated_data
  - write_consolidated_data
  - read_sensitive_data

  # Financial operations
  - create_journal_entry
  - approve_journal_entry
  - reverse_journal_entry
  - close_period
  - reopen_period

  # Analysis
  - run_variance_analysis
  - create_forecast
  - modify_assumptions

  # Reports
  - generate_report
  - export_data
  - share_report

  # Administrative
  - manage_users
  - modify_schema
  - view_audit_logs
  - modify_security_settings

  # System
  - execute_batch_job
  - access_api
```

#### API Key Configuration

```yaml
rbac:
  api_keys:
    enabled: true
    key_prefix: "fpa_"
    key_length: 43                   # 32 bytes base64
    default_expiration_days: 90
    max_expiration_days: 365
    rotation_warning_days: 14

    scoping:
      by_role: true
      by_company: true
      by_ip: false                   # Set to true for production
```

**API Key Format:**
```
fpa_<base64-encoded-32-bytes>
Example: fpa_abc123def456ghi789jkl012mno345pqr678stu901
```

#### Row-Level Security

```yaml
rbac:
  row_level_security:
    enabled: true
    enforce_in_database: true

    company_isolation:
      enabled: true
      filter_column: "company_id"
      session_variable: "app.allowed_companies"
```

**PostgreSQL Session Variable:**

```sql
-- Set allowed companies for current session
SET app.allowed_companies = 'effecti,leadlovers';

-- RLS policy will filter to only these companies
SELECT * FROM trial_balances;  -- Only returns effecti and leadlovers data
```

#### Audit Logging

```yaml
rbac:
  audit_logging:
    enabled: true
    log_all_access: true
    log_permission_violations: true
    log_failed_auth: true
    retention_days: 2555              # 7 years

    events:
      - "permission_check"
      - "permission_violation"
      - "api_key_created"
      - "api_key_revoked"
      - "api_key_used"
      - "data_access"
      - "data_modification"
      - "role_assignment"
      - "security_setting_change"
```

### Human Oversight Configuration

#### Confidence Thresholds

```yaml
human_oversight:
  enabled: true

  confidence_thresholds:
    green: 0.80                       # >= 80% confidence
    yellow: 0.50                      # 50-79% confidence
    # < 50% = red (implicit)
```

**Risk Level Determination:**

```python
if confidence >= 0.80:
    return RiskLevel.GREEN
elif confidence >= 0.50:
    return RiskLevel.YELLOW
else:
    return RiskLevel.RED
```

#### Sampling Rates

```yaml
human_oversight:
  sampling:
    green: 0.05                       # 5% post-review sampling
    yellow: 1.00                      # 100% mandatory pre-review
    red: 1.00                         # 100% mandatory pre-review
```

**Sampling Strategy:**
- **Green:** Random sampling for continuous monitoring
- **Yellow:** All transactions require review
- **Red:** All transactions require escalated review

#### Materiality Thresholds

```yaml
human_oversight:
  materiality_thresholds:
    small:
      amount: 10000
      currency: "USD"
    medium:
      amount: 50000
      currency: "USD"
    large:
      amount: 250000
      currency: "USD"
    enterprise:
      amount: 1000000
      currency: "USD"
```

**Company Size Determination:**
- `small`: Annual revenue < $10M
- `medium`: Annual revenue $10M-$100M
- `large`: Annual revenue $100M-$1B
- `enterprise`: Annual revenue > $1B

#### Risk Factor Weights

```yaml
human_oversight:
  risk_factors:
    materiality:
      weight: 0.30
      description: "Transaction amount relative to materiality threshold"

    pattern_deviation:
      weight: 0.25
      description: "Deviation from historical transaction patterns"

    data_quality:
      weight: 0.20
      description: "Data quality and completeness score"

    complexity:
      weight: 0.15
      description: "Transaction complexity and special handling"

    variance:
      weight: 0.10
      description: "Variance from budgeted or forecasted amounts"
```

**Constraint:** Weights must sum to 1.0

#### Mandatory Review Categories

```yaml
human_oversight:
  mandatory_review:
    - category: "period_close"
      description: "Monthly/quarterly period close operations"
      required_reviewers: 2
      escalation_level: "fpa_manager"

    - category: "intercompany_elimination"
      description: "Intercompany transaction eliminations"
      required_reviewers: 2
      escalation_level: "fpa_manager"

    - category: "regulatory_report"
      description: "External regulatory reporting"
      required_reviewers: 2
      escalation_level: "cfo"

    - category: "manual_adjustment"
      description: "Manual journal entries and adjustments"
      required_reviewers: 1
      escalation_level: "fpa_analyst"

    - category: "variance_exceeds_threshold"
      description: "Variances exceeding 15% of budget/forecast"
      required_reviewers: 1
      escalation_level: "fpa_analyst"
      threshold: 0.15
```

#### Four-Eyes Principle

```yaml
human_oversight:
  four_eyes:
    enabled: true
    required_for:
      - "period_close"
      - "intercompany_elimination"
      - "regulatory_report"
      - "external_communication"
      - "red_risk_level"
    minimum_reviewers: 2
    same_reviewer_allowed: false
```

#### Escalation Matrix

```yaml
human_oversight:
  escalation:
    levels:
      - level: 0
        name: "none"
        description: "No escalation - auto-approved with sampling"

      - level: 1
        name: "fpa_analyst"
        description: "FP&A Analyst review"
        sla_hours: 24

      - level: 2
        name: "fpa_manager"
        description: "FP&A Manager review"
        sla_hours: 12

      - level: 3
        name: "cfo"
        description: "CFO review"
        sla_hours: 6

      - level: 4
        name: "audit_committee"
        description: "Audit Committee review"
        sla_hours: 48

    auto_escalation:
      enabled: true
      escalate_if_overdue: true
      escalate_if_rejected: true
      escalate_after_hours: 24
```

#### Review Workflow

```yaml
human_oversight:
  review_workflow:
    notification_enabled: true
    notification_channels:
      - "email"
      - "slack"

    reminder_schedule:
      - hours: 12
        message: "Review pending - 12 hours"
      - hours: 24
        message: "Review overdue - escalating"
        action: "escalate"

    review_retention_days: 2555       # 7 years
```

#### Oversight Reporting

```yaml
human_oversight:
  oversight_reporting:
    enabled: true

    reports:
      - name: "daily_review_summary"
        frequency: "daily"
        recipients:
          - "fpa_manager"

      - name: "weekly_oversight_metrics"
        frequency: "weekly"
        recipients:
          - "fpa_manager"
          - "cfo"

      - name: "monthly_control_effectiveness"
        frequency: "monthly"
        recipients:
          - "cfo"
          - "audit_committee"

    metrics:
      - "total_reviews"
      - "approval_rate"
      - "average_confidence_score"
      - "risk_level_breakdown"
      - "four_eyes_percentage"
      - "sla_compliance"
      - "escalation_rate"
      - "average_review_time"
```

## Compliance Configuration

### Frameworks

```yaml
compliance:
  frameworks:
    - "SOC 2 Type II"
    - "ISO 27001"
    - "IFRS"
    - "US GAAP"
    - "NASDAQ Listing Requirements"
```

### Data Retention

```yaml
compliance:
  data_retention:
    financial_data_years: 7
    audit_logs_years: 7
    backups_years: 7
```

### Data Classification

```yaml
compliance:
  data_classification:
    levels:
      - name: "public"
        encryption_required: false
        access_logging: false

      - name: "internal"
        encryption_required: true
        access_logging: true

      - name: "confidential"
        encryption_required: true
        access_logging: true
        approval_required: false

      - name: "restricted"
        encryption_required: true
        access_logging: true
        approval_required: true
```

### Security Monitoring

```yaml
compliance:
  monitoring:
    enabled: true

    alerts:
      - event: "multiple_failed_auth"
        threshold: 5
        window_minutes: 15
        severity: "high"

      - event: "permission_violation"
        threshold: 3
        window_minutes: 60
        severity: "medium"

      - event: "unusual_data_access"
        threshold: 1
        window_minutes: 1
        severity: "high"

      - event: "encryption_failure"
        threshold: 1
        window_minutes: 1
        severity: "critical"

    incident_response:
      enabled: true
      notification_channels:
        - "email"
        - "pagerduty"
      escalation_minutes: 30
```

## System Configuration

### Environment

```yaml
system:
  environment: "${ENVIRONMENT}"       # development, staging, production
```

**Valid Environments:**
- `development` - Local development
- `staging` - Staging/UAT environment
- `production` - Production environment

### Feature Flags

```yaml
system:
  features:
    encryption: true
    rbac: true
    human_oversight: true
    audit_logging: true
```

### Security Hardening

```yaml
system:
  hardening:
    disable_root_access: true
    require_mfa: true
    session_timeout_minutes: 60
    password_policy:
      min_length: 16
      require_special_chars: true
      require_numbers: true
      require_uppercase: true
      expiration_days: 90
```

## Database Configuration

### Connection Settings

```yaml
database:
  host: "${DB_HOST}"
  port: 5432
  database: "${DB_NAME}"
  username: "${DB_USERNAME}"
  password: "${DB_PASSWORD}"

  ssl:
    enabled: true
    mode: "verify-full"
    cert_file: "/path/to/cert.pem"
    key_file: "/path/to/key.pem"
    ca_file: "/path/to/ca.pem"

  pool:
    min_size: 5
    max_size: 20
    timeout: 30
```

### Performance Tuning

```yaml
database:
  performance:
    shared_buffers: "8GB"
    effective_cache_size: "24GB"
    work_mem: "256MB"
    maintenance_work_mem: "2GB"
    max_worker_processes: 8
    max_parallel_workers_per_gather: 4
    max_parallel_workers: 8

  optimization:
    random_page_cost: 1.1             # For SSD
    effective_io_concurrency: 200
    enable_partition_pruning: true
    constraint_exclusion: "partition"
    default_statistics_target: 100
```

## ERP Connector Configuration

### TOTVS Protheus

```yaml
erp_connectors:
  totvs_protheus:
    base_url: "https://api.totvs.com.br/protheus"
    auth_type: "oauth2"
    credentials:
      client_id: "${TOTVS_CLIENT_ID}"
      client_secret: "${TOTVS_CLIENT_SECRET}"
      token_url: "https://api.totvs.com.br/oauth/token"
    config:
      tenant: "${TOTVS_TENANT_ID}"
      environment: "production"
      timeout: 30
      rate_limit: 100                 # requests per minute
```

### ContaAzul

```yaml
erp_connectors:
  contaazul:
    base_url: "https://api.contaazul.com/v1"
    auth_type: "oauth2"
    credentials:
      client_id: "${CONTAAZUL_CLIENT_ID}"
      client_secret: "${CONTAAZUL_CLIENT_SECRET}"
      token_url: "https://api.contaazul.com/oauth/token"
    config:
      timeout: 30
      rate_limit: 60
```

### Omie

```yaml
erp_connectors:
  omie:
    base_url: "https://app.omie.com.br/api/v1"
    auth_type: "api_key"
    credentials:
      app_key: "${OMIE_APP_KEY}"
      app_secret: "${OMIE_APP_SECRET}"
    config:
      timeout: 30
      rate_limit: 300
```

### Bling

```yaml
erp_connectors:
  bling:
    base_url: "https://bling.com.br/Api/v3"
    auth_type: "api_key"
    credentials:
      api_key: "${BLING_API_KEY}"
    config:
      api_version: "v3"
      timeout: 30
      rate_limit: 100
```

## Environment-Specific Configuration

### Development

```yaml
# environments/development.yaml
system:
  environment: "development"

database:
  host: "localhost"
  port: 5432
  pool:
    min_size: 2
    max_size: 10

encryption:
  kms:
    enabled: false                    # Use local encryption

human_oversight:
  confidence_thresholds:
    green: 0.60                       # Lower threshold for testing
    yellow: 0.30
```

### Production

```yaml
# environments/production.yaml
system:
  environment: "production"

database:
  host: "prod-db.fpa.nuvini.ai"
  ssl:
    mode: "verify-full"

encryption:
  kms:
    enabled: true
    multi_region: true

rbac:
  api_keys:
    scoping:
      by_ip: true                     # IP whitelisting in production

human_oversight:
  confidence_thresholds:
    green: 0.80
    yellow: 0.50

compliance:
  monitoring:
    enabled: true
```

## Loading Configuration

### Python

```python
import yaml
from pathlib import Path

# Load configuration
config_path = Path("/Volumes/AI/Code/FPA/config/security_policy.yaml")
with open(config_path) as f:
    config = yaml.safe_load(f)

# Load environment-specific overrides
env = os.environ.get("ENVIRONMENT", "development")
env_config_path = Path(f"/Volumes/AI/Code/FPA/config/environments/{env}.yaml")
if env_config_path.exists():
    with open(env_config_path) as f:
        env_config = yaml.safe_load(f)
        # Merge configurations (deep merge)
        config = deep_merge(config, env_config)

# Access configuration
encryption_enabled = config['encryption']['kms']['enabled']
green_threshold = config['human_oversight']['confidence_thresholds']['green']
```

### Environment Variable Substitution

```python
import os
import re

def substitute_env_vars(config_str):
    """Replace ${VAR} with environment variable values."""
    pattern = r'\$\{([^}]+)\}'
    return re.sub(
        pattern,
        lambda m: os.environ.get(m.group(1), m.group(0)),
        config_str
    )

# Load with substitution
with open(config_path) as f:
    config_str = f.read()
    config_str = substitute_env_vars(config_str)
    config = yaml.safe_load(config_str)
```

## Validation

### Schema Validation

```python
from jsonschema import validate

# Define schema
config_schema = {
    "type": "object",
    "required": ["encryption", "rbac", "human_oversight"],
    "properties": {
        "encryption": {
            "type": "object",
            "required": ["standards", "kms"]
        },
        "rbac": {
            "type": "object",
            "required": ["enabled", "roles"]
        },
        "human_oversight": {
            "type": "object",
            "required": ["enabled", "confidence_thresholds"]
        }
    }
}

# Validate configuration
validate(instance=config, schema=config_schema)
```

## See Also

- [Database Schema](/Volumes/AI/Code/FPA/manual/technical-reference/database.md)
- [API Reference](/Volumes/AI/Code/FPA/manual/technical-reference/api-reference.md)
- [Security Architecture](/Volumes/AI/Code/FPA/manual/technical-reference/security.md)
- [ERP Connectors](/Volumes/AI/Code/FPA/manual/technical-reference/erp-connectors.md)
- [Consolidation Engine](/Volumes/AI/Code/FPA/manual/technical-reference/consolidation-engine.md)
