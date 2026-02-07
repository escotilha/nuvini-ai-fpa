#!/usr/bin/env python3
"""
Security Implementation Verification Script

Verifies all security implementations for findings #6, #7, #8
Run this script to confirm everything is working correctly.
"""

import sys
sys.path.insert(0, '/Volumes/AI/Code/FPA/src')

from datetime import datetime


def print_header(title):
    """Print section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_success(message):
    """Print success message"""
    print(f"  ✅ {message}")


def print_error(message):
    """Print error message"""
    print(f"  ❌ {message}")


def verify_encryption():
    """Verify Finding #6: Data Encryption implementation"""
    print_header("Finding #6: Data Encryption Verification")
    
    try:
        from core.encryption import (
            EncryptionManager,
            EncryptionKeyType,
            SensitiveFieldType,
            TLSConfigManager,
            PostgreSQLEncryption,
            ENCRYPTION_STANDARDS
        )
        print_success("Encryption module imported successfully")
        
        # Test field encryption
        enc_manager = EncryptionManager()
        test_value = 1250000.50
        
        encrypted = enc_manager.encrypt_field(
            test_value,
            SensitiveFieldType.REVENUE
        )
        print_success(f"Field encryption successful: {encrypted[:30]}...")
        
        decrypted = float(enc_manager.decrypt_field(
            encrypted,
            SensitiveFieldType.REVENUE
        ))
        
        if abs(decrypted - test_value) < 0.01:
            print_success(f"Field decryption verified: {decrypted}")
        else:
            print_error(f"Decryption mismatch: {decrypted} != {test_value}")
            return False
        
        # Test TLS configuration
        ssl_context = TLSConfigManager.get_secure_ssl_context()
        print_success(f"TLS context created: {ssl_context.minimum_version}")
        
        # Test PostgreSQL encryption
        conn_str = PostgreSQLEncryption.get_connection_string(
            host='localhost',
            port=5432,
            database='test',
            user='test',
            password='test',
            require_ssl=True
        )
        
        if 'sslmode=require' in conn_str:
            print_success("PostgreSQL SSL enforcement verified")
        else:
            print_error("PostgreSQL SSL not enforced")
            return False
        
        # Verify standards
        if ENCRYPTION_STANDARDS['algorithm'] == 'AES-256-GCM':
            print_success(f"Encryption standards verified: {ENCRYPTION_STANDARDS['algorithm']}")
        else:
            print_error(f"Invalid encryption standard: {ENCRYPTION_STANDARDS['algorithm']}")
            return False
        
        print_success("All encryption tests passed")
        return True
        
    except Exception as e:
        print_error(f"Encryption verification failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def verify_access_control():
    """Verify Finding #7: RBAC implementation"""
    print_header("Finding #7: RBAC Verification")
    
    try:
        from core.access_control import (
            RBACManager,
            AgentRole,
            Permission,
            DataClassification,
            PostgreSQLRBACManager
        )
        print_success("Access control module imported successfully")
        
        rbac = RBACManager()
        
        # Test permission checks
        test_cases = [
            (AgentRole.DATA_INGESTION, Permission.WRITE_RAW_DATA, True),
            (AgentRole.DATA_INGESTION, Permission.WRITE_CONSOLIDATED_DATA, False),
            (AgentRole.READ_ONLY, Permission.WRITE_RAW_DATA, False),
            (AgentRole.SYSTEM_ADMIN, Permission.MODIFY_SCHEMA, True),
        ]
        
        all_passed = True
        for role, permission, expected in test_cases:
            result = rbac.check_permission(role, permission)
            if result == expected:
                print_success(f"Permission check: {role.value} -> {permission.value} = {result}")
            else:
                print_error(f"Permission check failed: {role.value} -> {permission.value} = {result} (expected {expected})")
                all_passed = False
        
        if not all_passed:
            return False
        
        # Test API key generation
        api_key = rbac.generate_api_key(
            role=AgentRole.DATA_INGESTION,
            agent_id='test_agent',
            companies=['effecti'],
            expires_days=90
        )
        
        if api_key.key.startswith('fpa_'):
            print_success(f"API key generated: {api_key.key[:20]}...")
        else:
            print_error("API key generation failed")
            return False
        
        # Test API key validation
        validated = rbac.validate_api_key(api_key.key)
        
        if validated and validated.agent_id == 'test_agent':
            print_success("API key validation successful")
        else:
            print_error("API key validation failed")
            return False
        
        # Test company scoping
        if validated.can_access_company('effecti') and not validated.can_access_company('mercos'):
            print_success("Company scoping verified")
        else:
            print_error("Company scoping failed")
            return False
        
        # Test PostgreSQL RBAC
        pg_rbac = PostgreSQLRBACManager()
        create_sql = pg_rbac.create_role_sql(AgentRole.DATA_INGESTION)
        
        if 'CREATE ROLE' in create_sql and 'fpa_data_ingestion' in create_sql:
            print_success("PostgreSQL RBAC SQL generation verified")
        else:
            print_error("PostgreSQL RBAC SQL generation failed")
            return False
        
        print_success("All RBAC tests passed")
        return True
        
    except Exception as e:
        print_error(f"RBAC verification failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def verify_human_oversight():
    """Verify Finding #8: Human Oversight implementation"""
    print_header("Finding #8: Human Oversight Verification")
    
    try:
        from core.human_oversight import (
            HumanOversightManager,
            RiskLevel,
            ReviewCategory,
            EscalationLevel,
            ConfidenceScoringEngine
        )
        print_success("Human oversight module imported successfully")
        
        oversight = HumanOversightManager()
        
        # Test low-risk transaction
        low_risk_tx = {
            'id': 'TX001',
            'amount': 5000,
            'account': 'office_supplies',
            'is_intercompany': False,
            'is_manual_adjustment': False
        }
        
        context = {
            'company_size': 'medium',
            'data_quality_score': 0.98,
            'historical_data': [
                {'account': 'office_supplies', 'amount': 4900}
            ],
            'budget': {'office_supplies': 5000},
            'agent_id': 'test_agent'
        }
        
        confidence, review = oversight.evaluate_transaction(low_risk_tx, context)
        
        if confidence.risk_level == RiskLevel.GREEN:
            print_success(f"Low-risk transaction scored correctly: {confidence.confidence_percentage:.1f}% (Green)")
        else:
            print_error(f"Low-risk transaction scored incorrectly: {confidence.risk_level.value}")
        
        # Test high-risk transaction
        high_risk_tx = {
            'id': 'TX002',
            'amount': 1500000,
            'account': 'intercompany_revenue',
            'is_intercompany': True,
            'is_manual_adjustment': True
        }
        
        context['historical_data'] = []
        
        confidence, review = oversight.evaluate_transaction(high_risk_tx, context)
        
        if confidence.risk_level == RiskLevel.RED:
            print_success(f"High-risk transaction scored correctly: {confidence.confidence_percentage:.1f}% (Red)")
        else:
            print_error(f"High-risk transaction scored incorrectly: {confidence.risk_level.value}")
            return False
        
        if review and review.required_reviewers >= 2:
            print_success(f"Four-eyes principle enforced: {review.required_reviewers} reviewers required")
        else:
            print_error("Four-eyes principle not enforced")
            return False
        
        # Test review submission
        if review:
            oversight.submit_review(
                review.request_id,
                'reviewer_001',
                'approved',
                'Test review 1'
            )
            
            updated = oversight.submit_review(
                review.request_id,
                'reviewer_002',
                'approved',
                'Test review 2'
            )
            
            if updated.is_complete() and updated.status == 'approved':
                print_success("Review workflow completed successfully")
            else:
                print_error("Review workflow failed")
                return False
        
        # Test mandatory review
        period_close_tx = {
            'id': 'TX003',
            'amount': 10000,
            'is_period_close': True
        }
        
        context['historical_data'] = [{'account': 'test', 'amount': 10000}]
        
        confidence, review = oversight.evaluate_transaction(period_close_tx, context)
        
        if review and review.category == ReviewCategory.PERIOD_CLOSE:
            print_success("Mandatory review category detected: period_close")
        else:
            print_error("Mandatory review not triggered")
            return False
        
        print_success("All human oversight tests passed")
        return True
        
    except Exception as e:
        print_error(f"Human oversight verification failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def verify_configuration():
    """Verify security policy configuration"""
    print_header("Security Policy Configuration Verification")
    
    try:
        import yaml
        
        with open('/Volumes/AI/Code/FPA/config/security_policy.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        print_success("Security policy YAML loaded successfully")
        
        # Verify encryption config
        if config['encryption']['standards']['algorithm'] == 'AES-256-GCM':
            print_success("Encryption algorithm configured: AES-256-GCM")
        else:
            print_error(f"Invalid encryption algorithm: {config['encryption']['standards']['algorithm']}")
            return False
        
        # Verify RBAC config
        if 'orchestrator' in config['rbac']['roles']:
            print_success(f"RBAC roles configured: {len(config['rbac']['roles'])} roles")
        else:
            print_error("RBAC roles not configured")
            return False
        
        # Verify oversight config
        if config['human_oversight']['confidence_thresholds']['green'] == 0.80:
            print_success("Confidence thresholds configured correctly")
        else:
            print_error("Confidence thresholds misconfigured")
            return False
        
        print_success("Configuration verification passed")
        return True
        
    except Exception as e:
        print_error(f"Configuration verification failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification tests"""
    print("\n" + "=" * 70)
    print("  AI FP&A SECURITY IMPLEMENTATION VERIFICATION")
    print("  Findings #6, #7, #8")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)
    
    results = {
        'Encryption (Finding #6)': verify_encryption(),
        'RBAC (Finding #7)': verify_access_control(),
        'Human Oversight (Finding #8)': verify_human_oversight(),
        'Configuration': verify_configuration()
    }
    
    print_header("VERIFICATION SUMMARY")
    
    for test, passed in results.items():
        if passed:
            print_success(f"{test}: PASSED")
        else:
            print_error(f"{test}: FAILED")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 70)
    if all_passed:
        print("  ✅ ALL VERIFICATIONS PASSED")
        print("  Security implementation is ready for deployment")
    else:
        print("  ❌ SOME VERIFICATIONS FAILED")
        print("  Please review the errors above")
    print("=" * 70 + "\n")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
