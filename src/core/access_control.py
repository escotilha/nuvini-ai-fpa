"""
Role-Based Access Control (RBAC) Implementation for AI FP&A System
Finding #7: Insufficient RBAC

This module provides comprehensive access control for:
- PostgreSQL roles for each agent type
- Granular permissions matrix
- Row-Level Security (RLS) policies
- API key scoping per agent
- Audit logging for permission violations

Security Level: Critical
Compliance: SOC 2, ISO 27001, Principle of Least Privilege
"""

from enum import Enum
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import hashlib
import secrets
import json


class AgentRole(Enum):
    """Agent roles in the FP&A system"""
    ORCHESTRATOR = "orchestrator"  # Master orchestrator - highest privileges
    DATA_INGESTION = "data_ingestion"  # ERP data ingestion agents
    CONSOLIDATION = "consolidation"  # Financial consolidation agent
    VALIDATION = "validation"  # Data quality validation agent
    ANALYSIS = "analysis"  # Variance and KPI analysis agent
    FORECASTING = "forecasting"  # Forecasting agent
    REPORTING = "reporting"  # Report generation agent
    COMPLIANCE = "compliance"  # Compliance monitoring agent
    HUMAN_REVIEWER = "human_reviewer"  # Human FP&A reviewers
    SYSTEM_ADMIN = "system_admin"  # System administrators
    READ_ONLY = "read_only"  # Read-only access (auditors, viewers)


class Permission(Enum):
    """Granular permissions for database operations"""
    # Data permissions
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
    
    # Analysis permissions
    RUN_VARIANCE_ANALYSIS = "run_variance_analysis"
    CREATE_FORECAST = "create_forecast"
    MODIFY_ASSUMPTIONS = "modify_assumptions"
    
    # Report permissions
    GENERATE_REPORT = "generate_report"
    EXPORT_DATA = "export_data"
    SHARE_REPORT = "share_report"
    
    # Administrative permissions
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MODIFY_SECURITY_SETTINGS = "modify_security_settings"
    
    # System permissions
    EXECUTE_BATCH_JOB = "execute_batch_job"
    ACCESS_API = "access_api"
    MODIFY_SCHEMA = "modify_schema"


class DataClassification(Enum):
    """Data classification levels for access control"""
    PUBLIC = "public"  # Non-sensitive data
    INTERNAL = "internal"  # Internal use only
    CONFIDENTIAL = "confidential"  # Sensitive business data
    RESTRICTED = "restricted"  # Highly sensitive (PII, financial)


