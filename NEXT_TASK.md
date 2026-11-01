Next task: Verify `.github/workflows/test.yml` passes on GitHub Actions across ubuntu/macos/windows.

Evidence:
- Workflow added at `.github/workflows/test.yml`; YAML parses cleanly.
- Baseline local checks green: pytest 5458 passed / 53 skipped; ruff clean; mypy clean (59 files); git clean except new workflow file.
- Constraints: cannot execute GitHub Actions locally; must trigger via push/PR and inspect the Actions run. Fix the workflow (smallest change) if any matrix job fails.
