from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.core.config import settings

MONEY_QUANT = Decimal("0.01")


def round_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


class CalculationEngine:
    def calculate_daily_trading(self, gross_trading_pnl: Decimal, transaction_charges: Decimal) -> Decimal:
        return round_money(gross_trading_pnl - transaction_charges)

    def calculate_active_clients(self, clients: list[Any], trading_date: Any) -> list[Any]:
        active: list[Any] = []
        for client in clients:
            status = client.get("status") if isinstance(client, dict) else getattr(client, "status", None)
            history = client.get("status_history") if isinstance(client, dict) else getattr(client, "status_history", [])
            effective_status = status
            if isinstance(history, list):
                for item in history:
                    if not item:
                        continue
                    from_date = item.get("from_date") if isinstance(item, dict) else getattr(item, "from_date", None)
                    to_date = item.get("to_date") if isinstance(item, dict) else getattr(item, "to_date", None)
                    item_status = item.get("status") if isinstance(item, dict) else getattr(item, "status", None)
                    if from_date <= trading_date <= to_date:
                        effective_status = item_status
                        break
            if effective_status == "ACTIVE":
                active.append(client)
        return active

    def calculate_client_capital(self, client: Any, date_value: Any) -> Decimal:
        return Decimal(str(client.opening_capital or "0.00"))

    def calculate_capital_share(self, client_capital: Decimal, total_active_capital: Decimal) -> Decimal:
        if total_active_capital == 0:
            return Decimal("0")
        return round_money((client_capital / total_active_capital) * Decimal("100"))

    def calculate_client_pnl(self, net_daily_pnl: Decimal, capital_share_percent: Decimal) -> Decimal:
        if capital_share_percent == 0:
            return Decimal("0.00")
        return round_money(net_daily_pnl * (capital_share_percent / Decimal("100")))

    def calculate_client_fee(self, allocated_pnl: Decimal, fee_type: str, fee_value: Decimal) -> Decimal:
        if fee_type == "NONE":
            return Decimal("0.00")
        if fee_type == "PERCENTAGE":
            if allocated_pnl > 0:
                return round_money(allocated_pnl * (fee_value / Decimal("100")))
            return Decimal("0.00")
        if fee_type == "FIXED":
            return round_money(fee_value)
        return Decimal("0.00")

    def calculate_manager_fee(self, total_client_fees: Decimal) -> Decimal:
        return round_money(total_client_fees)

    def calculate_closing_balance(
        self,
        opening_balance: Decimal,
        deposit: Decimal,
        withdrawal: Decimal,
        allocated_pnl: Decimal,
        fee_debited: Decimal,
    ) -> Decimal:
        return round_money(opening_balance + deposit - withdrawal + allocated_pnl - fee_debited)

    def calculate_proportional_allocations(
        self,
        net_daily_pnl: Decimal,
        client_capitals: dict[str, Decimal],
    ) -> dict[str, Decimal]:
        total_active_capital = sum(client_capitals.values(), Decimal("0.00"))
        if total_active_capital == 0:
            return {client_id: Decimal("0.00") for client_id in client_capitals}

        allocations: dict[str, Decimal] = {}
        for client_id, capital in client_capitals.items():
            share = Decimal(str(capital)) / total_active_capital
            allocations[client_id] = round_money(net_daily_pnl * share)
        return allocations

    def validate_status_periods(self, history: list[Any]) -> bool:
        periods_by_client: dict[str, list[tuple[Any, Any]]] = {}
        for item in history:
            client_id = item.get("client_id") if isinstance(item, dict) else getattr(item, "client_id", None)
            from_date = item.get("from_date") if isinstance(item, dict) else getattr(item, "from_date", None)
            to_date = item.get("to_date") if isinstance(item, dict) else getattr(item, "to_date", None)
            if client_id is None or from_date is None or to_date is None:
                continue
            periods_by_client.setdefault(str(client_id), []).append((from_date, to_date))

        for periods in periods_by_client.values():
            sorted_periods = sorted(periods, key=lambda p: p[0])
            for index in range(1, len(sorted_periods)):
                previous_end = sorted_periods[index - 1][1]
                current_start = sorted_periods[index][0]
                if current_start <= previous_end:
                    return False
        return True

    def recalculate_date(self, trading_date: Any, clients: list[Any]) -> list[dict[str, Any]]:
        return [
            {
                "trading_date": trading_date,
                "client": client.client_code,
                "allocated_pnl": Decimal("0.00"),
                "fee_debited": Decimal("0.00"),
                "closing_balance": Decimal("0.00"),
            }
            for client in clients
        ]

    def recalculate_all(self) -> dict[str, Any]:
        return {"status": "not_implemented", "message": "Calculation engine scaffold ready"}
