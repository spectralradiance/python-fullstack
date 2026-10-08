"""Rewrite secrets and personal details in a built folder, in place.

Usage: python -I scripts/sanitize.py curriculum [submissions ...]
Run after build_curriculum.py and before pii_scan.py.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pii_scan import ALLOWED_EMAIL, NOISE, ROOT, SELF, TEXT_EXTS, load_roster

API_PLACEHOLDER = "YOUR_API_KEY"
RULES = [
    # Django secret keys -> read from the environment
    (re.compile(r"""SECRET_KEY\s*=\s*(['"]).*?\1"""),
     "SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-REPLACE-ME')"),
    # FavQs-style token headers and generic assigned keys
    (re.compile(r"""(Token token=\\?["'])[0-9a-f]{16,}(\\?["'])"""), rf"\g<1>{API_PLACEHOLDER}\g<2>"),
    (re.compile(r"""(?i)(\b(?:api[_-]?key|apikey|token|secret|app[_-]?id)\b["']?\s*[:=]\s*["'])[^"'\s]{12,}(["'])"""),
     rf"\g<1>{API_PLACEHOLDER}\g<2>"),
    (re.compile(r"(?i)([?&](?:api[_-]?key|apikey|appid|key|token|access_token)=)[0-9A-Za-z_\-]{16,}"),
     rf"\g<1>{API_PLACEHOLDER}"),
    # Real-looking phone numbers (keep 555 numbers and obvious fakes like 123-456-7890)
    (re.compile(r"(?<![\d.])(\(?\d{3}\)?[-.\s])(?!555)(?!456)\d{3}([-.\s])\d{4}(?!\d)"), r"\g<1>555\g<2>0100"),
    # Thank-you notes to classmates in comments: <!-- thank you Kat -->, # thanks Sam!
    (re.compile(r"(?i)<!--\s*thanks?(?: you)?,? [A-Z][a-z]+[!.]?\s*-->\n?|(#|//)\s*thanks?(?: you)?,? [A-Z][a-z]+[!.]?\s*$", re.M), ""),
    # OS user folders: C:\Users\someone\ , /Users/someone/ , /home/someone/
    (re.compile(r"(?i)(C:\\\\?Users\\\\?)(?!student\b)[^\\/'\"\s]+"), r"\g<1>student"),
    (re.compile(r"(/(?:Users|home)/)(?!student\b)[A-Za-z0-9._-]+"), r"\g<1>student"),
]
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
GITHUB = re.compile(r"(https?://)?github\.com/([A-Za-z0-9-]+)(/[^\s)\]\"']*)?", re.I)
# "By Firstname Lastname." credits and their repo links in the past-capstones doc.
CAPSTONE_CREDIT = re.compile(r"\s*\bBy [A-Z][\w'-]+(?: [A-Z][\w'-]+){0,2}\.?(?=\s|$)")
GIT_AUTHOR = re.compile(r"(Author:\s+)[^<\n]+<[^>\n]*>")
CAPSTONE_REPO =re.compile(r"\s*\[(?:repo|github|code|site)\]\([^)]*\)", re.I)


def sanitize_text(text, rel, handles):
    for rx, repl in RULES:
        text = rx.sub(repl, text)
    text = EMAIL.sub(lambda m: m.group(0) if ALLOWED_EMAIL.search(m.group(0)) else "student@example.com", text)

    def gh(m):
        user = m.group(2).lower()
        return "https://github.com/example-student" + (m.group(3) or "") if user in handles else m.group(0)
    text = GITHUB.sub(gh, text)
    text = GIT_AUTHOR.sub(r"\g<1>Jane Developer <jane@example.com>", text)
    if "capstone" in rel:
        text = "\n".join(CAPSTONE_REPO.sub("", CAPSTONE_CREDIT.sub("", line)) for line in text.split("\n"))
    if rel.endswith(".py") and "os.environ.get('DJANGO_SECRET_KEY'" in text and not re.search(r"^import os\b", text, re.M):
        text = text.replace("SECRET_KEY = os.environ", "import os\nSECRET_KEY = os.environ", 1)
    return text


def roster_handles():
    """Lower-cased git handles of everyone in the roster (used for GitHub link scrubbing)."""
    handles = set()
    for line in (ROOT / "raw" / "_inventory" / "git_authors.txt").read_text(encoding="utf-8").splitlines():
        name, _, email = line.strip().split(" ", 1)[1].partition("|")
        for h in (name, email.split("@")[0]):
            h = h.lower().replace(" ", "")
            if h and h not in SELF | NOISE:
                handles.add(h)
    return handles | set(load_roster())


def main():
    handles = roster_handles()
    changed = 0
    for target in sys.argv[1:] or ["curriculum"]:
        for path in (ROOT / target).rglob("*"):
            if path.is_file() and path.suffix.lower() in TEXT_EXTS:
                text = path.read_text("utf-8", "replace")
                new = sanitize_text(text, path.relative_to(ROOT).as_posix(), handles)
                if new != text:
                    path.write_text(new, encoding="utf-8")
                    changed += 1
    print(f"sanitized {changed} files")


if __name__ == "__main__":
    main()
