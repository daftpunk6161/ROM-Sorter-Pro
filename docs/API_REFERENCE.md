# ROM-Sorter-Pro – API Reference (Controller)

> **Ziel:** Kurze Referenz der Controller/Facade APIs.

---

## Controller/Facade

Die UI ruft ausschließlich die dünne Facade-Schicht auf:

```python
from src.app.api import run_scan, plan_sort, execute_sort
```

### `run_scan(source_path, config, progress_cb, cancel_token) -> ScanResult`
- **source_path**: Quellordner
- **config**: Konfiguration (dict)
- **progress_cb**: Callback `(current, total)`
- **cancel_token**: `CancelToken`
- **Return**: `ScanResult`

### `plan_sort(scan_result, dest_path, config) -> SortPlan`
- **scan_result**: Ergebnis aus `run_scan`
- **dest_path**: Zielordner
- **config**: Konfiguration (dict)
- **Return**: `SortPlan`

### `execute_sort(sort_plan, progress_cb, cancel_token) -> SortReport`
- **sort_plan**: Plan aus `plan_sort`
- **progress_cb**: Callback `(current, total)`
- **cancel_token**: `CancelToken`
- **Return**: `SortReport`

---

## Datentypen (Kurz)

### `ScanResult`
- `items`: Liste erkannter ROMs
- `cancelled`: Abbruchstatus

### `SortPlan`
- `actions`: geplanter Aktionen
- `dest_path`: Zielpfad

### `SortReport`
- `copied`, `moved`, `errors`
- `cancelled`: Abbruchstatus

---

## CancelToken

```python
from src.app.api import CancelToken

cancel = CancelToken()
# cancel.cancel() stoppt laufende Operationen
```

---

## Hinweise
- UI darf Scanner/Sorter nicht direkt importieren.
- Controller-APIs sind deterministisch und thread-safe nutzbar.
