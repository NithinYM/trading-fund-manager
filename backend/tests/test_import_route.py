from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.main import app

client = TestClient(app)


def test_excel_import_returns_workbook_preview():
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Clients"
    worksheet.append(["Client Code", "Name"])
    worksheet.append(["C5001", "Imported Client"])
    stream = BytesIO()
    workbook.save(stream)

    response = client.post(
        "/import/excel",
        files={
            "file": (
                "fund.xlsx",
                stream.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["filename"] == "fund.xlsx"
    assert response.json()["sheets"] == [{"name": "Clients", "rows": 2, "columns": 2}]
    assert response.json()["mappings"] == [
        {
            "sheet": "Clients",
            "recognized": False,
            "data_rows": 0,
            "errors": ["Required headers were not found"],
        }
    ]


def test_excel_import_rejects_non_excel_files():
    response = client.post(
        "/import/excel",
        files={"file": ("fund.txt", b"not an Excel workbook", "text/plain")},
    )

    assert response.status_code == 400
    assert "xlsx" in response.json()["detail"].lower()


def test_excel_import_recognizes_reference_clients_sheet():
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Clients"
    worksheet.append(["CLIENT MASTER"])
    worksheet.append([])
    worksheet.append(["Client ID", "Client Name", "Opening Capital", "Current Status", "Join Date"])
    worksheet.append(["C001", "Poorna", 15000, "Active", "2026-01-01"])
    stream = BytesIO()
    workbook.save(stream)

    response = client.post(
        "/import/excel",
        files={"file": ("reference.xlsx", stream.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 200, response.text
    assert response.json()["mappings"] == [
        {
            "sheet": "Clients",
            "recognized": True,
            "header_row": 3,
            "data_rows": 1,
            "errors": [],
        }
    ]
