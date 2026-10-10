#!/usr/bin/env bash
# FlamFetch — огненный системный фетч
# Обёртка: находит рабочий Python с pyfiglet (venv или системный).

SCRIPT="$HOME/.local/share/flamfetch/flamfetch.py"

# Список python-интерпретаторов с pyfiglet (в порядке приоритета)
PYTHONS=(
    "$HOME/.venvs/ascii/bin/python"      # локальный venv с pyfiglet
    "$(command -v python3 2>/dev/null)"  # системный (если есть pyfiglet)
    "$(command -v python 2>/dev/null)"
)

for PY in "${PYTHONS[@]}"; do
    if [ -n "$PY" ] && [ -x "$PY" ]; then
        if "$PY" -c "import pyfiglet" 2>/dev/null; then
            exec "$PY" "$SCRIPT" "$@"
        fi
    fi
done

# Ни один интерпретатор не имеет pyfiglet
echo "FlamFetch: не найден Python с pyfiglet." >&2
echo "Установи: pip install pyfiglet" >&2
exit 1
