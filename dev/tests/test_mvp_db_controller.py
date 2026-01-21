import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_db_controller_init_and_backup(tmp_path):
    from src.app import db_controller

    db_path = tmp_path / "roms.db"
    init_path = db_controller.init_db(str(db_path))
    assert init_path.exists()

    backup_path = db_controller.backup_db(str(db_path))
    assert backup_path.exists()


def test_db_controller_scan_and_import(tmp_path):
    from src.app import db_controller

    db_path = tmp_path / "roms.db"
    db_controller.init_db(str(db_path))

    scan_dir = tmp_path / "roms"
    scan_dir.mkdir()
    (scan_dir / "game.rom").write_text("data")

    # No consoles configured, scan should be safe and return 0
    assert db_controller.scan_roms(str(scan_dir), db_path=str(db_path), recursive=True) == 0

    dat_file = tmp_path / "test.dat"
    dat_file.write_text(
        """<?xml version='1.0'?>
        <datafile>
          <header><name>TestConsole</name></header>
          <game name='Game'>
            <rom name='game.rom' size='1' crc='deadbeef'/>
          </game>
        </datafile>
        """
    )

    # Import should not error; count can be 0 if no matching rows
    assert db_controller.import_dat(str(dat_file), db_path=str(db_path)) >= 0
