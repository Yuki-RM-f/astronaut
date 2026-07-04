from __future__ import annotations

from pathlib import Path


LOCAL_MATERIALS_ROOT = Path("storage") / "materials"


def remove_local_material_file(storage_url: str | None) -> bool:
    path = _local_material_path(storage_url)
    if path is None or not path.is_file():
        return False
    try:
        path.unlink()
    except OSError:
        return False
    return True


def remove_local_material_files(storage_urls: list[str | None]) -> None:
    for storage_url in storage_urls:
        remove_local_material_file(storage_url)


def _local_material_path(storage_url: str | None) -> Path | None:
    if not storage_url or "://" in storage_url:
        return None

    path = Path(storage_url)
    try:
        root = LOCAL_MATERIALS_ROOT.resolve(strict=False)
        resolved = path.resolve(strict=False)
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return None
    return resolved
