# API Reference

**Version:** 1.0.0
**Base URL:** `https://api.fpa.nuvini.ai/v1`
**Last Updated:** 2026-02-07

## Overview

The AI FP&A system exposes a RESTful API for programmatic access to financial data, consolidation operations, and AI-powered insights. All API endpoints use JSON for request and response payloads.

## Authentication

### API Key Authentication

All API requests require authentication using an API key in the request header.

```http
GET /api/v1/entities
Authorization: Bearer fpa_abc123...xyz789
```

### Generating API Keys

```python
from core.access_control import RBACManager, AgentRole

rbac = RBACManager()
api_key = rbac.generate_api_key(
    role=AgentRole.DATA_INGESTION,
    agent_id='effecti_connector',
    companies=['effecti'],
    expires_days=90
)
```

### API Key Scoping

API keys are scoped by:
- **Role** - Determines available permissions
- **Companies** - Optional restriction to specific entities
- **Expiration** - Default 90 days, max 365 days

## Rate Limiting

- **Default:** 1000 requests per hour per API key
- **Burst:** Up to 100 requests per minute
- **Headers:**
  - `X-RateLimit-Limit` - Total requests allowed
  - `X-RateLimit-Remaining` - Remaining requests
  - `X-RateLimit-Reset` - Unix timestamp when limit resets

## Base URL and Versioning

- **Production:** `https://api.fpa.nuvini.ai/v1`
- **Staging:** `https://staging-api.fpa.nuvini.ai/v1`
- **Versioning:** URL-based (`/v1`, `/v2`)

## Common Response Formats

### Success Response

```json
{
  "success": true,
  "data": { ... },
  "metadata": {
    "timestamp": "2026-02-07T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid period format",
    "details": {
      "field": "period_month",
      "expected": "1-12",
      "received": "13"
    }
  },
  "metadata": {
    "timestamp": "2026-02-07T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTHENTICATION_FAILED` | 401 | Invalid or expired API key |
| `PERMISSION_DENIED` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

## Endpoints

### Portfolio Entities

#### List Entities

Get all portfolio entities accessible to the current API key.

