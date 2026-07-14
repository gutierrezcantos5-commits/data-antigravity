# Publish slim CI slice to GitHub (sin historial de 6 GB ni zip 394 MB).
# Uso:
#   1. Crear repo vacio en GitHub: gutierrezcantos5-commits/data-antigravity
#   2. .\scripts\publish_github_ci.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
$ExportDir = Join-Path $env:TEMP "data-antigravity-export"
$RemoteUrl = "https://github.com/gutierrezcantos5-commits/data-antigravity.git"

Write-Host "Repo local: $RepoRoot"
Write-Host "Export temp: $ExportDir"

if (Test-Path $ExportDir) {
    Remove-Item $ExportDir -Recurse -Force
}
New-Item -ItemType Directory -Path $ExportDir | Out-Null

function Copy-Tree($Rel) {
    $src = Join-Path $RepoRoot $Rel
    $dst = Join-Path $ExportDir $Rel
    if (Test-Path $src) {
        New-Item -ItemType Directory -Force -Path (Split-Path $dst -Parent) | Out-Null
        Copy-Item $src $dst -Recurse -Force
    }
}

@(
    ".github",
    ".cursor",
    "tests",
    "scripts",
    "opengravity\docs",
    "opengravity\runtime",
    "Habilidades Agentes Antigravity\nexus_orchestrator.py",
    "Habilidades Agentes Antigravity\cognee-memory"
) | ForEach-Object { Copy-Tree $_ }

@(
    ".gitignore",
    "pytest.ini",
    "requirements.txt",
    "antigravity_mcp_bridge.py",
    "CLAUDE.md",
    "opengravity\action.yml"
) | ForEach-Object {
    $src = Join-Path $RepoRoot $_
    if (Test-Path $src) {
        $dst = Join-Path $ExportDir $_
        New-Item -ItemType Directory -Force -Path (Split-Path $dst -Parent) | Out-Null
        Copy-Item $src $dst -Force
    }
}

@(
    "scripts\_restore_extract",
    "opengravity\runtime\memory\chroma_data",
    "opengravity\runtime\memory\embeddings_cache.json",
    "opengravity\runtime\memory\chroma_index.json"
) | ForEach-Object {
    $p = Join-Path $ExportDir $_
    if (Test-Path $p) { Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue }
}

Push-Location $ExportDir
$code = 1
try {
    git init -b main | Out-Null
    git add -A
    git commit -m "feat: Antigravity engineering OS (CI + evals + ledger)" -m "Slim export for GitHub Actions."

    $remotes = git remote 2>$null
    if ($remotes -match "origin") {
        git remote remove origin | Out-Null
    }
    git remote add origin $RemoteUrl
    Write-Host "Pushing to $RemoteUrl ..."
    git push -u origin main --force
    $code = $LASTEXITCODE
}
finally {
    Pop-Location
}

if ($code -eq 0) {
    Write-Host "OK - GitHub Actions should start in a few seconds."
} else {
    Write-Host "ERR push exit code $code. Did you create the empty repo on GitHub?"
    exit $code
}
