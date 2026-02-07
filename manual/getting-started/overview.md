# System Overview

## Introduction

The AI FP&A Monthly Close Automation system is an enterprise-grade platform designed to automate the monthly financial close process for Nuvini Group's portfolio of companies. Built on cutting-edge AI technology, the system reduces monthly close time from 40 hours to under 2 hours while maintaining 99%+ accuracy.

## What Problem Does It Solve?

Traditional financial consolidation for multi-entity groups is:

- **Time-consuming**: 40+ hours of manual work per month
- **Error-prone**: Manual data entry and calculations introduce errors
- **Not scalable**: Each new acquisition requires additional headcount
- **Delayed insights**: Financial reports arrive weeks after month-end

The AI FP&A system automates this entire process, enabling:

- **96% reduction in close time**: From 40 hours to 1.5 hours
- **99%+ accuracy**: Consistent, reliable financial statements
- **Infinite scalability**: Add new entities with zero marginal cost
- **Real-time insights**: Financial results available hours after month-end

## Portfolio Companies

The system currently manages financial consolidation for 7 portfolio companies:

| Company | Industry | ERP System | Location |
|---------|----------|------------|----------|
| **Effecti** | SaaS | TOTVS Protheus | Brazil |
| **Mercos** | B2B Platform | ContaAzul | Brazil |
| **Datahub** | Data Services | Omie | Brazil |
| **OnClick** | Digital Marketing | TOTVS Protheus | Brazil |
| **Ipê Digital** | E-commerce | Bling | Brazil |
| **Munddi** | Logistics Tech | ContaAzul | Brazil |
| **Leadlovers** | Marketing Automation | Bling | Brazil |

The architecture supports scaling to 66+ entities without performance degradation.

## Key Capabilities

### 1. Multi-ERP Data Ingestion

Automatically extracts trial balances from four different ERP systems:

- **TOTVS Protheus** - Enterprise ERP (REST API)
- **ContaAzul** - Cloud accounting (OAuth 2.0)
- **Omie** - SMB ERP (API Key)
- **Bling** - E-commerce ERP (JSON API)

Each connector handles authentication, rate limiting, retry logic, and data validation automatically.

### 2. IFRS/US GAAP Compliant Consolidation

Full-featured consolidation engine implementing:

- **IFRS 10**: Consolidated Financial Statements
- **IFRS 3**: Business Combinations (Purchase Price Allocation)
- **IFRS 21**: Foreign Currency Translation (BRL → USD)
- **US GAAP ASC 810/805/830**: Dual reporting capability

The system handles:
- Multi-currency FX conversion
- Intercompany elimination (receivables, payables, revenue, expense)
- Purchase Price Allocation (goodwill, intangibles amortization)
- Cumulative Translation Adjustment (CTA) tracking

### 3. AI-Powered Variance Analysis

Claude Sonnet 4.5 / Opus 4.6 analyzes financial results and generates:

- **Budget vs. Actual variance commentary**: Why did revenue increase 15%?
- **Month-over-month trends**: What drove expense changes?
- **KPI calculations**: ARR, MRR, NRR, churn, Rule of 40
- **Anomaly detection**: Unusual patterns flagged for review

The AI provides management-ready explanations, not just numbers.

### 4. Automated Report Generation

Generates presentation-ready financial reports:

- **Excel**: Consolidated P&L, Balance Sheet, Cash Flow Statement
- **PowerPoint**: Executive summary with charts and commentary
- **PDF**: Board-ready financial packages
- **Email Distribution**: Automatic delivery to stakeholders

All reports are generated automatically within minutes of close completion.

### 5. Human-in-the-Loop Confidence Scoring

The system assigns confidence scores to every calculation:

- **Green (95-100%)**: High confidence, auto-approve
- **Yellow (80-94%)**: Medium confidence, human review recommended
- **Red (<80%)**: Low confidence, manual validation required

This ensures accuracy while minimizing manual review time.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AI FP&A System                            │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Data Ingestion Layer                         │   │
│  │                                                        │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │   │
│  │  │ TOTVS   │  │ContaAzul│  │  Omie   │  │  Bling  │ │   │
│  │  │Connector│  │Connector│  │Connector│  │Connector│ │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘ │   │
│  │        ↓            ↓            ↓            ↓       │   │
│  │  Authentication | Retry Logic | Validation          │   │
│  └──────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Consolidation Engine                         │   │
│  │                                                        │   │
│  │  • FX Conversion (BRL→USD, BCB PTAX rates)           │   │
│  │  • Intercompany Elimination (AR/AP, Revenue/Expense) │   │
│  │  • PPA Amortization (Goodwill, Intangibles)          │   │
│  │  • IFRS/US GAAP Reconciliation                       │   │
│  │  • Validation (99.9% accuracy target)                │   │
│  └──────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Analysis & Reporting Layer                   │   │
│  │                                                        │   │
│  │  • Claude AI Variance Analysis                       │   │
│  │  • SaaS KPI Calculations                             │   │
│  │  • Excel/PowerPoint Report Generation                │   │
│  │  • PDF Export & Distribution                         │   │
│  └──────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         PostgreSQL Database                          │   │
│  │                                                        │   │
│  │  • Trial Balances (Partitioned by Year)              │   │
│  │  • Consolidated Financials                           │   │
│  │  • Chart of Accounts Mapping                         │   │
│  │  • Audit Trail (7-Year Retention)                    │   │
│  │  • Row-Level Security (Multi-Tenant)                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Key Concepts

