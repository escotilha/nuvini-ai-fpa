"""
Intercompany elimination engine for multi-entity consolidation.
Handles receivables/payables, revenues/expenses, dividends, and equity investments.
"""

from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from .models import (
    Currency,
    EliminationType,
    IntercompanyTransaction,
    EliminationEntry,
    TrialBalanceEntry,
    ConvertedEntry,
    FXRate,
    AuditLogEntry
)


class IntercompanyMatcher:
    """Matches intercompany transactions across entities."""

    def __init__(self, tolerance_percentage: Decimal = Decimal("0.01")):
        """
        Initialize matcher with tolerance for FX differences.

        Args:
            tolerance_percentage: Tolerance as decimal (0.01 = 1%)
        """
        self.tolerance_percentage = tolerance_percentage
        self._audit_log: List[AuditLogEntry] = []

    def match_receivables_payables(
        self,
        receivables: List[TrialBalanceEntry],
        payables: List[TrialBalanceEntry],
        fx_rates: Dict[Tuple[Currency, Currency], FXRate]
    ) -> List[IntercompanyTransaction]:
        """
        Match intercompany receivables to payables.

        Matching criteria:
        1. Reference number (invoice number, transaction ID)
        2. Amount (within FX tolerance)
        3. Transaction date proximity
        """
        matches: List[IntercompanyTransaction] = []
        matched_receivable_ids = set()
        matched_payable_ids = set()

        for ar in receivables:
            for ap in payables:
                if ar.entry_id in matched_receivable_ids or ap.entry_id in matched_payable_ids:
                    continue

                # Check if entities are different
                if ar.entity_id == ap.entity_id:
                    continue

                # Try to match
                is_match, fx_difference = self._is_matching_pair(
                    ar, ap, fx_rates
                )

                if is_match:
                    transaction = IntercompanyTransaction(
                        entity_a_id=ar.entity_id,
                        entity_b_id=ap.entity_id,
                        elimination_type=EliminationType.RECEIVABLE_PAYABLE,
                        amount_entity_a=ar.amount_functional,
                        amount_entity_b=ap.amount_functional,
                        currency_a=ar.currency,
                        currency_b=ap.currency,
                        transaction_date=ar.period_end_date,
                        reference_number=ar.description,
                        fx_gain_loss=fx_difference
                    )
                    matches.append(transaction)
                    matched_receivable_ids.add(ar.entry_id)
                    matched_payable_ids.add(ap.entry_id)

                    # Log the match
                    self._audit_log.append(AuditLogEntry(
                        action="MATCH_INTERCOMPANY",
                        entity_id=ar.entity_id,
                        description=f"Matched AR {ar.entry_id} with AP {ap.entry_id}, FX diff: {fx_difference}"
                    ))

        # Log unmatched items
        unmatched_ar = len(receivables) - len(matched_receivable_ids)
        unmatched_ap = len(payables) - len(matched_payable_ids)

        if unmatched_ar > 0 or unmatched_ap > 0:
            self._audit_log.append(AuditLogEntry(
                action="UNMATCHED_INTERCOMPANY",
                description=f"Unmatched: {unmatched_ar} receivables, {unmatched_ap} payables"
            ))

        return matches

    def _is_matching_pair(
        self,
        entry_a: TrialBalanceEntry,
        entry_b: TrialBalanceEntry,
        fx_rates: Dict[Tuple[Currency, Currency], FXRate]
    ) -> Tuple[bool, Decimal]:
        """
        Check if two entries are matching intercompany items.

        Returns:
            (is_match, fx_difference)
        """
        # Convert both to common currency for comparison
        amount_a = entry_a.amount_functional
        amount_b = entry_b.amount_functional

        # If different currencies, convert
        if entry_a.currency != entry_b.currency:
            rate_key = (entry_a.currency, entry_b.currency)
            if rate_key in fx_rates:
                amount_a_converted = amount_a * fx_rates[rate_key].rate
                difference = abs(amount_a_converted - amount_b)
                tolerance = amount_b * self.tolerance_percentage

                is_match = difference <= tolerance
                fx_difference = amount_a_converted - amount_b if is_match else Decimal("0")
                return is_match, fx_difference

        # Same currency comparison
        difference = abs(amount_a - amount_b)
        tolerance = max(amount_a, amount_b) * self.tolerance_percentage

        is_match = difference <= tolerance
        return is_match, Decimal("0")

    def match_revenues_expenses(
        self,
        revenues: List[TrialBalanceEntry],
        expenses: List[TrialBalanceEntry],
        entity_relationships: Dict[str, str]
    ) -> List[IntercompanyTransaction]:
        """
        Match intercompany revenue/expense transactions.

        entity_relationships: dict of parent_id -> subsidiary_id mappings
        """
        matches: List[IntercompanyTransaction] = []

        # Group by description/reference for matching
        revenue_by_ref: Dict[str, List[TrialBalanceEntry]] = {}
        for rev in revenues:
            ref = rev.description or rev.account_code
            if ref not in revenue_by_ref:
                revenue_by_ref[ref] = []
            revenue_by_ref[ref].append(rev)

        for exp in expenses:
            ref = exp.description or exp.account_code
            if ref in revenue_by_ref:
                for rev in revenue_by_ref[ref]:
                    # Check entity relationship
                    if self._are_related_entities(
                        rev.entity_id, exp.entity_id, entity_relationships
                    ):
                        transaction = IntercompanyTransaction(
                            entity_a_id=rev.entity_id,
                            entity_b_id=exp.entity_id,
                            elimination_type=EliminationType.REVENUE_EXPENSE,
                            amount_entity_a=rev.amount_functional,
                            amount_entity_b=exp.amount_functional,
                            currency_a=rev.currency,
                            currency_b=exp.currency,
                            transaction_date=rev.period_end_date,
                            reference_number=ref
                        )
                        matches.append(transaction)

        return matches

    def _are_related_entities(
        self,
        entity_a: str,
        entity_b: str,
        relationships: Dict[str, str]
    ) -> bool:
        """Check if two entities have a parent-subsidiary relationship."""
        return (
            relationships.get(entity_a) == entity_b or
            relationships.get(entity_b) == entity_a
        )


