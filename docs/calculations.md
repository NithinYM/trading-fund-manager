# Calculation Rules

## Rounding policy

- Use Python Decimal for all money calculations.
- Store values as PostgreSQL NUMERIC.
- Round to 2 decimal places using HALF_UP rounding.
- Apply rounding only at defined accounting boundaries.

## Allocation formula

For each active client:

capital_share_percent = client_capital_before_pnl / total_active_capital
allocated_pnl = daily_net_pnl * capital_share_percent

## Fees

- Percentage fee: allocated_pnl * fee_value / 100 if positive
- Fixed fee: fee_value for eligible active days
- No fee: zero

## Capital reconciliation

closing_balance = previous_capital + deposits - withdrawals + allocated_pnl - fees

This logic is centralized in the calculation engine and must not be duplicated across the UI or API routes.
