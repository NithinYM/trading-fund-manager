from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.client_ledger import ClientLedger
from app.models.daily_trading import DailyTrading
from app.services.calculation_engine import CalculationEngine, round_money


class LedgerService:
    def __init__(self) -> None:
        self.engine = CalculationEngine()

    def build_ledger_entry(
        self,
        client_id: str,
        trading_date: date,
        capital_before_pnl: Decimal,
        net_daily_pnl: Decimal,
        capital_share_percent: Decimal,
        allocated_pnl: Decimal,
        fee_debited: Decimal,
        status_on_date: str,
        fund_movement: Decimal,
        manager_fee_credit: Decimal,
        closing_balance: Decimal,
    ) -> dict[str, Any]:
        return {
            "client_id": client_id,
            "trading_date": trading_date,
            "fund_movement": fund_movement,
            "capital_before_pnl": capital_before_pnl,
            "capital_share_percent": capital_share_percent,
            "net_daily_pnl": net_daily_pnl,
            "allocated_pnl": allocated_pnl,
            "fee_debited": fee_debited,
            "net_client_pnl": allocated_pnl - fee_debited,
            "closing_balance": closing_balance,
            "status_on_date": status_on_date,
            "manager_fee_credit": manager_fee_credit,
            "calculation_version": "v1",
        }

    def recalculate_for_date(self, trading_date: date, active_clients: list[Any], total_net_pnl: Decimal) -> list[dict[str, Any]]:
        capital_by_client: dict[str, Decimal] = {}
        for client in active_clients:
            capital_by_client[str(client["id"])] = Decimal(str(client.get("capital_before_pnl", "0.00")))

        allocations = self.engine.calculate_proportional_allocations(total_net_pnl, capital_by_client)
        entries: list[dict[str, Any]] = []
        for client in active_clients:
            client_id = str(client["id"])
            allocated_pnl = allocations.get(client_id, Decimal("0.00"))
            fee_debited = Decimal("0.00")
            if client.get("fee_type") == "PERCENTAGE":
                fee_debited = self.engine.calculate_client_fee(allocated_pnl, "PERCENTAGE", Decimal(str(client.get("fee_value", "0.00"))))
            elif client.get("fee_type") == "FIXED":
                fee_debited = self.engine.calculate_client_fee(allocated_pnl, "FIXED", Decimal(str(client.get("fee_value", "0.00"))))

            closing_balance = self.engine.calculate_closing_balance(
                Decimal(str(client.get("opening_capital", "0.00"))),
                Decimal(str(client.get("fund_movement", "0.00"))),
                Decimal("0.00"),
                allocated_pnl,
                fee_debited,
            )

            entries.append(
                self.build_ledger_entry(
                    client_id=client_id,
                    trading_date=trading_date,
                    capital_before_pnl=Decimal(str(client.get("capital_before_pnl", "0.00"))),
                    net_daily_pnl=total_net_pnl,
                    capital_share_percent=Decimal("0.00"),
                    allocated_pnl=allocated_pnl,
                    fee_debited=fee_debited,
                    status_on_date=client.get("status", "ACTIVE"),
                    fund_movement=Decimal(str(client.get("fund_movement", "0.00"))),
                    manager_fee_credit=fee_debited,
                    closing_balance=closing_balance,
                )
            )
        return entries

    def recalculate_date_from_db(self, db: Session, trading_date: date) -> list[ClientLedger]:
        trading = db.query(DailyTrading).filter(DailyTrading.trading_date == trading_date).first()
        if trading is None:
            raise ValueError(f"No daily trading record exists for {trading_date}")

        clients = db.query(Client).filter(Client.is_deleted.is_(False), Client.join_date <= trading_date).all()
        capital_by_client: dict[str, Decimal] = {}
        movement_by_client: dict[str, Decimal] = {}
        status_by_client: dict[str, str] = {}

        for client in clients:
            previous = (
                db.query(ClientLedger)
                .filter(ClientLedger.client_id == client.id, ClientLedger.trading_date < trading_date)
                .order_by(ClientLedger.trading_date.desc())
                .first()
            )
            opening_balance = Decimal(str(previous.closing_balance)) if previous else Decimal(str(client.opening_capital or "0.00"))
            movement = sum(
                (Decimal(str(item.signed_amount or "0.00")) for item in client.fund_movements if item.date <= trading_date),
                Decimal("0.00"),
            )
            if previous is None:
                capital_before = opening_balance + movement
            else:
                prior_movement = sum(
                    (Decimal(str(item.signed_amount or "0.00")) for item in client.fund_movements if item.date <= previous.trading_date),
                    Decimal("0.00"),
                )
                capital_before = opening_balance + movement - prior_movement

            matching_status = next(
                (
                    history.status
                    for history in client.status_history
                    if history.from_date <= trading_date <= history.to_date
                ),
                client.status,
            )
            status_by_client[client.id] = matching_status
            capital_by_client[client.id] = round_money(capital_before)
            movement_by_client[client.id] = round_money(movement - (prior_movement if previous else Decimal("0.00")))

        active_capitals = {
            client_id: capital
            for client_id, capital in capital_by_client.items()
            if status_by_client[client_id] == "ACTIVE"
        }
        allocations = self.engine.calculate_proportional_allocations(Decimal(str(trading.net_pnl or "0.00")), active_capitals)
        total_active = sum(active_capitals.values(), Decimal("0.00"))

        db.query(ClientLedger).filter(ClientLedger.trading_date == trading_date).delete(synchronize_session=False)
        entries: list[ClientLedger] = []
        for client in clients:
            capital_before = capital_by_client[client.id]
            allocated_pnl = allocations.get(client.id, Decimal("0.00"))
            fee_start_ok = client.fee_start_date is None or client.fee_start_date <= trading_date
            fee = (
                self.engine.calculate_client_fee(allocated_pnl, client.fee_type, Decimal(str(client.fee_value or "0.00")))
                if fee_start_ok and status_by_client[client.id] == "ACTIVE"
                else Decimal("0.00")
            )
            net_client_pnl = round_money(allocated_pnl - fee)
            movement = movement_by_client[client.id]
            closing = self.engine.calculate_closing_balance(
                capital_before,
                Decimal("0.00"),
                Decimal("0.00"),
                allocated_pnl,
                fee,
            )
            share = (
                (capital_before / total_active * Decimal("100")).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
                if client.id in active_capitals and total_active
                else Decimal("0.000000")
            )
            daily_return = (
                (net_client_pnl / capital_before * Decimal("100")).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
                if capital_before
                else Decimal("0.000000")
            )
            entry = ClientLedger(
                id=str(uuid4()),
                trading_date=trading_date,
                client_id=client.id,
                fund_movement=movement,
                capital_before_pnl=capital_before,
                capital_share_percent=share,
                net_daily_pnl=Decimal(str(trading.net_pnl or "0.00")),
                allocated_pnl=allocated_pnl,
                fee_debited=fee,
                net_client_pnl=net_client_pnl,
                closing_balance=closing,
                daily_return_percent=daily_return,
                status_on_date=status_by_client[client.id],
                manager_fee_credit=fee,
            )
            db.add(entry)
            entries.append(entry)

        db.commit()
        for entry in entries:
            db.refresh(entry)
        return entries
