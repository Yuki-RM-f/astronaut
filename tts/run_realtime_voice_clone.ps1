$ErrorActionPreference = "Stop"
chcp 65001 > $null
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "未找到虚拟环境 Python：$python"
}

& $python -m voice_clone_app
pause

