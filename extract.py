#!/usr/bin/env python3
"""Extract the '3 Ideas From Me' section from every James Clear 3-2-1 newsletter.

Source: WordPress REST API, custom post type `3-2-1` (378 entries).
Output: ideas.json, ideas.md, ideas.csv

Parsing notes (each observed in the real archive):
  * Section heading is an <h2>: "3 IDEAS FROM ME" (title-case and a zero-width
    space variant exist; one issue has a "1 IDEAS" typo).
  * Ideas are delimited by roman-numeral markers: <p>I.</p>, <p><br>II.</p>
    (a stray <br>), and one issue omits the period on "II".
  * Between the idea text and the next marker there is a <div class="twitter-share">
    embed plus an <hr>. The embed must be removed, not flattened to text.
  * Idea bodies use <p>, <ul>/<ol> (e.g. the "guide to leadership" list), <br>.
"""
import json, glob, re, csv, html, sys, os

RAW_DIR = "raw"
HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- utilities
H2 = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.S | re.I)
SECTION = re.compile(r"^\W*\d?\s*ideas?\s+from\s+me\b", re.I)
# A marker paragraph contains NOTHING but the roman numeral (plus optional
# whitespace / <br> / &nbsp; / zero-width chars). It must be anchored on both
# sides or it also matches body paragraphs like "<p>In the long run...</p>".
_FILLER = r"(?:<br\s*/?>|&nbsp;|&#160;|[\s\u200b\u2060])*"
MARKER = re.compile(
    r"<p\b[^>]*>" + _FILLER + r"(I{1,3}|IV)\s*\.?" + _FILLER + r"</p>",
    re.S | re.I,
)
# Remove share/embed widgets (twitter-share etc.) up to the next real block.
EMBED = re.compile(
    r"<div\b[^>]*class=[\"'][^\"']*\b(?:twitter-share|jp-relatedposts|easy-share)\b[^\"']*[\"'][^>]*>.*?"
    r"(?=<hr\b|<p\b|<h[1-6]\b|</section|$)",
    re.S | re.I,
)
# Second embed variant: a bare "Share this on Twitter" link to ctt.ac, which
# sometimes sits inside its own <p> rather than in a twitter-share div.
TWEET_LINK = re.compile(r"<a\b[^>]*href=[\"'][^\"']*ctt\.ac[^\"']*[\"'][^>]*>.*?</a>", re.S | re.I)
BLOCK = re.compile(r"<p\b[^>]*>.*?</p>|<ul\b[^>]*>.*?</ul>|<ol\b[^>]*>.*?</ol>|<blockquote\b[^>]*>.*?</blockquote>", re.S | re.I)
BLOCK_OR_HR = re.compile(r"<hr\b[^>]*>|" + BLOCK.pattern, re.S | re.I)
HR = re.compile(r"<hr\b[^>]*>", re.I)
LI_OPEN = re.compile(r"<li\b[^>]*>", re.I)
LI_CLOSE = re.compile(r"</li\s*>", re.I)

def plain(s):
    """Strip tags, unescape entities, drop zero-width junk."""
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    for ch in ("\u200b", "\u2060", "\ufeff", "\u00ad"):
        s = s.replace(ch, "")
    return re.sub(r"[ \t]+", " ", s).strip()

def meaningful(t):
    """True if a rendered block still contains actual words (drops "(", "")."""
    return bool(re.search(r"[A-Za-z0-9]", t)) and bool(t.strip())

def block_to_text(block):
    """Render one content block (p / ul / ol / blockquote) to clean text."""
    if re.match(r"<ul\b|<ol\b", block, re.I):
        items = re.split(r"<li\b[^>]*>", block, flags=re.I)[1:]
        lines = []
        for it in items:
            it = LI_CLOSE.split(it, 1)[0]
            t = plain(it)
            if t:
                lines.append("- " + t)
        return "\n".join(lines)
    # paragraph or blockquote
    t = re.sub(r"<br\s*/?>", "\n", block, flags=re.I)
    t = plain(t)
    return t

def section_html(content):
    heads = list(H2.finditer(content))
    for i, h in enumerate(heads):
        if SECTION.match(plain(h.group(1))):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(content)
            return content[h.end():end]
    return None

