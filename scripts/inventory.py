"""Inventory the cohort clones in raw/ straight from git objects (no checkout needed).

Outputs:
  raw/_inventory/files.csv     every file, with student folder names (PII, gitignored)
  raw/_inventory/roster.csv    cohort x student folder x file count (PII, gitignored)
  inventory/lab_matrix.csv     canonical lab x cohort (name-free)
  inventory/summary.md         per-cohort stats and student-file -> lab match coverage (name-free)
"""
import collections
import csv
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
PRIVATE = RAW / "_inventory"
PUBLIC = ROOT / "inventory"

COHORTS = [  # chronological
    "20171003-FullStack-Day", "20180116-FullStack-Day", "class_ocelot", "class_platypus",
    "class_iguana", "class_sheep", "class_emu", "class_honeybadger", "class_raccoon",
    "class_mountain_goat", "class_armadillo", "class_bumble_bee", "class_eagle",
]

UNIT_PATTERNS = [
    ("intro", r"intro|general"),
    ("python", r"python"),
    ("flask_html_css", r"html|css|flask"),
    ("javascript", r"javascript|\bjs\b"),
    ("django", r"django"),
    ("capstone", r"capstone"),
    ("post_course", r"post"),
]
KINDS = {"docs", "labs", "solutions", "practice", "mob", "notebooks", "data", "examples", "demos"}

SYNONYMS = {
    "bogo_sort": "bogosort", "emoticons": "random_emoticon_generator",
    "random_emoticon": "random_emoticon_generator", "socks": "sock_sorter",
    "rot_cipher": "rot13", "random_password_generator": "random_password",
    "quotes_api": "quote_api", "random_quote": "quote_api", "pick_three": "pick_3",
    "redo_three": "redo_3", "bouncing_block": "bouncing_ball", "company": "company_home",
    "mad_lib": "madlib", "contacts": "contact_list", "palindrome": "palindrome_anagram",
    "anagram": "palindrome_anagram", "magic8ball": "magic_8_ball", "magic_8": "magic_8_ball",
    "hello": "hello_world", "tic_tac_toe": "tictactoe",
}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(RAW / repo), "-c", "core.quotepath=off", *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def norm_name(s):
    s = Path(s).stem.lower()
    s = re.sub(r"^(lab|optional|mob|group|practice|bonus)?[\s_-]*\d*(-\d+)?[\s_.-]*", "", s)
    s = re.sub(r"^(lab|optional|mob|group)[\s_-]+", "", s)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    s = re.sub(r"_?(v\d+|version_?\d+|part_?\d+|solution|lab)$", "", s).strip("_")
    return SYNONYMS.get(s, s)


def classify(path):
    parts = path.split("/")
    top = parts[0]
    if top.lower() == "code" and len(parts) > 2:
        return {"area": "student", "student": parts[1], "unit": "", "kind": "submission"}
    unit = ""
    if re.match(r"^\d", top) or re.search(r"intro|general|python|django|javascript|html|capstone|post", top, re.I):
        for key, pat in UNIT_PATTERNS:
            if re.search(pat, top, re.I):
                unit = key
                break
    kind = parts[1].lower() if len(parts) > 2 and parts[1].lower() in KINDS else ("doc" if unit else "")
    return {"area": "curriculum" if unit else "other", "student": "", "unit": unit, "kind": kind}


def main():
    PRIVATE.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    rows, labs = [], collections.defaultdict(dict)  # labs[(unit, key)][cohort] = flag
    for cohort in COHORTS:
        for line in git(cohort, "ls-tree", "-r", "-l", "HEAD").splitlines():
            meta, path = line.split("\t", 1)
            size = meta.split()[3]
            c = classify(path)
            ext = Path(path).suffix.lower().lstrip(".")
            rows.append({"cohort": cohort, "path": path, "size": int(size) if size.isdigit() else 0, "ext": ext, **c})
            if c["kind"] == "labs" and ext == "md":
                stem = Path(path).stem.lower()
                flag = "O" if stem.startswith("optional") else "M" if stem.startswith(("mob", "group")) else "L"
                labs[(c["unit"], norm_name(path))][cohort] = flag

    with open(PRIVATE / "files.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    roster = collections.Counter((r["cohort"], r["student"]) for r in rows if r["area"] == "student")
    with open(PRIVATE / "roster.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cohort", "student_folder", "files"])
        for (c, s), n in sorted(roster.items()):
            w.writerow([c, s, n])

    unit_order = [u for u, _ in UNIT_PATTERNS]
    lab_keys = sorted(labs, key=lambda k: (unit_order.index(k[0]) if k[0] in unit_order else 99, k[1]))
    with open(PUBLIC / "lab_matrix.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["unit", "lab", "n_cohorts", *COHORTS])
        for k in lab_keys:
            w.writerow([*k, len(labs[k]), *(labs[k].get(c, "") for c in COHORTS)])

    # Heuristic: does a student file's normalized name match a known lab key?
    all_keys = {k[1] for k in labs if len(k[1]) > 2}
    code_exts = {"py", "js", "html", "css", "ipynb", "md", "txt"}
    out = ["# Inventory summary", "", f"Cohorts: {len(COHORTS)}  |  Canonical labs: {len(labs)}  |  "
           f"Labs in >= 5 cohorts: {sum(len(v) >= 5 for v in labs.values())}", "",
           "| cohort | files | MB | curriculum md | lab md | solutions | students | student files | student code files | matched to lab |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for cohort in COHORTS:
        rs = [r for r in rows if r["cohort"] == cohort]
        stu = [r for r in rs if r["area"] == "student"]
        code = [r for r in stu if r["ext"] in code_exts]
        matched = sum(any(k in norm_name(r["path"]) or k in r["path"].lower().replace(" ", "_") for k in all_keys) for r in code)
        out.append(f"| {cohort} | {len(rs)} | {sum(r['size'] for r in rs) / 1e6:.0f} | "
                   f"{sum(r['area'] == 'curriculum' and r['ext'] == 'md' for r in rs)} | "
                   f"{sum(r['kind'] == 'labs' and r['ext'] == 'md' for r in rs)} | "
                   f"{sum(r['kind'] == 'solutions' for r in rs)} | {len({r['student'] for r in stu})} | "
                   f"{len(stu)} | {len(code)} | {matched / max(len(code), 1):.0%} |")
    ext_bytes = collections.Counter()
    for r in rows:
        ext_bytes[r["ext"] or "-"] += r["size"]
    out += ["", "## Bytes by extension (top 15, all cohorts)", ""]
    out += [f"- `{e}`: {b / 1e6:.1f} MB" for e, b in ext_bytes.most_common(15)]
    flagged = [r for r in rows if re.search(r"(^|/)(\.env|secrets?\.py|local_settings\.py)$|\.sqlite3$|id_rsa|\.pem$", r["path"], re.I)]
    out += ["", f"## Sensitive-file candidates: {len(flagged)}", ""]
    out += [f"- {e}: {n}" for e, n in collections.Counter(Path(r['path']).name if not r['path'].endswith('sqlite3') else '*.sqlite3' for r in flagged).most_common(10)]
    (PUBLIC / "summary.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
