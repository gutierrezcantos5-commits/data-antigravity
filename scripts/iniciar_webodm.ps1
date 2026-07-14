# Inicia WebODM con Docker + NodeODM (procesamiento de ortofotos).
param(
    [int]$NodeCount = 0,
    [switch]$NoWait
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_webodm_common.ps1"

if (-not (Test-DockerReady)) {
    Write-Host "Docker no esta en ejecucion." -ForegroundColor Red
    Write-Host "Abre Docker Desktop y vuelve a ejecutar este script."
    exit 1
}

$cfg = Get-WebODMConfig
if ($NodeCount -le 0) { $NodeCount = [int]$cfg.nodeCount }
if ($NodeCount -le 0) { $NodeCount = 1 }

$compose = Get-WebODMComposeCommand -NodeCount $NodeCount
Write-Host "Iniciando WebODM en $($compose.Root) con $NodeCount nodo(s) NodeODM..." -ForegroundColor Cyan

Push-Location $compose.Root
try {
    & docker @($compose.Args)
    if ($LASTEXITCODE -ne 0) { throw "docker compose fallo con codigo $LASTEXITCODE" }
} finally {
    Pop-Location
}

if ($NoWait) { exit 0 }

Write-Host "Esperando a que WebODM responda en $($cfg.url) ..."
if (Wait-WebODMReady -TimeoutSec 240) {
    Write-Host "WebODM listo: $($cfg.url)" -ForegroundColor Green
    Write-Host "Flujo recomendado:"
    Write-Host "  1) Sube fotos y procesa la tarea"
    Write-Host "  2) Exporta ortofoto: scripts\\exportar_ortofoto_webodm.ps1"
    Write-Host "  3) Libera espacio: scripts\\limpiar_webodm.ps1 -ProjectId <id> -Confirm"
    exit 0
}

Write-Host "WebODM aun no responde. Revisa logs con: docker logs webapp" -ForegroundColor Yellow
exit 2
