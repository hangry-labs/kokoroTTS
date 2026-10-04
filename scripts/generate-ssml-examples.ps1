param(
    [string]$BaseUrl = "http://localhost:7860",
    [string]$Device = "auto",
    [switch]$Play,
    [string]$ExampleName = ""
)

$ErrorActionPreference = "Stop"
$examplesPath = Join-Path (Split-Path $PSScriptRoot -Parent) "examples"

$examples = @(
    @{
        Name = "Morning model meeting"
        File = "kokorotts-ssml-dialogue.mp3"
        Voices = "af_heart,am_michael"
        MinimumDuration = 14.0
        Ssml = @"
<speak>
  <voice name="af_heart"><prosody speed="0.95" pitch="+1st">Good morning, Michael! Did you remember to warm up the speech model?</prosody></voice>
  <break time="140ms"/>
  <voice name="am_michael"><prosody speed="0.9" pitch="-1st" tempo="0.98">I did! But it started talking before I finished my coffee.</prosody></voice>
  <break time="140ms"/>
  <voice name="af_heart"><prosody speed="1.05" pitch="+1.5st">That sounds less like a bug and more like enthusiasm!</prosody></voice>
  <break time="140ms"/>
  <voice name="am_michael"><prosody speed="0.92" pitch="-1st" volume="0.95">So our synthetic colleague is officially the most productive one here!</prosody></voice>
</speak>
"@
    }
    @{
        Name = "The privileged sign"
        File = "kokorotts-ssml-british-deploy.mp3"
        Voices = "bf_emma,bm_george"
        MinimumDuration = 11.5
        Ssml = @"
<speak>
  <voice name="bf_emma"><prosody speed="0.98" pitch="+0.5st">George! The deployment says it is waiting for a sign.</prosody></voice>
  <break time="110ms"/>
  <voice name="bm_george"><prosody speed="0.92" pitch="-1st">I gave it one! It said the sign needed administrator privileges.</prosody></voice>
  <break time="110ms"/>
  <voice name="bf_emma"><prosody tempo="1.06" pitch="+1st">Did you try turning the sign off and on again?</prosody></voice>
  <break time="110ms"/>
  <voice name="bm_george"><prosody speed="0.88" pitch="-1.5st" volume="0.95">Yes! We are now running two signs.</prosody></voice>
</speak>
"@
    }
    @{
        Name = "Turn left at the moon"
        File = "kokorotts-ssml-moon-navigation.mp3"
        Voices = "af_bella,am_fenrir"
        MinimumDuration = 11.0
        Ssml = @"
<speak>
  <voice name="af_bella"><prosody speed="1.05" pitch="+1st">Beep-beep! Recalculating. In three hundred thousand kilometers, turn left at the moon.</prosody></voice>
  <break time="120ms"/>
  <voice name="am_fenrir"><prosody speed="0.88" pitch="-2st">Hmm? There is no road at the moon!</prosody></voice>
  <break time="120ms"/>
  <voice name="af_bella"><prosody tempo="1.08" pitch="+1.5st">Oh! That explains why traffic is unusually light.</prosody></voice>
  <break time="120ms"/>
  <voice name="am_fenrir"><prosody speed="0.92" volume="0.95">Can we please find a route with oxygen?</prosody></voice>
</speak>
"@
    }
    @{
        Name = "The shopping negotiation"
        File = "kokorotts-ssml-mother-daughter.mp3"
        Voices = "bf_isabella"
        MinimumDuration = 12.0
        Ssml = @"
<speak>
  <voice name="bf_isabella">
     <prosody speed="1" pitch="+4st" tempo="1.05" volume="0.9">Mommy mommy I want this</prosody>
     <prosody speed="0.9" pitch="-1st" tempo="1.1" volume="0.9">Isabel this is not for you</prosody>
     <prosody speed="1.3" pitch="-1st" tempo="1.1" volume="0.9">Put it down please !</prosody>
     <break time="500ms"/>
     <prosody speed="1" pitch="+4st" tempo="1.05" volume="0.9"> But, I </prosody>
     <break time="200ms"/>
     <prosody speed="1" pitch="+4st" tempo="1.05" volume="0.9"> I </prosody>
     <break time="200ms"/>
     <prosody speed="1" pitch="+4st" tempo="1.05" volume="0.9"> But, I really really want it. I spotted it first !</prosody>
     <break time="400ms"/>
     <prosody speed="0.8" pitch="-1st" tempo="1.1" volume="0.9">No, put it down right now.</prosody>
     <prosody speed="1.3" pitch="-1st" tempo="1.1" volume="0.9"> This is the end of this discussion.</prosody>
  </voice>
</speak>
"@
    }
    @{
        Name = "The coffee-machine incident"
        File = "kokorotts-ssml-multilingual-coffee.mp3"
        Voices = "zf_xiaoxiao,af_heart,dm_martin"
        MinimumDuration = 12.0
        Ssml = @"
<speak>
  <voice name="zf_xiaoxiao"><prosody speed="0.96" pitch="+0.5st">我发现了一个错误！咖啡机拒绝连接服务器。</prosody></voice>
  <break time="130ms"/>
  <voice name="af_heart"><prosody speed="1.02" pitch="+1st">Wait! That is not a bug. The coffee machine has boundaries.</prosody></voice>
  <break time="130ms"/>
  <voice name="dm_martin"><prosody speed="0.94" pitch="-1st">Dann geben wir der Kaffeemaschine ein eigenes Passwort!</prosody></voice>
  <break time="130ms"/>
  <voice name="zf_xiaoxiao"><prosody tempo="1.05" pitch="+1st">好主意！现在它要求管理员权限？</prosody></voice>
</speak>
"@
    }
)

