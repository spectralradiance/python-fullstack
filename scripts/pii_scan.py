"""Gate before publishing: scan a folder for people's names and secrets.

Usage: python -I scripts/pii_scan.py curriculum [submissions ...]

The roster (student folder names + every git author except the maintainer) is built from
raw/_inventory, and the detailed report is written there too, so names never leave raw/.
Exit code 1 if anything unresolved is found.
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIVATE = ROOT / "raw" / "_inventory"

# The maintainer's own names/handles (one per line, private) are not treated as PII.
_self_file = PRIVATE / "maintainer.txt"
SELF = set(_self_file.read_text(encoding="utf-8").lower().split()) if _self_file.exists() else set()
# Tokens from placeholder git identities ("Your Name", "not found", ...), not people.
NOISE = set("you your name not good email found pdx play ever unknown none null local desktop laptop users user".split())
# Roster tokens that are also ordinary words/identifiers; still reported, but as "ambiguous"
# so a reviewer can tell `drew a line` from `Drew's solution`.
COMMON_WORDS = set("""
will mark grant rich art bill jack may june april faith hope joy sky rose page lane drew al kat max ray
dawn chase hunter cash guy case gene young long king hill wood green brown white black gray grey love
star moon summer winter autumn hall bell price walker baker cook mason carter miles frank earl dean
nick pat sam dan ben tim tom don ron jim joe bob ted ed will rob sue ann lee kim jay amber ruby pearl
crystal penny sandy rusty dusty buck colt angel paris london phoenix jordan austin dallas houston
justice august monday wes chip josh mike steve tony ian eric adam paul john james scott peter matt
data code test user admin flux root master main python django student class lab demo
you your name not good email found pdx play ever unknown the and for none null new local desktop laptop
""".split())
SECRET_PATTERNS = {
    "django_secret_key": re.compile(r"SECRET_KEY\s*=\s*['\"](?!django-insecure-REPLACE)[^'\"]{20,}['\"]"),
    "aws_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "google_api_key": re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "slack_or_stripe": re.compile(r"\b(xox[abpr]-[0-9A-Za-z-]{10,}|sk_(live|test)_[0-9A-Za-z]{16,})"),
    "github_token": re.compile(r"\bgh[pousr]_[0-9A-Za-z]{30,}"),
    "assigned_key": re.compile(r"(?i)\b(api[_-]?key|apikey|token|secret|password|passwd|app[_-]?id)\b[\"']?\s*[:=]\s*[\"'][^\"'\s]{12,}[\"']"),
    "key_in_url": re.compile(r"(?i)[?&](api[_-]?key|apikey|appid|key|token|access_token)=[0-9A-Za-z_\-]{16,}"),
}
PII_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"(?<![\d.])\(?\d{3}\)?[-.\s](?!555)(?!456)\d{3}[-.\s]\d{4}(?!\d)"),
    "github_profile": re.compile(r"github\.com/([A-Za-z0-9-]+)", re.I),
}
ALLOWED_EMAIL = re.compile(r"(?i)@(example\.(com|org)|test\.com|email\.com|domain\.com)|noreply|^(user|you|name|me|foo|bar|john|jane|test)@")
PLACEHOLDER = re.compile(r"YOUR_API_KEY|REPLACE-ME|os\.environ")
TEXT_EXTS = {".md", ".py", ".js", ".html", ".css", ".txt", ".json", ".csv", ".vue", ".ipynb", ".yml", ".yaml", ".cfg", ".ini", ".toml"}


def split_tokens(name):
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    return {t.lower() for t in re.findall(r"[A-Za-z]{3,}", name)}


def load_roster():
    people = {}  # token -> set of source labels (kept private)
    with open(PRIVATE / "roster.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for t in split_tokens(row["student_folder"]):
                people.setdefault(t, set()).add(f"student:{row['cohort']}")
    for line in (PRIVATE / "git_authors.txt").read_text(encoding="utf-8").splitlines():
        name, _, email = line.strip().split(" ", 1)[1].partition("|")
        handle = email.split("@")[0]
        for t in split_tokens(name) | split_tokens(handle) | ({handle.lower()} if len(handle) > 3 else set()):
            people.setdefault(t, set()).add("git_author")
    extra = PRIVATE / "extra_names.txt"  # people who never committed under their real name
    if extra.exists():
        for t in extra.read_text(encoding="utf-8").lower().split():
            people.setdefault(t, set()).add("extra")
    for t in SELF | NOISE:
        people.pop(t, None)
    return people


def load_allowlist():
    """Reviewed false positives (private): category<TAB>match<TAB>path substring."""
    path = PRIVATE / "pii_allowlist.tsv"
    if not path.exists():
        return []
    rows = [l.split("\t") for l in path.read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
    return [(c, m.lower(), f) for c, m, f in rows]


def allowed(hit, allowlist):
    cat, match, rel = hit[0], hit[1].lower(), hit[2]
    return any((c == "*" or c == cat) and (m == "*" or m == match) and f in rel for c, m, f in allowlist)


def git_handles():
    """Lower-cased git names/handles of everyone except the maintainer."""
    handles = set()
    for line in (PRIVATE / "git_authors.txt").read_text(encoding="utf-8").splitlines():
        name, _, email = line.strip().split(" ", 1)[1].partition("|")
        handles |= {h.lower().replace(" ", "") for h in (name, email.split("@")[0]) if h}
    return handles - SELF - NOISE


def scan(targets):
    people = load_roster()
    handles = git_handles() | set(people)
    names_re = re.compile(r"(?i)(?<![A-Za-z])(" + "|".join(sorted(map(re.escape, people), key=len, reverse=True)) + r")(?![A-Za-z])")
    hits = []  # (category, token/pattern, file, line_no, line)
    for target in targets:
        for path in sorted(Path(target).rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            for m in names_re.finditer(rel):
                tok = m.group(1).lower()
                hits.append(("name_in_path" if tok not in COMMON_WORDS else "ambiguous_path", tok, rel, 0, ""))
            if path.suffix.lower() not in TEXT_EXTS:
                continue
            for n, line in enumerate(path.read_text("utf-8", "replace").splitlines(), 1):
                snippet = line.strip()[:160]
                for cat, rx in SECRET_PATTERNS.items():
                    m = rx.search(line)
                    if m and not PLACEHOLDER.search(m.group(0)):
                        hits.append(("secret", cat, rel, n, snippet))
                for cat, rx in PII_PATTERNS.items():
                    for m in rx.finditer(line):
                        val = m.group(0)
                        if cat == "email" and ALLOWED_EMAIL.search(val):
                            continue
                        if cat == "github_profile" and m.group(1).lower() not in handles:
                            continue  # library authors etc.; only classmates' profiles matter
                        hits.append((cat, val, rel, n, snippet))
                for m in names_re.finditer(line):
                    tok = m.group(1).lower()
                    hits.append(("name" if tok not in COMMON_WORDS else "ambiguous_name", tok, rel, n, snippet))
    return hits


def main():
    targets = [ROOT / t for t in (sys.argv[1:] or ["curriculum"])]
    allowlist = load_allowlist()
    hits = [h for h in scan(targets) if not allowed(h, allowlist)]
    label = "_".join(Path(t).name for t in targets)
    report = PRIVATE / f"pii_report_{label}.tsv"
    with open(report, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["category", "match", "file", "line", "text"])
        w.writerows(hits)
    counts = {}
    for h in hits:
        counts[h[0]] = counts.get(h[0], 0) + 1
    files = {h[0]: len({x[2] for x in hits if x[0] == h[0]}) for h in hits}
    print(f"report: {report}")
    for cat in sorted(counts):
        print(f"  {cat:<16} {counts[cat]:>5} hits in {files[cat]} files")
    blocking = {"secret", "email", "phone", "github_profile", "name", "name_in_path"}
    sys.exit(1 if blocking & set(counts) else 0)


if __name__ == "__main__":
    main()
