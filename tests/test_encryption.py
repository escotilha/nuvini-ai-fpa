"""
Test suite for encryption module (Finding #6)

Tests:
- Field encryption/decryption
- Key generation and rotation
- TLS configuration
- PostgreSQL encryption
- S3 encryption
- Backup encryption
"""

import unittest
import os
import tempfile
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add src to path
import sys
sys.path.insert(0, '/Volumes/AI/Code/FPA/src')

from core.encryption import (
    EncryptionManager,
    EncryptionKeyType,
    SensitiveFieldType,
    TLSConfigManager,
    PostgreSQLEncryption,
    S3EncryptionManager,
    BackupEncryptionManager,
    ENCRYPTION_STANDARDS
)


class TestEncryptionManager(unittest.TestCase):
    """Test EncryptionManager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.encryption_manager = EncryptionManager()
    
    def test_field_encryption_decryption(self):
        """Test encrypting and decrypting sensitive fields"""
        # Test with string
        original = "1250000.50"
        encrypted = self.encryption_manager.encrypt_field(
            original,
            SensitiveFieldType.REVENUE
        )
        
        # Encrypted should be different
        self.assertNotEqual(original, encrypted)
        
        # Should be base64 encoded
        import base64
        try:
            base64.b64decode(encrypted)
            is_base64 = True
        except:
            is_base64 = False
        self.assertTrue(is_base64)
        
        # Decrypt should return original
        decrypted = self.encryption_manager.decrypt_field(
            encrypted,
            SensitiveFieldType.REVENUE
        )
        self.assertEqual(original, decrypted)
    
    def test_field_encryption_with_numbers(self):
        """Test encrypting numeric values"""
        original = 1250000.50
        encrypted = self.encryption_manager.encrypt_field(
            original,
            SensitiveFieldType.REVENUE
        )
        
        decrypted = float(self.encryption_manager.decrypt_field(
            encrypted,
            SensitiveFieldType.REVENUE
        ))
        
        self.assertAlmostEqual(original, decrypted, places=2)
    
    def test_different_field_types(self):
        """Test that different field types use different keys"""
        value = "test_value"
        
        encrypted_revenue = self.encryption_manager.encrypt_field(
            value,
            SensitiveFieldType.REVENUE
        )
        
        encrypted_customer = self.encryption_manager.encrypt_field(
            value,
            SensitiveFieldType.CUSTOMER_DATA
        )
        
        # Different field types should produce different ciphertexts
        # (even with same plaintext, due to different keys and IVs)
        self.assertNotEqual(encrypted_revenue, encrypted_customer)
    
    def test_key_rotation(self):
        """Test key rotation functionality"""
        # Encrypt data
        original = "sensitive_data"
        encrypted = self.encryption_manager.encrypt_field(
            original,
            SensitiveFieldType.REVENUE
        )
        
        # Rotate keys
        self.encryption_manager.rotate_keys(SensitiveFieldType.REVENUE)
        
        # Old encrypted data should still decrypt (backward compatibility)
        decrypted = self.encryption_manager.decrypt_field(
            encrypted,
            SensitiveFieldType.REVENUE
        )
        self.assertEqual(original, decrypted)
    
    def test_data_key_generation(self):
        """Test generating data encryption keys"""
        plaintext_key, encrypted_key = self.encryption_manager.generate_data_key(
            EncryptionKeyType.DATA
        )
        
        # Keys should be bytes
        self.assertIsInstance(plaintext_key, bytes)
        self.assertIsInstance(encrypted_key, bytes)
        
        # Keys should not be empty
        self.assertGreater(len(plaintext_key), 0)
        self.assertGreater(len(encrypted_key), 0)


class TestTLSConfigManager(unittest.TestCase):
    """Test TLS configuration"""
    
    def test_ssl_context_creation(self):
        """Test creating secure SSL context"""
        context = TLSConfigManager.get_secure_ssl_context()
        
        # Check TLS version requirements
        import ssl
        self.assertGreaterEqual(
            context.minimum_version,
            ssl.TLSVersion.TLSv1_2
        )
        
        # Check that verification is enabled
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
    
    def test_requests_session(self):
        """Test creating requests session with TLS config"""
        session = TLSConfigManager.get_requests_session()
        
        # Should have custom adapter mounted
        self.assertIn('https://', session.adapters)


class TestPostgreSQLEncryption(unittest.TestCase):
    """Test PostgreSQL encryption utilities"""
    
    def test_connection_string_with_ssl(self):
        """Test generating connection string with SSL"""
        conn_str = PostgreSQLEncryption.get_connection_string(
            host='localhost',
            port=5432,
            database='test_db',
            user='test_user',
            password='test_pass',
            require_ssl=True
        )
        
        # Should include SSL mode
        self.assertIn('sslmode=require', conn_str)
    
    def test_connection_string_without_ssl(self):
        """Test generating connection string without SSL"""
        conn_str = PostgreSQLEncryption.get_connection_string(
            host='localhost',
            port=5432,
            database='test_db',
            user='test_user',
            password='test_pass',
            require_ssl=False
        )
        
        # Should not include SSL mode
        self.assertNotIn('sslmode', conn_str)
    
    def test_encryption_extension_sql(self):
        """Test SQL for enabling pgcrypto"""
        sql = PostgreSQLEncryption.create_encryption_extension_sql()
        
        self.assertIn('CREATE EXTENSION', sql)
        self.assertIn('pgcrypto', sql)
    
    def test_encrypt_column_sql(self):
        """Test SQL generation for column encryption"""
        sql = PostgreSQLEncryption.encrypt_column_sql(
            'revenue',
            '1000000',
            'encryption_key'
        )
        
        self.assertIn('pgp_sym_encrypt', sql)
    
    def test_decrypt_column_sql(self):
        """Test SQL generation for column decryption"""
        sql = PostgreSQLEncryption.decrypt_column_sql(
            'revenue',
            'encryption_key'
        )
        
        self.assertIn('pgp_sym_decrypt', sql)


class TestS3EncryptionManager(unittest.TestCase):
    """Test S3 encryption manager"""
    
    @patch('boto3.client')
    def setUp(self, mock_boto3):
        """Set up with mocked boto3"""
        self.mock_s3 = MagicMock()
        mock_boto3.return_value = self.mock_s3
        
        os.environ['AWS_KMS_S3_KEY_ID'] = 'test-key-id'
        os.environ['S3_BACKUP_BUCKET'] = 'test-bucket'
        
        self.s3_manager = S3EncryptionManager()
    
    def test_bucket_encryption_config(self):
        """Test configuring bucket encryption"""
        self.s3_manager.configure_bucket_encryption()
        
        # Should call put_bucket_encryption
        self.mock_s3.put_bucket_encryption.assert_called_once()
        
        # Check encryption configuration
        call_args = self.mock_s3.put_bucket_encryption.call_args
        config = call_args[1]['ServerSideEncryptionConfiguration']
        
        self.assertEqual(
            config['Rules'][0]['ApplyServerSideEncryptionByDefault']['SSEAlgorithm'],
            'aws:kms'
        )
    
    def test_enable_versioning(self):
        """Test enabling bucket versioning"""
        self.s3_manager.enable_versioning()
        
        # Should call put_bucket_versioning
        self.mock_s3.put_bucket_versioning.assert_called_once()
        
        call_args = self.mock_s3.put_bucket_versioning.call_args
        self.assertEqual(
            call_args[1]['VersioningConfiguration']['Status'],
            'Enabled'
        )
    
    def test_lifecycle_policy(self):
        """Test configuring lifecycle policy"""
        self.s3_manager.configure_lifecycle_policy(
            transition_days=90,
            expiration_days=2555
        )
        
        # Should call put_bucket_lifecycle_configuration
        self.mock_s3.put_bucket_lifecycle_configuration.assert_called_once()
        
        call_args = self.mock_s3.put_bucket_lifecycle_configuration.call_args
        lifecycle = call_args[1]['LifecycleConfiguration']
        
        # Check transition to Glacier
        self.assertEqual(
            lifecycle['Rules'][0]['Transitions'][0]['Days'],
            90
        )
        
        # Check expiration (7 years)
        self.assertEqual(
            lifecycle['Rules'][0]['Expiration']['Days'],
            2555
        )


class TestBackupEncryptionManager(unittest.TestCase):
    """Test backup encryption"""
    
    @patch('boto3.client')
    def setUp(self, mock_boto3):
        """Set up with mocked services"""
        self.mock_s3 = MagicMock()
        mock_boto3.return_value = self.mock_s3
        
        os.environ['AWS_KMS_S3_KEY_ID'] = 'test-key-id'
        os.environ['S3_BACKUP_BUCKET'] = 'test-bucket'
        
        self.encryption_manager = EncryptionManager()
        self.s3_manager = S3EncryptionManager()
        self.backup_manager = BackupEncryptionManager(
            self.encryption_manager,
            self.s3_manager
        )
    
    def test_create_encrypted_backup(self):
        """Test creating encrypted backup"""
        test_data = {
            'company': 'Effecti',
            'period': '2026-01',
            'revenue': 1250000,
            'expenses': 980000
        }
        
        s3_key = self.backup_manager.create_encrypted_backup(
            test_data,
            'test_backup',
            {'test': 'metadata'}
        )
        
        # Should generate S3 key with date path
        self.assertIn('backups/', s3_key)
        self.assertIn('.enc', s3_key)


class TestEncryptionStandards(unittest.TestCase):
    """Test encryption standards compliance"""
    
    def test_encryption_standards(self):
        """Verify encryption standards are defined"""
        self.assertEqual(ENCRYPTION_STANDARDS['algorithm'], 'AES-256-GCM')
        self.assertEqual(ENCRYPTION_STANDARDS['key_size'], 256)
        self.assertEqual(ENCRYPTION_STANDARDS['tls_version'], '1.3')
        self.assertEqual(ENCRYPTION_STANDARDS['key_rotation_days'], 90)
        self.assertEqual(ENCRYPTION_STANDARDS['backup_retention_years'], 7)
    
    def test_compliance_frameworks(self):
        """Verify compliance framework coverage"""
        compliance = ENCRYPTION_STANDARDS['compliance']
        
        self.assertIn('SOC2', compliance)
        self.assertIn('ISO27001', compliance)
        self.assertIn('IFRS', compliance)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