```http
GET /api/v1/entities
```

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "entity_id": "uuid-1",
      "entity_code": "EFFECTI",
      "entity_name": "Effecti",
      "parent_entity_id": null,
      "functional_currency": "BRL",
      "country_code": "BR",
      "ownership_percentage": 100.00,
      "is_active": true
    },
    ...
  ]
}
```

#### Get Entity Details

```http
GET /api/v1/entities/{entity_id}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "entity_id": "uuid-1",
    "entity_code": "EFFECTI",
    "entity_name": "Effecti",
    "parent_entity_id": null,
    "functional_currency": "BRL",
    "country_code": "BR",
    "ownership_percentage": 100.00,
    "acquisition_date": "2020-01-15",
    "entity_type": "subsidiary",
    "is_active": true,
    "created_at": "2020-01-15T00:00:00Z",
    "updated_at": "2026-02-07T10:30:00Z"
  }
}
```

### Trial Balances

#### Get Trial Balance

Retrieve trial balance for an entity and period.

```http
GET /api/v1/trial-balances?entity_id={entity_id}&year={year}&month={month}
```

**Query Parameters:**
- `entity_id` (required) - Entity UUID
- `year` (required) - Period year (e.g., 2024)
- `month` (required) - Period month (1-12)
- `include_zero_balances` (optional) - Include accounts with zero balance (default: false)

**Response:**

```json
{
  "success": true,
  "data": {
    "entity_id": "uuid-1",
    "entity_code": "EFFECTI",
    "period_year": 2024,
    "period_month": 12,
    "currency": "BRL",
    "accounts": [
      {
        "account_code": "1.01.001",
        "account_name": "Caixa",
        "standard_account_code": "1010",
        "standard_account_name": "Cash",
        "account_type": "asset",
        "opening_balance": 100000.00,
        "debit_amount": 50000.00,
        "credit_amount": 30000.00,
        "ending_balance": 120000.00
      },
      ...
    ],
    "totals": {
      "total_debits": 5000000.00,
      "total_credits": 5000000.00,
      "difference": 0.00
    }
  }
}
```

#### Upload Trial Balance

Upload trial balance data for an entity and period.

```http
POST /api/v1/trial-balances
```

**Request Body:**

```json
{
  "entity_id": "uuid-1",
  "period_year": 2024,
  "period_month": 12,
  "currency": "BRL",
  "source_system": "totvs_protheus",
  "accounts": [
    {
      "account_code": "1.01.001",
      "account_name": "Caixa",
      "opening_balance": 100000.00,
      "debit_amount": 50000.00,
      "credit_amount": 30000.00,
      "ending_balance": 120000.00
    },
    ...
  ]
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "batch_id": "batch-uuid",
    "entity_id": "uuid-1",
    "period_year": 2024,
    "period_month": 12,
    "accounts_uploaded": 150,
    "validation_results": {
      "is_valid": true,
      "warnings": [],
      "errors": []
    }
  }
}
```

### Consolidated Balances

#### Get Consolidated Balances

Retrieve consolidated financial statement balances.

```http
GET /api/v1/consolidated-balances?year={year}&month={month}&level={level}
```

**Query Parameters:**
- `year` (required) - Period year
- `month` (required) - Period month
- `level` (optional) - Consolidation level: `entity` or `group` (default: `group`)
- `account_type` (optional) - Filter by account type: `asset`, `liability`, `equity`, `revenue`, `expense`

**Response:**

```json
{
  "success": true,
  "data": {
    "period_year": 2024,
    "period_month": 12,
    "currency": "USD",
    "consolidation_level": "group",
    "accounts": [
      {
        "account_code": "1010",
        "account_name": "Cash",
        "account_type": "asset",
        "opening_balance": 1500000.00,
        "period_activity": 250000.00,
        "ending_balance": 1750000.00
      },
      ...
    ],
    "summary": {
      "total_assets": 50000000.00,
      "total_liabilities": 30000000.00,
      "total_equity": 20000000.00,
      "total_revenue": 15000000.00,
      "total_expenses": 12000000.00,
      "net_income": 3000000.00
    }
  }
}
```

#### Trigger Consolidation

Initiate consolidation process for a period.

```http
POST /api/v1/consolidation/run
```

**Request Body:**

```json
{
  "period_year": 2024,
  "period_month": 12,
  "presentation_currency": "USD",
  "options": {
    "include_eliminations": true,
    "include_ppa_amortization": true,
    "validate_results": true
  }
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "consolidation_id": "cons-uuid",
    "status": "in_progress",
    "period_year": 2024,
    "period_month": 12,
    "started_at": "2026-02-07T10:30:00Z",
    "estimated_completion": "2026-02-07T10:35:00Z"
  }
}
```

#### Get Consolidation Status

```http
GET /api/v1/consolidation/{consolidation_id}/status
```

**Response:**

```json
{
  "success": true,
  "data": {
    "consolidation_id": "cons-uuid",
    "status": "completed",
    "period_year": 2024,
    "period_month": 12,
    "started_at": "2026-02-07T10:30:00Z",
    "completed_at": "2026-02-07T10:34:23Z",
    "execution_time_seconds": 263,
    "validation_results": {
      "is_valid": true,
      "accuracy_score": 0.998,
      "warnings": [],
      "errors": []
    }
  }
}
```

### Journal Entries

#### List Journal Entries

```http
GET /api/v1/journal-entries?entity_id={entity_id}&year={year}&month={month}&status={status}
```

**Query Parameters:**
- `entity_id` (optional) - Filter by entity
- `year` (optional) - Filter by year
- `month` (optional) - Filter by month
- `status` (optional) - Filter by status: `draft`, `pending_review`, `approved`, `posted`, `reversed`
- `source` (optional) - Filter by source: `manual`, `ai_generated`, `system`, `consolidation`

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "entry_id": "je-uuid",
      "entry_number": "JE-2024-12-001",
      "entity_id": "uuid-1",
      "entity_code": "EFFECTI",
      "period_year": 2024,
      "period_month": 12,
      "entry_date": "2024-12-31",
      "status": "pending_review",
      "entry_source": "ai_generated",
      "description": "Accrued hosting expense",
      "ai_confidence": 0.87,
      "total_debit": 12500.00,
      "total_credit": 12500.00,
      "created_at": "2026-01-15T10:00:00Z"
    },
    ...
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 127
  }
}
```

#### Get Journal Entry Details

```http
GET /api/v1/journal-entries/{entry_id}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "entry_id": "je-uuid",
    "entry_number": "JE-2024-12-001",
    "entity_id": "uuid-1",
    "period_year": 2024,
    "period_month": 12,
    "entry_date": "2024-12-31",
    "status": "pending_review",
    "entry_source": "ai_generated",
    "description": "Accrued hosting expense",
    "ai_confidence": 0.87,
    "ai_explanation": "AI detected 15% increase in cloud usage vs. prior month.",
    "lines": [
      {
        "line_number": 1,
        "account_code": "5100",
        "account_name": "Hosting Expense",
        "debit_amount": 12500.00,
        "credit_amount": 0,
        "currency": "BRL",
        "description": "Accrued hosting expense - December 2024"
      },
      {
        "line_number": 2,
        "account_code": "2120",
        "account_name": "Accrued Liabilities",
        "debit_amount": 0,
        "credit_amount": 12500.00,
        "currency": "BRL",
        "description": "Accrued hosting liability"
      }
    ]
  }
}
```

