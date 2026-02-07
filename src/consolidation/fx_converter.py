"""
Foreign exchange conversion engine for multi-currency consolidation.
Implements IFRS 21 (IAS 21) and ASC 830 standards.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from .models import (
    AccountType,
    Currency,
    FXRate,
    FXRateType,
    TrialBalanceEntry,
    ConvertedEntry,
    AuditLogEntry
)


class FXRateManager:
    """Manages exchange rates with multiple sources and rate types."""

    def __init__(self):
        self._rates: Dict[Tuple[Currency, Currency, date, FXRateType], FXRate] = {}
        self._audit_log: List[AuditLogEntry] = []

    def add_rate(self, rate: FXRate) -> None:
        """Add or update an exchange rate."""
        key = (rate.from_currency, rate.to_currency, rate.rate_date, rate.rate_type)

        # Log the addition
        existing = self._rates.get(key)
        log_entry = AuditLogEntry(
            action="ADD_FX_RATE" if not existing else "UPDATE_FX_RATE",
            description=f"{rate.from_currency}/{rate.to_currency} {rate.rate_type.value} on {rate.rate_date}",
            previous_value=str(existing.rate) if existing else None,
            new_value=str(rate.rate)
        )
        self._audit_log.append(log_entry)

        self._rates[key] = rate

    def get_rate(
        self,
        from_currency: Currency,
        to_currency: Currency,
        rate_date: date,
        rate_type: FXRateType = FXRateType.CLOSING
    ) -> Optional[FXRate]:
        """Retrieve exchange rate for a specific date and type."""
        if from_currency == to_currency:
            return FXRate(
                from_currency=from_currency,
                to_currency=to_currency,
                rate_date=rate_date,
                rate_type=rate_type,
                rate=Decimal("1.0"),
                source="Same Currency"
            )

        # Try exact match first
        key = (from_currency, to_currency, rate_date, rate_type)
        if key in self._rates:
            return self._rates[key]

        # Try inverse rate
        inverse_key = (to_currency, from_currency, rate_date, rate_type)
        if inverse_key in self._rates:
            return self._rates[inverse_key].invert()

        # Try previous business day (up to 7 days back)
        for days_back in range(1, 8):
            prev_date = rate_date - timedelta(days=days_back)
            prev_key = (from_currency, to_currency, prev_date, rate_type)
            if prev_key in self._rates:
                rate = self._rates[prev_key]
                # Create a new rate with the requested date
                return FXRate(
                    from_currency=rate.from_currency,
                    to_currency=rate.to_currency,
                    rate_date=rate_date,
                    rate_type=rate.rate_type,
                    rate=rate.rate,
                    source=f"{rate.source} (from {prev_date})"
                )

        return None

    def get_average_rate(
        self,
        from_currency: Currency,
        to_currency: Currency,
        start_date: date,
        end_date: date
    ) -> Optional[FXRate]:
        """Calculate average rate for a period (for P&L translation)."""
        if from_currency == to_currency:
            return FXRate(
                from_currency=from_currency,
                to_currency=to_currency,
                rate_date=end_date,
                rate_type=FXRateType.AVERAGE,
                rate=Decimal("1.0"),
                source="Same Currency"
            )

        # Collect all rates in the period
        rates: List[Decimal] = []
        current_date = start_date

        while current_date <= end_date:
            rate = self.get_rate(from_currency, to_currency, current_date, FXRateType.CLOSING)
            if rate:
                rates.append(rate.rate)
            current_date += timedelta(days=1)

        if not rates:
            return None

        avg_rate = sum(rates) / len(rates)

        return FXRate(
            from_currency=from_currency,
            to_currency=to_currency,
            rate_date=end_date,
            rate_type=FXRateType.AVERAGE,
            rate=avg_rate,
            source=f"Average of {len(rates)} daily rates from {start_date} to {end_date}"
        )

    def load_rates_from_api(self, source: str = "BCB") -> None:
        """
        Load rates from external API (placeholder for integration).

        Sources:
        - BCB: Central Bank of Brazil (PTAX rates)
        - ECB: European Central Bank
        - FED: US Federal Reserve
        """
        # TODO: Implement API integration
        # For now, this is a placeholder for the integration point
        pass

    def get_audit_log(self) -> List[AuditLogEntry]:
        """Retrieve audit log of all rate changes."""
        return self._audit_log.copy()


class FXConverter:
    """Converts financial data between currencies per IFRS 21."""

    def __init__(self, rate_manager: FXRateManager):
        self.rate_manager = rate_manager
        self._cta_balances: Dict[str, Decimal] = {}  # entity_id -> CTA balance

    def convert_trial_balance_entry(
        self,
        entry: TrialBalanceEntry,
        presentation_currency: Currency,
        period_start_date: date
    ) -> ConvertedEntry:
        """
        Convert a trial balance entry to presentation currency.

        IFRS 21 Rules:
        - Balance Sheet items: Closing rate
        - P&L items: Average rate for the period
        - Equity items: Historical rate (rate at transaction date)
        """
        if entry.currency == presentation_currency:
            return ConvertedEntry(
                original_entry=entry,
                presentation_currency=presentation_currency,
                fx_rate=FXRate(
                    from_currency=entry.currency,
                    to_currency=presentation_currency,
                    rate=Decimal("1.0"),
                    source="Same Currency"
                ),
                converted_amount=entry.net_amount,
                conversion_method="No conversion needed"
            )

        # Determine appropriate rate type
        rate_type = self._get_rate_type_for_account(entry.account_type)

        # Get the exchange rate
        if rate_type == FXRateType.AVERAGE:
            fx_rate = self.rate_manager.get_average_rate(
                entry.currency,
                presentation_currency,
                period_start_date,
                entry.period_end_date
            )
        else:
            fx_rate = self.rate_manager.get_rate(
                entry.currency,
                presentation_currency,
                entry.period_end_date,
                rate_type
            )

        if not fx_rate:
            raise ValueError(
                f"No exchange rate found for {entry.currency}/{presentation_currency} "
                f"on {entry.period_end_date} ({rate_type.value})"
            )

        # Convert the amount
        converted_amount = entry.net_amount * fx_rate.rate

        # Calculate CTA for balance sheet items
        cta_amount = Decimal("0")
        if entry.account_type in [
            AccountType.BALANCE_SHEET_ASSET,
            AccountType.BALANCE_SHEET_LIABILITY
        ]:
            # CTA is the difference between historical and current translation
            # This is a simplified calculation; production systems would track
            # opening balances and movements separately
            cta_amount = self._calculate_cta(
                entry.entity_id,
                entry.net_amount,
                fx_rate.rate,
                period_start_date,
                entry.period_end_date
            )

        return ConvertedEntry(
            original_entry=entry,
            presentation_currency=presentation_currency,
            fx_rate=fx_rate,
            converted_amount=converted_amount,
            cta_amount=cta_amount,
            conversion_method=f"{rate_type.value} rate method per IFRS 21"
        )

    def _get_rate_type_for_account(self, account_type: AccountType) -> FXRateType:
        """Determine FX rate type based on account classification."""
        if account_type in [AccountType.INCOME, AccountType.EXPENSE]:
            return FXRateType.AVERAGE
        elif account_type == AccountType.EQUITY_TRANSACTION:
            return FXRateType.HISTORICAL
        else:
            return FXRateType.CLOSING

    def _calculate_cta(
        self,
        entity_id: str,
        amount: Decimal,
        current_rate: Decimal,
        period_start: date,
        period_end: date
    ) -> Decimal:
        """
        Calculate Cumulative Translation Adjustment.

        CTA arises from translating the same item at different rates over time.
        This is a simplified implementation; production would track opening
        balances and period movements separately.
        """
        # Initialize CTA balance if not exists
        if entity_id not in self._cta_balances:
            self._cta_balances[entity_id] = Decimal("0")

        # In a full implementation, this would:
        # 1. Track opening balance at opening rate
        # 2. Track period movements at average rate
        # 3. Calculate difference vs. closing rate translation
        # 4. Accumulate in equity

        # Simplified: assume 2% FX variance as placeholder
        # TODO: Implement full opening/movement tracking
        cta_change = amount * current_rate * Decimal("0.02")

        self._cta_balances[entity_id] += cta_change
        return self._cta_balances[entity_id]

    def get_total_cta(self, entity_id: Optional[str] = None) -> Decimal:
        """Get total CTA balance for an entity or all entities."""
        if entity_id:
            return self._cta_balances.get(entity_id, Decimal("0"))
        return sum(self._cta_balances.values())

    def reset_cta(self, entity_id: Optional[str] = None) -> None:
        """Reset CTA balances (e.g., at year-end or disposal)."""
        if entity_id:
            self._cta_balances[entity_id] = Decimal("0")
        else:
            self._cta_balances.clear()


def load_bcb_rates(
    rate_manager: FXRateManager,
    start_date: date,
    end_date: date,
    currencies: List[Currency] = None
) -> int:
    """
    Load rates from Brazilian Central Bank (BCB) API.

    BCB provides PTAX rates for BRL conversion.
    This is a placeholder for actual API integration.

    Returns:
        Number of rates loaded
    """
    if currencies is None:
        currencies = [Currency.USD, Currency.EUR, Currency.GBP]

    # TODO: Implement actual BCB API integration
    # API endpoint: https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata
    # Example: /CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)

    rates_loaded = 0

    # Placeholder: would fetch from API and populate rate_manager
    # For now, return 0 to indicate no rates loaded
    return rates_loaded


def create_sample_rates(rate_manager: FXRateManager, as_of_date: date) -> None:
    """Create sample FX rates for testing (placeholder data)."""

    # USD/BRL rates (common for Nuvini portfolio companies)
    rate_manager.add_rate(FXRate(
        from_currency=Currency.USD,
        to_currency=Currency.BRL,
        rate_date=as_of_date,
        rate_type=FXRateType.CLOSING,
        rate=Decimal("5.25"),
        source="Sample Data"
    ))

    rate_manager.add_rate(FXRate(
        from_currency=Currency.USD,
        to_currency=Currency.BRL,
        rate_date=as_of_date,
        rate_type=FXRateType.AVERAGE,
        rate=Decimal("5.20"),
        source="Sample Data"
    ))

    # EUR/USD rates
    rate_manager.add_rate(FXRate(
        from_currency=Currency.EUR,
        to_currency=Currency.USD,
        rate_date=as_of_date,
        rate_type=FXRateType.CLOSING,
        rate=Decimal("1.10"),
        source="Sample Data"
    ))

    # GBP/USD rates
    rate_manager.add_rate(FXRate(
        from_currency=Currency.GBP,
        to_currency=Currency.USD,
        rate_date=as_of_date,
        rate_type=FXRateType.CLOSING,
        rate=Decimal("1.27"),
        source="Sample Data"
    ))
