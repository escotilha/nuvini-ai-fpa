-- ============================================================================
-- AI FP&A Monthly Close Automation - Standard Chart of Accounts
-- ============================================================================
-- Version: 1.0.0
-- Created: 2026-02-07
-- Description: IFRS/US GAAP compliant standard chart of accounts
-- ============================================================================

-- ============================================================================
-- ASSETS (1000-1999)
-- ============================================================================

-- CURRENT ASSETS (1000-1499)
INSERT INTO standard_chart_of_accounts (account_code, account_name, account_type, account_subtype, normal_balance, parent_account_id, level, is_control_account, is_posting_account, accounting_standard, ifrs_tag, us_gaap_tag, description) VALUES
('1000', 'Current Assets', 'asset', 'current_asset', 'debit', NULL, 1, true, false, 'IFRS', 'CurrentAssets', 'AssetsCurrent', 'Total current assets'),
('1100', 'Cash and Cash Equivalents', 'asset', 'current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1000'), 2, true, false, 'IFRS', 'CashAndCashEquivalents', 'CashAndCashEquivalentsAtCarryingValue', 'All cash and near-cash instruments'),
('1110', 'Cash on Hand', 'asset', 'current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1100'), 3, false, true, 'IFRS', 'Cash', 'Cash', 'Physical cash and petty cash'),
('1120', 'Cash in Bank - Operating Account', 'asset', 'current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1100'), 3, false, true, 'IFRS', 'CashInBank', 'CashAndDueFromBanks', 'Operating bank accounts'),
('1130', 'Cash in Bank - Payroll Account', 'asset', 'current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1100'), 3, false, true, 'IFRS', 'CashInBank', 'CashAndDueFromBanks', 'Dedicated payroll accounts'),
('1140', 'Short-term Investments', 'asset', 'current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1100'), 3, false, true, 'IFRS', 'ShortTermInvestments', 'ShortTermInvestments', 'Liquid investments < 90 days'),

('1200', 'Trade and Other Receivables', 'asset', 'current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1000'), 2, true, false, 'IFRS', 'TradeAndOtherCurrentReceivables', 'AccountsReceivableNetCurrent', 'Customer receivables and other current receivables'),
('1210', 'Accounts Receivable - Trade', 'asset', 'current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1200'), 3, false, true, 'IFRS', 'TradeReceivables', 'AccountsReceivableNetCurrent', 'Trade receivables from customers', true),
('1215', 'Allowance for Doubtful Accounts', 'asset', 'current_asset', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1200'), 3, false, true, 'IFRS', 'AllowanceForDoubtfulAccounts', 'AllowanceForDoubtfulAccountsReceivableCurrent', 'Contra-asset for bad debt reserve'),
('1220', 'Unbilled Receivables', 'asset', 'current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1200'), 3, false, true, 'IFRS', 'ContractAssets', 'ContractWithCustomerAssetNetCurrent', 'Accrued revenue not yet billed'),
('1230', 'Other Receivables', 'asset', 'current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1200'), 3, false, true, 'IFRS', 'OtherCurrentReceivables', 'OtherReceivablesNetCurrent', 'Non-trade receivables'),

('1300', 'Inventory', 'asset', 'current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1000'), 2, true, false, 'IFRS', 'Inventories', 'InventoryNet', 'Inventory (if applicable)'),
('1310', 'Raw Materials', 'asset', 'current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1300'), 3, false, true, 'IFRS', 'RawMaterials', 'InventoryRawMaterialsNetOfReserves', 'Raw materials inventory'),
('1320', 'Work in Progress', 'asset', 'current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1300'), 3, false, true, 'IFRS', 'WorkInProgress', 'InventoryWorkInProcessNetOfReserves', 'WIP inventory'),
('1330', 'Finished Goods', 'asset', 'current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1300'), 3, false, true, 'IFRS', 'FinishedGoods', 'InventoryFinishedGoodsNetOfReserves', 'Finished goods inventory'),

