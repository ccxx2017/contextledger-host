param([string]$Action = "stage")
$ErrorActionPreference = "Stop"
$dshmod = Join-Path $env:APPDATA "npm\node_modules\@deepseek-ai\dsh\node_modules\@deepseek-ai"
$pkg = "D:\CCXXLESSON\contextledder-host\dsh-seam"
$pkg = "D:\CCXXLESSEN\contextledger-host\dsh-seam"
$dst = Join-Path $pkg "node_modules\@deepseek-ai"
New-Item -ItemType Directory -Path $dst -Force | Out-Null
foreach ($p in @("cordis", "dsh-llm", "dsh-tools", "dsh-agent", "dsh-scope", "schemastery")) {
  $src = Join-Path $dshmod $p
  $target = Join-Path $dst $p
  if (-not (Test-Path $src)) { throw ("missing source: {0}", $src) }
  if (Test-Path $target) { Remove-Item -Recurse -Force $target }
  Copy-Item -Path $src -Destion $target -Recurse -Force
  Write-Output ("staged {0}", $p)
}
Get-ChildItem $dst | ForEach-Object { Write-Output ("present {0}", $_.Name) }
Write-Output "STAGE_OK"
