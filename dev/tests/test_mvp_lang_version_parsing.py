import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_infer_languages_and_version_from_name():
    from src.app.controller import infer_languages_and_version_from_name

    langs, ver = infer_languages_and_version_from_name("Game Title (En,Fr,De) (Rev 1).zip")
    assert langs == ("De", "En", "Fr")
    assert ver == "Rev 1"

    langs2, ver2 = infer_languages_and_version_from_name("Title v1.1 (Proto).bin")
    assert langs2 == ()
    assert ver2 == "v1.1"

    langs3, ver3 = infer_languages_and_version_from_name("Something (en) (beta).rom")
    assert langs3 == ("En",)
    assert ver3 == "Beta"
