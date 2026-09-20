# Data Model

This project stores fund operations in a relational model designed for auditability, deterministic calculations, and easy historical reconstruction.

## Core entities

### clients

Stores the master record for each investor or trading participant.

- id: primary key
- client_code: unique external code such as C001
- name: client display name
- opening_capital: initial capital at onboarding
- join_date: first eligible trading date
- contact: optional contact information
- notes: optional free-text notes
- status: current live state, typically ACTIVE or INACTIVE
- fee_type: NONE, PERCENTAGE, or FIXED
- fee_value: configured fee percentage or fixed amount
- fee_basis: optional helper field for future usage
- fee_start_date: when fee collection begins
- created_at / updated_at: timestamps
- is_deleted: soft-delete flag

### client_status_history

Tracks all status changes over time and ensures one valid state exists per trading date.

- id
- client_id: FK to clients
- status: ACTIVE or INACTIVE
- from_date
- to_date
- remarks
- created_at

Rules:

- A client may have multiple historical periods.
- Status periods must not overlap for the same client.
- The active state for a trading date is resolved via the date range.

### fund_movements

Captures capital inflows and outflows as immutable financial events.

- id
- date
- client_id: FK to clients
- movement_type: DEPOSIT or WITHDRAWAL
- amount: raw amount value
- signed_amount: positive or negative accounting value
- remarks
- created_at / updated_at

Rules:

- Deposits use positive signed amounts.
- Withdrawals use negative signed amounts.
- Historical movements are never silently removed.

### daily_trading

Represents a daily aggregated trading result.

- id
- trading_date: unique business date for the trade record
- gross_trading_pnl
- transaction_charges
- net_pnl
- remarks
- created_at / updated_at

Rules:

- One daily trading record per date is expected.
- net_pnl = gross_trading_pnl - transaction_charges
- The backend generates the result and stores it as the source of truth.

### client_ledger

Persistent audit ledger for each client on each trading date.

- id
- trading_date
- client_id
- fund_movement
- capital_before_pnl
- capital_share_percent
- net_daily_pnl
- allocated_pnl
- fee_debited
- net_client_pnl
- closing_balance
- daily_return_percent
- status_on_date
- manager_fee_credit
- calculation_version
- created_at / updated_at

This table is the main accountability record for the daily calculation cycle.

### manager_accounts

Tracks the manager-side account that receives fee transfers.

- id
- code: unique account identifier
- name
- starting_balance
- created_at / updated_at

The business logic is configurable and does not hard-code any personal name into the engine.

### audit_logs

Captures data changes for accountability.

- id
- user_id
- action
- entity_type
- entity_id
- old_values
- new_values
- timestamp

This supports operational traceability for client edits, trading fixes, movement updates, and status changes.

### users

Stores application users and their roles.

- id
- username
- email
- password_hash
- role
- is_active
- created_at / updated_at

## Entity relationships

- One client has many status records.
- One client has many fund movements.
- One client has many ledger entries.
- One daily trading record is linked to many ledger rows.
- One manager account may receive many fee transfers.
- One user may generate many audit entries.

## Accounting model

The ledger is a derived history, not a raw spreadsheet. It is generated from:

- client opening capital
- prior ledger closing balances
- status history date resolution
- daily trading net P&L
- active-client allocation
- fee rules
- manager transfer entries

This keeps the system deterministic and easier to reconcile during audits.
