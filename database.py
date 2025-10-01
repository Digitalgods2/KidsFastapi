"""Compatibility shim that re-exports the final database layer.

Many legacy modules and tests expect a ``database`` package. The production
code, however, was consolidated into ``database_fixed``.  Importing this module
keeps those imports working while ensuring a single source of truth.
"""
from database_fixed import *  # noqa: F401,F403
