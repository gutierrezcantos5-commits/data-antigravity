# Limpia proyectos WebODM tras exportar ortofotos para liberar espacio en disco.
param(
    [int]$ProjectId = 0,
    [switch]$AllExported,
    [switch]$Confirm,
    [switch]$ListUsage,
    [switch]$PurgeMedia
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_webodm_common.ps1"

function Test-ProjectExported {
    param(
        [object]$Project,
        [string]$ExportRoot,
        [long]$MinSize
    )

    $safeName = ($Project.name -replace '[<>:"/\\|?*]', '_').Trim()
    $dir = Join-Path $ExportRoot $safeName
    if (-not (Test-Path $dir)) { return $false }

    $ortho = Get-ChildItem $dir -File -Filter "orthophoto*.tif" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $ortho) { return $false }
    return ($ortho.Length -ge $MinSize)
}

function Remove-WebODMProject {
    param([int]$Id)
    Invoke-WebODMApi -Method DELETE -Path "/api/projects/$Id/" | Out-Null
}

$cfg = Get-WebODMConfig
$media = Get-WebODMMediaPath
$exportRoot = [string]$cfg.exportRoot
$minSize = [long]$cfg.minExportSizeBytes

$mediaSize = Get-FolderSize $media
Write-Host "Uso actual media WebODM: $(Format-Bytes $mediaSize) ($media)" -ForegroundColor Cyan

if ($ListUsage -or ($ProjectId -eq 0 -and -not $AllExported -and -not $PurgeMedia)) {
    if (-not (Test-WebODMOnline)) {
        Write-Host "WebODM offline. Solo se muestra uso de disco." -ForegroundColor Yellow
        exit 0
    }

    $projects = Get-WebODMProjects
    Write-Host ""
    Write-Host "Proyectos:" -ForegroundColor Cyan
    foreach ($p in $projects) {
        $exported = Test-ProjectExported -Project $p -ExportRoot $exportRoot -MinSize $minSize
        $flag = if ($exported) { "EXPORTADO" } else { "PENDIENTE" }
        Write-Host ("- [{0}] {1} | {2}" -f $p.id, $p.name, $flag)
    }

    Write-Host ""
    Write-Host "Flujo seguro:"
    Write-Host "  1) .\exportar_ortofoto_webodm.ps1 -ProjectId <id>"
    Write-Host "  2) .\limpiar_webodm.ps1 -ProjectId <id> -Confirm"
    Write-Host "  3) .\limpiar_webodm.ps1 -AllExported -Confirm   (varios proyectos)"
    exit 0
}

if ($PurgeMedia) {
    if (-not $Confirm) {
        Write-Host "PurgeMedia requiere -Confirm. Borrara TODO appmedia." -ForegroundColor Red
        exit 1
    }
    Write-Host "Deteniendo WebODM antes de purgar media..." -ForegroundColor Yellow
    & "$PSScriptRoot\detener_webodm.ps1" | Out-Null
    if (Test-Path $media) {
        Remove-Item $media -Recurse -Force
        New-Item -ItemType Directory -Force -Path $media | Out-Null
    }
    Write-Host "Media purgada. Reinicia con iniciar_webodm.ps1" -ForegroundColor Green
    exit 0
}

if (-not (Test-WebODMOnline)) {
    Write-Host "WebODM no responde. Inicia el servicio o usa -PurgeMedia -Confirm (destructivo)." -ForegroundColor Red
    exit 1
}

$targets = @()
if ($ProjectId -gt 0) {
    $p = Get-WebODMProjects | Where-Object { $_.id -eq $ProjectId } | Select-Object -First 1
    if (-not $p) { throw "Proyecto $ProjectId no encontrado" }
    $targets = @($p)
} elseif ($AllExported) {
    $targets = @(
        Get-WebODMProjects | Where-Object {
            Test-ProjectExported -Project $_ -ExportRoot $exportRoot -MinSize $minSize
        }
    )
} else {
    Write-Host "Indica -ProjectId o -AllExported. Usa -ListUsage para ver estado." -ForegroundColor Yellow
    exit 1
}

if ($targets.Count -eq 0) {
    Write-Host "No hay proyectos exportados listos para borrar." -ForegroundColor Yellow
    exit 0
}

Write-Host "Proyectos a eliminar de WebODM:" -ForegroundColor Yellow
foreach ($p in $targets) {
    Write-Host "  - [$($p.id)] $($p.name)"
}

if (-not $Confirm) {
    Write-Host ""
    Write-Host "Operacion NO ejecutada. Anade -Confirm para borrar." -ForegroundColor Red
    exit 1
}

$removed = 0
foreach ($p in $targets) {
    if (-not (Test-ProjectExported -Project $p -ExportRoot $exportRoot -MinSize $minSize)) {
        Write-Host "Omitido [$($p.id)] $($p.name): no hay ortofoto exportada valida." -ForegroundColor DarkYellow
        continue
    }
    Write-Host "Eliminando [$($p.id)] $($p.name)..." -ForegroundColor Cyan
    Remove-WebODMProject -Id $p.id
    $removed++
}

$newSize = Get-FolderSize $media
Write-Host ""
Write-Host "Proyectos eliminados: $removed" -ForegroundColor Green
Write-Host "Uso media ahora: $(Format-Bytes $newSize) (antes $(Format-Bytes $mediaSize))"
