# Security Architecture

**Version:** 1.0.0
**Last Updated:** 2026-02-07
**Implementation:** `/Volumes/AI/Code/FPA/src/core/`
**Compliance:** SOC 2 Type II, ISO 27001, IFRS, US GAAP, NASDAQ

## Overview

The AI FP&A system implements comprehensive security controls addressing data encryption, access control, and human oversight. This document describes the technical implementation of security findings #6, #7, and #8.

## Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Human Oversight (Finding #8)                         │   │
│  │ - Risk-based decision framework                      │   │
│  │ - Confidence scoring                                 │   │
│  │ - Four-eyes principle                                │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ RBAC Layer (Finding #7)                              │   │
│  │ - 11 agent roles                                     │   │
│  │ - 25+ granular permissions                           │   │
│  │ - API key scoping                                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Encryption Layer (Finding #6)                        │   │
│  │ - TLS 1.3 (in transit)                               │   │
│  │ - AES-256-GCM (at rest)                              │   │
│  │ - Column-level encryption                            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Row-Level Security (RLS)                             │   │
│  │ - Multi-tenant isolation                             │   │
│  │ - Company-level filtering                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Database Encryption                                   │   │
│  │ - PostgreSQL SSL/TLS                                 │   │
│  │ - pgcrypto for column encryption                     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ AWS KMS                                               │   │
│  │ - Master key management                              │   │
│  │ - Key rotation                                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ S3 Encryption                                         │   │
│  │ - Server-side encryption (KMS)                       │   │
│  │ - 7-year retention                                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Finding #6: Data Encryption

### Encryption Standards

| Component | Algorithm | Key Size | Standard |
|-----------|-----------|----------|----------|
| At Rest | AES-256-GCM | 256 bits | FIPS 140-2 |
| In Transit | TLS 1.3 | 2048+ bits RSA | RFC 8446 |
| Key Encryption | AES-256-GCM | 256 bits | Envelope encryption |
| Backup | Double encryption | 256 bits | App + S3 KMS |

### EncryptionManager

Central encryption management with envelope encryption (KEK/DEK pattern).

```python
from core.encryption import EncryptionManager, SensitiveFieldType

enc_manager = EncryptionManager(
    kms_master_key_id="arn:aws:kms:us-east-1:123456789012:key/abc-123",
    key_rotation_days=90
)

# Encrypt sensitive field
encrypted_revenue = enc_manager.encrypt_field(
    plaintext=Decimal("1250000.50"),
    field_type=SensitiveFieldType.REVENUE,
    metadata={'company': 'Effecti', 'period': '2026-01'}
)

# Decrypt field
decrypted_revenue = enc_manager.decrypt_field(
    encrypted_data=encrypted_revenue,
    field_type=SensitiveFieldType.REVENUE
)
```

**Envelope Encryption Pattern:**

```
Plaintext Data
    ↓
Encrypt with DEK (Data Encryption Key)
    ↓
Encrypted Data + Encrypted DEK
    ↓
Store: {
    "ciphertext": "...",
    "encrypted_dek": "...",
    "algorithm": "AES-256-GCM",
    "iv": "...",
    "tag": "..."
}
```

### Sensitive Field Types

```python
class SensitiveFieldType(Enum):
    """Types of sensitive fields requiring encryption."""
    REVENUE = "revenue"
    CUSTOMER_DATA = "customer_data"
    EMPLOYEE_PII = "employee_pii"
    API_CREDENTIALS = "api_credentials"
    FINANCIAL_FORECAST = "financial_forecast"
    BANKING_INFO = "banking_info"
```

### TLS Configuration

#### TLSConfigManager

Enforce TLS 1.3 for all ERP API connections.

```python
from core.encryption import TLSConfigManager

# Get secure SSL context
ssl_context = TLSConfigManager.get_secure_ssl_context()

# Get requests session with TLS 1.3
session = TLSConfigManager.get_requests_session()

# Make secure API call
response = session.get('https://erp-api.example.com/data')
```

**TLS Configuration:**

```python
{
    "minimum_version": ssl.TLSVersion.TLSv1_2,
    "maximum_version": ssl.TLSVersion.TLSv1_3,
    "cipher_suites": [
        "ECDHE-ECDSA-AES256-GCM-SHA384",
        "ECDHE-RSA-AES256-GCM-SHA384",
        "ECDHE-ECDSA-CHACHA20-POLY1305",
        "ECDHE-RSA-CHACHA20-POLY1305",
        "ECDHE-ECDSA-AES128-GCM-SHA256",
        "ECDHE-RSA-AES128-GCM-SHA256"
    ],
    "verify_mode": ssl.CERT_REQUIRED,
    "check_hostname": True
}
```

### PostgreSQL Encryption

#### Connection Encryption

```python
from core.encryption import PostgreSQLEncryption

pg_enc = PostgreSQLEncryption(
    connection_string="postgresql://user:pass@host:5432/db?sslmode=require"
)

# Get encrypted connection
conn = pg_enc.get_encrypted_connection()
```

**SSL Modes:**
- `require` - Require SSL/TLS (minimum)
- `verify-ca` - Verify CA certificate
- `verify-full` - Verify CA and hostname (recommended)

#### Column-Level Encryption

```python
# Encrypt column using pgcrypto
encrypted_value = pg_enc.encrypt_column_value(
    plaintext="sensitive_data",
    column_name="revenue"
)

# Decrypt column value
decrypted_value = pg_enc.decrypt_column_value(
    ciphertext=encrypted_value,
    column_name="revenue"
)
```

**PostgreSQL SQL:**

```sql
-- Enable pgcrypto extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Encrypt on insert
INSERT INTO financials (entity_id, revenue_encrypted)
VALUES (
    'effecti',
    pgp_sym_encrypt('1250000.50', 'encryption_key')
);

-- Decrypt on select
SELECT
    entity_id,
    pgp_sym_decrypt(revenue_encrypted, 'encryption_key') AS revenue
FROM financials;
```

### S3 Backup Encryption

#### S3EncryptionManager

```python
from core.encryption import S3EncryptionManager

s3_manager = S3EncryptionManager(
    bucket_name="fpa-backups-prod",
    kms_key_id="arn:aws:kms:us-east-1:123456789012:key/s3-key",
    region="us-east-1"
)

# Upload encrypted object
s3_manager.upload_encrypted(
    key="backups/2024-12/trial_balance.json",
    data=json.dumps(trial_balance_data),
    metadata={'company': 'effecti', 'period': '2024-12'}
)

# Download and decrypt
data = s3_manager.download_encrypted(
    key="backups/2024-12/trial_balance.json"
)
```

**S3 Bucket Policy:**

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Deny",
            "Principal": "*",
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::fpa-backups-prod/*",
            "Condition": {
                "StringNotEquals": {
                    "s3:x-amz-server-side-encryption": "aws:kms"
                }
            }
        }
    ]
}
```

#### BackupEncryptionManager

Double encryption (application-level + S3 KMS).

```python
from core.encryption import BackupEncryptionManager

backup_manager = BackupEncryptionManager(
    encryption_manager=enc_manager,
    s3_manager=s3_manager
)

# Create encrypted backup
s3_key = backup_manager.create_encrypted_backup(
    data=financial_data,
    backup_name='monthly_close_2024_12',
    metadata={'type': 'financial_data'}
)

# Restore backup
restored_data = backup_manager.restore_encrypted_backup(
    s3_key=s3_key
)
```

**Backup Lifecycle:**

```python
{
    "retention_years": 7,
    "transition_to_glacier_days": 90,
    "versioning_enabled": True,
    "object_lock_enabled": True
}
```

### Key Rotation

#### Automatic Key Rotation

```python
# Rotate all keys
enc_manager.rotate_keys()

# Rotate specific field type
enc_manager.rotate_keys(field_type=SensitiveFieldType.REVENUE)

# Check rotation status
rotation_info = enc_manager.get_rotation_info()
print(f"Last rotated: {rotation_info['last_rotation_date']}")
print(f"Next rotation: {rotation_info['next_rotation_date']}")
```

**Rotation Process:**

1. Generate new DEK
2. Encrypt new DEK with KEK
3. Re-encrypt data with new DEK
4. Update encrypted DEK reference
5. Archive old DEK (for recovery)
6. Log rotation event

**Rotation Schedule:**
- **Default:** 90 days
- **Configurable:** 30-365 days
- **Triggered:** On security event

## Finding #7: Role-Based Access Control

### RBAC Architecture

#### RBACManager

```python
from core.access_control import RBACManager, AgentRole, Permission

rbac = RBACManager()

# Check permission
can_write = rbac.check_permission(
    role=AgentRole.DATA_INGESTION,
    permission=Permission.WRITE_RAW_DATA
)

# Get role permissions
permissions = rbac.get_role_permissions(AgentRole.DATA_INGESTION)
```

### Agent Roles

| Role | Permissions | Data Access | Companies |
|------|-------------|-------------|-----------|
| `orchestrator` | Full operational access | Confidential | All |
| `data_ingestion` | Write raw data | Internal | Scoped |
| `consolidation` | Read raw, write consolidated | Confidential | All |
| `validation` | Read-only | Confidential | All |
| `analysis` | Read consolidated | Confidential | All |
| `forecasting` | Create forecasts | Confidential | All |
| `reporting` | Generate reports | Confidential | All |
| `compliance` | Read + audit logs | Restricted | All |
| `human_reviewer` | Approval authority | Restricted | All |
| `system_admin` | Full access | Restricted | All |
| `read_only` | Read consolidated | Internal | Scoped |

### Permission Types

```python
class Permission(Enum):
    """Granular permissions."""
    # Data access
    READ_RAW_DATA = "read_raw_data"
    WRITE_RAW_DATA = "write_raw_data"
    READ_CONSOLIDATED_DATA = "read_consolidated_data"
    WRITE_CONSOLIDATED_DATA = "write_consolidated_data"
    READ_SENSITIVE_DATA = "read_sensitive_data"

    # Financial operations
    CREATE_JOURNAL_ENTRY = "create_journal_entry"
    APPROVE_JOURNAL_ENTRY = "approve_journal_entry"
    REVERSE_JOURNAL_ENTRY = "reverse_journal_entry"
    CLOSE_PERIOD = "close_period"
    REOPEN_PERIOD = "reopen_period"

    # Analysis
    RUN_VARIANCE_ANALYSIS = "run_variance_analysis"
    CREATE_FORECAST = "create_forecast"
    MODIFY_ASSUMPTIONS = "modify_assumptions"

    # Reports
    GENERATE_REPORT = "generate_report"
    EXPORT_DATA = "export_data"
    SHARE_REPORT = "share_report"

    # Administrative
    MANAGE_USERS = "manage_users"
    MODIFY_SCHEMA = "modify_schema"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MODIFY_SECURITY_SETTINGS = "modify_security_settings"

    # System
    EXECUTE_BATCH_JOB = "execute_batch_job"
    ACCESS_API = "access_api"
```

### API Key Management

#### Generate API Key

```python
# Generate scoped API key
api_key = rbac.generate_api_key(
    role=AgentRole.DATA_INGESTION,
    agent_id='effecti_connector',
    companies=['effecti'],
    expires_days=90
)

print(f"API Key: {api_key.key}")
print(f"Expires: {api_key.expires_at}")
```

**API Key Structure:**

```python
{
    "key_id": "uuid",
    "key": "fpa_abc123...xyz789",  # 43 characters (32 bytes base64)
    "role": "data_ingestion",
    "agent_id": "effecti_connector",
    "companies": ["effecti"],
    "created_at": "2026-02-07T10:00:00Z",
    "expires_at": "2026-05-07T10:00:00Z",
    "is_active": True
}
```

#### Validate API Key

```python
# Validate API key from request
validated = rbac.validate_api_key(api_key_string)

if validated:
    # Check company access
    if validated.can_access_company('effecti'):
        # Process request
        pass
    else:
        raise PermissionError("Access denied to company")
else:
    raise AuthenticationError("Invalid or expired API key")
```

#### Revoke API Key

```python
# Revoke API key
rbac.revoke_api_key(
    key_id="uuid",
    reason="Security incident - key compromised"
)
```

### Row-Level Security (RLS)

#### PostgreSQLRBACManager

Generate PostgreSQL RBAC setup SQL.

```python
from core.access_control import PostgreSQLRBACManager

pg_rbac = PostgreSQLRBACManager()

# Create database role
create_role_sql = pg_rbac.create_role_sql(AgentRole.DATA_INGESTION)

# Grant permissions
grant_sql = pg_rbac.grant_permissions_sql(
    role=AgentRole.DATA_INGESTION,
    permissions=[Permission.READ_RAW_DATA, Permission.WRITE_RAW_DATA]
)

# Create RLS policy
rls_sql = pg_rbac.create_rls_policy_sql(
    table_name='trial_balances',
    role=AgentRole.DATA_INGESTION,
    permissions=[Permission.WRITE_RAW_DATA]
)
```

**Generated SQL:**

```sql
-- Create role
CREATE ROLE data_ingestion_role;

-- Grant permissions
GRANT SELECT, INSERT ON trial_balances TO data_ingestion_role;

-- Enable RLS
ALTER TABLE trial_balances ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY data_ingestion_policy ON trial_balances
    FOR ALL
    TO data_ingestion_role
    USING (
        entity_id IN (
            SELECT entity_id FROM user_entity_access
            WHERE user_id = current_setting('app.user_id')::uuid
              AND can_read = TRUE
        )
    )
    WITH CHECK (
        entity_id IN (
            SELECT entity_id FROM user_entity_access
            WHERE user_id = current_setting('app.user_id')::uuid
              AND can_write = TRUE
        )
    );
```

### Audit Logging

All permission checks and violations are logged.

```python
# Permission violations auto-logged
rbac.check_permission(AgentRole.READ_ONLY, Permission.MODIFY_SCHEMA)

# View audit log
for entry in rbac.audit_log:
    print(f"{entry['timestamp']}: {entry['event']}")
    print(f"  Role: {entry['role']}")
    print(f"  Permission: {entry['permission']}")
    print(f"  Result: {entry['result']}")
    print(f"  Reason: {entry['reason']}")
```

**Audit Log Entry:**

```json
{
    "timestamp": "2026-02-07T10:30:00Z",
    "event": "permission_violation",
    "role": "read_only",
    "permission": "modify_schema",
    "result": "denied",
    "reason": "Role 'read_only' does not have permission 'modify_schema'",
    "agent_id": "viewer_001",
    "request_id": "req_abc123"
}
```

## Finding #8: Human Oversight

### Risk-Based Decision Framework

#### HumanOversightManager

```python
from core.human_oversight import HumanOversightManager

oversight = HumanOversightManager()

# Evaluate transaction
transaction = {
    'id': 'TX001',
    'amount': 1500000,
    'account': 'intercompany_revenue',
    'is_intercompany': True,
    'is_manual_adjustment': True
}

context = {
    'company_size': 'medium',
    'data_quality_score': 0.95,
    'historical_data': [],
    'budget': {},
    'agent_id': 'consolidation_agent'
}

confidence, review_request = oversight.evaluate_transaction(transaction, context)
```

### Confidence Scoring

#### ConfidenceScoringEngine

```python
from core.human_oversight import ConfidenceScoringEngine

scoring_engine = ConfidenceScoringEngine(
    green_threshold=0.80,
    yellow_threshold=0.50
)

# Calculate confidence score
confidence = scoring_engine.calculate_confidence(
    transaction=transaction,
    context=context
)

print(f"Confidence: {confidence.confidence_percentage:.1f}%")
print(f"Risk Level: {confidence.risk_level.value}")
print(f"Requires Review: {confidence.requires_review}")
```

**Risk Factors and Weights:**

| Factor | Weight | Description |
|--------|--------|-------------|
| Materiality | 30% | Amount vs. materiality threshold |
| Pattern Deviation | 25% | Deviation from historical patterns |
| Data Quality | 20% | Data quality and completeness |
| Complexity | 15% | Transaction complexity |
| Variance | 10% | Variance from budget/forecast |

**Calculation:**

```python
raw_score = 1.0 - sum(
    risk_factor.weight * risk_factor.value
    for risk_factor in risk_factors
)

if raw_score >= 0.80:
    risk_level = RiskLevel.GREEN
elif raw_score >= 0.50:
    risk_level = RiskLevel.YELLOW
else:
    risk_level = RiskLevel.RED
```

### Risk Levels

| Level | Confidence | Action | Sampling |
|-------|-----------|--------|----------|
| 🟢 Green | ≥80% | Auto-approve with post-review | 5% |
| 🟡 Yellow | 50-79% | Mandatory pre-review | 100% |
| 🔴 Red | <50% | Escalated multi-person review | 100% |

### Mandatory Review Categories

```python
class ReviewCategory(Enum):
    """Categories requiring mandatory review."""
    PERIOD_CLOSE = "period_close"
    INTERCOMPANY_ELIMINATION = "intercompany_elimination"
    REGULATORY_REPORT = "regulatory_report"
    EXTERNAL_COMMUNICATION = "external_communication"
    MANUAL_ADJUSTMENT = "manual_adjustment"
    VARIANCE_EXCEEDS_THRESHOLD = "variance_exceeds_threshold"
    FIRST_TIME_TRANSACTION = "first_time_transaction"
    LARGE_AMOUNT = "large_amount"
```

### Four-Eyes Principle

```python
# Create review request requiring 2 reviewers
review_request = ReviewRequest(
    request_id="review-uuid",
    transaction=transaction,
    confidence_score=confidence,
    category=ReviewCategory.PERIOD_CLOSE,
    required_reviewers=2,
    escalation_level=EscalationLevel.FPA_MANAGER,
    created_at=datetime.utcnow()
)

# First reviewer
oversight.submit_review(
    review_request_id="review-uuid",
    reviewer_id="reviewer_001",
    decision="approved",
    comments="Amounts reconcile correctly."
)

# Second reviewer (different person required)
oversight.submit_review(
    review_request_id="review-uuid",
    reviewer_id="reviewer_002",  # Must be different
    decision="approved",
    comments="Second review confirmed."
)

# Check if complete
is_complete = review_request.is_complete()
```

### Escalation Matrix

| Level | Role | SLA | Use Case |
|-------|------|-----|----------|
| 0 | None | - | Auto-approved (green) |
| 1 | FP&A Analyst | 24h | Yellow risk transactions |
| 2 | FP&A Manager | 12h | Red risk, period close |
| 3 | CFO | 6h | Regulatory, external comms |
| 4 | Audit Committee | 48h | Critical issues |

```python
class EscalationLevel(Enum):
    """Escalation levels for reviews."""
    NONE = 0
    FPA_ANALYST = 1
    FPA_MANAGER = 2
    CFO = 3
    AUDIT_COMMITTEE = 4
```

### Review Workflow

```python
# Get pending reviews
pending = oversight.get_pending_reviews(
    risk_level=RiskLevel.RED
)

# Get overdue reviews
overdue = oversight.get_overdue_reviews()

# Auto-escalate overdue reviews
for review in overdue:
    if review.hours_pending > 24:
        oversight.escalate_review(
            review_request_id=review.request_id,
            reason="Review overdue - escalating"
        )
```

### Oversight Reporting

```python
# Generate oversight report
report = oversight.generate_oversight_report(
    start_date=datetime(2024, 12, 1),
    end_date=datetime(2024, 12, 31)
)

print(f"Total Reviews: {report['total_reviews']}")
print(f"Approval Rate: {report['approval_rate']:.1%}")
print(f"Average Confidence: {report['average_confidence']:.1%}")
print(f"Four-Eyes Reviews: {report['four_eyes_percentage']:.1%}")
print(f"SLA Compliance: {report['sla_compliance']:.1%}")
```

## Compliance and Governance

### Security Standards

| Standard | Coverage | Evidence |
|----------|----------|----------|
| SOC 2 Type II | Access controls, encryption, audit logging | ✓ |
| ISO 27001 | Information security management | ✓ |
| IFRS | Financial data integrity, retention | ✓ |
| US GAAP | Internal controls, four-eyes | ✓ |
| NASDAQ | Financial reporting controls | ✓ |

### Data Classification

| Level | Encryption | Logging | Approval | Examples |
|-------|-----------|---------|----------|----------|
| Public | Optional | No | No | Product docs |
| Internal | Required | Yes | No | Trial balances |
| Confidential | Required | Yes | No | Revenue, EBITDA |
| Restricted | Required | Yes | Yes | Customer PII, bank accounts |

### Audit Trail Retention

All security events retained for 7 years:

- Permission checks and violations
- API key creation, usage, revocation
- Data access (read/write)
- Encryption key rotations
- Human review decisions
- Escalations
- Configuration changes

## Security Monitoring

### Alerts

```python
{
    "alerts": [
        {
            "event": "multiple_failed_auth",
            "threshold": 5,
            "window_minutes": 15,
            "severity": "high"
        },
        {
            "event": "permission_violation",
            "threshold": 3,
            "window_minutes": 60,
            "severity": "medium"
        },
        {
            "event": "unusual_data_access",
            "threshold": 1,
            "window_minutes": 1,
            "severity": "high"
        },
        {
            "event": "encryption_failure",
            "threshold": 1,
            "window_minutes": 1,
            "severity": "critical"
        }
    ]
}
```

### Incident Response

1. **Detection** - Automated alert triggered
2. **Containment** - Revoke compromised credentials
3. **Investigation** - Review audit logs
4. **Remediation** - Apply fixes and patches
5. **Documentation** - Document incident
6. **Post-Mortem** - Review and improve

## See Also

- [Database Schema](/Volumes/AI/Code/FPA/manual/technical-reference/database.md)
- [API Reference](/Volumes/AI/Code/FPA/manual/technical-reference/api-reference.md)
- [Configuration Reference](/Volumes/AI/Code/FPA/manual/technical-reference/configuration.md)
