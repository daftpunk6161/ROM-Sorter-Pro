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
    $existing = gh issue list --repo $Repo --search $epic.title --json title,number | ConvertFrom-Json | Where-Object { $_.title -eq $epic.title } | Select-Object -First 1
    if ($existing) {
        Write-Host "Epic existiert bereits: $($epic.title)"
        continue
    }

    $labels = $epic.labels -join ","
    $bodyFile = New-TemporaryFile
    Set-Content -Path $bodyFile -Value $epic.body -Encoding UTF8
    try {
        gh issue create --repo $Repo --title $epic.title --body-file $bodyFile --label $labels --milestone $epic.milestone | Out-Null
        Write-Host "Epic erstellt: $($epic.title)"
    } catch {
        Write-Host "Epic übersprungen: $($epic.title)"
    } finally {
        Remove-Item $bodyFile -ErrorAction SilentlyContinue
    }
}

Write-Host "Epics abgeschlossen für $Repo"
