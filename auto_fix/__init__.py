# auto_fix/__init__.py

from .backup import backup_file, list_backups, restore_backup
from .manifest_fixer import fix_manifest_issues, fix_all_mods
from .patch_generator import create_update_patch, generate_compatibility_patch, batch_generate

__all__ = [
    "backup_file", "list_backups", "restore_backup",
    "fix_manifest_issues", "fix_all_mods",
    "create_update_patch", "generate_compatibility_patch", "batch_generate",
]