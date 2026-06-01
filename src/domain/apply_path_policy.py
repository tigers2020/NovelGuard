"""Pure path policy for library-scoped move_duplicate operations."""

from __future__ import annotations

from pathlib import Path

from domain.apply_models import PolicyBlockReason, PolicyResult, PreviewOperation


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

    dest, dest_reason = resolve_destination_path(library_root, operation.dest_path)
    if dest_reason is not None or dest is None:
        return PolicyResult(allowed=False, reason=dest_reason or "invalid_target")

    if destination_exists:
        return PolicyResult(allowed=False, reason="destination_exists")

    return PolicyResult(allowed=True)


def build_move_duplicate_dest_relative(target_folder: str, source_basename: str) -> str:
    """Join relative target folder and basename using forward slashes."""
    folder = target_folder.strip().replace("\\", "/").strip("/")
    if not folder:
        return source_basename
    return f"{folder}/{source_basename}"


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