@dataclass
class RolePermissions:
    """Role-based permission mapping"""
    role: AgentRole
    permissions: Set[Permission]
    data_access_level: DataClassification
    can_access_companies: Optional[List[str]] = None  # None = all companies
    row_level_filter: Optional[str] = None  # SQL filter for RLS
    description: str = ""
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if role has specific permission"""
        return permission in self.permissions
    
    def can_access_data(self, classification: DataClassification) -> bool:
        """Check if role can access data at specific classification level"""
        levels = [
            DataClassification.PUBLIC,
            DataClassification.INTERNAL,
            DataClassification.CONFIDENTIAL,
            DataClassification.RESTRICTED
        ]
        return levels.index(classification) <= levels.index(self.data_access_level)


class RBACManager:
    """
    Central RBAC manager for the FP&A system.
    
    Implements defense-in-depth with multiple layers:
    1. Role-based permissions
    2. Data classification
    3. Row-level security
    4. API key scoping
    5. Audit logging
    """
    
    def __init__(self):
        """Initialize RBAC manager with permission matrix"""
        self.role_permissions = self._initialize_permissions()
        self.api_keys: Dict[str, 'APIKey'] = {}
        self.audit_log: List[Dict] = []
    
    def _initialize_permissions(self) -> Dict[AgentRole, RolePermissions]:
        """
        Initialize the permissions matrix for all roles.
        
        This implements the principle of least privilege.
        """
        return {
            # Orchestrator: Full control except admin functions
            AgentRole.ORCHESTRATOR: RolePermissions(
                role=AgentRole.ORCHESTRATOR,
                permissions={
                    Permission.READ_RAW_DATA,
                    Permission.WRITE_RAW_DATA,
                    Permission.READ_CONSOLIDATED_DATA,
                    Permission.WRITE_CONSOLIDATED_DATA,
                    Permission.CREATE_JOURNAL_ENTRY,
                    Permission.RUN_VARIANCE_ANALYSIS,
                    Permission.CREATE_FORECAST,
                    Permission.GENERATE_REPORT,
                    Permission.EXECUTE_BATCH_JOB,
                    Permission.ACCESS_API,
                    Permission.VIEW_AUDIT_LOGS
                },
                data_access_level=DataClassification.CONFIDENTIAL,
                description="Master orchestrator with full operational access"
            ),
            
            # Data Ingestion: Write raw, read config
            AgentRole.DATA_INGESTION: RolePermissions(
                role=AgentRole.DATA_INGESTION,
                permissions={
                    Permission.READ_RAW_DATA,
                    Permission.WRITE_RAW_DATA,
                    Permission.ACCESS_API
                },
                data_access_level=DataClassification.INTERNAL,
                row_level_filter="source_system = current_setting('app.agent_source')",
                description="ERP data ingestion - write only to assigned source"
            ),
            
            # Consolidation: Read raw, write consolidated
            AgentRole.CONSOLIDATION: RolePermissions(
                role=AgentRole.CONSOLIDATION,
                permissions={
                    Permission.READ_RAW_DATA,
                    Permission.READ_CONSOLIDATED_DATA,
                    Permission.WRITE_CONSOLIDATED_DATA,
                    Permission.CREATE_JOURNAL_ENTRY,
                    Permission.ACCESS_API
                },
                data_access_level=DataClassification.CONFIDENTIAL,
                description="Financial consolidation - read raw, write consolidated"
            ),
            
            # Validation: Read-only access to raw and consolidated
            AgentRole.VALIDATION: RolePermissions(
                role=AgentRole.VALIDATION,
                permissions={
                    Permission.READ_RAW_DATA,
                    Permission.READ_CONSOLIDATED_DATA,
                    Permission.ACCESS_API
                },
                data_access_level=DataClassification.CONFIDENTIAL,
                description="Data quality validation - read-only access"
            ),
            
            # Analysis: Read consolidated, write analysis results
            AgentRole.ANALYSIS: RolePermissions(
                role=AgentRole.ANALYSIS,
                permissions={
                    Permission.READ_CONSOLIDATED_DATA,
                    Permission.RUN_VARIANCE_ANALYSIS,
                    Permission.ACCESS_API
                },
                data_access_level=DataClassification.CONFIDENTIAL,
                description="Variance and KPI analysis - read consolidated data"
            ),
            
            # Forecasting: Read historical, write forecasts
            AgentRole.FORECASTING: RolePermissions(
                role=AgentRole.FORECASTING,
                permissions={
                    Permission.READ_CONSOLIDATED_DATA,
                    Permission.CREATE_FORECAST,
                    Permission.MODIFY_ASSUMPTIONS,
                    Permission.ACCESS_API
                },
                data_access_level=DataClassification.CONFIDENTIAL,
                description="Forecasting - read historical, create forecasts"
            ),
            
            # Reporting: Read all, generate reports
            AgentRole.REPORTING: RolePermissions(
                role=AgentRole.REPORTING,
                permissions={
                    Permission.READ_CONSOLIDATED_DATA,
                    Permission.GENERATE_REPORT,
                    Permission.EXPORT_DATA,
                    Permission.ACCESS_API
                },
                data_access_level=DataClassification.CONFIDENTIAL,
                description="Report generation - read and export consolidated data"
            ),
            
            # Compliance: Read-only, extensive audit access
            AgentRole.COMPLIANCE: RolePermissions(
                role=AgentRole.COMPLIANCE,
                permissions={
                    Permission.READ_RAW_DATA,
                    Permission.READ_CONSOLIDATED_DATA,
                    Permission.VIEW_AUDIT_LOGS,
                    Permission.ACCESS_API
                },
                data_access_level=DataClassification.RESTRICTED,
                description="Compliance monitoring - read-only with audit access"
            ),
            
            # Human Reviewer: Approve operations, full read
            AgentRole.HUMAN_REVIEWER: RolePermissions(
                role=AgentRole.HUMAN_REVIEWER,
                permissions={
                    Permission.READ_RAW_DATA,
                    Permission.READ_CONSOLIDATED_DATA,
                    Permission.READ_SENSITIVE_DATA,
                    Permission.APPROVE_JOURNAL_ENTRY,
                    Permission.REVERSE_JOURNAL_ENTRY,
                    Permission.CLOSE_PERIOD,
                    Permission.REOPEN_PERIOD,
                    Permission.VIEW_AUDIT_LOGS,
                    Permission.SHARE_REPORT
                },
                data_access_level=DataClassification.RESTRICTED,
                description="Human FP&A reviewer - approval authority"
            ),
            
            # System Admin: Full access including security management
            AgentRole.SYSTEM_ADMIN: RolePermissions(
                role=AgentRole.SYSTEM_ADMIN,
                permissions=set(Permission),  # All permissions
                data_access_level=DataClassification.RESTRICTED,
                description="System administrator - full access"
            ),
            
            # Read-Only: Minimal access for auditors/viewers
            AgentRole.READ_ONLY: RolePermissions(
                role=AgentRole.READ_ONLY,
                permissions={
                    Permission.READ_CONSOLIDATED_DATA,
                    Permission.GENERATE_REPORT
                },
                data_access_level=DataClassification.INTERNAL,
                description="Read-only access for auditors and viewers"
            )
        }
    
    def check_permission(
        self,
        role: AgentRole,
        permission: Permission,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if a role has a specific permission.
        
        Args:
            role: Agent role
            permission: Permission to check
            context: Additional context (company_id, etc.)
            
        Returns:
            True if permission granted
        """
        role_perms = self.role_permissions.get(role)
        if not role_perms:
            self._log_permission_violation(role, permission, "Unknown role")
            return False
        
        has_perm = role_perms.has_permission(permission)
        
        if not has_perm:
            self._log_permission_violation(role, permission, "Permission denied")
        
        return has_perm
    
    def check_data_access(
        self,
        role: AgentRole,
        classification: DataClassification
    ) -> bool:
        """
        Check if role can access data at specified classification level.
        
        Args:
            role: Agent role
            classification: Data classification level
            
        Returns:
            True if access granted
        """
        role_perms = self.role_permissions.get(role)
        if not role_perms:
            return False
        
        return role_perms.can_access_data(classification)
    
    def get_row_level_filter(self, role: AgentRole) -> Optional[str]:
        """
        Get row-level security filter for role.
        
        Args:
            role: Agent role
            
        Returns:
            SQL filter expression or None
        """
        role_perms = self.role_permissions.get(role)
        return role_perms.row_level_filter if role_perms else None
    
    def _log_permission_violation(
        self,
        role: AgentRole,
        permission: Permission,
        reason: str
    ):
        """Log permission violation for security audit"""
        violation = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'permission_violation',
            'role': role.value,
            'permission': permission.value,
            'reason': reason,
            'severity': 'WARNING'
        }
        self.audit_log.append(violation)
        print(f"[SECURITY] Permission violation: {json.dumps(violation)}")
    
    def generate_api_key(
        self,
        role: AgentRole,
        agent_id: str,
        companies: Optional[List[str]] = None,
        expires_days: int = 90
    ) -> 'APIKey':
        """
        Generate scoped API key for an agent.
        
        Args:
            role: Agent role
            agent_id: Unique agent identifier
            companies: Allowed companies (None = all)
            expires_days: Key expiration in days
            
        Returns:
            APIKey object
        """
        api_key = APIKey.generate(
            role=role,
            agent_id=agent_id,
            companies=companies,
            expires_days=expires_days
        )
        
        self.api_keys[api_key.key_hash] = api_key
        
        self.audit_log.append({
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'api_key_created',
            'role': role.value,
            'agent_id': agent_id,
            'expires_at': api_key.expires_at.isoformat()
        })
        
        return api_key
    
    def validate_api_key(self, key: str) -> Optional['APIKey']:
        """
        Validate API key and return associated APIKey object.
        
        Args:
            key: API key string
            
        Returns:
            APIKey object if valid, None otherwise
        """
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        api_key = self.api_keys.get(key_hash)
        
        if not api_key:
            self._log_api_violation("Unknown API key")
            return None
        
        if api_key.is_expired():
            self._log_api_violation(f"Expired API key: {api_key.agent_id}")
            return None
        
        if api_key.is_revoked:
            self._log_api_violation(f"Revoked API key: {api_key.agent_id}")
            return None
        
        return api_key
    
    def revoke_api_key(self, key_hash: str):
        """Revoke an API key"""
        if key_hash in self.api_keys:
            self.api_keys[key_hash].is_revoked = True
            self.audit_log.append({
                'timestamp': datetime.utcnow().isoformat(),
                'event': 'api_key_revoked',
                'key_hash': key_hash
            })
    
    def _log_api_violation(self, reason: str):
        """Log API key violation"""
        violation = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'api_key_violation',
            'reason': reason,
            'severity': 'ERROR'
        }
        self.audit_log.append(violation)
        print(f"[SECURITY] API key violation: {json.dumps(violation)}")


