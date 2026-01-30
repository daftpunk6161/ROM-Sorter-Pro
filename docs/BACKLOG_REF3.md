# REF-3 Backlog – MVVM/MVP Layer

**Datum:** 2026-01-30  
**Status:** Offen  
**Scope:** `src/ui/mvp/` (Qt), Controller-Integration

## Ziele
- View-Logik von Controller-Logik entkoppeln.
- Saubere State-Haltung (Scan/Plan/Execute) außerhalb der UI-Klassen.
- Testbare Logik ohne Qt/Tk Abhängigkeit.

## Backlog (Checkboxen)
- [ ] ViewModel-Schnittstelle definieren (Scan/Plan/Execute State, Progress, Errors)
- [ ] `QtMainWindowViewModel` anlegen (reiner State + Commands, keine Qt Imports)
- [ ] `UIStateMachine`-Bindings in ViewModel kapseln
- [ ] DTOs für UI-Listen (Results, Details, Queue) definieren
- [ ] Mapping-Layer: Controller-Modelle → UI-DTOs
- [ ] Command-Adapter: ViewModel → Controller (`run_scan`, `plan_sort`, `execute_sort`)
- [ ] CancelToken-Steuerung in ViewModel zentralisieren
- [ ] Ereignisbus/Signals-Adapter definieren (Qt Signals ↔ ViewModel Events)
- [ ] Unit-Tests für ViewModel (kein Qt) hinzufügen
- [ ] Qt-UI: Event-Wiring von `qt_app_impl.py` nach ViewModel umstellen (inkrementell)
- [ ] Logging-Strategie definieren (UI Log ↔ ViewModel Log Events)
- [ ] Fehlerdialoge: ViewModel Fehler → UI Dialog

## Notizen
- Refactor inkrementell, keine Mega-Umstrukturierung.
- UI-Builder bleiben bestehen; ViewModel steuert nur Zustände/Commands.
