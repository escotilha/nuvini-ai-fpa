"""
Core framework components for AI FP&A system.

Includes:
- Database session management
- Secrets management (AWS Secrets Manager)
- Audit logging (immutable S3 logs)
- Encryption utilities
- Access control
- Configuration
"""

from .config import settings
from .database import DatabaseSession, get_db
from .secrets import SecretsManager
from .audit_trail import ImmutableAuditLog
from .encryption import FieldEncryption
from .access_control import AccessController
from .models import (
    Entity,
    TrialBalance,
    ConsolidatedBalance,
    JournalEntry,
    ETLBatch,
    ValidationResult,
)

__all__ = [
    "settings",
    "DatabaseSession",
    "get_db",
    "SecretsManager",
    "ImmutableAuditLog",
    "FieldEncryption",
    "AccessController",
    "Entity",
    "TrialBalance",
    "ConsolidatedBalance",
    "JournalEntry",
    "ETLBatch",
    "ValidationResult",
]
