# Для Fedora/RHEL/CentOS/Rocky/Alma
#
# Способ 1 — универсальный установщик:
#   curl -fsSL https://raw.githubusercontent.com/LOSTFlam/FlamFetch/master/install.sh | bash
#
# Способ 2 — .rpm (из Releases):
#   curl -fsSL -o flamfetch.rpm https://github.com/LOSTFlam/FlamFetch/releases/latest/download/flamfetch-1.7.0-1.noarch.rpm
#   sudo dnf install -y ./flamfetch.rpm      # или: sudo rpm -i flamfetch.rpm
#
# Способ 3 — вручную (без root):
#   mkdir -p ~/.local/share/flamfetch
#   curl -fsSL -o ~/.local/share/flamfetch/flamfetch.py \
#     https://raw.githubusercontent.com/LOSTFlam/FlamFetch/master/flamfetch/flamfetch.py
#   pip3 install --user pyfiglet
#   # создай ~/.local/bin/flamfetch по образцу flamfetch-wrapper.sh из репозитория
