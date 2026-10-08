"""Copy the picks marked publish=yes in staging/picks.csv into submissions/, then gate them.

Writes submissions/manifest.json: {"<unit>/<lab>": [{"id", "cohort", "files"}]} for mcdev.
Exit code 1 (and nothing left in submissions/) if the PII/secret gate fails.
"""
import csv
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pii_scan import ROOT, allowed, load_allowlist, scan

STAGING = ROOT / "staging"
OUT = ROOT / "submissions"
BLOCKING = {"secret", "email", "phone", "github_profile", "name", "name_in_path"}


def main():
    with open(STAGING / "picks.csv", encoding="utf-8") as f:
        picks = [r for r in csv.DictReader(f) if r["publish"].strip().lower() in {"yes", "y", "1", "true"}]
    if OUT.exists():
        shutil.rmtree(OUT)
    manifest = {}
    for p in picks:
        src = STAGING / "submissions" / p["unit"] / p["lab"] / p["pseudonym"]
        dest = OUT / p["unit"] / p["lab"] / p["pseudonym"]
        shutil.copytree(src, dest)
        files = sorted(x.relative_to(dest).as_posix() for x in dest.rglob("*") if x.is_file())
        manifest.setdefault(f"{p['unit']}/{p['lab']}", []).append(
            {"id": p["pseudonym"], "cohort": p["pseudonym"].rsplit("-s", 1)[0], "files": files})

    allowlist = load_allowlist()
    hits = [h for h in scan([OUT]) if h[0] in BLOCKING and not allowed(h, allowlist)]
    if hits:
        shutil.rmtree(OUT)
        for h in hits[:20]:
            print("BLOCKED", h[0], h[2], h[3])
        sys.exit(1)

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Student submissions\n\n"
        "A curated selection of real student solutions from PDX Code Guild cohorts (2017–2021), shown to "
        "illustrate different approaches to each lab. They are unedited apart from anonymization: names are "
        "replaced with `Student`, each student has a stable pseudonym (`<cohort>-sNN`), and contact details, "
        "keys and file paths are scrubbed. They have not been run or corrected, so expect the bugs of people learning.\n\n"
        "If you recognize your own work and would like it removed, please open an issue.\n", encoding="utf-8")
    print(f"published {len(picks)} submissions for {len(manifest)} labs")


if __name__ == "__main__":
    main()
