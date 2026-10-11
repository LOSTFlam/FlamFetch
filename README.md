# FlamFetch 🔥

**Огненный системный фетч с живой анимацией и персональным цветом каждого пункта.**

Вдохновлён `fastfetch` и `neofetch`, но с душой: огненный логотип Flam/quency
пульсирует пламенем, рассыпается искрами, а `quency` глитчит цифровым дождём.
Справа — вся системная информация: **каждый пункт в своём цвете**, разбитая по
6 разделам. В анимированном режиме инфоблок оживает — печатающая машинка,
shimmer, растущие бары, scanning-полоса и цифровые глитчи.

Animated system fetch with live flame and glitch effects.

---

## 🇷🇺 По-русски

### Что это

`flamfetch` — системный фетч, который показывает:

- **Слева** — анимированный логотип **Flam/quency**:
  - `Flam` — живое пламя: жар-волны, свечение, искры с дымовыми трейлами
  - `quency` — цифровой глитч: блочные сдвиги, RGB split, scanlines,
    глитч-глифы, цифровой дождь из `0` и `1`
- **Справа** — 6 цветных разделов, и у **каждого пункта свой цвет**
  (стабильный по имени — `Kernel` всегда одного цвета, `Battery` — другого):
  - ◈ **Система** — ОС (+иконка дистрибутива), хост, ядро, аптайм (+бар),
    плата, BIOS, локаль, init, архитектура
  - ◈ **Оборудование** — CPU, governor, GPU, iGPU, драйвер NVIDIA,
    температура CPU/GPU, дисплей (+монитор), DE, терминал, оболочка (+версия),
    кем запущен
  - ◈ **Ресурсы** — память, swap, диск (/, /home если отдельный), батарея,
    пакеты, load average, процессы (всё с барами)
  - ◈ **Сеть** — интерфейсы, VPN (со страной), внешний IP, спидтест
  - ◈ **Тема** — GTK-тема, иконки, шрифт, курсор
  - ◈ **Сборка** — ID/версия/билд ОС

### Анимация инфоблока

В режиме `--animate` информация оживает:

- **Печатающая машинка** — строки появляются каскадом, символ за символом,
  с курсором `▌`
- **Shimmer** — каждый ключ мягко пульсирует яркостью
- **Растущие бары** — заполняются от 0 до реального значения
- **Огненные заголовки** — по разделу бежит огненный градиент
- **Scanning-полоса** — световая полоса медленно идёт вниз по инфоблоку
- **Цифровые глитчи** — случайные значения кратко рассыпаются глитч-глифами

### Установка

```bash
# Через репозиторий GitHub (pacman)
# Добавь в /etc/pacman.conf:
#   [flamfetch]
#   Server = https://lostflam.github.io/FlamFetch/repo/$arch
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
flamfetch --version        # версия
flamfetch --help           # помощь
```

### Зависимости

- Python 3.8+
- `pyfiglet` (`pip install pyfiglet`)
- Опционально: `hyprctl` (разрешение, версия WM), `gsettings` (тема),
  `nvidia-smi` (драйвер/температура GPU), `curl` (спидтест/гео),
  `lspci` (GPU), `sensors` (температуры)

---

## 🇬🇧 In English

### What it is

`flamfetch` is a system information fetch tool inspired by `fastfetch` and
`neofetch`, but with a soul: the Flam/quency logo pulses with flame, sheds
sparks, and `quency` glitches with digital rain. On the right — all your
system info in **6 colored sections, with every item in its own color**
(stable per name). In animated mode the info block comes alive: typewriter
reveal, shimmer, growing bars, fire-gradient headers, a scanning line and
digital glitches.

### Install

```bash
# Via GitHub repo (pacman)
# Add to /etc/pacman.conf:
#   [flamfetch]
#   Server = https://lostflam.github.io/FlamFetch/repo/$arch
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
flamfetch --version        # version
flamfetch --help           # help
```

### Dependencies

- Python 3.8+
- `pyfiglet` (`pip install pyfiglet`)
- Optional: `hyprctl` (resolution, WM version), `gsettings` (theme),
  `nvidia-smi` (GPU driver/temp), `curl` (speedtest/geo), `lspci` (GPU),
  `sensors` (temperatures)

---

## Лицензия / License

[MIT](LICENSE) © 2026 lostflam
