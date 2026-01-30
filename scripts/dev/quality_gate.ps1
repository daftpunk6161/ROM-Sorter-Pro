#!/usr/bin/env pwsh
#Requires -Version 5.1
<#
.SYNOPSIS
    Quality gate script for ROM-Sorter-Pro (Windows PowerShell).
.DESCRIPTION
    Runs pytest, ruff, and optionally pyright/bandit to validate code quality.
.EXAMPLE
    .\scripts\dev\quality_gate.ps1
    .\scripts\dev\quality_gate.ps1 -Full
#>
param(
    [switch]$Full,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($Help) {
    Get-Help $MyInvocation.MyCommand.Path -Detailed
    exit 0
}

$RepoRoot = (Get-Item $PSScriptRoot).Parent.Parent.FullName
Push-Location $RepoRoot

try {
    $Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $Python)) {
        $Python = "python"
    }

    Write-Host "`n=== Running Ruff ===" -ForegroundColor Cyan
    & $Python -m ruff check .
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Ruff failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "Ruff: OK" -ForegroundColor Green

    Write-Host "`n=== Running Pytest ===" -ForegroundColor Cyan
    & $Python -m pytest -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Pytest failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "Pytest: OK" -ForegroundColor Green

    if ($Full) {
        Write-Host "`n=== Running Pyright ===" -ForegroundColor Cyan
        $PyrightPath = Get-Command pyright -ErrorAction SilentlyContinue
        if ($PyrightPath) {
            & pyright
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Pyright failed!" -ForegroundColor Yellow
            } else {
                Write-Host "Pyright: OK" -ForegroundColor Green
            }
        } else {
            Write-Host "Pyright not installed, skipping." -ForegroundColor Yellow
        }

        Write-Host "`n=== Running Bandit ===" -ForegroundColor Cyan
        & $Python -m bandit -c .bandit.yaml -r src -q
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Bandit found issues!" -ForegroundColor Yellow
        } else {
            Write-Host "Bandit: OK" -ForegroundColor Green
        }
    }

    Write-Host "`n=== Quality Gate PASSED ===" -ForegroundColor Green
    exit 0
}
finally {
    Pop-Location
}
