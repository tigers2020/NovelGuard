"""Pure path policy for library-scoped move_duplicate operations."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from domain.apply_models import PolicyBlockReason, PolicyResult, PreviewOperation
from domain.duplicate_archive import (
    build_duplicate_archive_dest,
    is_path_under_duplicate_archive,
)


def resolve_under_library_root(
    library_root: Path, relative: str
) -> tuple[Path | None, PolicyBlockReason | None]:
    """Resolve an existing relative path under library_root, or return block reason."""
    rel = _normalize_relative(relative)
    if rel is None:
        return None, "path_traversal"
    root = library_root.resolve()
    candidate = (root / rel).resolve()
    if not _is_under_root(candidate, root):
        return None, "outside_root"
    return candidate, None


def resolve_destination_path(
    library_root: Path,
    dest_relative: str,
) -> tuple[Path | None, PolicyBlockReason | None]:
    """Resolve destination file path: parent resolved; basename appended lexically."""
    dest_norm = dest_relative.replace("\\", "/").strip()
    if not dest_norm or dest_norm.startswith("/"):
        return None, "absolute_path"
    dest_parts = Path(dest_norm)
    if ".." in dest_parts.parts:
        return None, "path_traversal"

    basename = dest_parts.name
    parent_rel = dest_parts.parent
    if parent_rel == Path("."):
        parent_resolved: Path | None = library_root.resolve()
    else:
        parent_resolved, reason = resolve_under_library_root(
            library_root, str(parent_rel).replace("\\", "/")
        )
        if reason is not None or parent_resolved is None:
            return None, reason or "invalid_target"

    assert parent_resolved is not None
    candidate = parent_resolved / basename
    root = library_root.resolve()
    if not _is_under_root(candidate, root):
        return None, "outside_root"
    return candidate, None


def resolve_apply_destination(
    library_root: Path,
    dest_path: str,
) -> tuple[Path | None, PolicyBlockReason | None]:
    """Resolve move destination: external duplicate archive or legacy library-relative path."""
    dest_text = dest_path.strip()
    if not dest_text:
        return None, "invalid_target"

    candidate = Path(dest_text)
    if candidate.is_absolute():
        resolved = candidate.resolve()
        if is_path_under_duplicate_archive(resolved, library_root):
            return resolved, None
        return None, "outside_root"

    dest_norm = dest_text.replace("\\", "/")
    if dest_norm == "duplicate" or dest_norm.startswith("duplicate/"):
        basename = Path(dest_norm).name
        if not basename:
            return None, "invalid_target"
        return build_duplicate_archive_dest(library_root.resolve(), basename).resolve(), None

    return resolve_destination_path(library_root, dest_text)


def validate_move_operation(
    library_root: Path,
    operation: PreviewOperation,
    *,
    destination_exists: bool,
) -> PolicyResult:
    if operation.action != "move_duplicate":
        return PolicyResult(allowed=False, reason="unsupported_action")

    source, src_reason = resolve_under_library_root(library_root, operation.source_path)
    if src_reason is not None or source is None:
        return PolicyResult(allowed=False, reason=src_reason or "invalid_target")

    dest, dest_reason = resolve_apply_destination(library_root, operation.dest_path)
    if dest_reason is not None or dest is None:
        return PolicyResult(allowed=False, reason=dest_reason or "invalid_target")

    root = library_root.resolve()
    if _is_under_root(dest, root):
        return PolicyResult(allowed=False, reason="invalid_target")

    if destination_exists:
        return PolicyResult(allowed=False, reason="destination_exists")

    return PolicyResult(allowed=True)


def build_move_duplicate_dest_relative(target_folder: str, source_basename: str) -> str:
    """Join relative target folder and basename using forward slashes."""
    folder = target_folder.strip().replace("\\", "/").strip("/")
    if not folder:
        return source_basename
    return f"{folder}/{source_basename}"


def allocate_unique_dest_relative(
    library_root: Path,
    dest_relative: str,
    *,
    destination_exists: Callable[[str], bool],
) -> str:
    """Pick ``dest_relative`` or ``name (2).ext`` when the destination file already exists."""
    if not destination_exists(dest_relative):
        return dest_relative

    path = Path(dest_relative.replace("\\", "/"))
    parent = path.parent
    parent_prefix = "" if parent == Path(".") else f"{parent.as_posix()}/"
    stem = path.stem
    suffix = path.suffix

    for index in range(2, 10_000):
        candidate = f"{parent_prefix}{stem} ({index}){suffix}"
        if not destination_exists(candidate):
            return candidate
    return dest_relative


def _normalize_relative(relative: str) -> Path | None:
    text = relative.replace("\\", "/").strip()
    if not text or text.startswith("/"):
        return None
    parts = [p for p in Path(text).parts if p not in (".", "")]
    if ".." in parts:
        return None
    return Path(*parts) if parts else Path(".")


def _is_under_root(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False
