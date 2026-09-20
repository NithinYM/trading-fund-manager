from datetime import date
from decimal import Decimal

from app.services.calculation_engine import CalculationEngine


def test_daily_trading_net_pnl_is_calculated():
    engine = CalculationEngine()
    assert engine.calculate_daily_trading(Decimal("5000.00"), Decimal("250.00")) == Decimal("4750.00")


def test_percentage_fee_on_positive_allocated_pnl():
    engine = CalculationEngine()
    assert engine.calculate_client_fee(Decimal("1000.00"), "PERCENTAGE", Decimal("10")) == Decimal("100.00")


def test_no_fee_on_negative_allocated_pnl():
    engine = CalculationEngine()
    assert engine.calculate_client_fee(Decimal("-1000.00"), "PERCENTAGE", Decimal("10")) == Decimal("0.00")


def test_fixed_fee_is_returned():
    engine = CalculationEngine()
    assert engine.calculate_client_fee(Decimal("500.00"), "FIXED", Decimal("500")) == Decimal("500.00")


def test_calculating_closing_balance():
    engine = CalculationEngine()
    assert engine.calculate_closing_balance(
        Decimal("10000.00"),
        Decimal("500.00"),
        Decimal("200.00"),
        Decimal("1200.00"),
        Decimal("50.00"),
    ) == Decimal("11450.00")


def test_active_clients_only_include_status_on_date():
    engine = CalculationEngine()
    clients = [
        {"id": "c1", "status": "ACTIVE", "status_history": [{"from_date": date(2026, 1, 1), "to_date": date(2026, 12, 31), "status": "ACTIVE"}]},
        {"id": "c2", "status": "INACTIVE", "status_history": [{"from_date": date(2026, 1, 1), "to_date": date(2026, 9, 14), "status": "INACTIVE"}]},
    ]

    active = engine.calculate_active_clients(clients, date(2026, 9, 15))
    assert [item["id"] for item in active] == ["c1"]


def test_status_history_overrides_current_active_status_for_its_effective_period():
    engine = CalculationEngine()
    clients = [
        {"id": "c1", "status": "ACTIVE", "status_history": [{"from_date": date(2026, 6, 1), "to_date": date(2026, 6, 30), "status": "INACTIVE"}]},
    ]

    assert engine.calculate_active_clients(clients, date(2026, 6, 15)) == []
    assert [item["id"] for item in engine.calculate_active_clients(clients, date(2026, 7, 1))] == ["c1"]


def test_proportional_allocation_sums_to_daily_pnl():
    engine = CalculationEngine()
    allocations = engine.calculate_proportional_allocations(
        net_daily_pnl=Decimal("5000.00"),
        client_capitals={
            "A": Decimal("60000.00"),
            "B": Decimal("40000.00"),
        },
    )

    assert allocations["A"] == Decimal("3000.00")
    assert allocations["B"] == Decimal("2000.00")
    assert sum(allocations.values(), Decimal("0.00")) == Decimal("5000.00")


def test_proportional_allocation_handles_negative_pnl_and_zero_capital():
    engine = CalculationEngine()
    negative = engine.calculate_proportional_allocations(Decimal("-100.00"), {"A": Decimal("60.00"), "B": Decimal("40.00")})
    zero = engine.calculate_proportional_allocations(Decimal("100.00"), {"A": Decimal("0.00"), "B": Decimal("0.00")})

    assert negative == {"A": Decimal("-60.00"), "B": Decimal("-40.00")}
    assert zero == {"A": Decimal("0.00"), "B": Decimal("0.00")}


def test_status_history_overlap_is_detected():
    engine = CalculationEngine()
    history = [
        {"client_id": "c1", "from_date": date(2026, 1, 1), "to_date": date(2026, 9, 30), "status": "ACTIVE"},
        {"client_id": "c1", "from_date": date(2026, 9, 15), "to_date": date(2026, 12, 31), "status": "ACTIVE"},
    ]

    assert engine.validate_status_periods(history) is False
