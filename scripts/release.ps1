param(
    [string]$DryRun = "0",
    [string]$NextVersion = "",
    [string]$SkipValidation = "0"
)

$ErrorActionPreference = "Stop"

function Test-Enabled {
    param([string]$Value)
    return $Value -match '^(1|true|yes|y)$'
}

function Set-Text {
    param(
        [string]$Path,
        [string]$Text
    )
    $resolved = (Resolve-Path -LiteralPath $Path).Path
    $encoding = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($resolved, $Text, $encoding)
}

function Convert-ToPackageVersion {
    param([string]$Version)
    if ($Version -match '^\d+\.\d+$') {
        return "$Version.0"
    }
    if ($Version -match '^\d+\.\d+\.\d+$') {
        return $Version
    }
    throw "Release version '$Version' must look like 0.2 or 0.2.0."
}

function Get-NextSnapshot {
    param([string]$Version)
    if ($Version -match '^(\d+)\.(\d+)$') {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2] + 1
        return "$major.$minor-snapshot"
    }
    if ($Version -match '^(\d+)\.(\d+)\.(\d+)$') {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2] + 1
        return "$major.$minor-snapshot"
    }
    throw "Cannot infer next snapshot from '$Version'. Pass NEXT_VERSION=..."
}

function Invoke-Step {
    param(
        [string]$Description,
        [scriptblock]$Action
    )
    Write-Host "==> $Description"
    if (-not (Test-Enabled $DryRun)) {
        & $Action
    }
}

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

if (-not (Test-Path -LiteralPath "VERSION")) {
    throw "VERSION file is missing from repo root."
}

$snapshotVersion = (Get-Content -Raw -LiteralPath "VERSION").Trim()
if ($snapshotVersion -notmatch '^(\d+\.\d+(?:\.\d+)?)-snapshot$') {
    throw "VERSION must be a snapshot version like 0.2-snapshot before release. Current: '$snapshotVersion'"
}

$releaseVersion = $Matches[1]
$releaseTag = "v$releaseVersion"
$releasePackageVersion = Convert-ToPackageVersion $releaseVersion

if ([string]::IsNullOrWhiteSpace($NextVersion)) {
    $nextSnapshotVersion = Get-NextSnapshot $releaseVersion
} else {
    $nextSnapshotVersion = $NextVersion.Trim()
}

if ($nextSnapshotVersion -notmatch '^\d+\.\d+(?:\.\d+)?-snapshot$') {
    throw "NextVersion must look like 0.3-snapshot or 0.3.0-snapshot. Current: '$nextSnapshotVersion'"
}

$nextReleaseBase = $nextSnapshotVersion -replace '-snapshot$', ''
$nextPackageVersion = "$(Convert-ToPackageVersion $nextReleaseBase).dev0"

$status = git status --porcelain -- . ":(exclude)todo"
if ($status -and -not (Test-Enabled $DryRun)) {
    throw "Working tree outside todo/ must be clean before release. Commit or stash release-relevant changes first."
}

if (git rev-parse -q --verify "refs/tags/$releaseTag" 2>$null) {
    throw "Tag $releaseTag already exists."
}

Write-Host "Release version: $releaseVersion"
Write-Host "Release tag:     $releaseTag"
Write-Host "Package version: $releasePackageVersion"
Write-Host "Next snapshot:   $nextSnapshotVersion"
Write-Host "Next package:    $nextPackageVersion"

Invoke-Step "Update files for $releaseTag" {
    Set-Text "VERSION" $releaseVersion

    $pyproject = Get-Content -Raw -LiteralPath "pyproject.toml"
    $pyproject = $pyproject -replace '(?m)^version = "[^"]+"', "version = `"$releasePackageVersion`""
    Set-Text "pyproject.toml" $pyproject

    foreach ($doc in @("README.md", "docs/dockerhub.md")) {
        $text = Get-Content -Raw -LiteralPath $doc
        $text = $text -replace [regex]::Escape("### v$snapshotVersion"), "### $releaseTag"
        $text = $text -replace [regex]::Escape(":v$snapshotVersion"), ":$releaseTag"
        Set-Text $doc $text
    }
}

Invoke-Step "Run release validation" {
    if (-not (Test-Enabled $SkipValidation)) {
        python -m compileall -q kokorotts
        task image
    }
}

Invoke-Step "Commit and tag $releaseTag" {
    git add VERSION pyproject.toml README.md docs/dockerhub.md
    git commit -m "release: $releaseTag"
    git tag -a $releaseTag -m "Release $releaseTag"
}

Invoke-Step "Prepare $nextSnapshotVersion" {
    Set-Text "VERSION" $nextSnapshotVersion

    $pyproject = Get-Content -Raw -LiteralPath "pyproject.toml"
    $pyproject = $pyproject -replace '(?m)^version = "[^"]+"', "version = `"$nextPackageVersion`""
    Set-Text "pyproject.toml" $pyproject

    git add VERSION pyproject.toml
    git commit -m "chore: start $nextSnapshotVersion"
}

Write-Host "Release workflow complete."
