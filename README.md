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

В режиме `--animate` информация оживает. **У каждого блока — своя анимация**
из библиотеки 14 эффектов, и набор сдвигается по кругу: при каждом запуске и
каждые ~20 секунд глитч «уезжает» во второй блок, свечение — в третий, и т.д.
Внутри блока каждая строка — та же анимация, но **чуть другая**: цвет немного
темнее к низу блока, тайминг сдвинут по позиции.

### Цвета из темы оформления

FlamFetch читает палитру активной темы (`~/.config/omarchy/themes/<тема>/colors.toml`)
и строит **все цвета на её основе**: семейства блоков, рамки, значки. Каждый блок
живёт в своей гамме темы, строки внутри идут по градиенту (яркий сверху, темнее
вниз), и палитра «дышит» — сдвиг по оттенку каждые ~7 сек, но **никогда не
выходит за палитру темы**. Сменишь тему — фетч перекрасится сам.

В блоке ◈ **Тема** появились строчки `Theme` (название + режим) и `Palette` —
живой образец палитры темы цветными квадратиками.

### Рамки-оконтовки

Блок оборачивается в рамку-ОКОНТОВКУ: боковые стенки не доходят до верхней и
нижней линий — рамка как бы «обнимает» блок, не запирая его. Заголовок сидит
на верхней линии, пункты — с древовидными коннекторами `├─` / `└─`, у каждой
строки свой значок (nerd font), окрашенный в цвет строки.

Стиль рамки **один на все блоки** и меняется со временем по кругу, цвета —
из темы с дыханием оттенка:

| Стиль | Эффект |
|-------|--------|
| `solid` | спокойная рамка |
| `march` | бегущая яркость вдоль рёбер |
| `pulse` | рамка дышит разом |
| `corners` | углы вспыхивают, рёбра спокойны |
| `wave` | волна цвета едет по периметру |
| `sparkle` | редкие искры `✦` на рёбрах |
| `dashes` | прерывистая рамка |
| `glow` | мягкое дыхательное свечение |

### Библиотека анимаций пунктов

