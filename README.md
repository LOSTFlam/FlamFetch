# FlamFetch 🔥

**Огненный системный фетч с живой анимацией.**

Вдохновлён `fastfetch` и `neofetch`, но с душой: огненный логотип Flam/quency
пульсирует пламенем, рассыпается искрами, а `quency` глитчит цифровым дождём.
Справа — вся системная информация, разбитая по цветным разделам.

Animated system fetch with live flame and glitch effects.

---

## 🇷🇺 По-русски

### Что это

`flamfetch` — системный фетч, который показывает:

- **Слева** — анимированный логотип **Flam/quency**:
  - `Flam` — живое пламя: жар-волны, свечение, искры с дымовыми трейлами
  - `quency` — цифровой глитч: блочные сдвиги, RGB split, scanlines,
    глитч-глифы, цифровой дождь из `0` и `1`
- **Справа** — 5 цветных разделов:
  - ◈ **Система** — ОС (+иконка дистрибутива), хост, ядро, аптайм (+бар)
  - ◈ **Оборудование** — CPU, GPU, GPU2, DE, терминал, оболочка, разрешение, температура
  - ◈ **Ресурсы** — память, диск, swap, батарея, load average, процессы (все с барами)
  - ◈ **Сеть** — интерфейсы, VPN (со страной), внешний IP, спидтест
  - ◈ **Сборка** — ID/версия/билд ОС

### Установка

```bash
# Через репозиторий GitHub (pacman)
# Добавь в /etc/pacman.conf:
#   [flamfetch]
#   Server = https://lostflam.github.io/FlamFetch/$arch
sudo pacman -Sy flamfetch

# AUR (пока недоступен — регистрация закрыта)
# yay -S flamfetch

# Вручную
git clone https://github.com/LOSTFlam/FlamFetch
cd FlamFetch
sudo install -Dm755 flamfetch/flamfetch.py /usr/bin/flamfetch
pip install pyfiglet
```

### Использование

```bash
flamfetch                  # обычный фетч (статичный логотип)
flamfetch --animate        # с живой анимацией (Ctrl+C — выход)
flamfetch -a --intro 4     # проиграть 4 сек и выйти
flamfetch --speed          # + быстрый спидтест (~2-8 сек)
flamfetch --no-logo        # только системная информация
flamfetch --help           # помощь
```

### Зависимости

- Python 3.8+
- `pyfiglet` (`pip install pyfiglet`)
- Опционально: `hyprctl` (разрешение), `curl` (спидтест/гео), `lspci` (GPU)

---

## 🇬🇧 In English

### What it is

`flamfetch` is a system information fetch tool inspired by `fastfetch` and
`neofetch`, but with a soul: the Flam/quency logo pulses with flame, sheds
sparks, and `quency` glitches with digital rain. All your system info is
shown on the right, split into 5 colored sections (System / Hardware /
Resources / Network / Build).

### Install

```bash
# Via GitHub repo (pacman)
# Add to /etc/pacman.conf:
#   [flamfetch]
#   Server = https://lostflam.github.io/FlamFetch/$arch
sudo pacman -Sy flamfetch

# Manual
git clone https://github.com/LOSTFlam/FlamFetch
cd FlamFetch
sudo install -Dm755 flamfetch/flamfetch.py /usr/bin/flamfetch
pip install pyfiglet
```

### Usage

```bash
flamfetch                  # standard fetch (static logo)
flamfetch --animate        # live animation (Ctrl+C to exit)
flamfetch -a --intro 4     # play for 4 seconds and exit
flamfetch --speed          # add quick speedtest (~2-8 sec)
flamfetch --no-logo        # system info only
flamfetch --help           # help
```

### Dependencies

- Python 3.8+
- `pyfiglet` (`pip install pyfiglet`)
- Optional: `hyprctl` (resolution), `curl` (speedtest/geo), `lspci` (GPU)

---

## Лицензия / License

[MIT](LICENSE) © 2026 lostflam
