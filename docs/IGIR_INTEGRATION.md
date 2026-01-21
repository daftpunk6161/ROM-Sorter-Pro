# IGIR Integration (Plan + Safety Diff + Execute Gate)

## Ziele
- IGIR darf rebuild/rename/copy **nur** via explizitem Execute-Button laufen
- Plan erzeugt Safety Diff (CSV/JSON Export)
- Dry-run startet **nie** IGIR

## Konfiguration
- src/tools/igir.yaml (neu)
  - enabled
  - exe_path
  - args_templates: probe, plan, execute
  - timeout_seconds
  - allowed_actions
  - enforce_dest_root=true
  - require_plan_before_execute=true
  - execute_requires_explicit_user_action=true
  - dry_run_never_runs_igir=true
  - report_dir_default: data/reports/igir/

## UI-Flow
1) **IGIR Plan**
   - erzeugt Report + Diff (Tabelle + Export)
2) **Safety Diff**
   - op, src, dst, collision, policy_action, notes
   - summary + risk flags
3) **Run IGIR Execute**
   - nur nach bestätigtem Diff

## Safety Gates
- dest_root containment
- Plan erforderlich + validiert
- Execute nur nach bestätigtem Diff
- Cancel/timeout killt Prozessbaum

## Outputs
- Logs: data/logs/igir/
- Reports: data/reports/igir/ (CSV/JSON)

## Ist-Zustand (Gap)
- external_tools.py unterstützt igir run/probe
- UI enthält IGIR Tab, aber ohne verpflichtenden Diff+Execute Gate
