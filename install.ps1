# FlamFetch - one-click Windows installer
#
# Run in PowerShell:
#   irm https://raw.githubusercontent.com/LOSTFlam/FlamFetch/master/install.ps1 | iex
#
# Steps:
#   1. Detect package manager (winget / scoop / choco)
#   2. Install Python 3 if missing
#   3. Install pyfiglet via pip
#   4. Download flamfetch.py
#   5. Create 'flamfetch' command in PATH
#   6. Run the fetch as a smoke test

$ErrorActionPreference = "Stop"
$Repo  = "https://github.com/LOSTFlam/FlamFetch"
$Raw   = "https://raw.githubusercontent.com/LOSTFlam/FlamFetch/master/flamfetch/flamfetch.py"
$Ver   = "1.8.2"
$BinDir   = Join-Path $env:USERPROFILE ".local\bin"
$ShareDir = Join-Path $env:USERPROFILE ".local\share\flamfetch"

function Write-Step($m) { Write-Host "`n==> $m" -ForegroundColor Cyan }
function Write-Ok($m)   { Write-Host "    $m" -ForegroundColor Green }
function Write-Warn($m) { Write-Host "    $m" -ForegroundColor Yellow }
function Write-Err($m)  { Write-Host "    $m" -ForegroundColor Red }

Write-Host ""
Write-Host "   ____  _                       _____   _         _       " -ForegroundColor Red
Write-Host "  / ___|| | __ _ _ __ ___   __ _|  ___| | |_ _   _| |__    " -ForegroundColor Red
Write-Host " | |  _ | |/ _`` | '_ `` _ \ / _`` | |_    | __| | | | '_ \   " -ForegroundColor Red
Write-Host " | |_| || | (_| | | | | | | (_| |  _|   | |_| |_| | |_) |  " -ForegroundColor Red
Write-Host "  \____||_|\__,_|_| |_| |_|\__,_|_|      \__|\__,_|_.__/   " -ForegroundColor Red
Write-Host ""
Write-Host "  FlamFetch Windows installer v$Ver" -ForegroundColor DarkRed
Write-Host ""

# ---------- 1. package manager ----------
Write-Step "Looking for a package manager..."

$PM = $null
if (Get-Command winget -ErrorAction SilentlyContinue) {
    $PM = "winget"; Write-Ok "found winget"
} elseif (Get-Command scoop -ErrorAction SilentlyContinue) {
    $PM = "scoop"; Write-Ok "found scoop"
} elseif (Get-Command choco -ErrorAction SilentlyContinue) {
    $PM = "choco"; Write-Ok "found choco"
}

if (-not $PM) {
    Write-Warn "no package manager found"
    Write-Host ""
    Write-Host "  winget ships with Windows 10/11 as 'App Installer'."
    Write-Host "  Install it from Microsoft Store:"
    Write-Host "    https://apps.microsoft.com/detail/9nblggh4nns1" -ForegroundColor Yellow
    Write-Host ""
    $ans = Read-Host "  Open Microsoft Store now? [Y/n]"
    if ($ans -notmatch '^[Nn]') {
        try {
            Start-Process "ms-windows-store://pdp/?ProductId=9nblggh4nns1"
            Write-Warn "press 'Install' in the Store, close it, then press Enter here"
            Read-Host "  Press Enter when done"
            if (Get-Command winget -ErrorAction SilentlyContinue) {
                $PM = "winget"; Write-Ok "winget is ready"
            } else {
                Write-Warn "winget still not found - continuing without it"
            }
        } catch {
            Write-Warn "could not open the Store: $_"
        }
    }
}

# ---------- 2. python ----------
Write-Step "Checking for Python..."

$py = $null
foreach ($c in @("python", "python3", "py")) {
    if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; break }
}

