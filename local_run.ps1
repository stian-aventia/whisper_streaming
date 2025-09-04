<#!
PowerShell run script for whisper_streaming.

Goals:
 - Provide sensible defaults aligning with entrypoint.sh fallbacks.
 - Allow overriding key env vars without typing many -e flags.
 - Optional GPU enable sets USE_GPU=True and adds --gpus all.
 - Optionally mount a local model cache directory to /tmp.
 - Support extra arbitrary environment variables via -ExtraEnv @{KEY='VAL'}.

Examples:
  .\local_run.ps1                       # tiny model, auto language
  .\local_run.ps1 -Model base -Language en -Gpu
  .\local_run.ps1 -Model NbAiLab/nb-whisper-large -CacheDir ./model_cache
  .\local_run.ps1 -ExtraEnv @{ LOG_LEVEL='DEBUG'; MIN_CHUNK_SIZE='1' }
#>
[CmdletBinding()]
param(
    [string]$ImageName = "whisper_streaming:local",
    [string]$Model = "tiny.en",            # matches entrypoint default
    [string]$Backend = "faster-whisper",
    [int]$Port = 3000,
    [string]$Language = "auto",
    [string]$LogLevel = "INFO",
    [int]$MinChunkSize = 1,
    [int]$SamplingRate = 16000,
    [string]$CacheDir = "",               # if set, mounted to /tmp
    [switch]$Gpu,
    [hashtable]$ExtraEnv
)

$envHash = [ordered]@{
    MODEL = $Model
    BACKEND = $Backend
    LANGUAGE = $Language
    LOG_LEVEL = $LogLevel
    MIN_CHUNK_SIZE = $MinChunkSize
    SAMPLING_RATE = $SamplingRate
}
if ($Gpu) { $envHash.USE_GPU = 'True' } else { $envHash.USE_GPU = 'False' }
if ($ExtraEnv) {
    foreach ($k in $ExtraEnv.Keys) { $envHash[$k] = $ExtraEnv[$k] }
}

$envArgs = @()
foreach ($k in $envHash.Keys) { $envArgs += @('-e', "${k}=$($envHash[$k])") }

$gpuArgs = @()
if ($Gpu) { $gpuArgs = @('--gpus','all') }

$volArgs = @()
if ($CacheDir) {
    if (-not (Test-Path $CacheDir)) { New-Item -ItemType Directory -Path $CacheDir | Out-Null }
    $volArgs += @('-v', (Resolve-Path $CacheDir).Path + ':/tmp')
}

Write-Host "Running $ImageName on port $Port (model=$Model backend=$Backend lang=$Language gpu=$($Gpu.IsPresent))" -ForegroundColor Cyan

# Build explicit argument list to avoid PowerShell line continuation / splat quirks causing '-p' mapping loss.
$dockerArgs = @('run','--rm')
if (-not $Port -or $Port -le 0) { Write-Error "Invalid -Port value: $Port"; exit 1 }
$portMap = ($Port.ToString() + ':3000')
$dockerArgs += @('-p', $portMap)
$dockerArgs += $envArgs
if ($gpuArgs) { $dockerArgs += $gpuArgs }
if ($volArgs) { $dockerArgs += $volArgs }
$dockerArgs += @('-t',$ImageName)

Write-Host "docker " ($dockerArgs -join ' ') -ForegroundColor DarkGray
docker @dockerArgs

Write-Host "Container exited." -ForegroundColor Yellow