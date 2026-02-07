"""
Purchase Price Allocation (PPA) and amortization engine.
Handles goodwill, intangible assets, and monthly amortization schedules.
"""

from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from .models import (
    Currency,
    PurchasePriceAllocation,
    AmortizationEntry,
    Entity,
    AuditLogEntry
)


class PPACalculator:
    """Calculates purchase price allocation for acquisitions."""

    def __init__(self):
        self._audit_log: List[AuditLogEntry] = []

    def calculate_ppa(
        self,
        entity: Entity,
        purchase_price: Decimal,
        fair_value_net_assets: Decimal,
        identified_intangibles: Dict[str, Decimal],
        amortization_periods: Dict[str, int],
        currency: Currency = Currency.USD
    ) -> PurchasePriceAllocation:
        """
        Calculate purchase price allocation.

        Args:
            entity: Acquired entity
            purchase_price: Total consideration paid
            fair_value_net_assets: Fair value of identifiable net assets
            identified_intangibles: Dict of intangible name -> fair value
            amortization_periods: Dict of intangible name -> useful life in years
            currency: Currency of the transaction

        Returns:
            PurchasePriceAllocation object
        """
        # Calculate total identified intangibles
        total_intangibles = sum(identified_intangibles.values())

        # Goodwill = Purchase Price - (FV Net Assets + Identified Intangibles)
        goodwill = purchase_price - fair_value_net_assets - total_intangibles

        if goodwill < 0:
            # Bargain purchase - gain recognized immediately
            self._audit_log.append(AuditLogEntry(
                action="BARGAIN_PURCHASE",
                entity_id=entity.entity_id,
                description=f"Bargain purchase gain: {abs(goodwill)} {currency.value}"
            ))

        ppa = PurchasePriceAllocation(
            entity_id=entity.entity_id,
            acquisition_date=entity.acquisition_date or date.today(),
            purchase_price=purchase_price,
            fair_value_net_assets=fair_value_net_assets,
            goodwill=goodwill,
            intangible_assets=identified_intangibles,
            amortization_schedule=amortization_periods,
            currency=currency
        )

        self._audit_log.append(AuditLogEntry(
            action="CREATE_PPA",
            entity_id=entity.entity_id,
            description=f"PPA created: Goodwill={goodwill}, Intangibles={total_intangibles}"
        ))

        return ppa

    def validate_ppa(self, ppa: PurchasePriceAllocation) -> Tuple[bool, List[str]]:
        """
        Validate PPA calculation.

        Checks:
        - Purchase price > 0
        - All intangibles have amortization periods
        - Goodwill calculation is correct
        """
        errors = []

        if ppa.purchase_price <= 0:
            errors.append("Purchase price must be positive")

        if ppa.fair_value_net_assets <= 0:
            errors.append("Fair value of net assets must be positive")

        # Check all intangibles have amortization periods
        for intangible_name in ppa.intangible_assets:
            if intangible_name not in ppa.amortization_schedule:
                errors.append(f"No amortization period for {intangible_name}")

        # Validate goodwill calculation
        expected_goodwill = ppa.purchase_price - ppa.fair_value_net_assets - ppa.total_intangibles
        if abs(ppa.goodwill - expected_goodwill) > Decimal("0.01"):
            errors.append(
                f"Goodwill calculation error: expected {expected_goodwill}, got {ppa.goodwill}"
            )

        return len(errors) == 0, errors


