from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any


class ValidationService:
    @staticmethod
    def validate_client_status_periods(periods: list[dict[str, Any]]) -> list[str]:
        errors: list[str] = []
        by_client: dict[str, list[tuple[date, date]]] = {}

        for period in periods:
            client_id = str(period.get("client_id", "")).strip()
            from_date = period.get("from_date")
            to_date = period.get("to_date")
            if not client_id:
                errors.append("Status period missing client_id.")
                continue
            if not from_date or not to_date:
                errors.append(f"Status period for client {client_id} is missing a date range.")
                continue
            if from_date > to_date:
                errors.append(f"Status period for client {client_id} has invalid date order.")
                continue
            by_client.setdefault(client_id, []).append((from_date, to_date))

        for client_id, entries in by_client.items():
            sorted_entries = sorted(entries, key=lambda item: item[0])
            for previous, current in zip(sorted_entries, sorted_entries[1:]):
                if current[0] <= previous[1]:
                    errors.append(f"Status periods overlap for client {client_id}.")

        return errors

    @staticmethod
    def validate_trading_record(gross_pnl: Decimal, transaction_charges: Decimal) -> list[str]:
        errors: list[str] = []
        if gross_pnl is None:
            errors.append("Gross Trading P&L is required.")
        if transaction_charges is None:
            errors.append("Transaction charges are required.")
        return errors

    @staticmethod
    def validate_fund_movement(amount: Decimal, movement_type: str) -> list[str]:
        errors: list[str] = []
        if amount is None or amount <= 0:
            errors.append("Movement amount must be a positive value.")
        if movement_type not in {"DEPOSIT", "WITHDRAWAL"}:
            errors.append("Movement type must be DEPOSIT or WITHDRAWAL.")
        return errors

    @staticmethod
    def validate_fee(fee_type: str, fee_value: Decimal, fee_start_date: date | None, join_date: date | None) -> list[str]:
        errors: list[str] = []
        if fee_type not in {"NONE", "PERCENTAGE", "FIXED"}:
            errors.append("Fee type must be NONE, PERCENTAGE, or FIXED.")
        if fee_type == "PERCENTAGE" and fee_value < 0:
            errors.append("Percentage fee cannot be negative.")
        if fee_type == "FIXED" and fee_value < 0:
            errors.append("Fixed fee cannot be negative.")
        if fee_start_date and join_date and fee_start_date < join_date:
            errors.append("Fee start date cannot be before client join date.")
        return errors

    @staticmethod
    def validate_allocation(total_daily_net_pnl: Decimal, allocated_pnl_total: Decimal, tolerance: Decimal = Decimal("0.01")) -> list[str]:
        errors: list[str] = []
        delta = abs(total_daily_net_pnl - allocated_pnl_total)
        if delta > tolerance:
            errors.append(f"Allocation mismatch: {delta}")
        return errors
