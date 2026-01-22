param(
    [string]$Repo = "",
    [string]$Owner = ""
)

$manifestPath = Join-Path $PSScriptRoot "..\..\issues\epics.json"
$manifest = Get-Content -Raw $manifestPath | ConvertFrom-Json

if (-not $Repo) { $Repo = $manifest.repo }
if (-not $Repo -or $Repo -eq "OWNER/REPO") {
    $Repo = gh repo view --json nameWithOwner -q ".nameWithOwner"
}

if (-not $Owner) {
    $Owner = $Repo.Split("/")[0]
}

$existing = gh project list --owner $Owner --format json | ConvertFrom-Json
$project = $existing | Where-Object { $_.title -eq $manifest.project_title }

if (-not $project) {
    gh project create --title $manifest.project_title --owner $Owner | Out-Null
    $existing = gh project list --owner $Owner --format json | ConvertFrom-Json
    $project = $existing | Where-Object { $_.title -eq $manifest.project_title }
}

if (-not $project) {
    throw "Projekt konnte nicht gefunden/erstellt werden: $($manifest.project_title)"
}

$projectNumber = $project.number
Write-Host "Project: $($manifest.project_title) (#$projectNumber)"

# Fields
$priorityOptions = $manifest.project_fields.Priority -join ","
$areaOptions = $manifest.project_fields.Area -join ","
$statusOptions = $manifest.project_fields.Status -join ","

try { gh project field-create $projectNumber --owner $Owner --name "Priority" --data-type "SINGLE_SELECT" --single-select-options $priorityOptions | Out-Null } catch { }
try { gh project field-create $projectNumber --owner $Owner --name "Area" --data-type "SINGLE_SELECT" --single-select-options $areaOptions | Out-Null } catch { }
try { gh project field-create $projectNumber --owner $Owner --name "Status" --data-type "SINGLE_SELECT" --single-select-options $statusOptions | Out-Null } catch { }

Write-Host "Project-Felder erstellt (oder bereits vorhanden)."
