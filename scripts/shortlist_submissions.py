"""Shortlist anonymized student submissions for each core lab.

Student code is never executed: quality checks are static (ast parse, size, structure).

Outputs (all git-ignored until published):
  staging/submissions/<unit>/<lab>/<pseudonym>/...   anonymized, sanitized, gate-checked copies
  staging/shortlist.csv                               every candidate considered, with scores
  staging/picks.csv                                   recommended picks (edit to change)
  staging/review.html                                 local page to compare candidates
  raw/_inventory/pseudonyms.csv                       real folder -> pseudonym (private)
"""
import ast
import csv
import difflib
import hashlib
import html
import json
import re
import secrets
import shutil
import statistics
import sys
import warnings
from collections import defaultdict
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_curriculum import (CODE_EXTS, SKIP_NAMES, SKIP_PARTS, UNITS, Repo, lab_key, norm_name,
                              solution_keys)
from inventory import COHORTS
from pii_scan import COMMON_WORDS, PRIVATE, ROOT, allowed, load_allowlist, load_roster, scan, split_tokens
from sanitize import roster_handles, sanitize_text

warnings.filterwarnings("ignore", category=SyntaxWarning)  # from parsing student code

STAGING = ROOT / "staging"
UNIT_DIR = {key: folder for key, folder, _, _ in UNITS}
PERSONAL_LABS = {"bio", "personal_portfolio", "blog"}  # in flask_html_css: the content is the student
GENERIC_LABS = {"practice"}  # name matches any scratch file called practice.*
BLOCKING = {"secret", "email", "phone", "github_profile", "name", "name_in_path"}
# Ambiguous roster tokens that are ordinary words (or code identifiers), kept even when capitalized.
ENGLISH_WORDS = set("""
will mark grant rich art bill jack may june april faith hope joy sky rose page lane drew dawn chase
hunter cash guy case gene young long king hill wood green brown white black gray grey love star moon
summer winter autumn hall bell price walker baker cook mason carter miles frank earl dean pat rob sue
amber ruby pearl crystal penny sandy rusty dusty buck colt angel justice august monday chip max ray
data code test user admin root master main python django student class lab demo the and for none
null new local desktop laptop
""".split())
PER_LAB = 3         # candidates kept per lab
RECOMMENDED = 2      # of which pre-selected
MAX_FOLDER_BYTES = 150_000
COHORT_SHORT = {c: c.replace("class_", "").replace("_", "-") for c in COHORTS}
COHORT_SHORT |= {"20171003-FullStack-Day": "fall17", "20180116-FullStack-Day": "winter18"}