if ($ExampleName) {
    $examples = @($examples | Where-Object { $_.Name -eq $ExampleName })
    if ($examples.Count -eq 0) {
        throw "Unknown SSML example: $ExampleName"
    }
}

Invoke-RestMethod -Uri "$BaseUrl/tts/ping" | Out-Null

foreach ($example in $examples) {
    $outputPath = Join-Path $examplesPath $example.File
    $pendingPath = "$outputPath.pending"
    $body = @{
        text = $example.Ssml
        input_type = "ssml"
        voice = ($example.Voices -split ",")[0]
        device = $Device
        output_format = "mp3"
    } | ConvertTo-Json -Compress
    $completed = $false
    $lastError = "generation did not run"
    try {
        foreach ($attempt in 1..3) {
            Remove-Item -LiteralPath $pendingPath -Force -ErrorAction SilentlyContinue
            try {
                $response = Invoke-WebRequest `
                    -UseBasicParsing `
                    -Method Post `
                    -Uri "$BaseUrl/tts/generate" `
                    -ContentType "application/json; charset=utf-8" `
                    -Body ([Text.Encoding]::UTF8.GetBytes($body)) `
                    -OutFile $pendingPath `
                    -PassThru

                $voices = $response.Headers["X-KokoroTTS-Voices"] -join ","
                $duration = [double]::Parse(
                    ($response.Headers["X-KokoroTTS-Duration"] -join ""),
                    [Globalization.CultureInfo]::InvariantCulture
                )
                $size = (Get-Item -LiteralPath $pendingPath).Length
                if ($voices -ne $example.Voices) {
                    throw "unexpected voices: $voices"
                }
                if ($size -le 10KB) {
                    throw "unexpectedly small output: $size bytes"
                }
                if ($duration -lt $example.MinimumDuration) {
                    throw "unexpectedly short output: $duration seconds"
                }

                Move-Item -LiteralPath $pendingPath -Destination $outputPath -Force
                $completed = $true
                break
            }
            catch {
                $lastError = $_.Exception.Message
                if ($attempt -lt 3) {
                    Write-Warning "$($example.Name) attempt $attempt failed validation: $lastError. Retrying."
                    Start-Sleep -Seconds 2
                }
            }
        }
    }
    finally {
        Remove-Item -LiteralPath $pendingPath -Force -ErrorAction SilentlyContinue
    }
    if (-not $completed) {
        throw "$($example.Name) failed after three attempts: $lastError"
    }

    Write-Output "$($example.Name): $voices, $duration seconds, $size bytes"
    if ($Play) {
        & (Join-Path $PSScriptRoot "play-audio.ps1") -Path $outputPath
    }
}