| Анимация | Эффект |
|----------|--------|
| `glitch` | цифровой глитч: символы рассыпаются глитч-глифами |
| `glow` | дыхательное свечение ключа |
| `typewriter` | классическая печать с курсором `▌` |
| `wave` | цветовая волна бежит по строке (в рамках семейства) |
| `flicker` | мерцание: строка гаснет и вспыхивает |
| `matrix` | цифровой дождь `0/1` по значению |
| `scanline` | узкая световая полоса проходит по строке |
| `sparkle` | случайные искры `✦` вспыхивают в строке |
| `colorcycle` | цвет пункта крутится по семейству блока |
| `breathe` | строка дышит яркостью |
| `fire` | огненный градиент + искры по строке |
| `drip` | капли: огненные точки стекают по символам |
| `slide` | строка выезжает слева с яркой головой |
| `rainbow` | радужный бегун по семейству блока |

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
flamfetch --animate        # с живой анимацией
flamfetch -a --intro 4     # проиграть 4 сек и выйти
flamfetch --speed          # + быстрый спидтест (~2-8 сек)
flamfetch --ping           # + пинг до 1.1.1.1
flamfetch --update-check   # проверить обновление (раз в сутки)
flamfetch --update         # обновиться до последней версии
flamfetch --no-update-check # отключить автопроверку
flamfetch --banner HELLO   # свой текст в блочном баннере
flamfetch --no-banner      # без блочного баннера (только slant-лого)
flamfetch --palette ice    # принудительная палитра (см. ниже)
flamfetch --theme-swap     # следующая палитра по кругу
flamfetch --json           # машинно-читаемый JSON
flamfetch --palette-hex    # палитра темы в #rrggbb
flamfetch --no-logo        # только системная информация
flamfetch --lang ru        # русский интерфейс
flamfetch --version        # версия
flamfetch --help           # помощь
```

### Готовые палитры (--palette)

| Палитра | Ощущение |
|---------|----------|
| `fire` | классический огонь (по умолчанию как тема) |
| `ice` | холодные синие тона |
| `forest` | зелёный лес |
| `neon` | кислотные неоновые |
| `sunset` | тёплый закат |
| `mono` | монохром (белый графит) |
| `candy` | конфетные розово-сиреневые |

`--theme-swap` перебирает их по кругу (имя текущей — в stderr).

### Блок ◈ Live

Первым блоком идёт **◈ Live** — время (обновляется каждую секунду в
режиме `--animate`) и погода из wttr.in. Всё живое — в одном месте:

```
╭──────────────── ◈ Live ─────────────────╮
·  ├─ Time         01:07:01               ⁚
·  └─ Weather      ☁️ +11°C Overcast 58%  ⁚
╰─────────────────────────────────────────╯
```

### Две колонки

Инфоблоки автоматически раскладываются в **две колонки** (слева —
Live/System/Hardware, справа — остальные): высота падает с 74 до 39
строк, огромное окно больше не нужно. Если терминал узкий — фолбэк
на одну колонку, если короткий — рендер с клипом (часть блоков ниже
экрана просто не рисуется).

### Обновления

FlamFetch **сам проверяет обновления раз в сутки** (по тегам GitHub)
и показывает строчку `Update` в блоке ◈ Сборка, когда вышла новая версия:

```
·  └─ FlamFetch    1.9.2
·  └─ Update       ↑ 1.9.3 — flamfetch --update
```

Ручное управление:

```bash
flamfetch --update-check    # проверить сейчас (игнорируя суточный кэш)
flamfetch --update          # обновиться до последней версии
flamfetch --no-update-check # отключить автопроверку (или no_update_check = true в конфиге)
```

Обновление идёт **тем же способом, каким стоял фетч**:
pacman → `pacman -Sy`, Scoop → `scoop update`, Winget → `winget upgrade`,
ручная установка → перезапись `flamfetch.py` из master.

### Управление в --animate (клавиатура)

| Клавиша | Действие |
|---------|----------|
| `q` | выйти |
| `пробел` | пауза / продолжить |
| `b` | вкл/выкл блочный баннер |
| `p` | сменить палитру (по кругу) |
| `+` / `-` | быстрее / медленнее |
| `r` | пересобрать анимации блоков (новая ротация) |

### Конфиг

Необязательный `~/.config/flamfetch/config.toml` (на Windows —
`%APPDATA%\flamfetch\config.toml`), формат `ключ = значение`:

```toml
banner_text = HELLO      # текст баннера вместо FLAMFETCH
lang = ru                # язык интерфейса
no_banner = true         # выключить баннер
```

Флаги CLI имеют приоритет над конфигом.

### Зависимости

- Python 3.8+
- `pyfiglet` (`pip install pyfiglet`)
- Опционально: `hyprctl` (разрешение, версия WM), `gsettings` (тема),
  `nvidia-smi` (драйвер/температура/VRAM), `curl` (спидтест/гео),
  `lspci` (GPU), `sensors` (температуры), `nmcli`/`iw` (Wi-Fi),
  `timedatectl` (часовой пояс)

### Установка на любой дистрибутив

```bash
# Универсальный установщик — сам определит пакетный менеджер
# (pacman/apt/dnf/xbps) или поставит в ~/.local/bin
curl -fsSL https://raw.githubusercontent.com/LOSTFlam/FlamFetch/master/install.sh | bash

# Arch/Omarchy — из репозитория (pacman.conf):
#   [flamfetch]
#   Server = https://lostflam.github.io/FlamFetch/repo/$arch
sudo pacman -Sy flamfetch

# Debian/Ubuntu (.deb), Fedora (.rpm) — см. INSTALL-DEBIAN.md / INSTALL-RPM.md
# Windows — см. ниже
```

### 🪟 Windows — установка одной кнопкой

**PowerShell → вставить одну строку → Enter.** Установщик сам сделает всё:
найдёт пакетный менеджер (winget/scoop/choco), поставит Python 3,
установит pyfiglet, скачает фетч и создаст команду `flamfetch`:

```powershell
irm https://raw.githubusercontent.com/LOSTFlam/FlamFetch/master/install.ps1 | iex
```

Что умеет установщик:

| Шаг | Действие |
|-----|----------|
| 1 | Определяет пакетный менеджер: winget → scoop → choco (если нет — подскажет) |
| 2 | Ставит Python 3, если не найден |
| 3 | Ставит pyfiglet через pip |
| 4 | Скачивает `flamfetch.py` в `%USERPROFILE%\.local\share\flamfetch\` |
| 5 | Создаёт `flamfetch.cmd` / `flamfetch.ps1` в `%USERPROFILE%\.local\bin\` и добавляет в PATH |
| 6 | Запускает фетч для проверки |

После установки откройте **новый** терминал и введите `flamfetch`.

**Альтернатива — через пакетный менеджер:**

```powershell
# Scoop
scoop install flamfetch