def compact(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


class LabIndex:
    """Map a path segment to a lab key, using names plus each cohort's own lab numbering."""

    def __init__(self, manifest, repos):
        self.labs = {}  # key -> (unit, lab dict)
        for u in manifest["units"]:
            for lab in u["labs"]:
                if (lab["tier"] == "core" and lab["key"] not in GENERIC_LABS
                        and not (u["key"] == "flask_html_css" and lab["key"] in PERSONAL_LABS)):
                    self.labs.setdefault(lab["key"], []).append((u["key"], lab))
        self.compact = {compact(k): k for k in self.labs}
        self.numbering = defaultdict(dict)  # (cohort, unit) -> {num: key}
        for repo in repos:
            for p in repo.files:
                parts = p.split("/")
                if len(parts) == 3 and parts[1].lower() == "labs" and p.endswith(".md"):
                    n = re.match(r"^lab(\d+)", PurePosixPath(p).stem.lower())
                    unit = next((k for k, _, _, pat in UNITS if re.search(pat, parts[0], re.I)), None)
                    if n and unit:
                        self.numbering[(repo.name, unit)][int(n.group(1))] = lab_key(p)

    def match(self, name):
        """Lab key for a file stem / folder name, or None."""
        for k in solution_keys(name) | {lab_key(name)}:
            if k in self.labs:
                return k
        c = compact(norm_name(name))
        if c in self.compact:
            return self.compact[c]
        for ck, k in self.compact.items():
            if len(ck) >= 6 and (c.startswith(ck) or c.endswith(ck)):
                return k
        return None

    def by_number(self, cohort, name, unit):
        n = re.fullmatch(r"lab_?(\d+)", PurePosixPath(name).stem.lower())
        key = self.numbering[(cohort, unit)].get(int(n.group(1))) if n else None
        return key if key in self.labs else None


def kind_fits(unit, files):
    exts = {PurePosixPath(f).suffix.lower() for f in files}
    names = {PurePosixPath(f).name.lower() for f in files}
    if unit == "python":
        return exts <= {".py", ".txt", ".csv", ".json", ".md"} and ".py" in exts and "models.py" not in names
    if unit == "django":
        return "views.py" in names or "models.py" in names
    if unit == "javascript":
        return bool(exts & {".html", ".js", ".vue"}) and ".py" not in exts
    if unit == "flask_html_css":
        return bool(exts & {".html", ".css"}) or "app.py" in names
    return False


def code_stats(files):
    """Static quality signals over the submission's text files."""
    loc = funcs = comments = 0
    parse_ok = True
    for name, text in files.items():
        lines = [l for l in text.splitlines() if l.strip()]
        loc += len(lines)
        comments += sum(l.strip().startswith(("#", "//", "<!--")) for l in lines)
        if name.endswith(".py"):
            try:
                tree = ast.parse(text)
                funcs += sum(isinstance(n, (ast.FunctionDef, ast.ClassDef)) for n in ast.walk(tree))
            except (SyntaxError, ValueError):
                parse_ok = False
        elif name.endswith((".js", ".html")):
            funcs += len(re.findall(r"\bfunction\b|=>|methods\s*:", text))
    return {"loc": loc, "funcs": funcs, "comments": comments, "parse_ok": parse_ok}


NAME = r"[A-Z][a-z]+(?:[ -][A-Z][a-z]+){0,2}"
ATTRIBUTION = [
    # a comment line that is only a name: "# Jane Doe", "// Jane", "<!-- Jane Doe -->"
    (re.compile(rf"^(\s*(?:#|//|<!--)\s*){NAME}(\s*(?:-->)?\s*)$", re.M), r"\1Student\2"),
]
# Lines that credit people. Every capitalized name after the marker is replaced; markup and
# punctuation are kept. "by"/"with" only count on comment lines, so code such as
# `with Image.open(...)` is untouched.
COPYRIGHT = re.compile(r"&copy;?|©|\(c\)\s*\d{4}", re.I)
COMMENT_LINE = re.compile(r"^\s*(#|//|/\*|\*|<!--)")
CREDIT = re.compile(r"(?i)\b(by|author|with)\b\s*:?")
KEEP_CAPS = {"Student", "Class", "Lab", "Code", "Guild", "Python", "Django", "Vue", "JavaScript"}


def _names_to_student(s):
    return re.sub(NAME, lambda m: m.group(0) if m.group(0).split()[0] in KEEP_CAPS else "Student", s)


def scrub_attribution(text):
    for rx, repl in ATTRIBUTION:
        text = rx.sub(repl, text)
    out = []
    for line in text.split("\n"):
        if COPYRIGHT.search(line):
            line = re.sub(r">([^<]*)<", lambda m: ">" + _names_to_student(m.group(1)) + "<", line)
            line = re.sub(rf"^(\s*){NAME}(?=\s*\|)", r"\1Student", line)
        elif COMMENT_LINE.match(line):
            m = CREDIT.search(line)
            if m:
                line = line[:m.end()] + " " + _names_to_student(line[m.end():]).lstrip()
        out.append(line)
    return "\n".join(out)


def anonymize(text, own_tokens, roster_re):
    text = scrub_attribution(text)
    # The student's own name (even if it is also a common word) when capitalized as a name.
    for t in own_tokens:
        text = re.sub(rf"(?<![A-Za-z]){re.escape(t.capitalize())}(?![a-z])", "Student", text)
        text = re.sub(rf"(?<![A-Za-z]){re.escape(t.upper())}(?![A-Z])", "STUDENT", text)
    # Everyone else on the roster. Ambiguous tokens are kept when they are real English words,
    # but a capitalized first name that is only a name ("Matt helped me") is still replaced.
    def repl(m):
        tok = m.group(1)
        if tok.lower() not in COMMON_WORDS:
            return "Student"
        return "Student" if tok[0].isupper() and tok.lower() not in ENGLISH_WORDS else tok
    return roster_re.sub(repl, text)


def pseudonyms(roster_rows):
    """Stable, non-reversible pseudonyms: <cohort>-s<NN>, numbered by salted hash order."""
    salt_file = PRIVATE / "pseudonym_salt"
    if not salt_file.exists():
        salt_file.write_text(secrets.token_hex(16), encoding="utf-8")
    salt = salt_file.read_text(encoding="utf-8").strip()
    by_cohort = defaultdict(list)
    for cohort, student in roster_rows:
        by_cohort[cohort].append(student)
    out = {}
    for cohort, students in by_cohort.items():
        ordered = sorted(students, key=lambda s: hashlib.sha256(f"{salt}:{cohort}:{s}".encode()).hexdigest())
        for i, s in enumerate(ordered, 1):
            out[(cohort, s)] = f"{COHORT_SHORT[cohort]}-s{i:02d}"
    with open(PRIVATE / "pseudonyms.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cohort", "student_folder", "pseudonym"])
        w.writerows([c, s, p] for (c, s), p in sorted(out.items()))
    return out


