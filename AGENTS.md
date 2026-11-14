# AGENTS.md

Operational notes for coding agents working in this repo.
Read `README.md` for the full design rationale and edge-case table.

## What this is

Scrapes the "3 Ideas From Me" section from all 380 issues of the James Clear
3-2-1 newsletter and bundles it into a single-file offline reader.

## Commands

```bash
./fetch.sh          # network: 384 API responses -> raw/   (~5.5 MB)
python3 extract.py  # raw/ -> ideas.{json,md,csv}          (offline)
python3 build_ui.py # ideas.json -> index.html             (offline)
open index.html
```

Only `fetch.sh` touches the network. `extract.py` and `build_ui.py` are pure
stdlib and fully offline. All three are cwd-independent (they resolve paths via
`__file__` / `BASH_SOURCE`).

## Stack

Python 3 standard library only (`json, glob, re, csv, html, sys, os`) + `curl`.
No pip packages, no venv, no Node, no framework, no build step.
Playwright was used once for manual UI verification and is **not** a project
dependency — do not add it.

## Hard invariant — check this after any parser change

```
issues parsed : 380 / 384 entries
ideas         : 1140
not exactly 3 : 0
```

380 issues × exactly 3 ideas = 1140. Any other number means a regression.
`extract.py` prints this report on every run; read it before committing.

These are *expected* results, not bugs:
- `no section : 4` — non-newsletter pages (`/refer`, `/refer-thanks`,
  `/sign-up-for-…`, `/confirmed`).
- 36 duplicate ideas across issues — the author re-runs older material.
- 4 issues carry a non-empty `intro` field.

## Generated files — never hand-edit

`index.html` is **built output**. All UI changes belong in the `HTML` template
string inside `build_ui.py`, then regenerate. Same for `ideas.{json,md,csv}`:
produced by `extract.py`, not editable by hand.

Hand-edits to `index.html` are silently destroyed by the next `build_ui.py` run.

## Parser warnings

The source markup is *nearly* uniform and the inconsistencies are load-bearing.
Before touching `MARKER` / `EMBED` / `split_ideas` in `extract.py`, read the
edge-case table in `README.md`. Two traps that have already been hit:

1. **The roman-numeral marker regex must be anchored on both sides.** An
   unanchored version matches any paragraph containing the letter I, so
   `<p>In the long run…</p>` becomes an idea boundary. Output still *looks*
   plausible but drops to 1,120 garbled ideas instead of 1,122 (when the
   corpus was 374 issues).

2. **Leading text before the first marker is ambiguous.** Fewer than 3 markers
   means a marker is missing (text is an idea); all 3 present means it is an
   intro sentence (`intro` field). Conflating them breaks 6 real issues.

Also: strip *both* share-embed variants (`<div class="twitter-share">` and bare
`ctt.ac` anchors), or `"Share this on Twitter"` leaks into idea text.

## UI gotchas

- **Do not add `autofocus` to the search input.** The keydown handler bails out
  when the input has focus (so typing `j` works). With `autofocus`, that guard
  fires on page load and *every* shortcut dies: `j`/`k` do nothing and `/`
  inserts a literal slash, turning a search into `"/habits"` → 0 results. This
  shipped once and was only caught by driving a real browser.
- The UI is intentionally dependency-free and offline. No CDN links, no fonts
  fetched at runtime, no analytics. Keep it that way — the file must work from
  `file://` forever.

## Verifying a change

There is no test suite. Minimum bar before calling parser work done:

```bash
python3 extract.py | head -3          # must show 380 / 1140 / 0
python3 -c "
import json; d=json.load(open('ideas.json'))
t=[i for r in d for i in r['ideas']]
assert len(d)==380 and len(t)==1140
assert all(len(r['ideas'])==3 for r in d)
bad=[x for x in t if 'ctt.ac' in x or 'Share this on Twitter' in x]
assert not bad, bad[:2]
print('ok')"
```

For UI changes, open `index.html` and check the console is clean and the
shortcuts work (`/`, `j`, `k`, `y`, `o`, `r`, `Esc`).

## Data provenance

Every idea retains its issue `date` and source `url` — do not drop them. Copy
(`y`) and open-source (`o`) both depend on them, and an idea without
attribution is not worth keeping.