# Funciones compartidas para gestionar WebODM (Docker) en Antigravity.

function Get-WebODMRoot {
    $repoRoot = Split-Path -Parent $PSScriptRoot
    return Join-Path $repoRoot "webodm"
}

function Get-WebODMConfigPath {
    $repoRoot = Split-Path -Parent $PSScriptRoot
    $candidates = @(
        (Join-Path $PSScriptRoot "webodm.local.json"),
        (Join-Path $repoRoot "webodm\webodm.local.json")
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    return Join-Path $PSScriptRoot "webodm.config.json"
}

function Get-WebODMConfig {
    $path = Get-WebODMConfigPath
    if (-not (Test-Path $path)) {
        throw "No existe configuracion WebODM: $path"
    }
    return Get-Content $path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Get-WebODMToken {
    param([string]$Root = (Get-WebODMRoot))

    $tokenPath = Join-Path $Root ".webodm_token"
    if (Test-Path $tokenPath) {
        return (Get-Content $tokenPath -Raw).Trim()
    }

    $cfg = Get-WebODMConfig
    if ($cfg.PSObject.Properties.Name -contains "apiToken" -and $cfg.apiToken) {
        return [string]$cfg.apiToken
    }

    if ($cfg.username -and $cfg.password) {
        $body = "username=$([uri]::EscapeDataString($cfg.username))&password=$([uri]::EscapeDataString($cfg.password))"
        $resp = Invoke-RestMethod -Method Post -Uri "$($cfg.url)/api/token-auth/" -Body $body -ContentType "application/x-www-form-urlencoded"
        if ($resp.token) {
            Set-Content -Path $tokenPath -Value $resp.token -Encoding UTF8 -NoNewline
            return $resp.token
        }
    }

    throw "Falta token API. Crea webodm/.webodm_token o define username/password en scripts/webodm.local.json"
}

function Test-DockerReady {
    try {
        docker info *> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Get-WebODMMediaPath {
    $root = Get-WebODMRoot
    $cfgPath = Join-Path $root ".env"
    $media = "appmedia"
    if (Test-Path $cfgPath) {
        foreach ($line in Get-Content $cfgPath) {
            if ($line -match '^\s*WO_MEDIA_DIR\s*=\s*(.+)\s*$') {
                $media = $Matches[1].Trim()
                break
            }
        }
    }
    if ([System.IO.Path]::IsPathRooted($media)) { return $media }
    return Join-Path $root $media
}

function Get-WebODMComposeCommand {
    param([int]$NodeCount = 1)

    $root = Get-WebODMRoot
    $files = @(
        "docker-compose.yml",
        "docker-compose.nodeodm.yml"
    ) | ForEach-Object { Join-Path $root $_ }

    foreach ($f in $files) {
        if (-not (Test-Path $f)) {
            throw "No se encuentra $f"
        }
    }

    $args = @("compose")
    foreach ($f in $files) { $args += @("-f", $f) }
    $args += @("up", "-d", "--scale", "node-odm=$NodeCount")
    return @{ Root = $root; Args = $args }
}

function Get-WebODMComposeDownArgs {
    $root = Get-WebODMRoot
    return @{
        Root = $root
        Args = @(
            "compose",
            "-f", (Join-Path $root "docker-compose.yml"),
            "-f", (Join-Path $root "docker-compose.nodeodm.yml"),
            "down", "--remove-orphans"
        )
    }
}

function Invoke-WebODMApi {
    param(
        [string]$Method = "GET",
        [string]$Path,
        [object]$Body = $null
    )

    $cfg = Get-WebODMConfig
    $token = Get-WebODMToken
    $uri = "$($cfg.url)$Path"
    $headers = @{ Authorization = "JWT $token" }

    $params = @{
        Method      = $Method
        Uri         = $uri
        Headers     = $headers
        ContentType = "application/json"
    }
    if ($null -ne $Body) {
        $params.Body = ($Body | ConvertTo-Json -Depth 8)
    }

    return Invoke-RestMethod @params
}

function Get-WebODMProjects {
    $resp = Invoke-WebODMApi -Path "/api/projects/?ordering=-created_at"
    if ($resp -is [System.Array]) { return $resp }
    if ($resp.results) { return $resp.results }
    return @()
}

function Get-WebODMTasks {
    param([int]$ProjectId)
    $resp = Invoke-WebODMApi -Path "/api/projects/$ProjectId/tasks/"
    if ($resp -is [System.Array]) { return $resp }
    if ($resp.results) { return $resp.results }
    return @()
}

function Format-Bytes {
    param([long]$Bytes)
    if ($Bytes -ge 1GB) { return "{0:N2} GB" -f ($Bytes / 1GB) }
    if ($Bytes -ge 1MB) { return "{0:N2} MB" -f ($Bytes / 1MB) }
    if ($Bytes -ge 1KB) { return "{0:N2} KB" -f ($Bytes / 1KB) }
    return "$Bytes B"
}

function Get-FolderSize {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return 0 }
    return (Get-ChildItem $Path -Recurse -File -Force -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum
}

function Test-WebODMOnline {
    param([string]$Url = (Get-WebODMConfig).url)
    try {
        Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5 | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Wait-WebODMReady {
    param([int]$TimeoutSec = 180)

    $cfg = Get-WebODMConfig
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-WebODMOnline -Url $cfg.url) { return $true }
        Start-Sleep -Seconds 3
    }
    return $false
}
