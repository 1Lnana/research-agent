$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$dbId = docker compose -f "$projectRoot\compose.yml" -f "$projectRoot\compose.override.yml" ps -q db

if (-not $dbId) {
    throw "PostgreSQL container is not running"
}

$passwordLine = docker inspect $dbId --format '{{range .Config.Env}}{{println .}}{{end}}' |
    Where-Object { $_ -like "POSTGRES_PASSWORD=*" } |
    Select-Object -First 1

if (-not $passwordLine) {
    throw "PostgreSQL password was not found"
}

$password = $passwordLine.Substring("POSTGRES_PASSWORD=".Length)
$encodedPassword = [uri]::EscapeDataString($password)
$env:DATABASE_URL = "postgresql://postgres:$encodedPassword@localhost:5432/app_test"

Push-Location "$projectRoot\backend"
try {
    & "D:\Develop\uv\Scripts\uv.exe" run pytest @args
}
finally {
    Pop-Location
}