# Python Full Stack

A single, merged version of the PDX Code Guild **Python Full Stack** bootcamp curriculum,
assembled from the 13 cohorts I taught or assisted with between 2017 and 2021.

Browse it in [`curriculum/`](curriculum/README.md):

| Unit | What's in it |
|---|---|
| [General](curriculum/00-general/README.md) | Setup, Git, Markdown, regex, the internet, professional practice |
| [Python](curriculum/01-python/README.md) | 23 docs and 26 core labs, from Turtle to a text adventure, plus mob and optional labs |
| [Flask + HTML + CSS](curriculum/02-flask-html-css/README.md) | HTML, CSS, layout, forms, Flask |
| [Django](curriculum/03-django/README.md) | Routes, views, templates, models, auth, deployment |
| [JavaScript](curriculum/04-javascript/README.md) | Language basics, DOM, events, AJAX, Vue |
| [Capstone](curriculum/05-capstone/README.md) | Proposals, ideas, APIs |
| [Post-Course](curriculum/06-post-course/README.md) | Resume, LinkedIn, interviewing, job search |

`curriculum/manifest.json` describes every unit, doc and lab (title, tier, which cohorts used it,
source, reference solution) for programmatic use, e.g. by [mcdev](https://github.com/spectralradiance/mcdev).

## How it was merged

Source cohorts, oldest to newest: `20171003-FullStack-Day`, `20180116-FullStack-Day`, `class_ocelot`,
`class_platypus`, `class_iguana`, `class_sheep`, `class_emu`, `class_honeybadger`, `class_raccoon`,
`class_mountain_goat`, `class_armadillo`, `class_bumble_bee`, `class_eagle`. The curriculum
template repos `PythonFullStack` and `PythonFullStack2` were used as references only.

- **One version per item.** Docs and labs are matched across cohorts by normalized name
  (`lab12-rot13.md`, `11 Rot Cipher.md` → `rot13`), and the newest cohort's text is used.
- **Tiers.** Labs keep the newest cohort's designation (core / mob / optional). Anything not
  taught in the last four cohorts is listed as *archived* rather than dropped.
- **Order.** Labs are ordered by their median relative position in the five most recent cohorts
  that taught them.
- **Reference solutions** come from the newest cohort's `solutions/` folder that has a matching
  file or project. Paths that belong to individual students are skipped.
- `inventory/provenance.csv` records, for every item, how many cohorts used it, where the
  canonical text came from, and how much it changed (`drift_vs_oldest`, 1.0 = unchanged).

## Privacy

This repository contains **no student work and no student names** at this stage. Every build runs
`scripts/sanitize.py` (removes secrets/API keys, Django `SECRET_KEY`s, personal emails and phone
numbers, classmates' GitHub links, OS user paths, and name credits on past capstones) followed by
`scripts/pii_scan.py`, which checks every file against a roster of everyone who ever committed to
the source repos and blocks the build on any unreviewed match. The roster and raw clones live in
`raw/`, which is git-ignored and never published.

Anonymized, curated student submissions will be added in `submissions/` under the same gate.

## Rebuilding

```bash
bash scripts/build.sh
```

Requires git and Python 3.10+. No third-party packages.

## License and attribution

Curriculum content © PDX Code Guild and its instructors, released under the
[GNU GPL v3](LICENSE), the license of the original repositories. This repository is a derivative
work under the same license. PDX Code Guild did not produce or endorse this compilation.
