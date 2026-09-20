# Architecture

This project follows a layered architecture with clear separation of concerns.

## Layers

- Presentation: React frontend
- API: FastAPI service layer
- Domain: calculation and reconciliation services
- Data access: SQLAlchemy models and repositories
- Database: PostgreSQL

## Core design principles

- Centralized financial calculations
- Persistent ledger for auditability
- Deterministic recalculation engine
- Strong validation, role checks, and audit logs
- Dependency on DB and backend rather than Excel
