param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("baked", "tiny")]
    [string]$Target,

    [Parameter(Mandatory = $true)]
    [string]$Image
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$buildDate = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
$vcsRef = (git -C $root rev-parse --short=12 HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($vcsRef)) {
    throw "Unable to resolve the current Git revision."
}

Write-Host "Building $Image ($Target) at $buildDate from $vcsRef"
& docker build `
    --target $Target `
    --build-arg "BUILD_DATE=$buildDate" `
    --build-arg "VCS_REF=$vcsRef" `
    -t $Image `
    $root

if ($LASTEXITCODE -ne 0) {
    throw "Docker build failed with exit code $LASTEXITCODE."
}
