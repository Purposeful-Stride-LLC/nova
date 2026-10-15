# start_daemon_only.ps1 - NOVA 2.1 daemon autostart (daemon ONLY: no GUI, no TUI, no nova.launch)
# Invoked by scheduled task "NOVA Daemon" (at logon, 60s delay):
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "<kit>\bin\start_daemon_only.ps1"
# Data home: <kit>\NOVA_HOME.txt (path relative to the kit), else the kit itself. Log: <home>\data\daemon_autostart.log
# Refuses in a STAGED kit. Duplicate guard: any "python -m nova" process -> SKIP.
$ErrorActionPreference = 'Stop'
$Kit = Split-Path -Parent $PSScriptRoot
$HomeDir = $Kit
$ptr = Join-Path $Kit 'NOVA_HOME.txt'
if (Test-Path -LiteralPath $ptr) { $HomeDir = (Resolve-Path -LiteralPath (Join-Path $Kit ((Get-Content -LiteralPath $ptr -Raw).Trim()))).Path }
$HomeDp0 = $HomeDir.TrimEnd('\') + '\'
$KitDp0  = $Kit.TrimEnd('\') + '\'
$Python = if ($env:NOVA_PYTHON) { $env:NOVA_PYTHON } else { (Get-Command python.exe -ErrorAction Stop).Source }
$Log = Join-Path $HomeDir 'data\daemon_autostart.log'
function Write-Log([string]$msg) { Add-Content -LiteralPath $Log -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') CT] $msg" -Encoding ASCII }
try {
    if (Test-Path -LiteralPath (Join-Path $Kit 'STAGED')) { Write-Log "REFUSE STAGED kit=$Kit"; exit 3 }
    $existing = @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
        Where-Object { $_.CommandLine -match '(?i)pythonw?(\.exe)?"?\s+-m\s+nova\s*$' })
    if ($existing.Count -gt 0) { Write-Log "SKIP daemon already running pid=$(($existing | % ProcessId) -join ',') kit=$Kit"; exit 0 }
    $env:PYTHONPATH = $KitDp0
    $env:NOVA_HOME  = $HomeDp0
    $env:NOVA_FAST  = '1'
    Set-Location -LiteralPath $Kit
    $p = Start-Process -FilePath $Python -ArgumentList '-m','nova' -WorkingDirectory $Kit -WindowStyle Hidden -PassThru
    Write-Log "START python -m nova pid=$($p.Id) kit=$Kit home=$HomeDp0 NOVA_FAST=1 (user=$env:USERNAME)"
    exit 0
}
catch { Write-Log "ERROR $($_.Exception.Message)"; exit 1 }
