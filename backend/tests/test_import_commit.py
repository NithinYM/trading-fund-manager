from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.db.database import SessionLocal
from app.main import app
from app.models.client import Client
from app.models.client_ledger import ClientLedger
from app.models.daily_trading import DailyTrading

client = TestClient(app)


def workbook_bytes(include_overlap: bool = False, include_example_note: bool = False, include_nested_exception: bool = False, include_ledger: bool = False) -> bytes:
    workbook = Workbook()
    clients = workbook.active
    clients.title = "Clients"
    clients.append(["CLIENT MASTER"])
    clients.append([])
    clients.append(["Client ID", "Client Name", "Opening Capital", "Current Status", "Join Date", "Fee Type", "Fee Value"])
    clients.append(["C001", "Poorna", 15000, "Active", "2026-01-01", "None", 0])

    status = workbook.create_sheet("Status History")
    status.append(["STATUS HISTORY"])
    status.append([])
    status.append(["Client ID", "Client Name", "Status", "From Date", "To Date", "Remarks"])
    if include_nested_exception:
        status.append(["C001", "Poorna", "Active", "2026-01-01", "2026-12-31", None])
        status.append(["C001", "Poorna", "Inactive", "2026-09-07", "2026-09-14", None])
    else:
        status.append(["C001", "Poorna", "Active", "2026-01-01", "2026-06-30", None])
        status.append(["C001", "Poorna", "Inactive", "2026-07-01", "2026-12-31", None])
    if include_overlap:
        status.append(["C001", "Poorna", "Active", "2026-06-30", "2026-08-01", None])
    if include_example_note:
        status.append(["Example", "Instructional note only", None, None, None, None])

    movements = workbook.create_sheet("Fund Movements")
    movements.append(["FUND MOVEMENTS"])
    movements.append([])
    movements.append(["Date", "Client ID", "Client Name", "Type", "Amount", "Signed Amount", "Remarks"])
    movements.append(["2026-01-01", "C001", "Poorna", "Deposit", 500, 500, "opening top-up"])

    trading = workbook.create_sheet("Daily Trading")
    trading.append(["DAILY TRADING"])
    trading.append([])
    trading.append(["Date", "Day", "Gross Trading P&L", "Transaction Charges", "Net P&L"])
    trading.append(["2026-01-01", "Thursday", 1000, 100, 900])

    if include_ledger:
        ledger = workbook.create_sheet("Client Ledger")
        ledger.append(["CLIENT LEDGER"])
        ledger.append([])
        ledger.append(["Date", "Client ID", "Fund Movement", "Capital Before P&L", "Capital Share %", "Net Daily P&L", "Allocated P&L", "Closing Balance (After Fee)", "Daily Return %", "Status on Date", "Fee Debited", "Net Client P&L", "Manager Fee Credit"])
        ledger.append(["2026-01-01", "C001", 500, 10500, 100, 900, 900, 11400, 8.571429, "Active", 0, 900, 0])

    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def test_excel_import_commit_persists_reference_rows(auth_headers):
    response = client.post(
        "/import/excel/commit",
        files={"file": ("reference.xlsx", workbook_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["imported"] == {
        "clients": 1,
        "status_history": 2,
        "fund_movements": 1,
        "daily_trading": 1,
        "client_ledger": 0,
    }

    with SessionLocal() as db:
        assert db.query(Client).filter_by(client_code="C001").count() == 1
        assert db.query(DailyTrading).filter_by(trading_date="2026-01-01").count() == 1
        assert db.query(ClientLedger).filter_by(client_id=db.query(Client).filter_by(client_code="C001").one().id).count() == 1


def test_excel_import_commit_rolls_back_on_status_overlap(auth_headers):
    response = client.post(
        "/import/excel/commit",
        files={"file": ("invalid.xlsx", workbook_bytes(include_overlap=True), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )

    assert response.status_code == 400
    with SessionLocal() as db:
        assert db.query(Client).filter_by(client_code="C001").count() == 0


def test_excel_import_ignores_status_history_instruction_rows(auth_headers):
    response = client.post(
        "/import/excel/commit",
        files={"file": ("reference.xlsx", workbook_bytes(include_example_note=True), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text


def test_excel_import_splits_nested_status_exceptions(auth_headers):
    response = client.post(
        "/import/excel/commit",
        files={"file": ("reference.xlsx", workbook_bytes(include_nested_exception=True), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["imported"]["status_history"] == 3


def test_excel_import_preserves_workbook_ledger_values(auth_headers):
    response = client.post(
        "/import/excel/commit",
        files={"file": ("reference.xlsx", workbook_bytes(include_ledger=True), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["imported"]["client_ledger"] == 1
    with SessionLocal() as db:
        entry = db.query(ClientLedger).one()
        assert entry.closing_balance == 11400
        assert entry.calculation_version == "workbook-import"
