<#
.SYNOPSIS
    Starts the whole Capivara IA: Ollama, the brain (in its own terminal window) and the Godot world.

.DESCRIPTION
    1. Makes sure Ollama answers; starts "ollama serve" in the background when it does not.
    2. Opens the brain (python -m src.live_capybara) in a new PowerShell window, so its logs stay visible.
    3. Waits for the brain's WebSocket server, then runs the Godot world.

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
    [string]$OllamaUrl = "http://localhost:11434",
    [string]$BrainHost = "127.0.0.1",
    [int]$BrainPort = 8765,
    [int]$WaitSeconds = 30
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$brainDirectory = Join-Path $projectRoot "brain"
$worldDirectory = Join-Path $projectRoot "world"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

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
    param([scriptblock]$Condition, [string]$WaitingFor)
    $deadline = (Get-Date).AddSeconds($WaitSeconds)
    while ((Get-Date) -lt $deadline) {
        if (& $Condition) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    Write-Warning "Gave up waiting for $WaitingFor after $WaitSeconds seconds."
    return $false
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

# 2. The brain, in its own window so the logs can be followed.
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

# 3. The Godot world.
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
