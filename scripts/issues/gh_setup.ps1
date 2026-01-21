# ROM-Sorter-Pro: GitHub setup (labels, milestones, project)
# Requires: gh auth login

$Repo = "daftpunk6161/Code"
$Owner = "daftpunk6161"

Write-Host "Checking gh auth..."
gh auth status

# Labels (create/update)
$labels = @(
  @{ name = "type:epic"; color = "5319e7"; desc = "Epic issue" },
  @{ name = "priority:P0"; color = "b60205"; desc = "Blocker" },
  @{ name = "priority:P1"; color = "d93f0b"; desc = "High" },
  @{ name = "priority:P2"; color = "0e8a16"; desc = "Normal" },
  @{ name = "area:identification"; color = "1d76db"; desc = "Identification pipeline" },
  @{ name = "area:index"; color = "1d76db"; desc = "DAT index" },
  @{ name = "area:archive"; color = "1d76db"; desc = "Archive awareness" },
  @{ name = "area:normalization"; color = "1d76db"; desc = "Normalization/conversion" },
  @{ name = "area:igir"; color = "1d76db"; desc = "IGIR integration" },
  @{ name = "area:gui"; color = "1d76db"; desc = "GUI/UX" },
  @{ name = "area:ci"; color = "1d76db"; desc = "CI/tooling" }
)

foreach ($label in $labels) {
  gh label create $label.name --repo $Repo --color $label.color --description $label.desc --force
}

# Milestones
$milestones = @("MVP-GUI", "Detection-Accuracy", "Normalization-v1", "CI-Hardening", "Cleanup-Refactor")

$existing = gh api repos/$Repo/milestones --paginate | ConvertFrom-Json
$existingTitles = $existing | ForEach-Object { $_.title }

foreach ($m in $milestones) {
  if ($existingTitles -notcontains $m) {
    gh api repos/$Repo/milestones -f title="$m" -f state="open" | Out-Null
  }
}

# Project v2
$projectTitle = "ROM-Sorter-Pro Roadmap"
$projectId = gh project create --owner $Owner --title $projectTitle --format json --jq '.id'
Write-Host "Project ID: $projectId"

# Priority field (single-select)
if ($projectId) {
  gh project field-create $projectId --name "Priority" --data-type "SINGLE_SELECT" --single-select-options "P0,P1,P2" | Out-Null
}

Write-Host "Setup complete. Save project id in PROJECT_ID env var if needed."
