$ErrorActionPreference = "Continue"
Write-Output ("=== env probe ===")
Write-Output ("TLS_REJECT = {0}", $env:NODE_TLS_REJECT_UNAUTHORIZED)
Write-Output ("NPM_CONFIG_REGISTRY = {0}", $env:NPM_CONFIG_REGISTRY)
Write-Output "--- npm ping ---"
& npm ping 2>&1 | Select-Object -Last 6 | ForEach-Object { Write-Output $_ }
Write-Output ("PING_EXIT = {0}", $LASTEXITCODE)