def split_ideas(section):
    section = EMBED.sub("", section)
    section = TWEET_LINK.sub("", section)
    section = re.sub(r"Share this on Twitter", "", section, flags=re.I)
    markers = list(MARKER.finditer(section))
    if not markers:
        # Fallback: some issues have no visible numerals, so split on the <hr>
        # rules that separate the ideas.
        chunks, buf = [], []
        for b in BLOCK_OR_HR.findall(section):
            if b.lstrip().lower().startswith("<hr"):
                if buf:
                    chunks.append("\n\n".join(x for x in buf if meaningful(x)))
                    buf = []
            else:
                buf.append(block_to_text(b))
        if buf:
            chunks.append("\n\n".join(x for x in buf if meaningful(x)))
        return [c.strip() for c in chunks if c.strip()], ""
    ideas, intro = [], ""
    lead = HR.sub("", section[: markers[0].start()]) if markers else section
    lead_text = "\n\n".join(x for x in (block_to_text(b) for b in BLOCK.findall(lead)) if meaningful(x))
    lead_text = lead_text.strip()
    if len(markers) < 3 and lead_text:
        # A marker is genuinely missing (e.g. 2020-07-16, 2022-12-15).
        ideas.append(lead_text)
    elif lead_text:
        # All 3 markers are present, so the lead is just an intro sentence.
        intro = lead_text
    for i, m in enumerate(markers):
        end = markers[i + 1].start() if i + 1 < len(markers) else len(section)
        body = HR.sub("", section[m.end():end])
        chunks = [block_to_text(b) for b in BLOCK.findall(body)]
        text = "\n\n".join(c for c in chunks if meaningful(c))
        if meaningful(text):
            ideas.append(text.strip())
    return ideas, intro

# ---------------------------------------------------------------- main
def load():
    files = sorted(glob.glob(os.path.join(HERE, RAW_DIR, "page*.json")))
    if not files:
        sys.exit(f"No {RAW_DIR}/page*.json found. Run ./fetch.sh first.")
    posts = []
    for f in files:
        data = json.load(open(f))
        posts += data if isinstance(data, list) else [data]
    return posts

def main():
    posts = load()
    results, missing = [], []
    for p in posts:
        sec = section_html(p["content"]["rendered"])
        if sec is None:
            missing.append((p["date"][:10], p["link"]))
            continue
        ideas, intro = split_ideas(sec)
        results.append({
            "date": p["date"][:10],
            "url": p["link"],
            "intro": intro,
            "ideas": ideas,
        })
    results.sort(key=lambda r: r["date"])

    with open(os.path.join(HERE, "ideas.json"), "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    with open(os.path.join(HERE, "ideas.md"), "w") as f:
        total = sum(len(r["ideas"]) for r in results)
        f.write("# 3 Ideas From Me\n\n")
        f.write(f"Extracted from the James Clear 3-2-1 newsletter archive: "
                f"{len(results)} issues, {total} ideas.\n\n---\n\n")
        for r in results:
            f.write(f"## {r['date']}\n\n")
            if r.get("intro"):
                f.write(f"*{r['intro']}*\n\n")
            for i, idea in enumerate(r["ideas"], 1):
                f.write(f"{idea}\n\n")
            f.write(f"[source]({r['url']})\n\n---\n\n")

    with open(os.path.join(HERE, "ideas.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "issue", "url", "idea"])
        for r in results:
            for n, idea in enumerate(r["ideas"], 1):
                w.writerow([r["date"], n, r["url"], idea])

    total = sum(len(r["ideas"]) for r in results)
    print(f"issues parsed : {len(results)} / {len(posts)} entries")
    print(f"ideas         : {total}")
    print(f"no section    : {len(missing)}")
    for d, u in missing:
        print(f"    {d}  {u}")
    odd = [r for r in results if len(r["ideas"]) != 3]
    print(f"not exactly 3 : {len(odd)}")
    for r in odd:
        print(f"    {r['date']} -> {len(r['ideas'])}  {r['url']}")

if __name__ == "__main__":
    main()