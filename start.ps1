<#
.SYNOPSIS
    Starts the whole Capivara IA: Ollama, the memory database, the brain (in its own terminal
    window) and the Godot world.

.DESCRIPTION
    1. Makes sure Ollama answers; starts "ollama serve" in the background when it does not.
    2. Starts the long-term memory (PostgreSQL in Docker) and waits until it is healthy,
       opening Docker Desktop first when needed. The memory is optional: when Docker is
       missing or the database fails, it warns and the capybara runs without remembering.
    3. Opens the brain (python -m src.live_capybara) in a new PowerShell window, so its logs stay visible.
    4. Waits for the brain's WebSocket server, then runs the Godot world.

    The Godot executable comes from -GodotPath, the GODOT_PATH environment variable or a
    "godot" command on the PATH. Set it once with:
        setx GODOT_PATH "C:\path\to\Godot_v4.x-stable_win64.exe"

.EXAMPLE
    .\start.ps1
    .\start.ps1 -Editor
#>
param(
    [string]$GodotPath = $env:GODOT_PATH,
    # Opens the Godot editor instead of running the game.
    [switch]$Editor,
    # 127.0.0.1, not localhost: on Windows, localhost tries IPv6 first, Ollama only listens
    # on IPv4, and the 2-second health check timed out before falling back, so the script
    # thought Ollama was down and stopped before starting the brain.
    [string]$OllamaUrl = "http://127.0.0.1:11434",
    [string]$BrainHost = "127.0.0.1",
    [int]$BrainPort = 8765,
    [int]$WaitSeconds = 30,
    # Docker Desktop can take a minute or two to start.
    [int]$DockerWaitSeconds = 120
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$brainDirectory = Join-Path $projectRoot "brain"
$brainEnvFile = Join-Path $brainDirectory ".env"
$worldDirectory = Join-Path $projectRoot "world"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$dockerDesktopCandidates = @(
    (Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\Docker Desktop.exe")
)
$memoryUnavailableMessage = "The capybara will run without long-term memory (her discoveries are still saved as files)."

function Test-OllamaRunning {
    try {
        Invoke-WebRequest -Uri "$OllamaUrl/api/tags" -UseBasicParsing -TimeoutSec 2 | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Test-PortOpen {
    param([string]$HostName, [int]$Port)
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    try {
        $connectAttempt = $tcpClient.BeginConnect($HostName, $Port, $null, $null)
        return $connectAttempt.AsyncWaitHandle.WaitOne(500) -and $tcpClient.Connected
    }
    catch {
        return $false
    }
    finally {
        $tcpClient.Close()
    }
}

function Wait-Until {
    param([scriptblock]$Condition, [string]$WaitingFor, [int]$TimeoutSeconds = $WaitSeconds)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (& $Condition) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    Write-Warning "Gave up waiting for $WaitingFor after $TimeoutSeconds seconds."
    return $false
}

# Docker writes progress to stderr, which "Stop" would turn into a fatal error in
# Windows PowerShell 5.1, so docker always runs with "Continue" and is judged by its exit code.
function Invoke-Docker {
    param([string[]]$Arguments, [switch]$Quiet)
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        if ($Quiet) {
            & docker @Arguments *> $null
        }
        else {
            & docker @Arguments 2>&1 | ForEach-Object { Write-Host "  $_" }
        }
        return $LASTEXITCODE -eq 0
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
}

function Test-DockerRunning {
    return Invoke-Docker -Arguments @("info") -Quiet
}

function Resolve-DockerDesktopPath {
    return $dockerDesktopCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

function Start-DockerIfNeeded {
    if (Test-DockerRunning) {
        return $true
    }
    $dockerDesktopPath = Resolve-DockerDesktopPath
    if (-not $dockerDesktopPath) {
        Write-Warning "Docker is not running and Docker Desktop was not found."
        return $false
    }
    Write-Host "Starting Docker Desktop (this can take a minute)..."
    Start-Process -FilePath $dockerDesktopPath
    return Wait-Until -Condition { Test-DockerRunning } -WaitingFor "Docker" -TimeoutSeconds $DockerWaitSeconds
}

function Start-MemoryDatabase {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Warning "The 'docker' command was not found. $memoryUnavailableMessage"
        return
    }
    if (-not (Test-Path $brainEnvFile)) {
        Write-Warning "$brainEnvFile not found (it holds MEMORY_DB_PASSWORD). $memoryUnavailableMessage"
        return
    }
    if (-not (Start-DockerIfNeeded)) {
        Write-Warning $memoryUnavailableMessage
        return
    }
    Write-Host "Starting the memory database..."
    # --wait returns once the healthcheck in compose.yaml reports the database is ready.
    $composeArguments = @(
        "compose", "--project-directory", $projectRoot, "--env-file", $brainEnvFile, "up", "--detach", "--wait"
    )
    if (Invoke-Docker -Arguments $composeArguments) {
        Write-Host "The memory database is ready."
    }
    else {
        Write-Warning "The memory database did not start. $memoryUnavailableMessage"
    }
}

function Resolve-GodotPath {
    if ($GodotPath -and (Test-Path $GodotPath)) {
        return $GodotPath
    }
    $godotCommand = Get-Command godot -ErrorAction SilentlyContinue
    if ($godotCommand) {
        return $godotCommand.Source
    }
    return $null
}

# 1. Ollama: the brain's language model.
if (Test-OllamaRunning) {
    Write-Host "Ollama is already running."
}
else {
    if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
        throw "Ollama is not running and the 'ollama' command was not found. Install it from https://ollama.com."
    }
    Write-Host "Starting Ollama..."
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    if (-not (Wait-Until -Condition { Test-OllamaRunning } -WaitingFor "Ollama")) {
        throw "Ollama did not start."
    }
}

# 2. The long-term memory, before the brain, so the brain starts with it ready.
Start-MemoryDatabase

# 3. The brain, in its own window so the logs can be followed.
if (-not (Test-Path $venvPython)) {
    throw "Python virtual environment not found at $venvPython. See the README to create it."
}
if (Test-PortOpen -HostName $BrainHost -Port $BrainPort) {
    Write-Host "The brain is already running on ${BrainHost}:$BrainPort."
}
else {
    Write-Host "Starting the brain in a new window..."
    $brainCommand = "`$Host.UI.RawUI.WindowTitle = 'Capivara IA - cerebro'; & '$venvPython' -m src.live_capybara"
    Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", $brainCommand -WorkingDirectory $brainDirectory
    Wait-Until -Condition { Test-PortOpen -HostName $BrainHost -Port $BrainPort } -WaitingFor "the brain" | Out-Null
}

# 4. The Godot world.
$resolvedGodotPath = Resolve-GodotPath
if (-not $resolvedGodotPath) {
    Write-Warning "Godot not found. Pass -GodotPath or set GODOT_PATH; the brain keeps running meanwhile."
    return
}
$godotArguments = @("--path", $worldDirectory)
if ($Editor) {
    $godotArguments += "--editor"
}
Write-Host "Starting the world..."
Start-Process -FilePath $resolvedGodotPath -ArgumentList $godotArguments
