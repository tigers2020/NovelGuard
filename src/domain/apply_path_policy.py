"""Pure path policy for library-scoped move_duplicate operations."""

from __future__ import annotations

from pathlib import Path

from domain.apply_models import PolicyBlockReason, PolicyResult, PreviewOperation

DEFAULT_MOVE_DUPLICATE_FOLDER = "duplicate"


def duplicate_folder_name(target_folder: str) -> str:
    folder = target_folder.strip().replace("\\", "/").strip("/")
    return folder if folder else DEFAULT_MOVE_DUPLICATE_FOLDER


def duplicate_output_root(library_root: Path, target_folder: str) -> Path:
    """Sibling duplicate folder outside library root (per-library subfolder)."""
    name = duplicate_folder_name(target_folder)
    return (library_root.parent / name / library_root.name).resolve()


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


def resolve_duplicate_destination_path(
    library_root: Path,
    target_folder: str,
    dest_relative: str,
) -> tuple[Path | None, PolicyBlockReason | None]:
    """Resolve destination under sibling duplicate folder (outside library_root)."""
    rel = _normalize_relative(dest_relative)
    if rel is None:
        return None, "path_traversal"
    out_root = duplicate_output_root(library_root, target_folder)
    candidate = (out_root / rel).resolve()
    if not _is_under_root(candidate, out_root):
        return None, "outside_root"
    lib = library_root.resolve()
    if _is_under_root(candidate, lib):
        return None, "invalid_target"
    return candidate, None


def resolve_destination_path(
    library_root: Path,
    dest_relative: str,
) -> tuple[Path | None, PolicyBlockReason | None]:
    """Backward-compatible alias: duplicate moves resolve outside library_root."""
    return resolve_duplicate_destination_path(
        library_root, DEFAULT_MOVE_DUPLICATE_FOLDER, dest_relative
    )


def validate_move_operation(
    library_root: Path,
    operation: PreviewOperation,
    *,
    destination_exists: bool,
    target_folder: str = DEFAULT_MOVE_DUPLICATE_FOLDER,
) -> PolicyResult:
    if operation.action != "move_duplicate":
        return PolicyResult(allowed=False, reason="unsupported_action")

    source, src_reason = resolve_under_library_root(library_root, operation.source_path)
    if src_reason is not None or source is None:
        return PolicyResult(allowed=False, reason=src_reason or "invalid_target")

    dest, dest_reason = resolve_duplicate_destination_path(
        library_root, target_folder, operation.dest_path
    )
    if dest_reason is not None or dest is None:
        return PolicyResult(allowed=False, reason=dest_reason or "invalid_target")

    if destination_exists:
        return PolicyResult(allowed=False, reason="destination_exists")

    return PolicyResult(allowed=True)


def build_move_duplicate_dest_relative(target_folder: str, source_relative_path: str) -> str:
    """Path inside external duplicate folder (preserves library-relative layout)."""
    rel = source_relative_path.replace("\\", "/").lstrip("/")
    folder = duplicate_folder_name(target_folder)
    if rel == folder or rel.startswith(f"{folder}/"):
        rel = rel[len(folder) :].lstrip("/")
    return rel


def format_move_duplicate_dest_display(
    library_root: Path, target_folder: str, dest_relative: str
) -> str:
    """Human-readable destination for preview UI (sibling duplicate folder)."""
    rel = dest_relative.replace("\\", "/").lstrip("/")
    name = duplicate_folder_name(target_folder)
    lib = library_root.name
    if rel:
        return f"../{name}/{lib}/{rel}"
    return f"../{name}/{lib}"


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
