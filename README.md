# 3 Ideas From Me

Every **"3 Ideas From Me"** section from every issue of the [James Clear 3-2-1
newsletter](https://jamesclear.com/3-2-1), extracted into a searchable local
archive.

**380 issues · 1,140 ideas · Aug 2019 → Nov 2026 · ~48,000 words**

---

## Quick start

```bash
./fetch.sh          # download all 384 archive entries -> raw/
python3 extract.py  # parse "3 Ideas From Me" -> ideas.{json,md,csv}
python3 build_ui.py # bundle ideas.json -> index.html
open index.html
```

Re-run steps 2 and 3 any time; step 1 only needs re-running when new issues are
published. All three scripts resolve paths relative to themselves, so they work
from any directory.

**No dependencies.** The pipeline is pure Python 3 standard library plus `curl`.
There is no `pip install`, no virtualenv, no build step, and nothing to install
for the output to work.

---

## How it works

### 1. `fetch.sh` — getting the archive

`jamesclear.com` is a WordPress site, and 3-2-1 is a **custom post type**
(`3-2-1`), not a paginated blog list. The archive page's "load more" button is
irrelevant — the entire corpus is exposed through the REST API:

```
GET https://jamesclear.com/wp-json/wp/v2/3-2-1?per_page=100&page=N
→ X-WP-Total: 384
```

Four requests return every issue as JSON with rendered HTML, publication date,
and canonical URL. The raw responses are cached in `raw/` (~5.5 MB) so the
parser can be re-run without hitting the network.

### 2. `extract.py` — parsing

For each issue: find the `<h2>` whose text is "3 IDEAS FROM ME", take everything
up to the next `<h2>`, then split that section into three ideas on the
roman-numeral markers (`<p>I.</p>` … `<p>III.</p>`).

The markup is *almost* consistent, and "almost" is where all the work went. See
[Parser edge cases](#parser-edge-cases) below — **read that before changing the
parser.**

### 3. `build_ui.py` — the reader

Inlines `ideas.json` into a single self-contained `index.html` (~381 KB). No
server, no CDN, no network calls. It works from `file://`, survives being
emailed, and will still open in ten years.

---

## Output formats

| File | Purpose |
|---|---|
| `ideas.json` | Source of truth. One object per issue: `{date, url, intro, ideas[]}` |
| `ideas.md` | Readable, one issue per `##` heading, with a source link |
| `ideas.csv` | One row per idea: `date, issue_number, url, idea` |
| `index.html` | The searchable reader (**generated — do not hand-edit**) |
| `raw/page*.json` | Cached API responses |

---

## The reader

Press <kbd>/</kbd> to search — with 1,122 items, search *is* the interface.

| Key | Action |
|---|---|
| <kbd>/</kbd> | Focus search |
| <kbd>j</kbd> <kbd>k</kbd> | Move between ideas |
| <kbd>y</kbd> | Copy idea **with its date and source link** |
| <kbd>o</kbd> | Open the original newsletter |
| <kbd>r</kbd> | Random idea |
| <kbd>Esc</kbd> | Clear search |

- **Multi-word search is AND** — `"compound interest"` returns only ideas
  containing both, ranked by earliest match so the tightest phrasing ranks first.
- Matches are highlighted; light and dark themes follow the OS setting.
- Keyboard hints are hidden below 620px, where they are meaningless on touch.

---

## Parser edge cases

The archive is *nearly* uniform. Each of these is a real defect that was
observed in the data and is handled explicitly. **All of them are guarded by
tests in the validation section below — if you "simplify" one away, the
invariant breaks.**

| # | Defect in the source | Handling |
|---|---|---|
| 1 | Heading varies: `3 IDEAS FROM ME`, `3 Ideas From Me`, a zero-width-space prefix, and one issue with a `1 IDEAS FROM ME` typo | Match on heading *text* with a loose regex, never on the `id` attribute |
| 2 | Marker written as `<p><br>II.</p>` — a stray `<br>` inside the paragraph | Allow filler markup inside the marker paragraph |
| 3 | One issue omits the period: `<p>II</p>` (2026-04-16) | Make the period optional |
| 4 | Two share-embed variants: a `<div class="twitter-share">` block, *and* a bare `ctt.ac` "Share this on Twitter" anchor inside a `<p>` | Strip both; they otherwise leak into the idea text |
| 5 | Some ideas contain `<ul>` lists (e.g. 2021-01-14) | Render list items as `- …` instead of dropping them |
| 6 | Two issues have **no `I.` marker at all** (2020-07-16, 2022-12-15) | Treat leading text as an idea — *but only if* fewer than 3 markers were found |
| 7 | Four issues have all 3 markers *plus* a genuine intro sentence (2023-06-15, 2025-01-23, 2026-01-01, 2026-05-28) | Same leading-text detection, but store it as `intro` rather than an idea |

Rules 6 and 7 are the subtle pair: leading text before the first marker means a
**missing marker** when markers < 3, and an **intro sentence** when all 3 are
present. Conflating them produces 4 issues with four "ideas" or 2 issues with
two.

> **A trap worth naming.** The marker regex must be anchored on *both* sides of
> the roman numeral. An unanchored version also matches any paragraph merely
> *containing* the letter I — so `<p>In the long run…</p>` becomes an idea
> boundary. When the corpus was 374 issues this produced 1,120 garbled ideas
> instead of 1,122 and looked superficially plausible. Anchor with the `_FILLER`
> character class, and always confirm the count is exactly 380 × 3.

---

## Validation

`extract.py` prints a report; these numbers are the **regression invariant**:

```
issues parsed : 380 / 384 entries
ideas         : 1140
no section    : 4
not exactly 3 : 0
```

If `not exactly 3` is anything other than `0`, or `ideas` is not `1140`, the
parser has regressed. Check the table above before changing anything.

Additional checks that were run when this pipeline was built:

- Zero artifacts in output: no `ctt.ac`, no `Share this on Twitter`, no stray
  HTML or HTML entities, no leakage from the adjacent "1 QUESTION FOR YOU" /
  "2 QUOTES FROM OTHERS" sections.
- The 4 entries without a section are **expected** — they are not newsletters
  (`/refer`, `/refer-thanks`, `/sign-up-for-…`, `/confirmed`).
- Four random issues were re-fetched from the **live web pages** and their ideas
  matched the parsed output exactly.

> There is **no automated test suite in this repo.** Verification was done
> ad-hoc (Node + Playwright for the UI, direct assertions against the data). The
> invariant above is currently the regression check. If you add real tests, the
> highest-value ones are: assert 1140 ideas, assert every issue has exactly 3,
> and assert no issue text contains `ctt.ac` or `Share this on Twitter`.

---

## Data notes

- **36 ideas appear more than once.** These are genuine repeats — James Clear
  re-runs older material (e.g. the 2020 "learn by teaching" idea returns in
  2025-05-08 and 2025-08-21). 1,140 total, 1,104 unique. Dedupe if you prefer.
- **Ideas are verbatim**, including original paragraph breaks and curly quotes.
  Text is not paraphrased, re-ordered, or truncated.
- The 4 issues with an `intro` keep that sentence in `ideas.json` as `intro`, so
  it is never mistaken for an idea.

## Use of the source

Content is copyrighted by James Clear. This is a personal reading archive:
extracted for private study and reference, with a link back to the original
issue on every single idea. The reader deliberately makes attribution and
provenance a one-keystroke action (`y` to copy, `o` to open the source).