class AmortizationScheduler:
    """Generates amortization schedules for intangible assets."""

    def __init__(self):
        self._schedules: Dict[str, List[AmortizationEntry]] = {}

    def create_monthly_schedule(
        self,
        ppa: PurchasePriceAllocation,
        start_date: Optional[date] = None,
        months: int = 120  # Default 10 years
    ) -> Dict[str, List[AmortizationEntry]]:
        """
        Create monthly amortization schedule for all intangibles.

        Args:
            ppa: Purchase price allocation
            start_date: Start date for amortization (defaults to acquisition date)
            months: Number of months to generate (default 120 = 10 years)

        Returns:
            Dict of intangible name -> list of monthly amortization entries
        """
        if start_date is None:
            start_date = ppa.acquisition_date

        schedules = {}

        for intangible_name, intangible_value in ppa.intangible_assets.items():
            useful_life_years = ppa.amortization_schedule.get(intangible_name)
            if not useful_life_years:
                continue

            # Calculate monthly amortization (straight-line)
            total_months = useful_life_years * 12
            monthly_amortization = intangible_value / total_months

            # Generate schedule
            schedule = []
            accumulated = Decimal("0")

            for month_num in range(min(months, total_months)):
                period_date = start_date + relativedelta(months=month_num)
                accumulated += monthly_amortization
                remaining = intangible_value - accumulated

                entry = AmortizationEntry(
                    ppa_id=ppa.ppa_id,
                    period_end_date=period_date,
                    asset_name=intangible_name,
                    monthly_amortization=monthly_amortization,
                    accumulated_amortization=accumulated,
                    remaining_value=remaining
                )
                schedule.append(entry)

            schedules[intangible_name] = schedule

        self._schedules[ppa.ppa_id] = schedules
        return schedules

    def get_amortization_for_period(
        self,
        ppa_id: str,
        period_end_date: date
    ) -> List[AmortizationEntry]:
        """Get all amortization entries for a specific period."""
        if ppa_id not in self._schedules:
            return []

        period_entries = []
        for intangible_schedule in self._schedules[ppa_id].values():
            for entry in intangible_schedule:
                if entry.period_end_date.year == period_end_date.year and \
                   entry.period_end_date.month == period_end_date.month:
                    period_entries.append(entry)

        return period_entries

    def get_total_monthly_amortization(
        self,
        ppa_id: str,
        period_end_date: date
    ) -> Decimal:
        """Get total amortization for all intangibles in a period."""
        entries = self.get_amortization_for_period(ppa_id, period_end_date)
        return sum(entry.monthly_amortization for entry in entries)


class GoodwillImpairmentTester:
    """
    Goodwill impairment testing framework.

    Per IFRS, goodwill is tested for impairment annually or when indicators exist.
    Per US GAAP, qualitative and quantitative testing allowed.
    """

    def __init__(self):
        self._impairment_history: List[Dict] = []

    def test_impairment_qualitative(
        self,
        ppa: PurchasePriceAllocation,
        entity: Entity,
        indicators: Dict[str, bool]
    ) -> Tuple[bool, str]:
        """
        Qualitative impairment test (US GAAP Step 0).

        indicators: Dict of impairment indicator -> present (True/False)
        Examples:
        - significant_adverse_change: Market conditions deteriorated
        - regulatory_changes: New regulations impacting business
        - increased_competition: Competitive position weakened
        - key_personnel_departure: Loss of key management
        - adverse_financial_performance: Declining revenues/margins

        Returns:
            (requires_quantitative_test, reason)
        """
        triggered_indicators = [k for k, v in indicators.items() if v]

        if len(triggered_indicators) >= 2:
            reason = f"Multiple impairment indicators: {', '.join(triggered_indicators)}"
            return True, reason

        if indicators.get("significant_adverse_change", False):
            return True, "Significant adverse change in business climate"

        if indicators.get("adverse_financial_performance", False):
            return True, "Sustained underperformance vs. projections"

        return False, "No indicators of impairment"

    def test_impairment_quantitative(
        self,
        ppa: PurchasePriceAllocation,
        carrying_amount: Decimal,
        recoverable_amount: Decimal
    ) -> Tuple[Decimal, str]:
        """
        Quantitative impairment test.

        IFRS: Recoverable amount = higher of fair value less costs to sell
              and value in use (discounted future cash flows)

        US GAAP: Step 1 - Compare carrying value to fair value
                 Step 2 - If carrying > fair value, measure impairment

        Args:
            ppa: Purchase price allocation
            carrying_amount: Current carrying amount of goodwill
            recoverable_amount: Estimated recoverable amount

        Returns:
            (impairment_amount, explanation)
        """
        impairment = Decimal("0")
        explanation = ""

        if carrying_amount > recoverable_amount:
            impairment = carrying_amount - recoverable_amount
            explanation = (
                f"Goodwill impairment: Carrying amount {carrying_amount} "
                f"exceeds recoverable amount {recoverable_amount}"
            )

            self._impairment_history.append({
                "ppa_id": ppa.ppa_id,
                "entity_id": ppa.entity_id,
                "impairment_date": date.today(),
                "impairment_amount": impairment,
                "carrying_amount": carrying_amount,
                "recoverable_amount": recoverable_amount
            })
        else:
            explanation = "No impairment: Recoverable amount exceeds carrying amount"

        return impairment, explanation

    def get_impairment_history(self, entity_id: Optional[str] = None) -> List[Dict]:
        """Get historical impairment tests."""
        if entity_id:
            return [h for h in self._impairment_history if h["entity_id"] == entity_id]
        return self._impairment_history