#### Create Journal Entry

```http
POST /api/v1/journal-entries
```

**Request Body:**

```json
{
  "entity_id": "uuid-1",
  "period_year": 2024,
  "period_month": 12,
  "entry_date": "2024-12-31",
  "entry_source": "manual",
  "description": "Accrual for consulting fees",
  "lines": [
    {
      "account_code": "5200",
      "debit_amount": 25000.00,
      "credit_amount": 0,
      "currency": "BRL",
      "description": "Consulting fees"
    },
    {
      "account_code": "2120",
      "debit_amount": 0,
      "credit_amount": 25000.00,
      "currency": "BRL",
      "description": "Accrued consulting payable"
    }
  ]
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "entry_id": "je-uuid",
    "entry_number": "JE-2024-12-125",
    "status": "draft",
    "created_at": "2026-02-07T10:30:00Z"
  }
}
```

#### Approve Journal Entry

```http
POST /api/v1/journal-entries/{entry_id}/approve
```

**Request Body:**

```json
{
  "comments": "Reviewed and approved. Accrual is reasonable based on contract."
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "entry_id": "je-uuid",
    "status": "approved",
    "approved_by": "user-uuid",
    "approved_at": "2026-02-07T10:30:00Z"
  }
}
```

#### Post Journal Entry

```http
POST /api/v1/journal-entries/{entry_id}/post
```

**Response:**

```json
{
  "success": true,
  "data": {
    "entry_id": "je-uuid",
    "status": "posted",
    "posted_by": "user-uuid",
    "posted_at": "2026-02-07T10:30:00Z"
  }
}
```

### Intercompany Balances

#### Get Intercompany Reconciliation

```http
GET /api/v1/intercompany-balances?year={year}&month={month}&variance_threshold={threshold}
```

