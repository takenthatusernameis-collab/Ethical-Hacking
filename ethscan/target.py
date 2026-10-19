"""Shared target-specification types for ethscan.

Several protocol modules accept a target string that may be a bare host, a
``host:port`` pair, or a scheme URL (``redis://host:port``). When such a
string does not contain a usable host, the module raises
:class:`TargetSpecError` so the CLI layer can report the problem as a usage
error instead of letting a raw traceback escape.

The module is intentionally free of any click import: the translation from a
library error to a click usage error happens in :mod:`ethscan.cli`.
"""
from __future__ import annotations


class TargetSpecError(ValueError):
    """Raised when a target string does not contain a usable host.

    Subclasses :class:`ValueError` so that modules which treat an
    unparsable target as a failed probe (and report it inside their own
    output) keep working unchanged, while letting the CLI layer distinguish
    an invalid target from unrelated value errors and turn it into a usage
    error.
    """
