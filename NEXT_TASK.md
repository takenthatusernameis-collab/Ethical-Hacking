# Next Task

## Status
Session 111 removed duplicated README usage/error text (repeated mysql/mongodb/mssql vs oracle/postgresql target-contract note and duplicated file-validation/example block) while preserving verified command behaviors. `ruff check ethscan/ tests/` passed; representative CLI checks reproduced expected usage-error behavior for malformed nmap XML and invalid UTF-8 credential-file input.

## One precise next task
Make the README `nmap --input-file broken.xml` example resilient to parser wording differences by documenting/illustrating the stable contract (usage error, exit 2, `Invalid value for '--input-file': invalid Nmap XML:` prefix) rather than asserting one specific parser tail message, then verify the updated example against `python -m ethscan nmap --input-file /tmp/broken.xml` (or equivalent malformed file) and run `python -m ruff check README.md` is not applicable—run `python -m ruff check ethscan/ tests/`.

## Notes
- Keep README examples evidence-based; do not invent outputs.
- Do not weaken CLI validation or tests. Preserve oracle/postgresql in-band exit-0 contract vs usage-error exits elsewhere.