# Winget (когда появится в каталоге)
winget install LOSTFlam.FlamFetch
```

**Или вручную** — см. [INSTALL-WINDOWS.md](INSTALL-WINDOWS.md):
Scoop bucket, portable ZIP, ручная установка через Python.

FlamFetch определяет пакеты через `pacman`, `dpkg`, `rpm` — и подстраивает
цвета под тему **любой** ОС: Omarchy → GTK → конфиг терминала
(alacritty/kitty/foot/ghostty) → Xresources → KDE → акцент Windows →
системная палитра.

### Язык интерфейса

По умолчанию — **английский**. Русский включается флагом, переменной
окружения или системной локалью:

```bash
flamfetch --lang ru           # русский интерфейс
flamfetch --lang en           # английский (по умолчанию)
FLAMFETCH_LANG=ru flamfetch   # через переменную окружения
```

При запуске на системе с русской локалью (LANG=ru_*) язык выберется сам.

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

# Universal installer — detects your package manager
# (pacman/apt/dnf/xbps) or installs to ~/.local/bin
curl -fsSL https://raw.githubusercontent.com/LOSTFlam/FlamFetch/master/install.sh | bash

# Manual
git clone https://github.com/LOSTFlam/FlamFetch
cd FlamFetch
sudo install -Dm755 flamfetch/flamfetch.py /usr/bin/flamfetch
pip install pyfiglet
```

### 🪟 Windows — one-click install

**PowerShell → paste one line → Enter.** The installer does everything:
finds a package manager (winget/scoop/choco), installs Python 3,
installs pyfiglet, downloads the fetch and creates a `flamfetch` command:

```powershell
irm https://raw.githubusercontent.com/LOSTFlam/FlamFetch/master/install.ps1 | iex
```

| Step | What it does |
|------|--------------|
| 1 | Detects package manager: winget → scoop → choco (or guides you) |
| 2 | Installs Python 3 if not found |
| 3 | Installs pyfiglet via pip |
| 4 | Downloads `flamfetch.py` to `%USERPROFILE%\.local\share\flamfetch\` |
| 5 | Creates `flamfetch.cmd` / `flamfetch.ps1` in `%USERPROFILE%\.local\bin\` and adds it to PATH |
| 6 | Runs the fetch as a smoke test |

Open a **new** terminal afterwards and type `flamfetch`.

Alternative — via package manager:

```powershell
# Scoop
scoop install flamfetch

# Winget (once listed in the catalog)
winget install LOSTFlam.FlamFetch
```

Or manually — see [INSTALL-WINDOWS.md](INSTALL-WINDOWS.md).

### Usage

```bash
flamfetch                  # standard fetch (static logo)
flamfetch --animate        # live animation
flamfetch -a --intro 4     # play for 4 seconds and exit
flamfetch --speed          # add quick speedtest (~2-8 sec)
flamfetch --ping           # add ping to 1.1.1.1
flamfetch --banner HELLO   # custom block banner text
flamfetch --no-banner      # hide the block banner
flamfetch --json           # machine-readable JSON
flamfetch --palette-hex    # theme palette as #rrggbb
flamfetch --no-logo        # system info only
flamfetch --lang ru        # Russian interface
flamfetch --version        # version
flamfetch --help           # help
```

### Keyboard control in --animate

| Key | Action |
|-----|--------|
| `q` | quit |
| `space` | pause / resume |
| `b` | toggle the block banner |
| `+` / `-` | faster / slower |
| `r` | rebuild block animations (new rotation) |

### Config

Optional `~/.config/flamfetch/config.toml` (`%APPDATA%\flamfetch\config.toml`
on Windows), `key = value` format:

```toml
banner_text = HELLO      # banner text instead of FLAMFETCH
lang = ru                # interface language
no_banner = true         # disable the banner
```

CLI flags take priority over the config file.

### Dependencies

- Python 3.8+
- `pyfiglet` (`pip install pyfiglet`)
- Optional: `hyprctl` (resolution, WM version), `gsettings` (theme),
  `nvidia-smi` (GPU driver/temp), `curl` (speedtest/geo), `lspci` (GPU),
  `sensors` (temperatures)

---

## Лицензия / License

[MIT](LICENSE) © 2026 lostflam
