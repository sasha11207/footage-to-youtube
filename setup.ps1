# One-time setup for Windows 10 / 11. Everything goes INSIDE this project folder:
#   .venv\      Python environment used by the scripts
#   .tools\     uv + Python (only if this computer has no Python 3.9+), ffmpeg (only if needed)
# Nothing is installed system-wide, no settings are changed, no admin rights are needed.
# To remove everything: delete the project folder.
#
# Run it like this (the Bypass applies only to this one run, it changes no settings):
#   powershell -ExecutionPolicy Bypass -File setup.ps1          show what would be downloaded
#   powershell -ExecutionPolicy Bypass -File setup.ps1 -Yes     do it
param([switch]$Yes)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Set-Location -LiteralPath $PSScriptRoot
$Here = (Get-Location).Path

$arch = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "aarch64" } else { "x86_64" }

# --- 1. Python: use one that is already here (read-only), else a private copy in .tools\ ---
function Test-Py($cmd, $argList) {
    try {
        $out = & $cmd @argList -c "import sys, venv; print(sys.executable) if sys.version_info >= (3, 9) else None" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out -and (Test-Path -LiteralPath "$out")) { return "$out" }
    } catch {}
    return $null
}
$pybase = $null
if (Test-Path ".venv\Scripts\python.exe") { $pybase = "(existing .venv)" }
else {
    # 'python' may be the Microsoft Store shortcut that only opens the Store: Test-Py rejects it.
    foreach ($s in @("py -3", "python", "python3")) {
        $parts = $s.Split(" ")
        $name = $parts[0]
        $extra = @($parts | Select-Object -Skip 1)
        if (Get-Command $name -ErrorAction SilentlyContinue) {
            $r = Test-Py $name $extra
            if ($r) { $pybase = $r; break }
        }
    }
}

# --- 2. ffmpeg: the system one is fine if it has the filters we need, else a private copy ---
$ffOk = $false
if ((Test-Path ".tools\ffmpeg\ffmpeg.exe") -and (Test-Path ".tools\ffmpeg\ffprobe.exe")) { $ffOk = $true }
elseif ((Get-Command ffmpeg -ErrorAction SilentlyContinue) -and (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    $f = (& ffmpeg -hide_banner -filters 2>$null) -join "`n"
    if ($f -match " zscale " -and $f -match " xfade ") { $ffOk = $true }
}

Write-Host "Setup plan for this folder: $Here"
if ($pybase) { Write-Host "  Python : use $pybase  (nothing to download)" }
else { Write-Host "  Python : download uv (~20 MB, github.com/astral-sh/uv) and Python 3.12 (~30 MB) into .tools\" }
if ($ffOk) { Write-Host "  ffmpeg : already OK  (nothing to download)" }
else { Write-Host "  ffmpeg : download ffmpeg essentials build (~115 MB, gyan.dev, linked from ffmpeg.org) into .tools\ffmpeg\" }
Write-Host "  Then   : create .venv and run the computer check (scripts\doctor.py)"
if (-not $Yes) { Write-Host ""; Write-Host "Nothing changed. Run again with -Yes to do this."; exit 0 }

New-Item -ItemType Directory -Force -Path ".tools" | Out-Null
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    if ($pybase) {
        & $pybase -m venv .venv
    } else {
        Write-Host "Downloading uv ..."
        New-Item -ItemType Directory -Force -Path ".tools\uv" | Out-Null
        $zip = ".tools\uv.zip"
        Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/astral-sh/uv/releases/latest/download/uv-$arch-pc-windows-msvc.zip" -OutFile $zip
        Expand-Archive -LiteralPath $zip -DestinationPath ".tools\uv" -Force
        Remove-Item -LiteralPath $zip
        $env:UV_PYTHON_INSTALL_DIR = "$Here\.tools\python"
        $env:UV_CACHE_DIR = "$Here\.tools\uv-cache"
        $env:UV_NO_CONFIG = "1"
        & ".tools\uv\uv.exe" python install 3.12
        & ".tools\uv\uv.exe" venv .venv --python 3.12
    }
}
$Py = "$Here\.venv\Scripts\python.exe"
& $Py -c "import sys; print('Python ready:', sys.version.split()[0], sys.executable)"

if (-not $ffOk) { & $Py scripts\get_ffmpeg.py --yes }

Write-Host ""
& $Py scripts\doctor.py
Write-Host ""
Write-Host "Done. Run the scripts with: .venv\Scripts\python.exe scripts\<name>.py"
