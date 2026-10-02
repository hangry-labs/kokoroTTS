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

function Update-DockerImageTags {
    param(
        [string]$Text,
        [string]$ReleaseTag
    )

    $updated = [regex]::Replace(
        $Text,
        'hangrylabs/kokorotts:v\d+\.\d+(?:\.\d+)?(_tiny)?',
        { param($match) "hangrylabs/kokorotts:$ReleaseTag$($match.Groups[1].Value)" }
    )
    $updated = [regex]::Replace(
        $updated,
        '(?m)^- Full image: `v\d+\.\d+(?:\.\d+)?`,',
        "- Full image: ``$ReleaseTag``,"
    )
    $updated = [regex]::Replace(
        $updated,
        '(?m)^- Tiny image: `v\d+\.\d+(?:\.\d+)?_tiny`,',
        "- Tiny image: ``${ReleaseTag}_tiny``,"
    )
    $updated = [regex]::Replace(
        $updated,
        '(?m)^- Current release tag: `v\d+\.\d+(?:\.\d+)?`\r?$',
        "- Current release tag: ``$ReleaseTag``"
    )
    return [regex]::Replace(
        $updated,
        'standard `v\d+\.\d+(?:\.\d+)?` commands above',
        "standard ``$ReleaseTag`` commands above"
    )
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

$status = git status --porcelain -- . ":(exclude)todo" ":(exclude).ai"
if ($status -and -not (Test-Enabled $DryRun)) {
    throw "Working tree outside .ai/ and todo/ must be clean before release. Commit or stash release-relevant changes first."
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

    $readme = Get-Content -Raw -LiteralPath "README.md"
    $readme = $readme.Replace("### v$releaseVersion Snapshot", "### $releaseTag")
    $readme = $readme.Replace("### v$snapshotVersion", "### $releaseTag")
    $historyMarker = "## Version History"
    $historyIndex = $readme.IndexOf($historyMarker, [System.StringComparison]::Ordinal)
    if ($historyIndex -lt 0) {
        throw "README.md is missing the '$historyMarker' section."
    }
    $readmePrefix = Update-DockerImageTags $readme.Substring(0, $historyIndex) $releaseTag
    $readme = $readmePrefix + $readme.Substring($historyIndex)
    Set-Text "README.md" $readme

    $dockerHub = Get-Content -Raw -LiteralPath "docs/dockerhub.md"
    $dockerHub = Update-DockerImageTags $dockerHub $releaseTag
    Set-Text "docs/dockerhub.md" $dockerHub
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
