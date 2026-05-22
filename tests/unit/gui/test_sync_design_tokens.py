"""DESIGN.md token sync tests."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_design_md_exists() -> None:
    assert (REPO_ROOT / "DESIGN.md").is_file()


def test_generated_dark_primary_matches_design() -> None:
    from gui.styles.tokens.colors_dark import PRIMARY

    assert PRIMARY == "#BB86FC"


def test_theme_registry_dark_has_no_gradient() -> None:
    from gui.styles.theme_mode import ThemeMode
    from gui.styles.theme_registry import get_stylesheet

    qss = get_stylesheet(ThemeMode.DARK)
    assert "#BB86FC" in qss
    assert "qlineargradient" not in qss
