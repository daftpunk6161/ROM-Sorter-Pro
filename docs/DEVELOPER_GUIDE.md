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

## 6. Code-Qualität
- Keine Dead Code
- Pylance/Bandit ernst nehmen
- Keine großen Refactors ohne Notwendigkeit

---

## 7. Release-Prozess
- Siehe [docs/RELEASE_PROCESS.md](RELEASE_PROCESS.md)
- Checkliste: [docs/RELEASE_BACKLOG_CHECKLIST.md](RELEASE_BACKLOG_CHECKLIST.md)
