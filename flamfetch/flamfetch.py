#!/usr/bin/env python3
"""FlamFetch — огненный системный фетч с живой анимацией.

Вдохновлён fastfetch + neofetch, но с душой:
- Слева:  анимированный логотип Flam/quency (пламя + глитч)
- Справа: системная информация, разбитая по цветным разделам
           Hardware / Software / Storage / Network

Зависимости: Python 3.8+, pyfiglet. Всё остальное — stdlib.

Использование:
    flamfetch                  обычный фетч (статичный логотип)
    flamfetch --animate        фетч с живой анимацией
    flamfetch --animate --intro 4   проиграть 4 сек и выйти
    flamfetch --no-logo        только системная информация
    flamfetch --help           помощь
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


def truecolor(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


# Цвета разделов (по важности)
COLOR_HEADER = 196      # красный — заголовки разделов
COLOR_KEY = 208         # оранжевый — ключи
COLOR_VALUE = 255       # белый — значения
COLOR_ACCENT = 141      # фиолетовый — акценты
COLOR_DIM = 245         # серый — второстепенное


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
            # короткое имя модели
            for junk in ("CPU", "Processor", "(R)", "(TM)", "with Radeon Graphics"):
                model = model.replace(junk, "")
            model = " ".join(model.split())
            return f"{model} ({cores})"
    return platform.processor() or "?"


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
    # fallback через hyprctl
    out = _run(["hyprctl", "monitors"])
    if out:
        import re
        for line in out.splitlines():
            m = re.search(r"(\d{3,4}x\d{3,4})", line)
            if m:
                return m.group(1)
    return None


def get_de() -> str:
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return "Hyprland (Wayland)"
    if os.environ.get("WAYLAND_DISPLAY"):
        return "Wayland"
    return "TTY"


def get_shell() -> str:
    sh = os.environ.get("SHELL", "")
    return Path(sh).name if sh else "?"


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
            # берём имя после ': '
            name = line.split(": ", 1)[-1].strip()
            # чистим от мусора
            for junk in ("(rev a1)", "(rev c6)", "Corporation", "Advanced Micro Devices, Inc."):
                name = name.replace(junk, "")
            name = " ".join(name.split())
            # короткое имя
            name = name.replace("[AMD/ATI]", "").strip()
            if name:
                gpus.append(name)
    return gpus


def get_temps() -> dict[str, float]:
    """Температуры CPU/GPU в °C."""
    temps = {}
    # k10temp (AMD)
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
    # fallback через sysfs
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


def get_terminal() -> str:
    term = os.environ.get("TERM_PROGRAM", "")
    if term:
        return term
    # fallback по процессу
    try:
        ppid = os.getppid()
        comm = _read(f"/proc/{ppid}/comm")
        if comm:
            return comm
    except Exception:
        pass
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


# ---------------------------------------------------------------- прогресс-бары

BAR_FILLED = "━"      # ━
BAR_EMPTY = "─"       # ─


def bar(pct: float, width: int = 10) -> str:
    """Прогресс-бар с цветом по загрузке: зелёный/жёлтый/красный."""
    pct = max(0.0, min(100.0, pct))
    filled = int(pct / 100 * width)
    bar_str = BAR_FILLED * filled + BAR_EMPTY * (width - filled)
    # цвет по загрузке
    if pct < 50:
        color = 78      # зелёный
    elif pct < 80:
        color = 220     # жёлтый
    else:
        color = 196     # красный
    return fg(color) + bar_str + RESET


def uptime_bar(seconds: float, max_days: float = 7.0, width: int = 10) -> str:
    """Бар uptime: сколько от максимума (7 дней) отработала система."""
    pct = min(100.0, seconds / (max_days * 86400) * 100)
    filled = int(pct / 100 * width)
    if filled == 0 and pct > 0:
        filled = 1          # минимум 1 клетка если система работает
    bar_str = BAR_FILLED * filled + BAR_EMPTY * (width - filled)
    # цвет: молодой uptime = зелёный, старый = жёлтый/красный
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
        # пропускаем loopback и неактивные
        if name == "lo" or status not in ("UP", "UNKNOWN"):
            continue
        # UNKNOWN с IP = активен (типично для tun)
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
    """Быстрый спидтест: скачивает 10MB с Cloudflare, возвращает (Mbps, сек).
    Возвращает None при ошибке/таймауте."""
    import time
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
    """(used, total) swap в GiB или None если нет."""
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
    """Load average (1/5/15 мин) из /proc/loadavg."""
    raw = _read("/proc/loadavg")
    if not raw:
        return "?"
    parts = raw.split()
    return f"{parts[0]} {parts[1]} {parts[2]}"


def get_processes() -> int:
    """Число запущенных процессов."""
    try:
        return len([d for d in os.listdir("/proc") if d.isdigit()])
    except Exception:
        return 0


def get_parent_process() -> str:
    """Родительский процесс (чем запущен flamfetch)."""
    try:
        ppid = os.getppid()
        comm = _read(f"/proc/{ppid}/comm")
        return comm or "?"
    except Exception:
        return "?"


# ============================================================ разделы

def _parse_mem() -> tuple[float, float, float]:
    """(used, total, pct) в GiB."""
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
    """(used, total, pct) в GiB."""
    try:
        usage = shutil.disk_usage(path)
        total = usage.total / 1024 ** 3
        used = usage.used / 1024 ** 3
        pct = 100 * used / total if total else 0.0
        return used, total, pct
    except Exception:
        return 0.0, 0.0, 0.0


def _parse_battery() -> tuple[int, str] | None:
    """(percent, status) или None."""
    for b in Path("/sys/class/power_supply").glob("BAT*"):
        cap = _read(str(b / "capacity"))
        status = _read(str(b / "status")) or ""
        if cap:
            try:
                return int(cap), status
            except ValueError:
                return None
    return None


def build_sections(with_speed: bool = False) -> list[tuple[str, list[tuple[str, str]]]]:
    """Возвращает [(заголовок, [(ключ, значение), ...]), ...]
    with_speed=True — делает спидтест (медленно, ~2-8 сек)."""
    host, os_name = get_host()
    icon = get_distro_icon()

    # температура CPU
    temps = get_temps()
    cpu_temp = None
    for label, val in temps.items():
        if any(x in label.lower() for x in ("tctl", "cpu", "core", "k10temp", "temp1")):
            cpu_temp = val
            break
    if cpu_temp is None and temps:
        cpu_temp = next(iter(temps.values()))

    # батарея
    bat = _parse_battery()
    # память / диск
    mu, mt, mpct = _parse_mem()
    du, dt, dpct = _parse_disk("/")
    # uptime
    up_sec = get_uptime_seconds()

    # ===== сеть =====
    ifaces = get_interfaces()
    vpns = get_vpn_interfaces()
    ext = get_external_info()
    speed = get_speed() if with_speed else None

    sections = [
        ("◈ Система", [
            ("OS", f"{icon} {os_name}"),
            ("Host", host),
            ("Kernel", get_kernel()),
            ("Uptime", f"{get_uptime()} {uptime_bar(up_sec)}"),
        ]),
        ("◈ Оборудование", [
            ("CPU", get_cpu()),
            ("GPU", get_gpu()[0] if get_gpu() else "?"),
            ("DE", get_de()),
            ("Terminal", get_terminal()),
            ("Shell", get_shell()),
            ("Launched", get_parent_process()),
        ]),
        ("◈ Ресурсы", [
            ("Memory", f"{mu:.1f}/{mt:.1f}GiB {bar(mpct)}"),
            ("Disk /", f"{du:.0f}/{dt:.0f}GiB {bar(dpct)}"),
        ]),
    ]

    # опциональные — оборудование
    res = get_resolution()
    if res:
        sections[1][1].append(("Display", res))
    if len(get_gpu()) > 1:
        sections[1][1].append(("GPU2", get_gpu()[1]))
    if cpu_temp is not None:
        sections[1][1].append(("Temp", f"{cpu_temp:.0f}°C"))

    # ===== раздел Сеть =====
    net_items = []
    # активные интерфейсы
    for name, status, ip in ifaces:
        if name in vpns:
            continue  # VPN покажем отдельно
        tag = "VPN" if any(v in name for v in vpns) else name
        ip_short = ip.split("/")[0] if ip else "-"
        net_items.append(("Iface", f"{tag} ({ip_short})"))
    # VPN-статус
    if vpns:
        vpn_name = vpns[0]
        if ext:
            net_items.append(("VPN", f"✓ {vpn_name} → {ext['country']} ({ext['city']})"))
        else:
            net_items.append(("VPN", f"✓ {vpn_name}"))
        # подсказка что WAN через VPN
        net_items.append(("Note", "WAN IP / страна — через VPN"))
    else:
        if ext:
            net_items.append(("VPN", f"✗ off → {ext['country']} ({ext['city']})"))
    # внешний IP
    if ext:
        net_items.append(("WAN IP", ext["ip"]))
    # скорость
    if speed:
        mbps, elapsed = speed
        net_items.append(("Speed", f"↓ {mbps:.0f} Mbps ({elapsed:.1f}s)"))
    elif with_speed:
        net_items.append(("Speed", "недоступен"))

    if net_items:
        sections.append(("◈ Сеть", net_items))

    # батарея, IP, пакеты — в Ресурсы
    if bat:
        pct, status = bat
        icon_b = "⚡" if status == "Charging" else "🔋"
        sections[2][1].append(("Battery", f"{pct}% {icon_b} {bar(pct)}"))
    pkgs = get_packages()
    if pkgs != "?":
        sections[2][1].append(("Packages", pkgs))
    # swap
    swap = get_swap()
    if swap:
        su, st = swap
        spct = 100 * su / st if st else 0
        sections[2][1].append(("Swap", f"{su:.1f}/{st:.1f}GiB {bar(spct)}"))
    # load + процессы
    sections[2][1].append(("Load", get_load()))
    procs = get_processes()
    if procs:
        sections[2][1].append(("Processes", str(procs)))

    # ===== раздел Сборка =====
    binfo = get_build_info()
    build_items = [
        ("OS ID", binfo["id"]),
        ("Version", binfo["version"]),
        ("Build", binfo["build_id"]),
    ]
    sections.append(("◈ Сборка", build_items))

    return sections


# ============================================================ рендер (статика)

def render_static(with_speed: bool = False) -> None:
    """Отрисовывает логотип + инфу, выходит."""
    art = get_art()
    sections = build_sections(with_speed=with_speed)
    user = os.environ.get("USER", "user")
    host = socket.gethostname()

    # рисуем арт с огненным градиентом
    art_lines = []
    for ri, line in enumerate(art):
        t = ri / max(len(art) - 1, 1)
        ct = 0.35 + 0.65 * (1.0 - t)
        art_lines.append(fg(fire_color(ct)) + line)

    # заголовок user@host под артом
    art_lines.append("")
    art_lines.append(fg(196) + BOLD + " " * 2 + user + RESET
                     + fg(208) + "@" + RESET
                     + fg(226) + BOLD + host + RESET)

    # подпись
    art_lines.append("")
    art_lines.append(fg(fire_color(0.3)) + " " * 6 + "by lostflam")

    # инфо-блок
    info_lines = []
    info_lines.append("")
    for title, items in sections:
        info_lines.append(fg(COLOR_HEADER) + BOLD + f"  {title}" + RESET)
        for k, v in items:
            info_lines.append(
                fg(COLOR_KEY) + f"  {k:<11}" + RESET
                + fg(COLOR_DIM) + "│ " + RESET
                + fg(COLOR_VALUE) + v
            )
        info_lines.append("")

    # склеиваем арт и инфу рядом
    total = max(len(art_lines), len(info_lines))
    # ширина арта для выравнивания
    art_w = max((len(l) for l in art_lines), default=0)
    # убираем ANSI при подсчёте — грубая оценка по видимому тексту
    def visible_len(s):
        import re
        return len(re.sub(r"\033\[[0-9;]*m", "", s))

    art_w = max(visible_len(l) for l in art_lines)

    for i in range(total):
        left = art_lines[i] if i < len(art_lines) else ""
        right = info_lines[i] if i < len(info_lines) else ""
        pad = " " * max(0, art_w - visible_len(left) + 4)
        # добиваем цвет, чтобы не течёк на инфу
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


def render_animated(intro: float = 0.0, with_speed: bool = False) -> None:
    art = get_art()
    flam = art[:5]
    quency = art[7:]
    art_h = len(art)

    try:
        cols, rows = os.get_terminal_size()
    except OSError:
        cols, rows = 120, 30

    need = art_h + 9
    if rows < need:
        if intro:
            rows = need
        else:
            print(f"Терминал мал: нужно ~{need} строк, есть {rows}.")
            return

    particles = []
    frame = 0
    start = time.monotonic()
    max_frames = int(intro / 0.08) + 4 if intro else 0
    deadline = start + intro + 0.5 if intro else None

    flam_rows = list(range(2, 2 + len(flam)))
    quency_rows = list(range(2 + len(flam) + 1, 2 + len(flam) + 1 + len(quency)))

    # ===== собираем инфо-блок один раз =====
    sections = build_sections(with_speed=with_speed)
    info_text = []
    for title, items in sections:
        info_text.append((None, None, f"{title}", "header"))
        for k, v in items:
            info_text.append((k, v, None, "kv"))
        info_text.append((None, None, "", "blank"))

    # ===== статичная ширина колонки арта =====
    art_w = max(len(l) for l in art)
    info_col = art_w + 6          # отступ между артом и инфой

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
                        # пользователь красный, @ оранжевый, хост жёлтый
                        if i < len(user):
                            ccolor[ty][tx + i] = 196
                        elif ch == "@":
                            ccolor[ty][tx + i] = 208
                        else:
                            ccolor[ty][tx + i] = 226

            # ===== инфо-блок: кладём в canvas справа =====
            info_y = 2
            for kind_key, kind_val, title, kind in info_text:
                if info_y >= rows:
                    break
                if kind == "header":
                    # заголовок раздела
                    line = f"{title}"
                    for i, ch in enumerate(line):
                        if info_col + i < cols:
                            canvas[info_y][info_col + i] = ch
                            ccolor[info_y][info_col + i] = COLOR_HEADER
                            cattr[info_y][info_col + i] = BOLD
                elif kind == "kv":
                    key = (kind_key or "")[:11].ljust(11)
                    line = f"{key}│ {kind_val}"
                    for i, ch in enumerate(line):
                        if info_col + i < cols:
                            c = ch
                            col = 0
                            if i < 11:
                                col = COLOR_KEY
                            elif i == 11:
                                col = COLOR_DIM
                            else:
                                col = COLOR_VALUE
                            if c != " ":
                                canvas[info_y][info_col + i] = c
                                ccolor[info_y][info_col + i] = col
                info_y += 1

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
    args = parser.parse_args()

    if args.no_logo:
        sections = build_sections(with_speed=args.speed)
        for title, items in sections:
            print(fg(COLOR_HEADER) + BOLD + title + RESET)
            for k, v in items:
                print(fg(COLOR_KEY) + f"{k:<12}" + RESET
                      + fg(COLOR_DIM) + "│ " + RESET
                      + fg(COLOR_VALUE) + v)
            print()
        return

    if args.animate:
        render_animated(args.intro, with_speed=args.speed)
    else:
        render_static(with_speed=args.speed)


if __name__ == "__main__":
    main()
