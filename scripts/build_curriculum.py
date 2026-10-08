"""Merge the 13 cohort repos into one canonical curriculum under curriculum/.

Rules (see README):
  - Each doc / lab is keyed by a normalized name; the newest cohort's version wins.
  - Reference repos (PythonFullStack, PythonFullStack2) are compared against, never copied.
  - Unit placement and ordering follow the newest cohort that contains the item.
  - Text drift between oldest and newest version is flagged for review.
  - One reference solution per lab: newest cohort with a matching file/folder under solutions/.

Outputs: curriculum/**, curriculum/manifest.json, inventory/provenance.csv
"""
import csv
import difflib
import os
import json
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inventory import COHORTS, RAW, ROOT, norm_name
from pii_scan import COMMON_WORDS, load_roster

OUT = ROOT / "curriculum"
REFERENCES = ["_reference/PythonFullStack2", "_reference/PythonFullStack"]

UNITS = [  # key, folder, title, matcher on the cohort's top-level folder name
    ("general", "00-general", "General", r"intro|general"),
    ("python", "01-python", "Python", r"python"),
    ("flask_html_css", "02-flask-html-css", "Flask + HTML + CSS", r"html|css|flask"),
    ("django", "03-django", "Django", r"django"),
    ("javascript", "04-javascript", "JavaScript", r"javascript"),
    ("capstone", "05-capstone", "Capstone", r"capstone"),
    ("post_course", "06-post-course", "Post-Course", r"post"),
]
UNIT_KEYS = [u[0] for u in UNITS]
CODE_EXTS = {".py", ".js", ".html", ".css", ".md", ".txt", ".json", ".ipynb", ".csv", ".vue"}
SKIP_PARTS = {"__pycache__", "node_modules", "venv", ".venv", "env", "migrations", ".idea", ".vscode"}
SKIP_NAMES = re.compile(r"(\.sqlite3|\.pyc|\.DS_Store|\.icloud|\.back|secrets?\.py|local_settings\.py|\.env)$", re.I)
MAX_SOLUTION_BYTES = 200_000
IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)[^)]*\)|<img[^>]+src=[\"']([^\"']+)[\"']", re.I)
DOC_STOP = {"and", "the"}

# Docs renamed between eras. Docs merged or split (e.g. using/defining functions -> functions)
# are not aliased; they fall into the archived tier instead.
DOC_ALIASES = {
    "fileio": "file_io", "while_for_loops": "loops", "imports_modules_packages": "modules_packages",
    "python:overview": "python_overview", "javascript:overview": "javascript_overview",
    "javascript:fundamentals": "javascript_fundamentals", "datetime": "datetimes", "virtualenv": "virtual_environments",
    "objectives": "objectives_activities", "programming": "programming_overview",
    "css_bootstrap_materialize": "css_bootstrap",
    "comparisons_conditionals": "booleans_comparisons_conditionals",
    "booleans_conditionals": "booleans_comparisons_conditionals", "ajax": "apis_ajax",
    "timing_events": "timing", "vanilla_js_vs_vue": "vue_vs_vanilla",
}
RECENT = 4  # an item not used in any of the last RECENT cohorts is "archived"
TIERS = ["core", "mob", "optional", "archived"]

# Labs whose normalized names differ but are the same assignment.
LAB_ALIASES = {
    "pick3": "pick_3", "cc_validation": "credit_card_validation", "s_hangman": "hangman",
    "vue_todos": "vue_todo", "todolist": "todo", "comsci_data_structures": "compsci_data_structures",
    "quotes": "quote_api", "any_api_vue": "any_api", "vanilla_quiz": "quiz", "todo2": "todo",
    "rps": "rock_paper_scissors",
}


def unit_of(top):
    for key, _, _, pat in UNITS:
        if re.search(pat, top, re.I):
            return key
    return None


