"""
IFRS to US GAAP reconciliation engine.
Handles key differences between accounting standards.
"""

from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from .models import (
    GAAPReconciliation,
    ConsolidatedFinancials,
    AccountingStandard,
    AuditLogEntry
)


class GAAPDifferenceHandler:
    """Handles individual GAAP differences and adjustments."""

    def __init__(self):
        self._audit_log: List[AuditLogEntry] = []

    def calculate_development_costs_adjustment(
        self,
        ifrs_capitalized_amount: Decimal,
        us_gaap_policy: str = "expense"
    ) -> Decimal:
        """
        Development Costs Difference:

        IFRS: Capitalize development costs when criteria met (IAS 38)
        US GAAP: Expense all R&D costs (ASC 730)

        Exception: Software development costs can be capitalized under ASC 985-20

        Args:
            ifrs_capitalized_amount: Amount capitalized under IFRS
            us_gaap_policy: "expense" or "capitalize"

        Returns:
            Adjustment amount (negative = reduce net income for US GAAP)
        """
        if us_gaap_policy == "expense":
            # Reverse capitalization for US GAAP
            adjustment = -ifrs_capitalized_amount
            self._audit_log.append(AuditLogEntry(
                action="GAAP_ADJUSTMENT",
                description=f"Development costs: Expensed {ifrs_capitalized_amount} under US GAAP"
            ))
            return adjustment

        return Decimal("0")

    def calculate_lease_classification_adjustment(
        self,
        ifrs_right_of_use_asset: Decimal,
        us_gaap_operating_lease_expense: Decimal,
        us_gaap_finance_lease_expense: Decimal
    ) -> Decimal:
        """
        Lease Classification Difference:

        IFRS 16: Single model - all leases on balance sheet
        US GAAP ASC 842: Dual model - operating vs. finance leases

        The impact is primarily on presentation, but can affect metrics.

        Returns:
            Adjustment to net income (usually minimal)
        """
        # Simplified: ASC 842 now similar to IFRS 16, differences are minimal
        # Main difference is in presentation and initial classification

        # For most practical purposes, adjustment is zero
        # unless there are specific lease modifications or sale-leasebacks
        return Decimal("0")

    def calculate_revenue_recognition_adjustment(
        self,
        ifrs_revenue: Decimal,
        us_gaap_revenue: Decimal,
        difference_reason: str = ""
    ) -> Decimal:
        """
        Revenue Recognition Difference:

        IFRS 15 and ASC 606 are largely converged, but differences exist in:
        - Principal vs. agent considerations
        - Licensing arrangements
        - Variable consideration constraints

        Args:
            ifrs_revenue: Revenue recognized under IFRS 15
            us_gaap_revenue: Revenue that would be recognized under ASC 606
            difference_reason: Explanation of the difference

        Returns:
            Adjustment amount
        """
        adjustment = us_gaap_revenue - ifrs_revenue

        if adjustment != Decimal("0"):
            self._audit_log.append(AuditLogEntry(
                action="GAAP_ADJUSTMENT",
                description=f"Revenue recognition: {difference_reason}, adjustment={adjustment}"
            ))

        return adjustment

    def calculate_goodwill_impairment_adjustment(
        self,
        ifrs_impairment: Decimal,
        us_gaap_impairment: Decimal
    ) -> Decimal:
        """
        Goodwill Impairment Difference:

        IFRS: Single-step impairment test (recoverable amount)
        US GAAP: Optional qualitative assessment, then quantitative if needed

        IFRS may result in earlier/larger impairments.

        Returns:
            Adjustment amount (positive = less impairment under US GAAP)
        """
        adjustment = ifrs_impairment - us_gaap_impairment

        if adjustment != Decimal("0"):
            self._audit_log.append(AuditLogEntry(
                action="GAAP_ADJUSTMENT",
                description=f"Goodwill impairment: IFRS={ifrs_impairment}, US GAAP={us_gaap_impairment}"
            ))

        return adjustment

    def calculate_financial_instruments_adjustment(
        self,
        ifrs_9_classification: str,
        us_gaap_classification: str,
        instrument_value: Decimal
    ) -> Decimal:
        """
        Financial Instruments Difference:

        IFRS 9 vs. ASC 320/321/815:
        - Classification and measurement differences
        - Impairment model (IFRS 9 uses expected credit loss)

        Returns:
            Adjustment amount
        """
        # Simplified: Most common difference is impairment timing
        # IFRS 9 expected credit loss is more forward-looking

        # This would require detailed analysis in production
        return Decimal("0")

    def calculate_inventory_costing_adjustment(
        self,
        ifrs_inventory_value: Decimal,
        us_gaap_allows_lifo: bool = True
    ) -> Decimal:
        """
        Inventory Costing Difference:

        IFRS: LIFO prohibited, only FIFO or weighted average
        US GAAP: LIFO allowed

        Returns:
            Adjustment if LIFO used under US GAAP
        """
        # This requires company-specific data on LIFO reserve
        # Placeholder for the adjustment logic
        return Decimal("0")


