param(
    [string]$BaseUrl = "http://localhost:7860",
    [string]$Device = "auto",
    [switch]$Play
)

$ErrorActionPreference = "Stop"
$outputDirectory = Join-Path $env:TEMP "kokorotts_chinese_v11_test"
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

function ConvertFrom-Utf8Base64([string]$Value) {
    return [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($Value))
}

function Invoke-AudioRequest {
    param(
        [string]$Name,
        [string]$Route,
        [hashtable]$Payload,
        [string]$Extension = "mp3",
        [int]$MinimumBytes = 10000
    )

    $outputPath = Join-Path $outputDirectory "$Name.$Extension"
    $body = $Payload | ConvertTo-Json -Compress -Depth 8
    $response = Invoke-WebRequest `
        -UseBasicParsing `
        -Method Post `
        -Uri "$BaseUrl$Route" `
        -ContentType "application/json; charset=utf-8" `
        -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
        -OutFile $outputPath `
        -PassThru

    $size = (Get-Item -LiteralPath $outputPath).Length
    if ($size -le $MinimumBytes) {
        throw "$Name returned only $size bytes."
    }
    Write-Host "PASS $Name ($size bytes)"
    return @{ Path = $outputPath; Response = $response }
}

try {
    Invoke-RestMethod -Uri "$BaseUrl/tts/ping" | Out-Null
    $settings = Invoke-RestMethod -Uri "$BaseUrl/system/settings"
    if ($settings.served_model_families -notcontains "kokoro-v1.1-zh") {
        throw "The Kokoro v1.1 Chinese model family is not enabled."
    }
    if ($settings.served_voices.Count -lt 173) {
        throw "Expected at least 173 served voices, got $($settings.served_voices.Count)."
    }
    Write-Output "PASS discovery ($($settings.served_voices.Count) voices, $($settings.served_model_families.Count) model packs)"

    $female = Invoke-AudioRequest -Name "female" -Route "/tts/generate" -Payload @{
        text = ConvertFrom-Utf8Base64 "5qyi6L+O5L2/55SoIEhhbmdyeSBMYWJzIEtva29ybyDmlofmnKzovazor63pn7PjgILov5nmmK/mlrDnmoTkuK3mloflpbPlo7DmqKHlnovjgII="
        voice = "zf_001"
        device = $Device
        output_format = "mp3"
    }
    $male = Invoke-AudioRequest -Name "male" -Route "/tts/generate" -Payload @{
        text = ConvertFrom-Utf8Base64 "5qyi6L+O5L2/55SoIEhhbmdyeSBMYWJzIEtva29ybyDmlofmnKzovazor63pn7PjgILov5nmmK/mlrDnmoTkuK3mlofnlLflo7DmqKHlnovjgII="
        voice = "zm_010"
        device = $Device
        output_format = "mp3"
    }

    foreach ($voice in @("af_maple", "af_sol", "bf_vale")) {
        Invoke-AudioRequest -Name $voice -Route "/tts/generate" -Payload @{
            text = "The Chinese model family also includes this clear English voice for mixed-language dialogue."
            voice = $voice
            device = $Device
            output_format = "mp3"
        } | Out-Null
    }

    Invoke-AudioRequest -Name "mixed-language" -Route "/tts/generate" -Payload @{
        text = ConvertFrom-Utf8Base64 "5L2g5aW977yBV2VsY29tZSB0byBIYW5ncnkgTGFicyBLb2tvcm8gdGV4dCB0byBzcGVlY2guIOS4reaWh+WSjCBFbmdsaXNoIOWPr+S7peiHqueEtuWcsOWHuueOsOWcqOWQjOS4gOWPpeivnemHjOOAgg=="
        voice = "zf_002"
        device = $Device
        output_format = "mp3"
    } | Out-Null

    Invoke-AudioRequest -Name "audio-controls" -Route "/tts/generate" -Payload @{
        text = ConvertFrom-Utf8Base64 "6L+Z5q616K+t6Z+z6aqM6K+B6Z+z6auY44CB6IqC5aWP5ZKM6Z+z6YeP5o6n5Yi244CC"
        voice = "zf_003"
        device = $Device
        output_format = "mp3"
        speed = 0.95
        pitch_semitones = 1.25
        tempo = 1.05
        volume = 0.9
    } | Out-Null

    Invoke-AudioRequest -Name "stream" -Route "/tts/stream" -Payload @{
        text = ConvertFrom-Utf8Base64 "6L+Z5piv5LiA5Liq5rWB5byP5Lit5paH6K+t6Z+z5rWL6K+V44CC56ys5LqM5Y+l6K+d56Gu6K6k5rWB5Lit5YyF5ZCr5aSa5Liq5a6M5pW054mH5q6144CC"
        voice = "zm_011"
        device = $Device
        stream_format = "mp3"
    } | Out-Null

    $ssmlChineseOpening = ConvertFrom-Utf8Base64 "5L2g5aW977yB5qyi6L+O5p2l5Yiw5aSa5qih5Z6L5a+56K+d44CC"
    $ssmlChineseStandard = ConvertFrom-Utf8Base64 "5qCH5YeG55qEIEtva29ybyDkuK3mloflo7Dpn7PkuZ/lj6/ku6XliqDlhaXlkIzkuIDmrrXlr7nor53jgII="
    $ssml = @"
<speak>
  <voice name="zf_004">$ssmlChineseOpening</voice>
  <break time="120ms"/>
  <voice name="af_maple"><prosody pitch="+1st" tempo="1.05">Hello! The v1.1 family can answer in English too.</prosody></voice>
  <break time="120ms"/>
  <voice name="zf_xiaoxiao">$ssmlChineseStandard</voice>
</speak>
"@
    $dialogue = Invoke-AudioRequest -Name "cross-family-ssml" -Route "/tts/generate" -Payload @{
        text = $ssml
        input_type = "ssml"
        voice = "zf_004"
        device = $Device
        output_format = "mp3"
    } -MinimumBytes 20000
    $dialogueVoices = $dialogue.Response.Headers["X-KokoroTTS-Voices"] -join ","
    if ($dialogueVoices -ne "zf_004,af_maple,zf_xiaoxiao") {
        throw "Unexpected SSML voice metadata: $dialogueVoices"
    }

    $longSentenceOne = ConvertFrom-Utf8Base64 "S29rb3JvVFRTIOato+WcqOmqjOivgei+g+mVv+eahOS4reaWh+WGheWuueOAguavj+S4gOWPpemDveW6lOivpeS/neaMgea4healmuOAgeiHqueEtu+8jOiAjOS4lOS4jeiDveS4ouWkseOAgg=="
    $longSentenceTwo = ConvertFrom-Utf8Base64 "5qih5Z6L5Lya5aSE55CG5qCH54K556ym5Y+344CB5Lit5paH5pWw5a2X5ZKMIEVuZ2xpc2ggd29yZHPvvIznhLblkI7nu6fnu63mnJfor7vlkI7pnaLnmoTlhoXlrrnjgII="
    $longText = ($longSentenceOne + $longSentenceTwo) * 8
    $tokenResponse = Invoke-WebRequest `
        -UseBasicParsing `
        -Method Post `
        -Uri "$BaseUrl/tts/tokenize" `
        -ContentType "application/json; charset=utf-8" `
        -Body ([System.Text.Encoding]::UTF8.GetBytes((@{
            text = $longText
            voice = "zf_005"
        } | ConvertTo-Json -Compress)))
    $tokenJson = [System.Text.Encoding]::UTF8.GetString(
        $tokenResponse.RawContentStream.ToArray()
    )
    $tokens = $tokenJson | ConvertFrom-Json
    if ($tokens.segments.Count -le 1) {
        throw "Long Chinese text was not split into multiple model-safe segments."
    }
    $segmentLengths = @($tokens.segments | ForEach-Object { $_.Length })
    $maximumSegmentLength = [int](
        $segmentLengths | Measure-Object -Maximum
    ).Maximum
    Write-Output "Long Chinese segment lengths: $($segmentLengths -join ', ')"
    if ($maximumSegmentLength -gt 510) {
        throw "Long Chinese tokenization reached $maximumSegmentLength phonemes, above the 510-phoneme model limit."
    }
    $long = Invoke-AudioRequest -Name "long-chinese" -Route "/tts/generate" -Payload @{
        text = $longText
        voice = "zf_005"
        device = $Device
        output_format = "mp3"
    } -MinimumBytes 100000
    Write-Output "PASS long tokenization ($($tokens.segments.Count) segments, maximum $maximumSegmentLength phonemes)"

    if ($Play) {
        & (Join-Path $PSScriptRoot "play-audio.ps1") -Path $female.Path
        & (Join-Path $PSScriptRoot "play-audio.ps1") -Path $male.Path
        & (Join-Path $PSScriptRoot "play-audio.ps1") -Path $dialogue.Path
        & (Join-Path $PSScriptRoot "play-audio.ps1") -Path $long.Path
    }
}
finally {
    Remove-Item -LiteralPath $outputDirectory -Recurse -Force -ErrorAction SilentlyContinue
}
