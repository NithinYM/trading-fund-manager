from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.services.excel_commit_service import ExcelCommitService
from app.services.excel_import_service import ExcelImportService
from app.services.audit_service import record_audit

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/excel")
async def import_excel(file: UploadFile = File(...)) -> dict[str, object]:
    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .xlsx Excel files are supported",
        )

    try:
        content = await file.read()
        preview = ExcelImportService.preview(content)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid .xlsx workbook",
        ) from exc

    return {"filename": filename, **preview}


@router.post("/excel/commit")
async def commit_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles("ADMIN", "MANAGER")),
) -> dict[str, object]:
    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .xlsx Excel files are supported",
        )

    try:
        imported = ExcelCommitService.import_workbook(await file.read(), db)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workbook import failed") from exc

    record_audit(db, user, "IMPORT", "WORKBOOK", filename, new_values={"filename": filename, "imported": imported})
    return {"filename": filename, "imported": imported}
