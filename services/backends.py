"""Centralized backend registry and validation"""
from typing import Set

SUPPORTED_BACKENDS: Set[str] = {
    "dall-e-3",
    "dall-e-2",
    "vertex-imagen",
    "vertex-children",
    "vertex-artistic",
}

def validate_backend(name: str) -> bool:
    return name in SUPPORTED_BACKENDS
