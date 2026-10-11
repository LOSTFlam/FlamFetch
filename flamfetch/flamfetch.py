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

Версия: 1.3.0
"""

import argparse
import math
import os
import platform
import random
import shutil
import socket
import subprocess
import sys
import time
import zlib
from pathlib import Path

try:
    import pyfiglet
except ImportError:
    print("FlamFetch требует pyfiglet:  pip install pyfiglet", file=sys.stderr)
    sys.exit(1)


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
    return platform.release()


def get_uptime() -> str:
    raw = _read("/proc/uptime")
    if not raw:
        return "?"
    secs = int(float(raw.split()[0]))
    d, secs = divmod(secs, 86400)
    h, secs = divmod(secs, 3600)
    m, _ = divmod(secs, 60)
    parts = []
    if d:
        parts.append(f"{d}д")
    if h:
        parts.append(f"{h}ч")
    parts.append(f"{m}м")
    return " ".join(parts)


def get_board() -> str | None:
    vendor = _read("/sys/class/dmi/id/board_vendor")
    name = _read("/sys/class/dmi/id/board_name")
    if vendor or name:
        return f"{vendor or ''} {name or ''}".strip()
    return None


def get_bios() -> str | None:
    return _read("/sys/class/dmi/id/bios_version")


def get_locale() -> str:
    loc = os.environ.get("LC_ALL") or os.environ.get("LANG") or "?"
    return loc.split(".")[0] if loc != "?" else loc


def get_init() -> str:
    comm = _read("/proc/1/comm")
    return comm or "?"


def get_arch() -> str:
    return platform.machine()


def get_cpu() -> str:
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
    return None


def get_de() -> str:
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return "Hyprland (Wayland)"
    if os.environ.get("WAYLAND_DISPLAY"):
        return "Wayland"
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


def get_packages() -> str:
    counts = []
    for mgr, cmd in (
        ("pacman", ["pacman", "-Q"]),
        ("flatpak", ["flatpak", "list"]),
    ):
        out = _run(cmd)
        if out:
            n = len(out.splitlines())
            counts.append(f"{n} ({mgr})")
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


def get_gpu() -> list[str]:
    """Возвращает список GPU (NVIDIA + AMD и т.д.)."""
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
    """GTK-тема, иконки, шрифт, курсор."""
    theme = {}
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
    raw = _read("/proc/loadavg")
    if not raw:
        return "?"
    parts = raw.split()
    return f"{parts[0]} {parts[1]} {parts[2]}"


def get_processes() -> int:
    try:
        return len([d for d in os.listdir("/proc") if d.isdigit()])
    except Exception:
        return 0


def get_parent_process() -> str:
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
    sys_items.append(("Locale", get_locale(), None))
    sys_items.append(("Init", get_init(), None))
    sys_items.append(("Arch", get_arch(), None))

    # ---------- ◈ Оборудование ----------
    hw_items = [
        ("CPU", get_cpu(), None),
    ]
    if gov:
        hw_items.append(("Governor", gov, None))
    if gpus:
        hw_items.append(("GPU", gpus[0], None))
    if len(gpus) > 1:
        hw_items.append(("iGPU", gpus[1], None))
    if gpu_drv:
        hw_items.append(("Driver", gpu_drv, None))
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
        res_items.append(("Battery", f"{pct}% {icon_b}", float(pct)))
    pkgs = get_packages()
    if pkgs != "?":
        res_items.append(("Packages", pkgs, None))
    res_items.append(("Load", get_load(), None))
    procs = get_processes()
    if procs:
        res_items.append(("Processes", str(procs), None))

    sections = [
        ("◈ Система", sys_items),
        ("◈ Оборудование", hw_items),
        ("◈ Ресурсы", res_items),
    ]

    # ---------- ◈ Сеть ----------
    net_items = []
    for name, status, ip in ifaces:
        if name in vpns:
            continue
        ip_short = ip.split("/")[0] if ip else "-"
        net_items.append(("Iface", f"{name} ({ip_short})", None))
    if vpns:
        vpn_name = vpns[0]
        if ext:
            net_items.append(("VPN", f"✓ {vpn_name} → {ext['country']} ({ext['city']})", None))
        else:
            net_items.append(("VPN", f"✓ {vpn_name}", None))
        net_items.append(("Note", "WAN IP / страна — через VPN", None))
    else:
        if ext:
            net_items.append(("VPN", f"✗ off → {ext['country']} ({ext['city']})", None))
    if ext:
        net_items.append(("WAN IP", ext["ip"], None))
    if speed:
        mbps, elapsed = speed
        net_items.append(("Speed", f"↓ {mbps:.0f} Mbps ({elapsed:.1f}s)", None))
    elif with_speed:
        net_items.append(("Speed", "недоступен", None))
    if net_items:
        sections.append(("◈ Сеть", net_items))

    # ---------- ◈ Тема ----------
    theme_items = []
    if theme.get("gtk"):
        theme_items.append(("GTK", theme["gtk"], None))
    if theme.get("icons"):
        theme_items.append(("Icons", theme["icons"], None))
    if theme.get("font"):
        theme_items.append(("Font", theme["font"], None))
    if theme.get("cursor"):
        theme_items.append(("Cursor", theme["cursor"], None))
    if theme_items:
        sections.append(("◈ Тема", theme_items))

    # ---------- ◈ Сборка ----------
    binfo = get_build_info()
    sections.append(("◈ Сборка", [
        ("OS ID", binfo["id"], None),
        ("Version", binfo["version"], None),
        ("Build", binfo["build_id"], None),
    ]))

    return sections


# ============================================================ общий рендер инфо

KEY_WIDTH = 12


def _format_line(key: str, value: str, pct: float | None,
                 bar_kind: str | None = None) -> str:
    """Строка пункта в статичном виде: цветной ключ + значение + бар."""
    kc = item_color(key)
    line = fg(kc) + BOLD + f"{key:<{KEY_WIDTH}}" + RESET
    line += fg(COLOR_DIM) + "│ " + RESET
    line += fg(COLOR_VALUE) + (value or "-")
    if pct is not None:
        if bar_kind == "uptime":
            line += " " + uptime_bar(pct / 100 * 7 * 86400)
        else:
            line += " " + bar(pct)
    return line


def render_info_static(sections, indent: str = "") -> None:
    """Печать инфоблока (для --no-logo)."""
    for si, (title, items) in enumerate(sections):
        sc = SECTION_COLORS[si % len(SECTION_COLORS)]
        print(fg(sc) + BOLD + f"{indent}{title}" + RESET)
        for key, value, pct in items:
            print(indent + _format_line(key, value, pct,
                                        bar_kind="uptime" if key == "Uptime" else None))
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

    info_lines = [""]
    for si, (title, items) in enumerate(sections):
        sc = SECTION_COLORS[si % len(SECTION_COLORS)]
        info_lines.append(fg(sc) + BOLD + f"  {title}" + RESET)
        for key, value, pct in items:
            info_lines.append("  " + _format_line(
                key, value, pct,
                bar_kind="uptime" if key == "Uptime" else None))
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
    __slots__ = ("kind", "key", "value", "pct", "bar_kind", "color", "start")

    def __init__(self, kind, key="", value="", pct=None, bar_kind=None,
                 color=None, start=0):
        self.kind = kind            # 'header' | 'kv' | 'blank'
        self.key = key
        self.value = value
        self.pct = pct
        self.bar_kind = bar_kind
        self.color = color
        self.start = start          # кадр, на котором строка начинает печататься


def build_info_rows(sections) -> list[InfoRow]:
    rows = []
    frame = 6
    for si, (title, items) in enumerate(sections):
        sec_color = SECTION_COLORS[si % len(SECTION_COLORS)]
        rows.append(InfoRow("header", value=title, color=sec_color, start=frame))
        frame += 2
        kv_i = 0
        for key, value, pct in items:
            if value is None:
                continue
            rows.append(InfoRow("kv", key=key, value=value, pct=pct,
                                bar_kind="uptime" if key == "Uptime" else None,
                                color=item_color(key), start=frame))
            # каскад: чётные строки стартуют сразу, нечётные — на кадр позже
            frame += 1 if kv_i % 2 == 0 else 0
            kv_i += 1
        rows.append(InfoRow("blank", start=frame))
        frame += 1
    return rows


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

    sections = build_sections(with_speed=with_speed)
    info_rows = build_info_rows(sections)

    # сколько строк нужно под инфоблок (+ логотип/подписи слева)
    need_rows = len(info_rows) + 3
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

    art_w = max(len(l) for l in art)
    info_col = art_w + 6

    # глитч-состояние: {индекс строки: кадр начала}
    glitch_rows = {}

    sys.stdout.write("\033[2J\033[H" + "\033[?25l")
    sys.stdout.flush()

    try:
        while True:
            if intro and (time.monotonic() - start > intro
                          or (max_frames and frame >= max_frames)
                          or (deadline and time.monotonic() > deadline)):
                break

            frame += 1
            canvas = [[" "] * cols for _ in range(rows)]
            ccolor = [[0] * cols for _ in range(rows)]
            cattr = [[""] * cols for _ in range(rows)]
            glow = [[0.0] * cols for _ in range(rows)]

            # ---- Flam: пламя + свечение ----
            for ri, line in enumerate(flam):
                y = flam_rows[ri]
                if y >= rows:
                    break
                shimmer = int(1.6 * math.sin(frame * 0.09 + ri * 0.8))
                for ci, ch in enumerate(line):
                    if ch == " ":
                        continue
                    x = ci + 2 + shimmer
                    if not (0 <= x < cols):
                        continue
                    canvas[y][x] = ch
                    wave = ri / max(len(flam) - 1, 1)
                    flicker = random.uniform(-0.15, 0.15)
                    pulse = 0.3 * math.sin(frame * 0.25 + ri)
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
                        wave = (i / max(len(sub) - 1, 1) + frame * 0.04) % 1.0
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

            # ===== инфоблок: печатающая машинка + shimmer + бары + скан-полоса =====
            # scanning-полоса медленно идёт вниз по инфоблоку
            scan_y = 2 + ((frame * 0.55) % (len(info_rows) + 10))

            # случайные цифровые глитчи на значениях
            if frame % 61 == 0 and info_rows:
                idx = random.randrange(len(info_rows))
                if info_rows[idx].kind == "kv":
                    glitch_rows[idx] = frame

            for ri, row in enumerate(info_rows):
                y = 2 + ri
                if y >= rows:
                    break
                st = row.start
                if frame < st:
                    continue
                prog = (frame - st + 1) * 8        # символов за кадр (быстрая печать)
                scanned = abs(y - scan_y) < 1.3    # полоса проходит по строке
                glitched = glitch_rows.get(ri, 0) and frame - glitch_rows[ri] < 3

                if row.kind == "blank":
                    continue

                if row.kind == "header":
                    title = row.value
                    n = min(len(title), int(prog))
                    for i in range(n):
                        x = info_col + i
                        if x >= cols:
                            break
                        # огненный градиент, бегущий по заголовку
                        t = (i / max(len(title) - 1, 1) + frame * 0.04) % 1.0
                        canvas[y][x] = title[i]
                        ccolor[y][x] = fire_color(0.35 + 0.65 * t)
                        cattr[y][x] = BOLD
                    # курсор печатающей машинки
                    if prog < len(title):
                        x = info_col + int(prog)
                        if x < cols and canvas[y][x] == " ":
                            canvas[y][x] = "▌"
                            ccolor[y][x] = COLOR_CURSOR
                    continue

                # ---- kv-строка ----
                key = row.key
                value = row.value or "-"
                pct = row.pct
                base = row.color
                # shimmer: пульс яркости ключа
                attr = BOLD if math.sin(frame * 0.12 + ri * 0.9) > -0.3 else ""
                # свежая строка вспыхивает белым
                fresh = frame - st < 5
                key_col = 255 if fresh else base

                seq = [(key.ljust(KEY_WIDTH), key_col, attr),
                       ("│ ", COLOR_DIM, ""),
                       (value, COLOR_VALUE, "")]
                pos = 0
                for text, col, at in seq:
                    for j, ch in enumerate(text):
                        gp = pos + j
                        if gp >= prog:
                            break
                        x = info_col + gp
                        if x >= cols:
                            break
                        c = ch
                        cc = col
                        if scanned and c != " ":
                            cc = 255          # полоса подсвечивает строку
                        if glitched and c != " " and random.random() < 0.4:
                            c = random.choice(GLITCH_GLYPHS)
                            cc = random.choice([201, 51, 196])
                        if c != " ":
                            canvas[y][x] = c
                            ccolor[y][x] = cc
                            if at:
                                cattr[y][x] = at
                    pos += len(text)

                # бар: растёт от 0 до целевого значения
                if pct is not None and pos + 1 < prog:
                    grow = min(1.0, (prog - pos - 1) / 22.0)
                    fill_pct = (pct or 0) * grow
                    bx = info_col + pos + 1
                    for sym, bcol in _bar_cells(fill_pct, 10):
                        if bx >= cols:
                            break
                        if sym != " ":
                            canvas[y][bx] = sym
                            ccolor[y][bx] = 255 if (scanned and sym == BAR_FILLED) else bcol
                        bx += 1

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
            time.sleep(0.08)

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
    parser = argparse.ArgumentParser(
        prog="flamfetch",
        description="FlamFetch — огненный системный фетч с живой анимацией",
        add_help=True,
    )
    parser.add_argument("--animate", "-a", action="store_true",
                        help="живая анимация логотипа")
    parser.add_argument("--intro", type=float, default=0.0,
                        help="секунд анимации, затем выход (0 = бесконечно)")
    parser.add_argument("--no-logo", action="store_true",
                        help="только системная информация, без логотипа")
    parser.add_argument("--speed", "-s", action="store_true",
                        help="сделать быстрый спидтест (добавляет ~2-8 сек)")
    parser.add_argument("--version", "-V", action="version", version="flamfetch 1.3.0")
    args = parser.parse_args()

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
