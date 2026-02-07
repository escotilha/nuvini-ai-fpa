"""
Validation rules and quality checks for consolidated financials.
Ensures accuracy, completeness, and compliance with accounting standards.
"""

from datetime import date
from decimal import Decimal
from typing import Dict, List, Tuple, Optional

from .models import (
    ConsolidatedFinancials,
    Entity,
    TrialBalanceEntry,
    ConvertedEntry,
    EliminationEntry,
    AccountingStandard,
    AuditLogEntry
)


class ValidationRule:
    """Base class for validation rules."""

    def __init__(self, rule_id: str, description: str, severity: str = "ERROR"):
        self.rule_id = rule_id
        self.description = description
        self.severity = severity  # ERROR, WARNING, INFO

    def validate(self, consolidated: ConsolidatedFinancials) -> Tuple[bool, Optional[str]]:
        """
        Validate the rule.

        Returns:
            (is_valid, error_message)
        """
        raise NotImplementedError()


class BalanceSheetBalanceRule(ValidationRule):
    """Validates that Assets = Liabilities + Equity."""

    def __init__(self, tolerance: Decimal = Decimal("0.01")):
        super().__init__(
            "BS_BALANCE",
            "Balance sheet must balance (Assets = Liabilities + Equity)",
            "ERROR"
        )
        self.tolerance = tolerance

    def validate(self, consolidated: ConsolidatedFinancials) -> Tuple[bool, Optional[str]]:
        difference = abs(
            consolidated.total_assets - (consolidated.total_liabilities + consolidated.total_equity)
        )

        is_valid = difference <= self.tolerance

        if not is_valid:
            return False, (
                f"Balance sheet out of balance by {difference}: "
                f"Assets={consolidated.total_assets}, "
                f"Liabilities+Equity={consolidated.total_liabilities + consolidated.total_equity}"
            )

        return True, None


class DebitCreditBalanceRule(ValidationRule):
    """Validates that total debits = total credits."""

    def __init__(self, tolerance: Decimal = Decimal("0.01")):
        super().__init__(
            "DR_CR_BALANCE",
            "Total debits must equal total credits",
            "ERROR"
        )
        self.tolerance = tolerance

    def validate(self, consolidated: ConsolidatedFinancials) -> Tuple[bool, Optional[str]]:
        total_debits = Decimal("0")
        total_credits = Decimal("0")

        for entry in consolidated.trial_balance:
            total_debits += entry.original_entry.debit_amount
            total_credits += entry.original_entry.credit_amount

        difference = abs(total_debits - total_credits)
        is_valid = difference <= self.tolerance

        if not is_valid:
            return False, (
                f"Debit/Credit imbalance: Debits={total_debits}, "
                f"Credits={total_credits}, Difference={difference}"
            )

        return True, None


class EntityOwnershipRule(ValidationRule):
    """Validates entity ownership percentages."""

    def __init__(self):
        super().__init__(
            "OWNERSHIP",
            "Entity ownership must be between 0% and 100%",
            "ERROR"
        )

    def validate(self, consolidated: ConsolidatedFinancials) -> Tuple[bool, Optional[str]]:
        # This requires access to entities, which we'd need to pass
        # For now, return True as placeholder
        return True, None


class NetIncomeReconciliationRule(ValidationRule):
    """Validates that net income = revenue - expenses."""

    def __init__(self, tolerance: Decimal = Decimal("0.01")):
        super().__init__(
            "NET_INCOME",
            "Net income must equal revenue minus expenses",
            "ERROR"
        )
        self.tolerance = tolerance

    def validate(self, consolidated: ConsolidatedFinancials) -> Tuple[bool, Optional[str]]:
        calculated_net_income = consolidated.total_revenue - consolidated.total_expenses
        difference = abs(consolidated.net_income - calculated_net_income)

        is_valid = difference <= self.tolerance

        if not is_valid:
            return False, (
                f"Net income mismatch: Reported={consolidated.net_income}, "
                f"Calculated={calculated_net_income}, Difference={difference}"
            )

        return True, None


class MinimumEntitiesRule(ValidationRule):
    """Validates minimum number of entities for consolidation."""

    def __init__(self, minimum: int = 2):
        super().__init__(
            "MIN_ENTITIES",
            f"Consolidation must include at least {minimum} entities",
            "WARNING"
        )
        self.minimum = minimum

    def validate(self, consolidated: ConsolidatedFinancials) -> Tuple[bool, Optional[str]]:
        entity_count = len(consolidated.entities_included)

        is_valid = entity_count >= self.minimum

        if not is_valid:
            return False, (
                f"Only {entity_count} entities included, "
                f"expected at least {self.minimum}"
            )

        return True, None


