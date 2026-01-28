import sys
import time
import threading
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.integration


def test_dat_index_cancel_mid_parse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.core.dat_index_sqlite import DatHashRow, DatIndexSqlite

    index = DatIndexSqlite(tmp_path / "index.sqlite")
    fake_path = tmp_path / "fake.dat"
    fake_path.write_text("dummy")

    monkeypatch.setattr(index, "_collect_dat_files", lambda paths: [fake_path])
    monkeypatch.setattr(index, "_ensure_dat_file", lambda path: (1, True))
    monkeypatch.setattr(index, "_clear_dat_rows", lambda dat_id: None)
    monkeypatch.setattr(index, "_insert_rows", lambda rows: len(rows))

    cancel_event = threading.Event()

    def fake_parse(path, dat_id, *, cancel_event=None):
        for i in range(1000):
            if i == 10 and cancel_event is not None:
                cancel_event.set()
            yield DatHashRow(dat_id, None, f"rom{i}", None, "deadbeef", None, 1)
            time.sleep(0.0001)

    monkeypatch.setattr(index, "_parse_dat_file", fake_parse)

    result = index.ingest([str(fake_path)], cancel_event=cancel_event)

    assert cancel_event.is_set()
    assert result["processed"] == 0
    assert result["inserted"] < 1000
    index.close()
