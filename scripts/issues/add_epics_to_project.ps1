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
$projectList = @()
if ($null -ne $existing.projects) {
    $projectList = $existing.projects
} elseif ($existing -is [System.Array]) {
    $projectList = $existing
} else {
    $projectList = @($existing)
}
$project = $projectList | Where-Object { $_.title -eq $manifest.project_title } | Sort-Object number -Descending | Select-Object -First 1
if (-not $project) {
    throw "Project nicht gefunden: $($manifest.project_title)"
}

$projectNumber = [string]$project.number
Write-Host "Project: $($manifest.project_title) (#$projectNumber)"

foreach ($epic in $manifest.epics) {
    $issue = gh issue list --repo $Repo --search $epic.title --json url,title | ConvertFrom-Json | Where-Object { $_.title -eq $epic.title } | Select-Object -First 1
    if (-not $issue) {
        Write-Host "Issue nicht gefunden: $($epic.title)"
        continue
    }

    try {
        gh project item-add $projectNumber --owner $Owner --url $issue.url | Out-Null
        Write-Host "Zum Project hinzugefügt: $($epic.title)"
    } catch {
        Write-Host "Projekt-Add übersprungen: $($epic.title)"
    }
}

Write-Host "Hinweis: Field-Zuweisungen (Priority/Area/Status) ggf. manuell im Project setzen."