class Repo:
    def __init__(self, name):
        self.name = name
        self.path = RAW / name
        out = self._git("ls-tree", "-r", "-l", "HEAD").decode("utf-8", "replace")
        self.files = {}
        for line in out.splitlines():
            meta, p = line.split("\t", 1)
            size = meta.split()[3]
            self.files[p] = int(size) if size.isdigit() else 0

    def _git(self, *args):
        return subprocess.run(["git", "-C", str(self.path), "-c", "core.quotepath=off", *args],
                              capture_output=True, check=True).stdout

    def read(self, p):
        return self._git("show", f"HEAD:{p}")


def doc_key(path, unit):
    s = PurePosixPath(path).stem.lower()
    s = re.sub(r"^\d+\s*[-.]?\s*", "", s).replace("&", " ").replace("+", " ")
    words = [w for w in re.findall(r"[a-z0-9]+", s) if w not in DOC_STOP]
    key = "_".join(words)
    return DOC_ALIASES.get(f"{unit}:{key}", DOC_ALIASES.get(key, key))


def lab_key(path):
    k = norm_name(path)
    k = re.sub(r"^bed_", "", k) or slugify(PurePosixPath(path).stem).replace("-", "_")
    return LAB_ALIASES.get(k, k)


SOLUTION_ALIASES = {"shortener": "url_shortener", "contacts": "contact_list", "dadjokes": "dad_joke_api",
                    "blackjack": "blackjack_advice", "mysite": "polls"}


def solution_keys(name):
    """Solution files/folders -> candidate lab keys: 'shortenerproj' -> url_shortener,
    'lab08_pick6' -> pick6, 'lab22-rain_data2' -> rain_data."""
    k = re.sub(r"_?(proj|project|app|site|demo|example)$", "", norm_name(name)) or norm_name(name)
    keys = {k, re.sub(r"_?\d+$", "", k)}
    return {SOLUTION_ALIASES.get(x, LAB_ALIASES.get(x, x)) for x in keys if x}


def lab_flag(path):
    stem = PurePosixPath(path).stem.lower()
    return "optional" if stem.startswith("optional") else "mob" if stem.startswith(("mob", "group")) else "core"


def title_of(text, fallback):
    m = re.search(r"^#{1,2}\s+(.+?)\s*#*\s*$", text, re.M)
    t = m.group(1) if m else fallback
    t = re.sub(r"^(lab|optional|mob)\s*\d*\s*[:.-]\s*", "", t, flags=re.I)
    return re.sub(r"[*_`]", "", t).strip()


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def collect(repos):
    """Return docs[(unit,key)] and labs[(unit,key)] -> list of versions, oldest first."""
    docs, labs, solutions = {}, {}, {}
    for order, repo in enumerate(repos):
        for p, size in repo.files.items():
            parts = p.split("/")
            unit = unit_of(parts[0]) if len(parts) > 1 and not parts[0].lower().startswith("code") else None
            if not unit:
                continue
            sub = parts[1].lower() if len(parts) > 2 else ""
            ext = PurePosixPath(p).suffix.lower()
            v = {"repo": repo, "path": p, "order": order, "size": size}
            if ext == ".md" and (len(parts) == 2 or (sub == "docs" and len(parts) == 3)):
                docs.setdefault((unit, doc_key(p, unit)), []).append(v)
            elif ext == ".md" and sub == "labs" and len(parts) == 3:
                n = re.match(r"^(?:lab)?(\d+)", PurePosixPath(p).stem.lower())
                v |= {"flag": lab_flag(p), "num": int(n.group(1)) if n else None}
                labs.setdefault((unit, lab_key(p)), []).append(v)
            elif sub == "solutions" and len(parts) >= 3:
                solutions.setdefault(repo.name, []).append(v | {"unit": unit, "rel": "/".join(parts[2:])})
    return docs, labs, solutions


def is_recent(versions):
    return versions[-1]["order"] >= len(COHORTS) - RECENT


