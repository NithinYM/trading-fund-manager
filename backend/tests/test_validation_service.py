from datetime import date
from decimal import Decimal

from app.services.validation_service import ValidationService


def test_status_overlap_detection():
    errors = ValidationService.validate_client_status_periods([
        {"client_id": "C001", "from_date": date(2026, 1, 1), "to_date": date(2026, 9, 30)},
        {"client_id": "C001", "from_date": date(2026, 9, 15), "to_date": date(2026, 12, 31)},
    ])
    assert any("overlap" in message.lower() for message in errors)


def test_valid_allocation_has_no_error():
    errors = ValidationService.validate_allocation(Decimal("5000.00"), Decimal("5000.00"))
    assert errors == []


def test_invalid_allocation_has_error():
    errors = ValidationService.validate_allocation(Decimal("5000.00"), Decimal("4900.00"))
    assert len(errors) == 1


def test_percentage_fee_validation():
    errors = ValidationService.validate_fee("PERCENTAGE", Decimal("10"), date(2026, 1, 1), date(2025, 12, 1))
    assert errors == []
