<#
.SYNOPSIS
    Records a clip of the capybara with Godot's Movie Maker, filmed by the clip camera
    (close to her, the protagonist), and turns it into MP4s for Instagram Reels.

.DESCRIPTION
    1. Makes sure the brain is running; when it is not, runs .\start.ps1 -SkipWorld
       (Ollama, memory and brain) and waits for it.
    2. Runs the world in clip mode ("-- --clip"): the clip camera films her, the interface
       is hidden, and -Shot picks the framing (Auto cuts between shots like a series). The
       Movie Maker (--write-movie) records at a fixed frame rate for the given number of
       seconds and saves an .avi (MJPEG video + PCM audio) in -OutputDir.
    3. Converts the .avi with ffmpeg (H.264, -preset veryfast, -crf 20, yuv420p, AAC audio).
       Vertical (the default) is rendered standing up at 1080x1920: <name>-reels.mp4.
       Horizontal is rendered at 1920x1080: <name>-horizontal.mp4, plus <name>-reels.mp4
       made from it (-VerticalMode). The .avi is deleted after a good conversion, unless -KeepAvi.
    4. Compares the game time with the real time the recording took. The Movie Maker
       advances the game exactly 1/FPS per frame, however long the frame takes to render,
       while the brain lives in real time: when the two differ, her lines and orders land
       at the wrong moment in the clip, and the script warns.

    The Godot executable comes from -GodotPath, the GODOT_PATH environment variable or the
    usual folder on this machine (D:\Godot_v4.7.2-stable_win64.exe\). The console build
    is preferred, so Godot's messages show in this terminal.

.EXAMPLE
    .\record_clip.ps1
    .\record_clip.ps1 -Seconds 45 -Shot Close
    .\record_clip.ps1 -Seconds 30 -Orientation Horizontal -VerticalMode Crop -KeepAvi
#>
param(
    # Length of the clip in game seconds.
    [ValidateRange(1, 3600)]
    [int]$Seconds = 20,
    [ValidateRange(1, 120)]
    [int]$Fps = 30,
    # Recorded before the clip and cut off: the brain connects, the real sky arrives and the
    # first stutters pass. The clip itself still lasts -Seconds.
    [ValidateRange(0, 30)]
    [int]$WarmupSeconds = 3,
    [string]$OutputDir = "D:\clipes",
    [string]$GodotPath = $env:GODOT_PATH,
    # ffmpeg.exe, or a folder that holds it (searched inside). Without it: the PATH, then
    # D:\tools\ffmpeg (where winget install Gyan.FFmpeg --location put it), then winget's folder.
    [string]$FfmpegPath = $env:FFMPEG_PATH,
    # Vertical renders the world standing up, for Reels; Horizontal renders it lying down.
    [ValidateSet("Vertical", "Horizontal")]
    [string]$Orientation = "Vertical",
    # Auto cuts like a series: opens wide, then medium and close, and close when she speaks
    # or her feeling changes. Close, Medium and Wide keep one shot for the whole clip.
    [ValidateSet("Auto", "Close", "Medium", "Wide")]
    [string]$Shot = "Auto",
    # Window size the world is rendered at. Empty: 1080x1920 vertical, 1920x1080 horizontal.
    [ValidatePattern('^(\d+x\d+)?$')]
    [string]$Resolution = "",
    # Only for -Orientation Horizontal, to make the Reels copy from the horizontal clip.
    # Blur: the whole scene in the middle, over a blurred copy of itself filling the frame.
    # Crop: the center of the scene filling the whole frame (the sides are cut).
    [ValidateSet("Blur", "Crop")]
    [string]$VerticalMode = "Blur",
    # Keeps the .avi straight from Godot next to the MP4s.
    [switch]$KeepAvi,
    [string]$BrainHost = "127.0.0.1",
    [int]$BrainPort = 8765,
    # The first start loads the model from disk, which can take a while.
    [int]$BrainWaitSeconds = 90
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$worldDirectory = Join-Path $projectRoot "world"
$defaultGodotDirectory = "D:\Godot_v4.7.2-stable_win64.exe"
$defaultFfmpegDirectory = "D:\tools\ffmpeg"
# Below this ratio between game time and real time, the clip is out of sync with the brain.
$syncTolerance = 0.05
$h264Arguments = @("-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-color_range", "tv")
# Godot's MJPEG uses the full color range (yuvj420p); players and Instagram expect the TV
# range of plain yuv420p, or the colors come out washed or crushed. -pix_fmt alone keeps it full.
$toTvRange = "scale=in_range=full:out_range=tv,format=yuv420p"
$audioArguments = @("-c:a", "aac", "-b:a", "192k")

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

# A folder holding Godot is accepted too: the console build inside it is used.
function Resolve-GodotPath {
    $candidates = @()
    if ($GodotPath) {
        $candidates += $GodotPath
    }
    $candidates += $defaultGodotDirectory
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate -PathType Leaf) {
            $consoleBuild = $candidate -replace '\.exe$', '_console.exe'
            if (Test-Path $consoleBuild -PathType Leaf) {
                return $consoleBuild
            }
            return $candidate
        }
        if (Test-Path $candidate -PathType Container) {
            $found = Get-ChildItem -Path $candidate -Filter "Godot*_console.exe" | Select-Object -First 1
            if (-not $found) {
                $found = Get-ChildItem -Path $candidate -Filter "Godot*.exe" | Select-Object -First 1
            }
            if ($found) {
                return $found.FullName
            }
        }
    }
    return $null
}

