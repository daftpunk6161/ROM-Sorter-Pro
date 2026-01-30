from __future__ import annotations

from src.config.config_service import ConfigService


def test_config_service_roundtrip() -> None:
    seen = {}

    def loader():
        return {"ok": True}

    def saver(data):
        seen.update(data)

    service = ConfigService(loader, saver)
    assert service.load() == {"ok": True}
    service.save({"saved": 1})
    assert seen == {"saved": 1}
