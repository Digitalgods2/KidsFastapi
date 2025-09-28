# SQLite shim for local development
# This module re-exports everything from database_fixed to avoid Postgres dependency
from database_fixed import *  # noqa: F401,F403

try:
    from database_fixed import __all__  # type: ignore
except Exception:
    __all__ = [n for n in globals().keys() if not n.startswith('_')]