class EliminationEngine:
    """Creates elimination journal entries for intercompany transactions."""

    def __init__(self):
        self._eliminations: List[EliminationEntry] = []
        self._audit_log: List[AuditLogEntry] = []

    def create_elimination_entry(
        self,
        transaction: IntercompanyTransaction,
        presentation_currency: Currency,
        period_end_date: date,
        chart_of_accounts: Dict[str, str]
    ) -> EliminationEntry:
        """
        Create elimination journal entry for an intercompany transaction.

        chart_of_accounts: mapping of elimination_type to account codes
        """
        elimination_type = transaction.elimination_type

        # Determine accounts based on elimination type
        if elimination_type == EliminationType.RECEIVABLE_PAYABLE:
            debit_account = chart_of_accounts.get("IC_PAYABLE", "IC Payables")
            credit_account = chart_of_accounts.get("IC_RECEIVABLE", "IC Receivables")
        elif elimination_type == EliminationType.REVENUE_EXPENSE:
            debit_account = chart_of_accounts.get("IC_REVENUE", "IC Revenue")
            credit_account = chart_of_accounts.get("IC_EXPENSE", "IC Expense")
        elif elimination_type == EliminationType.DIVIDEND:
            debit_account = chart_of_accounts.get("DIVIDEND_INCOME", "Dividend Income")
            credit_account = chart_of_accounts.get("DIVIDEND_PAYABLE", "Dividend Payable")
        elif elimination_type == EliminationType.EQUITY_INVESTMENT:
            debit_account = chart_of_accounts.get("EQUITY_INVESTMENT", "Investment in Subsidiary")
            credit_account = chart_of_accounts.get("SUBSIDIARY_EQUITY", "Subsidiary Equity")
        else:
            debit_account = "IC Debit"
            credit_account = "IC Credit"

        # Use the average of both amounts (should be similar)
        elimination_amount = (transaction.amount_entity_a + transaction.amount_entity_b) / 2

        # Handle FX gain/loss if exists
        fx_gain_loss_account = None
        if transaction.fx_gain_loss != Decimal("0"):
            fx_gain_loss_account = chart_of_accounts.get("FX_GAIN_LOSS", "FX Gain/Loss")

        elimination = EliminationEntry(
            intercompany_transaction=transaction,
            period_end_date=period_end_date,
            debit_account=debit_account,
            credit_account=credit_account,
            elimination_amount=elimination_amount,
            currency=presentation_currency,
            fx_gain_loss_account=fx_gain_loss_account,
            fx_gain_loss_amount=transaction.fx_gain_loss,
            notes=f"Elimination: {transaction.entity_a_id} <-> {transaction.entity_b_id}"
        )

        self._eliminations.append(elimination)

        # Log the elimination
        self._audit_log.append(AuditLogEntry(
            action="CREATE_ELIMINATION",
            entity_id=transaction.entity_a_id,
            description=f"Eliminated {elimination_type.value}: {elimination_amount} {presentation_currency.value}"
        ))

        return elimination

    def create_all_eliminations(
        self,
        transactions: List[IntercompanyTransaction],
        presentation_currency: Currency,
        period_end_date: date,
        chart_of_accounts: Dict[str, str]
    ) -> List[EliminationEntry]:
        """Create elimination entries for all matched transactions."""
        eliminations = []

        for transaction in transactions:
            elimination = self.create_elimination_entry(
                transaction,
                presentation_currency,
                period_end_date,
                chart_of_accounts
            )
            eliminations.append(elimination)

        return eliminations

    def get_elimination_summary(self) -> Dict[str, Decimal]:
        """Get summary of eliminations by type."""
        summary: Dict[str, Decimal] = {}

        for elim in self._eliminations:
            elim_type = elim.intercompany_transaction.elimination_type.value
            if elim_type not in summary:
                summary[elim_type] = Decimal("0")
            summary[elim_type] += elim.elimination_amount

        return summary

    def get_total_fx_impact(self) -> Decimal:
        """Get total FX gain/loss from eliminations."""
        return sum(elim.fx_gain_loss_amount for elim in self._eliminations)

    def get_eliminations(self) -> List[EliminationEntry]:
        """Get all elimination entries."""
        return self._eliminations.copy()

    def clear_eliminations(self) -> None:
        """Clear all elimination entries (for new period)."""
        self._eliminations.clear()


