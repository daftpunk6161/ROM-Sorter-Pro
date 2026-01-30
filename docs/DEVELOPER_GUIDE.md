# ROM-Sorter-Pro – Developer Guide

> **Zielgruppe:** Contributors

---

## 1. Architektur (Kurz)
- GUI (Qt/Tk) ruft **nur** die Facade-Schicht auf.
- Backend ist deterministisch, CancelToken wird überall durchgereicht.
- Sicherheit: Pfadvalidierung & Traversal-Schutz sind Pflicht.

Wichtige Einstiegspunkte:
- `start_rom_sorter.py`
- `src/main.py`
- `src/ui/compat.py`
- `src/app/api.py` / `src/app/controller.py`

---

## 2. GUI-Backends
- Qt (PySide6/PyQt5) bevorzugt, Tk Fallback
- Auswahl über CLI oder `ROM_SORTER_GUI_BACKEND`
- Optional imports dürfen GUI-Start nie crashen

---

## 3. Threading & Cancel
- Qt: QThread/QThreadPool + Signals
- Tk: Thread + Queue + `after()`
- CancelToken muss in Worker-Calls genutzt werden

---

## 4. Tests
Empfohlene Tests:
- `dev/tests/test_mvp_backend_selection.py`
- `dev/tests/test_mvp_controller_planning.py`
- `dev/tests/test_mvp_execute_cancel.py`

GUI-Smoke:
- `dev/tests/test_mvp_gui_render_smoke.py` (ENV: `ROM_SORTER_GUI_RENDER_SMOKE=1`)

---

## 5. Konfiguration
- `src/config.json` als Basis
- `src/config/io.py` für Load/Save
- Schema-Validation in `src/config/schema.py`

---

## 5.1 Plugins
- Plugins werden aus `plugins/` geladen (oder `ROM_SORTER_PLUGIN_PATHS`).
- Ein Plugin implementiert `register(registry)` und kann Detektoren/Converter hinzufügen.

```python
def register(registry):
	registry.register_detector("demo", lambda name, path: ("Demo", 0.95))
	registry.register_converter_rule({
		"converter_id": "demo_converter",
		"input_kinds": ["RawRom"],
		"output_extension": ".bin",
		"exe_path": "tool.exe",
		"args_template": ["{input}", "{output}"]
	})
```

---

## 5.2 Rollback (Move)
- `execute_sort()` erzeugt bei Move ein Manifest.
- Rollback via `apply_rollback()` oder CLI `--rollback`.

---

## 5.3 Backup (Lokal + OneDrive)
- Sort-Report wird nach Execute gesichert.
- OneDrive wird automatisch genutzt, wenn verfügbar.

---

## 5.4 Progress Persistence
- Resume‑Checkpoints werden alle X Sekunden geschrieben.
- Pfade in `features.progress_persistence`.

---

## 6. Code-Qualität
- Keine Dead Code
- Pylance/Bandit ernst nehmen
- Keine großen Refactors ohne Notwendigkeit

---

## 7. Release-Prozess
- Siehe [docs/RELEASE_PROCESS.md](RELEASE_PROCESS.md)
- Checkliste: [docs/RELEASE_BACKLOG_CHECKLIST.md](RELEASE_BACKLOG_CHECKLIST.md)