('1400', 'Prepaid Expenses and Other Current Assets', 'asset', 'current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1000'), 2, true, false, 'IFRS', 'PrepaidExpensesAndOtherAssetsCurrent', 'PrepaidExpenseAndOtherAssetsCurrent', 'Prepaid and other current assets'),
('1410', 'Prepaid Insurance', 'asset', 'current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1400'), 3, false, true, 'IFRS', 'PrepaidInsurance', 'PrepaidInsurance', 'Prepaid insurance premiums'),
('1420', 'Prepaid Software Licenses', 'asset', 'current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1400'), 3, false, true, 'IFRS', 'PrepaidExpenses', 'PrepaidExpenseCurrent', 'Prepaid SaaS and software subscriptions'),
('1430', 'Prepaid Rent', 'asset', 'current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1400'), 3, false, true, 'IFRS', 'PrepaidRent', 'PrepaidRent', 'Prepaid office rent'),
('1440', 'Deferred Contract Costs', 'asset', 'current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1400'), 3, false, true, 'IFRS', 'DeferredCosts', 'CapitalizedContractCostNetCurrent', 'Deferred sales commissions and costs'),
('1450', 'Tax Credits Recoverable', 'asset', 'current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1400'), 3, false, true, 'IFRS', 'CurrentTaxAssets', 'IncomeTaxReceivable', 'Tax credits and refunds receivable'),

-- NON-CURRENT ASSETS (1500-1999)
('1500', 'Non-Current Assets', 'asset', 'non_current_asset', 'debit', NULL, 1, true, false, 'IFRS', 'NoncurrentAssets', 'AssetsNoncurrent', 'Total non-current assets'),
('1600', 'Property, Plant and Equipment', 'asset', 'non_current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1500'), 2, true, false, 'IFRS', 'PropertyPlantAndEquipment', 'PropertyPlantAndEquipmentNet', 'PP&E net of depreciation'),
('1610', 'Computer Equipment', 'asset', 'non_current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1600'), 3, false, true, 'IFRS', 'ComputerEquipment', 'ComputerEquipmentGross', 'Computers and servers'),
('1615', 'Accumulated Depreciation - Computer Equipment', 'asset', 'non_current_asset', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1600'), 3, false, true, 'IFRS', 'AccumulatedDepreciation', 'AccumulatedDepreciationDepletionAndAmortizationPropertyPlantAndEquipment', 'Accumulated depreciation contra-asset'),
('1620', 'Furniture and Fixtures', 'asset', 'non_current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1600'), 3, false, true, 'IFRS', 'FurnitureAndFixtures', 'FurnitureAndFixturesGross', 'Office furniture'),
('1625', 'Accumulated Depreciation - Furniture', 'asset', 'non_current_asset', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1600'), 3, false, true, 'IFRS', 'AccumulatedDepreciation', 'AccumulatedDepreciationDepletionAndAmortizationPropertyPlantAndEquipment', 'Accumulated depreciation contra-asset'),
('1630', 'Leasehold Improvements', 'asset', 'non_current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1600'), 3, false, true, 'IFRS', 'LeaseholdImprovements', 'LeaseholdImprovementsGross', 'Office improvements'),
('1635', 'Accumulated Amortization - Leasehold', 'asset', 'non_current_asset', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1600'), 3, false, true, 'IFRS', 'AccumulatedAmortization', 'AccumulatedDepreciationDepletionAndAmortizationPropertyPlantAndEquipment', 'Accumulated amortization contra-asset'),

('1700', 'Intangible Assets', 'asset', 'non_current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1500'), 2, true, false, 'IFRS', 'IntangibleAssetsOtherThanGoodwill', 'IntangibleAssetsNetExcludingGoodwill', 'Intangible assets excluding goodwill'),
('1710', 'Software and Technology', 'asset', 'non_current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1700'), 3, false, true, 'IFRS', 'Software', 'SoftwareAndSoftwareDevelopmentCostsGross', 'Capitalized software development'),
('1715', 'Accumulated Amortization - Software', 'asset', 'non_current_asset', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1700'), 3, false, true, 'IFRS', 'AccumulatedAmortization', 'AccumulatedAmortizationOfIntangibleAssets', 'Accumulated amortization contra-asset'),
('1720', 'Goodwill', 'asset', 'non_current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1500'), 2, false, true, 'IFRS', 'Goodwill', 'Goodwill', 'Goodwill from acquisitions'),
('1730', 'Customer Relationships', 'asset', 'non_current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1700'), 3, false, true, 'IFRS', 'CustomerRelationships', 'CustomerRelationships', 'Intangible customer relationships'),
('1735', 'Accumulated Amortization - Customer Relationships', 'asset', 'non_current_asset', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1700'), 3, false, true, 'IFRS', 'AccumulatedAmortization', 'AccumulatedAmortizationOfIntangibleAssets', 'Accumulated amortization contra-asset'),

('1800', 'Right-of-Use Assets', 'asset', 'non_current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1500'), 2, true, false, 'IFRS', 'RightOfUseAssets', 'OperatingLeaseRightOfUseAsset', 'IFRS 16 / ASC 842 lease assets'),
('1810', 'ROU Asset - Office Lease', 'asset', 'non_current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1800'), 3, false, true, 'IFRS', 'RightOfUseAssets', 'OperatingLeaseRightOfUseAsset', 'Office lease ROU assets'),
('1815', 'Accumulated Amortization - ROU Assets', 'asset', 'non_current_asset', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1800'), 3, false, true, 'IFRS', 'AccumulatedAmortization', 'OperatingLeaseRightOfUseAssetAmortizationExpense', 'ROU asset amortization'),

('1900', 'Other Non-Current Assets', 'asset', 'non_current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1500'), 2, true, false, 'IFRS', 'OtherNoncurrentAssets', 'OtherAssetsNoncurrent', 'Other long-term assets'),
('1910', 'Security Deposits', 'asset', 'non_current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1900'), 3, false, true, 'IFRS', 'SecurityDeposits', 'DepositsAssetsNoncurrent', 'Long-term security deposits'),
('1920', 'Deferred Tax Assets', 'asset', 'non_current_asset', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '1900'), 3, false, true, 'IFRS', 'DeferredTaxAssets', 'DeferredTaxAssetsNetNoncurrent', 'Deferred tax assets');

