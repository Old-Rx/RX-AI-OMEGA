# Security policy

## Supported versions

Security updates are provided for the latest release on the default branch.

## Reporting a vulnerability

Do not open a public issue. Use GitHub's private vulnerability reporting feature for this repository. Include affected routes/components, reproduction steps, impact, and any suggested mitigation. Maintainers should acknowledge a complete report within five business days and coordinate disclosure after a fix is available.

Never include real credentials, access tokens, personal data, or production document content in a report. Rotate any credential accidentally exposed during testing.

## Operational responsibility

Operators must provide strong secrets, TLS, network isolation, authentication throttling at the edge, backups, and least-privilege provider credentials. See `docs/DEPLOYMENT.md`.
