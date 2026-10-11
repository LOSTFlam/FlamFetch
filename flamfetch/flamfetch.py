#!/usr/bin/env python3
"""FlamFetch — огненный системный фетч с живой анимацией.

Вдохновлён fastfetch + neofetch, но с душой:
- Слева:  анимированный логотип Flam/quency (пламя + глитч)
- Справа: системная информация, разбитая по цветным разделам
           Система / Оборудование / Ресурсы / Сеть / Тема / Сборка
- Каждый пункт имеет свой собственный цвет из палитры
- В анимированном режиме инфоблок оживает:
  печатающая машинка, shimmer каждого пункта, растущие бары,
  огненные заголовки, scanning-полоса и цифровые глитчи

Зависимости: Python 3.8+, pyfiglet. Всё остальное — stdlib.

Использование:
    flamfetch                  обычный фетч (статичный логотип)
    flamfetch --animate        фетч с живой анимацией
    flamfetch --animate --intro 4   проиграть 4 сек и выйти
    flamfetch --no-logo        только системная информация
    flamfetch --help           помощь

Версия: 1.8.1
"""

import argparse
import locale
import math
import os
import platform
import random
import shutil
import socket
import subprocess
import sys
import time
import unicodedata
import zlib
from pathlib import Path

# ============================================================ платформа
#
# FlamFetch сам понимает, где он запущен, и берёт данные из системных
# источников этой ОС: Linux (/proc, /sys), Windows (реестр, WMI через
# ctypes), macOS (sysctl, sw_vers). Всё, чего нет на платформе,
# просто не показывается — фетч не падает.

IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

# ============================================================ язык
#
# Двуязычный интерфейс. По умолчанию — английский; --lang ru включает
# русский. Все надписи (заголовки блоков, ключи, подписи, ошибки)
# прогоняются через T(). Семейства цветов привязаны к смыслу ключа,
# а не к языку, поэтому палитра одинакова в обоих режимах.

CURRENT_LANG = "en"


def T(text: str) -> str:
    """Перевод надписи на текущий язык (по умолчанию — как есть)."""
    if CURRENT_LANG == "ru" and text in RU:
        return RU[text]
    return text


RU = {
    # заголовки блоков
    "◈ System": "◈ Система",
    "◈ Hardware": "◈ Оборудование",
    "◈ Resources": "◈ Ресурсы",
    "◈ Network": "◈ Сеть",
    "◈ Theme": "◈ Тема",
    "◈ Build": "◈ Сборка",
    # ключи — Система
    "OS": "ОС",
    "Host": "Хост",
    "Kernel": "Ядро",
    "Uptime": "Аптайм",
    "Board": "Плата",
    "BIOS": "BIOS",
    "Timezone": "Пояс",
    "Locale": "Локаль",
    "Init": "Init",
    "Arch": "Арх.",
    # ключи — Оборудование
    "CPU": "Проц",
    "Governor": "Гувер.",
    "GPU": "Видео",
    "iGPU": "iGPU",
    "Driver": "Драйвер",
    "VRAM": "Видеопам.",
    "GPU Use": "Загрузка GPU",
    "CPU Temp": "Т проц",
    "GPU Temp": "Т видео",
    "Display": "Экран",
    "DE": "ОС(стол)",
    "Terminal": "Терминал",
    "Shell": "Оболочка",
    "Launched": "Запущено из",
    # ключи — Ресурсы
    "Memory": "Память",
    "Swap": "Своп",
    "Disk /": "Диск /",
    "Disk /home": "Диск /home",
    "Battery": "Батарея",
    "Health": "Здоровье",
    "Packages": "Пакеты",
    "Load": "Нагрузка",
    "Processes": "Процессы",
    # ключи — Сеть
    "Iface": "Интерфейс",
    "WiFi": "Wi-Fi",
    "VPN": "VPN",
    "Note": "Заметка",
    "WAN IP": "Внеш. IP",
    "Speed": "Скорость",
    # ключи — Тема
    "GTK": "GTK",
    "Icons": "Иконки",
    "Font": "Шрифт",
    "Cursor": "Курсор",
    "Theme": "Тема",
    "Palette": "Палитра",
    # ключи — Сборка
    "OS ID": "ID ОС",
    "Version": "Версия",
    "Build": "Сборка",
    # прочее
    "unavailable": "недоступен",
    "yes": "да",
    "no": "нет",
    # единицы времени
    "d": "д",
    "h": "ч",
    "m": "м",
    # прочие надписи значений
    "WAN IP / country — via VPN": "Внеш. IP / страна — через VPN",
    "off": "выкл",
}

try:
    import pyfiglet
except ImportError:
    print("FlamFetch requires pyfiglet:  pip install pyfiglet", file=sys.stderr)
    sys.exit(1)


# ============================================================ словарь перевода
#
# Русские эквиваленты надписей. Ключи — английские строки из интерфейса.



# Русские эквиваленты надписей. Ключи — английские строки из интерфейса.

# ============================================================ палитра огня

FIRE = [52, 88, 124, 160, 196, 202, 208, 214, 220, 226, 227, 228, 229, 230, 231, 255]


def fire_color(t: float) -> int:
    return FIRE[min(int(t * (len(FIRE) - 1)), len(FIRE) - 1)]


# ============================================================ ANSI

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
INVERSE = "\033[7m"


def fg(code: int) -> str:
    return f"\033[38;5;{code}m"


# ============================================================ цвета пунктов
#
# Каждый ключ получает СВОЙ цвет — детерминированно, по хешу имени.
# Так «Kernel» всегда одного цвета, «Battery» — другого, и т.д.

ITEM_PALETTE = [
    196, 203, 209, 215, 221, 228,      # красное → золото
    190, 154, 118, 82, 46,             # лайм → изумруд
    49, 51, 45, 39,                    # циан → синий
    99, 141, 177, 213,                 # фиолет → лаванда
    204,                               # розовый
]

SECTION_COLORS = [196, 208, 154, 51, 141, 99]   # по одному на раздел

COLOR_VALUE = 255       # белый — значения
COLOR_DIM = 245         # серый — разделители
COLOR_CURSOR = 255      # курсор печатающей машинки


def item_color(key: str) -> int:
    """Стабильный цвет пункта по его имени."""
    return ITEM_PALETTE[zlib.crc32(key.encode()) % len(ITEM_PALETTE)]


def palette_index(color: int) -> int:
    """Индекс цвета в палитре (для cycling-анимаций)."""
    try:
        return ITEM_PALETTE.index(color)
    except ValueError:
        return 0


# ============================================================ затемнение/осветление
#
# 256-цветный код → такой же оттенок, но темнее (factor<1) или ярче (>1).
# Работает с кубом 16-231 и серым 232-255.

_CUBE = [0, 95, 135, 175, 215, 255]


def _scale_cube(v: int, factor: float) -> int:
    idx = _CUBE.index(v) if v in _CUBE else round(v / 51)
    return max(0, min(5, round(idx * factor)))


def shade_color(code: int, factor: float) -> int:
    """Цвет, умноженный на яркость (0.0 — чёрный, 1.0 — как есть, >1 — ярче)."""
    if factor == 1.0 or code < 16:
        return code
    if 16 <= code < 232:
        c = code - 16
        r, g, b = c // 36, (c // 6) % 6, c % 6
        return 16 + _scale_cube(_CUBE[r], factor) * 36 \
                  + _scale_cube(_CUBE[g], factor) * 6 \
                  + _scale_cube(_CUBE[b], factor)
    if 232 <= code < 256:
        v = (code - 232) * factor
        return 232 + max(0, min(23, round(v)))
    return code


def brighten_color(code: int, factor: float) -> int:
    """Осветлить цвет (factor > 1 уводит к вершине куба/серого)."""
    return shade_color(code, factor)


# ---- плавные оттенки через настоящий RGB ----
#
# shade_color округляет к уровням куба и на тёмных цветах теряет
# вариации (88 осветлённое == 88). Эти функции интерполируют к белому
# или чёрному в RGB и мапят в ближайший 256-цвет — оттенки плавные.

def _rgb256(code: int) -> tuple[int, int, int]:
    """256-код → (r, g, b) 0..255."""
    if 16 <= code < 232:
        ci = code - 16
        return _CUBE[ci // 36], _CUBE[(ci // 6) % 6], _CUBE[ci % 6]
    if 232 <= code < 256:
        v = (code - 232) * 10
        return v, v, v
    return 0, 0, 0


def _nearest256(r: int, g: int, b: int) -> int:
    """(r, g, b) → ближайший 256-цвет (куб или серый)."""
    if abs(r - g) < 12 and abs(g - b) < 12 and abs(r - b) < 12:
        v = max(0, min(255, r))
        return 232 + max(0, min(23, round(v / 10)))
    return 16 + min(5, round(r / 51)) * 36 \
              + min(5, round(g / 51)) * 6 \
              + min(5, round(b / 51))


def shade_rgb(code: int, factor: float) -> int:
    """Оттенок через RGB: <1 — к чёрному, >1 — к белому."""
    if factor == 1.0:
        return code
    r, g, b = _rgb256(code)
    if factor < 1:
        r, g, b = r * factor, g * factor, b * factor
    else:
        t = factor - 1
        r = r + (255 - r) * t
        g = g + (255 - g) * t
        b = b + (255 - b) * t
    return _nearest256(int(r), int(g), int(b))


def _resample(pal: list[int], n: int) -> list[int]:
    """Интерполирует палитру ровно до n цветов (в RGB)."""
    if not pal:
        return []
    if len(pal) == 1:
        return [pal[0]] * n
    out = []
    for i in range(n):
        t = i / max(n - 1, 1) * (len(pal) - 1)
        a = int(t)
        b = min(a + 1, len(pal) - 1)
        f = t - a
        r1, g1, b1 = _rgb256(pal[a])
        r2, g2, b2 = _rgb256(pal[b])
        out.append(_nearest256(int(r1 + (r2 - r1) * f),
                               int(g1 + (g2 - g1) * f),
                               int(b1 + (b2 - b1) * f)))
    return out


# сколько разделов максимум показывается
_MAX_SECTIONS = 6


def palette_for_sections(n: int = _MAX_SECTIONS) -> list[int]:
    """Палитра темы, приведённая ровно к n цветам, строго от самого
    светлого к самому тёмному. Блоки и строка Palette используют её —
    так порядок палитры и порядок блоков сверху-вниз совпадают."""
    pal = get_theme_palette()
    if not pal:
        pal = sorted([196, 208, 215, 154, 51, 141, 99],
                     key=_lum, reverse=True)
    return _resample(pal, n)


# ============================================================ библиотека анимаций
#
# Каждый блок инфоблока получает свою анимацию. Набор сдвигается (ротация):
# при каждом запуске и каждые ROTATE_FRAMES кадров внутри --animate блоки
# по кругу получают анимацию соседа — глитч уезжает во второй блок,
# свечение в третий, и т.д.

ANIM_LIBRARY = [
    "glitch",        # цифровой глитч: символы рассыпаются, RGB-вспышки
    "glow",          # мягкое дыхательное свечение ключа
    "typewriter",    # классическая печать с курсором ▌
    "wave",          # цветовая волна бежит по строке
    "flicker",        # мерцание: строка иногда гаснет и вспыхивает
    "matrix",        # цифровой дождь 0/1 по значению
    "scanline",      # узкая световая полоса проходит по строке
    "sparkle",       # случайные искры ✦ вспыхивают в строке
    "colorcycle",    # цвет пункта медленно крутится по всей палитре
    "breathe",       # строка дышит яркостью
    "fire",          # огненный градиент + искры по строке
    "drip",          # капли: символы стекают вниз огненными точками
    "slide",         # строка выезжает слева с яркой головой
    "rainbow",       # радужный бегун по всей строке
]

ROTATE_FRAMES = 240      # ~20 сек при 0.08с/кадр — смена набора анимаций

# ============================================================ единый такт
#
# Все пульсации (свечение, дыхание, волны, мерцание) идут от ОДНОГО
# часового механизма: beat(frame, h) = frame × TEMPO × h. Гармоники
# кратны базовой, поэтому всё движется в унисон — ничего не «скачет»
# сама по себе. Кадр чуть спокойнее (0.09с), чтобы не рябило.

FRAME_DELAY = 0.09       # сек между кадрами (было 0.08)
TEMPO = 0.055            # базовая скорость пульсаций


def beat(frame: int, h: float = 1.0) -> float:
    """Фаза пульсации в едином темпе. h — гармоника: 0.5 (медленно),
    1.0 (базовая), 2.0 (быстро) — всё кратно, поэтому синхронно."""
    return frame * TEMPO * h


# ============================================================ тема пользователя
#
# FlamFetch работает на ЛЮБОМ дистрибутиве (Linux/macOS/BSD) и читает палитру
# откуда может: Omarchy → GTK-тема → конфиг терминала → Xresources → KDE →
# системная палитра xterm. Все цвета строятся на её основе: семейства блоков,
# рамки, значки. Палитра «дышит» — сдвиг по оттенку внутри темы, но никогда
# не выходит за её пределы, поэтому картинка всегда цельная.

HOME = Path.home()
XDG_CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", str(HOME / ".config")))
XDG_STATE = Path(os.environ.get("XDG_STATE_HOME", str(HOME / ".local" / "state")))

# стандартная палитра xterm — последний fallback
XTERM_FALLBACK = {
    "red": 167, "green": 71, "yellow": 179, "blue": 68,
    "magenta": 139, "cyan": 73, "foreground": 253, "background": 16,
    "accent": 68,
}


def _hex_colors_from_text(text: str, keys: set[str] | None = None) -> dict[str, str]:
    """Достаёт из текста пары «имя=#rrggbb» / «имя: #rrggbb» / «имя #rrggbb».
    Универсально для TOML, INI, CSS, conf."""
    out = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";", "//")):
            continue
        if "=" not in line and ":" not in line:
            continue
        for sep in ("=", ":"):
            if sep in line:
                k, v = line.split(sep, 1)
                break
        v = v.strip().strip('"').strip("'").strip(",").rstrip(";")
        if v.startswith("#") and len(v) >= 7:
            try:
                int(v[1:3], 16), int(v[3:5], 16), int(v[5:7], 16)
            except ValueError:
                continue
            name = k.strip().lower()
            if keys is None or name in keys:
                out[name] = v
    return out


