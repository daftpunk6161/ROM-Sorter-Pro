param(
    [string]$Repo = ""
)

$manifestPath = Join-Path $PSScriptRoot "..\..\issues\epics.json"
$manifest = Get-Content -Raw $manifestPath | ConvertFrom-Json

if (-not $Repo) { $Repo = $manifest.repo }
if (-not $Repo -or $Repo -eq "OWNER/REPO") {
    $Repo = gh repo view --json nameWithOwner -q ".nameWithOwner"
}

foreach ($milestone in $manifest.milestones) {
    try {
        gh api --method POST "repos/$Repo/milestones" -f title="$milestone" | Out-Null
        Write-Host "Milestone erstellt: $milestone"
    } catch {
        Write-Host "Milestone übersprungen: $milestone"
    }
}

Write-Host "Milestones abgeschlossen für $Repo"
