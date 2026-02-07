"""
Main consolidation engine for multi-entity financial consolidation.
Orchestrates FX conversion, eliminations, PPA, and GAAP reconciliation.
"""

from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from .models import (
    Entity,
    Currency,
    AccountingStandard,
    TrialBalanceEntry,
    ConvertedEntry,
    ConsolidatedFinancials,
    EliminationEntry,
    AmortizationEntry,
    GAAPReconciliation,
    AuditLogEntry
)
from .fx_converter import FXRateManager, FXConverter
from .eliminations import ConsolidationEliminator
from .ppa import PPAManager
from .gaap_reconciliation import ReconciliationEngine, DualReportingEngine


class ConsolidationEngine:
    """
    Main consolidation engine orchestrating all consolidation activities.

    Process flow:
    1. Load trial balances from all entities
    2. Convert to presentation currency (FX)
    3. Identify and eliminate intercompany transactions
    4. Apply PPA amortization entries
    5. Sum and validate consolidated balances
    6. Generate GAAP reconciliation if needed
    """

    def __init__(
        self,
        presentation_currency: Currency = Currency.USD,
        accounting_standard: AccountingStandard = AccountingStandard.IFRS
    ):
        self.presentation_currency = presentation_currency
        self.accounting_standard = accounting_standard

        # Initialize sub-components
        self.fx_rate_manager = FXRateManager()
        self.fx_converter = FXConverter(self.fx_rate_manager)
        self.eliminator = ConsolidationEliminator()
        self.ppa_manager = PPAManager()
        self.gaap_engine = ReconciliationEngine()
        self.dual_reporting = DualReportingEngine()

        # State
        self._entities: Dict[str, Entity] = {}
        self._trial_balances: Dict[str, List[TrialBalanceEntry]] = {}
        self._audit_log: List[AuditLogEntry] = []

    def register_entity(self, entity: Entity) -> None:
        """Register an entity in the consolidation group."""
        self._entities[entity.entity_id] = entity
        self._audit_log.append(AuditLogEntry(
            action="REGISTER_ENTITY",
            entity_id=entity.entity_id,
            description=f"Registered {entity.name} ({entity.ownership_percentage}% ownership)"
        ))

    def load_trial_balance(
        self,
        entity_id: str,
        entries: List[TrialBalanceEntry]
    ) -> None:
        """Load trial balance for an entity."""
        if entity_id not in self._entities:
            raise ValueError(f"Entity {entity_id} not registered")

        self._trial_balances[entity_id] = entries
        self._audit_log.append(AuditLogEntry(
            action="LOAD_TRIAL_BALANCE",
            entity_id=entity_id,
            description=f"Loaded {len(entries)} trial balance entries"
        ))

    def consolidate(
        self,
        period_end_date: date,
        period_start_date: date,
        chart_of_accounts: Dict[str, str],
        include_gaap_reconciliation: bool = False
    ) -> ConsolidatedFinancials:
        """
        Perform complete consolidation for a period.

        Args:
            period_end_date: Period end date
            period_start_date: Period start date (for average FX rates)
            chart_of_accounts: Mapping of account types to account codes
            include_gaap_reconciliation: Whether to generate US GAAP reconciliation

        Returns:
            ConsolidatedFinancials object
        """
        self._audit_log.append(AuditLogEntry(
            action="START_CONSOLIDATION",
            description=f"Starting consolidation for {period_end_date}"
        ))

        # Step 1: Convert all trial balances to presentation currency
        converted_entries = self._convert_all_trial_balances(
            period_start_date,
            period_end_date
        )

        # Step 2: Identify and eliminate intercompany transactions
        eliminations = self._perform_eliminations(
            period_end_date,
            chart_of_accounts
        )

        # Step 3: Calculate and apply PPA amortization
        ppa_entries = self._apply_ppa_amortization(period_end_date)

        # Step 4: Aggregate all entries
        consolidated = self._aggregate_consolidated_financials(
            converted_entries,
            eliminations,
            ppa_entries,
            period_end_date
        )

        # Step 5: Validate
        is_valid = consolidated.validate_balance()
        if not is_valid:
            self._audit_log.append(AuditLogEntry(
                action="VALIDATION_ERROR",
                description=f"Consolidation failed validation: {consolidated.validation_errors}"
            ))

        # Step 6: GAAP reconciliation if requested
        if include_gaap_reconciliation and self.accounting_standard == AccountingStandard.IFRS:
            # This would require adjustment inputs
            # Placeholder for now
            pass

        self._audit_log.append(AuditLogEntry(
            action="COMPLETE_CONSOLIDATION",
            consolidation_id=consolidated.consolidation_id,
            description=f"Consolidation complete: {len(self._entities)} entities"
        ))

        return consolidated

    def _convert_all_trial_balances(
        self,
        period_start_date: date,
        period_end_date: date
    ) -> List[ConvertedEntry]:
        """Convert all entity trial balances to presentation currency."""
        converted: List[ConvertedEntry] = []

        for entity_id, trial_balance in self._trial_balances.items():
            entity = self._entities[entity_id]

            for entry in trial_balance:
                converted_entry = self.fx_converter.convert_trial_balance_entry(
                    entry,
                    self.presentation_currency,
                    period_start_date
                )
                converted.append(converted_entry)

            self._audit_log.append(AuditLogEntry(
                action="CONVERT_CURRENCY",
                entity_id=entity_id,
                description=f"Converted {len(trial_balance)} entries from {entity.functional_currency} to {self.presentation_currency}"
            ))

        return converted

    def _perform_eliminations(
        self,
        period_end_date: date,
        chart_of_accounts: Dict[str, str]
    ) -> List[EliminationEntry]:
        """Identify and create elimination entries."""
        # Flatten all trial balances
        all_entries = []
        for entries in self._trial_balances.values():
            all_entries.extend(entries)

        # Build entity relationships (parent-subsidiary)
        relationships = {
            e.entity_id: e.parent_entity_id
            for e in self._entities.values()
            if e.parent_entity_id
        }

        # Build FX rate lookup
        fx_rates = {}
        for entity in self._entities.values():
            if entity.functional_currency != self.presentation_currency:
                rate = self.fx_rate_manager.get_rate(
                    entity.functional_currency,
                    self.presentation_currency,
                    period_end_date
                )
                if rate:
                    fx_rates[(entity.functional_currency, self.presentation_currency)] = rate

        # Perform eliminations
        eliminations, stats = self.eliminator.process_eliminations(
            all_entries,
            relationships,
            fx_rates,
            self.presentation_currency,
            period_end_date,
            chart_of_accounts
        )

        self._audit_log.append(AuditLogEntry(
            action="CREATE_ELIMINATIONS",
            description=f"Created {stats['total_eliminations']} eliminations totaling {stats['total_amount_eliminated']}"
        ))

        return eliminations

    def _apply_ppa_amortization(
        self,
        period_end_date: date
    ) -> List[AmortizationEntry]:
        """Calculate PPA amortization for all entities."""
        all_ppa_entries = []

        for entity_id in self._entities:
            ppa_entries = self.ppa_manager.get_monthly_ppa_entries(
                entity_id,
                period_end_date
            )
            all_ppa_entries.extend(ppa_entries)

        if all_ppa_entries:
            total_amortization = sum(e.monthly_amortization for e in all_ppa_entries)
            self._audit_log.append(AuditLogEntry(
                action="APPLY_PPA",
                description=f"Applied {len(all_ppa_entries)} PPA amortization entries totaling {total_amortization}"
            ))

        return all_ppa_entries

    def _aggregate_consolidated_financials(
        self,
        converted_entries: List[ConvertedEntry],
        eliminations: List[EliminationEntry],
        ppa_entries: List[AmortizationEntry],
        period_end_date: date
    ) -> ConsolidatedFinancials:
        """Aggregate all entries into consolidated financials."""
        consolidated = ConsolidatedFinancials(
            period_end_date=period_end_date,
            presentation_currency=self.presentation_currency,
            accounting_standard=self.accounting_standard,
            entities_included=list(self._entities.keys())
        )

        consolidated.trial_balance = converted_entries
        consolidated.eliminations = eliminations
        consolidated.ppa_adjustments = ppa_entries

        # Calculate totals from converted entries
        for entry in converted_entries:
            original = entry.original_entry

            # Assets
            if "asset" in original.account_type.value.lower():
                consolidated.total_assets += entry.converted_amount

            # Liabilities
            elif "liability" in original.account_type.value.lower():
                consolidated.total_liabilities += abs(entry.converted_amount)

            # Equity
            elif "equity" in original.account_type.value.lower():
                consolidated.total_equity += entry.converted_amount

            # Revenue
            elif "income" in original.account_type.value.lower():
                consolidated.total_revenue += entry.converted_amount

            # Expenses
            elif "expense" in original.account_type.value.lower():
                consolidated.total_expenses += abs(entry.converted_amount)

        # Apply eliminations
        for elim in eliminations:
            # Eliminations reduce both sides
            if "asset" in elim.debit_account.lower() or "receivable" in elim.debit_account.lower():
                consolidated.total_assets -= elim.elimination_amount
            if "liability" in elim.credit_account.lower() or "payable" in elim.credit_account.lower():
                consolidated.total_liabilities -= elim.elimination_amount
            if "revenue" in elim.debit_account.lower():
                consolidated.total_revenue -= elim.elimination_amount
            if "expense" in elim.credit_account.lower():
                consolidated.total_expenses -= elim.elimination_amount

        # Apply PPA amortization (increases expenses)
        total_ppa_amortization = sum(entry.monthly_amortization for entry in ppa_entries)
        consolidated.total_expenses += total_ppa_amortization

        # Calculate net income
        consolidated.net_income = consolidated.total_revenue - consolidated.total_expenses

        # Calculate total CTA
        consolidated.total_cta = self.fx_converter.get_total_cta()

        # Adjust equity for net income
        consolidated.total_equity += consolidated.net_income

        return consolidated

    def generate_consolidation_summary(
        self,
        consolidated: ConsolidatedFinancials
    ) -> Dict[str, any]:
        """Generate summary statistics for the consolidation."""
        return {
            "period_end_date": consolidated.period_end_date,
            "presentation_currency": consolidated.presentation_currency.value,
            "accounting_standard": consolidated.accounting_standard.value,
            "entities_count": len(consolidated.entities_included),
            "total_assets": float(consolidated.total_assets),
            "total_liabilities": float(consolidated.total_liabilities),
            "total_equity": float(consolidated.total_equity),
            "total_revenue": float(consolidated.total_revenue),
            "total_expenses": float(consolidated.total_expenses),
            "net_income": float(consolidated.net_income),
            "is_balanced": consolidated.is_balanced,
            "balance_difference": float(
                abs(consolidated.total_assets - (consolidated.total_liabilities + consolidated.total_equity))
            ),
            "eliminations_count": len(consolidated.eliminations),
            "ppa_adjustments_count": len(consolidated.ppa_adjustments),
            "total_cta": float(consolidated.total_cta)
        }

    def get_consolidation_audit_trail(self) -> List[AuditLogEntry]:
        """Get complete audit trail of consolidation process."""
        return self._audit_log.copy()


