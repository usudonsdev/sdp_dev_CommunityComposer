# ローカル開発用: localhost の OAuth リダイレクトで起動
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")
docker compose -f compose.yaml -f compose.local.yaml up -d --build @args

Write-Host ""
Write-Host "Local dev started."
Write-Host "  UI:  http://localhost:8080/login"
Write-Host "  API: http://localhost:8000"
Write-Host "  OAuth redirect: http://localhost:8080/auth/google/callback"
