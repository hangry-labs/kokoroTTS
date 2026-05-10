param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$ErrorActionPreference = "Stop"

$expandedPath = [Environment]::ExpandEnvironmentVariables($Path)
$resolved = Resolve-Path -LiteralPath $expandedPath
Add-Type -AssemblyName PresentationCore

$player = [System.Windows.Media.MediaPlayer]::new()
$player.Open([Uri]$resolved.Path)

try {
    $player.Play()
    $deadline = [DateTime]::UtcNow.AddSeconds(10)
    while (-not $player.NaturalDuration.HasTimeSpan -and [DateTime]::UtcNow -lt $deadline) {
        Start-Sleep -Milliseconds 100
    }

    if ($player.NaturalDuration.HasTimeSpan) {
        $durationMs = [int][Math]::Ceiling($player.NaturalDuration.TimeSpan.TotalMilliseconds) + 500
        Start-Sleep -Milliseconds $durationMs
    } else {
        Start-Sleep -Seconds 5
    }
}
finally {
    $player.Close()
}