class QuickConsolidator:
    """
    Simplified consolidation interface for common use cases.
    Provides convenience methods for typical consolidation workflows.
    """

    def __init__(self):
        self.engine = ConsolidationEngine()

    def quick_consolidate(
        self,
        entities: List[Entity],
        trial_balances: Dict[str, List[TrialBalanceEntry]],
        period_end_date: date,
        period_start_date: date,
        presentation_currency: Currency = Currency.USD
    ) -> ConsolidatedFinancials:
        """
        Quick consolidation with sensible defaults.

        Args:
            entities: List of entities to consolidate
            trial_balances: Dict of entity_id -> trial balance entries
            period_end_date: Period end date
            period_start_date: Period start date
            presentation_currency: Presentation currency

        Returns:
            ConsolidatedFinancials
        """
        self.engine.presentation_currency = presentation_currency

        # Register all entities
        for entity in entities:
            self.engine.register_entity(entity)

        # Load all trial balances
        for entity_id, entries in trial_balances.items():
            self.engine.load_trial_balance(entity_id, entries)

        # Default chart of accounts
        default_coa = {
            "IC_RECEIVABLE": "2000",
            "IC_PAYABLE": "3000",
            "IC_REVENUE": "4000",
            "IC_EXPENSE": "5000",
            "FX_GAIN_LOSS": "7000",
            "DIVIDEND_INCOME": "4100",
            "DIVIDEND_PAYABLE": "3100",
            "EQUITY_INVESTMENT": "1500",
            "SUBSIDIARY_EQUITY": "2500"
        }

        # Consolidate
        return self.engine.consolidate(
            period_end_date,
            period_start_date,
            default_coa
        )

    def get_summary(self) -> Dict[str, any]:
        """Get summary of last consolidation."""
        # This would track the last consolidation
        # For now, return empty dict
        return {}
