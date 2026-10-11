# FlamFetch на Windows 🪟

Полностью совместимый порт: те же рамки, анимации и палитра — только данные
берутся из систем Windows (реестр, WMI через ctypes, tasklist, netsh).

## Способ 1 — Scoop (рекомендуется)

```powershell
scoop bucket add flamfetch https://github.com/LOSTFlam/FlamFetch
scoop install flamfetch
```

## Способ 2 — Winget

```powershell
winget install LOSTFlam.FlamFetch
```

## Способ 3 — вручную (Python)

Нужен Python 3.8+ ([python.org](https://python.org), отметь «Add to PATH»):

```powershell
# 1. Установить pyfiglet
pip install pyfiglet

# 2. Скачать flamfetch
mkdir "$env:USERPROFILE\.local\share\flamfetch" -Force
Invoke-WebRequest https://raw.githubusercontent.com/LOSTFlam/FlamFetch/master/flamfetch/flamfetch.py -OutFile "$env:USERPROFILE\.local\share\flamfetch\flamfetch.py"

# 3. Создать запускалку flamfetch.ps1 в PATH (например ~\.local\bin\)
# Содержимое файла:
#   python "$env:USERPROFILE\.local\share\flamfetch\flamfetch.py" @args

# 4. Запускать
flamfetch
```

## Способ 4 — portable ZIP

Скачайте `flamfetch-windows.zip` из [Releases](https://github.com/LOSTFlam/FlamFetch/releases),
распакуйте куда угодно, запускайте `flamfetch.cmd`.

## Что показывается на Windows

| Пункт | Источник |
|-------|----------|
| OS / Host / Board / BIOS | реестр (HARDWARE\DESCRIPTION\System\BIOS) |
| Kernel | NT 10.0 (build NNNNN) |
| CPU | ProcessorNameString из реестра |
| GPU | реестр (Class\{4d36e968...}) или nvidia-smi |
| VRAM / GPU Use | nvidia-smi (если есть NVIDIA) |
| Memory | GlobalMemoryStatusEx |
| Swap (pagefile) | GlobalMemoryStatusEx (pagefile) |
| Battery | GetSystemPowerStatus |
| Load | GetSystemTimes → % CPU |
| Processes | tasklist |
| Display | GetSystemMetrics |
| Terminal | WT_SESSION → Windows Terminal |
| Shell | powershell / cmd |
| WiFi | netsh wlan show interfaces |
| Theme / Palette | акцент из реестра DWM + режим темы |
| Locale | системная локаль |
| Timezone | tzname |

## Цвета

FlamFetch читает акцентный цвет Windows из реестра (DWM → AccentColor)
и строит всю палитру на его основе: семейства блоков, рамки, значки.
Режим dark/light определяется по `AppsUseLightTheme`. Если акцент недоступен —
берётся стандартная палитра xterm.

## Язык

По умолчанию английский. Для русского:

```powershell
flamfetch --lang ru
# или постояно:
$env:FLAMFETCH_LANG = "ru"
```

## Терминал

Для лучших результатов — **Windows Terminal** (поддерживает 256 цветов,
юникод и рамки). В классической консоли цвета ограничены, но фетч работает.

## Частые проблемы

**«python не является внутренней командой»** — Python не в PATH.
Переустанови Python с галочкой «Add python.exe to PATH».

**Кривые рамки / кракозябры** — нужен шрифт с поддержкой юникода
(Consolas, Cascadia Code) и Windows Terminal. В старом cmd шрифт Lucida
Console не показывает box-drawing символы.

**«pyfiglet не найден»** — `pip install pyfiglet`.
