$labels = @(
  @{ name = 'priority:P0'; color = 'b60205' },
  @{ name = 'priority:P1'; color = 'd93f0b' },
  @{ name = 'priority:P2'; color = 'fbca04' },
  @{ name = 'area:detection'; color = '1d76db' },
  @{ name = 'area:conversion'; color = '0e8a16' },
  @{ name = 'area:gui'; color = '5319e7' },
  @{ name = 'area:scanner'; color = '006b75' },
  @{ name = 'area:security'; color = 'b60205' },
  @{ name = 'area:db'; color = '0052cc' },
  @{ name = 'area:tests'; color = 'c5def5' },
  @{ name = 'area:cleanup'; color = 'fef2c0' },
  @{ name = 'area:ci'; color = '0e8a16' },
  @{ name = 'area:docs'; color = '0075ca' },
  @{ name = 'area:config'; color = 'f9d0c4' },
  @{ name = 'type:bug'; color = 'd73a4a' },
  @{ name = 'type:feature'; color = 'a2eeef' },
  @{ name = 'type:refactor'; color = 'cfd3d7' },
  @{ name = 'type:test'; color = 'c2e0c6' },
  @{ name = 'type:chore'; color = 'ededed' }
)

foreach ($label in $labels) {
  gh label create $label.name --color $label.color --force | Out-Null
}

Write-Host "Labels created/updated."