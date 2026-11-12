# Next Task

## Status
Session 112 made the README `nmap --input-file broken.xml` example resilient to parser wording differences by documenting the stable contract (usage error exit 2 and `Invalid value for '--input-file': invalid Nmap XML:` prefix) instead of asserting one parser-specific tail. `ruff check ethscan/ tests/` passed; the reproduced CLI check confirmed exit 2 with the expected prefix.

## One precise next task
No further task identified this session. If a new task is needed, inspect `TASK.md`, the README, and recent git history for the next bounded, high-value improvement.

## Notes
- Keep README examples evidence-based; do not invent outputs.
- Do not weaken CLI validation or tests. Preserve oracle/postgresql in-band exit-0 contract vs usage-error exits elsewhere.

(End of file - total 11 lines)