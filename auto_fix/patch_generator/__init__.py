# auto_fix/patch_generator/__init__.py

from .update_patch import create_update_patch
from .compatibility_patch import generate_compatibility_patch, batch_generate

__all__ = [
    "create_update_patch",
    "generate_compatibility_patch",
    "batch_generate",
]