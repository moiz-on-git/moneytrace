# Runs the daily Money Trace brief and stores a timestamped log.
# Used by Windows Task Scheduler (see register_task.ps1) or run by hand.

param([switch]$NoAi)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$log = Join-Path $logDir "run_$stamp.log"

$python = if (Get-Command python -ErrorAction SilentlyContinue) { (Get-Command python).Source } else { "python" }
$args = @("-m", "moneytrace", "run", "--max-age-hours", "6")
if ($NoAi) { $args += "--no-ai" }

"[$stamp] starting: $python $($args -join ' ')" | Out-File -FilePath $log -Encoding utf8
& $python @args *>&1 | Out-File -FilePath $log -Append -Encoding utf8
$code = $LASTEXITCODE
"[$stamp] exit=$code" | Out-File -FilePath $log -Append -Encoding utf8

# keep the last 60 logs only
Get-ChildItem $logDir -Filter "run_*.log" | Sort-Object LastWriteTime -Descending |
    Select-Object -Skip 60 | Remove-Item -Force -ErrorAction SilentlyContinue

exit $code