-- ============================================================================
-- LIABILITIES (2000-2999)
-- ============================================================================

-- CURRENT LIABILITIES (2000-2499)
INSERT INTO standard_chart_of_accounts (account_code, account_name, account_type, account_subtype, normal_balance, parent_account_id, level, is_control_account, is_posting_account, accounting_standard, ifrs_tag, us_gaap_tag, description) VALUES
('2000', 'Current Liabilities', 'liability', 'current_liability', 'credit', NULL, 1, true, false, 'IFRS', 'CurrentLiabilities', 'LiabilitiesCurrent', 'Total current liabilities'),
('2100', 'Accounts Payable and Accrued Liabilities', 'liability', 'current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2000'), 2, true, false, 'IFRS', 'TradeAndOtherCurrentPayables', 'AccountsPayableAndAccruedLiabilitiesCurrent', 'Trade payables and accruals'),
('2110', 'Accounts Payable - Trade', 'liability', 'current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2100'), 3, false, true, 'IFRS', 'TradePayables', 'AccountsPayableCurrent', 'Trade payables to vendors', true),
('2120', 'Accrued Expenses', 'liability', 'current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2100'), 3, false, true, 'IFRS', 'AccruedExpenses', 'AccruedLiabilitiesCurrent', 'General accrued expenses'),
('2130', 'Accrued Payroll', 'liability', 'current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2100'), 3, false, true, 'IFRS', 'AccruedPayroll', 'EmployeeRelatedLiabilitiesCurrent', 'Payroll accruals'),
('2140', 'Accrued Bonuses', 'liability', 'current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2100'), 3, false, true, 'IFRS', 'AccruedBonuses', 'AccruedBonusesCurrent', 'Accrued employee bonuses'),
('2150', 'Accrued Vacation', 'liability', 'current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2100'), 3, false, true, 'IFRS', 'AccruedVacation', 'AccruedVacationCurrent', 'Accrued vacation liability'),

('2200', 'Deferred Revenue', 'liability', 'current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2000'), 2, true, false, 'IFRS', 'DeferredRevenue', 'ContractWithCustomerLiabilityCurrent', 'Unearned revenue from customers'),
('2210', 'Deferred Revenue - Annual Subscriptions', 'liability', 'current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2200'), 3, false, true, 'IFRS', 'DeferredRevenue', 'ContractWithCustomerLiabilityCurrent', 'Deferred SaaS subscription revenue', true),
('2220', 'Deferred Revenue - Professional Services', 'liability', 'current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2200'), 3, false, true, 'IFRS', 'DeferredRevenue', 'ContractWithCustomerLiabilityCurrent', 'Deferred professional services revenue'),

