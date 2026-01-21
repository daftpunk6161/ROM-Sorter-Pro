# Contributing

## Development setup
- Python 3.11+ recommended
- Create venv and install dependencies
  - GUI: `pip install -r requirements-gui.txt`
  - Optional YAML: `pip install PyYAML`
  - Dev: `pip install pytest pytest-cov ruff`

## Project conventions
- Public UI/API boundary: import only from `src.app.api`.
- Optional dependencies must be guarded (lazy import or feature flag).
- GUI must remain responsive (no heavy IO on UI thread).
- Dry-run must do **zero writes** and run **zero external tools**.

## Tests
- MVP smoke: see [_archive/docs/BASELINE.md](_archive/docs/BASELINE.md)
- Coverage gate: 80% on `src/app`, `src/core`, `src/security`, `src/ui/mvp`

## Code style
- Ruff: `ruff check .`

## Pull requests
- Keep changes reviewable (small, focused)
- Update docs for behavior changes
