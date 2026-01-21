# Project Setup (GitHub Projects v2)

Goal: Create project "ROM-Sorter-Pro Roadmap" with columns Todo / In Progress / Done and add epic issues.

## CLI Steps (gh project)
1) Ensure project scopes:
```
gh auth refresh -s project,read:project
```

2) Create the project:
```
gh project create --owner daftpunk6161 --title "ROM-Sorter-Pro Roadmap"
```

3) Add a Status field with options:
```
# Replace PROJECT_ID with the created project id from the command output.
gh project field-create PROJECT_ID --owner daftpunk6161 --name Status --type single_select \
  --single-select-options "Todo,In Progress,Done"
```

4) Add epic issues to the project:
```
# Replace PROJECT_ID and ISSUE_IDS
for id in ISSUE_IDS; do
  gh project item-add PROJECT_ID --owner daftpunk6161 --content-id $id
done
```

## UI Steps (if CLI not available)
- GitHub → Projects → New project → Name "ROM-Sorter-Pro Roadmap".
- Add Status field with options Todo / In Progress / Done.
- Add epic issues to project.
