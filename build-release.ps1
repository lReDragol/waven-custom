param([string]$Version='2.1.0', [string]$ISCC, [switch]$SkipPlayer)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not $SkipPlayer) { & .\build.ps1 }
if (-not $ISCC) {
    $candidates=@(
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
        (Join-Path $env:ProgramFiles 'Inno Setup 7\ISCC.exe'))
    $ISCC=$candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $ISCC) { throw 'Установите Inno Setup 6/7 или передайте -ISCC с путём к ISCC.exe.' }
$stage=Join-Path $PSScriptRoot ('build\portable-'+[guid]::NewGuid().ToString('N'))
$portable=Join-Path $stage 'Waven Custom'
New-Item -ItemType Directory -Force -Path $portable,(Join-Path $PSScriptRoot 'releases') | Out-Null
Copy-Item -LiteralPath '.\dist\Waven Custom.exe' -Destination $portable -Force
Copy-Item -LiteralPath '.\packaging\portable.flag','.\packaging\ПРОЧИТАЙТЕ.txt' -Destination $portable -Force
$zip=Join-Path $PSScriptRoot ('releases\WavenCustom-Portable-'+$Version+'-x64.zip')
Compress-Archive -LiteralPath $portable -DestinationPath $zip -Force
& $ISCC ('/DAppVersion='+$Version) '.\installer\waven.iss'
if ($LASTEXITCODE -ne 0) { throw 'Сборка установщика завершилась ошибкой.' }
Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'releases') | Select-Object Name,Length
