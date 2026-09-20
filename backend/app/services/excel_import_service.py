from __future__ import annotations

from io import BytesIO
from typing import Any

from openpyxl import load_workbook


SUPPORTED_SHEETS = {
    "Clients": {"Client ID", "Client Name", "Opening Capital", "Join Date"},
    "Status History": {"Client ID", "Status", "From Date", "To Date"},
    "Fund Movements": {"Date", "Client ID", "Type", "Amount"},
    "Daily Trading": {"Date", "Gross Trading P&L", "Transaction Charges"},
    "Client Ledger": {"Date", "Client ID", "Allocated P&L", "Closing Balance (After Fee)"},
}

PRIMARY_COLUMNS = {
    "Clients": "Client ID",
    "Status History": "Client ID",
    "Fund Movements": "Client ID",
    "Daily Trading": "Date",
    "Client Ledger": "Date",
}


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _find_header(rows: list[tuple[Any, ...]], required: set[str]) -> tuple[int, dict[str, int]] | None:
    for row_index, row in enumerate(rows[:10]):
        headers = {_text(value): index for index, value in enumerate(row) if _text(value)}
        if required.issubset(headers):
            return row_index, headers
    return None


def _analyze_sheet(name: str, rows: list[tuple[Any, ...]]) -> dict[str, Any] | None:
    required = SUPPORTED_SHEETS.get(name)
    if required is None:
        return None
    header = _find_header(rows, required)
    if header is None:
        return {"sheet": name, "recognized": False, "data_rows": 0, "errors": ["Required headers were not found"]}

    header_index, headers = header
    key_index = headers[PRIMARY_COLUMNS[name]]
    data_rows = 0
    errors: list[str] = []
    for row_number, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        if not any(value is not None for value in row):
            continue
        if key_index >= len(row) or row[key_index] in (None, ""):
            errors.append(f"Row {row_number}: missing primary value")
            continue
        if name == "Clients":
            row_values = {_text(header): row[index] if index < len(row) else None for header, index in headers.items()}
            if row_values.get("Client ID") and not row_values.get("Client Name") and not row_values.get("Opening Capital") and not row_values.get("Join Date"):
                continue
        data_rows += 1

    return {
        "sheet": name,
        "recognized": True,
        "header_row": header_index + 1,
        "data_rows": data_rows,
        "errors": errors,
    }


def _content_dimensions(rows: list[tuple[Any, ...]]) -> tuple[int, int]:
    non_empty_rows = [row for row in rows if any(value not in (None, "") for value in row)]
    columns = max(
        (index + 1 for row in non_empty_rows for index, value in enumerate(row) if value not in (None, "")),
        default=0,
    )
    return len(non_empty_rows), columns


class ExcelImportService:
    @staticmethod
    def preview(content: bytes) -> dict[str, Any]:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        sheets = []
        mappings = []
        for worksheet in workbook.worksheets:
            rows = list(worksheet.iter_rows(values_only=True))
            content_rows, content_columns = _content_dimensions(rows)
            sheets.append(
                {
                    "name": worksheet.title,
                    "rows": content_rows,
                    "columns": content_columns,
                }
            )
            mapping = _analyze_sheet(worksheet.title, rows)
            if mapping is not None:
                mappings.append(mapping)
        workbook.close()
        return {"sheets": sheets, "mappings": mappings}
