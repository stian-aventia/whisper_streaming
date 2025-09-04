<#!
PowerShell build script for whisper_streaming.

Goals:
 - Fast local default: single-arch build (no emulation slowdown).
 - Optional multi-arch via BuildKit buildx (only when explicitly requested).
 - Optional push when producing a real multi-arch manifest.

Usage examples:
  # Fast local image (current host arch)
  .\local_build.ps1

  # Multi-arch (amd64 + arm64) and load only one arch into daemon (mostly for sanity check)
  .\local_build.ps1 -MultiArch

  # Multi-arch and push manifest to registry
  .\local_build.ps1 -MultiArch -Push -ImageName yourrepo/whisper_streaming:dev

Notes:
 - --load can only load a single architecture into the local daemon; multiple platforms are only preserved when using --push.
 - If buildx builder not present, script will create a named one (whisper_builder) automatically.
 - Fallback: if buildx is unavailable, will warn and perform single-arch build.
#>
[CmdletBinding()]
param(
    [string]$ImageName = "whisper_streaming:local",
    [string]$Platforms = "linux/amd64,linux/arm64",
    [switch]$MultiArch,
    [switch]$Push
)

function Ensure-BuildxBuilder {
    $builderName = 'whisper_builder'
    $existing = docker buildx ls 2>$null | Select-String -SimpleMatch $builderName
    if (-not $existing) {
        Write-Host "Creating buildx builder '$builderName'" -ForegroundColor DarkCyan
        docker buildx create --name $builderName --use | Out-Null
    } else {
        docker buildx use $builderName | Out-Null
    }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "docker CLI not found in PATH"; exit 1
}

if (-not $MultiArch) {
    Write-Host "[single-arch] docker build -t $ImageName ." -ForegroundColor Cyan
    docker build -t $ImageName . || exit $LASTEXITCODE
    Write-Host "Done." -ForegroundColor Green
    return
}

# Multi-arch path
if (-not (docker buildx version 2>$null)) {
    Write-Warning "docker buildx not available; falling back to single-arch build"
    docker build -t $ImageName . || exit $LASTEXITCODE
    Write-Host "Done (single-arch fallback)." -ForegroundColor Yellow
    return
}

Ensure-BuildxBuilder

if ($Push) {
    Write-Host "[multi-arch] build & push => $ImageName ($Platforms)" -ForegroundColor Cyan
    docker buildx build --platform $Platforms -t $ImageName --push . || exit $LASTEXITCODE
    Write-Host "Pushed multi-arch manifest." -ForegroundColor Green
} else {
    Write-Host "[multi-arch] build (no push) => $ImageName ($Platforms) --load" -ForegroundColor Cyan
    docker buildx build --platform $Platforms -t $ImageName --load . || exit $LASTEXITCODE
    Write-Host "Loaded one platform image (others discarded)." -ForegroundColor Green
}