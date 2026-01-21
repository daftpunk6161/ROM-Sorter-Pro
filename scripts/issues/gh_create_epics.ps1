# ROM-Sorter-Pro: Create epics from issues/epics.json
# Requires: gh auth login

$Repo = "daftpunk6161/Code"
$ManifestPath = Join-Path $PSScriptRoot "..\..\issues\epics.json"

if (-not (Test-Path $ManifestPath)) {
  Write-Error "Manifest not found: $ManifestPath"
  exit 1
}

$manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
$projectNumber = $env:PROJECT_NUMBER
$projectOwner = $env:PROJECT_OWNER
if (-not $projectOwner) { $projectOwner = "daftpunk6161" }

$projectId = $null
$priorityFieldId = $null
$priorityOptions = @{}

if ($projectNumber) {
  $project = gh project view $projectNumber --owner $projectOwner --format json | ConvertFrom-Json
  $projectId = $project.id

  $fields = gh project field-list $projectNumber --owner $projectOwner --format json | ConvertFrom-Json
  foreach ($field in $fields.fields) {
    if ($field.name -eq "Priority" -and $field.options) {
      $priorityFieldId = $field.id
      foreach ($opt in $field.options) {
        $priorityOptions[$opt.name] = $opt.id
      }
    }
  }
}

foreach ($epic in $manifest.epics) {
  $labels = ($epic.labels -join ",")
  $milestone = $epic.milestone
  $body = $epic.body
  $title = $epic.title

  $issueUrl = gh issue create --repo $Repo --title $title --body $body --label $labels --milestone $milestone
  Write-Host "Created: $issueUrl"

  if ($projectNumber) {
    $itemId = gh project item-add $projectNumber --owner $projectOwner --url $issueUrl --format json --jq '.id'
    if ($itemId -and $projectId -and $priorityFieldId) {
      if ($labels -match "priority:P0") { $prio = "P0" }
      elseif ($labels -match "priority:P1") { $prio = "P1" }
      else { $prio = "P2" }
      $optionId = $priorityOptions[$prio]
      if ($optionId) {
        gh project item-edit --project-id $projectId --id $itemId --field-id $priorityFieldId --single-select-option-id $optionId | Out-Null
      }
    }
  }
}
