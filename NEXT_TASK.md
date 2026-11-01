# Next Task
Verify `.github/workflows/test.yml` on GitHub Actions across ubuntu/macos/windows.

Blocked: current token lacks `workflows` permission, so the workflow file cannot be pushed. Obtain a PAT with `workflows` scope (or run matrix via `act` locally), then create the workflow and trigger it.