class ReconciliationEngine:
    """Creates IFRS to US GAAP reconciliation."""

    def __init__(self):
        self.difference_handler = GAAPDifferenceHandler()
        self._reconciliations: List[GAAPReconciliation] = []

    def create_reconciliation(
        self,
        ifrs_financials: ConsolidatedFinancials,
        adjustments: Dict[str, Decimal],
        period_end_date: date
    ) -> GAAPReconciliation:
        """
        Create a complete IFRS to US GAAP reconciliation.

        Args:
            ifrs_financials: Consolidated financials prepared under IFRS
            adjustments: Dict of adjustment category -> amount
            period_end_date: Period end date

        Returns:
            GAAPReconciliation object
        """
        # Start with IFRS net income
        ifrs_net_income = ifrs_financials.net_income

        # Calculate US GAAP net income
        total_adjustments = sum(adjustments.values())
        us_gaap_net_income = ifrs_net_income + total_adjustments

        reconciliation = GAAPReconciliation(
            period_end_date=period_end_date,
            ifrs_net_income=ifrs_net_income,
            us_gaap_net_income=us_gaap_net_income,
            adjustments=adjustments,
            development_costs_capitalization=adjustments.get("development_costs", Decimal("0")),
            lease_classification=adjustments.get("lease_classification", Decimal("0")),
            revenue_recognition=adjustments.get("revenue_recognition", Decimal("0")),
            goodwill_impairment=adjustments.get("goodwill_impairment", Decimal("0")),
            other_adjustments=adjustments.get("other", Decimal("0"))
        )

        # Validate reconciliation
        is_valid = reconciliation.validate_reconciliation()
        if not is_valid:
            raise ValueError(
                f"Reconciliation does not balance: "
                f"IFRS {ifrs_net_income} + Adj {total_adjustments} != US GAAP {us_gaap_net_income}"
            )

        self._reconciliations.append(reconciliation)
        return reconciliation

    def generate_reconciliation_table(
        self,
        reconciliation: GAAPReconciliation
    ) -> List[Tuple[str, Decimal]]:
        """
        Generate reconciliation table for reporting.

        Returns:
            List of (description, amount) tuples
        """
        table = [
            ("Net Income (IFRS)", reconciliation.ifrs_net_income),
        ]

        # Add adjustments
        if reconciliation.development_costs_capitalization != Decimal("0"):
            table.append((
                "Development costs adjustment",
                reconciliation.development_costs_capitalization
            ))

        if reconciliation.lease_classification != Decimal("0"):
            table.append((
                "Lease classification adjustment",
                reconciliation.lease_classification
            ))

        if reconciliation.revenue_recognition != Decimal("0"):
            table.append((
                "Revenue recognition adjustment",
                reconciliation.revenue_recognition
            ))

        if reconciliation.goodwill_impairment != Decimal("0"):
            table.append((
                "Goodwill impairment adjustment",
                reconciliation.goodwill_impairment
            ))

        if reconciliation.other_adjustments != Decimal("0"):
            table.append((
                "Other adjustments",
                reconciliation.other_adjustments
            ))

        # Total adjustments
        table.append((
            "Total adjustments",
            reconciliation.total_adjustments
        ))

        # US GAAP result
        table.append((
            "Net Income (US GAAP)",
            reconciliation.us_gaap_net_income
        ))

        return table

    def format_reconciliation_disclosure(
        self,
        reconciliation: GAAPReconciliation
    ) -> str:
        """
        Format reconciliation as disclosure text for SEC filing.

        Returns:
            Formatted disclosure text
        """
        table = self.generate_reconciliation_table(reconciliation)

        disclosure = "RECONCILIATION OF NET INCOME UNDER IFRS TO US GAAP\n"
        disclosure += "=" * 70 + "\n\n"

        for description, amount in table:
            # Format amount with thousands separator
            amount_str = f"${amount:,.2f}"
            disclosure += f"{description:<50} {amount_str:>18}\n"

        disclosure += "\n" + "=" * 70 + "\n"

        # Add narrative explanation
        disclosure += "\nNotes:\n"
        disclosure += self._generate_adjustment_notes(reconciliation)

        return disclosure

    def _generate_adjustment_notes(self, reconciliation: GAAPReconciliation) -> str:
        """Generate explanatory notes for adjustments."""
        notes = []

        if reconciliation.development_costs_capitalization != Decimal("0"):
            notes.append(
                "Development Costs: Under IFRS, development costs meeting "
                "certain criteria are capitalized. Under US GAAP, research and "
                "development costs are generally expensed as incurred."
            )

        if reconciliation.goodwill_impairment != Decimal("0"):
            notes.append(
                "Goodwill Impairment: IFRS uses a single-step impairment test, "
                "while US GAAP allows for qualitative assessment. This may result "
                "in timing differences in impairment recognition."
            )

        if reconciliation.revenue_recognition != Decimal("0"):
            notes.append(
                "Revenue Recognition: While IFRS 15 and ASC 606 are largely "
                "converged, differences exist in specific areas such as principal "
                "vs. agent considerations and licensing arrangements."
            )

        return "\n\n".join(f"{i+1}. {note}" for i, note in enumerate(notes))


