"""
Test suite for access control module (Finding #7)

Tests:
- Role permissions
- Permission checking
- Data classification
- API key generation and validation
- Row-level security
- PostgreSQL RBAC
"""

import unittest
import hashlib
from datetime import datetime, timedelta

# Add src to path
import sys
sys.path.insert(0, '/Volumes/AI/Code/FPA/src')

from core.access_control import (
    AgentRole,
    Permission,
    DataClassification,
    RolePermissions,
    RBACManager,
    APIKey,
    PostgreSQLRBACManager,
    export_permission_matrix
)


class TestRolePermissions(unittest.TestCase):
    """Test role permission objects"""
    
    def test_has_permission(self):
        """Test permission checking"""
        role_perms = RolePermissions(
            role=AgentRole.DATA_INGESTION,
            permissions={Permission.READ_RAW_DATA, Permission.WRITE_RAW_DATA},
            data_access_level=DataClassification.INTERNAL
        )
        
        self.assertTrue(role_perms.has_permission(Permission.READ_RAW_DATA))
        self.assertTrue(role_perms.has_permission(Permission.WRITE_RAW_DATA))
        self.assertFalse(role_perms.has_permission(Permission.CLOSE_PERIOD))
    
    def test_data_access_levels(self):
        """Test data classification access"""
        # Internal level can access public and internal
        role_perms = RolePermissions(
            role=AgentRole.DATA_INGESTION,
            permissions=set(),
            data_access_level=DataClassification.INTERNAL
        )
        
        self.assertTrue(role_perms.can_access_data(DataClassification.PUBLIC))
        self.assertTrue(role_perms.can_access_data(DataClassification.INTERNAL))
        self.assertFalse(role_perms.can_access_data(DataClassification.CONFIDENTIAL))
        self.assertFalse(role_perms.can_access_data(DataClassification.RESTRICTED))
        
        # Restricted level can access all
        admin_perms = RolePermissions(
            role=AgentRole.SYSTEM_ADMIN,
            permissions=set(),
            data_access_level=DataClassification.RESTRICTED
        )
        
        self.assertTrue(admin_perms.can_access_data(DataClassification.PUBLIC))
        self.assertTrue(admin_perms.can_access_data(DataClassification.INTERNAL))
        self.assertTrue(admin_perms.can_access_data(DataClassification.CONFIDENTIAL))
        self.assertTrue(admin_perms.can_access_data(DataClassification.RESTRICTED))


