<#!
PowerShell run script for whisper_streaming.
Replaces local_run.sh.
#>
[CmdletBinding()]
param(
    [string]$ImageName = "whisper_streaming:local",
    [string]$Model = "tiny",
    [string]$Backend = "faster-whisper",
    [int]$Port = 3000,
    [string]$Language = "auto",
    [switch]$Gpu
)

$envArgs = @(
    "-e", "MODEL=$Model",
    "-e", "BACKEND=$Backend",
    "-e", "LANGUAGE=$Language"
)

$gpuArgs = @()
if ($Gpu) { $gpuArgs = @('--gpus','all') }

Write-Host "Running $ImageName on port $Port (model=$Model backend=$Backend lang=$Language gpu=$($Gpu.IsPresent))" -ForegroundColor Cyan

docker run --rm `
    -p "$Port:3000" `
    @envArgs `
    @gpuArgs `
    -t $ImageName

Write-Host "Container exited." -ForegroundColor Yellow