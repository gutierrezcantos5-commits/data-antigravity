# Detiene contenedores WebODM (Docker Compose down).
param([switch]$KeepData)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_webodm_common.ps1"

if (-not (Test-DockerReady)) {
    Write-Host "Docker no esta en ejecucion. Nada que detener."
    exit 0
}

$down = Get-WebODMComposeDownArgs
Write-Host "Deteniendo WebODM..." -ForegroundColor Cyan

Push-Location $down.Root
try {
    & docker @($down.Args)
    if ($LASTEXITCODE -ne 0) { throw "docker compose down fallo con codigo $LASTEXITCODE" }
} finally {
    Pop-Location
}

if (-not $KeepData) {
    Write-Host "Datos conservados en:"
    Write-Host "  Media: $(Get-WebODMMediaPath)"
    Write-Host "Para liberar espacio tras exportar, usa limpiar_webodm.ps1"
}

Write-Host "WebODM detenido." -ForegroundColor Green
