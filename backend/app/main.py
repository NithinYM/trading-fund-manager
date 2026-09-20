from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.audit_logs import router as audit_logs_router
from app.api.routes.clients import router as clients_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.fund_movements import router as fund_movements_router
from app.api.routes.health import router as health_router
from app.api.routes.importer import router as import_router
from app.api.routes.manager_accounts import router as manager_accounts_router
from app.api.routes.reports import router as reports_router
from app.api.routes.status_history import router as status_history_router
from app.api.routes.trading import router as trading_router
from app.core.config import settings

app = FastAPI(
    title="Trading Fund Manager",
    version="0.1.0",
    description="Trading fund management backend",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(audit_logs_router)
app.include_router(dashboard_router)
app.include_router(clients_router)
app.include_router(fund_movements_router)
app.include_router(trading_router)
app.include_router(status_history_router)
app.include_router(manager_accounts_router)
app.include_router(reports_router)
app.include_router(import_router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Trading Fund Manager API"}
