# Issue Backlog (Roadmap & Epics)

Diese Roadmap wird über Manifest + Scripts gepflegt:
- Manifest: [issues/epics.json](../issues/epics.json)
- Scripts: [scripts/issues](../scripts/issues/)

## Ablauf (GitHub CLI)

### PowerShell (Windows)
1) Labels erstellen/aktualisieren:
- `powershell -ExecutionPolicy Bypass -File scripts/issues/create_labels.ps1`

2) Milestones anlegen:
- `powershell -ExecutionPolicy Bypass -File scripts/issues/create_milestones.ps1`

3) Project v2 anlegen + Felder:
- `powershell -ExecutionPolicy Bypass -File scripts/issues/create_project.ps1`

4) Epics anlegen:
- `powershell -ExecutionPolicy Bypass -File scripts/issues/create_epics.ps1`

5) Epics zum Project hinzufügen + Felder setzen:
- `powershell -ExecutionPolicy Bypass -File scripts/issues/add_epics_to_project.ps1`

### Bash (Linux/macOS)
1) Labels erstellen/aktualisieren:
- `pwsh scripts/issues/create_labels.ps1`

2) Milestones anlegen:
- `pwsh scripts/issues/create_milestones.ps1`

3) Project v2 anlegen + Felder:
- `pwsh scripts/issues/create_project.ps1`

4) Epics anlegen:
- `pwsh scripts/issues/create_epics.ps1`

5) Epics zum Project hinzufügen + Felder setzen:
- `pwsh scripts/issues/add_epics_to_project.ps1`

## Hinweise
- Falls `gh auth login` fehlt, erst authentifizieren.
- Repo-Override in [issues/epics.json](../issues/epics.json) setzen (`repo`).
- Project-Felder/IDs werden im Script erzeugt oder bei Bedarf manuell ergänzt.
