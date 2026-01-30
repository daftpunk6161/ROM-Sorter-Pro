#!/usr/bin/env bash
# Quality gate script for ROM-Sorter-Pro (Linux/macOS).
# Usage: ./scripts/dev/quality_gate.sh [--full]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

FULL=false
if [[ "$1" == "--full" ]]; then
    FULL=true
fi

# Find Python
if [[ -f ".venv/bin/python" ]]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

echo ""
echo "=== Running Ruff ==="
$PYTHON -m ruff check .
echo "Ruff: OK"

echo ""
echo "=== Running Pytest ==="
$PYTHON -m pytest -q --tb=short
echo "Pytest: OK"

if $FULL; then
    echo ""
    echo "=== Running Pyright ==="
    if command -v pyright &> /dev/null; then
        pyright || echo "Pyright found issues!"
    else
        echo "Pyright not installed, skipping."
    fi

    echo ""
    echo "=== Running Bandit ==="
    $PYTHON -m bandit -c .bandit.yaml -r src -q || echo "Bandit found issues!"
fi

echo ""
echo "=== Quality Gate PASSED ==="
exit 0