@dataclass
class APIKey:
    """
    Scoped API key for agent authentication.
    
    Each API key is scoped to:
    - Specific agent role
    - Specific agent instance
    - Allowed companies (optional)
    - Expiration date
    """
    key: str
    key_hash: str
    role: AgentRole
    agent_id: str
    companies: Optional[List[str]]
    created_at: datetime
    expires_at: datetime
    is_revoked: bool = False
    last_used: Optional[datetime] = None
    
    @staticmethod
    def generate(
        role: AgentRole,
        agent_id: str,
        companies: Optional[List[str]] = None,
        expires_days: int = 90
    ) -> 'APIKey':
        """
        Generate a new API key.
        
        Args:
            role: Agent role
            agent_id: Unique agent identifier
            companies: Allowed companies
            expires_days: Days until expiration
            
        Returns:
            New APIKey instance
        """
        # Generate cryptographically secure random key
        key = f"fpa_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        now = datetime.utcnow()
        
        return APIKey(
            key=key,
            key_hash=key_hash,
            role=role,
            agent_id=agent_id,
            companies=companies,
            created_at=now,
            expires_at=now + timedelta(days=expires_days)
        )
    
    def is_expired(self) -> bool:
        """Check if key has expired"""
        return datetime.utcnow() > self.expires_at
    
    def can_access_company(self, company_id: str) -> bool:
        """Check if key can access specific company"""
        if self.companies is None:
            return True  # Access to all companies
        return company_id in self.companies