class TestRBACManager(unittest.TestCase):
    """Test RBAC manager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.rbac = RBACManager()
    
    def test_all_roles_defined(self):
        """Test that all agent roles have permissions defined"""
        for role in AgentRole:
            self.assertIn(role, self.rbac.role_permissions)
    
    def test_orchestrator_permissions(self):
        """Test orchestrator has broad operational permissions"""
        self.assertTrue(
            self.rbac.check_permission(AgentRole.ORCHESTRATOR, Permission.READ_RAW_DATA)
        )
        self.assertTrue(
            self.rbac.check_permission(AgentRole.ORCHESTRATOR, Permission.WRITE_RAW_DATA)
        )
        self.assertTrue(
            self.rbac.check_permission(AgentRole.ORCHESTRATOR, Permission.CREATE_JOURNAL_ENTRY)
        )
        
        # But not admin permissions
        self.assertFalse(
            self.rbac.check_permission(AgentRole.ORCHESTRATOR, Permission.MODIFY_SCHEMA)
        )
    
    def test_data_ingestion_permissions(self):
        """Test data ingestion agent has limited write permissions"""
        self.assertTrue(
            self.rbac.check_permission(AgentRole.DATA_INGESTION, Permission.WRITE_RAW_DATA)
        )
        
        # Should not be able to write consolidated data
        self.assertFalse(
            self.rbac.check_permission(AgentRole.DATA_INGESTION, Permission.WRITE_CONSOLIDATED_DATA)
        )
        
        # Should not be able to close periods
        self.assertFalse(
            self.rbac.check_permission(AgentRole.DATA_INGESTION, Permission.CLOSE_PERIOD)
        )
    
    def test_validation_read_only(self):
        """Test validation agent has read-only access"""
        self.assertTrue(
            self.rbac.check_permission(AgentRole.VALIDATION, Permission.READ_RAW_DATA)
        )
        self.assertTrue(
            self.rbac.check_permission(AgentRole.VALIDATION, Permission.READ_CONSOLIDATED_DATA)
        )
        
        # Should not be able to write
        self.assertFalse(
            self.rbac.check_permission(AgentRole.VALIDATION, Permission.WRITE_RAW_DATA)
        )
        self.assertFalse(
            self.rbac.check_permission(AgentRole.VALIDATION, Permission.WRITE_CONSOLIDATED_DATA)
        )
    
    def test_human_reviewer_approval_permissions(self):
        """Test human reviewer has approval authority"""
        self.assertTrue(
            self.rbac.check_permission(AgentRole.HUMAN_REVIEWER, Permission.APPROVE_JOURNAL_ENTRY)
        )
        self.assertTrue(
            self.rbac.check_permission(AgentRole.HUMAN_REVIEWER, Permission.CLOSE_PERIOD)
        )
        self.assertTrue(
            self.rbac.check_permission(AgentRole.HUMAN_REVIEWER, Permission.REOPEN_PERIOD)
        )
    
    def test_system_admin_all_permissions(self):
        """Test system admin has all permissions"""
        for permission in Permission:
            self.assertTrue(
                self.rbac.check_permission(AgentRole.SYSTEM_ADMIN, permission)
            )
    
    def test_read_only_minimal_permissions(self):
        """Test read-only has minimal permissions"""
        self.assertTrue(
            self.rbac.check_permission(AgentRole.READ_ONLY, Permission.READ_CONSOLIDATED_DATA)
        )
        
        # Should not have any write permissions
        self.assertFalse(
            self.rbac.check_permission(AgentRole.READ_ONLY, Permission.WRITE_RAW_DATA)
        )
        self.assertFalse(
            self.rbac.check_permission(AgentRole.READ_ONLY, Permission.CREATE_JOURNAL_ENTRY)
        )
    
    def test_permission_violation_logging(self):
        """Test that permission violations are logged"""
        initial_log_count = len(self.rbac.audit_log)
        
        # Attempt unauthorized access
        self.rbac.check_permission(AgentRole.READ_ONLY, Permission.MODIFY_SCHEMA)
        
        # Should have logged the violation
        self.assertEqual(len(self.rbac.audit_log), initial_log_count + 1)
        
        last_log = self.rbac.audit_log[-1]
        self.assertEqual(last_log['event'], 'permission_violation')
    
    def test_row_level_filter(self):
        """Test row-level security filter retrieval"""
        # Data ingestion should have RLS filter
        filter_sql = self.rbac.get_row_level_filter(AgentRole.DATA_INGESTION)
        self.assertIsNotNone(filter_sql)
        self.assertIn('source_system', filter_sql)
        
        # Orchestrator should not have RLS filter (access to all)
        filter_sql = self.rbac.get_row_level_filter(AgentRole.ORCHESTRATOR)
        self.assertIsNone(filter_sql)


class TestAPIKey(unittest.TestCase):
    """Test API key functionality"""
    
    def test_api_key_generation(self):
        """Test generating API keys"""
        api_key = APIKey.generate(
            role=AgentRole.DATA_INGESTION,
            agent_id='test_agent',
            companies=['effecti'],
            expires_days=90
        )
        
        # Key should start with prefix
        self.assertTrue(api_key.key.startswith('fpa_'))
        
        # Key hash should be SHA256
        expected_hash = hashlib.sha256(api_key.key.encode()).hexdigest()
        self.assertEqual(api_key.key_hash, expected_hash)
        
        # Should have correct role
        self.assertEqual(api_key.role, AgentRole.DATA_INGESTION)
        
        # Should have correct companies
        self.assertEqual(api_key.companies, ['effecti'])
        
        # Should expire in 90 days
        expected_expiry = datetime.utcnow() + timedelta(days=90)
        self.assertAlmostEqual(
            api_key.expires_at.timestamp(),
            expected_expiry.timestamp(),
            delta=10  # 10 seconds tolerance
        )
    
    def test_api_key_expiration(self):
        """Test API key expiration checking"""
        # Create expired key
        expired_key = APIKey.generate(
            role=AgentRole.DATA_INGESTION,
            agent_id='test_agent',
            expires_days=-1  # Already expired
        )
        
        self.assertTrue(expired_key.is_expired())
        
        # Create valid key
        valid_key = APIKey.generate(
            role=AgentRole.DATA_INGESTION,
            agent_id='test_agent',
            expires_days=90
        )
        
        self.assertFalse(valid_key.is_expired())
    
    def test_api_key_company_scoping(self):
        """Test API key company access scoping"""
        # Scoped to specific companies
        scoped_key = APIKey.generate(
            role=AgentRole.DATA_INGESTION,
            agent_id='test_agent',
            companies=['effecti', 'mercos']
        )
        
        self.assertTrue(scoped_key.can_access_company('effecti'))
        self.assertTrue(scoped_key.can_access_company('mercos'))
        self.assertFalse(scoped_key.can_access_company('datahub'))
        
        # Not scoped (access to all)
        unscoped_key = APIKey.generate(
            role=AgentRole.ORCHESTRATOR,
            agent_id='orchestrator',
            companies=None
        )
        
        self.assertTrue(unscoped_key.can_access_company('effecti'))
        self.assertTrue(unscoped_key.can_access_company('mercos'))
        self.assertTrue(unscoped_key.can_access_company('datahub'))


class TestAPIKeyManagement(unittest.TestCase):
    """Test API key management in RBAC manager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.rbac = RBACManager()
    
    def test_generate_and_validate_api_key(self):
        """Test API key generation and validation"""
        # Generate key
        api_key = self.rbac.generate_api_key(
            role=AgentRole.DATA_INGESTION,
            agent_id='effecti_connector',
            companies=['effecti']
        )
        
        # Validate key
        validated = self.rbac.validate_api_key(api_key.key)
        
        self.assertIsNotNone(validated)
        self.assertEqual(validated.role, AgentRole.DATA_INGESTION)
        self.assertEqual(validated.agent_id, 'effecti_connector')
    
    def test_invalid_api_key(self):
        """Test validation fails for invalid key"""
        validated = self.rbac.validate_api_key('invalid_key')
        
        self.assertIsNone(validated)
    
    def test_expired_api_key(self):
        """Test validation fails for expired key"""
        # Generate expired key
        api_key = self.rbac.generate_api_key(
            role=AgentRole.DATA_INGESTION,
            agent_id='test_agent',
            expires_days=-1
        )
        
        # Validation should fail
        validated = self.rbac.validate_api_key(api_key.key)
        
        self.assertIsNone(validated)
    
    def test_revoked_api_key(self):
        """Test validation fails for revoked key"""
        # Generate key
        api_key = self.rbac.generate_api_key(
            role=AgentRole.DATA_INGESTION,
            agent_id='test_agent'
        )
        
        # Revoke key
        self.rbac.revoke_api_key(api_key.key_hash)
        
        # Validation should fail
        validated = self.rbac.validate_api_key(api_key.key)
        
        self.assertIsNone(validated)