def _parse_toml_colors(path: Path) -> dict[str, str]:
    """Мини-парсер colors.toml: ключ = "значение" (строки и #rrggbb)."""
    try:
        return _hex_colors_from_text(path.read_text())
    except Exception:
        return {}


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_to_256(r: int, g: int, b: int) -> int:
    """Ближайший цвет палитры xterm-256 (куб 6×6×6)."""
    # уровни куба: 0, 95, 135, 175, 215, 255
    levels = [0, 95, 135, 175, 215, 255]
    def nearest(v):
        return min(range(6), key=lambda i: abs(levels[i] - v))
    ri, gi, bi = nearest(r), nearest(g), nearest(b)
    return 16 + 36 * ri + 6 * gi + bi


def _parse_gtk_theme_name() -> str | None:
    """Имя GTK-темы из settings.ini (gsettings как fallback)."""
    for ini in (XDG_CONFIG / "gtk-3.0" / "settings.ini",
                XDG_CONFIG / "gtk-4.0" / "settings.ini"):
        if ini.exists():
            try:
                for line in ini.read_text().splitlines():
                    if line.strip().lower().startswith("gtk-theme-name"):
                        return line.split("=", 1)[1].strip()
            except Exception:
                pass
    out = _run(["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"])
    if out:
        return out.strip().strip("'")
    return None


def _parse_terminal_theme() -> dict[str, str]:
    """Цвета из конфигов терминалов: alacritty/kitty/foot/ghostty/xresources."""
    found = {}
    # --- alacritty (TOML) ---
    for p in (XDG_CONFIG / "alacritty" / "alacritty.toml",
              XDG_CONFIG / "alacritty" / "alacritty.yml",
              HOME / ".alacritty.toml"):
        if p.exists():
            try:
                found.update(_hex_colors_from_text(p.read_text()))
            except Exception:
                pass
    # --- kitty ---
    for p in (XDG_CONFIG / "kitty" / "kitty.conf", XDG_CONFIG / "kitty" / "theme.conf"):
        if p.exists():
            try:
                for line in p.read_text().splitlines():
                    parts = line.split()
                    if len(parts) >= 2 and parts[0] in (
                            "foreground", "background", "color1", "color2",
                            "color3", "color4", "color5", "color6", "color7",
                            "color8", "color9", "color10", "color11",
                            "color12", "color13", "color14", "color15"):
                        v = parts[1]
                        if v.startswith("#"):
                            found[parts[0].lower()] = v
            except Exception:
                pass
    # --- foot ---
    p = XDG_CONFIG / "foot" / "foot.ini"
    if p.exists():
        try:
            found.update(_hex_colors_from_text(p.read_text()))
        except Exception:
            pass
    # --- ghostty ---
    p = XDG_CONFIG / "ghostty" / "config"
    if p.exists():
        try:
            for line in p.read_text().splitlines():
                line = line.strip()
                if "=" in line and "palette" not in line:
                    k, v = line.split("=", 1)
                    v = v.strip()
                    if v.startswith("#"):
                        found[k.strip().lower()] = v
                elif line.startswith("palette"):
                    # palette = 0=#rrggbb;1=#rrggbb...
                    body = line.split("=", 1)[1] if "=" in line else ""
                    for item in body.split(";"):
                        if "=" in item:
                            idx, v = item.split("=", 1)
                            v = v.strip()
                            if v.startswith("#") and idx.strip().isdigit():
                                found[f"color{idx.strip()}"] = v
        except Exception:
            pass
    # --- Xresources ---
    for p in (HOME / ".Xresources", HOME / ".Xdefaults"):
        if p.exists():
            try:
                found.update(_hex_colors_from_text(p.read_text()))
            except Exception:
                pass
    return found


def _parse_kde_theme() -> dict[str, str]:
    """Цвета из kdeglobals (KDE Plasma)."""
    p = XDG_CONFIG / "kdeglobals"
    if not p.exists():
        return {}
    try:
        return _hex_colors_from_text(p.read_text())
    except Exception:
        return {}


def _normalize_terminal_colors(raw: dict[str, str]) -> dict[str, str]:
    """ANSI-номера терминалов → семантические имена (color1=red и т.д.)."""
    ansi_map = {
        "color1": "red", "color2": "green", "color3": "yellow",
        "color4": "blue", "color5": "magenta", "color6": "cyan",
        "color7": "foreground", "color8": "background",
        "color9": "bright_red", "color10": "bright_green",
        "color11": "bright_yellow", "color12": "bright_blue",
        "color13": "bright_magenta", "color14": "bright_cyan",
        "color15": "bright_foreground", "color0": "background",
        "foreground": "foreground", "background": "background",
        "accent": "accent",
    }
    out = {}
    for k, v in raw.items():
        name = ansi_map.get(k.lower())
        if name and name not in out:
            out[name] = v
    return out


def _find_theme_sources() -> list[tuple[str, Path]]:
    """Кандидаты colors.toml в порядке приоритета (Omarchy → прочее)."""
    sources = []
    # 1. живое состояние Omarchy
    live = XDG_STATE / "omarchy" / "current" / "theme" / "colors.toml"
    if live.exists():
        sources.append(("Omarchy", live))
    # 2. тема по имени из Omarchy
    name_file = XDG_CONFIG / "omarchy" / "theme.name"
    if name_file.exists():
        try:
            name = name_file.read_text().strip()
            if name:
                p = XDG_CONFIG / "omarchy" / "themes" / name / "colors.toml"
                if p.exists():
                    sources.append(("Omarchy", p))
        except Exception:
            pass
    # 3. общие места colors.toml (pywal и подобные)
    for p in (XDG_CONFIG / "colors.toml",
              XDG_STATE / "colors.toml",
              HOME / ".cache" / "wal" / "colors.toml",
              HOME / ".config" / "wal" / "colors.toml"):
        if p.exists():
            sources.append(("custom", p))
    return sources


