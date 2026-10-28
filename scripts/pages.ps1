param([ValidateSet('build','preview')][string]$Action='preview')
$ErrorActionPreference='Stop'
$repoRoot=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$previewRoot=[IO.Path]::GetFullPath((Join-Path $repoRoot '.ai/scratch/pages'))
$stagedRoot=Join-Path $previewRoot 'source'
$outputRoot=Join-Path $previewRoot 'output'
New-Item -ItemType Directory -Path $previewRoot,$outputRoot -Force | Out-Null
Push-Location $repoRoot
try {
    & uv run --no-project --python 3.13 python scripts/stage_pages.py
    if ($LASTEXITCODE -ne 0) { throw 'Public Pages staging failed.' }
    & docker build --file site/Dockerfile --tag kokorotts:pages site
    if ($LASTEXITCODE -ne 0) { throw 'Pages builder image failed.' }
    & docker run --rm --mount "type=bind,source=$stagedRoot,target=/source,readonly" `
        --mount "type=bind,source=$outputRoot,target=/output" `
        kokorotts:pages build --source /source --destination /output --config /source/_config.yml --safe --trace
    if ($LASTEXITCODE -ne 0) { throw 'Pages build failed.' }
    if ($Action -eq 'preview') {
        Write-Output 'Project website: http://127.0.0.1:9006/kokoroTTS/'
        & uv run --no-project --python 3.13 python scripts/serve_pages.py
    } else { Write-Output "Website built into $outputRoot" }
}
finally { Pop-Location }