if (-not $py) {
    if ($PM -eq "winget") {
        Write-Step "Installing Python 3 via winget..."
        winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
    } elseif ($PM -eq "scoop") {
        Write-Step "Installing Python 3 via scoop..."
        scoop install python
    } elseif ($PM -eq "choco") {
        Write-Step "Installing Python 3 via choco..."
        choco install python -y
    } else {
        Write-Err "no package manager to install Python with."
        Write-Host "    Install Python manually: https://www.python.org/downloads/" -ForegroundColor Yellow
        Write-Host "    (make sure 'Add python.exe to PATH' is checked)" -ForegroundColor Yellow
        exit 1
    }
    # refresh PATH for this session
    $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path","User")
    foreach ($c in @("python", "python3", "py")) {
        if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; break }
    }
}

if (-not $py) {
    Write-Err "Python still not found. Restart your terminal and re-run:"
    Write-Host "    irm https://raw.githubusercontent.com/LOSTFlam/FlamFetch/master/install.ps1 | iex" -ForegroundColor Yellow
    Write-Host "    or install Python: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

$pyVer = & $py --version 2>&1
Write-Ok "Python: $pyVer"

# ---------- 3. pyfiglet ----------
Write-Step "Checking pyfiglet..."

& $py -c "import pyfiglet" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Step "Installing pyfiglet via pip..."
    & $py -m pip install --user pyfiglet 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        & $py -m pip install pyfiglet 2>&1 | Out-Null
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Err "could not install pyfiglet. Try manually:"
        Write-Host "    $py -m pip install pyfiglet" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Ok "pyfiglet already installed"
}

# ---------- 4. download ----------
Write-Step "Downloading FlamFetch v$Ver..."

New-Item -ItemType Directory -Force -Path $ShareDir | Out-Null
New-Item -ItemType Directory -Force -Path $BinDir   | Out-Null

$target = Join-Path $ShareDir "flamfetch.py"
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $Raw -OutFile $target -UseBasicParsing
    Write-Ok "saved to $target"
} catch {
    Write-Err "download failed: $_"
    Write-Host "    download manually: $Raw" -ForegroundColor Yellow
    exit 1
}

# ---------- 5. command ----------
Write-Step "Creating the 'flamfetch' command..."

# .cmd wrapper (works in cmd, PowerShell, Windows Terminal)
$cmdPath = Join-Path $BinDir "flamfetch.cmd"
$cmdLines = @(
    '@echo off',
    'REM FlamFetch - fiery animated system fetch',
    'where python >nul 2>nul',
    'if errorlevel 1 (',
    '    echo FlamFetch: Python not found. Install it from https://python.org',
    '    exit /b 1',
    ')',
    ('python "' + $target + '" %*')
)
Set-Content -Path $cmdPath -Value $cmdLines -Encoding ASCII

# .ps1 wrapper for PowerShell
$ps1Path = Join-Path $BinDir "flamfetch.ps1"
Set-Content -Path $ps1Path -Value ('python "' + $target + '" @args') -Encoding UTF8

# add to user PATH if needed
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not $userPath) { $userPath = "" }
if ($userPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", ($userPath.TrimEnd(';') + ';' + $BinDir), "User")
    Write-Ok "added to your PATH"
} else {
    Write-Ok "already in PATH"
}
$env:Path += ";$BinDir"

# ---------- 6. smoke test ----------
Write-Step "Verifying..."

Write-Ok "command ready: flamfetch"
Write-Host ""
Write-Host "  +-------------------------------------------------+" -ForegroundColor DarkGray
Write-Host "  |  Open a NEW terminal and run:                    |" -ForegroundColor DarkGray
Write-Host "  |                                                 |" -ForegroundColor DarkGray
Write-Host "  |    flamfetch            (standard fetch)         |" -ForegroundColor White
Write-Host "  |    flamfetch --animate  (live animation)         |" -ForegroundColor White
Write-Host "  |    flamfetch --lang ru  (Russian interface)      |" -ForegroundColor White
Write-Host "  +-------------------------------------------------+" -ForegroundColor DarkGray
Write-Host ""

Write-Step "First run..."
try {
    & $py $target --no-logo
} catch {
    Write-Warn "auto-run failed - just open a new terminal and type 'flamfetch'"
}

Write-Host ""
Write-Host "  FlamFetch is installed. Enjoy! (one-click installer)" -ForegroundColor Red
Write-Host ""
