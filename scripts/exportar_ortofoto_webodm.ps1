# Exporta ortofotos (y opcionalmente DSM) de tareas completadas de WebODM.
param(
    [int]$ProjectId = 0,
    [int]$TaskId = 0,
    [string]$Destino = "",
    [switch]$AllCompleted,
    [switch]$ListOnly
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_webodm_common.ps1"

if (-not (Test-WebODMOnline)) {
    Write-Host "WebODM no responde. Ejecuta primero iniciar_webodm.ps1" -ForegroundColor Red
    exit 1
}

$cfg = Get-WebODMConfig
$exportRoot = if ($Destino) { $Destino } else { [string]$cfg.exportRoot }
$minSize = [long]$cfg.minExportSizeBytes
$assets = @($cfg.assets)
if (-not $assets -or $assets.Count -eq 0) { $assets = @("orthophoto.tif") }

function Export-TaskAssets {
    param(
        [object]$Project,
        [object]$Task
    )

    if ($Task.status.code -ne 40) {
        Write-Host "  Tarea $($Task.id) omitida (estado $($Task.status.name))" -ForegroundColor DarkYellow
        return $false
    }

    $safeName = ($Project.name -replace '[<>:"/\\|?*]', '_').Trim()
    $outDir = Join-Path $exportRoot $safeName
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null

    $exported = $false
    foreach ($asset in $assets) {
        $outFile = Join-Path $outDir ("{0}_{1}_{2}" -f $safeName, $Task.id, $asset)
        $url = "$($cfg.url)/api/projects/$($Project.id)/tasks/$($Task.id)/download/$asset"
        $token = Get-WebODMToken
        Write-Host "  Descargando $asset -> $outFile"

        try {
            Invoke-WebRequest -Uri $url -Headers @{ Authorization = "JWT $token" } -OutFile $outFile -UseBasicParsing
        } catch {
            Write-Host "  No disponible: $asset ($($_.Exception.Message))" -ForegroundColor DarkYellow
            continue
        }

        $size = (Get-Item $outFile -ErrorAction SilentlyContinue).Length
        if ($size -lt $minSize) {
            Remove-Item $outFile -Force -ErrorAction SilentlyContinue
            Write-Host "  Archivo demasiado pequeno, descartado: $asset" -ForegroundColor DarkYellow
            continue
        }

        Write-Host "  OK $asset ($(Format-Bytes $size))" -ForegroundColor Green
        $exported = $true
    }

    if ($exported) {
        $manifest = Join-Path $outDir ("manifest_{0}.json" -f $Task.id)
        @{
            projectId   = $Project.id
            projectName = $Project.name
            taskId      = $Task.id
            taskName    = $Task.name
            exportedAt  = (Get-Date).ToString("o")
            assets      = $assets
        } | ConvertTo-Json -Depth 4 | Set-Content -Path $manifest -Encoding UTF8
    }

    return $exported
}

$projects = Get-WebODMProjects
if ($ProjectId -gt 0) {
    $projects = @($projects | Where-Object { $_.id -eq $ProjectId })
    if (-not $projects -or $projects.Count -eq 0) {
        throw "Proyecto $ProjectId no encontrado"
    }
}

if ($ListOnly -or ($ProjectId -eq 0 -and -not $AllCompleted)) {
    Write-Host "Proyectos WebODM:" -ForegroundColor Cyan
    foreach ($p in $projects) {
        $tasks = Get-WebODMTasks -ProjectId $p.id
        $done = @($tasks | Where-Object { $_.status.code -eq 40 }).Count
        Write-Host ("- [{0}] {1} | tareas completadas: {2}/{3}" -f $p.id, $p.name, $done, $tasks.Count)
    }
    Write-Host ""
    Write-Host "Ejemplos:"
    Write-Host "  .\exportar_ortofoto_webodm.ps1 -ProjectId 12"
    Write-Host "  .\exportar_ortofoto_webodm.ps1 -AllCompleted"
    exit 0
}

New-Item -ItemType Directory -Force -Path $exportRoot | Out-Null
$count = 0

foreach ($p in $projects) {
    $tasks = Get-WebODMTasks -ProjectId $p.id
    if ($TaskId -gt 0) {
        $tasks = @($tasks | Where-Object { $_.id -eq $TaskId })
    } elseif ($AllCompleted) {
        $tasks = @($tasks | Where-Object { $_.status.code -eq 40 })
    }

    if ($tasks.Count -eq 0) { continue }

    Write-Host "Proyecto [$($p.id)] $($p.name)" -ForegroundColor Cyan
    foreach ($t in $tasks) {
        if (Export-TaskAssets -Project $p -Task $t) { $count++ }
    }
}

Write-Host ""
Write-Host "Exportaciones validas: $count" -ForegroundColor Green
Write-Host "Destino: $exportRoot"
