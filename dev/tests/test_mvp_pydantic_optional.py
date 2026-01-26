import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_pydantic_validation_optional():
    from src.config.pydantic_models import validate_with_pydantic

    assert isinstance(validate_with_pydantic({}), bool)
