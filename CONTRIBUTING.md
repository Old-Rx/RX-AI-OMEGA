# Contributing

Thank you for improving RX-AI OMEGA.

1. Open an issue for substantial behavior or schema changes.
2. Create a focused branch and never commit credentials, customer data, or `.env`.
3. Add or update tests for every control-flow or permission change.
4. Run the Python lint, type, test, migration, frontend lint, and frontend build commands from the README.
5. Explain risk, migration impact, and manual validation in the pull request template.

Security controls are not cosmetic. Changes that move a provider invocation before governance, weaken role checks, mutate decided approvals, or omit audit records require explicit security review.