class ConsolidationEliminator:
    """
    High-level consolidation eliminator combining matching and elimination.
    """

    def __init__(self, tolerance_percentage: Decimal = Decimal("0.01")):
        self.matcher = IntercompanyMatcher(tolerance_percentage)
        self.engine = EliminationEngine()

    def process_eliminations(
        self,
        trial_balances: List[TrialBalanceEntry],
        entity_relationships: Dict[str, str],
        fx_rates: Dict[Tuple[Currency, Currency], FXRate],
        presentation_currency: Currency,
        period_end_date: date,
        chart_of_accounts: Dict[str, str]
    ) -> Tuple[List[EliminationEntry], Dict[str, any]]:
        """
        Complete elimination process.

        Returns:
            (elimination_entries, statistics)
        """
        # Separate entries by type
        receivables = [
            e for e in trial_balances
            if "receivable" in e.account_name.lower() and e.net_amount > 0
        ]
        payables = [
            e for e in trial_balances
            if "payable" in e.account_name.lower() and e.net_amount < 0
        ]
        revenues = [
            e for e in trial_balances
            if "revenue" in e.account_name.lower() or "income" in e.account_name.lower()
        ]
        expenses = [
            e for e in trial_balances
            if "expense" in e.account_name.lower() or "cost" in e.account_name.lower()
        ]

        # Match transactions
        ar_ap_matches = self.matcher.match_receivables_payables(
            receivables, payables, fx_rates
        )
        rev_exp_matches = self.matcher.match_revenues_expenses(
            revenues, expenses, entity_relationships
        )

        all_matches = ar_ap_matches + rev_exp_matches

        # Create elimination entries
        eliminations = self.engine.create_all_eliminations(
            all_matches,
            presentation_currency,
            period_end_date,
            chart_of_accounts
        )

        # Compile statistics
        statistics = {
            "total_eliminations": len(eliminations),
            "ar_ap_eliminations": len(ar_ap_matches),
            "rev_exp_eliminations": len(rev_exp_matches),
            "total_amount_eliminated": sum(e.elimination_amount for e in eliminations),
            "total_fx_impact": self.engine.get_total_fx_impact(),
            "elimination_summary": self.engine.get_elimination_summary()
        }

        return eliminations, statistics
