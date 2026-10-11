#!/usr/bin/env bash
# FlamFetch — установка одним скриптом на любой дистрибутив Linux.
# Определяет пакетный менеджер и ставит через него; иначе — в ~/.local/bin.
set -euo pipefail

REPO="https://github.com/LOSTFlam/FlamFetch"
NAME="flamfetch"
VERSION="1.7.0"

say() { printf '\033[1;36m▸\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m✗\033[0m %s\n' "$*" >&2; exit 1; }

say "FlamFetch $VERSION — установка"

# --- зависимости: python3 + pyfiglet ---
say "проверяю Python..."
command -v python3 >/dev/null || die "нужен python3 — установи его и повтори"
python3 -c "import pyfiglet" 2>/dev/null || {
    say "ставлю pyfiglet..."
    if command -v pipx >/dev/null; then
        pipx install pyfiglet || true
    fi
    python3 -m pip install --user pyfiglet 2>/dev/null || \
    pip3 install --user pyfiglet 2>/dev/null || \
    pip install --user pyfiglet 2>/dev/null || \
    die "не смог поставить pyfiglet — поставь вручную: pip install pyfiglet"
}

# --- способ установки по пакетному менеджеру ---
if command -v pacman >/dev/null; then
    say "обнаружен pacman (Arch/Omarchy/Manjaro) — ставлю из GitHub-репозитория"
    TMP=$(mktemp -d)
    curl -fsSL "$REPO/releases/latest/download/$NAME-$VERSION-1-any.pkg.tar.zst" -o "$TMP/pkg.zst" 2>/dev/null && \
        sudo pacman -U --noconfirm "$TMP/pkg.zst" && { say "готово через pacman ✓"; exit 0; }
    say "не вышло через репозиторий — пробую AUR"
    if command -v yay >/dev/null; then
        yay -S --noconfirm $NAME && { say "готово через AUR ✓"; exit 0; }
    fi
elif command -v apt >/dev/null || command -v apt-get >/dev/null; then
    say "обнаружен apt (Debian/Ubuntu) — качаю .deb"
    TMP=$(mktemp -d)
    curl -fsSL "$REPO/releases/latest/download/${NAME}_${VERSION}_all.deb" -o "$TMP/pkg.deb" && \
        sudo dpkg -i "$TMP/pkg.deb" || sudo apt install -f -y && { say "готово через dpkg ✓"; exit 0; }
elif command -v dnf >/dev/null; then
    say "обнаружен dnf (Fedora/RHEL)"
    TMP=$(mktemp -d)
    curl -fsSL "$REPO/releases/latest/download/$NAME-$VERSION-1.noarch.rpm" -o "$TMP/pkg.rpm" && \
        sudo dnf install -y "$TMP/pkg.rpm" && { say "готово через dnf ✓"; exit 0; }
elif command -v xbps-install >/dev/null; then
    say "обнаружен xbps (Void)"
    TMP=$(mktemp -d)
    curl -fsSL "$REPO/releases/latest/download/$NAME-$VERSION-1.x86_64.xbps" -o "$TMP/pkg.xbps" && \
        sudo xbps-install -y "$TMP/pkg.xbps" && { say "готово через xbps ✓"; exit 0; }
fi

# --- универсальный путь: ~/.local ---
say "ставлю в ~/.local/bin (универсально)"
mkdir -p "$HOME/.local/bin" "$HOME/.local/share/$NAME"
curl -fsSL "$REPO/raw/master/flamfetch/flamfetch.py" -o "$HOME/.local/share/$NAME/$NAME.py"
cat > "$HOME/.local/bin/$NAME" <<'WRAP'
#!/usr/bin/env bash
# FlamFetch — обёртка: находит Python с pyfiglet
SCRIPT="$HOME/.local/share/flamfetch/flamfetch.py"
for PY in "$HOME/.venvs/ascii/bin/python" "$(command -v python3)" "$(command -v python)"; do
    if [ -n "$PY" ] && [ -x "$PY" ] && "$PY" -c "import pyfiglet" 2>/dev/null; then
        exec "$PY" "$SCRIPT" "$@"
    fi
done
echo "FlamFetch: не найден Python с pyfiglet. Установи: pip install pyfiglet" >&2
exit 1
WRAP
chmod +x "$HOME/.local/bin/$NAME"

case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) say "добавь ~/.local/bin в PATH, если ещё не:"; say '  echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> ~/.bashrc' ;;
esac

say "готово ✓ — запускай: $NAME"