('2300', 'Short-term Debt', 'liability', 'current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2000'), 2, true, false, 'IFRS', 'ShorttermBorrowings', 'ShortTermBorrowings', 'Short-term borrowings'),
('2310', 'Short-term Bank Loans', 'liability', 'current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2300'), 3, false, true, 'IFRS', 'ShorttermBankLoans', 'BankOverdrafts', 'Short-term bank financing'),
('2320', 'Current Portion of Long-term Debt', 'liability', 'current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2300'), 3, false, true, 'IFRS', 'CurrentPortionOfLongtermDebt', 'LongTermDebtCurrent', 'Current portion of LT debt'),

('2400', 'Taxes Payable', 'liability', 'current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2000'), 2, true, false, 'IFRS', 'CurrentTaxLiabilities', 'AccruedIncomeTaxesCurrent', 'Tax liabilities'),
('2410', 'Income Tax Payable', 'liability', 'current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2400'), 3, false, true, 'IFRS', 'IncomeTaxPayable', 'AccruedIncomeTaxesCurrent', 'Income tax liability'),
('2420', 'Payroll Taxes Payable', 'liability', 'current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2400'), 3, false, true, 'IFRS', 'PayrollTaxes', 'EmployeeRelatedLiabilitiesCurrent', 'Employer payroll taxes'),
('2430', 'Sales Tax Payable', 'liability', 'current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2400'), 3, false, true, 'IFRS', 'SalesTaxPayable', 'SalesTaxPayableCurrent', 'VAT/Sales tax payable'),

('2450', 'Current Lease Liabilities', 'liability', 'current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2000'), 2, false, true, 'IFRS', 'CurrentLeaseLiabilities', 'OperatingLeaseLiabilityCurrent', 'Current portion of lease liabilities'),

-- NON-CURRENT LIABILITIES (2500-2999)
('2500', 'Non-Current Liabilities', 'liability', 'non_current_liability', 'credit', NULL, 1, true, false, 'IFRS', 'NoncurrentLiabilities', 'LiabilitiesNoncurrent', 'Total non-current liabilities'),
('2600', 'Long-term Debt', 'liability', 'non_current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2500'), 2, true, false, 'IFRS', 'LongtermBorrowings', 'LongTermDebtNoncurrent', 'Long-term borrowings'),
('2610', 'Term Loans', 'liability', 'non_current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2600'), 3, false, true, 'IFRS', 'TermLoans', 'SeniorNotes', 'Long-term bank loans'),
('2620', 'Convertible Notes', 'liability', 'non_current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2600'), 3, false, true, 'IFRS', 'ConvertibleDebt', 'ConvertibleDebt', 'Convertible debt instruments'),

('2700', 'Non-Current Lease Liabilities', 'liability', 'non_current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2500'), 2, false, true, 'IFRS', 'NoncurrentLeaseLiabilities', 'OperatingLeaseLiabilityNoncurrent', 'Long-term lease liabilities'),

('2800', 'Deferred Tax Liabilities', 'liability', 'non_current_liability', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '2500'), 2, false, true, 'IFRS', 'DeferredTaxLiabilities', 'DeferredTaxLiabilitiesNoncurrent', 'Deferred tax liabilities');

-- ============================================================================
-- EQUITY (3000-3999)
-- ============================================================================

INSERT INTO standard_chart_of_accounts (account_code, account_name, account_type, account_subtype, normal_balance, parent_account_id, level, is_control_account, is_posting_account, accounting_standard, ifrs_tag, us_gaap_tag, description) VALUES
('3000', 'Equity', 'equity', 'contributed_capital', 'credit', NULL, 1, true, false, 'IFRS', 'Equity', 'StockholdersEquity', 'Total equity'),
('3100', 'Share Capital', 'equity', 'contributed_capital', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '3000'), 2, false, true, 'IFRS', 'IssuedCapital', 'CommonStockValue', 'Issued share capital'),
('3200', 'Additional Paid-in Capital', 'equity', 'contributed_capital', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '3000'), 2, false, true, 'IFRS', 'SharePremium', 'AdditionalPaidInCapital', 'Share premium'),
('3300', 'Retained Earnings', 'equity', 'retained_earnings', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '3000'), 2, false, true, 'IFRS', 'RetainedEarnings', 'RetainedEarningsAccumulatedDeficit', 'Accumulated retained earnings'),
('3400', 'Other Comprehensive Income', 'equity', 'other_equity', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '3000'), 2, false, true, 'IFRS', 'OtherComprehensiveIncome', 'AccumulatedOtherComprehensiveIncomeLossNetOfTax', 'Accumulated OCI'),
('3410', 'Foreign Currency Translation Reserve', 'equity', 'other_equity', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '3400'), 3, false, true, 'IFRS', 'ForeignCurrencyTranslationReserve', 'AccumulatedOtherComprehensiveIncomeLossForeignCurrencyTranslationAdjustmentNetOfTax', 'FX translation adjustments');

