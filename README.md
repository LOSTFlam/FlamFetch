# FlamFetch 🔥

**Огненный системный фетч с живой анимацией.**

Вдохновлён `fastfetch` и `neofetch`, но с душой: огненный логотип Flam/quency
пульсирует пламенем, рассыпается искрами, а `quency` глитчит цифровым дождём.
Справа — вся системная информация, разбитая по цветным разделам.

Animated system fetch with live flame and glitch effects.

---

## 🇷🇺 По-русски

### Что это

`flamfetch` — это системный фетч (вывод информации о системе), который
показывает:

- **Слева** — анимированный логотип **Flam/quency**:
  - `Flam` — живое пламя: жар-волны, свечение вокруг букв, искры и угольки
    взлетают с дымовыми трейлами
  - `quency` — цифровой глитч: блочные сдвиги, хроматические призраки
    (RGB split), scanlines, глитч-глифы, цифровой дождь из `0` и `1`
- **Справа** — системная информация по разделам:
  - ◈ Система (ОС, хост, ядро, аптайм)
  - ◈ Оборудование (CPU, DE, оболочка, разрешение)
  - ◈ Ресурсы (память, диск, батарея, IP, пакеты)

### Установка

```bash
# AUR (yay/paru)
yay -S flamfetch

# pacman (из репозитория)
sudo pacman -S flamfetch

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
flamfetch --no-logo        # только системная информация
flamfetch --help           # помощь
```

### Зависимости

- Python 3.8+
- `pyfiglet` (`pip install pyfiglet`)
- Опционально: `hyprctl` (для определения разрешения экрана)

---

## 🇬🇧 In English

### What it is

`flamfetch` is a system information fetch tool inspired by `fastfetch` and
`neofetch`, but with a soul: the Flam/quency logo pulses with flame, sheds
sparks, and `quency` glitches with digital rain. All your system info is
shown on the right, split into colored sections.

### Install

```bash
# AUR
yay -S flamfetch

# pacman
sudo pacman -S flamfetch

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
flamfetch --no-logo        # system info only
flamfetch --help           # help
```

### Dependencies

- Python 3.8+
- `pyfiglet` (`pip install pyfiglet`)
- Optional: `hyprctl` (for screen resolution detection)

---

## Лицензия / License

[MIT](LICENSE) © 2026 lostflam
