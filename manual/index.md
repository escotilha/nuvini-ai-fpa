# AI FP&A Monthly Close Automation

## Welcome

Welcome to the **AI FP&A Monthly Close Automation System** user manual. This comprehensive guide will help you understand, deploy, and operate an AI-powered financial consolidation system for Nuvini Group Limited's portfolio companies.

## What is AI FP&A?

The AI FP&A system automates the monthly financial close process across multiple portfolio companies, consolidating financial data from diverse ERP systems into standardized IFRS and US GAAP compliant reports.

### Key Capabilities

- **Automated Data Extraction** from 4+ Brazilian ERP systems (TOTVS, ContaAzul, Omie, Bling)
- **Multi-Currency Consolidation** with IFRS 21 compliant FX translation
- **Intercompany Elimination** with intelligent matching and FX tolerance
- **IFRS/US GAAP Reconciliation** for dual reporting standards
- **Human Oversight** with confidence scoring and risk-based review
- **Complete Audit Trail** with 7-year retention for compliance

### Portfolio Coverage

Currently supports **7 portfolio companies**:

| Company | ERP System | Currency | ARR |
|---------|-----------|----------|-----|
| Effecti | TOTVS Protheus | BRL | $8.5M |
| Mercos | ContaAzul | BRL | $7.2M |
| Datahub | Omie | BRL | $6.8M |
| OnClick | TOTVS Protheus | BRL | $6.1M |
| Ipê Digital | Bling | BRL | $5.4M |
| Munddi | ContaAzul | BRL | $4.8M |
| Leadlovers | Bling | BRL | $4.8M |

**Total ARR:** $43.6M | **Total Employees:** 665

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AI FP&A SYSTEM                            │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ ERP Systems  │  │ Consolidation│  │   Reports    │      │
│  │ (4 Adapters) │→ │   Engine     │→ │ (IFRS/GAAP)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         ↓                 ↓                   ↓             │
│  ┌──────────────────────────────────────────────────┐      │
│  │         PostgreSQL Database (25 tables)          │      │
│  │         - Multi-tenant RLS                       │      │
│  │         - 7-year audit trail                     │      │
│  │         - 80+ optimized indexes                  │      │
│  └──────────────────────────────────────────────────┘      │
│                                                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │         Security & Compliance Layer              │      │
│  │         - AES-256 encryption                     │      │
│  │         - RBAC (11 roles)                        │      │
│  │         - Human oversight                        │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

!!! tip "New User?"
    Start with the [Quick Start Guide](getting-started/quick-start.md) for a hands-on introduction.

1. **[System Requirements](getting-started/requirements.md)** - Verify prerequisites
2. **[Installation](getting-started/installation.md)** - Set up the system
3. **[Quick Start](getting-started/quick-start.md)** - Run your first consolidation
4. **[Monthly Close Process](user-guide/monthly-close.md)** - Understand the workflow

## Key Features

### 🤖 Intelligent Automation

- **99.9% accuracy target** with comprehensive validation
- **Confidence scoring** (Green/Yellow/Red) for all AI-generated entries
- **Risk-based sampling** - 5% review for green, 100% for yellow/red
- **Automatic retry** logic with circuit breakers

### 🌍 Multi-Entity Support

- **7 portfolio companies** with ability to scale to 66+
- **Multi-currency** consolidation (BRL → USD presentation)
- **Intercompany elimination** with FX-aware matching
- **Purchase Price Allocation** (goodwill, amortization, impairment)

### 🔒 Enterprise Security

- **AES-256-GCM** field-level encryption
- **Row-Level Security** (RLS) for multi-tenant isolation
- **11 RBAC roles** with 25+ granular permissions
- **Complete audit trail** with immutable S3 Object Lock storage

### 📊 Regulatory Compliance

- ✅ **IFRS 10, IFRS 3, IFRS 21** - Consolidation, business combinations, FX
- ✅ **US GAAP ASC 810/805/830** - Consolidation, business combinations, FX
- ✅ **SOC 2 Type II** - Access controls, encryption, audit logging
- ✅ **ISO 27001** - Information security management

## Documentation Structure

This manual is organized into the following sections:

### [Getting Started](getting-started/overview.md)
System overview, installation, and initial setup

### [User Guide](user-guide/monthly-close.md)
Day-to-day operations and workflows

### [Technical Reference](technical-reference/database.md)
Detailed technical documentation for developers

### [Deployment](deployment/aws-setup.md)
Production deployment guides and best practices

### [Appendix](appendix/glossary.md)
Glossary, FAQ, compliance information, and changelog

## Support

- **GitHub Issues:** [https://github.com/escotilha/nuvini-ai-fpa/issues](https://github.com/escotilha/nuvini-ai-fpa/issues)
- **Email:** Pierre Schurmann ([pschumacher@nuvini.ai](mailto:pschumacher@nuvini.ai))
- **Documentation:** This manual and `/docs` folder in the repository

## Version Information

- **Version:** 1.0.0
- **Release Date:** February 7, 2026
- **Last Updated:** February 7, 2026
- **Python Version:** 3.13+
- **PostgreSQL Version:** 15+

---

**Next:** [System Overview →](getting-started/overview.md)
