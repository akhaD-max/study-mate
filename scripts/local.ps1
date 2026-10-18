# Запускать из PowerShell: .\scripts\local.ps1 check
# Формат .env: KEY=value без кавычек, подстановок и многострочных значений.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$environmentPath = Join-Path $projectRoot '.env'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Сначала создайте .venv и установите requirements.txt.'
}
if (-not (Test-Path -LiteralPath $environmentPath)) {
    throw 'Сначала выполните python scripts/setup_env.py.'
}
foreach ($line in Get-Content -LiteralPath $environmentPath -Encoding UTF8) {
    if ($line -match '^\s*(#|$)') { continue }
    if ($line -notmatch '^([A-Z][A-Z0-9_]*)=(.*)$') {
        throw 'Неподдерживаемый формат .env: используйте KEY=value.'
    }
    [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
}
$env:DB_HOST = '127.0.0.1'
$env:DB_PORT = $env:POSTGRES_PORT
if ([string]::IsNullOrWhiteSpace($env:DB_PORT)) { $env:DB_PORT = '5432' }
& $pythonPath (Join-Path $projectRoot 'manage.py') @args
exit $LASTEXITCODE
