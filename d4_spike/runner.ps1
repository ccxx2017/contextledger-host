# 通用 runner：把任意 action 的执行输出落盘，规避 stdout 通道异常。
param([string]$Action = "probe")
$base = $PSScriptRoot
$log = [System.IO.Path]::Combine($base, "runner_last.log")
$out = & ([System.IO.Path]::Combine($base, "install_seam.ps1")) -Action $Action 2>&1
$text = ($out | ForEach-Object { $_.ToString() }) -join "`n"
[System.IO.File]::WriteAllText($log, "ACTION=$Action`nEXIT=$LASTEXITCODE`n----`n$text`n")
Write-Output ("wrote {0}", $log)