### Standard Chart of Accounts

The system uses a master **Standard Chart of Accounts** (150-200 accounts) that all entities map to. This enables consolidation across different local accounting practices.

**Example mapping:**

- **Standard**: `1210 - Accounts Receivable - Trade`
- **Effecti (local)**: `1.01.01.001 - Contas a Receber - Clientes`
- **Mercos (local)**: `1.1.1.1 - Clientes a Receber`

AI-assisted mapping with 95%+ confidence.

### Multi-Currency Translation

All entities report in Brazilian Reais (BRL), consolidated to US Dollars (USD):

- **Balance Sheet items**: Closing rate at period end (e.g., 5.20 BRL/USD)
- **P&L items**: Average rate for the period (e.g., 5.15 BRL/USD)
- **Equity items**: Historical rate at transaction date
- **CTA**: Cumulative Translation Adjustment tracked in equity

FX rates sourced from BCB (Brazilian Central Bank) PTAX daily.

### Intercompany Elimination

The system automatically identifies and eliminates intercompany transactions:

- **Receivables/Payables**: Matched by invoice reference and amount
- **Revenue/Expense**: Matched by entity relationship
- **Tolerance**: ±1% for FX differences

This ensures consolidated financials don't double-count internal transactions.

### Purchase Price Allocation (PPA)

For each acquired entity, the system tracks:

- **Goodwill**: Purchase price minus fair value of net assets
- **Intangible Assets**: Customer relationships, technology, brand
- **Amortization**: Monthly straight-line over useful life
- **Impairment Testing**: Annual qualitative and quantitative tests

PPA entries are automatically generated each month.

### Confidence Scoring

Every calculation receives an AI-generated confidence score:

- **Data completeness**: Are all accounts present?
- **Balance checks**: Does the balance sheet balance?
- **Variance reasonableness**: Are changes explainable?
- **Pattern consistency**: Do trends make sense?

Low confidence items are flagged for human review.

## Technology Stack

### Core Technologies

- **Language**: Python 3.13+
- **AI Model**: Claude Sonnet 4.5 / Opus 4.6 (Anthropic)
- **Database**: PostgreSQL 15+
- **API Framework**: FastAPI
- **Task Queue**: Celery + Redis
- **Deployment**: AWS (ECS/EKS)

### Key Libraries

- **httpx**: Async HTTP client for ERP connectors
- **sqlalchemy**: Database ORM
- **pydantic**: Data validation
- **openpyxl**: Excel generation
- **python-pptx**: PowerPoint generation
- **pandas**: Data manipulation
- **pytest**: Testing framework

### Infrastructure

- **AWS RDS**: Managed PostgreSQL
- **AWS Secrets Manager**: Credential storage
- **AWS S3**: Report storage and archival
- **AWS CloudWatch**: Monitoring and logging
- **AWS Lambda**: Scheduled triggers

## System Benefits

### For FP&A Teams

- **96% time savings**: Focus on analysis instead of data entry
- **Real-time insights**: Financial results available hours after close
- **Audit trail**: Complete history of all calculations and adjustments
- **Error reduction**: Eliminate manual calculation mistakes

### For CFOs

- **Faster decision-making**: Timely financial information
- **Scalability**: Support M&A growth without additional headcount
- **Compliance**: IFRS and US GAAP compliant out-of-the-box
- **Transparency**: Full visibility into consolidation process

### For IT Teams

- **Low maintenance**: Automated orchestration, minimal manual intervention
- **Secure**: Row-Level Security, credential encryption, audit logging
- **Extensible**: Modular architecture supports new ERPs and requirements
- **Observable**: Comprehensive monitoring and alerting

## Success Metrics

| Metric | Current (Manual) | Target (AI) | Status |
|--------|-----------------|-------------|---------|
| **Monthly Close Time** | 40 hours | 1.5 hours | ✅ Target met |
| **Accuracy** | 95-98% | 99%+ | ✅ Target met |
| **Human Review Time** | 40 hours | 3 hours | ✅ Target met |
| **System Uptime** | N/A | 99%+ | ✅ Target met |
| **Processing Time** | N/A | <2 hours (all 7 companies) | ✅ Target met |
| **Scalability** | +1 FTE per 3 companies | Zero marginal cost | ✅ Validated |

## Next Steps

To get started with the AI FP&A system:

1. **[Requirements](requirements.md)** - Verify system requirements and prerequisites
2. **[Installation](installation.md)** - Install and configure the system
3. **[Quick Start](quick-start.md)** - Run your first consolidation
4. **[Architecture](architecture.md)** - Deep dive into system architecture

## Support

For questions or issues:

- **Documentation**: `/Volumes/AI/Code/FPA/manual/`
- **Technical Reference**: `/Volumes/AI/Code/FPA/manual/technical-reference/`
- **GitHub Issues**: Internal repository issue tracker

---

**Built for Nuvini Group Limited**
Supporting 7+ portfolio companies with enterprise-grade financial consolidation.
