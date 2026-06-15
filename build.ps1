# Student System Frontend - PowerShell Build Script
# Copies static/ contents to dist/

$src = "static"
$dst = "dist"

if (Test-Path $dst) {
    Remove-Item $dst -Recurse -Force
}
New-Item -ItemType Directory -Path $dst | Out-Null

$srcFull = (Resolve-Path $src).Path
Get-ChildItem -Path $srcFull -Recurse | ForEach-Object {
    $relPath = $_.FullName.Substring($srcFull.Length)
    $targetPath = Join-Path $dst $relPath
    if ($_.PSIsContainer) {
        if (-not (Test-Path $targetPath)) {
            New-Item -ItemType Directory -Path $targetPath -Force | Out-Null
        }
    } else {
        $targetDir = Split-Path $targetPath -Parent
        if (-not (Test-Path $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }
        Copy-Item -Path $_.FullName -Destination $targetPath -Force
    }
}

Write-Host ""
Write-Host "[build] dist contents:" -ForegroundColor Green
Get-ChildItem $dst | ForEach-Object { Write-Host "  $($_.Name)" }
Write-Host ""
Write-Host "[build] Verify css/js:" -ForegroundColor Green
if (Test-Path "dist\css\style.css") { Write-Host "  [OK] dist\css\style.css" -ForegroundColor Green } else { Write-Host "  [MISSING] dist\css\style.css" -ForegroundColor Red }
if (Test-Path "dist\js\api.js") { Write-Host "  [OK] dist\js\api.js" -ForegroundColor Green } else { Write-Host "  [MISSING] dist\js\api.js" -ForegroundColor Red }
Write-Host ""
Write-Host "[build] Done" -ForegroundColor Green
