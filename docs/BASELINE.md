# Baseline Definition of Done (DoD)

## Baseline DoD
- [ ] GUI startet mit `python start_rom_sorter.py --gui` (Windows/macOS/Linux).
- [ ] GUI bleibt responsiv: Hashing/Index/IGIR laufen im Worker.
- [ ] Scan → Preview (Dry-run) → Execute End-to-End funktioniert.
- [ ] Cancel/Stop beendet Jobs sauber, keine Partial Files.
- [ ] Dry-run: **keine Writes, keine External Tools**.
- [ ] Identifikation: **DAT/Hash-first**, Unknown statt falsch.
- [ ] Archive: ZIP Entries einzeln gehasht, Mixed-Content → Unknown.
- [ ] Security: Path-Traversal + Dest-Root-Containment überall.
- [ ] Optional Deps crashen GUI-Start nicht.
- [ ] CI: ruff + pytest + coverage gate erfolgreich.

## Start-Kommandos
- Windows: `python start_rom_sorter.py --gui`
- Linux/macOS: `python3 start_rom_sorter.py --gui`
- Windows (Module): `python -m src --gui`
- Linux/macOS (Module): `python3 -m src --gui`

## Smoke-Tests (MVP)
- `pytest -q dev/tests/test_mvp_backend_selection.py`
- `pytest -q dev/tests/test_mvp_controller_planning.py`
- `pytest -q dev/tests/test_mvp_security_paths.py`
- `pytest -q dev/tests/test_mvp_execute_cancel.py`
- `pytest -q dev/tests/test_mvp_execute_cancel_mid_copy.py`
- `pytest -q dev/tests/test_mvp_lang_version_parsing.py`

## Security Invariants
- Writes nur unter dest-root (temp/output eingeschlossen)
- Symlink-Policy explizit (default: follow=false/strict)
- Archive-Schutz: zip-slip + symlink-entries blockiert

## Mutation-Proof Minimum
1) Pfad-Containment entfernen → Security-Tests müssen rot werden
2) Heuristik erzwingt falschen Treffer bei low confidence → Detection-Tests rot
3) Dry-run führt externen Prozess aus → Execute/Dry-run-Tests rot
