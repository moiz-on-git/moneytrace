# Registers the daily Money Trace run with Windows Task Scheduler.
# Tue-Sat at 07:30 local, which is after the 16:00 ET US close, so it covers Mon-Fri sessions.
# Remove with:  Unregister-ScheduledTask -TaskName "Money Trace Daily" -Confirm:$false

$ErrorActionPreference = "Stop"
$taskName = "Money Trace Daily"
$runner = Join-Path $PSScriptRoot "run_daily.ps1"

if (-not (Test-Path $runner)) { throw "run_daily.ps1 not found next to this script" }

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$runner`"" `
    -WorkingDirectory (Split-Path -Parent $PSScriptRoot)

$trigger = New-ScheduledTaskTrigger -Weekly `
    -DaysOfWeek Tuesday, Wednesday, Thursday, Friday, Saturday -At 7:30am

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "Daily money-flow brief: where capital moved, who drove it, what to watch." -Force | Out-Null

Write-Host "Registered '$taskName' for Tue-Sat 07:30."
Write-Host "Test it now:  Start-ScheduledTask -TaskName '$taskName'"
Write-Host "Remove it:    Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false"