function Find-FfmpegIn {
    param([string]$Location)
    if (-not $Location -or -not (Test-Path $Location)) {
        return $null
    }
    if (Test-Path $Location -PathType Leaf) {
        return $Location
    }
    $found = Get-ChildItem -Path $Location -Filter "ffmpeg.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) {
        return $found.FullName
    }
    return $null
}

function Resolve-FfmpegPath {
    $chosen = Find-FfmpegIn $FfmpegPath
    if ($chosen) {
        return $chosen
    }
    $command = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    $onDriveD = Find-FfmpegIn $defaultFfmpegDirectory
    if ($onDriveD) {
        return $onDriveD
    }
    # winget puts a link here; a terminal opened before the install does not see it on the PATH yet.
    $wingetLink = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links\ffmpeg.exe"
    if (Test-Path $wingetLink) {
        return $wingetLink
    }
    $wingetPackage = Get-ChildItem -Path (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages") -Filter "ffmpeg.exe" -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($wingetPackage) {
        return $wingetPackage.FullName
    }
    return $null
}

function Start-BrainIfNeeded {
    if (Test-PortOpen -HostName $BrainHost -Port $BrainPort) {
        Write-Host "The brain is already running on ${BrainHost}:$BrainPort."
        return
    }
    Write-Host "The brain is not running: starting it with start.ps1 -SkipWorld..."
    & (Join-Path $projectRoot "start.ps1") -SkipWorld -BrainHost $BrainHost -BrainPort $BrainPort -WaitSeconds $BrainWaitSeconds
    if (-not (Test-PortOpen -HostName $BrainHost -Port $BrainPort)) {
        throw "The brain did not start on ${BrainHost}:$BrainPort. Look at its window for the error."
    }
}

function Invoke-Ffmpeg {
    param([string[]]$Arguments, [string]$Description)
    Write-Host $Description
    # ffmpeg writes its progress to stderr; under "Stop" Windows PowerShell would treat that as an error.
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $ffmpegPath -hide_banner -loglevel error -y @Arguments
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($exitCode -ne 0) {
        throw "ffmpeg failed ($Description), exit code $exitCode."
    }
}

function Get-VerticalFilter {
    if ($VerticalMode -eq "Crop") {
        return "[0:v]scale=-2:1920,crop=1080:1920,setsar=1,$toTvRange[reels]"
    }
    return (
        "[0:v]split=2[background][scene];" +
        "[background]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:2[blurred];" +
        "[scene]scale=1080:-2[centered];" +
        "[blurred][centered]overlay=(W-w)/2:(H-h)/2,setsar=1,$toTvRange[reels]"
    )
}

function Format-Size {
    param([string]$Path)
    return "{0:N1} MB" -f ((Get-Item $Path).Length / 1MB)
}