class EliminationCompletenessRule(ValidationRule):
    """Validates that material intercompany balances are eliminated."""

    def __init__(self, materiality_threshold: Decimal = Decimal("10000")):
        super().__init__(
            "ELIMINATION_COMPLETE",
            "All material intercompany transactions must be eliminated",
            "WARNING"
        )
        self.materiality_threshold = materiality_threshold

    def validate(self, consolidated: ConsolidatedFinancials) -> Tuple[bool, Optional[str]]:
        # Check for remaining intercompany accounts
        ic_accounts = [
            "intercompany", "ic ", "related party", "affiliate"
        ]

        remaining_balances = []

        for entry in consolidated.trial_balance:
            account_name_lower = entry.original_entry.account_name.lower()

            if any(ic_term in account_name_lower for ic_term in ic_accounts):
                if abs(entry.converted_amount) > self.materiality_threshold:
                    remaining_balances.append(
                        f"{entry.original_entry.account_name}: {entry.converted_amount}"
                    )

        if remaining_balances:
            return False, (
                f"Material intercompany balances remaining after elimination: "
                f"{', '.join(remaining_balances)}"
            )

        return True, None


class FXRateConsistencyRule(ValidationRule):
    """Validates FX rate consistency across entries."""

    def __init__(self):
        super().__init__(
            "FX_CONSISTENCY",
            "FX rates should be consistent for same currency pair and date",
            "WARNING"
        )

    def validate(self, consolidated: ConsolidatedFinancials) -> Tuple[bool, Optional[str]]:
        # Track rates by (from_currency, to_currency, date, rate_type)
        rate_groups: Dict[Tuple, List[Decimal]] = {}

        for entry in consolidated.trial_balance:
            key = (
                entry.fx_rate.from_currency,
                entry.fx_rate.to_currency,
                entry.fx_rate.rate_date,
                entry.fx_rate.rate_type
            )

            if key not in rate_groups:
                rate_groups[key] = []

            rate_groups[key].append(entry.fx_rate.rate)

        # Check for inconsistencies
        inconsistencies = []
        for key, rates in rate_groups.items():
            unique_rates = set(rates)
            if len(unique_rates) > 1:
                inconsistencies.append(
                    f"{key[0]}/{key[1]} on {key[2]}: {unique_rates}"
                )

        if inconsistencies:
            return False, (
                f"Inconsistent FX rates found: {', '.join(inconsistencies)}"
            )

        return True, None


class ReasonablenessRule(ValidationRule):
    """Validates reasonableness of financial ratios."""

    def __init__(self):
        super().__init__(
            "REASONABLENESS",
            "Financial metrics should be within reasonable ranges",
            "WARNING"
        )

    def validate(self, consolidated: ConsolidatedFinancials) -> Tuple[bool, Optional[str]]:
        warnings = []

        # Check for negative equity (may be legitimate but worth flagging)
        if consolidated.total_equity < 0:
            warnings.append("Negative equity position")

        # Check for negative assets (should never happen)
        if consolidated.total_assets < 0:
            warnings.append("Negative total assets (ERROR)")

        # Check for extremely high debt-to-equity
        if consolidated.total_equity > 0:
            debt_to_equity = consolidated.total_liabilities / consolidated.total_equity
            if debt_to_equity > 10:
                warnings.append(f"Very high debt-to-equity ratio: {debt_to_equity:.2f}")

        # Check for negative revenue (unusual)
        if consolidated.total_revenue < 0:
            warnings.append("Negative total revenue")

        if warnings:
            return False, f"Reasonableness checks: {'; '.join(warnings)}"

        return True, None