def find_submissions(repo, index):
    """Yield (student, unit, lab_key, root, [rel files]) for one cohort."""
    groups = defaultdict(list)  # (student, root) -> files
    for p, size in repo.files.items():
        parts = p.split("/")
        if parts[0].lower() != "code" or len(parts) < 3:
            continue
        if set(x.lower() for x in parts) & SKIP_PARTS or SKIP_NAMES.search(p):
            continue
        student, rel = parts[1], parts[2:]
        if any("capstone" in x.lower() for x in rel):
            continue
        # Deepest matching segment wins: a file match is a single-file submission,
        # a folder match makes the whole folder the submission.
        for depth in range(len(rel) - 1, -1, -1):
            seg = rel[depth]
            name = PurePosixPath(seg).stem if depth == len(rel) - 1 else seg
            key = index.match(name)
            if not key and depth == len(rel) - 1:
                key = index.by_number(repo.name, seg, "python") if seg.endswith(".py") else None
            if key:
                groups[(student, key, "/".join(parts[:3 + depth]))].append((p, size))
                break
    for (student, key, root), files in groups.items():
        files = [(p, s) for p, s in files if PurePosixPath(p).suffix.lower() in CODE_EXTS]
        if not files or sum(s for _, s in files) > MAX_FOLDER_BYTES:
            continue
        for unit, lab in index.labs[key]:
            if kind_fits(unit, [p for p, _ in files]):
                yield student, unit, lab, root, files
                break


