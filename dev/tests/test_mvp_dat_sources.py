import sys
import zipfile
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_analyze_dat_sources_counts(tmp_path):
    from src.app.controller import analyze_dat_sources

    dat_dir = tmp_path / "dats"
    dat_dir.mkdir()
    (dat_dir / "a.dat").write_text("x")
    (dat_dir / "b.xml").write_text("x")
    zip_path = dat_dir / "c.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("inner.dat", "x")

    missing = tmp_path / "missing"

    report = analyze_dat_sources([str(dat_dir), str(missing)])

    assert str(dat_dir) in report.existing_paths
    assert str(missing) in report.missing_paths
    assert report.dat_files == 1
    assert report.dat_xml_files == 1
    assert report.dat_zip_files == 1
