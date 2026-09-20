# Business Rules

This document captures the rules represented by the Excel workbook and translated into application logic.

## Client status

- A client may be ACTIVE or INACTIVE.
- Status is determined by trading date.
- Only active clients participate in P&L allocation.
- Historical status periods may not overlap.

## Fund movements

- Deposits increase capital and carry positive signed values.
- Withdrawals decrease capital and carry negative signed values.
- Movements remain auditable and are never silently deleted.

## Daily trading

- Net P&L is gross trading P&L minus transaction charges.
- One trading record per date is expected.

## Allocation

- Allocate P&L proportionally to active capital.
- Avoid floating-point arithmetic; use Decimal.
- Preserve rounding policy at defined accounting boundaries.

## Manager fees

- Fees are transferred to a configurable manager account.
- The manager account should not be hard-coded in the business logic.
