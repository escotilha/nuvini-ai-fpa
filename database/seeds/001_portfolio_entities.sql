-- ============================================================================
-- AI FP&A Monthly Close Automation - Portfolio Entities Seed Data
-- ============================================================================
-- Version: 1.0.0
-- Created: 2026-02-07
-- Description: Seed data for 7 initial portfolio companies
-- ============================================================================

-- Insert holding company (parent entity)
INSERT INTO portfolio_entities (
    entity_code,
    legal_name,
    trade_name,
    tax_id,
    functional_currency,
    presentation_currency,
    accounting_standard,
    country_code,
    status,
    parent_entity_id,
    ownership_percentage,
    consolidation_method,
    fiscal_year_end,
    inception_date,
    metadata
) VALUES
-- Parent holding company
(
    'HOLDING',
    'AI FP&A Holdings Ltd.',
    'AI FP&A',
    '00.000.000/0001-00',
    'USD',
    'USD',
    'IFRS',
    'US',
    'active',
    NULL,
    100.00,
    'full',
    '2024-12-31',
    '2018-01-01',
    '{"type": "holding_company", "segment": "investment", "notes": "Parent consolidation entity"}'::jsonb
);

-- Get holding company ID for foreign key references
DO $$
DECLARE
    v_holding_id UUID;
BEGIN
    SELECT entity_id INTO v_holding_id
    FROM portfolio_entities
    WHERE entity_code = 'HOLDING';

    -- Insert 7 portfolio companies
    INSERT INTO portfolio_entities (
        entity_code,
        legal_name,
        trade_name,
        tax_id,
        functional_currency,
        presentation_currency,
        accounting_standard,
        country_code,
        status,
        parent_entity_id,
        ownership_percentage,
        consolidation_method,
        fiscal_year_end,
        inception_date,
        metadata
    ) VALUES
    -- 1. Effecti - Sales Effectiveness Platform
    (
        'EFFECTI',
        'Effecti Tecnologia S.A.',
        'Effecti',
        '12.345.678/0001-90',
        'BRL',
        'USD',
        'IFRS',
        'BR',
        'active',
        v_holding_id,
        100.00,
        'full',
        '2024-12-31',
        '2019-03-15',
        '{"type": "operating_company", "segment": "SaaS", "vertical": "sales_enablement", "employees": 85, "arr_usd": 4200000}'::jsonb
    ),

    -- 2. Mercos - B2B Commerce Platform
    (
        'MERCOS',
        'Mercos Soluções em Tecnologia Ltda.',
        'Mercos',
        '23.456.789/0001-01',
        'BRL',
        'USD',
        'IFRS',
        'BR',
        'active',
        v_holding_id,
        100.00,
        'full',
        '2024-12-31',
        '2017-06-01',
        '{"type": "operating_company", "segment": "SaaS", "vertical": "b2b_commerce", "employees": 120, "arr_usd": 8500000}'::jsonb
    ),

    -- 3. Datahub - Data Integration Platform
    (
        'DATAHUB',
        'Datahub Integração de Dados S.A.',
        'Datahub',
        '34.567.890/0001-12',
        'BRL',
        'USD',
        'IFRS',
        'BR',
        'active',
        v_holding_id,
        100.00,
        'full',
        '2024-12-31',
        '2020-01-20',
        '{"type": "operating_company", "segment": "SaaS", "vertical": "data_integration", "employees": 45, "arr_usd": 2800000}'::jsonb
    ),

    -- 4. OnClick - Digital Marketing Automation
    (
        'ONCLICK',
        'OnClick Marketing Digital Ltda.',
        'OnClick',
        '45.678.901/0001-23',
        'BRL',
        'USD',
        'IFRS',
        'BR',
        'active',
        v_holding_id,
        100.00,
        'full',
        '2024-12-31',
        '2018-09-10',
        '{"type": "operating_company", "segment": "SaaS", "vertical": "marketing_automation", "employees": 95, "arr_usd": 5600000}'::jsonb
    ),

    -- 5. Ipê Digital - E-commerce Platform
    (
        'IPEDIG',
        'Ipê Digital Comércio Eletrônico S.A.',
        'Ipê Digital',
        '56.789.012/0001-34',
        'BRL',
        'USD',
        'IFRS',
        'BR',
        'active',
        v_holding_id,
        100.00,
        'full',
        '2024-12-31',
        '2019-11-05',
        '{"type": "operating_company", "segment": "SaaS", "vertical": "ecommerce", "employees": 75, "arr_usd": 3900000}'::jsonb
    ),

    -- 6. Munddi - Multi-channel Payment Gateway
    (
        'MUNDDI',
        'Munddi Pagamentos Digitais Ltda.',
        'Munddi',
        '67.890.123/0001-45',
        'BRL',
        'USD',
        'IFRS',
        'BR',
        'active',
        v_holding_id,
        100.00,
        'full',
        '2024-12-31',
        '2020-04-12',
        '{"type": "operating_company", "segment": "FinTech", "vertical": "payments", "employees": 65, "arr_usd": 6200000}'::jsonb
    ),

    -- 7. Leadlovers - Marketing & CRM Platform
    (
        'LEADLVR',
        'Leadlovers Tecnologia e Marketing S.A.',
        'Leadlovers',
        '78.901.234/0001-56',
        'BRL',
        'USD',
        'IFRS',
        'BR',
        'active',
        v_holding_id,
        100.00,
        'full',
        '2024-12-31',
        '2016-02-28',
        '{"type": "operating_company", "segment": "SaaS", "vertical": "marketing_crm", "employees": 180, "arr_usd": 12400000}'::jsonb
    );