class DualReportingEngine:
    """
    Manages dual reporting under both IFRS and US GAAP.
    Useful for foreign private issuers reporting on US exchanges.
    """

    def __init__(self):
        self.reconciliation_engine = ReconciliationEngine()
        self._ifrs_financials: Dict[date, ConsolidatedFinancials] = {}
        self._us_gaap_financials: Dict[date, ConsolidatedFinancials] = {}

    def prepare_dual_reporting(
        self,
        ifrs_financials: ConsolidatedFinancials,
        adjustments: Dict[str, Decimal]
    ) -> Tuple[ConsolidatedFinancials, GAAPReconciliation]:
        """
        Prepare both IFRS and US GAAP financials with reconciliation.

        Args:
            ifrs_financials: Consolidated financials under IFRS
            adjustments: GAAP adjustments

        Returns:
            (us_gaap_financials, reconciliation)
        """
        # Create reconciliation
        reconciliation = self.reconciliation_engine.create_reconciliation(
            ifrs_financials,
            adjustments,
            ifrs_financials.period_end_date
        )

        # Create US GAAP version by applying adjustments
        us_gaap_financials = self._apply_adjustments_to_financials(
            ifrs_financials,
            adjustments
        )

        # Store both versions
        self._ifrs_financials[ifrs_financials.period_end_date] = ifrs_financials
        self._us_gaap_financials[ifrs_financials.period_end_date] = us_gaap_financials

        return us_gaap_financials, reconciliation

    def _apply_adjustments_to_financials(
        self,
        ifrs_financials: ConsolidatedFinancials,
        adjustments: Dict[str, Decimal]
    ) -> ConsolidatedFinancials:
        """Apply GAAP adjustments to create US GAAP version of financials."""
        # Create a copy of IFRS financials
        us_gaap = ConsolidatedFinancials(
            period_end_date=ifrs_financials.period_end_date,
            presentation_currency=ifrs_financials.presentation_currency,
            accounting_standard=AccountingStandard.US_GAAP,
            entities_included=ifrs_financials.entities_included.copy(),
            trial_balance=ifrs_financials.trial_balance.copy(),
            eliminations=ifrs_financials.eliminations.copy(),
            ppa_adjustments=ifrs_financials.ppa_adjustments.copy(),
            total_assets=ifrs_financials.total_assets,
            total_liabilities=ifrs_financials.total_liabilities,
            total_equity=ifrs_financials.total_equity,
            total_revenue=ifrs_financials.total_revenue,
            total_expenses=ifrs_financials.total_expenses,
            total_cta=ifrs_financials.total_cta
        )

        # Apply adjustments to net income
        total_adjustments = sum(adjustments.values())
        us_gaap.net_income = ifrs_financials.net_income + total_adjustments

        # Adjust equity for retained earnings impact
        us_gaap.total_equity = ifrs_financials.total_equity + total_adjustments

        # Validate balance
        us_gaap.validate_balance()

        return us_gaap

    def get_comparative_financials(
        self,
        period_end_date: date
    ) -> Tuple[Optional[ConsolidatedFinancials], Optional[ConsolidatedFinancials]]:
        """Get both IFRS and US GAAP financials for comparison."""
        ifrs = self._ifrs_financials.get(period_end_date)
        us_gaap = self._us_gaap_financials.get(period_end_date)
        return ifrs, us_gaap