-- ============================================================================
-- REVENUE (4000-4999)
-- ============================================================================

INSERT INTO standard_chart_of_accounts (account_code, account_name, account_type, account_subtype, normal_balance, parent_account_id, level, is_control_account, is_posting_account, accounting_standard, ifrs_tag, us_gaap_tag, description) VALUES
('4000', 'Revenue', 'revenue', 'operating_revenue', 'credit', NULL, 1, true, false, 'IFRS', 'Revenue', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'Total revenue'),
('4100', 'Subscription Revenue', 'revenue', 'operating_revenue', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '4000'), 2, false, true, 'IFRS', 'SubscriptionRevenue', 'SoftwareRevenueRecurring', 'Recurring SaaS subscription revenue', true),
('4200', 'Professional Services Revenue', 'revenue', 'operating_revenue', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '4000'), 2, false, true, 'IFRS', 'ServiceRevenue', 'ServiceMember', 'Implementation and consulting revenue'),
('4300', 'Transaction Revenue', 'revenue', 'operating_revenue', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '4000'), 2, false, true, 'IFRS', 'TransactionRevenue', 'TransactionProcessingServiceRevenue', 'Usage-based transaction fees'),
('4900', 'Other Revenue', 'revenue', 'non_operating_revenue', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '4000'), 2, false, true, 'IFRS', 'OtherRevenue', 'OtherSalesRevenueNet', 'Miscellaneous revenue');

-- ============================================================================
-- EXPENSES (5000-9999)
-- ============================================================================

INSERT INTO standard_chart_of_accounts (account_code, account_name, account_type, account_subtype, normal_balance, parent_account_id, level, is_control_account, is_posting_account, accounting_standard, ifrs_tag, us_gaap_tag, description) VALUES
('5000', 'Cost of Revenue', 'expense', 'cost_of_goods_sold', 'debit', NULL, 1, true, false, 'IFRS', 'CostOfSales', 'CostOfRevenue', 'Direct costs of delivering services'),
('5100', 'Hosting and Infrastructure', 'expense', 'cost_of_goods_sold', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '5000'), 2, false, true, 'IFRS', 'HostingCosts', 'CostOfGoodsAndServicesSoldOther', 'Cloud hosting and infrastructure costs', true),
('5200', 'Customer Support', 'expense', 'cost_of_goods_sold', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '5000'), 2, false, true, 'IFRS', 'CustomerSupportCosts', 'CustomerServiceExpense', 'Direct customer support costs'),
('5300', 'Third-party Services', 'expense', 'cost_of_goods_sold', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '5000'), 2, false, true, 'IFRS', 'SubcontractorCosts', 'CostOfGoodsAndServicesSoldOther', 'Third-party service costs'),

('6000', 'Operating Expenses', 'expense', 'operating_expense', 'debit', NULL, 1, true, false, 'IFRS', 'OperatingExpenses', 'OperatingExpenses', 'Total operating expenses'),
('6100', 'Sales and Marketing', 'expense', 'operating_expense', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '6000'), 2, true, false, 'IFRS', 'SellingAndMarketingExpense', 'SellingAndMarketingExpense', 'Sales and marketing expenses'),
('6110', 'Salaries - Sales', 'expense', 'operating_expense', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '6100'), 3, false, true, 'IFRS', 'Salaries', 'LaborAndRelatedExpense', 'Sales team salaries'),
('6120', 'Sales Commissions', 'expense', 'operating_expense', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '6100'), 3, false, true, 'IFRS', 'Commissions', 'SalesCommissionExpense', 'Sales commissions'),
('6130', 'Marketing and Advertising', 'expense', 'operating_expense', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '6100'), 3, false, true, 'IFRS', 'MarketingExpense', 'MarketingAndAdvertisingExpense', 'Marketing campaigns'),

