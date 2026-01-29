# ROM-Sorter-Pro (MVP GUI)

MVP‑fokussiertes ROM‑Sortier‑Tool mit stabiler GUI (Qt bevorzugt, Tk als Fallback).

## 🚀 Schnellstart

- **GUI starten**: `python start_rom_sorter.py --gui`
  - Backend wählen: `--backend qt` oder `--backend tk`
  - Kurzformen: `--qt` / `--tk`
  - Env‑Override: `ROM_SORTER_GUI_BACKEND=qt|tk`
  - Smoke‑Check ohne UI‑Start: `python start_rom_sorter.py --gui-smoke`
- **Installation**: `python install_dependencies.py`

GUI‑Abhängigkeiten (Qt bevorzugt):

```
pip install -r requirements-gui.txt
```

## ✅ MVP‑Status (Kurzfassung)

- **GUI‑Start stabil** (Qt/Tk)
- **Scan → Preview Sort (Dry‑run) → Execute Sort**
- **Filter** (im Arbeitsbereich): Sprache, Version, Region, Extension, Größe (MB), Dedupe, Hide Unknown
- **DAT‑Matching** mit Cache und Auto‑Load‑Toggle
- **External Tools**: wud2app / wudcompress (konfigurierbar)

Details: [docs/MVP_DOCS.md](docs/MVP_DOCS.md)

## 🧩 Legacy/Optional UI-Assets

- Der Ordner [src/ui/qt/](src/ui/qt/) enthält optionale Qt-Assets (Layouts/Themes/Shell).
- Diese Imports sind **guarded** (optional) und dürfen den GUI-Start nicht crashen.
- Entfernen nur, wenn die zugehörigen optionalen Imports in [src/ui/mvp/qt_app.py](src/ui/mvp/qt_app.py) ebenfalls entfernt werden.

## 🤝 Contributing / Help
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## 📁 Projektstruktur (bereinigt)

```
rom-sorter-pro/
├── src/                 # Produktivcode (MVP)
├── dev/tests/           # MVP‑Tests
├── _archive/            # Archivierte Legacy‑/Dev‑/Runtime‑Dateien
├── start_rom_sorter.py  # Entry‑Point (GUI)
├── requirements-*.txt
├── install_dependencies.py
└── README.md
```

## 🧪 Tests

Empfohlene MVP‑Tests:

- `dev/tests/test_mvp_backend_selection.py`
- `dev/tests/test_mvp_controller_planning.py`
- `dev/tests/test_mvp_execute_cancel.py`
- `dev/tests/test_mvp_execute_cancel_mid_copy.py`
- `dev/tests/test_mvp_security_paths.py`
- `dev/tests/test_mvp_lang_version_parsing.py`
- `dev/tests/test_mvp_igir_gates.py`
- `dev/tests/test_mvp_identify_rules.py`
- `dev/tests/test_mvp_dat_index.py`

## 📄 Lizenz

MIT‑Lizenz (siehe LICENSE).
