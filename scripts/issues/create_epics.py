import json
import subprocess
from pathlib import Path


def main() -> None:
    manifest = Path("scripts/issues/epics.json")
    if not manifest.exists():
        raise SystemExit("scripts/issues/epics.json not found")

    data = json.loads(manifest.read_text(encoding="utf-8"))
    repo = data.get("repo")
    if not repo:
        raise SystemExit("repo missing in epics.json")

    created = []
    for epic in data.get("epics", []):
        title = epic["title"]
        body = epic["body"]
        labels = epic.get("labels", [])
        milestone = epic.get("milestone")

        cmd = [
            "gh",
            "issue",
            "create",
            "--repo",
            repo,
            "--title",
            title,
            "--body",
            body,
        ]
        if labels:
            cmd += ["--label", ",".join(labels)]
        if milestone:
            cmd += ["--milestone", milestone]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise SystemExit(result.stdout + result.stderr)

        created.append((title, result.stdout.strip()))

    print("CREATED:")
    for title, url in created:
        print(f"{title} -> {url}")


if __name__ == "__main__":
    main()
