"""
Example usage of the ERP Connector Framework

This file demonstrates how to use the connectors for different ERP systems.
"""

import asyncio
from datetime import datetime, timedelta
from connectors import create_connector, get_erp_for_company


async def example_totvs_protheus():
    """Example: Connect to TOTVS Protheus and extract trial balance"""

    print("\n=== TOTVS Protheus Example ===")

    connector = create_connector(
        erp_type="totvs_protheus",
        auth_type="oauth2",
        credentials={
            "client_id": "your_client_id",
            "client_secret": "your_client_secret"
        },
        config={
            "base_url": "https://api.totvs.com.br",
            "tenant": "your_tenant_id",
            "environment": "PRODUCAO"
        }
    )

    async with connector:
        # Check connection health
        health = await connector.health_check()
        print(f"Status: {health.status.value}")
        print(f"Latency: {health.latency_ms:.2f}ms")

        # Get companies
        companies = await connector.get_companies()
        print(f"Found {len(companies)} companies")

        if companies:
            company = companies[0]
            company_id = company["id"]

            # Get trial balance for last year
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)

            trial_balance = await connector.get_trial_balance(
                company_id=company_id,
                period_start=start_date,
                period_end=end_date
            )

            print(f"\nTrial Balance for {trial_balance.company_name}")
            print(f"Period: {trial_balance.period_start.date()} to {trial_balance.period_end.date()}")
            print(f"Total accounts: {len(trial_balance.accounts)}")

            # Show top 5 accounts
            print("\nTop 5 accounts:")
            for account in trial_balance.accounts[:5]:
                print(f"  {account.account_code} - {account.account_name}")
                print(f"    Type: {account.account_type}")
                print(f"    Balance: {account.closing_balance:,.2f}")

            # Get subledger details for first account
            if trial_balance.accounts:
                first_account = trial_balance.accounts[0]
                entries = await connector.get_subledger_details(
                    company_id=company_id,
                    account_code=first_account.account_code,
                    period_start=start_date,
                    period_end=end_date
                )

                print(f"\nSubledger entries for {first_account.account_code}: {len(entries)}")
                if entries:
                    print("Latest 3 entries:")
                    for entry in entries[:3]:
                        print(f"  {entry.transaction_date.date()}: {entry.description}")
                        print(f"    Debit: {entry.debit_amount:,.2f}, Credit: {entry.credit_amount:,.2f}")


async def example_contaazul():
    """Example: Connect to ContaAzul and extract financial data"""

    print("\n=== ContaAzul Example ===")

    connector = create_connector(
        erp_type="contaazul",
        auth_type="oauth2",
        credentials={
            "client_id": "your_client_id",
            "client_secret": "your_client_secret"
        },
        config={
            "base_url": "https://api.contaazul.com"
        }
    )

    async with connector:
        # Get company info
        companies = await connector.get_companies()
        print(f"Company: {companies[0]['name']}")

        # Get chart of accounts
        chart = await connector.get_chart_of_accounts(
            company_id=companies[0]['id']
        )
        print(f"Chart of accounts has {len(chart)} accounts")


async def example_omie():
    """Example: Connect to Omie and extract data"""

    print("\n=== Omie Example ===")

    connector = create_connector(
        erp_type="omie",
        auth_type="api_key",
        credentials={
            "app_key": "your_app_key",
            "app_secret": "your_app_secret"
        },
        config={}
    )

    async with connector:
        # Get companies
        companies = await connector.get_companies()
        print(f"Found {len(companies)} companies:")
        for company in companies:
            print(f"  - {company['name']} (CNPJ: {company['document']})")


async def example_bling():
    """Example: Connect to Bling and extract data"""

    print("\n=== Bling Example ===")

    connector = create_connector(
        erp_type="bling",
        auth_type="api_key",
        credentials={
            "api_key": "your_api_key"
        },
        config={
            "api_version": "3"  # Use v3 JSON API
        }
    )

    async with connector:
        # Get company info
        companies = await connector.get_companies()
        print(f"Company: {companies[0]['name']}")


async def example_portfolio_company_lookup():
    """Example: Use portfolio company mapping"""

    print("\n=== Portfolio Company Lookup Example ===")

    companies = ["effecti", "mercos", "datahub", "leadlovers"]

    for company_name in companies:
        erp_type = get_erp_for_company(company_name)
        print(f"{company_name.capitalize()} uses: {erp_type.value if erp_type else 'Unknown'}")


async def example_error_handling():
    """Example: Proper error handling"""

    print("\n=== Error Handling Example ===")

    from connectors import ValidationError, RetryExhaustedError
    import httpx

    connector = create_connector(
        erp_type="totvs_protheus",
        auth_type="oauth2",
        credentials={
            "client_id": "test_id",
            "client_secret": "test_secret"
        },
        config={
            "tenant": "test_tenant"
        }
    )

    try:
        async with connector:
            trial_balance = await connector.get_trial_balance(
                company_id="01",
                period_start=datetime(2024, 1, 1),
                period_end=datetime(2024, 12, 31)
            )
            print(f"Successfully extracted trial balance with {len(trial_balance.accounts)} accounts")

    except ValidationError as e:
        print(f"Data validation error: {e}")
    except RetryExhaustedError as e:
        print(f"All retry attempts failed: {e}")
    except httpx.HTTPStatusError as e:
        print(f"HTTP error {e.response.status_code}: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


async def example_custom_filters():
    """Example: Using filters to refine data extraction"""

    print("\n=== Custom Filters Example ===")

    connector = create_connector(
        erp_type="totvs_protheus",
        auth_type="oauth2",
        credentials={
            "client_id": "your_client_id",
            "client_secret": "your_client_secret"
        },
        config={"tenant": "your_tenant"}
    )

    async with connector:
        # Extract trial balance with account range filter
        trial_balance = await connector.get_trial_balance(
            company_id="01",
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 12, 31),
            filters={
                "account_range": {
                    "from": "1.01.001",
                    "to": "1.99.999"
                },
                "cost_center": "CC001"
            }
        )

        print(f"Filtered accounts: {len(trial_balance.accounts)}")

        # Extract subledger with document type filter
        entries = await connector.get_subledger_details(
            company_id="01",
            account_code="1.01.001",
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 12, 31),
            filters={
                "document_type": "NF",  # Nota Fiscal
                "cost_center": "CC001"
            }
        )

        print(f"Filtered entries: {len(entries)}")


async def main():
    """Run all examples"""

    print("ERP Connector Framework - Examples")
    print("=" * 50)

    # Portfolio company lookup (doesn't require credentials)
    await example_portfolio_company_lookup()

    # Note: Other examples require valid credentials
    # Uncomment to run with actual credentials:

    # await example_totvs_protheus()
    # await example_contaazul()
    # await example_omie()
    # await example_bling()
    # await example_error_handling()
    # await example_custom_filters()


if __name__ == "__main__":
    asyncio.run(main())
