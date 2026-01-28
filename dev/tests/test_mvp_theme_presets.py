from src.ui.theme_manager import ThemeManager


def test_premium_themes_present(tmp_path):
    manager = ThemeManager(config_dir=str(tmp_path))
    names = manager.get_theme_names()
    assert "Neo Dark" in names
    assert "Nord Frost" in names
    assert "Solar Light" in names
    assert "CRT Green" in names
    assert "GameBoy DMG" in names
