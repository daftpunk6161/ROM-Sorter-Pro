import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_dat_index_parses_xml(tmp_path):
    from src.core.dat_index import DatIndex

    dat_xml = tmp_path / "sample.dat"
    dat_xml.write_text(
        """<?xml version=\"1.0\"?>
<datfile>
  <header>
    <name>Nintendo - Nintendo Entertainment System</name>
  </header>
  <game name=\"Test Game\">
    <rom name=\"test.nes\" crc=\"1234abcd\" md5=\"0123456789abcdef0123456789abcdef\" sha1=\"0123456789abcdef0123456789abcdef01234567\" />
  </game>
</datfile>
""",
        encoding="utf-8",
    )

    index = DatIndex()
    index.load_paths([str(dat_xml)])

    match = index.lookup_game("Test Game")
    assert match is not None
    assert match.system == "NES"

    hash_match = index.lookup_hashes(crc="1234abcd")
    assert hash_match is not None
    assert hash_match.system == "NES"