('6200', 'Research and Development', 'expense', 'operating_expense', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '6000'), 2, true, false, 'IFRS', 'ResearchAndDevelopmentExpense', 'ResearchAndDevelopmentExpense', 'R&D expenses'),
('6210', 'Salaries - Engineering', 'expense', 'operating_expense', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '6200'), 3, false, true, 'IFRS', 'Salaries', 'LaborAndRelatedExpense', 'Engineering salaries'),
('6220', 'Software and Tools', 'expense', 'operating_expense', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '6200'), 3, false, true, 'IFRS', 'SoftwareExpense', 'InformationTechnologyAndDataProcessing', 'Development tools and software'),

('6300', 'General and Administrative', 'expense', 'operating_expense', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '6000'), 2, true, false, 'IFRS', 'GeneralAndAdministrativeExpense', 'GeneralAndAdministrativeExpense', 'G&A expenses'),
('6310', 'Salaries - Administrative', 'expense', 'operating_expense', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '6300'), 3, false, true, 'IFRS', 'Salaries', 'LaborAndRelatedExpense', 'Admin staff salaries'),
('6320', 'Office Rent', 'expense', 'operating_expense', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '6300'), 3, false, true, 'IFRS', 'RentExpense', 'OperatingLeasesRentExpenseNet', 'Office lease expense'),
('6330', 'Professional Fees', 'expense', 'operating_expense', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '6300'), 3, false, true, 'IFRS', 'ProfessionalFees', 'ProfessionalFees', 'Legal, accounting, consulting fees'),
('6340', 'Insurance', 'expense', 'operating_expense', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '6300'), 3, false, true, 'IFRS', 'InsuranceExpense', 'GeneralInsuranceExpense', 'General insurance premiums'),
('6350', 'Depreciation and Amortization', 'expense', 'operating_expense', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '6300'), 3, false, true, 'IFRS', 'DepreciationAndAmortization', 'DepreciationDepletionAndAmortization', 'D&A expense'),

('7000', 'Other Income (Expense)', 'expense', 'non_operating_expense', 'debit', NULL, 1, true, false, 'IFRS', 'OtherIncomeExpense', 'NonoperatingIncomeExpense', 'Non-operating items'),
('7100', 'Interest Income', 'revenue', 'non_operating_revenue', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '7000'), 2, false, true, 'IFRS', 'InterestIncome', 'InterestIncomeOther', 'Interest earned'),
('7200', 'Interest Expense', 'expense', 'non_operating_expense', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '7000'), 2, false, true, 'IFRS', 'InterestExpense', 'InterestExpense', 'Interest on debt'),
('7300', 'Foreign Exchange Gain (Loss)', 'expense', 'non_operating_expense', 'debit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '7000'), 2, false, true, 'IFRS', 'ForeignExchangeGainLoss', 'ForeignCurrencyTransactionGainLossBeforeTax', 'FX gains and losses'),
('7400', 'Other Income', 'revenue', 'non_operating_revenue', 'credit', (SELECT account_id FROM standard_chart_of_accounts WHERE account_code = '7000'), 2, false, true, 'IFRS', 'OtherIncome', 'OtherNonoperatingIncomeExpense', 'Miscellaneous other income'),

('9000', 'Income Tax Expense', 'expense', 'operating_expense', 'debit', NULL, 1, false, true, 'IFRS', 'IncomeTaxExpense', 'IncomeTaxExpenseBenefit', 'Income tax provision');

-- Verify insertion
SELECT
    account_code,
    account_name,
    account_type,
    level,
    CASE WHEN is_control_account THEN 'Control' ELSE 'Posting' END as account_class
FROM standard_chart_of_accounts
ORDER BY account_code;

-- Summary statistics
SELECT
    account_type,
    COUNT(*) as total_accounts,
    COUNT(*) FILTER (WHERE is_control_account) as control_accounts,
    COUNT(*) FILTER (WHERE is_posting_account) as posting_accounts
FROM standard_chart_of_accounts
GROUP BY account_type
ORDER BY account_type;
