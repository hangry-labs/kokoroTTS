param(
    [string]$BaseUrl = "http://localhost:7860",
    [string]$Device = "auto"
)

$ErrorActionPreference = "Stop"
$outputPath = Join-Path $env:TEMP "kokorotts_ssml_dialogue.mp3"
$ssml = @"
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

try {
    Invoke-RestMethod -Uri "$BaseUrl/tts/ping" | Out-Null
    $body = @{
        text = $ssml
        input_type = "ssml"
        voice = "af_heart"
        device = $Device
        output_format = "mp3"
    } | ConvertTo-Json -Compress

    $response = Invoke-WebRequest `
        -UseBasicParsing `
        -Method Post `
        -Uri "$BaseUrl/tts/generate" `
        -ContentType "application/json" `
        -Body $body `
        -OutFile $outputPath `
        -PassThru

    $voices = $response.Headers["X-KokoroTTS-Voices"] -join ","
    $dialogue = $response.Headers["X-KokoroTTS-Dialogue"] -join ","
    if ($voices -ne "af_heart,am_michael") {
        throw "Unexpected dialogue voices: $voices"
    }
    if ($dialogue -ne "true") {
        throw "Dialogue response metadata was not enabled."
    }
    $size = (Get-Item -LiteralPath $outputPath).Length
    if ($size -le 10KB) {
        throw "Generated dialogue was unexpectedly small: $size bytes"
    }

    Write-Output "SSML styled dialogue passed: $voices, $size bytes"
    & (Join-Path $PSScriptRoot "play-audio.ps1") -Path $outputPath
}
finally {
    Remove-Item -LiteralPath $outputPath -Force -ErrorAction SilentlyContinue
}