class TestPostgreSQLRBACManager(unittest.TestCase):
    """Test PostgreSQL RBAC SQL generation"""
    
    def test_create_role_sql(self):
        """Test SQL generation for role creation"""
        sql = PostgreSQLRBACManager.create_role_sql(AgentRole.DATA_INGESTION)
        
        self.assertIn('CREATE ROLE', sql)
        self.assertIn('fpa_data_ingestion', sql)
        self.assertIn('NOLOGIN', sql)
        self.assertIn('NOSUPERUSER', sql)
    
    def test_grant_permissions_sql(self):
        """Test SQL generation for permission grants"""
        rbac = RBACManager()
        role_perms = rbac.role_permissions[AgentRole.DATA_INGESTION]
        
        sql = PostgreSQLRBACManager.grant_permissions_sql(
            AgentRole.DATA_INGESTION,
            role_perms
        )
        
        self.assertIn('GRANT', sql)
        self.assertIn('fpa_data_ingestion', sql)
    
    def test_rls_policy_sql(self):
        """Test SQL generation for RLS policy"""
        rbac = RBACManager()
        role_perms = rbac.role_permissions[AgentRole.DATA_INGESTION]
        
        sql = PostgreSQLRBACManager.create_rls_policy_sql(
            'raw_data',
            AgentRole.DATA_INGESTION,
            role_perms
        )
        
        self.assertIn('CREATE POLICY', sql)
        self.assertIn('raw_data', sql)
        self.assertIn('fpa_data_ingestion', sql)
    
    def test_enable_rls_sql(self):
        """Test SQL generation for enabling RLS"""
        sql = PostgreSQLRBACManager.enable_rls_sql('raw_data')
        
        self.assertIn('ALTER TABLE', sql)
        self.assertIn('raw_data', sql)
        self.assertIn('ENABLE ROW LEVEL SECURITY', sql)
    
    def test_company_isolation_policy_sql(self):
        """Test SQL generation for company isolation"""
        sql = PostgreSQLRBACManager.create_company_isolation_policy_sql('raw_data')
        
        self.assertIn('CREATE POLICY', sql)
        self.assertIn('company_id', sql)
        self.assertIn('app.allowed_companies', sql)


class TestPermissionMatrix(unittest.TestCase):
    """Test permission matrix export"""
    
    def test_export_permission_matrix(self):
        """Test exporting permission matrix"""
        matrix = export_permission_matrix()
        
        # Should have version and timestamp
        self.assertIn('version', matrix)
        self.assertIn('updated', matrix)
        
        # Should have all roles
        self.assertIn('roles', matrix)
        
        for role in AgentRole:
            self.assertIn(role.value, matrix['roles'])
            
            role_data = matrix['roles'][role.value]
            self.assertIn('permissions', role_data)
            self.assertIn('data_access_level', role_data)
            self.assertIn('description', role_data)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
