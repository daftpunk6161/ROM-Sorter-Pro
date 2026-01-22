param(
    [string]$Repo = ""
)

$manifestPath = Join-Path $PSScriptRoot "..\..\issues\epics.json"
$manifest = Get-Content -Raw $manifestPath | ConvertFrom-Json

if (-not $Repo) { $Repo = $manifest.repo }
if (-not $Repo -or $Repo -eq "OWNER/REPO") {
    $Repo = gh repo view --json nameWithOwner -q ".nameWithOwner"
}

foreach ($epic in $manifest.epics) {
    $labels = $epic.labels -join ","
    try {
        gh issue create --repo $Repo --title $epic.title --body $epic.body --label $labels --milestone $epic.milestone | Out-Null
        Write-Host "Epic erstellt: $($epic.title)"
    } catch {
        Write-Host "Epic übersprungen: $($epic.title)"
    }
}

Write-Host "Epics abgeschlossen für $Repo"
