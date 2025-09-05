[CmdletBinding()]
param(
    [string]$Model = 'NbAiLab/nb-whisper-tiny',
    [int]$Port = 3000,
    [switch]$Gpu
)

$image = 'whisper_streaming:local'

Write-Host "Running $image model=$Model port=$Port gpu=$($Gpu.IsPresent)" -ForegroundColor Cyan
docker run --gpus=all -e MODEL=$Model -p "$Port`:3000" -t $image