**Query Parameters:**
- `year` (required) - Period year
- `month` (required) - Period month
- `variance_threshold` (optional) - Minimum variance to include (default: 0.01)
- `include_eliminated` (optional) - Include already eliminated balances (default: false)

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "ic_balance_id": "ic-uuid",
      "entity_from_code": "EFFECTI",
      "entity_to_code": "LEADLOVERS",
      "account_code": "1210",
      "account_name": "Accounts Receivable - IC",
      "amount_from": 150000.00,
      "amount_to": -150025.00,
      "variance": 25.00,
      "variance_percentage": 0.017,
      "currency": "USD",
      "is_eliminated": false,
      "status": "minor_variance"
    },
    ...
  ],
  "summary": {
    "total_ic_balances": 47,
    "matched": 42,
    "minor_variance": 4,
    "significant_variance": 1,
    "total_variance": 1250.75
  }
}
```

### FX Rates

#### Get FX Rate

```http
GET /api/v1/fx-rates?from={currency}&to={currency}&date={date}
```

**Query Parameters:**
- `from` (required) - Source currency code (e.g., BRL)
- `to` (required) - Target currency code (e.g., USD)
- `date` (required) - Rate date (YYYY-MM-DD)

**Response:**

```json
{
  "success": true,
  "data": {
    "from_currency": "BRL",
    "to_currency": "USD",
    "rate_date": "2024-12-31",
    "rate": 0.187453,
    "rate_source": "bcb"
  }
}
```

#### Get Monthly Average FX Rate

```http
GET /api/v1/fx-rates/monthly?from={currency}&to={currency}&year={year}&month={month}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "from_currency": "BRL",
    "to_currency": "USD",
    "period_year": 2024,
    "period_month": 12,
    "average_rate": 0.185234,
    "rate_source": "bcb"
  }
}
```

#### Upload FX Rates

```http
POST /api/v1/fx-rates
```

**Request Body:**

```json
{
  "rates": [
    {
      "from_currency": "BRL",
      "to_currency": "USD",
      "rate_date": "2024-12-31",
      "rate": 0.187453,
      "rate_source": "manual"
    },
    ...
  ]
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "rates_uploaded": 5,
    "rates_updated": 2
  }
}
```

### Validation

#### Validate Trial Balance

```http
POST /api/v1/validation/trial-balance
```

**Request Body:**

```json
{
  "entity_id": "uuid-1",
  "period_year": 2024,
  "period_month": 12
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "is_valid": true,
    "validation_results": [
      {
        "rule": "debit_credit_balance",
        "passed": true,
        "total_debits": 5000000.00,
        "total_credits": 5000000.00,
        "difference": 0.00
      },
      {
        "rule": "account_mapping_completeness",
        "passed": true,
        "total_accounts": 150,
        "mapped_accounts": 150,
        "unmapped_accounts": 0
      }
    ],
    "warnings": [],
    "errors": []
  }
}
```

### Reporting

#### Generate Financial Report

```http
POST /api/v1/reports/generate
```

**Request Body:**

```json
{
  "report_type": "balance_sheet",
  "period_year": 2024,
  "period_month": 12,
  "consolidation_level": "group",
  "currency": "USD",
  "format": "json",
  "options": {
    "include_prior_period": true,
    "include_variance_analysis": true
  }
}
```

**Report Types:**
- `balance_sheet` - Balance Sheet
- `income_statement` - Income Statement
- `cash_flow` - Cash Flow Statement
- `trial_balance` - Trial Balance
- `consolidation_summary` - Consolidation Summary
- `variance_analysis` - Variance Analysis

**Formats:**
- `json` - JSON response
- `pdf` - PDF download
- `excel` - Excel download
- `csv` - CSV download

**Response:**

```json
{
  "success": true,
  "data": {
    "report_id": "report-uuid",
    "report_type": "balance_sheet",
    "status": "completed",
    "download_url": "https://api.fpa.nuvini.ai/v1/reports/report-uuid/download",
    "expires_at": "2026-02-08T10:30:00Z"
  }
}
```

## Webhooks

### Register Webhook

Subscribe to events.

```http
POST /api/v1/webhooks
```

**Request Body:**

```json
{
  "url": "https://your-app.com/webhooks/fpa",
  "events": [
    "consolidation.completed",
    "journal_entry.approved",
    "period.closed"
  ],
  "secret": "your-webhook-secret"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "webhook_id": "webhook-uuid",
    "url": "https://your-app.com/webhooks/fpa",
    "events": [
      "consolidation.completed",
      "journal_entry.approved",
      "period.closed"
    ],
    "created_at": "2026-02-07T10:30:00Z"
  }
}
```

### Webhook Events

| Event | Description | Payload |
|-------|-------------|---------|
| `consolidation.completed` | Consolidation process finished | consolidation_id, period_year, period_month, status |
| `consolidation.failed` | Consolidation process failed | consolidation_id, error_message |
| `journal_entry.created` | New journal entry created | entry_id, entity_id, period |
| `journal_entry.approved` | Journal entry approved | entry_id, approved_by |
| `journal_entry.posted` | Journal entry posted | entry_id, posted_by |
| `period.closed` | Period hard locked | entity_id, period_year, period_month |
| `validation.failed` | Validation check failed | entity_id, validation_type, errors |

### Webhook Payload Example

```json
{
  "event": "consolidation.completed",
  "timestamp": "2026-02-07T10:34:23Z",
  "data": {
    "consolidation_id": "cons-uuid",
    "period_year": 2024,
    "period_month": 12,
    "status": "completed",
    "accuracy_score": 0.998
  },
  "signature": "sha256=abc123..."
}
```

## SDKs and Client Libraries

### Python

```python
from fpa_client import FPAClient

client = FPAClient(api_key='fpa_abc123...xyz789')

# Get trial balance
trial_balance = client.trial_balances.get(
    entity_id='uuid-1',
    year=2024,
    month=12
)

# Trigger consolidation
consolidation = client.consolidation.run(
    period_year=2024,
    period_month=12,
    presentation_currency='USD'
)
```

### TypeScript/JavaScript

```typescript
import { FPAClient } from '@nuvini/fpa-client';

const client = new FPAClient({ apiKey: 'fpa_abc123...xyz789' });

// Get trial balance
const trialBalance = await client.trialBalances.get({
  entityId: 'uuid-1',
  year: 2024,
  month: 12
});

// Trigger consolidation
const consolidation = await client.consolidation.run({
  periodYear: 2024,
  periodMonth: 12,
  presentationCurrency: 'USD'
});
```

## Pagination

Paginated endpoints support the following query parameters:

- `page` - Page number (default: 1)
- `per_page` - Items per page (default: 50, max: 200)

**Response includes pagination metadata:**

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 127,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```

## See Also

- [Database Schema](/Volumes/AI/Code/FPA/manual/technical-reference/database.md)
- [Security Architecture](/Volumes/AI/Code/FPA/manual/technical-reference/security.md)
- [ERP Connectors](/Volumes/AI/Code/FPA/manual/technical-reference/erp-connectors.md)
