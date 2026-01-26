import json
import logging
import sys

from src.logging_config import JsonFormatter


def test_json_formatter_outputs_expected_fields():
    record = logging.LogRecord(
        name="rom_sorter.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=123,
        msg="hello",
        args=(),
        exc_info=None,
    )

    formatter = JsonFormatter()
    payload = json.loads(formatter.format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "rom_sorter.test"
    assert payload["message"] == "hello"
    assert payload["pathname"] == __file__
    assert payload["lineno"] == 123
    assert "timestamp" in payload
    assert "thread" in payload
    assert "process" in payload


def test_json_formatter_includes_exc_info():
    formatter = JsonFormatter()
    try:
        raise ValueError("boom")
    except Exception:
        record = logging.LogRecord(
            name="rom_sorter.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=55,
            msg="failed",
            args=(),
            exc_info=sys.exc_info(),
        )

    payload = json.loads(formatter.format(record))
    assert "exc_info" in payload
    assert "ValueError" in payload["exc_info"]
