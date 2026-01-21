# Milestones (GH CLI)

Create milestones via GH API:

```
# MVP-GUI
# Detection-Accuracy
# Normalization-v1
# CI-Hardening
# Cleanup-Refactor
```

PowerShell example:
```
$milestones = @('MVP-GUI','Detection-Accuracy','Normalization-v1','CI-Hardening','Cleanup-Refactor')
foreach ($m in $milestones) {
  gh api -X POST repos/daftpunk6161/Code/milestones -f title="$m" | Out-Null
}
```
