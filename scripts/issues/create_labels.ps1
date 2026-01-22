param(
    [string]$Repo = ""
)

$manifestPath = Join-Path $PSScriptRoot "..\..\issues\epics.json"
$manifest = Get-Content -Raw $manifestPath | ConvertFrom-Json

if (-not $Repo) { $Repo = $manifest.repo }
if (-not $Repo -or $Repo -eq "OWNER/REPO") {
    $Repo = gh repo view --json nameWithOwner -q ".nameWithOwner"
}

foreach ($label in $manifest.labels) {
    try {
        gh label create $label --repo $Repo --force | Out-Null
        Write-Host "Label erstellt/aktualisiert: $label"
    } catch {
        Write-Host "Label übersprungen: $label"
    }
}

Write-Host "Labels abgeschlossen für $Repo"
