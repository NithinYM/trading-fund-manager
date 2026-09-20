"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-09-19 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="ADMIN"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "clients",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("client_code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("opening_capital", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("join_date", sa.Date(), nullable=False),
        sa.Column("contact", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("fee_type", sa.String(), nullable=False, server_default="NONE"),
        sa.Column("fee_value", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("fee_basis", sa.String(), nullable=True),
        sa.Column("fee_start_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_code"),
    )
    op.create_index(op.f("ix_clients_client_code"), "clients", ["client_code"], unique=True)
    op.create_index(op.f("ix_clients_id"), "clients", ["id"], unique=False)

    op.create_table(
        "client_status_history",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("client_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("from_date", sa.Date(), nullable=False),
        sa.Column("to_date", sa.Date(), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_client_status_history_client_id"), "client_status_history", ["client_id"], unique=False)
    op.create_index(op.f("ix_client_status_history_id"), "client_status_history", ["id"], unique=False)

    op.create_table(
        "fund_movements",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("client_id", sa.String(), nullable=False),
        sa.Column("movement_type", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("signed_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fund_movements_client_id"), "fund_movements", ["client_id"], unique=False)
    op.create_index(op.f("ix_fund_movements_date"), "fund_movements", ["date"], unique=False)
    op.create_index(op.f("ix_fund_movements_id"), "fund_movements", ["id"], unique=False)

    op.create_table(
        "daily_trading",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("trading_date", sa.Date(), nullable=False),
        sa.Column("gross_trading_pnl", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("transaction_charges", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("net_pnl", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trading_date"),
    )
    op.create_index(op.f("ix_daily_trading_id"), "daily_trading", ["id"], unique=False)
    op.create_index(op.f("ix_daily_trading_trading_date"), "daily_trading", ["trading_date"], unique=True)

    op.create_table(
        "client_ledger",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("trading_date", sa.Date(), nullable=False),
        sa.Column("client_id", sa.String(), nullable=False),
        sa.Column("fund_movement", sa.Numeric(precision=18, scale=2), nullable=True, server_default="0.00"),
        sa.Column("capital_before_pnl", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("capital_share_percent", sa.Numeric(precision=18, scale=6), nullable=False, server_default="0.000000"),
        sa.Column("net_daily_pnl", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("allocated_pnl", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("fee_debited", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("net_client_pnl", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("closing_balance", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("daily_return_percent", sa.Numeric(precision=18, scale=6), nullable=True, server_default="0.000000"),
        sa.Column("status_on_date", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("manager_fee_credit", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("calculation_version", sa.String(), nullable=False, server_default="v1"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_client_ledger_id"), "client_ledger", ["id"], unique=False)
    op.create_index(op.f("ix_client_ledger_client_id"), "client_ledger", ["client_id"], unique=False)
    op.create_index(op.f("ix_client_ledger_trading_date"), "client_ledger", ["trading_date"], unique=False)

    op.create_table(
        "manager_accounts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("opening_capital", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_manager_accounts_code"), "manager_accounts", ["code"], unique=True)
    op.create_index(op.f("ix_manager_accounts_id"), "manager_accounts", ["id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("old_values", sa.JSON(), nullable=True),
        sa.Column("new_values", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_id"), "audit_logs", ["id"], unique=False)
    op.create_index(op.f("ix_audit_logs_timestamp"), "audit_logs", ["timestamp"], unique=False)
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("manager_accounts")
    op.drop_table("client_ledger")
    op.drop_table("daily_trading")
    op.drop_table("fund_movements")
    op.drop_table("client_status_history")
    op.drop_table("clients")
    op.drop_table("users")
