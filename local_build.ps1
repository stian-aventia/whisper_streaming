<#!
PowerShell build script for whisper_streaming.
Replaces local_build.sh (multi-arch build by default).
#>
[CmdletBinding()]
param(
    [string]$ImageName = "whisper_streaming:local",
    [string]$Platforms = "linux/amd64,linux/arm64",
    [switch]$NoMultiArch
)

if ($NoMultiArch) {
    Write-Host "Building single-arch image: $ImageName" -ForegroundColor Cyan
    docker build -t $ImageName .
} else {
    Write-Host "Building multi-arch image ($Platforms): $ImageName" -ForegroundColor Cyan
    docker build --platform $Platforms -t $ImageName .
}

Write-Host "Done." -ForegroundColor Green