class PPAManager:
    """
    High-level PPA management combining calculation, amortization, and impairment.
    """

    def __init__(self):
        self.calculator = PPACalculator()
        self.scheduler = AmortizationScheduler()
        self.impairment_tester = GoodwillImpairmentTester()
        self._ppas: Dict[str, PurchasePriceAllocation] = {}

    def create_ppa(
        self,
        entity: Entity,
        purchase_price: Decimal,
        fair_value_net_assets: Decimal,
        identified_intangibles: Dict[str, Decimal],
        amortization_periods: Dict[str, int],
        currency: Currency = Currency.USD
    ) -> PurchasePriceAllocation:
        """Create and validate PPA."""
        ppa = self.calculator.calculate_ppa(
            entity,
            purchase_price,
            fair_value_net_assets,
            identified_intangibles,
            amortization_periods,
            currency
        )

        # Validate
        is_valid, errors = self.calculator.validate_ppa(ppa)
        if not is_valid:
            raise ValueError(f"Invalid PPA: {', '.join(errors)}")

        # Store
        self._ppas[ppa.ppa_id] = ppa

        # Generate amortization schedule
        self.scheduler.create_monthly_schedule(ppa)

        return ppa

    def get_monthly_ppa_entries(
        self,
        entity_id: str,
        period_end_date: date
    ) -> List[AmortizationEntry]:
        """Get all PPA amortization entries for an entity in a period."""
        entries = []

        for ppa_id, ppa in self._ppas.items():
            if ppa.entity_id == entity_id:
                period_entries = self.scheduler.get_amortization_for_period(
                    ppa_id, period_end_date
                )
                entries.extend(period_entries)

        return entries

    def get_total_monthly_amortization(
        self,
        entity_id: str,
        period_end_date: date
    ) -> Decimal:
        """Get total PPA amortization for an entity in a period."""
        entries = self.get_monthly_ppa_entries(entity_id, period_end_date)
        return sum(entry.monthly_amortization for entry in entries)

    def run_impairment_test(
        self,
        entity_id: str,
        carrying_amount: Decimal,
        recoverable_amount: Decimal,
        qualitative_indicators: Optional[Dict[str, bool]] = None
    ) -> Tuple[Decimal, str]:
        """Run comprehensive impairment test."""
        # Find PPA for entity
        ppa = None
        for p in self._ppas.values():
            if p.entity_id == entity_id:
                ppa = p
                break

        if not ppa:
            return Decimal("0"), "No PPA found for entity"

        # Qualitative test first (if indicators provided)
        if qualitative_indicators:
            requires_quant, reason = self.impairment_tester.test_impairment_qualitative(
                ppa, None, qualitative_indicators
            )
            if not requires_quant:
                return Decimal("0"), reason

        # Quantitative test
        return self.impairment_tester.test_impairment_quantitative(
            ppa, carrying_amount, recoverable_amount
        )
