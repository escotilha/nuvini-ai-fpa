# AWS Infrastructure Setup

This guide covers setting up the AWS infrastructure required for the AI FP&A system.

## Overview

The AI FP&A system uses the following AWS services:

- **RDS PostgreSQL** - Primary database
- **Secrets Manager** - ERP credentials storage
- **S3** - Audit trail storage with Object Lock (WORM)
- **KMS** - Encryption key management
- **CloudWatch** - Logging and monitoring

## Prerequisites

- AWS Account with admin access
- AWS CLI installed and configured
- Terraform (optional, for infrastructure as code)

## Step 1: PostgreSQL RDS Setup

### Create RDS Instance

```bash
aws rds create-db-instance \
    --db-instance-identifier nuvini-fpa-prod \
    --db-instance-class db.t3.large \
    --engine postgres \
    --engine-version 15.4 \
    --master-username fpa_admin \
    --master-user-password <SECURE_PASSWORD> \
    --allocated-storage 100 \
    --storage-type gp3 \
    --storage-encrypted \
    --kms-key-id <KMS_KEY_ARN> \
    --backup-retention-period 7 \
    --preferred-backup-window "03:00-04:00" \
    --preferred-maintenance-window "sun:04:00-sun:05:00" \
    --multi-az \
    --publicly-accessible false \
    --vpc-security-group-ids <SECURITY_GROUP_ID> \
    --db-subnet-group-name <SUBNET_GROUP_NAME> \
    --enable-iam-database-authentication \
    --tags Key=Project,Value=AI-FPA Key=Environment,Value=Production
```

### Configure PostgreSQL Parameters

Create parameter group:

```bash
aws rds create-db-parameter-group \
    --db-parameter-group-name fpa-postgres15 \
    --db-parameter-group-family postgres15 \
    --description "AI FP&A PostgreSQL 15 parameters"

# Set parameters
aws rds modify-db-parameter-group \
    --db-parameter-group-name fpa-postgres15 \
    --parameters \
        "ParameterName=shared_buffers,ParameterValue=8GB,ApplyMethod=pending-reboot" \
        "ParameterName=work_mem,ParameterValue=256MB,ApplyMethod=immediate" \
        "ParameterName=maintenance_work_mem,ParameterValue=2GB,ApplyMethod=immediate" \
        "ParameterName=effective_cache_size,ParameterValue=24GB,ApplyMethod=immediate" \
        "ParameterName=random_page_cost,ParameterValue=1.1,ApplyMethod=immediate"
```

### Enable SSL/TLS

```bash
# Download RDS certificate
wget https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem

# Configure connection string
DATABASE_URL="postgresql://fpa_admin:<PASSWORD>@nuvini-fpa-prod.xxxx.us-east-1.rds.amazonaws.com:5432/fpa_db?sslmode=require&sslrootcert=global-bundle.pem"
```

## Step 2: Secrets Manager Setup

### Create Secrets for ERP Credentials

```bash
# TOTVS Protheus (Effecti)
aws secretsmanager create-secret \
    --name fpa/erp/effecti/totvs \
    --description "Effecti TOTVS Protheus credentials" \
    --secret-string '{
        "client_id": "effecti_oauth_client",
        "client_secret": "XXXX",
        "tenant_id": "effecti_tenant",
        "api_endpoint": "https://api.totvs.com.br/protheus"
    }' \
    --tags Key=Project,Value=AI-FPA Key=Company,Value=Effecti

# ContaAzul (Mercos)
aws secretsmanager create-secret \
    --name fpa/erp/mercos/contaazul \
    --description "Mercos ContaAzul credentials" \
    --secret-string '{
        "api_key": "XXXX",
        "api_endpoint": "https://api.contaazul.com/v1"
    }' \
    --tags Key=Project,Value=AI-FPA Key=Company,Value=Mercos

# Repeat for all 7 companies...
```

### Grant Access to Secrets

```bash
# Create IAM policy
aws iam create-policy \
    --policy-name FPA-SecretsAccess \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret"
            ],
            "Resource": "arn:aws:secretsmanager:*:*:secret:fpa/erp/*"
        }]
    }'

# Attach to application role
aws iam attach-role-policy \
    --role-name FPA-Application-Role \
    --policy-arn <POLICY_ARN>
```

## Step 3: S3 Audit Trail Setup

### Create S3 Bucket with Object Lock

```bash
# Create bucket with versioning and Object Lock
aws s3api create-bucket \
    --bucket nuvini-fpa-audit-logs \
    --region us-east-1 \
    --object-lock-enabled-for-bucket

# Enable versioning (required for Object Lock)
aws s3api put-bucket-versioning \
    --bucket nuvini-fpa-audit-logs \
    --versioning-configuration Status=Enabled

# Set Object Lock configuration (7-year retention)
aws s3api put-object-lock-configuration \
    --bucket nuvini-fpa-audit-logs \
    --object-lock-configuration '{
        "ObjectLockEnabled": "Enabled",
        "Rule": {
            "DefaultRetention": {
                "Mode": "GOVERNANCE",
                "Years": 7
            }
        }
    }'

# Enable encryption with KMS
aws s3api put-bucket-encryption \
    --bucket nuvini-fpa-audit-logs \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "aws:kms",
                "KMSMasterKeyID": "<KMS_KEY_ARN>"
            },
            "BucketKeyEnabled": true
        }]
    }'

# Block public access
aws s3api put-public-access-block \
    --bucket nuvini-fpa-audit-logs \
    --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

### Configure Lifecycle Policy

```bash
aws s3api put-bucket-lifecycle-configuration \
    --bucket nuvini-fpa-audit-logs \
    --lifecycle-configuration '{
        "Rules": [{
            "Id": "TransitionToIA",
            "Status": "Enabled",
            "Transitions": [{
                "Days": 90,
                "StorageClass": "STANDARD_IA"
            }],
            "NoncurrentVersionTransitions": [{
                "NoncurrentDays": 30,
                "StorageClass": "STANDARD_IA"
            }]
        }]
    }'