def main():
    manifest = json.loads((ROOT / "curriculum" / "manifest.json").read_text(encoding="utf-8"))
    repos = [Repo(c) for c in COHORTS]
    index = LabIndex(manifest, repos)
    people = load_roster()
    roster_re = re.compile(r"(?<![A-Za-z])(" + "|".join(sorted(map(re.escape, people), key=len, reverse=True)) + r")(?![A-Za-z])", re.I)
    handles = roster_handles()
    allowlist = load_allowlist()
    with open(PRIVATE / "roster.csv", encoding="utf-8") as f:
        roster_rows = [(r["cohort"], r["student_folder"]) for r in csv.DictReader(f)]
    names = pseudonyms(roster_rows)

    # 1. collect candidates, keeping the largest version per student x lab
    cands = {}
    for repo in repos:
        for student, unit, lab, root, files in find_submissions(repo, index):
            texts = {}
            for p, _ in files:
                rel = p[len(root) + 1:] if p != root else PurePosixPath(p).name
                texts[rel or PurePosixPath(p).name] = repo.read(p).decode("utf-8", "replace")
            stats = code_stats(texts)
            k = (repo.name, student, unit, lab["key"])
            if k not in cands or stats["loc"] > cands[k]["stats"]["loc"]:
                cands[k] = {"cohort": repo.name, "student": student, "unit": unit, "lab": lab,
                            "root": root, "texts": texts, "stats": stats}

    # 2. score per lab and pick diverse candidates that survive anonymization + the gate
    if STAGING.exists():
        shutil.rmtree(STAGING)
    (STAGING / "submissions").mkdir(parents=True)
    by_lab = defaultdict(list)
    for c in cands.values():
        by_lab[(c["unit"], c["lab"]["key"])].append(c)

    shortlist_rows, picks_rows, review = [], [], []
    stats_total = {"labs": 0, "with_picks": 0, "candidates": len(cands), "dropped_gate": 0}
    for (unit, key), cs in sorted(by_lab.items(), key=lambda kv: (list(UNIT_DIR).index(kv[0][0]), kv[0][1])):
        lab = cs[0]["lab"]
        stats_total["labs"] += 1
        solution_text = ""
        if lab["solution"]:
            sol_dir = ROOT / "curriculum" / UNIT_DIR[unit] / "labs" / lab["slug"]
            solution_text = "\n".join((sol_dir / f).read_text("utf-8", "replace") for f in lab["solution"]["files"]
                                      if (sol_dir / f).suffix in {".py", ".html", ".js"})
        median_loc = statistics.median(c["stats"]["loc"] for c in cs)
        for c in cs:
            s = c["stats"]
            joined = "\n".join(c["texts"].values())
            c["copy_of_solution"] = bool(solution_text) and difflib.SequenceMatcher(None, joined[:6000], solution_text[:6000]).quick_ratio() > 0.9
            closeness = 1 - min(abs(s["loc"] - median_loc) / max(median_loc, 1), 1)
            c["score"] = round((2 * s["parse_ok"]) + closeness + min(s["funcs"], 5) / 5
                               + min(s["comments"] / max(s["loc"], 1) * 5, 1) - 3 * c["copy_of_solution"]
                               - 2 * (s["loc"] < 8), 3)
        ranked = sorted(cs, key=lambda c: -c["score"])
        picked = []
        for c in ranked:
            if len(picked) >= PER_LAB:
                break
            if c["copy_of_solution"] or not c["stats"]["parse_ok"] or c["stats"]["loc"] < 8:
                continue
            joined = "\n".join(c["texts"].values())
            if any(difflib.SequenceMatcher(None, joined[:4000], "\n".join(p["texts"].values())[:4000]).quick_ratio() > 0.85 for p in picked):
                continue  # too similar to one already picked
            pseudo = names[(c["cohort"], c["student"])]
            dest = STAGING / "submissions" / UNIT_DIR[unit] / lab["slug"] / pseudo
            own = split_tokens(c["student"]) - {"code"}
            for rel, text in c["texts"].items():
                rel_clean = anonymize(rel, own, roster_re)
                out = sanitize_text(anonymize(text, own, roster_re), f"submissions/{rel_clean}", handles)
                (dest / rel_clean).parent.mkdir(parents=True, exist_ok=True)
                (dest / rel_clean).write_text(out, encoding="utf-8")
            hits = [h for h in scan([dest]) if h[0] in BLOCKING and not allowed(h, allowlist)]
            if hits:
                shutil.rmtree(dest)
                stats_total["dropped_gate"] += 1
                c["dropped"] = sorted({h[0] for h in hits})
                continue
            c["pseudonym"] = pseudo
            picked.append(c)
        for c in cs:
            shortlist_rows.append([unit, lab["slug"], names[(c["cohort"], c["student"])], c["cohort"], c["stats"]["loc"],
                                   c["stats"]["funcs"], c["stats"]["parse_ok"], c["copy_of_solution"], c["score"],
                                   "picked" if c in picked else ";".join(c.get("dropped", [])) or ""])
        if picked:
            stats_total["with_picks"] += 1
        for i, c in enumerate(picked):
            picks_rows.append([UNIT_DIR[unit], lab["slug"], c["pseudonym"], "yes" if i < RECOMMENDED else "no",
                               c["stats"]["loc"], len(c["texts"])])
        review.append((unit, lab, len(cs), picked))

    with open(STAGING / "shortlist.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["unit", "lab", "pseudonym", "cohort", "loc", "funcs", "parses", "copy_of_solution", "score", "status"])
        w.writerows(shortlist_rows)
    with open(STAGING / "picks.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["unit", "lab", "pseudonym", "publish", "loc", "files"])
        w.writerows(picks_rows)
    write_review(review)
    print(json.dumps(stats_total))
    print(f"picks: {len(picks_rows)} candidates staged, {sum(r[3] == 'yes' for r in picks_rows)} recommended")


def write_review(review):
    parts = ["<!doctype html><meta charset=utf-8><title>Submission shortlist</title>",
             "<style>body{font:14px system-ui;max-width:1100px;margin:auto;padding:16px}pre{background:#f5f5f5;"
             "padding:8px;overflow:auto;max-height:400px}details{margin:4px 0}.rec{color:#070}h2{border-bottom:1px solid #ccc}</style>",
             "<h1>Submission shortlist</h1><p>Recommended picks are marked. Edit <code>staging/picks.csv</code> "
             "(publish = yes/no) or tell Claude which to change.</p>"]
    unit = None
    for u, lab, n, picked in review:
        if u != unit:
            parts.append(f"<h2>{html.escape(u)}</h2>")
            unit = u
        parts.append(f"<h3>{html.escape(lab['title'])} <small>({n} submissions found, {len(picked)} shortlisted)</small></h3>")
        for i, c in enumerate(picked):
            tag = "<span class=rec>recommended</span>" if i < RECOMMENDED else "alternate"
            dest = STAGING / "submissions" / UNIT_DIR[u] / lab["slug"] / c["pseudonym"]
            body = "".join(f"<p><code>{html.escape(p.relative_to(dest).as_posix())}</code></p><pre>{html.escape(p.read_text('utf-8', 'replace'))}</pre>"
                           for p in sorted(dest.rglob("*")) if p.is_file())
            parts.append(f"<details><summary>{c['pseudonym']} — {tag} — {c['stats']['loc']} lines</summary>{body}</details>")
    (STAGING / "review.html").write_text("\n".join(parts), encoding="utf-8")


if __name__ == "__main__":
    main()
