# REF-3 Backlog – MVVM/MVP Layer

**Datum:** 2026-01-30  
**Status:** Offen  
**Scope:** `src/ui/mvp/` (Qt), Controller-Integration

## Ziele
- View-Logik von Controller-Logik entkoppeln.
- Saubere State-Haltung (Scan/Plan/Execute) außerhalb der UI-Klassen.
- Testbare Logik ohne Qt/Tk Abhängigkeit.

## Backlog (Checkboxen)
- [x] ViewModel-Schnittstelle definieren (Scan/Plan/Execute State, Progress, Errors)
- [x] `QtMainWindowViewModel` anlegen (reiner State + Commands, keine Qt Imports)
- [x] `UIStateMachine`-Bindings in ViewModel kapseln
- [x] DTOs für UI-Listen (Results, Details, Queue) definieren
- [x] Mapping-Layer: Controller-Modelle → UI-DTOs
- [x] Command-Adapter: ViewModel → Controller (`run_scan`, `plan_sort`, `execute_sort`)
- [x] CancelToken-Steuerung in ViewModel zentralisieren
- [x] Ereignisbus/Signals-Adapter definieren (Qt Signals ↔ ViewModel Events)
- [x] Unit-Tests für ViewModel (kein Qt) hinzufügen
- [x] Qt-UI: Event-Wiring von `qt_app_impl.py` nach ViewModel umstellen (inkrementell)
- [x] Logging-Strategie definieren (UI Log ↔ ViewModel Log Events)
- [x] Fehlerdialoge: ViewModel Fehler → UI Dialog

## Notizen
- Refactor inkrementell, keine Mega-Umstrukturierung.
- UI-Builder bleiben bestehen; ViewModel steuert nur Zustände/Commands.