class ConsolidationValidator:
    """
    Comprehensive validation engine for consolidated financials.
    Runs all validation rules and compiles results.
    """

    def __init__(self, accuracy_target: Decimal = Decimal("0.999")):
        """
        Initialize validator.

        Args:
            accuracy_target: Target accuracy (0.999 = 99.9%)
        """
        self.accuracy_target = accuracy_target
        self.rules: List[ValidationRule] = []
        self._initialize_default_rules()

    def _initialize_default_rules(self) -> None:
        """Initialize standard validation rules."""
        self.rules = [
            BalanceSheetBalanceRule(),
            DebitCreditBalanceRule(),
            NetIncomeReconciliationRule(),
            MinimumEntitiesRule(),
            EliminationCompletenessRule(),
            FXRateConsistencyRule(),
            ReasonablenessRule()
        ]

    def add_rule(self, rule: ValidationRule) -> None:
        """Add a custom validation rule."""
        self.rules.append(rule)

    def validate_all(
        self,
        consolidated: ConsolidatedFinancials
    ) -> Tuple[bool, Dict[str, List[str]]]:
        """
        Run all validation rules.

        Returns:
            (is_valid, results_by_severity)
        """
        results = {
            "ERROR": [],
            "WARNING": [],
            "INFO": []
        }

        all_valid = True

        for rule in self.rules:
            is_valid, message = rule.validate(consolidated)

            if not is_valid:
                results[rule.severity].append(f"[{rule.rule_id}] {message}")

                if rule.severity == "ERROR":
                    all_valid = False

        return all_valid, results

    def calculate_accuracy_score(
        self,
        consolidated: ConsolidatedFinancials
    ) -> Decimal:
        """
        Calculate overall accuracy score (0-1).

        Based on:
        - Balance sheet balance
        - Debit/credit balance
        - Net income reconciliation
        """
        scores = []

        # Balance sheet accuracy
        bs_diff = abs(
            consolidated.total_assets - (consolidated.total_liabilities + consolidated.total_equity)
        )
        if consolidated.total_assets > 0:
            bs_accuracy = 1 - (bs_diff / consolidated.total_assets)
            scores.append(max(Decimal("0"), bs_accuracy))

        # Net income accuracy
        calculated_ni = consolidated.total_revenue - consolidated.total_expenses
        if abs(calculated_ni) > 0:
            ni_diff = abs(consolidated.net_income - calculated_ni)
            ni_accuracy = 1 - (ni_diff / abs(calculated_ni))
            scores.append(max(Decimal("0"), ni_accuracy))

        if not scores:
            return Decimal("0")

        return sum(scores) / len(scores)

    def generate_validation_report(
        self,
        consolidated: ConsolidatedFinancials
    ) -> str:
        """Generate comprehensive validation report."""
        is_valid, results = self.validate_all(consolidated)
        accuracy_score = self.calculate_accuracy_score(consolidated)

        report = "CONSOLIDATION VALIDATION REPORT\n"
        report += "=" * 70 + "\n\n"

        report += f"Period: {consolidated.period_end_date}\n"
        report += f"Entities: {len(consolidated.entities_included)}\n"
        report += f"Accounting Standard: {consolidated.accounting_standard.value}\n"
        report += f"Presentation Currency: {consolidated.presentation_currency.value}\n\n"

        report += f"Overall Status: {'PASS' if is_valid else 'FAIL'}\n"
        report += f"Accuracy Score: {accuracy_score * 100:.2f}%\n"
        report += f"Target Accuracy: {self.accuracy_target * 100:.2f}%\n\n"

        if accuracy_score >= self.accuracy_target:
            report += "✓ Accuracy target met\n\n"
        else:
            report += "✗ Accuracy target NOT met\n\n"

        # Errors
        if results["ERROR"]:
            report += "ERRORS:\n"
            for error in results["ERROR"]:
                report += f"  ✗ {error}\n"
            report += "\n"

        # Warnings
        if results["WARNING"]:
            report += "WARNINGS:\n"
            for warning in results["WARNING"]:
                report += f"  ! {warning}\n"
            report += "\n"

        # Info
        if results["INFO"]:
            report += "INFORMATION:\n"
            for info in results["INFO"]:
                report += f"  i {info}\n"
            report += "\n"

        # Summary metrics
        report += "SUMMARY METRICS:\n"
        report += f"  Total Assets:      ${consolidated.total_assets:,.2f}\n"
        report += f"  Total Liabilities: ${consolidated.total_liabilities:,.2f}\n"
        report += f"  Total Equity:      ${consolidated.total_equity:,.2f}\n"
        report += f"  Total Revenue:     ${consolidated.total_revenue:,.2f}\n"
        report += f"  Total Expenses:    ${consolidated.total_expenses:,.2f}\n"
        report += f"  Net Income:        ${consolidated.net_income:,.2f}\n\n"

        report += "=" * 70 + "\n"

        return report


class ComplianceChecker:
    """
    Checks compliance with IFRS and US GAAP disclosure requirements.
    """

    def __init__(self, standard: AccountingStandard):
        self.standard = standard

    def check_required_disclosures(
        self,
        consolidated: ConsolidatedFinancials
    ) -> List[str]:
        """
        Check for required disclosures.

        Returns:
            List of missing or incomplete disclosures
        """
        missing = []

        if self.standard == AccountingStandard.IFRS:
            missing.extend(self._check_ifrs_disclosures(consolidated))
        elif self.standard == AccountingStandard.US_GAAP:
            missing.extend(self._check_us_gaap_disclosures(consolidated))

        return missing

    def _check_ifrs_disclosures(
        self,
        consolidated: ConsolidatedFinancials
    ) -> List[str]:
        """Check IFRS-specific disclosure requirements."""
        missing = []

        # IAS 1: Presentation of Financial Statements
        if not consolidated.entities_included:
            missing.append("IAS 1: List of consolidated entities not provided")

        # IFRS 3: Business Combinations
        if consolidated.ppa_adjustments:
            # Should have acquisition date, consideration, goodwill
            # This would require additional metadata
            pass

        # IAS 21: Foreign Currency
        if consolidated.total_cta != Decimal("0"):
            # Should disclose CTA movements
            missing.append("IAS 21: CTA movement disclosure required")

        return missing

    def _check_us_gaap_disclosures(
        self,
        consolidated: ConsolidatedFinancials
    ) -> List[str]:
        """Check US GAAP-specific disclosure requirements."""
        missing = []

        # ASC 810: Consolidation
        if not consolidated.entities_included:
            missing.append("ASC 810: Consolidation policy disclosure missing")

        # ASC 805: Business Combinations
        # Similar to IFRS 3

        return missing