END $$;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify all entities were inserted
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count FROM portfolio_entities;

    IF v_count != 8 THEN
        RAISE EXCEPTION 'Expected 8 entities (1 holding + 7 operating), found %', v_count;
    END IF;

    RAISE NOTICE 'Successfully inserted % portfolio entities', v_count;
END $$;

-- Display entity hierarchy
SELECT
    CASE
        WHEN parent_entity_id IS NULL THEN entity_code
        ELSE '  ├─ ' || entity_code
    END as hierarchy,
    legal_name,
    functional_currency,
    presentation_currency,
    status,
    TO_CHAR(ownership_percentage, '999.99%') as ownership,
    consolidation_method,
    metadata->>'vertical' as vertical,
    (metadata->>'arr_usd')::INTEGER as arr_usd
FROM portfolio_entities
ORDER BY
    CASE WHEN parent_entity_id IS NULL THEN 0 ELSE 1 END,
    entity_code;

-- Summary statistics
SELECT
    COUNT(*) as total_entities,
    COUNT(*) FILTER (WHERE parent_entity_id IS NULL) as holding_companies,
    COUNT(*) FILTER (WHERE parent_entity_id IS NOT NULL) as operating_companies,
    SUM((metadata->>'arr_usd')::INTEGER) FILTER (WHERE parent_entity_id IS NOT NULL) as total_arr_usd,
    SUM((metadata->>'employees')::INTEGER) FILTER (WHERE parent_entity_id IS NOT NULL) as total_employees
FROM portfolio_entities;

-- ============================================================================
-- NOTES
-- ============================================================================

/*
Portfolio Structure:
- AI FP&A Holdings Ltd. (Parent)
  ├─ Effecti (Sales Enablement SaaS)
  ├─ Mercos (B2B Commerce SaaS)
  ├─ Datahub (Data Integration SaaS)
  ├─ OnClick (Marketing Automation SaaS)
  ├─ Ipê Digital (E-commerce SaaS)
  ├─ Munddi (Payment Gateway FinTech)
  └─ Leadlovers (Marketing & CRM SaaS)

Total Portfolio:
- 7 Operating Companies
- 665 Employees
- $43.6M ARR (as of seed data)
- 100% ownership (full consolidation)
- All Brazilian entities (BRL functional currency)
- USD presentation currency (IFRS)
- Fiscal year end: December 31

Next Steps:
1. Create user accounts with entity access
2. Seed standard chart of accounts
3. Map entity-specific COA to standard
4. Import historical trial balances
*/
