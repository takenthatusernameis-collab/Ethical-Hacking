Next task: Land `.github/workflows/test.yml` on remote/main. BLOCKED by credential scope — `GH_TOKEN`/`GITHUB_TOKEN` are a GitHub App token lacking `workflows` write scope (confirmed 403 on push and actions/permissions API); no PAT with `workflows` scope available. `test.yml` content is preserved in git history at commits `4686103` and `b4d5c13` (identical). HEAD = origin/main = `75199d3` (clean, in sync, test.yml absent; `75199d3` removed it). Locally verified green previously: `python -m ruff check ethscan tests` clean and `python -m pytest -q` 5472 passed/50 skipped.

Precise next task: Obtain a PAT/GitHub App token with `workflows` write scope for `takenthatusernameis-collab/Ethical-Hacking`, then:
1. Restore `test.yml` (`git show 4686103:.github/workflows/test.yml > .github/workflows/test.yml`) and commit.
2. `git push origin main`.
3. Trigger (`gh workflow run test.yml -R takenthatusernameis-collab/Ethical-Hacking --ref main`) and confirm ubuntu/macos/windows pass.

If no token: infrastructure blocker — durable state is test.yml content in git history (`4686103`/`b4d5c13`) plus local verification. Do not retry the push without a new token (deterministic 403).
