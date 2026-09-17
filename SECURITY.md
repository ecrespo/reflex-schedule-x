# Security Policy

## Supported versions

Only the latest released version of `reflex-schedule-x` receives security fixes.

## Reporting a vulnerability

Please **do not open a public issue** for security problems. Report them privately through
[GitHub Security Advisories](https://github.com/ecrespo/reflex-schedule-x/security/advisories/new).

Include a description of the issue, steps to reproduce and the affected version. You should get a first response
within 7 days.

## Automated checks

Every push and pull request runs the `Security` workflow: CodeQL (Python, JavaScript and GitHub Actions),
Bandit, pip-audit against the locked dependencies, Gitleaks over the full git history and, on pull requests,
GitHub dependency review.