def similarity(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio() if a and b else None


def copy_images(text, version, dest_dir, problems):
    repo, src_dir = version["repo"], PurePosixPath(version["path"]).parent

    def fix(m):
        url = m.group(1) or m.group(2)
        if re.match(r"^(https?:|data:|#|mailto:)", url):
            return m.group(0)
        src = str(PurePosixPath(*[x for x in (src_dir / url.split("#")[0]).parts]))
        # normalize ../
        parts = []
        for part in src.split("/"):
            if part == "..":
                parts and parts.pop()
            elif part not in (".", ""):
                parts.append(part)
        src = "/".join(parts).replace("%20", " ")
        if src not in repo.files:
            problems.append(f"missing image {url} in {repo.name}:{version['path']}")
            return m.group(0)
        name = PurePosixPath(src).name
        (dest_dir / "images").mkdir(parents=True, exist_ok=True)
        (dest_dir / "images" / name).write_bytes(repo.read(src))
        return m.group(0).replace(url, f"images/{name.replace(' ', '%20')}")

    return IMG_RE.sub(fix, text)


def names_in(path, people):
    """Unambiguous roster names appearing as words in a path (student copies in solutions/)."""
    words = set(re.findall(r"[a-z]+", re.sub(r"([a-z])([A-Z])", r" ", path).lower()))
    return {w for w in words if w in people and w not in COMMON_WORDS}


MD_LINK = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+?\.md)(#[^)\s]*)?\)", re.I)


def rewrite_links(written, index):
    """Point relative .md links (which use the source cohort's filenames) at the merged files.

    The target is resolved against the source file's location, then matched by normalized
    doc/lab key, preferring the unit the target lived in. Unresolvable links become plain text.
    """
    unresolved = []
    for dest, unit, version in written:
        src_dir = PurePosixPath(version["path"]).parent

        def fix(m):
            bang, label, target, anchor = m.group(1), m.group(2), m.group(3), m.group(4) or ""
            if bang or re.match(r"^[a-z]+:", target):
                return m.group(0)
            parts = []
            for part in (src_dir / target.replace("%20", " ")).parts:
                if part == "..":
                    parts and parts.pop()
                elif part != ".":
                    parts.append(part)
            target_unit = unit_of(parts[0]) if len(parts) > 1 else None
            name = parts[-1] if parts else target
            units = [u for u in [target_unit or unit] + UNIT_KEYS if u]
            for u in units:
                for kind, key in (("doc", doc_key(name, u)), ("lab", lab_key(name))):
                    hit = index.get((kind, u, key))
                    if hit:
                        rel = Path(os.path.relpath(hit, dest.parent)).as_posix()
                        return f"[{label}]({rel}{anchor})"
            unresolved.append((dest, target))
            return label

        text = dest.read_text(encoding="utf-8")
        new = MD_LINK.sub(fix, text)
        if new != text:
            dest.write_text(new, encoding="utf-8")
    return unresolved


def pick_solution(key, unit, solutions, cohort_order, people):
    """Newest cohort whose solutions/ has a file or top folder for the lab.

    Exact key matches beat substring matches (which catch variants like 'lab02-blog-flex');
    within a tier the shortest name wins.
    """
    for cohort in reversed(cohort_order):
        tops = {}
        for s in solutions.get(cohort, []):
            if s["unit"] != unit or names_in(s["rel"], people):
                continue
            first = s["rel"].split("/")[0]
            sks = solution_keys(first)
            rank = 0 if key in sks else 1 if len(key) > 4 and any(key in sk for sk in sks) else None
            if rank is not None:
                tops.setdefault(first, [rank, []])[1].append(s)
        for name, (rank, group) in sorted(tops.items(), key=lambda kv: (kv[1][0], len(kv[0]))):
            files = [s for s in group if not (set(s["rel"].split("/")) & SKIP_PARTS)
                     and not SKIP_NAMES.search(s["rel"]) and PurePosixPath(s["rel"]).suffix.lower() in CODE_EXTS
                     and s["size"] <= MAX_SOLUTION_BYTES]
            if files:
                return cohort, name, files
    return None, None, []


def main():
    people = load_roster()
    repos = [Repo(c) for c in COHORTS]
    refs = [Repo(r) for r in REFERENCES]
    docs, labs, solutions = collect(repos)
    ref_docs, ref_labs, _ = collect(refs)
    unit_size = {}  # (cohort, unit) -> highest lab number
    for (u, _), vs in labs.items():
        vs.sort(key=lambda v: v["order"])
        for v in vs:
            k = (v["repo"].name, u)
            unit_size[k] = max(unit_size.get(k, 1), v["num"] or 1)
    ref_labs_by_key = {k[1]: v for k, v in ref_labs.items()}

    if OUT.exists():
        shutil.rmtree(OUT)
    problems, prov = [], []
    written, index = [], {}  # md files written (for link rewriting) and (kind, unit, key) -> path
    manifest = {"source": "PDX Code Guild Python Full Stack, 13 cohorts 2017-2021",
                "cohorts": COHORTS, "units": []}

    for ukey, folder, utitle, _ in UNITS:
        unit = {"key": ukey, "slug": folder, "title": utitle, "docs": [], "labs": []}
        udir = OUT / folder

        # ---- docs: current (used recently) first, ordered by the newest version's numeric prefix
        unit_docs = [(k, vs) for (u, k), vs in docs.items() if u == ukey]
        def doc_sort(item):
            p = PurePosixPath(item[1][-1]["path"]).stem
            n = re.match(r"^(\d+)", p)
            return (not is_recent(item[1]), 0 if n else 1, int(n.group(1)) if n else 0, p.lower())
        doc_counters = {}
        for key, vs in sorted(unit_docs, key=doc_sort):
            newest = vs[-1]
            tier = "current" if is_recent(vs) else "archived"
            doc_counters[tier] = doc_counters.get(tier, 0) + 1
            i = doc_counters[tier]
            text = newest["repo"].read(newest["path"]).decode("utf-8", "replace")
            title = title_of(text, PurePosixPath(newest["path"]).stem)
            slug = f"{'arc-' if tier == 'archived' else ''}{i:02d}-{slugify(key) or 'doc'}"
            dest = udir / "docs"
            dest.mkdir(parents=True, exist_ok=True)
            text = copy_images(text, newest, dest, problems)
            (dest / f"{slug}.md").write_text(text, encoding="utf-8")
            written.append((dest / f"{slug}.md", ukey, newest))
            index[("doc", ukey, key)] = dest / f"{slug}.md"
            oldest = vs[0]["repo"].read(vs[0]["path"]).decode("utf-8", "replace")
            drift = similarity(oldest, text)
            cohorts = sorted({v["repo"].name for v in vs}, key=COHORTS.index)
            unit["docs"].append({"slug": slug, "title": title, "tier": tier, "path": f"{folder}/docs/{slug}.md",
                                 "cohorts": cohorts, "source": newest["repo"].name,
                                 "drift": round(drift, 2) if drift is not None else None})
            prov.append(["doc", ukey, key, slug, len(cohorts), newest["repo"].name, newest["path"],
                         f"{drift:.2f}" if drift is not None else "", "", ""])

        # ---- labs: tier from the newest version; within a tier, order by median relative
        # position (lab number / labs in that cohort's unit) over the five most recent cohorts.
        unit_labs = [(k, vs) for (u, k), vs in labs.items() if u == ukey]
        def lab_tier(vs):
            return "archived" if not is_recent(vs) else vs[-1]["flag"]
        def lab_sort(item):
            key, vs = item
            rel = [v["num"] / unit_size[(v["repo"].name, ukey)] for v in vs if v["num"]][-5:]
            return (TIERS.index(lab_tier(vs)), statistics.median(rel) if rel else 2, key)
        counters = {}
        for key, vs in sorted(unit_labs, key=lab_sort):
            newest = vs[-1]
            tier = lab_tier(vs)
            counters[tier] = counters.get(tier, 0) + 1
            prefix = {"core": "", "mob": "mob-", "optional": "opt-", "archived": "arc-"}[tier]
            slug = f"{prefix}{counters[tier]:02d}-{slugify(key)}"
            ldir = udir / "labs" / slug
            ldir.mkdir(parents=True, exist_ok=True)
            text = newest["repo"].read(newest["path"]).decode("utf-8", "replace")
            title = title_of(text, key.replace("_", " ").title())
            text = copy_images(text, newest, ldir, problems)
            (ldir / "README.md").write_text(text, encoding="utf-8")
            written.append((ldir / "README.md", ukey, newest))
            index[("lab", ukey, key)] = ldir / "README.md"

            oldest = vs[0]["repo"].read(vs[0]["path"]).decode("utf-8", "replace")
            drift = similarity(oldest, text)
            ref = ref_labs_by_key.get(key)
            ref_sim = similarity(ref[-1]["repo"].read(ref[-1]["path"]).decode("utf-8", "replace"), text) if ref else None

            sol_cohort, sol_name, sol_files = pick_solution(key, ukey, solutions, COHORTS, people)
            sol_paths = []
            if sol_files:
                for s in sol_files:
                    rel = s["rel"].split("/", 1)[1] if "/" in s["rel"] and s["rel"].split("/")[0] == sol_name else PurePosixPath(s["rel"]).name
                    target = ldir / "solution" / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(s["repo"].read(s["path"]))
                    sol_paths.append(f"solution/{rel}")

            cohorts = sorted({v["repo"].name for v in vs}, key=COHORTS.index)
            unit["labs"].append({"slug": slug, "key": key, "title": title, "tier": tier,
                                 "path": f"{folder}/labs/{slug}/README.md", "cohorts": cohorts,
                                 "source": newest["repo"].name,
                                 "drift": round(drift, 2) if drift is not None else None,
                                 "reference_similarity": round(ref_sim, 2) if ref_sim is not None else None,
                                 "solution": {"source": sol_cohort, "files": sol_paths} if sol_paths else None})
            prov.append(["lab", ukey, key, slug, len(cohorts), newest["repo"].name, newest["path"],
                         f"{drift:.2f}" if drift is not None else "",
                         f"{ref_sim:.2f}" if ref_sim is not None else "", sol_cohort or ""])

        # ---- unit index
        lines = [f"# {utitle}", ""]
        for tier, label in [("current", "Docs"), ("archived", "Archived Docs")]:
            ds = [d for d in unit["docs"] if d["tier"] == tier]
            if ds:
                lines += [f"## {label}", ""] + [f"- [{d['title']}](docs/{d['slug']}.md)" for d in ds] + [""]
        for tier, label in [("core", "Labs"), ("mob", "Mob Labs"), ("optional", "Optional Labs"), ("archived", "Archived Labs")]:
            ls = [l for l in unit["labs"] if l["tier"] == tier]
            if ls:
                lines += [f"## {label}", ""] + [f"- [{l['title']}](labs/{l['slug']}/README.md)" for l in ls] + [""]
        udir.mkdir(parents=True, exist_ok=True)
        (udir / "README.md").write_text("\n".join(lines), encoding="utf-8")
        manifest["units"].append(unit)

    unresolved = rewrite_links(written, index)
    problems += [f"unresolved link {t} in {p.relative_to(OUT).as_posix()}" for p, t in unresolved]
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    top = ["# Python Full Stack Curriculum", "",
           "Merged from 13 PDX Code Guild cohorts (2017–2021). See the repository README for provenance and license.", ""]
    top += [f"- [{u['title']}]({u['slug']}/README.md) — {len(u['docs'])} docs, {len(u['labs'])} labs" for u in manifest["units"]]
    (OUT / "README.md").write_text("\n".join(top) + "\n", encoding="utf-8")

    with open(ROOT / "inventory" / "provenance.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["type", "unit", "key", "slug", "n_cohorts", "source_cohort", "source_path",
                    "drift_vs_oldest", "similarity_to_reference", "solution_cohort"])
        w.writerows(prov)
    (ROOT / "inventory" / "build_problems.txt").write_text("\n".join(problems) + "\n", encoding="utf-8")

    for u in manifest["units"]:
        tiers = {t: sum(l["tier"] == t for l in u["labs"]) for t in ("core", "mob", "optional", "archived")}
        sols = sum(bool(l["solution"]) for l in u["labs"])
        cur = sum(d["tier"] == "current" for d in u["docs"])
        print(f"{u['title']:<20} docs={cur}+{len(u['docs']) - cur}arc labs={tiers} with_solution={sols}")
    print(f"problems: {len(problems)}")


if __name__ == "__main__":
    main()