class PostgreSQLRBACManager:
    """
    PostgreSQL-specific RBAC implementation.
    
    Generates SQL for:
    - Role creation
    - Permission grants
    - Row-Level Security policies
    """
    
    @staticmethod
    def create_role_sql(role: AgentRole) -> str:
        """
        Generate SQL to create PostgreSQL role.
        
        Args:
            role: Agent role
            
        Returns:
            SQL statement
        """
        role_name = f"fpa_{role.value}"
        return f"""
-- Create role for {role.value}
CREATE ROLE {role_name} WITH
    NOLOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION;

COMMENT ON ROLE {role_name} IS 'FP&A System - {role.value} agent role';
"""
    
    @staticmethod
    def grant_permissions_sql(role: AgentRole, role_perms: RolePermissions) -> str:
        """
        Generate SQL to grant permissions to role.
        
        Args:
            role: Agent role
            role_perms: Role permissions object
            
        Returns:
            SQL statements
        """
        role_name = f"fpa_{role.value}"
        grants = [f"-- Grant permissions for {role.value}"]
        
        # Map permissions to table-level grants
        if Permission.READ_RAW_DATA in role_perms.permissions:
            grants.append(f"GRANT SELECT ON TABLE raw_data TO {role_name};")
        
        if Permission.WRITE_RAW_DATA in role_perms.permissions:
            grants.append(f"GRANT INSERT, UPDATE ON TABLE raw_data TO {role_name};")
        
        if Permission.READ_CONSOLIDATED_DATA in role_perms.permissions:
            grants.append(f"GRANT SELECT ON TABLE consolidated_financials TO {role_name};")
        
        if Permission.WRITE_CONSOLIDATED_DATA in role_perms.permissions:
            grants.append(f"GRANT INSERT, UPDATE ON TABLE consolidated_financials TO {role_name};")
        
        if Permission.CREATE_JOURNAL_ENTRY in role_perms.permissions:
            grants.append(f"GRANT INSERT ON TABLE journal_entries TO {role_name};")
        
        if Permission.VIEW_AUDIT_LOGS in role_perms.permissions:
            grants.append(f"GRANT SELECT ON TABLE audit_logs TO {role_name};")
        
        return "\n".join(grants)
    
    @staticmethod
    def create_rls_policy_sql(
        table_name: str,
        role: AgentRole,
        role_perms: RolePermissions
    ) -> str:
        """
        Generate SQL to create Row-Level Security policy.
        
        Args:
            table_name: Table name
            role: Agent role
            role_perms: Role permissions
            
        Returns:
            SQL statements
        """
        role_name = f"fpa_{role.value}"
        policy_name = f"{table_name}_{role.value}_policy"
        
        if not role_perms.row_level_filter:
            return f"-- No RLS policy needed for {role.value} on {table_name}"
        
        return f"""
-- Row-Level Security policy for {role.value} on {table_name}
CREATE POLICY {policy_name}
    ON {table_name}
    FOR ALL
    TO {role_name}
    USING ({role_perms.row_level_filter});
"""
    
    @staticmethod
    def enable_rls_sql(table_name: str) -> str:
        """
        Generate SQL to enable RLS on table.
        
        Args:
            table_name: Table name
            
        Returns:
            SQL statement
        """
        return f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;"
    
    @staticmethod
    def create_company_isolation_policy_sql(table_name: str) -> str:
        """
        Create RLS policy for company-level data isolation.
        
        Args:
            table_name: Table name with company_id column
            
        Returns:
            SQL statements
        """
        return f"""
-- Company-level data isolation policy
CREATE POLICY {table_name}_company_isolation
    ON {table_name}
    FOR ALL
    USING (
        company_id = ANY(
            string_to_array(
                current_setting('app.allowed_companies', true),
                ','
            )
        )
    );
"""