```

## Step 4: KMS Key Setup

### Create Master Encryption Key

```bash
aws kms create-key \
    --description "AI FP&A master encryption key" \
    --key-usage ENCRYPT_DECRYPT \
    --origin AWS_KMS \
    --multi-region false \
    --tags TagKey=Project,TagValue=AI-FPA

# Create alias
aws kms create-alias \
    --alias-name alias/fpa-master-key \
    --target-key-id <KEY_ID>

# Set key policy
aws kms put-key-policy \
    --key-id <KEY_ID> \
    --policy-name default \
    --policy '{
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "Enable IAM User Permissions",
            "Effect": "Allow",
            "Principal": {"AWS": "arn:aws:iam::<ACCOUNT_ID>:root"},
            "Action": "kms:*",
            "Resource": "*"
        }, {
            "Sid": "Allow FPA Application",
            "Effect": "Allow",
            "Principal": {"AWS": "arn:aws:iam::<ACCOUNT_ID>:role/FPA-Application-Role"},
            "Action": [
                "kms:Decrypt",
                "kms:DescribeKey",
                "kms:GenerateDataKey"
            ],
            "Resource": "*"
        }]
    }'
```

## Step 5: CloudWatch Setup

### Create Log Groups

```bash
# Application logs
aws logs create-log-group \
    --log-group-name /fpa/application

# ERP connector logs
aws logs create-log-group \
    --log-group-name /fpa/erp-connectors

# Consolidation logs
aws logs create-log-group \
    --log-group-name /fpa/consolidation

# Security audit logs
aws logs create-log-group \
    --log-group-name /fpa/security

# Set retention (7 years for compliance)
for group in /fpa/application /fpa/erp-connectors /fpa/consolidation /fpa/security; do
    aws logs put-retention-policy \
        --log-group-name $group \
        --retention-in-days 2555  # 7 years
done
```

### Create CloudWatch Alarms

```bash
# Database connection failures
aws cloudwatch put-metric-alarm \
    --alarm-name fpa-database-connection-failures \
    --alarm-description "Alert on database connection failures" \
    --metric-name DatabaseConnections \
    --namespace AWS/RDS \
    --statistic Sum \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 10 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=DBInstanceIdentifier,Value=nuvini-fpa-prod

# Consolidation errors
aws cloudwatch put-metric-alarm \
    --alarm-name fpa-consolidation-errors \
    --alarm-description "Alert on consolidation validation errors" \
    --metric-name ConsolidationErrors \
    --namespace FPA/Consolidation \
    --statistic Sum \
    --period 3600 \
    --evaluation-periods 1 \
    --threshold 5 \
    --comparison-operator GreaterThanThreshold
```

## Step 6: IAM Roles and Policies

### Create Application Role

```bash
# Create role
aws iam create-role \
    --role-name FPA-Application-Role \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }'

# Attach managed policies
aws iam attach-role-policy \
    --role-name FPA-Application-Role \
    --policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy

# Create custom policy
aws iam create-policy \
    --policy-name FPA-Application-Policy \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:PutObjectRetention",
                "s3:GetObject"
            ],
            "Resource": "arn:aws:s3:::nuvini-fpa-audit-logs/*"
        }, {
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt",
                "kms:GenerateDataKey"
            ],
            "Resource": "<KMS_KEY_ARN>"
        }, {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:log-group:/fpa/*"
        }]
    }'
```

## Step 7: Verification

### Test Database Connection

```bash
psql "$DATABASE_URL" -c "SELECT version();"
```

### Test Secrets Access

```python
import boto3
import json

client = boto3.client('secretsmanager', region_name='us-east-1')
response = client.get_secret_value(SecretId='fpa/erp/effecti/totvs')
credentials = json.loads(response['SecretString'])
print(f"Retrieved credentials for: {credentials.get('api_endpoint')}")
```

### Test S3 Audit Log Write

```python
import boto3

s3 = boto3.client('s3')
s3.put_object(
    Bucket='nuvini-fpa-audit-logs',
    Key='test/audit.log',
    Body=b'Test audit entry',
    ServerSideEncryption='aws:kms',
    ObjectLockMode='GOVERNANCE',
    ObjectLockRetainUntilDate=datetime.now() + timedelta(days=2555)
)
```

## Cost Estimate

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| RDS PostgreSQL | db.t3.large, 100GB gp3, Multi-AZ | ~$280 |
| S3 | 100GB STANDARD, 1TB IA | ~$45 |
| Secrets Manager | 7 secrets | ~$3 |
| KMS | 1 key, 10K requests/month | ~$2 |
| CloudWatch | 50GB logs, 10 alarms | ~$30 |
| **Total** | | **~$360/month** |

## Security Best Practices

1. **Enable MFA** on all admin accounts
2. **Use IAM roles** instead of access keys
3. **Enable CloudTrail** for API audit logging
4. **Regular backups** with automated restore testing
5. **Encrypt everything** - RDS, S3, EBS volumes
6. **Least privilege** - minimal permissions per role
7. **VPC isolation** - private subnets for RDS
8. **Security groups** - whitelist only required IPs

## Next Steps

- [Environment Configuration](environment.md)
- [PostgreSQL Setup](postgresql.md)
- [Monitoring Configuration](monitoring.md)