# 1. Tools, before anything slow starts.
$resolvedGodotPath = Resolve-GodotPath
if (-not $resolvedGodotPath) {
    throw "Godot not found. Pass -GodotPath or set GODOT_PATH (the .exe or the folder that holds it)."
}
$ffmpegPath = Resolve-FfmpegPath
if (-not $ffmpegPath) {
    throw "ffmpeg not found. Install it with: winget install Gyan.FFmpeg --location D:\tools\ffmpeg (or pass -FfmpegPath)."
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$isVertical = $Orientation -eq "Vertical"
if (-not $Resolution) {
    $Resolution = if ($isVertical) { "1080x1920" } else { "1920x1080" }
}

# 2. The brain, so the capybara is alive in the clip.
Start-BrainIfNeeded

# 3. The recording. --quit-after counts frames, and with the Movie Maker each frame is
#    exactly 1/FPS of game time.
$clipName = "capivara-" + (Get-Date -Format "yyyyMMdd-HHmmss")
$aviPath = Join-Path $OutputDir "$clipName.avi"
$frameCount = ($WarmupSeconds + $Seconds) * $Fps
Write-Host "Recording $WarmupSeconds s of warm-up + $Seconds s ($frameCount frames at $Fps FPS, $Resolution, shot $Shot) with $resolvedGodotPath..."
# What comes after "--" goes to the game itself (ClipMode in world/scripts/clip).
$godotArguments = @(
    "--path", $worldDirectory,
    "--fixed-fps", $Fps,
    "--write-movie", $aviPath,
    "--quit-after", $frameCount,
    "--", "--clip", "--clip-shot=$($Shot.ToLower())", "--clip-warmup=$WarmupSeconds"
)
# The Movie Maker ignores --resolution. An override.cfg next to project.godot overrides
# settings for one run, and is removed right after:
# - the "viewport" stretch mode renders the game at exactly $Resolution, whatever the window;
# - the window is half that size, so it fits the screen. A window bigger than the screen
#   (1080x1920 on a 1080p monitor) made every frame ~60 ms slower.
# The interface keeps its size: its base size scales the same way in both stretch modes.
$overrideConfigPath = Join-Path $worldDirectory "override.cfg"
if (Test-Path $overrideConfigPath) {
    throw "$overrideConfigPath already exists; move it away before recording."
}
$width, $height = [int[]]($Resolution -split "x")
Set-Content -Path $overrideConfigPath -Encoding ascii -Value @(
    "[display]",
    "",
    "window/size/viewport_width=$width",
    "window/size/viewport_height=$height",
    "window/size/window_width_override=$([int]($width / 2))",
    "window/size/window_height_override=$([int]($height / 2))",
    'window/stretch/mode="viewport"'
)
$previousPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    & $resolvedGodotPath @godotArguments
}
finally {
    $ErrorActionPreference = $previousPreference
    Remove-Item -Path $overrideConfigPath -Confirm:$false -ErrorAction SilentlyContinue
}
if (-not (Test-Path $aviPath)) {
    throw "Godot finished without writing $aviPath."
}
# Real time from the first frame written (the file is created) to the last one: Godot's
# start (loading the scene) and exit are left out.
$aviFile = Get-Item $aviPath
$recordingSeconds = ($aviFile.LastWriteTime - $aviFile.CreationTime).TotalSeconds

# 4. The MP4s.
$horizontalPath = Join-Path $OutputDir "$clipName-horizontal.mp4"
$reelsPath = Join-Path $OutputDir "$clipName-reels.mp4"
$clipPaths = @()
if ($isVertical) {
    Invoke-Ffmpeg -Description "Converting to the vertical MP4..." -Arguments (
        @("-ss", $WarmupSeconds, "-i", $aviPath, "-vf", $toTvRange) + $h264Arguments + $audioArguments + @("-movflags", "+faststart", $reelsPath)
    )
    $clipPaths += $reelsPath
}
else {
    Invoke-Ffmpeg -Description "Converting to the horizontal MP4..." -Arguments (
        @("-ss", $WarmupSeconds, "-i", $aviPath, "-vf", $toTvRange) + $h264Arguments + $audioArguments + @("-movflags", "+faststart", $horizontalPath)
    )
    Invoke-Ffmpeg -Description "Converting to the vertical 1080x1920 MP4 ($VerticalMode)..." -Arguments (
        @("-ss", $WarmupSeconds, "-i", $aviPath, "-filter_complex", (Get-VerticalFilter), "-map", "[reels]", "-map", "0:a?") +
        $h264Arguments + $audioArguments + @("-movflags", "+faststart", $reelsPath)
    )
    $clipPaths += $horizontalPath, $reelsPath
}

# 5. Report: where the files are, how big, and whether the game kept the brain's pace.
Write-Host ""
Write-Host "Clips in ${OutputDir}:"
if ($KeepAvi) {
    Write-Host "  $aviPath  ($(Format-Size $aviPath))"
}
foreach ($clipPath in $clipPaths) {
    Write-Host "  $clipPath  ($(Format-Size $clipPath))"
}
if (-not $KeepAvi) {
    Remove-Item -Path $aviPath -Confirm:$false
}

$realSeconds = $recordingSeconds
$gameSeconds = $WarmupSeconds + $Seconds
$gameSpeed = $gameSeconds / $realSeconds
Write-Host ("Game time {0} s in {1:N1} s of real time: the game ran at {2:N2}x real time." -f $gameSeconds, $realSeconds, $gameSpeed)
if ([math]::Abs($gameSpeed - 1) -gt $syncTolerance) {
    Write-Warning (
        "Out of sync with the brain: the brain lives in real time, so in this clip her lines and " +
        "orders happen {0:N2}x as fast as they really did (the voice itself plays at its normal speed)." -f (1 / $gameSpeed)
    )
}
else {
    Write-Host "In sync with the brain (within $([int]($syncTolerance * 100))%)."
}
