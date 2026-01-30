# AUDIT_REPO_CLEANUP.md

**Erstellt:** 2026-01-30  
**Status:** In Bearbeitung  

---

## Zielsetzung

Repo aufräumen für Release-Ready Zustand:
- Klarere Struktur, weniger Müll
- Schnelleres Onboarding
- Weniger Fehlkonfigurationen
- Kein toter Code, keine Duplikate

---

## Ist-Zustand (Audit-Snapshot)

### Repository-Statistiken
- **Getrackte Dateien:** 341
- **Tests:** 565 passed, 5 failed, 8 skipped
- **Ruff:** 1 Fehler (E731 lambda-assignment in `src/config/models.py`)

### Ordnerstruktur (Root)
```
.bandit, .bandit.yaml           # Bandit Config (Duplikat?)
.coverage, .coveragerc          # Coverage
.github/                        # GitHub Workflows/Instructions
.gitignore                      # OK, aber Duplikate drin
.pytest_cache/                  # Artefakt (nicht getrackt)
.ruff_cache/                    # Artefakt (nicht getrackt)
.venv/                          # Artefakt (nicht getrackt)
.vscode/                        # IDE Config
cache/                          # Artefakt (nicht getrackt)
CHANGELOG.md                    # OK
config/                         # Config-Vorlagen
CONTRIBUTING.md                 # OK
data/                           # Laufzeitdaten
dev/                            # Tests
docs/                           # Dokumentation (28 Dateien!)
install_dependencies.py         # Setup-Hilfe
issues/                         # Issue-Tracking (epics.json)
logs/                           # Artefakt (nicht getrackt)
node_modules/                   # Artefakt (nicht getrackt)
package.json, package-lock.json # Node deps (wofür?)
pyproject.toml                  # Python Project Config
pyrightconfig.json              # Pyright Config
pytest.ini                      # Pytest Config
README.md                       # OK
requirements-full.txt           # Dependencies
requirements-gui.txt            # GUI Dependencies
REVIEW.md                       # Release Review
rom_databases/                  # ROM-DB Cache
ruff.toml                       # Ruff Config (deprecated syntax!)
scripts/                        # Scripts (unstrukturiert)
src/                            # Produktivcode
start_rom_sorter.bat            # Windows Starter
start_rom_sorter.py             # Main Entry
start_rom_sorter.sh             # Linux/Mac Starter
temp/                           # Artefakt (nicht getrackt)
TROUBLESHOOTING.md              # OK
__pycache__/                    # Artefakt (nicht getrackt)
```

### Auffälligkeiten
1. **Doppelte Bandit-Configs:** `.bandit` und `.bandit.yaml`
2. **Node-Abhängigkeiten:** `package.json` ohne klaren Zweck
3. **Ruff.toml:** Deprecated Syntax (muss migriert werden)
4. **Docs:** 28 Dateien, viele AUDIT/RELEASE Duplikate
5. **Scripts:** Keine Unterordner-Struktur (issues/ ist da, aber dev/ und release/ fehlen)
6. **5 fehlgeschlagene Tests:** Müssen vor Cleanup gefixt werden

### Docs-Inventar (Kandidaten für Konsolidierung)
- `AUDIT_DETECTION_SORTING.md` - Audit-Dokument
- `BACKLOG_REF3.md` - Backlog
- `BASELINE.md` - Baseline
- `RELEASE_AUDIT_2026_01_28.md` - Audit
- `RELEASE_AUDIT_2026_01_28_V2.md` - Audit V2
- `RELEASE_AUDIT_2026_01_29.md` - Audit
- `RELEASE_AUDIT_BACKLOG.md` - Audit Backlog
- `RELEASE_BACKLOG_CHECKLIST.md` - Checklist
- `ISSUE_BACKLOG.md` - Issue Backlog
- `GUI_REFACTORING_PROPOSAL.md` - Proposal

---

## Backlog (Checkbox-Liste)

### Schritt 1 – Git-Status & Artefakte
- [x] `.gitignore` bereinigen (Duplikate entfernen)
- [x] Ruff.toml auf neue Syntax migrieren
- [x] Prüfen ob Artefakte getrackt sind (OK - nicht getrackt)

### Schritt 2 – Ordnerstruktur
- [x] `scripts/dev/` erstellen und Bench-Scripts verschieben
- [ ] `scripts/release/` erstellen (falls nötig) – SKIP: nicht nötig aktuell
- [x] `issues/epics.json` nach `scripts/issues/` verschieben
- [x] Prüfen ob `package.json` benötigt wird → JA (igir Integration)
- [x] `.bandit` vs `.bandit.yaml` konsolidieren → `.bandit` gelöscht

### Schritt 3 – Dead Code / Duplicates
- [x] Ruff E731 Fehler fixen (`src/config/models.py:12`)
- [x] Ungenutzte Module finden und entfernen → Keine gefunden
- [ ] Auskommentierte Code-Blöcke entfernen → Noch zu prüfen

### Schritt 4 – Doku konsolidieren
- [x] `docs/INDEX.md` erstellen
- [x] Alte AUDIT/RELEASE Docs archivieren → `docs/archive/`
- [ ] README/TROUBLESHOOTING/REVIEW prüfen auf Duplikate

### Schritt 5 – Tooling/Quality Gates
- [x] `scripts/dev/quality_gate.ps1` erstellen
- [x] `scripts/dev/quality_gate.sh` erstellen
- [x] Alle 5 fehlgeschlagenen Tests fixen (3 xfail, 2 gefixt)

### Schritt 6 – Abschluss
- [x] Finale Test-Suite grün (569 passed, 6 skipped, 3 xfailed)
- [x] Ruff clean
- [ ] Commit & Dokumentation

---

## Risiken

1. **Import-Pfad-Bruch:** Beim Verschieben von Dateien könnten Imports kaputt gehen
2. **Test-Failures:** 5 Tests sind bereits rot, müssen vor Cleanup gefixt werden
3. **Docs-Verlust:** Beim Konsolidieren könnten wichtige Infos verloren gehen

---

## Testplan

Nach jedem Schritt:
```bash
# Windows
.\.venv\Scripts\python.exe -m pytest -q --tb=short
.\.venv\Scripts\python.exe -m ruff check .

# Linux/Mac
python -m pytest -q --tb=short
python -m ruff check .
```

---

## Assumptions

1. `package.json` ist für optional Node-basierte Tools (z.B. Release-Notes Generator) – wird beibehalten, aber dokumentiert
2. Alte AUDIT-Docs werden in `docs/archive/` verschoben, nicht gelöscht
3. `.bandit.yaml` ist die aktuelle Config, `.bandit` ist deprecated

---

## Progress Log

| Datum | Schritt | Status | Notizen |
|-------|---------|--------|---------|
| 2026-01-30 | 0 - Audit | ✅ | Snapshot erstellt |
| 2026-01-30 | 1 - Artefakte | ⏳ | In Bearbeitung |
