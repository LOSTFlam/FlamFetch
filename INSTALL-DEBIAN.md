# Для Debian/Ubuntu/Mint/Pop!_OS
#
# Способ 1 — универсальный установщик (сам определит пакетный менеджер):
#   curl -fsSL https://raw.githubusercontent.com/LOSTFlam/FlamFetch/master/install.sh | bash
#
# Способ 2 — напрямую .deb (из Releases):
#   curl -fsSL -o flamfetch.deb https://github.com/LOSTFlam/FlamFetch/releases/latest/download/flamfetch_1.7.0_all.deb
#   sudo dpkg -i flamfetch.deb || sudo apt install -f -y
#
# Способ 3 — вручную (без root):
#   mkdir -p ~/.local/share/flamfetch
#   curl -fsSL -o ~/.local/share/flamfetch/flamfetch.py \
#     https://raw.githubusercontent.com/LOSTFlam/FlamFetch/master/flamfetch/flamfetch.py
#   pip install --user pyfiglet
#   # создай ~/.local/bin/flamfetch по образцу flamfetch-wrapper.sh из репозитория
