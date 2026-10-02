"""Shared kit every domain tool server is built on.

The kit is what makes tools written by different teams look the same to the model:
one result envelope, one way to resolve periods, one way identity arrives, and one
contract checker the reviewing team runs in CI.
"""

from .envelope import Envelope, ResolvedPeriod, ToolError, data, empty, error
from .identity import Identity, identity_from, issue_token, require_identity, Unauthenticated
from .periods import NamedPeriod, PeriodError, resolve_period
from .contract import Violation, check_tools

__all__ = [
    "Envelope", "ResolvedPeriod", "ToolError", "data", "empty", "error",
    "Identity", "identity_from", "issue_token", "require_identity", "Unauthenticated",
    "NamedPeriod", "PeriodError", "resolve_period",
    "Violation", "check_tools",
]
