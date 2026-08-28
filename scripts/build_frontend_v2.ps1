param(
  [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
  [switch]$SwitchStatic
)

$ErrorActionPreference = "Stop"
$v2 = Join-Path $ProjectRoot "frontend-v2"
$dist = Join-Path $v2 "dist"
$target = Join-Path $ProjectRoot "frontend\dist"
$legacy = Join-Path $ProjectRoot "frontend\dist-vue-legacy"

if (-not (Test-Path (Join-Path $v2 "package.json"))) { throw "frontend-v2/package.json not found" }
Push-Location $v2
try {
  npm.cmd ci --no-audit --no-fund
  npm.cmd run build
} finally { Pop-Location }

if (-not (Test-Path (Join-Path $dist "index.html"))) { throw "frontend-v2 build did not produce dist/index.html" }

if ($SwitchStatic) {
  if (Test-Path $legacy) { Remove-Item -LiteralPath $legacy -Recurse -Force }
  if (Test-Path $target) { Copy-Item -LiteralPath $target -Destination $legacy -Recurse }
  if (Test-Path $target) { Remove-Item -LiteralPath $target -Recurse -Force }
  Copy-Item -LiteralPath $dist -Destination $target -Recurse
  Write-Output "Switched frontend/dist to frontend-v2/dist"
  Write-Output "Legacy Vue build preserved at frontend/dist-vue-legacy"
} else {
  Write-Output "Build completed; static directory was not changed"
}
