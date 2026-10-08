param([string]$Action = "stage")
$ErrorActionPreference = "Stop"
$dshmod = [System.IO.Path]::Combine($env:APPDATA, "npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai")
$pkg = "D:\CCXXLESSON\contextledger-host\dsh-seam"
$dst = [System.IO.Path]::Combine($pkg, "node_modules/@deepseek-ai")
$peers = "cordis", "dsh-llm", "dsh-tools", "dsh-agent", "dsh-scope", "schemastery"

if ($Action -eq "stage") {
  [void][System.IO.Directory]::CreateDirectory($dst)
  foreach ($p in $peers) {
    $src = [System.IO.Path]::Combine($dshmod, $p)
    $target = [System.IO.Path]::Combine($dst, $p)
    if (-not [System.IO.Directory]::Exists($src)) { throw "missing source: $src" }
    if ([System.IO.Directory]::Exists($target)) {
      [void][System.IO.Directory]::Delete($target, $true)
    }
    Copy-Item -LiteralPath $src -Destination $target -Recurse -Force
    Write-Output "staged $p"
  }
  $names = [System.IO.Directory]::GetDirectories($dst)
  foreach ($n in $names) { Write-Output ("present {0}", [System.IO.Path]::GetFileName($n)) }
  Write-Output "STAGE_OK"
}
if ($Action -eq "probe") {
  Write-Output ("TLS_REJECT = {0}", $env:NODE_TLS_REJECT_UNAUTHORIZED)
  Write-Output ("NPM_CONFIG_REGISTRY = {0}", $env:NPM_CONFIG_REGISTRY)
  Write-Output "--- npm ping ---"
  & npm ping 2>&1 | Select-Object -Last 6 | ForEach-Object { Write-Output $_ }
  Write-Output ("PING_EXIT = {0}", $LASTEXITCODE)
  $tsc = [System.IO.Path]::Combine($pkg, "node_modules/typescript/bin/tsc")
  Write-Output ("local tsc present: {0}", [System.IO.File]::Exists($tsc))
  $dshTs = [System.IO.Path]::Combine($dshmod, "..", "typescript")
  Write-Output ("dsh-relative typescript dir present: {0}", [System.IO.Directory]::Exists($dshTs))
  Write-Output "PROBE_OK"
}
if ($Action -eq "build") {
  Set-Location -LiteralPath $pkg
  $tscLocal = [System.IO.Path]::Combine($pkg, "node_modules/typescript/bin/tsc")
  if ([System.IO.File]::Exists($tscLocal)) {
    & node $tscLocal -p tsconfig.json
  } else {
    & npx --yes typescript@5.9.2 tsc -p tsconfig.json
  }
  if ($LASTEXITCODE -ne 0) { throw "tsc failed: $LASTEXITCODE" }
  $dist = [System.IO.Path]::Combine($pkg, "dist")
  if ([System.IO.Directory]::Exists($dist)) {
    foreach ($f in [System.IO.Directory]::GetFiles($dist)) { Write-Output ("built {0}", [System.IO.Path]::GetFileName($f)) }
  }
  Write-Output "BUILD_OK"
}
