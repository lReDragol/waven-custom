$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
python -m PyInstaller --noconfirm --clean --onefile --windowed --name 'Waven Custom' --icon 'assets\waven-custom.ico' --version-file 'packaging\version_info.txt' --hidden-import dialogs app.py
if ($LASTEXITCODE -ne 0) { throw 'Сборка не завершена' }
Write-Output (Join-Path $PSScriptRoot 'dist\Waven Custom.exe')