def load_theme() -> dict:
    """Универсальная загрузка палитры: {'name', 'mode', 'colors', 'source'}.
    Пробует источники по кругу, пока не наберутся основные цвета."""
    theme = {"name": "?", "mode": "?", "colors": {}, "source": "?"}
    c = theme["colors"]

    # --- 1. colors.toml (Omarchy / pywal / custom) ---
    for src_name, path in _find_theme_sources():
        raw = _parse_toml_colors(path)
        if raw:
            theme["source"] = src_name
            theme["name"] = path.parent.name
            if "mode" in raw:
                theme["mode"] = raw["mode"]
            for k, v in raw.items():
                if not v.startswith("#") or k == "mode":
                    continue
                r, g, b = hex_to_rgb(v)
                c[k] = rgb_to_256(r, g, b)
            # ANSI-цвета (color0-15) → семантические имена
            ansi_to_semantic = {
                "color1": "red", "color2": "green", "color3": "yellow",
                "color4": "blue", "color5": "magenta", "color6": "cyan",
                "color7": "foreground", "color8": "background",
                "color9": "bright_red", "color10": "bright_green",
                "color11": "bright_yellow", "color12": "bright_blue",
                "color13": "bright_magenta", "color14": "bright_cyan",
                "color15": "bright_foreground", "color0": "background",
            }
            for num, name in ansi_to_semantic.items():
                if num in c and name not in c:
                    c[name] = c[num]
            if c:
                break

    # --- 2. GTK-тема: имя + цвета из CSS ---
    if not c:
        gtk_name = _parse_gtk_theme_name()
        if gtk_name:
            theme["source"] = "GTK"
            theme["name"] = gtk_name
            css = None
            for base in (Path("/usr/share/themes"), HOME / ".themes",
                         XDG_CONFIG / "themes"):
                for rel in ("gtk-3.0/gtk.css", "gtk-3.0/gtk-dark.css",
                            "gtk-4.0/gtk.css", "gtk-4.0/gtk-dark.css"):
                    p = base / gtk_name / rel
                    if p.exists():
                        css = p
                        break
                if css:
                    break
            if css:
                try:
                    gtk_map = {
                        "theme_bg_color": "background",
                        "theme_fg_color": "foreground",
                        "theme_selected_bg_color": "accent",
                        "success_color": "green",
                        "warning_color": "yellow",
                        "error_color": "red",
                        "theme_unfocused_selected_bg_color": "blue",
                    }
                    for line in css.read_text().splitlines():
                        line = line.strip()
                        if line.startswith("@define-color") and "#" in line:
                            body = line[len("@define-color"):].strip()
                            parts = body.split()
                            if len(parts) >= 2 and parts[1].startswith("#"):
                                name = gtk_map.get(parts[0].lower())
                                if name and name not in c:
                                    r, g, b = hex_to_rgb(parts[1])
                                    c[name] = rgb_to_256(r, g, b)
                except Exception:
                    pass
            # режим по имени темы
            low = gtk_name.lower()
            theme["mode"] = "light" if "light" in low else "dark"

    # --- 2b. Windows: акцент из реестра ---
    if not c and IS_WINDOWS:
        theme["source"] = "Windows"
        theme["name"] = f"Windows {platform.release()}"
        try:
            import winreg
            # акцентный цвет (DWM)
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\DWM") as k:
                accent = winreg.QueryValueEx(k, "AccentColor")[0]
            # формат: AABBGGRR
            a, b, g, r = ((accent >> 24) & 0xFF, (accent >> 16) & 0xFF,
                          (accent >> 8) & 0xFF, accent & 0xFF)
            c["accent"] = rgb_to_256(r, g, b)
            c["blue"] = c["accent"]
            c["red"] = rgb_to_256(min(255, r + 40), g // 2, b // 2)
        except Exception:
            pass
        # тема (светлая/тёмная)
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
                theme["mode"] = "light" if winreg.QueryValueEx(k, "AppsUseLightTheme")[0] else "dark"
        except Exception:
            theme["mode"] = "dark"

    # --- 3. терминалы ---
    if not c or len(c) < 4:
        term = _normalize_terminal_colors(_parse_terminal_theme())
        if term:
            if not c:
                theme["source"] = "terminal"
            for k, v in term.items():
                if k not in c:
                    r, g, b = hex_to_rgb(v)
                    c[k] = rgb_to_256(r, g, b)

    # --- 4. KDE ---
    if not c or len(c) < 4:
        kde = _normalize_terminal_colors(_parse_kde_theme())
        if kde:
            if not c:
                theme["source"] = "KDE"
            for k, v in kde.items():
                if k not in c:
                    r, g, b = hex_to_rgb(v)
                    c[k] = rgb_to_256(r, g, b)

    # --- 5. fallback: xterm ---
    if not c:
        theme["source"] = "xterm"
        theme["name"] = "xterm"
        c.update(XTERM_FALLBACK)

    # accent, если не нашли
    if "accent" not in c:
        c["accent"] = c.get("blue") or c.get("red") or 68
    # гарантируем базовые цвета из xterm, если тема их не дала
    for k, v in XTERM_FALLBACK.items():
        if k not in c:
            c[k] = v
    # режим: из темы, иначе по яркости фона (тёмный < 128)
    if theme["mode"] == "?":
        bg = theme["colors"].get("background", 16)
        # 256-код → яркость (грубо: куб/серый)
        if 16 <= bg < 232:
            ci = bg - 16
            r, g, b = _CUBE[ci // 36], _CUBE[(ci // 6) % 6], _CUBE[ci % 6]
            lum = 0.299 * r + 0.587 * g + 0.114 * b
        elif 232 <= bg < 256:
            lum = (bg - 232) * 10
        else:
            lum = 0
        theme["mode"] = "light" if lum > 128 else "dark"
    # имя темы: человекочитаемо (обрезаем длинные хвосты)
    name = theme["name"]
    if len(name) > 30:
        name = name[:27] + "..."
    theme["name"] = name
    # яркие варианты = обычные, если темa их не дала
    for base, bright in (("red", "bright_red"), ("green", "bright_green"),
                         ("yellow", "bright_yellow"), ("blue", "bright_blue"),
                         ("magenta", "bright_magenta"), ("cyan", "bright_cyan")):
        if bright not in c:
            c[bright] = c[base]
    return theme


_THEME_CACHE = load_theme()


def theme_colors() -> dict:
    return _THEME_CACHE["colors"]


def theme_name() -> str:
    return _THEME_CACHE["name"]


def theme_family(si: int) -> list[int]:
    """Семейство блока: один цвет палитры темы + его оттенки.

    Палитра (palette_for_sections) отсортирована от самого светлого к
    самому тёмному. Каждый раздел получает СВОЙ цвет этой палитры (в том
    же порядке, сверху-вниз), а внутри блока — градиент именно этого
    тона: оттенки ярче и темнее. Так рамка, заголовок и строки блока
    всегда одного тона, а блоки идут в порядке палитры."""
    pal = palette_for_sections(_MAX_SECTIONS)
    base = pal[si % len(pal)]
    return [
        shade_rgb(base, 1.30),      # ярче — заголовок
        shade_rgb(base, 1.12),      # светлый акцент
        base,                        # базовый тон блока
        shade_rgb(base, 0.82),       # чуть глубже
        shade_rgb(base, 0.62),       # глубокий
        shade_rgb(base, 0.42),       # самый тёмный — низ блока
    ]


def theme_ui(key: str, fallback: int) -> int:
    """UI-цвет темы (foreground/muted/accent/…) с запасным значением."""
    return theme_colors().get(key, fallback)


# ============================================================ цвет строки
#
# Цвет строки: семейство блока (из темы) + градиент по позиции
# (яркий сверху → темнее вниз) + дыхание палитры во времени.

FAMILY_SHIFT_FRAMES = 90   # ~7 сек — палитра блока сдвигается на шаг


def family_color(si: int, row_i: int, n_rows: int, frame: int) -> int:
    fam = theme_family(si)
    n = len(fam)
    pos = row_i * (n - 1) // max(n_rows - 1, 1)
    shift = (frame // FAMILY_SHIFT_FRAMES) % n
    return fam[(pos + shift) % n]


# ============================================================ значки строк
#
# У каждой строчки — свой значок (nerd font). Значок окрашивается в цвет
# строки и участвует в анимациях наравне с текстом.

KEY_ICONS = {
    "OS": "\uf303",
    "Host": "\uf015",
    "Kernel": "\uf109",
    "Uptime": "\uf017",
    "Board": "\uf2db",
    "BIOS": "\uf013",
    "Locale": "\uf0ac",
    "Init": "\uf0e7",
    "Arch": "\uf085",
    "Timezone": "\uf017",
    "CPU": "\uf4bc",
    "Governor": "\uf0e7",
    "GPU": "\uf26c",
    "iGPU": "\uf03e",
    "Driver": "\uf0ad",
    "VRAM": "\uf538",
    "GPU Use": "\uf080",
    "CPU Temp": "\uf2c9",
    "GPU Temp": "\uf2cb",
    "Display": "\uf108",
    "DE": "\uf2d0",
    "Terminal": "\uf120",
    "Shell": "\uf489",
    "Launched": "\uf04b",
    "Memory": "\uf538",
    "Swap": "\uf0a0",
    "Disk /": "\uf0a0",
    "Disk /home": "\uf015",
    "Battery": "\uf240",
    "Health": "\uf21e",
    "Packages": "\uf1c0",
    "Load": "\uf201",
    "Processes": "\uf0e0",
    "Iface": "\uf0ac",
    "WiFi": "\uf1eb",
    "VPN": "\uf084",
    "Note": "\uf05a",
    "WAN IP": "\uf0c0",
    "Speed": "\uf0e4",
    "GTK": "\uf1fc",
    "Icons": "\uf03e",
    "Font": "\uf031",
    "Cursor": "\uf245",
    "Theme": "\uf03e",
    "Palette": "\uf53f",
    "OS ID": "\uf13a",
    "Version": "\uf02c",
    "Build": "\uf1b3",
}


def key_icon(key: str) -> str:
    """Значок строки (или нейтральный, если для ключа нет своего)."""
    return KEY_ICONS.get(key, "•")


# ============================================================ ширина символов
#
# Эмодзи (⚡) и CJK занимают 2 клетки терминала, но len() считает их за 1 —
# из-за этого рамки кривились. visible_width считает по-настоящему.

def _char_width(ch: str) -> int:
    if unicodedata.combining(ch):
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def visible_width(s: str) -> int:
    return sum(_char_width(c) for c in s)


# ============================================================ рамки блоков
#
# Каждый блок оборачивается в рамку-ОКОНТОВКУ: боковые стенки не доходят
# до верхней и нижней линий — рамка как бы «обнимает» блок, не запирая его.
# Заголовок сидит на верхней линии, пункты — с древовидными коннекторами
# ├─ / └─, у каждой строки свой значок.
#
# Цвета рамки берутся из ТЕМЫ пользователя и слегка «дышат» по оттенку,
# не выходя за палитру темы. Стиль рамки один на все блоки и меняется
# со временем по кругу — картинка остаётся цельной.

# оконтовка: стенки короче линий на INSET клеток с каждой стороны
FRAME_INSET = 2

FRAME_TL, FRAME_TR = "╭", "╮"
FRAME_BL, FRAME_BR = "╰", "╯"
FRAME_H, FRAME_V = "─", "│"
TREE_MID, TREE_END = "├─ ", "└─ "

# узоры на разрывах рамки (там, где стенка не доходит до линии).
# Меняются по кругу вместе со стилями рамки — как маленькие украшения.
FRAME_BREAK_PATTERNS = [
    ("·", "⁚"),        # точки
    ("┄", "┆"),        # штрихи
    ("∴", "∵"),        # треугольники
    ("∙", "⁃"),        # ромбы/точки
    ("╌", "╎"),        # волнистые
    ("⁘", "⁙"),        # звёздочки
    ("⁖", "⁗"),        # четвёрки
]


def break_pattern(frame: int) -> tuple[str, str]:
    """(левый, правый) узор на разрывах рамки — общий, меняется по кругу."""
    return FRAME_BREAK_PATTERNS[(frame // ROTATE_FRAMES) % len(FRAME_BREAK_PATTERNS)]

FRAME_STYLES = ["solid", "march", "pulse", "corners", "wave", "sparkle",
                "dashes", "glow"]


def frame_style(frame: int) -> str:
    """Текущий стиль рамки — общий для всех блоков, меняется по кругу."""
    return FRAME_STYLES[(frame // ROTATE_FRAMES) % len(FRAME_STYLES)]


def frame_hchar(style: str, frame: int, pos: int) -> str:
    """Символ горизонтальной линии для стиля."""
    if style == "dashes":
        return "─" if (pos + frame // 4) % 4 else " "
    if style == "sparkle" and random.random() < 0.03:
        return "✦"
    return FRAME_H


def frame_vchar(style: str, frame: int, pos: int) -> str:
    """Символ вертикальной стенки для стиля."""
    if style == "dashes":
        return "│" if (pos + frame // 4) % 4 else " "
    return FRAME_V


def frame_colors(si: int, frame: int) -> tuple[int, int]:
    """(приглушённый, яркий) цвета рамки из темы, с дыханием оттенка."""
    fam = theme_family(si)
    n = len(fam)
    shift = (frame // FAMILY_SHIFT_FRAMES) % n
    bright = fam[shift % n]
    dim = fam[(shift + 3) % n]        # тот же тон темы, но глубже
    return dim, bright


def frame_cell(style: str, frame: int, kind: str, pos: int,
               fam_dim: int, fam_bright: int) -> tuple[str, int, str]:
    """Символ/цвет/атрибут клетки рамки для текущего стиля."""
    if style == "solid":
        return kind, fam_dim, ""

    if style == "march":
        # бегущая яркость вдоль рамки
        f = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(pos * 0.6 + beat(frame, 2.2)))
        return kind, shade_color(fam_dim, f), ""

    if style == "pulse":
        # вся рамка дышит разом
        f = 0.50 + 0.50 * (0.5 + 0.5 * math.sin(beat(frame, 1.3)))
        return kind, shade_color(fam_dim, f), ""

    if style == "corners":
        # углы вспыхивают, рёбра спокойны
        if kind in (FRAME_TL, FRAME_TR, FRAME_BL, FRAME_BR):
            f = 0.75 + 0.25 * math.sin(beat(frame, 3.6))
            return kind, shade_color(fam_bright, f), BOLD
        return kind, shade_color(fam_dim, 0.7), ""

    if style == "wave":
        # волна цвета едет по периметру
        f = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(pos * 0.4 - beat(frame, 1.8)))
        return kind, shade_color(fam_bright if f > 0.8 else fam_dim, f), ""

    if style == "sparkle":
        # редкие искры на рёбрах
        if random.random() < 0.02:
            return "✦", fam_bright, BOLD
        return kind, shade_color(fam_dim, 0.85), ""

    if style == "dashes":
        # прерывистая рамка
        return kind, shade_color(fam_dim, 0.8), DIM

    if style == "glow":
        # мягкое дыхательное свечение всей рамки
        f = 0.65 + 0.35 * (0.5 + 0.5 * math.sin(beat(frame, 0.9) + pos * 0.2))
        return kind, shade_color(fam_bright, f), ""

    return kind, fam_dim, ""


def _rotation_offset() -> int:
    """Счётчик запусков: каждая новая сессия стартует со сдвигом набора."""
    try:
        cache = Path(os.environ.get("XDG_CACHE_HOME",
                                    str(Path.home() / ".cache"))) / "flamfetch"
        cache.mkdir(parents=True, exist_ok=True)
        f = cache / "rotation"
        try:
            n = int((f.read_text().strip() or 0))
        except (FileNotFoundError, ValueError):
            n = 0
        f.write_text(str(n + 1))
        return n
    except Exception:
        return int(time.time()) % len(ANIM_LIBRARY)


def apply_anim(anim: str, ch: str, frame: int, phase: float, gi: int,
               base_color: int, shade: float, fam: list[int],
               prog: float) -> tuple[str, int, str]:
    """Анимация одного символа пункта → (символ, цвет, attr).
    fam — цветовое семейство блока: cycling-эффекты ходят по нему,
    поэтому блок сохраняет свою идентичность (красный остаётся красным)."""
    col = shade_color(base_color, shade)
    if ch == " ":
        return ch, col, ""
    rnd = random.random()
    nf = len(fam)

    if anim == "glitch":
        # цифровой глитч: символы рассыпаются глитч-глифами
        if rnd < 0.025 + 0.02 * math.sin(beat(frame, 1.8) + phase):
            return random.choice(GLITCH_GLYPHS), random.choice(GLITCH_COLORS), ""
        return ch, col, ""

    if anim == "glow":
        # дыхательное свечение: яркость пульсирует со своим сдвигом
        f = shade * (0.70 + 0.30 * (0.5 + 0.5 * math.sin(beat(frame, 1.6) + phase)))
        return ch, brighten_color(base_color, f), ""

    if anim == "typewriter":
        # классика: печать + редкие пропуски-паузы (по фазе)
        return ch, col, ""

    if anim == "wave":
        # цветовая волна по СЕМЕЙСТВУ блока: оттенок едет по строке
        idx = (gi // 4 + frame // 6) % nf
        return ch, shade_color(fam[idx], shade), ""

    if anim == "flicker":
        # мерцание: иногда гаснет, иногда вспыхивает белым
        if rnd < 0.06:
            return ch, col, DIM
        if rnd > 0.985:
            return ch, 255, ""
        return ch, col, ""

    if anim == "matrix":
        # цифровой дождь: символы значения превращаются в 0/1
        if rnd < 0.035:
            return random.choice("01░▒▓█"), shade_color(fam[0], 0.9), ""
        return ch, col, ""

    if anim == "scanline":
        # узкая полоса бежит по строке, подсвечивая символы
        sx = int((frame * 1.6 + phase * 30) % 200)
        if abs(gi - sx) < 1:
            return ch, 255, BOLD
        return ch, col, ""

    if anim == "sparkle":
        # искры: случайный символ вспыхивает ✦
        if rnd < 0.012:
            return "✦", fam[0], BOLD
        return ch, col, ""

    if anim == "colorcycle":
        # цвет пункта медленно крутится по семейству блока
        idx = (frame // 9) % nf
        return ch, shade_color(fam[idx], shade), ""

    if anim == "breathe":
        # строка дышит яркостью
        f = shade * (0.50 + 0.50 * (0.5 + 0.5 * math.sin(beat(frame, 0.9) + phase)))
        return ch, shade_color(base_color, f), ""

    if anim == "fire":
        # огненный градиент по семейству блока + искры
        t = (gi / 26.0 + beat(frame, 0.55) + phase * 0.1) % 1.0
        if rnd < 0.015:
            return random.choice("·'`"), fam[0], ""
        idx = min(nf - 1, int(t * nf))
        return ch, fam[idx], ""

    if anim == "drip":
        # капли: редкие символы становятся огненными точками семейства
        if rnd < 0.02:
            return random.choice("'·,"), fam[1] if nf > 1 else fam[0], ""
        return ch, col, ""

    if anim == "slide":
        # выезд слева: яркая голова на границе prog
        if abs(gi - prog) < 2 and prog > 0:
            return ch, 255, BOLD
        return ch, col, ""

    if anim == "rainbow":
        # радужный бегун по семейству блока
        idx = (gi // 2 + frame // 4) % nf
        return ch, fam[idx], BOLD if gi % 3 == 0 else ""

    return ch, col, ""


# ============================================================ арт

def get_art() -> list[str]:
    return pyfiglet.figlet_format("Flam\nquency", font="slant").rstrip("\n").split("\n")


# ============================================================ системная инфа

def _run(cmd: list[str]) -> str | None:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or None
    except Exception:
        return None


def _read(path: str) -> str | None:
    try:
        return Path(path).read_text().strip()
    except Exception:
        return None


def get_host() -> tuple[str, str]:
    # ---- Windows ----
    if IS_WINDOWS:
        import winreg
        name = None
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"HARDWARE\DESCRIPTION\System\BIOS") as k:
                vendor = winreg.QueryValueEx(k, "SystemManufacturer")[0]
                product = winreg.QueryValueEx(k, "SystemProductName")[0]
                name = f"{vendor} {product}".strip()
        except Exception:
            pass
        os_name = f"Windows {platform.release()}"
        if platform.version():
            os_name += f" (build {platform.version().split('.')[2] if len(platform.version().split('.')) > 2 else platform.version()})"
        return (name or socket.gethostname()), os_name
    # ---- macOS ----
    if IS_MACOS:
        name = _run(["sysctl", "-n", "hw.model"]) or ""
        os_name = _run(["sw_vers", "-productVersion"]) or "macOS"
        return (name or socket.gethostname()), f"macOS {os_name}"
    # ---- Linux/BSD ----
    vendor = _read("/sys/class/dmi/id/sys_vendor") or ""
    product = _read("/sys/class/dmi/id/product_name") or ""
    name = f"{vendor} {product}".strip()
    os_name = ""
    osrel = _read("/etc/os-release")
    if osrel:
        for line in osrel.splitlines():
            if line.startswith("PRETTY_NAME="):
                os_name = line.split("=", 1)[1].strip('"')
                break
    return (name or socket.gethostname()), (os_name or "Linux")


def get_kernel() -> str:
    if IS_WINDOWS:
        ver = platform.version()      # '10.0.22631.4602'
        parts = ver.split(".")
        if len(parts) >= 3:
            return f"NT {parts[0]}.{parts[1]} (build {parts[2]})"
        return f"NT {ver}"
    if IS_MACOS:
        out = _run(["uname", "-r"])
        return f"Darwin {out}" if out else "Darwin"
    return platform.release()


def get_uptime() -> str:
    secs = None
    if IS_WINDOWS:
        # GetTickCount64 — миллисекунды с загрузки системы
        try:
            import ctypes
            lib = ctypes.windll.kernel32
            secs = lib.GetTickCount64() // 1000
        except Exception:
            secs = None
    elif IS_MACOS:
        out = _run(["sysctl", "-n", "kern.boottime"])
        if out:
            import re
            m = re.search(r"sec\s*=\s*(\d+)", out)
            if m:
                secs = int(time.time()) - int(m.group(1))
    else:
        raw = _read("/proc/uptime")
        if raw:
            secs = int(float(raw.split()[0]))
    if secs is None:
        return "?"
    d, secs = divmod(secs, 86400)
    h, secs = divmod(secs, 3600)
    m, _ = divmod(secs, 60)
    parts = []
    if d:
        parts.append(f"{d}{T('d')}")
    if h:
        parts.append(f"{h}{T('h')}")
    parts.append(f"{m}{T('m')}")
    return " ".join(parts)


def get_board() -> str | None:
    if IS_WINDOWS:
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"HARDWARE\DESCRIPTION\System\BIOS") as k:
                vendor = winreg.QueryValueEx(k, "BaseBoardManufacturer")[0]
                name = winreg.QueryValueEx(k, "BaseBoardProduct")[0]
                if vendor or name:
                    return f"{vendor} {name}".strip()
        except Exception:
            pass
        return None
    if not IS_LINUX:
        return None
    vendor = _read("/sys/class/dmi/id/board_vendor")
    name = _read("/sys/class/dmi/id/board_name")
    if vendor or name:
        return f"{vendor or ''} {name or ''}".strip()
    return None


def get_bios() -> str | None:
    if IS_WINDOWS:
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"HARDWARE\DESCRIPTION\System\BIOS") as k:
                return winreg.QueryValueEx(k, "BIOSVersion")[0]
        except Exception:
            return None
    if not IS_LINUX:
        return None
    return _read("/sys/class/dmi/id/bios_version")


def get_locale() -> str:
    if IS_WINDOWS:
        try:
            import locale
            name = locale.getdefaultlocale()[0]
            return name or "?"
        except Exception:
            return "?"
    loc = os.environ.get("LC_ALL") or os.environ.get("LANG") or "?"
    return loc.split(".")[0] if loc != "?" else loc


def get_init() -> str:
    if IS_WINDOWS:
        return "Windows"
    if IS_MACOS:
        return "launchd"
    comm = _read("/proc/1/comm")
    return comm or "?"


def get_arch() -> str:
    return platform.machine()


def get_cpu() -> str:
    # ---- Windows: WMI через ctypes ----
    if IS_WINDOWS:
        try:
            import ctypes
            import ctypes.wintypes as wt
            # имя процессора из реестра (быстрее WMI)
            import winreg
            name = None
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
                name = winreg.QueryValueEx(k, "ProcessorNameString")[0]
            cores = os.cpu_count() or 0
            if name:
                name = " ".join(name.split())
                return f"{name} ({cores})"
        except Exception:
            pass
        return f"{platform.processor()} ({os.cpu_count() or 0})"
    # ---- macOS ----
    if IS_MACOS:
        name = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
        if name:
            name = " ".join(name.split())
            cores = _run(["sysctl", "-n", "hw.ncpu"]) or "?"
            return f"{name} ({cores})"
        return platform.processor() or "?"
    # ---- Linux ----
    info = _read("/proc/cpuinfo")
    if info:
        model = None
        cores = 0
        for line in info.splitlines():
            if "model name" in line and model is None:
                model = line.split(":", 1)[1].strip()
            if line.startswith("processor"):
                cores += 1
        if model:
            for junk in ("CPU", "Processor", "(R)", "(TM)", "with Radeon Graphics"):
                model = model.replace(junk, "")
            model = " ".join(model.split())
            return f"{model} ({cores})"
    return platform.processor() or "?"


def get_cpu_governor() -> str | None:
    gov = _read("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
    if gov:
        return gov
    return None


def get_memory() -> str:
    info = _read("/proc/meminfo")
    if not info:
        return "?"
    vals = {}
    for line in info.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            vals[parts[0].rstrip(":")] = int(parts[1])
    total = vals.get("MemTotal", 0) / 1024 / 1024
    avail = vals.get("MemAvailable", 0) / 1024 / 1024
    used = total - avail
    return f"{used:.1f}GiB / {total:.1f}GiB ({100 * used / total:.0f}%)"


def get_disk(path: str = "/") -> str:
    try:
        usage = shutil.disk_usage(path)
        total = usage.total / 1024 ** 3
        used = usage.used / 1024 ** 3
        return f"{used:.0f}GiB / {total:.0f}GiB ({100 * used / total:.0f}%)"
    except Exception:
        return "?"


def get_battery() -> str | None:
    if IS_WINDOWS:
        try:
            import ctypes
            class SYSTEM_POWER_STATUS(ctypes.Structure):
                _fields_ = [
                    ("ACLineStatus", ctypes.c_byte),
                    ("BatteryFlag", ctypes.c_byte),
                    ("BatteryLifePercent", ctypes.c_byte),
                    ("SystemStatusFlag", ctypes.c_byte),
                    ("BatteryLifeTime", ctypes.c_ulong),
                    ("BatteryFullLifeTime", ctypes.c_ulong),
                ]
            s = SYSTEM_POWER_STATUS()
            ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s))
            if s.BatteryLifePercent > 100:
                return None
            icon = " ⚡" if s.ACLineStatus == 1 else " 🔋"
            return f"{s.BatteryLifePercent}%{icon}"
        except Exception:
            return None
    if not IS_LINUX:
        return None
    bat = Path("/sys/class/power_supply")
    for b in bat.glob("BAT*"):
        cap = _read(str(b / "capacity"))
        status = _read(str(b / "status"))
        if cap:
            icon = ""
            if status == "Charging":
                icon = " ⚡"
            elif status == "Discharging":
                icon = " 🔋"
            return f"{cap}%{icon}"
    return None


def get_resolution() -> str | None:
    out = _run(["hyprctl", "monitors"])
    if out:
        import re
        for line in out.splitlines():
            m = re.search(r"(\d{3,4}x\d{3,4})@(\d+)", line)
            if m:
                return f"{m.group(1)}@{m.group(2)}Hz"
    # sway
    out = _run(["swaymsg", "-t", "get_outputs"])
    if out:
        import re
        m = re.search(r'"width":(\d+),"height":(\d+),"refresh":(\d+)', out)
        if m:
            return f"{m.group(1)}x{m.group(2)}@{m.group(3)}Hz"
    # xrandr (X11)
    out = _run(["xrandr"])
    if out:
        import re
        for line in out.splitlines():
            m = re.search(r"\s+(\d{3,4}x\d{3,4})\s", line)
            if m and ("*" in line or "+" in line):
                hz = re.search(r"\*\+?\s+(\d+)\.\d+\*", line)
                if hz:
                    return f"{m.group(1)}@{hz.group(1)}Hz"
                return m.group(1)
    return None


def get_monitor_name() -> str | None:
    """Имя активного монитора (eDP-1 и т.п.)."""
    out = _run(["hyprctl", "monitors"])
    if out:
        import re
        for line in out.splitlines():
            m = re.search(r"^Monitor\s+(\S+)", line)
            if m:
                return m.group(1)
    if IS_WINDOWS:
        try:
            import ctypes
            w = ctypes.windll.user32.GetSystemMetrics(0)
            h = ctypes.windll.user32.GetSystemMetrics(1)
            if w and h:
                return f"{w}x{h}"
        except Exception:
            pass
        return None
    return None


def get_de() -> str:
    """Окружение рабочего стола: Wayland/X11 композиторы и классические DE."""
    # Wayland-композиторы
    if IS_WINDOWS:
        try:
            import ctypes
            # ver == 10 → Windows 10/11 (по build)
            ver = sys.getwindowsversion()
            return f"Windows Explorer ({ver.major}.{ver.minor} build {ver.build})"
        except Exception:
            return "Windows Explorer"
    if IS_MACOS:
        return "Aqua"
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return "Hyprland (Wayland)"
    if os.environ.get("SWAYSOCK"):
        return "Sway (Wayland)"
    if os.environ.get("WAYLAND_DISPLAY"):
        # попробуем угадать по процессам
        for comp, name in (("niri", "Niri"), ("river", "River"),
                           ("wayfire", "Wayfire"), ("labwc", "Labwc"),
                           ("hyprland", "Hyprland"), ("sway", "Sway")):
            if _read(f"/proc/{os.getppid()}/comm") == comp:
                return f"{name} (Wayland)"
        return "Wayland"
    # X11
    if os.environ.get("DISPLAY"):
        de = os.environ.get("XDG_CURRENT_DESKTOP", "")
        if de:
            return f"{de} (X11)"
        for wm, name in (("i3", "i3"), ("bspwm", "bspwm"), ("openbox", "Openbox"),
                         ("awesome", "Awesome"), ("dwm", "dwm"),
                         ("xmonad", "xmonad"), ("qtile", "Qtile")):
            try:
                if Path(f"/proc/{os.getppid()}/comm").read_text().strip() == wm:
                    return f"{name} (X11)"
            except Exception:
                pass
        return "X11"
    return "TTY"


def get_wm_version() -> str | None:
    out = _run(["hyprctl", "version"])
    if out:
        import re
        m = re.search(r"Hyprland\s+([\d.]+)", out)
        if m:
            return m.group(1)
    return None


def get_shell() -> str:
    if IS_WINDOWS:
        if os.environ.get("PSModulePath"):
            return "powershell"
        return "cmd"
    sh = os.environ.get("SHELL", "")
    return Path(sh).name if sh else "?"


def get_shell_version() -> str | None:
    sh = get_shell()
    if sh == "fish":
        out = _run(["fish", "--version"])
        if out:
            return out.split()[-1] if "version" in out else out
    elif sh == "bash":
        out = _run(["bash", "--version"])
        if out:
            return out.split()[3].split("(")[0]
    elif sh == "zsh":
        out = _run(["zsh", "--version"])
        if out:
            return out.split()[1]
    return None


def get_gpu_memory() -> tuple[int, int] | None:
    """(всего, использовано) VRAM в MiB — только NVIDIA."""
    out = _run(["nvidia-smi", "--query-gpu=memory.total,memory.used",
                "--format=csv,noheader,nounits"])
    if out:
        try:
            parts = out.splitlines()[0].split(",")
            return int(parts[0].strip()), int(parts[1].strip())
        except (ValueError, IndexError):
            return None
    return None


def get_gpu_util() -> int | None:
    """Утилизация GPU в % (NVIDIA)."""
    out = _run(["nvidia-smi", "--query-gpu=utilization.gpu",
                "--format=csv,noheader,nounits"])
    if out:
        try:
            return int(out.splitlines()[0].strip())
        except ValueError:
            return None
    return None


def get_wifi_info() -> tuple[str | None, int | None]:
    """(SSID, сигнал %) активного Wi-Fi, или (None, None)."""
    ssid = None
    signal = None
    if IS_WINDOWS:
        out = _run(["netsh", "wlan", "show", "interfaces"])
        if out:
            import re
            m = re.search(r"SSID\s*:\s*(.+)", out)
            if m and "BSSID" not in m.group(1):
                ssid = m.group(1).strip()
            m = re.search(r"Signal\s*:\s*(\d+)%", out)
            if m:
                signal = int(m.group(1))
        return ssid, signal
    # nmcli — самый распространённый
    out = _run(["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL", "dev", "wifi"])
    if out:
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[0] == "yes":
                ssid = parts[1] or None
                try:
                    signal = int(parts[2])
                except ValueError:
                    pass
                break
    # iw как fallback
    if ssid is None:
        out = _run(["iw", "dev"])
        if out:
            import re
            m = re.search(r"ssid\s+(\S+)", out, re.I)
            if m:
                ssid = m.group(1)
    if signal is None:
        out = _run(["iwconfig"])
        if out:
            import re
            m = re.search(r"Signal level[=:]?\s*(-?\d+)", out)
            if m:
                signal = int(m.group(1))
    return ssid, signal


def get_timezone() -> str | None:
    if IS_WINDOWS:
        import time as _t
        try:
            # стандартное имя зоны из tzdata
            return _t.tzname[0] if _t.tzname else None
        except Exception:
            return None
    out = _run(["timedatectl", "show", "-p", "Timezone", "--value"])
    if out:
        return out.strip()
    tz = _read("/etc/timezone")
    if tz:
        return tz.strip()
    return os.environ.get("TZ")


def get_battery_health() -> float | None:
    """Здоровье батареи в % (energy_full / energy_full_design)."""
    bat = Path("/sys/class/power_supply")
    for b in bat.glob("BAT*"):
        full = _read(str(b / "energy_full"))
        design = _read(str(b / "energy_full_design"))
        if full and design:
            try:
                return 100 * int(full) / int(design)
            except (ValueError, ZeroDivisionError):
                return None
    return None


def get_cpu_threads() -> int:
    try:
        return os.cpu_count() or 0
    except Exception:
        return 0


def get_packages() -> str:
    """Пакеты: pacman / dpkg / rpm / apk / xbps — что найдётся."""
    counts = []
    # Arch
    out = _run(["pacman", "-Q"])
    if out:
        counts.append(f"{len(out.splitlines())} (pacman)")
    # Debian/Ubuntu
    if not counts:
        out = _run(["dpkg", "-l"])
        if out:
            n = sum(1 for l in out.splitlines()
                    if len(l) > 2 and l[:2] in ("ii", "hi"))
            if n:
                counts.append(f"{n} (dpkg)")
    # Fedora/RHEL/SUSE
    if not counts:
        out = _run(["rpm", "-qa"])
        if out:
            counts.append(f"{len(out.splitlines())} (rpm)")
    # Void
    if not counts:
        out = _run(["xbps-query", "-l"])
        if out:
            counts.append(f"{len(out.splitlines())} (xbps)")
    # Alpine
    if not counts:
        out = _run(["apk", "info"])
        if out:
            counts.append(f"{len(out.splitlines())} (apk)")
    # Windows: winget / choco / scoop
    if IS_WINDOWS:
        wc = []
        out = _run(["winget", "list"])
        if out and "Name" in out:
            n = sum(1 for l in out.splitlines() if l.strip() and "—" not in l[:5])
            if n:
                wc.append(f"{n} (winget)")
        out = _run(["choco", "list", "--local-only"])
        if out:
            n = sum(1 for l in out.splitlines() if " packages installed" not in l and l.strip())
            if n:
                wc.append(f"{n} (choco)")
        out = _run(["scoop", "list"])
        if out:
            n = sum(1 for l in out.splitlines() if l.strip() and "Installed apps" not in l)
            if n:
                wc.append(f"{n} (scoop)")
        return ", ".join(wc) or "?"
    # flatpak — всегда показываем, если есть
    out = _run(["flatpak", "list"])
    if out:
        n = len(out.splitlines())
        if n:
            counts.append(f"{n} (flatpak)")
    return ", ".join(counts) or "?"


def get_ip() -> str | None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def _wmi_gpu_windows() -> list[str]:
    """Имена видеокарт через WMI (ctypes, без внешних зависимостей)."""
    try:
        import ctypes
        import ctypes.wintypes as wt
        ole32 = ctypes.windll.ole32
        ole32.CoInitialize(None)
        # LOCALE_SYSTEM_DEFAULT = 0x400
        p_loc = ctypes.create_unicode_buffer(9)
        # CLSID_WbemLocator / IID_IWbemLocator
        clsid = ctypes.OLE.BSTR if False else None
        # упрощённо: используем COM-строки
        import uuid
        CLSID_WbemLocator = uuid.UUID("4590f811-1d3a-11d0-891f-00aa004b2e24")
        IID_IWbemLocator = uuid.UUID("dc12a687-737f-11cf-884d-00aa004b2e24")
        p_locator = ctypes.c_void_p()
        hr = ole32.CoCreateInstance(
            (ctypes.c_char * 16).from_buffer_copy(CLSID_WbemLocator.bytes_le),
            None, 4,  # CLSCTX_INPROC_SERVER... но Wbem — inproc
            (ctypes.c_char * 16).from_buffer_copy(IID_IWbemLocator.bytes_le),
            ctypes.byref(p_locator))
        if hr != 0 or not p_locator:
            return []
        # ConnectServer через vtable слишком глубоко для чистого ctypes —
        # fallback: имена из реестра (GPU class)
        import winreg
        gpus = []
        base = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as k:
                for i in range(20):
                    try:
                        sub = f"{i:04d}"
                        with winreg.OpenKey(k, sub) as sk:
                            desc = winreg.QueryValueEx(sk, "DriverDesc")[0]
                            if desc:
                                gpus.append(" ".join(desc.split()))
                    except OSError:
                        break
        except Exception:
            pass
        return gpus[:2]
    except Exception:
        return []


def get_gpu() -> list[str]:
    """Возвращает список GPU (NVIDIA + AMD и т.д.)."""
    if IS_WINDOWS:
        return _wmi_gpu_windows()
    if IS_MACOS:
        out = _run(["system_profiler", "SPDisplaysDataType"])
        gpus = []
        if out:
            import re
            for m in re.finditer(r"Chipset Model:\s*(.+)", out):
                name = m.group(1).strip()
                if name:
                    gpus.append(name)
        return gpus[:2]
    out = _run(["lspci"])
    if not out:
        return []
    gpus = []
    for line in out.splitlines():
        low = line.lower()
        if "vga" in low or "3d controller" in low or "display controller" in low:
            name = line.split(": ", 1)[-1].strip()
            for junk in ("(rev a1)", "(rev c6)", "Corporation",
                         "Advanced Micro Devices, Inc."):
                name = name.replace(junk, "")
            name = " ".join(name.split())
            name = name.replace("[AMD/ATI]", "").strip()
            if name:
                gpus.append(name)
    return gpus


def get_gpu_driver() -> str | None:
    out = _run(["nvidia-smi", "--query-gpu=driver_version",
                "--format=csv,noheader"])
    if out:
        return out.splitlines()[0].strip()
    return None


def get_temps() -> dict[str, float]:
    """Температуры CPU/GPU в °C."""
    if not IS_LINUX:
        return {}
    temps = {}
    out = _run(["sensors"])
    if out:
        for line in out.splitlines():
            if ":" in line and "°C" in line:
                parts = line.split(":")
                if len(parts) == 2:
                    label = parts[0].strip()
                    try:
                        val = float(parts[1].strip().split("°")[0].replace("+", ""))
                        temps[label] = val
                    except ValueError:
                        pass
    if not temps:
        for z in sorted(Path("/sys/class/thermal").glob("thermal_zone*")):
            t = _read(str(z / "temp"))
            typ = _read(str(z / "type")) or "temp"
            if t:
                try:
                    temps[typ] = int(t) / 1000
                except ValueError:
                    pass
    return temps


def get_cpu_temp() -> float | None:
    """Температура CPU: Tctl (AMD) / Package (Intel) / первая доступная."""
    temps = get_temps()
    for label, val in temps.items():
        low = label.lower()
        if "tctl" in low or "package" in low or "cpu" in low:
            return val
    for label, val in temps.items():
        if "k10temp" in label.lower() or "coretemp" in label.lower():
            return val
    if temps:
        return next(iter(temps.values()))
    return None


def get_gpu_temp() -> float | None:
    out = _run(["nvidia-smi", "--query-gpu=temperature.gpu",
                "--format=csv,noheader"])
    if out:
        try:
            return float(out.splitlines()[0].strip())
        except ValueError:
            return None
    return None


def get_terminal() -> str:
    """Настоящий терминал: TERM_PROGRAM → обход дерева процессов вверх."""
    if IS_WINDOWS:
        if os.environ.get("WT_SESSION"):
            return "Windows Terminal"
        if os.environ.get("TERM_PROGRAM"):
            return os.environ["TERM_PROGRAM"]
        return "conhost"
    term = os.environ.get("TERM_PROGRAM", "")
    if term:
        return term
    known = ("foot", "alacritty", "kitty", "ghostty", "wezterm-gui", "wezterm",
             "xterm", "konsole", "gnome-terminal-server", "gnome-terminal",
             "st", "urxvt", "terminator", "tilix", "ptyxis", "contour", "wave")
    try:
        pid = os.getppid()
        first_comm = _read(f"/proc/{pid}/comm")
        for _ in range(8):
            if pid <= 1:
                break
            comm = _read(f"/proc/{pid}/comm")
            cmd = (_read(f"/proc/{pid}/cmdline") or "").replace("\0", " ").strip()
            # basename первого аргумента cmdline — защита от ложных совпадений
            argv0 = os.path.basename(cmd.split()[0]) if cmd.split() else ""
            for cand in {comm or "", argv0}:
                cl = cand.lower()
                if cl in known:
                    return cl
            # kitty/ghostty иногда прячутся в аргументах вида kitty --session
            for k in ("kitty", "ghostty", "wezterm", "alacritty", "foot"):
                if k in cmd.lower().split():
                    return k
            stat = _read(f"/proc/{pid}/stat")
            if not stat:
                break
            rparen = stat.rfind(")")
            fields = stat[rparen + 2:].split()
            pid = int(fields[1])
    except Exception:
        pass
    # ничего знакомого не нашли — покажем ближайшего родителя (обёртку)
    if first_comm:
        return first_comm
    return os.environ.get("TERM", "?")


def get_distro_icon() -> str:
    """Иконка дистрибутива (nerd font)."""
    osrel = _read("/etc/os-release")
    distro = ""
    if osrel:
        for line in osrel.splitlines():
            if line.startswith("ID="):
                distro = line.split("=", 1)[1].strip('"').lower()
                break
    icons = {
        "arch": "",
        "endeavouros": "",
        "manjaro": "",
        "omarchy": "",
        "ubuntu": "",
        "debian": "",
        "fedora": "",
        "nixos": "",
        "gentoo": "",
        "void": "",
    }
    return icons.get(distro, "󰣇")


def get_theme() -> dict[str, str]:
    """GTK-тема, иконки, шрифт, курсор (или Windows: тема оформления)."""
    theme = {}
    if IS_WINDOWS:
        try:
            import winreg
            key = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
                apps = winreg.QueryValueEx(k, "AppsUseLightTheme")[0]
            theme["gtk"] = f"Windows {'light' if apps else 'dark'}"
            theme["icons"] = "fluent"
            theme["font"] = "Segoe UI"
            theme["cursor"] = "windows"
        except Exception:
            pass
        return theme
    for key, schema, setting in (
        ("gtk", "org.gnome.desktop.interface", "gtk-theme"),
        ("icons", "org.gnome.desktop.interface", "icon-theme"),
        ("font", "org.gnome.desktop.interface", "font-name"),
        ("cursor", "org.gnome.desktop.interface", "cursor-theme"),
    ):
        out = _run(["gsettings", "get", schema, setting])
        if out:
            val = out.strip().strip("'")
            if val:
                theme[key] = val
    return theme


def _lum(code: int) -> float:
    """Яркость 256-цветного кода (грубо, для сортировки)."""
    if 16 <= code < 232:
        ci = code - 16
        r, g, b = _CUBE[ci // 36], _CUBE[(ci // 6) % 6], _CUBE[ci % 6]
    elif 232 <= code < 256:
        return (code - 232) * 10
    else:
        return code
    return 0.299 * r + 0.587 * g + 0.114 * b


def get_theme_palette() -> list[int] | None:
    """Образец палитры активной темы: ключевые акценты,
    отсортированные от самого СВЕТЛОГО к самому ТЁМНОМУ."""
    c = theme_colors()
    if not c:
        return None
    out = []
    for key in ("red", "orange", "yellow", "green", "cyan",
                "blue", "magenta", "accent"):
        if key in c and c[key] not in out:
            out.append(c[key])
    out.sort(key=_lum, reverse=True)      # светлый → тёмный
    return out or None


def is_palette_value(value) -> bool:
    """Значение-палитра (список цветов) рисуется квадратиками, не текстом."""
    return isinstance(value, list)


# ---------------------------------------------------------------- прогресс-бары

BAR_FILLED = "━"      # ━
BAR_EMPTY = "─"       # ─


def bar(pct: float, width: int = 10) -> str:
    """Прогресс-бар с цветом по загрузке: зелёный/жёлтый/красный."""
    pct = max(0.0, min(100.0, pct))
    filled = int(pct / 100 * width)
    bar_str = BAR_FILLED * filled + BAR_EMPTY * (width - filled)
    if pct < 50:
        color = 78
    elif pct < 80:
        color = 220
    else:
        color = 196
    return fg(color) + bar_str + RESET


def uptime_bar(seconds: float, max_days: float = 7.0, width: int = 10) -> str:
    """Бар uptime: сколько от максимума (7 дней) отработала система."""
    pct = min(100.0, seconds / (max_days * 86400) * 100)
    filled = int(pct / 100 * width)
    if filled == 0 and pct > 0:
        filled = 1
    bar_str = BAR_FILLED * filled + BAR_EMPTY * (width - filled)
    if pct < 30:
        color = 78
    elif pct < 70:
        color = 220
    else:
        color = 196
    return fg(color) + bar_str + RESET


# ---------------------------------------------------------------- сеть

def get_interfaces() -> list[tuple[str, str, str]]:
    """Активные сетевые интерфейсы: [(имя, статус, IP), ...]"""
    if IS_WINDOWS:
        out = _run(["netsh", "interface", "show", "interface"])
        ifaces = []
        if out:
            import re
            for line in out.splitlines():
                m = re.match(r"\s*(Enabled|Connected)\s+(\S+)\s+(\S+)", line)
                if m and m.group(2).lower() != "loopback":
                    ifaces.append((m.group(2), m.group(1), ""))
        return ifaces
    if IS_MACOS:
        out = _run(["ifconfig"])
        ifaces = []
        if out:
            import re
            for m in re.finditer(r"^(\w+): flags.*?status: (\w+).*?inet (\S+)",
                                 out, re.S | re.M):
                name, status, ip = m.groups()
                if name != "lo" and status == "active":
                    ifaces.append((name, "UP", ip))
        return ifaces
    out = _run(["ip", "-brief", "addr", "show"])
    if not out:
        return []
    ifaces = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        name = parts[0]
        status = parts[1]
        ip = parts[2] if len(parts) > 2 else ""
        if name == "lo" or status not in ("UP", "UNKNOWN"):
            continue
        if status == "UNKNOWN" and not ip:
            continue
        ifaces.append((name, status, ip))
    return ifaces


def get_vpn_interfaces() -> list[str]:
    """VPN-интерфейсы (tun, wg, tap, ppp)."""
    if not IS_LINUX:
        return []
    out = _run(["ip", "-brief", "addr", "show"])
    if not out:
        return []
    vpns = []
    for line in out.splitlines():
        name = line.split()[0] if line.split() else ""
        if any(x in name.lower() for x in ("tun", "wg", "tap", "ppp", "proton", "nord")):
            vpns.append(name)
    return vpns


def get_external_info() -> dict | None:
    """Внешний IP + гео (страна, город) через ipinfo.io."""
    out = _run(["curl", "-s", "--max-time", "5", "https://ipinfo.io/json"])
    if not out:
        return None
    try:
        import json
        data = json.loads(out)
        return {
            "ip": data.get("ip", "?"),
            "country": data.get("country", "?"),
            "city": data.get("city", "?"),
            "org": data.get("org", "?"),
        }
    except Exception:
        return None


def get_speed() -> tuple[float, float] | None:
    """Быстрый спидтест: скачивает 10MB с Cloudflare, возвращает (Mbps, сек)."""
    url = "https://speed.cloudflare.com/__down?bytes=10000000"
    try:
        start = time.monotonic()
        r = subprocess.run(
            ["curl", "-s", "--max-time", "8", "-o", "/dev/null",
             "-w", "%{size_download}", url],
            capture_output=True, text=True, timeout=10,
        )
        elapsed = time.monotonic() - start
        size = int(r.stdout.strip() or 0)
        if size <= 0 or elapsed <= 0:
            return None
        mbps = (size * 8) / (elapsed * 1_000_000)
        return mbps, elapsed
    except Exception:
        return None


def get_build_info() -> dict:
    """Инфа о сборке ОС."""
    osrel = _read("/etc/os-release")
    info = {"id": "?", "version": "?", "build_id": "?"}
    if osrel:
        for line in osrel.splitlines():
            if line.startswith("ID="):
                info["id"] = line.split("=", 1)[1].strip('"')
            elif line.startswith("VERSION_ID="):
                info["version"] = line.split("=", 1)[1].strip('"')
            elif line.startswith("BUILD_ID="):
                info["build_id"] = line.split("=", 1)[1].strip('"')
    return info


def get_uptime_seconds() -> float:
    raw = _read("/proc/uptime")
    if raw:
        return float(raw.split()[0])
    return 0.0


def get_swap() -> tuple[float, float] | None:
    if IS_WINDOWS:
        try:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            m = MEMORYSTATUSEX()
            m.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            total = m.ullTotalPageFile / 1024**3
            avail = m.ullAvailPageFile / 1024**3
            used = total - avail
            if total <= 0:
                return None
            return used, total
        except Exception:
            return None
    if not IS_LINUX:
        return None
    info = _read("/proc/meminfo")
    if not info:
        return None
    vals = {}
    for line in info.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            vals[parts[0].rstrip(":")] = int(parts[1])
    total = vals.get("SwapTotal", 0) / 1024 / 1024
    free = vals.get("SwapFree", 0) / 1024 / 1024
    if total <= 0:
        return None
    used = total - free
    return used, total


def get_load() -> str:
    """Load average (1/5/15 мин) или CPU % на Windows."""
    if IS_WINDOWS:
        try:
            import ctypes, time as _t
            class FILETIME(ctypes.Structure):
                _fields_ = [("dwLowDateTime", ctypes.c_ulong),
                            ("dwHighDateTime", ctypes.c_ulong)]
            def ft2int(ft):
                return (ft.dwHighDateTime << 32) | ft.dwLowDateTime
            idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
            ctypes.windll.kernel32.GetSystemTimes(
                ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user))
            _t.sleep(0.3)
            idle2, kernel2, user2 = FILETIME(), FILETIME(), FILETIME()
            ctypes.windll.kernel32.GetSystemTimes(
                ctypes.byref(idle2), ctypes.byref(kernel2), ctypes.byref(user2))
            idle_d = ft2int(idle2) - ft2int(idle)
            total_d = (ft2int(kernel2) + ft2int(user2)) - (ft2int(kernel) + ft2int(user))
            if total_d > 0:
                load = 100 * (1 - idle_d / total_d)
                return f"{load:.0f}% CPU"
        except Exception:
            pass
        return "?"
    if IS_MACOS:
        out = _run(["sysctl", "-n", "vm.loadavg"])
        if out:
            parts = out.strip("{}\n ").split()
            if len(parts) >= 3:
                return f"{parts[0]} {parts[1]} {parts[2]}"
        return "?"
    raw = _read("/proc/loadavg")
    if not raw:
        return "?"
    parts = raw.split()
    return f"{parts[0]} {parts[1]} {parts[2]}"


def get_processes() -> int:
    if IS_WINDOWS:
        out = _run(["tasklist"])
        if out:
            return sum(1 for l in out.splitlines()
                       if l.strip() and ".exe" in l.lower())
        return 0
    if IS_MACOS:
        out = _run(["ps", "-ax"])
        if out:
            return len(out.splitlines()) - 1
        return 0
    try:
        return len([d for d in os.listdir("/proc") if d.isdigit()])
    except Exception:
        return 0


def get_parent_process() -> str:
    if IS_WINDOWS:
        try:
            import ctypes
            import ctypes.wintypes as wt
            GetCurrentProcessId = ctypes.windll.kernel32.GetCurrentProcessId
            return "explorer"  # упрощённо: процесс запущен из Explorer/cmd
        except Exception:
            return "?"
    if IS_MACOS:
        try:
            ppid = os.getppid()
            comm = _run(["ps", "-p", str(ppid), "-o", "comm="])
            if comm:
                return Path(comm.strip()).name
        except Exception:
            pass
        return "?"
    try:
        ppid = os.getppid()
        comm = _read(f"/proc/{ppid}/comm")
        return comm or "?"
    except Exception:
        return "?"


# ============================================================ разделы
#
# Пункт: (ключ, значение, процент_для_бара | None)

def _parse_mem() -> tuple[float, float, float]:
    if IS_WINDOWS:
        try:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            m = MEMORYSTATUSEX()
            m.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            total = m.ullTotalPhys / 1024**3
            used = total - m.ullAvailPhys / 1024**3
            return used, total, m.dwMemoryLoad
        except Exception:
            return 0.0, 0.0, 0.0
    if IS_MACOS:
        total = _run(["sysctl", "-n", "hw.memsize"])
        if total:
            try:
                t = int(total) / 1024**3
                vm = _run(["vm_stat"]) or ""
                free = 0.0
                for line in vm.splitlines():
                    if "Pages free" in line:
                        import re
                        mm = re.search(r"(\d+)", line)
                        if mm:
                            free = int(mm.group(1)) * 4096 / 1024**3
                used = t - free
                return used, t, 100 * used / t
            except Exception:
                return 0.0, 0.0, 0.0
        return 0.0, 0.0, 0.0
    info = _read("/proc/meminfo")
    if not info:
        return 0.0, 0.0, 0.0
    vals = {}
    for line in info.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            vals[parts[0].rstrip(":")] = int(parts[1])
    total = vals.get("MemTotal", 0) / 1024 / 1024
    avail = vals.get("MemAvailable", 0) / 1024 / 1024
    used = total - avail
    pct = 100 * used / total if total else 0.0
    return used, total, pct


def _parse_disk(path: str = "/") -> tuple[float, float, float]:
    try:
        usage = shutil.disk_usage(path)
        total = usage.total / 1024 ** 3
        used = usage.used / 1024 ** 3
        pct = 100 * used / total if total else 0.0
        return used, total, pct
    except Exception:
        return 0.0, 0.0, 0.0


def _is_separate_mount(path: str) -> bool:
    """True, если путь — отдельное УСТРОЙСТВО (btrfs-subvol того же device не считается)."""
    try:
        mounts = _read("/proc/mounts") or ""
        root_dev = None
        path_dev = None
        for line in mounts.splitlines():
            parts = line.split()
            if len(parts) < 2:
                continue
            dev, target = parts[0], parts[1]
            if target == "/":
                root_dev = dev
            if target == path:
                path_dev = dev
        if path_dev and root_dev and path_dev != root_dev:
            return True
    except Exception:
        pass
    return False


def _parse_battery() -> tuple[int, str] | None:
    if IS_WINDOWS:
        try:
            import ctypes
            class SYSTEM_POWER_STATUS(ctypes.Structure):
                _fields_ = [
                    ("ACLineStatus", ctypes.c_byte),
                    ("BatteryFlag", ctypes.c_byte),
                    ("BatteryLifePercent", ctypes.c_byte),
                    ("SystemStatusFlag", ctypes.c_byte),
                    ("BatteryLifeTime", ctypes.c_ulong),
                    ("BatteryFullLifeTime", ctypes.c_ulong),
                ]
            s = SYSTEM_POWER_STATUS()
            ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s))
            if s.BatteryLifePercent > 100:
                return None
            return s.BatteryLifePercent, ("Charging" if s.ACLineStatus == 1 else "Discharging")
        except Exception:
            return None
    if not IS_LINUX:
        return None
    for b in Path("/sys/class/power_supply").glob("BAT*"):
        cap = _read(str(b / "capacity"))
        status = _read(str(b / "status")) or ""
        if cap:
            try:
                return int(cap), status
            except ValueError:
                return None
    return None


def build_sections(with_speed: bool = False) -> list[tuple[str, list[tuple[str, str, float | None]]]]:
    """Возвращает [(заголовок, [(ключ, значение, бар%), ...]), ...]
    with_speed=True — делает спидтест (медленно, ~2-8 сек)."""
    host, os_name = get_host()
    icon = get_distro_icon()

    gpus = get_gpu()
    cpu_temp = get_cpu_temp()
    gpu_temp = get_gpu_temp()
    gpu_drv = get_gpu_driver()
    wm_ver = get_wm_version()
    gov = get_cpu_governor()
    board = get_board()
    bios = get_bios()
    mon = get_monitor_name()
    res = get_resolution()
    theme = get_theme()

    bat = _parse_battery()
    mu, mt, mpct = _parse_mem()
    du, dt, dpct = _parse_disk("/")
    hu, ht, hpct = _parse_disk("/home")
    up_sec = get_uptime_seconds()

    # ===== сеть =====
    ifaces = get_interfaces()
    vpns = get_vpn_interfaces()
    ext = get_external_info()
    speed = get_speed() if with_speed else None

    de = get_de()
    if wm_ver and "Hyprland" in de:
        de = f"{de} {wm_ver}"

    # ---------- ◈ Система ----------
    sys_items = [
        ("OS", f"{icon} {os_name}", None),
        ("Host", host, None),
        ("Kernel", get_kernel(), None),
        ("Uptime", get_uptime(), min(100.0, up_sec / (7 * 86400) * 100)),
    ]
    if board:
        sys_items.append(("Board", board, None))
    if bios:
        sys_items.append(("BIOS", bios, None))
    tz = get_timezone()
    if tz:
        sys_items.append(("Timezone", tz, None))
    sys_items.append(("Locale", get_locale(), None))
    sys_items.append(("Init", get_init(), None))
    sys_items.append(("Arch", get_arch(), None))

    # ---------- ◈ Оборудование ----------
    cpu = get_cpu()
    hw_items = [
        ("CPU", cpu, None),
    ]
    if gov:
        hw_items.append(("Governor", gov, None))
    if gpus:
        hw_items.append(("GPU", gpus[0], None))
    if len(gpus) > 1:
        hw_items.append(("iGPU", gpus[1], None))
    if gpu_drv:
        hw_items.append(("Driver", gpu_drv, None))
    vram = get_gpu_memory()
    if vram:
        hw_items.append(("VRAM", f"{vram[1]}/{vram[0]} MiB", None))
    util = get_gpu_util()
    if util is not None:
        hw_items.append(("GPU Use", f"{util}%", float(util)))
    if cpu_temp is not None:
        hw_items.append(("CPU Temp", f"{cpu_temp:.0f}°C", None))
    if gpu_temp is not None:
        hw_items.append(("GPU Temp", f"{gpu_temp:.0f}°C", None))
    if res:
        disp = res + (f" ({mon})" if mon else "")
        hw_items.append(("Display", disp, None))
    hw_items.append(("DE", de, None))
    hw_items.append(("Terminal", get_terminal(), None))
    shell = get_shell()
    shv = get_shell_version()
    hw_items.append(("Shell", f"{shell} {shv}" if shv else shell, None))
    hw_items.append(("Launched", get_parent_process(), None))

    # ---------- ◈ Ресурсы ----------
    swap = get_swap()
    res_items = [
        ("Memory", f"{mu:.1f}/{mt:.1f}GiB", mpct),
        ("Swap", f"{swap[0]:.1f}/{swap[1]:.1f}GiB" if swap else None,
         (100 * swap[0] / swap[1]) if swap else None),
        ("Disk /", f"{du:.0f}/{dt:.0f}GiB", dpct),
    ]
    # /home показываем только если это реально отдельная точка монтирования
    if _is_separate_mount("/home"):
        res_items.append(("Disk /home", f"{hu:.0f}/{ht:.0f}GiB", hpct))
    if bat:
        pct, status = bat
        icon_b = "⚡" if status == "Charging" else "🔋"
        health = get_battery_health()
        res_items.append(("Battery", f"{pct}% {icon_b}", float(pct)))
        if health is not None:
            res_items.append(("Health", f"{health:.0f}%", health))
    pkgs = get_packages()
    if pkgs != "?":
        res_items.append(("Packages", pkgs, None))
    res_items.append(("Load", get_load(), None))
    procs = get_processes()
    if procs:
        res_items.append(("Processes", str(procs), None))

    sections = [
        ("◈ System", sys_items),
        ("◈ Hardware", hw_items),
        ("◈ Resources", res_items),
    ]

    # ---------- ◈ Сеть ----------
    net_items = []
    for name, status, ip in ifaces:
        if name in vpns:
            continue
        ip_short = ip.split("/")[0] if ip else "-"
        net_items.append(("Iface", f"{name} ({ip_short})", None))
    # Wi-Fi: SSID + сила сигнала
    ssid, signal = get_wifi_info()
    if ssid:
        sig = f"{signal}%" if signal is not None else ""
        net_items.append(("WiFi", f"{ssid}" + (f" ({sig})" if sig else ""), None))
    if vpns:
        vpn_name = vpns[0]
        if ext:
            net_items.append(("VPN", f"✓ {vpn_name} → {ext['country']} ({ext['city']})", None))
        else:
            net_items.append(("VPN", f"✓ {vpn_name}", None))
        net_items.append(("Note", T("WAN IP / country — via VPN"), None))
    else:
        if ext:
            net_items.append(("VPN", f"✗ {T('off')} → {ext['country']} ({ext['city']})", None))
    if ext:
        net_items.append(("WAN IP", ext["ip"], None))
    if speed:
        mbps, elapsed = speed
        net_items.append(("Speed", f"↓ {mbps:.0f} Mbps ({elapsed:.1f}s)", None))
    elif with_speed:
        net_items.append(("Speed", T("unavailable"), None))
    if net_items:
        sections.append(("◈ Network", net_items))

    # ---------- ◈ Тема ----------
    theme_items = []
    # название активной темы + режим
    tname = theme_name()
    if tname != "?":
        tmode = _THEME_CACHE.get("mode", "?")
        theme_items.append(("Theme", f"{tname} ({tmode})", None))
    if theme.get("gtk"):
        theme_items.append(("GTK", theme["gtk"], None))
    if theme.get("icons"):
        theme_items.append(("Icons", theme["icons"], None))
    if theme.get("font"):
        theme_items.append(("Font", theme["font"], None))
    if theme.get("cursor"):
        theme_items.append(("Cursor", theme["cursor"], None))
    # образец палитры темы — цветными квадратиками (спец-значение: список цветов).
    # Порядок тот же, что и у блоков: от самого светлого к самому тёмному.
    palette = palette_for_sections(_MAX_SECTIONS)
    if palette:
        theme_items.append(("Palette", palette, None))
    if theme_items:
        sections.append(("◈ Theme", theme_items))

    # ---------- ◈ Сборка ----------
    binfo = get_build_info()
    sections.append(("◈ Build", [
        ("OS ID", binfo["id"], None),
        ("Version", binfo["version"], None),
        ("Build", binfo["build_id"], None),
    ]))

    return sections


# ============================================================ общий рендер инфо

KEY_WIDTH = 12


def _static_block_lines(blk, frame: int = 0) -> list[str]:
    """Блок в статичном виде: рамка-оконтовка + дерево, семейство темы."""
    fam_dim, fam_bright = frame_colors(blk.si, frame)
    lines = []
    # ---- верхняя линия с заголовком ----
    title = f" {T(blk.title)} "
    inner = blk.width - 2
    pad = max(0, inner - len(title))
    left_pad = pad // 2
    right_pad = pad - left_pad
    lines.append(fg(fam_dim) + FRAME_TL + FRAME_H * left_pad + RESET
                 + fg(fam_bright) + BOLD + title + RESET
                 + fg(fam_dim) + FRAME_H * right_pad + FRAME_TR + RESET)
    # ---- строки ----
    n = len(blk.rows)
    for kv_i, row in enumerate(blk.rows):
        is_last = kv_i == n - 1
        conn = TREE_END if is_last else TREE_MID
        col = family_color(blk.si, kv_i, n, frame)
        icon = key_icon(row.key)
        # палитра темы — особая строчка с цветными квадратиками
        if is_palette_value(row.value):
            swatches = " ".join(fg(c) + "██" + RESET for c in row.value)
            body = f"{icon} {conn}{T(row.key):<{KEY_WIDTH}} {swatches}"
            body_vis = visible_width(icon) + 1 + len(conn) + KEY_WIDTH + 1 \
                + 2 * len(row.value) + max(0, len(row.value) - 1)
        else:
            value = row.value or "-"
            body = f"{icon} {conn}{T(row.key):<{KEY_WIDTH}} {value}"
            if row.pct is not None:
                if row.bar_kind == "uptime":
                    body += " " + uptime_bar(row.pct / 100 * 7 * 86400)
                else:
                    body += " " + bar(row.pct)
            body_vis = visible_width(icon) + 1 + len(conn) + KEY_WIDTH + 1 \
                + visible_width(str(value)) \
                + (11 if row.pct is not None else 0)
        # стенки-оконтовка: первая и последняя строки блока — без стенок,
        # но на разрывах — узор
        pl, pr = break_pattern(frame)
        if kv_i == 0 or is_last:
            left = fg(fam_dim) + pl + RESET
            right = fg(fam_dim) + pr + RESET
        else:
            left = fg(fam_dim) + FRAME_V + " " + RESET
            right = fg(fam_dim) + " " + FRAME_V + RESET
        vis = blk.width - 2 - body_vis
        fill = " " * max(0, vis)
        lines.append(left + fg(col) + BOLD + body + RESET + fill + right)
    # ---- нижняя линия ----
    lines.append(fg(fam_dim) + FRAME_BL + FRAME_H * (blk.width - 2)
                 + FRAME_BR + RESET)
    return lines


def render_info_static(sections, indent: str = "") -> None:
    """Печать инфоблока (для --no-logo)."""
    blocks = build_blocks(sections, rot=_rotation_offset())
    for blk in blocks:
        for line in _static_block_lines(blk):
            print(indent + line)
        print()


# ============================================================ рендер (статика)

def render_static(with_speed: bool = False) -> None:
    """Отрисовывает логотип + инфу, выходит."""
    art = get_art()
    sections = build_sections(with_speed=with_speed)
    user = os.environ.get("USER", "user")
    host = socket.gethostname()

    art_lines = []
    for ri, line in enumerate(art):
        t = ri / max(len(art) - 1, 1)
        ct = 0.35 + 0.65 * (1.0 - t)
        art_lines.append(fg(fire_color(ct)) + line)

    art_lines.append("")
    art_lines.append(fg(196) + BOLD + " " * 2 + user + RESET
                     + fg(208) + "@" + RESET
                     + fg(226) + BOLD + host + RESET)

    art_lines.append("")
    art_lines.append(fg(fire_color(0.3)) + " " * 6 + "by lostflam")

    blocks = build_blocks(sections, rot=_rotation_offset())
    info_lines = [""]
    for blk in blocks:
        info_lines.extend(_static_block_lines(blk))
        info_lines.append("")

    total = max(len(art_lines), len(info_lines))

    import re

    def visible_len(s):
        return len(re.sub(r"\033\[[0-9;]*m", "", s))

    art_w = max(visible_len(l) for l in art_lines)

    for i in range(total):
        left = art_lines[i] if i < len(art_lines) else ""
        right = info_lines[i] if i < len(info_lines) else ""
        pad = " " * max(0, art_w - visible_len(left) + 4)
        if left:
            print(left + RESET + pad + right)
        else:
            print(pad + right)


# ============================================================ рендер (анимация)

GLITCH_COLORS = [45, 51, 87, 201, 129, 141]
GLITCH_GLYPHS = "░▒▓█┤├┼╳╱╲▚▞≡⌁01"
FIRE_PARTICLE_CHARS = [".", "*", "·", "'", "`", ":", "⁚"]


class Particle:
    __slots__ = ("x", "y", "px", "py", "vx", "vy", "life", "max_life", "char", "kind")

    def __init__(self, x, y, kind):
        self.x = self.px = x
        self.y = self.py = y
        self.kind = kind
        if kind == "fire":
            self.vx = random.uniform(-0.5, 0.5)
            self.vy = random.uniform(-1.7, -0.5)
            self.char = random.choice(FIRE_PARTICLE_CHARS)
            self.max_life = self.life = random.uniform(12, 30)
        else:
            self.vx = random.uniform(-0.15, 0.15)
            self.vy = random.choice([random.uniform(-1.1, -0.3), random.uniform(0.3, 1.1)])
            self.char = random.choice("01░▒▓█")
            self.max_life = self.life = random.uniform(16, 34)

    def step(self):
        self.px, self.py = self.x, self.y
        self.x += self.vx
        self.y += self.vy
        self.vy *= 0.93
        if self.kind == "fire":
            self.vx += random.uniform(-0.09, 0.09)
            self.vy -= 0.012
        else:
            self.vx += random.uniform(-0.05, 0.05)
        self.life -= 1
        return self.life > 0

    def color(self):
        t = self.life / self.max_life
        if self.kind == "fire":
            if t > 0.75:
                return 255
            if t > 0.5:
                return 226
            if t > 0.25:
                return 208
            return 52
        return GLITCH_COLORS[int(t * (len(GLITCH_COLORS) - 1)) % len(GLITCH_COLORS)]


# ---------------------------------------------------------------- модель инфоблока

class InfoRow:
    """Строка инфоблока: заголовок раздела, пункт или пустая."""
    __slots__ = ("kind", "key", "value", "pct", "bar_kind", "color", "start",
                 "anim", "phase", "shade", "si", "row_i")

    def __init__(self, kind, key="", value="", pct=None, bar_kind=None,
                 color=None, start=0, anim="typewriter", phase=0.0,
                 shade=1.0, si=0, row_i=0):
        self.kind = kind            # 'header' | 'kv' | 'blank'
        self.key = key
        self.value = value
        self.pct = pct
        self.bar_kind = bar_kind
        self.color = color
        self.start = start          # кадр, на котором строка начинает печататься
        self.anim = anim            # анимация блока (свой код из ANIM_LIBRARY)
        self.phase = phase          # личный сдвиг тайминга строки
        self.shade = shade          # лёгкое затемнение цвета по позиции
        self.si = si                # индекс блока (для цветового семейства)
        self.row_i = row_i          # позиция строки внутри блока


class Block:
    """Блок инфоблока: заголовок + строки + геометрия рамки."""
    __slots__ = ("si", "title", "rows", "y_top", "height", "width",
                 "first_start", "last_start", "anim")

    def __init__(self, si, title, rows, y_top, width, anim):
        self.si = si
        self.title = title
        self.rows = rows
        self.y_top = y_top          # строка верхней рамки
        self.height = len(rows) + 2 # рамка сверху + строки + рамка снизу
        self.width = width          # полная ширина рамки
        self.first_start = rows[0].start if rows else 0
        self.last_start = rows[-1].start if rows else 0
        self.anim = anim


def _row_content_width(key: str, value: str, pct: float | None) -> int:
    """Ширина строки внутри рамки: значок + коннектор + ключ + значение + бар.
    Ключ выравнивается по колонке KEY_WIDTH — считаем по ней, не по факту."""
    w = visible_width(key_icon(key)) + 1 + len(TREE_MID) + KEY_WIDTH + 1 + visible_width(str(value))
    if pct is not None:
        w += 1 + 10 + 1              # пробел + бар (10) + запас
    return w


def build_blocks(sections, rot: int = 0, frame_base: int = 0,
                 max_width: int = 100) -> list[Block]:
    """Собирает блоки с рамками. Каждый блок — своя анимация из библиотеки
    (с ротацией rot) и своё цветовое семейство; строки внутри блока —
    та же анимация, но градиент темнее и сдвиг тайминга по позиции."""
    blocks = []
    y = 2
    frame = 6 + frame_base
    n_anim = len(ANIM_LIBRARY)
    for si, (title, items) in enumerate(sections):
        real = [(k, v, p) for k, v, p in items if v is not None]
        if not real:
            continue
        block_anim = ANIM_LIBRARY[(si + rot) % n_anim]
        n_rows = len(real)
        # ширина рамки — по самой длинной строке блока
        content_w = max(_row_content_width(k, str(v), p) for k, v, p in real)
        content_w = max(content_w, len(title) + 6)
        width = min(content_w + 4, max_width)   # │ + пробел + контент + пробел + │

        rows = []
        for kv_i, (key, value, pct) in enumerate(real):
            depth = kv_i / max(n_rows - 1, 1)
            shade = 1.0 - 0.35 * depth          # до 35% темнее к концу блока
            phase = si * 1.7 + kv_i * 0.55      # каскад внутри блока
            rows.append(InfoRow("kv", key=key, value=value, pct=pct,
                                bar_kind="uptime" if key == "Uptime" else None,
                                color=item_color(key), start=frame,
                                anim=block_anim, phase=phase, shade=shade,
                                si=si, row_i=kv_i))
            frame += 1 if kv_i % 2 == 0 else 0
        blocks.append(Block(si, title, rows, y, width, block_anim))
        y += n_rows + 3          # рамка + строки + рамка + пропуск
    return blocks


def _bar_cells(pct: float, width: int) -> list[tuple[str, int]]:
    """Ячейки бара: [(символ, цвет), ...] — цвет по загрузке."""
    pct = max(0.0, min(100.0, pct))
    filled = int(pct / 100 * width)
    if filled == 0 and pct > 0:
        filled = 1
    if pct < 50:
        color = 78
    elif pct < 80:
        color = 220
    else:
        color = 196
    cells = [(BAR_FILLED, color)] * filled + [(BAR_EMPTY, COLOR_DIM)] * (width - filled)
    return cells


def render_animated(intro: float = 0.0, with_speed: bool = False) -> None:
    art = get_art()
    flam = art[:5]
    quency = art[7:]
    art_h = len(art)

    try:
        cols, rows = os.get_terminal_size()
    except OSError:
        cols, rows = 120, 30

    # ротация: каждая сессия стартует со сдвигом набора анимаций
    rot = _rotation_offset()
    sections = build_sections(with_speed=with_speed)

    art_w = max(len(l) for l in art)
    info_col = art_w + 6
    max_block_w = max(20, cols - info_col - 1)
    blocks = build_blocks(sections, rot=rot, max_width=max_block_w)
    rot_frame = 0          # кадр, на котором пересобрали анимации

    # сколько строк нужно под инфоблок (+ логотип/подписи слева)
    need_rows = max((b.y_top + b.height for b in blocks), default=0) + 3
    if rows < need_rows and not intro:
        print(f"Терминал мал: нужно ~{need_rows} строк, есть {rows}.")
        return

    particles = []
    frame = 0
    start = time.monotonic()
    max_frames = int(intro / 0.08) + 4 if intro else 0
    deadline = start + intro + 0.5 if intro else None

    flam_rows = list(range(2, 2 + len(flam)))
    quency_rows = list(range(2 + len(flam) + 1, 2 + len(flam) + 1 + len(quency)))

    # глитч-состояние: {(индекс блока, индекс строки): кадр начала}
    glitch_rows = {}
    # scanning-полоса медленно идёт вниз по инфоблоку
    scan_span = max((b.y_top + b.height for b in blocks), default=20)

    sys.stdout.write("\033[2J\033[H" + "\033[?25l")
    sys.stdout.flush()

    try:
        while True:
            if intro and (time.monotonic() - start > intro
                          or (max_frames and frame >= max_frames)
                          or (deadline and time.monotonic() > deadline)):
                break

            frame += 1
            # ротация набора анимаций: каждые ROTATE_FRAMES кадров блоки
            # по кругу получают анимацию соседа (глитч уезжает во второй блок,
            # свечение — в третий, и т.д.)
            if frame - rot_frame >= ROTATE_FRAMES:
                rot_frame = frame
                rot = (rot + 1) % len(ANIM_LIBRARY)
                # мягко сдвигаем тайминги, чтобы каскад не «схлопывался»
                blocks = build_blocks(sections, rot=rot, frame_base=frame,
                                      max_width=max_block_w)
            canvas = [[" "] * cols for _ in range(rows)]
            ccolor = [[0] * cols for _ in range(rows)]
            cattr = [[""] * cols for _ in range(rows)]
            glow = [[0.0] * cols for _ in range(rows)]

            # ---- Flam: пламя + свечение ----
            for ri, line in enumerate(flam):
                y = flam_rows[ri]
                if y >= rows:
                    break
                shimmer = int(1.6 * math.sin(beat(frame, 1.6) + ri * 0.8))
                for ci, ch in enumerate(line):
                    if ch == " ":
                        continue
                    x = ci + 2 + shimmer
                    if not (0 <= x < cols):
                        continue
                    canvas[y][x] = ch
                    wave = ri / max(len(flam) - 1, 1)
                    flicker = random.uniform(-0.15, 0.15)
                    pulse = 0.3 * math.sin(beat(frame, 3.6) + ri)
                    t = max(0.0, min(1.0, wave + 0.4 + pulse + flicker))
                    ccolor[y][x] = fire_color(t)
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < rows and 0 <= nx < cols:
                                d = max(abs(dy), abs(dx))
                                g = (0.42 if d == 1 else 0.18) * (0.6 + 0.4 * t)
                                glow[ny][nx] = max(glow[ny][nx], g)

            # ---- quency: глитч + RGB split ----
            inverted_row = None
            if quency and random.random() < 0.06:
                inverted_row = random.choice(quency_rows)
            for ri, line in enumerate(quency):
                y = quency_rows[ri]
                if y >= rows:
                    break
                chars = line
                if random.random() < 0.10:
                    shift = random.randint(-4, 4)
                    if shift > 0:
                        chars = chars[shift:] + " " * shift
                    elif shift < 0:
                        chars = " " * (-shift) + chars[:shift]
                for ci, ch in enumerate(chars):
                    if ch == " ":
                        continue
                    x = ci + 2
                    if not (0 <= x < cols):
                        continue
                    glyph = ch
                    if random.random() < 0.02:
                        glyph = random.choice(GLITCH_GLYPHS)
                    canvas[y][x] = glyph
                    if random.random() < 0.08:
                        ccolor[y][x] = random.choice([208, 226, 255])
                    else:
                        ccolor[y][x] = random.choice(GLITCH_COLORS)
                    if random.random() < 0.14:
                        if x - 1 >= 0 and canvas[y][x - 1] == " ":
                            canvas[y][x - 1] = glyph
                            ccolor[y][x - 1] = 196
                        if x + 1 < cols and canvas[y][x + 1] == " ":
                            canvas[y][x + 1] = glyph
                            ccolor[y][x + 1] = 51
                    if y == inverted_row:
                        cattr[y][x] = INVERSE
                    elif ri % 2 == 1:
                        cattr[y][x] = DIM

            # ---- жаровые волны ----
            if flam_rows and frame % 3 == 0:
                heat_row = flam_rows[-1] + 1
                if 0 <= heat_row < rows:
                    for _ in range(2):
                        hx = random.randint(2, min(cols - 3, 60))
                        if canvas[heat_row][hx] == " ":
                            canvas[heat_row][hx] = random.choice(["·", ".", "'"])
                            ccolor[heat_row][hx] = random.choice([208, 214, 220, 226])

            # ---- спавн частиц ----
            if frame % 2 == 0:
                for _ in range(4):
                    ri = random.randint(0, len(flam) - 1)
                    line = flam[ri]
                    if line.strip():
                        ci = random.randint(0, len(line) - 1)
                        if line[ci] != " ":
                            particles.append(Particle(ci + 2, flam_rows[ri], "fire"))
                for _ in range(2):
                    ri = random.randint(0, len(quency) - 1)
                    line = quency[ri]
                    if line.strip():
                        ci = random.randint(0, len(line) - 1)
                        if line[ci] != " ":
                            particles.append(Particle(ci + 2, quency_rows[ri], "digital"))

            # ---- частицы + трейлы ----
            alive = []
            for p in particles:
                if not p.step():
                    continue
                tx, ty = int(p.px), int(p.py)
                if (0 <= tx < cols and 0 <= ty < rows and canvas[ty][tx] == " "
                        and p.kind == "fire" and p.life < p.max_life * 0.7):
                    canvas[ty][tx] = random.choice(["·", ".", " "])
                    ccolor[ty][tx] = 52 if p.life > 6 else 238
                x, y = int(p.x), int(p.y)
                if 0 <= x < cols and 0 <= y < rows and canvas[y][x] == " ":
                    canvas[y][x] = p.char
                    ccolor[y][x] = p.color()
                alive.append(p)
            particles = alive
            if len(particles) > 420:
                particles = particles[-420:]

            # ---- подпись: градиент + свечение ----
            sub = "by lostflam"
            sx = 6
            sy = art_h + 2
            if 0 <= sy < rows:
                for i, ch in enumerate(sub):
                    if sx + i < cols:
                        canvas[sy][sx + i] = ch
                        wave = (i / max(len(sub) - 1, 1) + beat(frame, 0.75)) % 1.0
                        ccolor[sy][sx + i] = fire_color(wave)
                        for dy in (-1, 0, 1):
                            for dx in (-1, 0, 1):
                                ny, nx = sy + dy, sx + i + dx
                                if 0 <= ny < rows and 0 <= nx < cols and canvas[ny][nx] == " ":
                                    glow[ny][nx] = max(glow[ny][nx], 0.5)

            # ---- заголовок user@host под артом ----
            user = os.environ.get("USER", "user")
            host = socket.gethostname()
            header = f"{user}@{host}"
            ty = sy + 2
            if 0 <= ty < rows:
                tx = 4
                for i, ch in enumerate(header):
                    if tx + i < cols:
                        canvas[ty][tx + i] = ch
                        if i < len(user):
                            ccolor[ty][tx + i] = 196
                        elif ch == "@":
                            ccolor[ty][tx + i] = 208
                        else:
                            ccolor[ty][tx + i] = 226

            # ===== инфоблок: блоки с рамками, дерево, семейства цветов =====
            fstyle = frame_style(frame)
            scan_y = 2 + ((beat(frame, 10.0)) % (scan_span + 10))

            # случайные цифровые глитчи на значениях (по блокам и строкам)
            if frame % 61 == 0 and blocks:
                bi = random.randrange(len(blocks))
                if blocks[bi].rows:
                    ri = random.randrange(len(blocks[bi].rows))
                    glitch_rows[(bi, ri)] = frame

            for blk in blocks:
                si = blk.si
                fam_dim, fam_bright = frame_colors(si, frame)
                fx = info_col                            # левый край рамки
                fy = blk.y_top
                fw = blk.width
                if fy + blk.height > rows:
                    continue
                # рамка появляется, когда блок начинает печататься
                if frame < blk.first_start:
                    continue
                frame_prog = (frame - blk.first_start + 1) * 5

                # ---- верхняя линия: ╭── заголовок ──╮ ----
                top_y = fy
                if top_y < rows:
                    for i in range(fw):
                        x = fx + i
                        if x >= cols:
                            break
                        if i >= frame_prog:
                            break
                        if i == 0:
                            ch, col, at = FRAME_TL, fam_dim, ""
                        elif i == fw - 1:
                            ch, col, at = FRAME_TR, fam_dim, ""
                        else:
                            ch, col, at = frame_cell(fstyle, frame, FRAME_H,
                                                     fx + i, fam_dim, fam_bright)
                        canvas[top_y][x] = ch
                        ccolor[top_y][x] = col
                        if at:
                            cattr[top_y][x] = at
                    # заголовок сидит на верхней линии
                    title = f" {T(blk.title)} "
                    n = min(len(title), int(frame_prog) - 2)
                    for i in range(max(0, n)):
                        x = fx + 2 + i
                        if x >= cols:
                            break
                        # заголовок плавится в тон теме, но ярче стенок
                        canvas[top_y][x] = title[i]
                        ccolor[top_y][x] = fam_bright
                        cattr[top_y][x] = BOLD

                # ---- строки: значок + коннектор + ключ + значение ----
                n_rows = len(blk.rows)
                for kv_i, row in enumerate(blk.rows):
                    y = fy + 1 + kv_i
                    if y >= rows:
                        break
                    st = row.start
                    if frame < st:
                        continue
                    prog = (frame - st + 1) * 8        # символов за кадр
                    scanned = abs(y - scan_y) < 1.3
                    glitched = glitch_rows.get((si, kv_i), 0) and \
                        frame - glitch_rows[(si, kv_i)] < 3
                    is_last = kv_i == n_rows - 1

                    # цвет строки: семейство блока (из темы) + градиент
                    base = family_color(si, row.row_i, n_rows, frame)
                    fam_list = theme_family(si)
                    fresh = frame - st < 5
                    key_base = 255 if fresh else base
                    anim = row.anim
                    phase = row.phase
                    shade = row.shade

                    # коннектор дерева: ├─ или └─ на последней строке
                    conn = TREE_END if is_last else TREE_MID
                    icon = key_icon(row.key)

                    # стенки-оконтовка: первая и последняя строки — без стенок,
                    # на разрывах — узор
                    pl, pr = break_pattern(frame)
                    if kv_i == 0 or is_last:
                        if fx < cols:
                            canvas[y][fx] = pl
                            ccolor[y][fx] = shade_color(fam_dim, 0.9)
                        rx = fx + fw - 1
                        if rx < cols:
                            canvas[y][rx] = pr
                            ccolor[y][rx] = shade_color(fam_dim, 0.9)
                    else:
                        if fx < cols:
                            canvas[y][fx] = frame_vchar(fstyle, frame, y)
                            ccolor[y][fx] = shade_color(fam_dim, 0.9)
                        rx = fx + fw - 1
                        if rx < cols:
                            canvas[y][rx] = frame_vchar(fstyle, frame, y)
                            ccolor[y][rx] = shade_color(fam_dim, 0.9)

                    # ---- палитра темы: цветные квадратики вместо текста ----
                    if is_palette_value(row.value):
                        # префикс: значок + коннектор + ключ — как у обычной строки
                        prefix = f"{icon} {conn}{T(row.key).ljust(KEY_WIDTH)} "
                        pos = 0
                        for j, ch in enumerate(prefix):
                            gp = pos + j
                            if gp >= prog:
                                break
                            x = fx + 1 + gp
                            if x >= cols:
                                break
                            if ch != " ":
                                canvas[y][x] = ch
                                if j < visible_width(icon):
                                    ccolor[y][x] = base
                                elif j < visible_width(icon) + 1 + len(conn):
                                    ccolor[y][x] = shade_color(fam_dim, 0.8)
                                else:
                                    ccolor[y][x] = key_base
                        pos = len(prefix)
                        # образцы палитры: по 2 клетки на цвет, с пробелом
                        bx = fx + 1 + pos + 1
                        sw_prog = (frame - st + 1) * 8 - pos - 1
                        for ci, pc in enumerate(row.value):
                            for k in range(2):
                                if bx >= cols or bx >= fx + fw - 1:
                                    break
                                if sw_prog > ci * 3 + k:
                                    canvas[y][bx] = "█"
                                    ccolor[y][bx] = pc
                                bx += 1
                            bx += 1     # пробел между образцами
                        continue

                    seq = [(icon + " ", base, "", "icon"),
                           (conn, shade_color(fam_dim, 0.8), "", "conn"),
                           (T(row.key).ljust(KEY_WIDTH), key_base,
                            BOLD if math.sin(beat(frame, 2.2) + phase) > -0.3 else "",
                            "key"),
                           (" ", COLOR_DIM, "", "gap"),
                           (row.value, COLOR_VALUE, "", "value")]
                    pos = 0
                    for text, col, at, seg in seq:
                        for j, ch in enumerate(text):
                            gp = pos + j
                            if gp >= prog:
                                break
                            x = fx + 1 + gp
                            if x >= cols:
                                break
                            if seg in ("icon", "conn", "gap"):
                                c, cc, ca = ch, col, at
                            elif seg == "key":
                                c, cc, ca = apply_anim(anim, ch, frame,
                                                       phase + 0.4, gp,
                                                       key_base, shade,
                                                       fam_list, prog)
                                if fresh:
                                    cc = 255
                            else:
                                c, cc, ca = apply_anim(anim, ch, frame, phase,
                                                       gp, base, shade,
                                                       fam_list, prog)
                            if scanned and c != " ":
                                cc = 255
                            if glitched and c != " " and random.random() < 0.4:
                                c = random.choice(GLITCH_GLYPHS)
                                cc = random.choice([201, 51, 196])
                            if c != " ":
                                canvas[y][x] = c
                                ccolor[y][x] = cc
                                if ca or at:
                                    cattr[y][x] = ca or at
                        pos += len(text)

                    # курсор печатающей машинки
                    if prog < pos and anim == "typewriter":
                        x = fx + 1 + int(prog)
                        if x < cols and canvas[y][x] == " ":
                            canvas[y][x] = "▌"
                            ccolor[y][x] = COLOR_CURSOR

                    # бар: растёт от 0 до целевого значения
                    if row.pct is not None and pos + 1 < prog:
                        grow = min(1.0, (prog - pos - 1) / 22.0)
                        fill_pct = (row.pct or 0) * grow
                        bx = fx + 1 + pos + 1
                        for sym, bcol in _bar_cells(fill_pct, 10):
                            if bx >= cols:
                                break
                            if sym != " ":
                                canvas[y][bx] = sym
                                ccolor[y][bx] = 255 if (scanned and sym == BAR_FILLED) else bcol
                            bx += 1

                # ---- нижняя рамка: ╰──────╯ ----
                bot_y = fy + blk.height - 1
                if bot_y < rows:
                    # низ появляется, когда допечатана последняя строка
                    bot_prog = (frame - blk.last_start + 1) * 5
                    for i in range(fw):
                        x = fx + i
                        if x >= cols:
                            break
                        if i >= bot_prog:
                            break
                        if i == 0:
                            ch, col, at = FRAME_BL, fam_dim, ""
                        elif i == fw - 1:
                            ch, col, at = FRAME_BR, fam_dim, ""
                        else:
                            ch, col, at = frame_cell(fstyle, frame, FRAME_H,
                                                     fx + i, fam_dim, fam_bright)
                        canvas[bot_y][x] = ch
                        ccolor[bot_y][x] = col
                        if at:
                            cattr[bot_y][x] = at

            # ===== вывод кадра =====
            out = ["\033[H"]
            for y in range(rows):
                line_chars = []
                prev_color = -1
                prev_attr = ""
                for x in range(cols):
                    c = canvas[y][x]
                    col = ccolor[y][x]
                    attr = cattr[y][x]
                    if c == " " and col == 0 and glow[y][x] > 0.3:
                        col = fire_color(glow[y][x] * 0.5)
                    if c == " " and col == 0 and not attr:
                        line_chars.append(" ")
                        continue
                    piece = ""
                    if attr != prev_attr:
                        piece += prev_attr and RESET or ""
                        piece += attr
                        prev_attr = attr
                    if col != prev_color:
                        piece += fg(col)
                        prev_color = col
                    line_chars.append(piece + c)
                tail = RESET if (prev_attr or prev_color != -1) else ""
                out.append("".join(line_chars) + tail + "\033[K\n")

            out_str = "".join(out)
            try:
                sys.stdout.write(out_str)
                sys.stdout.flush()
            except (BrokenPipeError, BlockingIOError, OSError):
                pass
            time.sleep(FRAME_DELAY)

    except KeyboardInterrupt:
        pass
    except Exception:
        if not intro:
            raise
    finally:
        sys.stdout.write("\033[?25h" + "\033[2J\033[H")
        sys.stdout.flush()


# ============================================================ main

def main():
    global CURRENT_LANG
    parser = argparse.ArgumentParser(
        prog="flamfetch",
        description="FlamFetch — fiery animated system fetch",
        add_help=True,
    )
    parser.add_argument("--animate", "-a", action="store_true",
                        help="live logo animation")
    parser.add_argument("--intro", type=float, default=0.0,
                        help="seconds of animation, then exit (0 = forever)")
    parser.add_argument("--no-logo", action="store_true",
                        help="system info only, no logo")
    parser.add_argument("--speed", "-s", action="store_true",
                        help="quick speedtest (~2-8 sec)")
    parser.add_argument("--lang", "-l", choices=["en", "ru"], default=None,
                        help="interface language (default: en; env FLAMFETCH_LANG)")
    parser.add_argument("--version", "-V", action="version",
                        version="flamfetch 1.8.1")
    args = parser.parse_args()

    # язык: флаг > переменная окружения > системная локаль > en
    if args.lang:
        CURRENT_LANG = args.lang
    elif os.environ.get("FLAMFETCH_LANG", "").lower() in ("ru", "en"):
        CURRENT_LANG = os.environ["FLAMFETCH_LANG"].lower()
    else:
        loc = (os.environ.get("LC_ALL") or os.environ.get("LANG")
               or os.environ.get("LANGUAGE") or "").lower()
        if loc.startswith("ru"):
            CURRENT_LANG = "ru"
    locale.setlocale(locale.LC_ALL, "")   # для корректного вывода на Windows

    if args.no_logo:
        sections = build_sections(with_speed=args.speed)
        render_info_static(sections)
        return

    if args.animate:
        render_animated(args.intro, with_speed=args.speed)
    else:
        render_static(with_speed=args.speed)


if __name__ == "__main__":
    main()
