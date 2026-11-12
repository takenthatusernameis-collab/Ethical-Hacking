# Next Task

## Status
Session 119 closed the `smb` formatter `security_flags` hostile-shape gap (the source hardening from session 118 was already in place; this session fixed its defective test so the sweep is green).

## One precise next task
Harden `ldap` formatter `root_dse` handling: `ethscan/ldap.py` `format_ldap_report_markdown` (lines 692-712) and `format_ldap_report_csv` (lines 776-780) iterate `root_dse` as a dict and join its values, raising when `root_dse` is `None`/`int`/`str`/`list` or a dict with non-list/non-string values. Reproduce with the 7 hostile shapes, fix by coercing `root_dse` to a normalized dict of string-lists (reject non-dict; stringify list elements; drop non-list values), add a focused hostile-sweep test, verify module tests + mypy/ruff. One module, reproduce first.

Repro evidence (pre-fix): `{"root_dse": 1}` → TypeError; `{"root_dse": "string"}` / `{"root_dse": [1,2]}` → AttributeError; `{"root_dse": {"vendorName": 1}}` / `{"vendorName": None}` → TypeError; `{"vendorName": [None, 1]}` → TypeError.

## Notes
- `oracle` and `postgresql` empty-target handling remains intentionally out of scope per their documented contract (exit 0, in-band error).
- Other hostile-shape gaps noted by the session 117 fuzzer (wrong-typed iterable fields in ftp/ntp/oracle/smtp/snmp and others) remain open but are separate bounded families — pick one at a time and reproduce first.
- Do not weaken CLI validation or tests. Preserve oracle/postgresql in-band exit-0 contract vs usage-error exits elsewhere.