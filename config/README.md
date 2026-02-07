# Configuration Files

## Directory Structure

```
config/
├── security_policy.yaml       # Security policies and compliance rules
├── access_control.yaml        # RBAC matrix and permissions
├── compliance_policy.yaml     # SEC/NASDAQ compliance rules
├── erp_credentials_policy.yaml # ERP connection policies
├── validation_rules.yaml      # Data validation rules
└── consolidation_rules.yaml   # Consolidation methodology
```

## Usage

Configuration files are loaded at application startup and cached in memory.

**Python usage:**
```python
from src.core.config import settings
from src.core.policies import load_policy

# Access settings
database_url = settings.database_url

# Load policies
security_policy = load_policy("security_policy.yaml")
access_control = load_policy("access_control.yaml")
```

## Security Notes

- **NEVER commit credentials** to version control
- Use AWS Secrets Manager for all sensitive data
- Policy files contain rules, not secrets
- Review policies quarterly for compliance

## Policy Validation

All policy files are validated against JSON schemas at startup:

```bash
python -m src.core.validate_policies
```

## Environment-Specific Configs

Different configs per environment:

```
config/
├── development/
│   ├── security_policy.yaml
│   └── access_control.yaml
├── staging/
│   ├── security_policy.yaml
│   └── access_control.yaml
└── production/
    ├── security_policy.yaml
    └── access_control.yaml
```

Load based on `ENVIRONMENT` env var.