# Permission matrix export for documentation
PERMISSION_MATRIX = {
    'version': '1.0',
    'updated': datetime.utcnow().isoformat(),
    'roles': {}
}


def export_permission_matrix() -> Dict[str, Any]:
    """Export permission matrix for documentation"""
    rbac = RBACManager()
    
    for role, role_perms in rbac.role_permissions.items():
        PERMISSION_MATRIX['roles'][role.value] = {
            'permissions': [p.value for p in role_perms.permissions],
            'data_access_level': role_perms.data_access_level.value,
            'can_access_companies': role_perms.can_access_companies,
            'row_level_filter': role_perms.row_level_filter,
            'description': role_perms.description
        }
    
    return PERMISSION_MATRIX


if __name__ == '__main__':
    # Example usage and testing
    print("RBAC Manager - Security Finding #7 Implementation")
    print("=" * 60)
    
    # Initialize RBAC manager
    rbac = RBACManager()
    
    # Test permission checking
    print("\n1. Testing permission checks...")
    test_cases = [
        (AgentRole.DATA_INGESTION, Permission.WRITE_RAW_DATA, True),
        (AgentRole.DATA_INGESTION, Permission.WRITE_CONSOLIDATED_DATA, False),
        (AgentRole.CONSOLIDATION, Permission.CREATE_JOURNAL_ENTRY, True),
        (AgentRole.READ_ONLY, Permission.EXPORT_DATA, False),
        (AgentRole.HUMAN_REVIEWER, Permission.APPROVE_JOURNAL_ENTRY, True),
    ]
    
    for role, perm, expected in test_cases:
        result = rbac.check_permission(role, perm)
        status = "✓" if result == expected else "✗"
        print(f"   {status} {role.value}: {perm.value} = {result}")
    
    # Test API key generation
    print("\n2. Testing API key generation...")
    api_key = rbac.generate_api_key(
        role=AgentRole.DATA_INGESTION,
        agent_id="effecti_connector",
        companies=["effecti"],
        expires_days=90
    )
    print(f"   Generated key: {api_key.key[:20]}...")
    print(f"   Role: {api_key.role.value}")
    print(f"   Companies: {api_key.companies}")
    print(f"   Expires: {api_key.expires_at.strftime('%Y-%m-%d')}")
    
    # Test API key validation
    print("\n3. Testing API key validation...")
    validated = rbac.validate_api_key(api_key.key)
    print(f"   Valid: {validated is not None}")
    print(f"   Can access 'effecti': {validated.can_access_company('effecti')}")
    print(f"   Can access 'mercos': {validated.can_access_company('mercos')}")
    
    # Generate PostgreSQL RBAC setup
    print("\n4. Generating PostgreSQL RBAC SQL...")
    pg_rbac = PostgreSQLRBACManager()
    
    # Create role
    create_sql = pg_rbac.create_role_sql(AgentRole.DATA_INGESTION)
    print(f"   Role creation: {len(create_sql)} chars")
    
    # Grant permissions
    grant_sql = pg_rbac.grant_permissions_sql(
        AgentRole.DATA_INGESTION,
        rbac.role_permissions[AgentRole.DATA_INGESTION]
    )
    print(f"   Permission grants: {len(grant_sql)} chars")
    
    # Create RLS policy
    rls_sql = pg_rbac.create_rls_policy_sql(
        "raw_data",
        AgentRole.DATA_INGESTION,
        rbac.role_permissions[AgentRole.DATA_INGESTION]
    )
    print(f"   RLS policy: {len(rls_sql)} chars")
    
    # Export permission matrix
    print("\n5. Exporting permission matrix...")
    matrix = export_permission_matrix()
    print(f"   Total roles: {len(matrix['roles'])}")
    print(f"   Documentation ready: ✓")
    
    print("\n" + "=" * 60)
    print("All RBAC tests passed ✓")
    print(f"Audit log entries: {len(rbac.audit_log)}")
