import html
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BOXOFFICE_DIR = ROOT_DIR.parent / "PunFiction-BoxOffice"
SCRATCH_DIR = Path(r"C:\Users\iwand\.gemini\antigravity\brain\8e85f99a-5038-43de-bb77-d679c6cc96ca\scratch")

BANNED_AI_PHRASES = [
    "testament",
    "tapestry",
    "delve",
    "nestled",
    "beacon",
    "more than just",
    "whether you're",
    "in conclusion",
    "it's no secret",
    "marvel at",
    "breathtaking",
    "captivating",
    "bustling",
    "steeped in",
    "treasure trove",
    "symphony",
    "stands tall",
    "iconic",
    "rich history",
    "crown jewel",
    "feast for the eyes",
]


def slugify(text: str) -> str:
    s = text.lower().strip()
    s = (
        s.replace("í", "i")
        .replace("á", "a")
        .replace("é", "e")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ü", "u")
        .replace("ñ", "n")
    )
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def classify_region(lat: float, lng: float) -> str:
    if lng < -25:
        return "Americas"
    if lng <= 60 and lat >= 34:
        return "Europe"
    if lng <= 65 and lat < 34:
        return "Africa & Middle East"
    return "Asia & Oceania"


def format_coords(lat, lng) -> str:
    if lat is None or lng is None:
        return "Coordinates Verified"
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lng >= 0 else "W"
    return f"{abs(float(lat)):.4f}° {ns}, {abs(float(lng)):.4f}° {ew}"


def difficulty_label(tier: int) -> str:
    if tier == 1:
        return "Easy"
    if tier == 3:
        return "Hard"
    return "Medium"


def resolve_poster_rel_url(raw_url: str) -> str:
    if not raw_url:
        return ""
    clean = raw_url.strip()
    if clean.startswith("http://") or clean.startswith("https://"):
        return clean
    if clean.startswith("/travelreviews/"):
        return "../" + clean[len("/travelreviews/") :]
    if clean.startswith("travelreviews/"):
        return "../" + clean[len("travelreviews/") :]
    if clean.startswith("/"):
        return ".." + clean
    return "../" + clean


def load_and_merge_histories() -> dict:
    merged = {}
    for idx in range(1, 5):
        batch_path = SCRATCH_DIR / f"essays_batch_{idx}.json"
        if not batch_path.exists():
            raise FileNotFoundError(f"Missing batch file: {batch_path}")
        data = json.loads(batch_path.read_text(encoding="utf-8"))
        for k, v in data.items():
            pnum = str(k).zfill(3)
            merged[pnum] = v

    if len(merged) < 120:
        raise RuntimeError(f"Expected 120 essay entries, found {len(merged)}")

    # Validate word counts and anti-AI rules
    for pnum, item in sorted(merged.items()):
        full_text = f"{item.get('p1', '')} {item.get('p2', '')} {item.get('p3', '')}"
        words = full_text.split()
        if len(words) < 300:
            raise ValueError(f"Challenge #{pnum} essay has only {len(words)} words (< 300)")
        lower_all = f"{item.get('headline', '')} {full_text} {item.get('visitor_tip', '')}".lower()
        for phrase in BANNED_AI_PHRASES:
            if phrase in lower_all:
                raise ValueError(f"Challenge #{pnum} contains banned phrase '{phrase}'")

    out_path = ROOT_DIR / "backend" / "travelreviews_landmark_histories.json"
    out_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if (BOXOFFICE_DIR / "backend").exists():
        shutil.copy2(out_path, BOXOFFICE_DIR / "backend" / "travelreviews_landmark_histories.json")
    print(f"Saved and validated 120 landmark histories in {out_path}")
    return merged


SHARED_ARCHIVE_CSS = """
:root {
    --bg-color: #FAF8F5;
    --bg-gradient-end: #F0EDE6;
    --card-bg: #FFFFFF;
    --text-primary: #2D3436;
    --text-secondary: #57606F;
    --accent-main: #00AA6C;
    --accent-dark: #008755;
    --accent-amber: #F59E0B;
    --accent-coral: #FF4757;
    --border-color: #2D3436;
}
* {
    box-sizing: border-box;
}
body {
    margin: 0;
    padding: 0;
    font-family: 'Nunito', -apple-system, BlinkMacSystemFont, sans-serif;
    background: linear-gradient(180deg, var(--bg-color) 0%, var(--bg-gradient-end) 100%);
    color: var(--text-primary);
    line-height: 1.68;
    min-height: 100vh;
}
.site-header {
    max-width: 880px;
    margin: 0 auto;
    padding: 24px 20px 10px 20px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}
.brand-link {
    text-decoration: none;
    display: inline-flex;
    align-items: baseline;
    gap: 10px;
}
.brand-title {
    font-family: 'Bangers', cursive;
    font-size: 2.5rem;
    letter-spacing: 2px;
    color: var(--text-primary);
    text-shadow: 3px 3px 0px #FFD166;
    margin: 0;
}
.brand-title .accent {
    color: var(--accent-main);
}
.brand-sub {
    font-weight: 900;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--text-secondary);
}
.header-nav {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: center;
}
.nav-pill {
    text-decoration: none;
    font-weight: 800;
    font-size: 0.88rem;
    padding: 8px 14px;
    border-radius: 8px;
    border: 2px solid var(--border-color);
    background: var(--card-bg);
    color: var(--text-primary);
    box-shadow: 3px 3px 0px var(--border-color);
    transition: transform 0.1s ease, box-shadow 0.1s ease;
}
.nav-pill:hover {
    transform: translate(-1px, -1px);
    box-shadow: 4px 4px 0px var(--border-color);
}
.nav-pill.primary {
    background: var(--accent-main);
    color: #FFFFFF;
}
.breadcrumbs {
    max-width: 880px;
    margin: 0 auto;
    padding: 4px 20px 14px 20px;
    font-size: 0.85rem;
    font-weight: 700;
    color: var(--text-secondary);
}
.breadcrumbs a {
    color: var(--accent-dark);
    text-decoration: none;
}
.breadcrumbs a:hover {
    text-decoration: underline;
}
.container {
    max-width: 880px;
    margin: 0 auto;
    padding: 0 20px 48px 20px;
}
.neo-card {
    background: var(--card-bg);
    border: 3px solid var(--border-color);
    border-radius: 14px;
    box-shadow: 6px 6px 0px var(--border-color);
    padding: 28px;
    margin-bottom: 26px;
}
.meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    margin-bottom: 12px;
}
.badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.76rem;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: 1.5px solid var(--border-color);
}
.badge-challenge {
    background: #FFF3BF;
    color: var(--text-primary);
}
.badge-region {
    background: #E3FAFC;
    color: #0B7285;
}
.badge-easy {
    background: #D3F9D8;
    color: #2B8A3E;
}
.badge-medium {
    background: #FFF3BF;
    color: #B45309;
}
.badge-hard {
    background: #FFE3E3;
    color: #C92A2A;
}
h1.page-title {
    font-family: 'Bangers', cursive;
    font-size: 2.35rem;
    letter-spacing: 1.2px;
    line-height: 1.15;
    margin: 6px 0 10px 0;
    color: var(--text-primary);
}
.page-deck {
    font-size: 1.14rem;
    font-weight: 800;
    color: var(--text-secondary);
    margin: 0 0 16px 0;
    line-height: 1.45;
}
.facts-strip {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 10px;
    background: #F8F6FF;
    border: 2px solid var(--border-color);
    border-radius: 10px;
    padding: 12px 16px;
    margin-top: 14px;
    font-size: 0.88rem;
}
.fact-item strong {
    display: block;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
}
.section-heading {
    font-family: 'Bangers', cursive;
    font-size: 1.65rem;
    letter-spacing: 1px;
    margin: 0 0 14px 0;
    color: var(--text-primary);
    display: flex;
    align-items: center;
    gap: 8px;
}
.review-box {
    background: #FFFDF7;
    border: 2px solid var(--border-color);
    border-left: 6px solid var(--accent-coral);
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 14px;
}
.stars-row {
    color: #F59E0B;
    font-size: 1.1rem;
    letter-spacing: 2px;
    font-weight: 900;
    margin-bottom: 4px;
}
.review-headline {
    font-size: 1.18rem;
    font-weight: 900;
    margin: 0 0 6px 0;
    color: var(--text-primary);
}
.reviewer-byline {
    font-size: 0.82rem;
    font-weight: 800;
    color: var(--text-secondary);
    text-transform: uppercase;
    margin-bottom: 10px;
}
.review-quote {
    font-size: 1.04rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0;
}
.followup-clues {
    margin-top: 14px;
    padding-top: 12px;
    border-top: 2px dashed #CBD5E1;
}
.followup-clues h3 {
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--text-secondary);
    margin: 0 0 8px 0;
}
.followup-clues ul {
    margin: 0;
    padding-left: 20px;
}
.followup-clues li {
    font-size: 0.96rem;
    font-weight: 700;
    margin-bottom: 6px;
}
.essay-prose p {
    font-size: 1.06rem;
    line-height: 1.78;
    margin: 0 0 18px 0;
    color: #1E272E;
}
.visitor-tip-box {
    background: #E6FCF5;
    border: 2px solid var(--accent-main);
    border-radius: 10px;
    padding: 14px 18px;
    font-size: 0.96rem;
    font-weight: 700;
    color: #087F5B;
    margin-top: 10px;
}
.ext-links-row {
    margin-top: 16px;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    font-size: 0.9rem;
    font-weight: 800;
}
.ext-links-row a {
    color: var(--accent-dark);
    text-decoration: underline;
}
details.spoiler-details {
    background: #FFF9DB;
    border: 2px solid var(--border-color);
    border-radius: 10px;
    padding: 16px 20px;
}
details.spoiler-details summary {
    cursor: pointer;
    font-weight: 900;
    font-size: 1.02rem;
    color: var(--text-primary);
}
.spoiler-body {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 2px dashed var(--border-color);
}
.parody-answer-banner {
    font-family: 'Bangers', cursive;
    font-size: 1.85rem;
    letter-spacing: 1px;
    color: var(--accent-coral);
    margin: 0 0 12px 0;
}
.postcard-img {
    max-width: 360px;
    width: 100%;
    height: auto;
    border: 3px solid var(--border-color);
    border-radius: 10px;
    box-shadow: 4px 4px 0px var(--border-color);
    display: block;
    margin: 0 0 14px 0;
}
.owner-reply-box {
    background: #FFFFFF;
    border: 2px solid var(--border-color);
    border-radius: 8px;
    padding: 14px 16px;
    font-size: 0.98rem;
    font-weight: 700;
}
.cta-banner {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    background: #E6FCF5;
    border: 2px solid var(--border-color);
    border-radius: 10px;
    padding: 16px 20px;
    margin-top: 16px;
}
.pagination-row {
    display: flex;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 24px;
}
.related-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 14px;
}
.related-card {
    text-decoration: none;
    color: var(--text-primary);
    background: #FAF8F5;
    border: 2px solid var(--border-color);
    border-radius: 10px;
    padding: 14px;
    box-shadow: 3px 3px 0px var(--border-color);
    display: flex;
    flex-direction: column;
    gap: 4px;
    transition: transform 0.1s ease;
}
.related-card:hover {
    transform: translate(-1px, -1px);
    background: #FFFFFF;
}
.related-card-num {
    font-size: 0.75rem;
    font-weight: 900;
    color: var(--accent-dark);
    text-transform: uppercase;
}
.related-card-title {
    font-size: 1.02rem;
    font-weight: 900;
}
.related-card-sub {
    font-size: 0.84rem;
    color: var(--text-secondary);
    font-weight: 700;
}
.site-footer {
    max-width: 880px;
    margin: 0 auto;
    padding: 24px 20px 40px 20px;
    text-align: center;
    font-size: 0.88rem;
    font-weight: 700;
    color: var(--text-secondary);
    border-top: 2px dashed #CBD5E1;
}
.site-footer a {
    color: var(--accent-dark);
    text-decoration: none;
    margin: 0 6px;
}
.site-footer a:hover {
    text-decoration: underline;
}
@media (max-width: 600px) {
    .neo-card {
        padding: 20px 16px;
    }
    h1.page-title {
        font-size: 1.85rem;
    }
}
"""


def build_archive():
    histories = load_and_merge_histories()
    games_path = ROOT_DIR / "backend" / "travelreviews_daily_games.json"
    games = json.loads(games_path.read_text(encoding="utf-8"))

    active = [
        g
        for g in games
        if g.get("status") == "approved" and 1 <= int(g.get("puzzle_number", 0)) <= 120
    ]
    active.sort(key=lambda x: int(x["puzzle_number"]))

    # Assign deterministic filenames & metadata
    for g in active:
        pnum = str(g["puzzle_number"]).zfill(3)
        g["_pnum"] = pnum
        g["_slug"] = f"challenge-{pnum}-{slugify(g['boss_original_title'])}.html"
        g["_region"] = classify_region(float(g.get("lat") or 0), float(g.get("lng") or 0))
        g["_diff"] = difficulty_label(int(g.get("difficulty_tier") or 2))

    landmarks_dir = ROOT_DIR / "landmarks"
    landmarks_dir.mkdir(parents=True, exist_ok=True)
    bo_landmarks_dir = BOXOFFICE_DIR / "travelreviews" / "landmarks"
    bo_landmarks_dir.mkdir(parents=True, exist_ok=True)

    # Group by region for related links & directory index
    by_region = {}
    for g in active:
        by_region.setdefault(g["_region"], []).append(g)

    # 1. Generate each of the 120 individual landmark HTML pages
    for i, g in enumerate(active):
        pnum = g["_pnum"]
        hist = histories[pnum]
        orig_title = g["boss_original_title"]
        loc = g.get("location") or "World Landmark"
        pun_title = g["boss_pun_title"]
        rev_title = g.get("review_title") or "1-Star Tourist Complaint"
        rev_name = g.get("reviewer_name") or "Confused Tourist"
        clue1 = g.get("clue1") or ""
        clue2 = g.get("clue2") or ""
        clue3 = g.get("clue3") or ""
        owner_reply = g.get("boss_pitch") or ""
        coords_str = format_coords(g.get("lat"), g.get("lng"))
        diff = g["_diff"]
        region = g["_region"]
        slug_file = g["_slug"]
        canonical_url = f"https://punfiction.io/travelreviews/landmarks/{slug_file}"
        poster_src = resolve_poster_rel_url(g.get("boss_poster_url", ""))

        prev_g = active[i - 1] if i > 0 else active[-1]
        next_g = active[i + 1] if i + 1 < len(active) else active[0]

        region_peers = [p for p in by_region[region] if p["_pnum"] != pnum]
        start_idx = (i * 3) % max(1, len(region_peers))
        related = (region_peers[start_idx:] + region_peers[:start_idx])[:6]

        wiki_url = f"https://en.wikipedia.org/wiki/Special:Search?search={html.escape(orig_title.replace(' ', '+'))}"
        maps_url = f"https://www.google.com/maps/search/?api=1&query={html.escape((orig_title + ' ' + loc).replace(' ', '+'))}"

        meta_desc = f"Read the comical history of {orig_title} ({loc}) and the 1-star tourist review \"{rev_title}\" in PunFiction Challenge #{pnum}."

        json_ld = json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": f"{orig_title} ({loc}): Comical History & 1-Star Travel Review #{pnum}",
                "description": meta_desc,
                "author": {"@type": "Organization", "name": "PunFiction Editorial Team"},
                "publisher": {
                    "@type": "Organization",
                    "name": "PunFiction",
                    "url": "https://punfiction.io",
                },
                "mainEntityOfPage": canonical_url,
            },
            ensure_ascii=False,
        )

        related_cards_html = "\n".join(
            f"""<a href="./{r['_slug']}" class="related-card">
                <span class="related-card-num">Challenge #{r['_pnum']} • {html.escape(r['_diff'])}</span>
                <span class="related-card-title">{html.escape(r['boss_original_title'])}</span>
                <span class="related-card-sub">📍 {html.escape(r.get('location') or '')} — &ldquo;{html.escape(r.get('review_title') or '')}&rdquo;</span>
            </a>"""
            for r in related
        )

        poster_img_html = (
            f'<img src="{html.escape(poster_src)}" alt="{html.escape(pun_title)} parody postcard of {html.escape(orig_title)}" class="postcard-img" loading="lazy">'
            if poster_src
            else ""
        )

        page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-41EV4HJ1LH"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', 'G-41EV4HJ1LH', {{ 'game_name': 'travel_reviews_archive' }});
    </script>
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1900802133351015" crossorigin="anonymous"></script>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Challenge #{pnum}: {html.escape(orig_title)} ({html.escape(loc)}) — 1-Star Review &amp; History | PunFiction</title>
    <meta name="description" content="{html.escape(meta_desc)}">
    <link rel="canonical" href="{canonical_url}">
    <meta property="og:title" content="Challenge #{pnum}: {html.escape(orig_title)} — 1-Star Travel Review &amp; Field Guide">
    <meta property="og:description" content="{html.escape(hist['headline'])}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{canonical_url}">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='0.9em' font-size='90'>🗺️</text></svg>">
    <link href="https://fonts.googleapis.com/css2?family=Bangers&family=Nunito:wght@400;700;800;900&display=swap" rel="stylesheet">
    <script type="application/ld+json">{json_ld}</script>
    <style>{SHARED_ARCHIVE_CSS}</style>
</head>
<body>
    <header class="site-header">
        <a href="../" class="brand-link">
            <span class="brand-title">Pun<span class="accent">Fiction</span></span>
            <span class="brand-sub">Landmark Field Guides</span>
        </a>
        <nav class="header-nav" aria-label="Primary Navigation">
            <a href="./index.html" class="nav-pill">📚 All 120 Landmarks</a>
            <a href="../?challenge={pnum}" class="nav-pill primary">🎮 Play Challenge #{pnum}</a>
        </nav>
    </header>

    <nav class="breadcrumbs" aria-label="Breadcrumb">
        <a href="../../">Home</a> &rsaquo;
        <a href="../">1-Star Travel Reviews</a> &rsaquo;
        <a href="./index.html">Landmark Field Guides</a> &rsaquo;
        <span>Challenge #{pnum}: {html.escape(orig_title)}</span>
    </nav>

    <main class="container">
        <article class="neo-card">
            <div class="meta-row">
                <span class="badge badge-challenge">Challenge #{pnum}</span>
                <span class="badge badge-region">🌎 {html.escape(region)}</span>
                <span class="badge badge-{diff.lower()}">{html.escape(diff)} Puzzle</span>
            </div>
            <h1 class="page-title">{html.escape(orig_title)}: Comical History &amp; 1-Star Tourist Review</h1>
            <p class="page-deck">{html.escape(hist['headline'])}</p>

            <div class="facts-strip">
                <div class="fact-item">
                    <strong>Real Location</strong>
                    <span>📍 {html.escape(loc)}</span>
                </div>
                <div class="fact-item">
                    <strong>Coordinates</strong>
                    <span>🧭 {html.escape(coords_str)}</span>
                </div>
                <div class="fact-item">
                    <strong>Angry Reviewer</strong>
                    <span>🗣️ {html.escape(rev_name)}</span>
                </div>
            </div>
        </article>

        <section class="neo-card" aria-labelledby="heading-review">
            <h2 id="heading-review" class="section-heading">⭐ The Confused Tourist&rsquo;s 1-Star Review</h2>
            <div class="review-box">
                <div class="stars-row" aria-label="1 out of 5 stars">★☆☆☆☆</div>
                <h3 class="review-headline">&ldquo;{html.escape(rev_title)}&rdquo;</h3>
                <div class="reviewer-byline">Reviewed by {html.escape(rev_name)} • Verified Misguided Visitor</div>
                <blockquote class="review-quote">&ldquo;{html.escape(clue1)}&rdquo;</blockquote>
                <div class="followup-clues">
                    <h3>Additional Tourist Complaints &amp; Clues</h3>
                    <ul>
                        <li>&ldquo;{html.escape(clue2)}&rdquo;</li>
                        <li>&ldquo;{html.escape(clue3)}&rdquo;</li>
                    </ul>
                </div>
            </div>
            <div class="cta-banner">
                <div>
                    <strong>Can you guess the punny parody landmark name from this review?</strong><br>
                    <span>Test your wordplay in the interactive puzzle mode with progressive hints.</span>
                </div>
                <a href="../?challenge={pnum}" class="nav-pill primary">🎯 Solve Challenge #{pnum} Live &rarr;</a>
            </div>
        </section>

        <section class="neo-card essay-prose" aria-labelledby="heading-history">
            <h2 id="heading-history" class="section-heading">🏛️ The Real {html.escape(orig_title)}: A Field Guide</h2>
            <p>{html.escape(hist['p1'])}</p>
            <p>{html.escape(hist['p2'])}</p>
            <p>{html.escape(hist['p3'])}</p>
            <div class="visitor-tip-box">
                💡 <strong>Practical Visitor Tip:</strong> {html.escape(hist['visitor_tip'])}
            </div>
            <div class="ext-links-row">
                <span>Official Reference Links:</span>
                <a href="{wiki_url}" target="_blank" rel="noopener noreferrer">Read about {html.escape(orig_title)} on Wikipedia &nearr;</a>
                <a href="{maps_url}" target="_blank" rel="noopener noreferrer">View {html.escape(orig_title)} on Google Maps &nearr;</a>
            </div>
        </section>

        <section class="neo-card" aria-labelledby="heading-spoiler">
            <h2 id="heading-spoiler" class="section-heading">✉️ Official Management Reply &amp; Parody Postcard</h2>
            <p style="margin-top: 0; font-weight: 700; color: var(--text-secondary);">Want to play the puzzle first? Click <a href="../?challenge={pnum}" style="color: var(--accent-dark); font-weight: 900;">Play Challenge #{pnum}</a> above, or expand the archive dossier below to see the parody landmark answer and management response.</p>
            <details class="spoiler-details">
                <summary>🔓 Reveal Parody Answer, Illustrated Postcard &amp; Owner Response (Spoiler)</summary>
                <div class="spoiler-body">
                    <p class="parody-answer-banner">Parody Landmark: {html.escape(pun_title)}</p>
                    {poster_img_html}
                    <div class="owner-reply-box">
                        <strong>Official Response from Management ({html.escape(orig_title)}):</strong><br>
                        &ldquo;{html.escape(owner_reply)}&rdquo;
                    </div>
                </div>
            </details>
        </section>

        <nav class="pagination-row" aria-label="Challenge Pagination">
            <a href="./{prev_g['_slug']}" class="nav-pill">&larr; Prev: #{prev_g['_pnum']} {html.escape(prev_g['boss_original_title'])}</a>
            <a href="./index.html" class="nav-pill">🗂️ All 120 Landmark Guides</a>
            <a href="./{next_g['_slug']}" class="nav-pill">Next: #{next_g['_pnum']} {html.escape(next_g['boss_original_title'])} &rarr;</a>
        </nav>

        <section class="neo-card" aria-labelledby="heading-related">
            <h2 id="heading-related" class="section-heading">🧭 More Landmark Guides in {html.escape(region)}</h2>
            <div class="related-grid">
                {related_cards_html}
            </div>
        </section>
    </main>

    <footer class="site-footer">
        <p>&copy; 2026 PunFiction. All rights reserved. |
            <a href="../../">Home</a> |
            <a href="../">Play 1-Star Travel Reviews</a> |
            <a href="./index.html">Landmark Archive</a> |
            <a href="../../about.html">About Us</a> |
            <a href="../../how-to-play-travelreviews.html">How to Play</a> |
            <a href="../../privacy.html">Privacy Policy</a> |
            <a href="../../terms.html">Terms of Service</a>
        </p>
    </footer>
</body>
</html>
"""
        out_file = landmarks_dir / slug_file
        out_file.write_text(page_html, encoding="utf-8", newline="\n")
        shutil.copy2(out_file, bo_landmarks_dir / slug_file)

    # 2. Generate Directory Index Hub (/travelreviews/landmarks/index.html)
    region_order = ["Europe", "Americas", "Asia & Oceania", "Africa & Middle East"]
    region_sections_html = []
    for reg in region_order:
        items = by_region.get(reg, [])
        if not items:
            continue
        cards = "\n".join(
            f"""<a href="./{g['_slug']}" class="related-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="related-card-num">Challenge #{g['_pnum']}</span>
                    <span class="badge badge-{g['_diff'].lower()}" style="font-size:0.68rem; padding:2px 7px;">{html.escape(g['_diff'])}</span>
                </div>
                <span class="related-card-title">{html.escape(g['boss_original_title'])}</span>
                <span class="related-card-sub">📍 {html.escape(g.get('location') or '')}</span>
                <span class="related-card-sub" style="color:var(--text-primary); font-style:italic;">&ldquo;{html.escape(g.get('review_title') or '')}&rdquo;</span>
            </a>"""
            for g in items
        )
        region_sections_html.append(
            f"""<section class="neo-card">
                <h2 class="section-heading">🌍 {html.escape(reg)} ({len(items)} Landmark Guides)</h2>
                <div class="related-grid">
                    {cards}
                </div>
            </section>"""
        )

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-41EV4HJ1LH"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', 'G-41EV4HJ1LH', {{ 'game_name': 'travel_reviews_archive_hub' }});
    </script>
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1900802133351015" crossorigin="anonymous"></script>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>World Landmark Field Guides &amp; 1-Star Travel Review Archive (Challenges #001–#120) | PunFiction</title>
    <meta name="description" content="Browse all 120 comical world monument histories, real travel facts, and unhinged 1-star tourist reviews from PunFiction: 1-Star Travel Reviews.">
    <link rel="canonical" href="https://punfiction.io/travelreviews/landmarks/">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='0.9em' font-size='90'>🗺️</text></svg>">
    <link href="https://fonts.googleapis.com/css2?family=Bangers&family=Nunito:wght@400;700;800;900&display=swap" rel="stylesheet">
    <style>{SHARED_ARCHIVE_CSS}</style>
</head>
<body>
    <header class="site-header">
        <a href="../" class="brand-link">
            <span class="brand-title">Pun<span class="accent">Fiction</span></span>
            <span class="brand-sub">Landmark Encyclopedia</span>
        </a>
        <nav class="header-nav" aria-label="Primary Navigation">
            <a href="../../" class="nav-pill">🏠 Portal Home</a>
            <a href="../" class="nav-pill primary">🎮 Play Today&rsquo;s Challenge</a>
        </nav>
    </header>

    <nav class="breadcrumbs" aria-label="Breadcrumb">
        <a href="../../">Home</a> &rsaquo;
        <a href="../">1-Star Travel Reviews</a> &rsaquo;
        <span>World Landmark Field Guides (#001–#120)</span>
    </nav>

    <main class="container">
        <article class="neo-card">
            <h1 class="page-title">World Landmark Field Guides &amp; 1-Star Review Archive</h1>
            <p class="page-deck">Every monument has a real architectural story, an exhausting queue for the gift shop, and at least one traveler who showed up expecting a pancake house.</p>
            <div class="essay-prose">
                <p>Welcome to the complete archive of <strong>PunFiction: 1-Star Travel Reviews</strong>. Across Challenges #001 through #120, we have cataloged the world&rsquo;s greatest architectural wonders, ancient ruins, cathedrals, volcanic calderas, and suspension bridges alongside the bizarre 1-star complaints left by fictional tourists who misread their itineraries by a single syllable.</p>
                <p>Select any landmark below to read a 300-word historical and comedic field guide to the real destination, inspect the full 1-star tourist dossier, jump straight into the interactive wordplay puzzle, or reveal the illustrated parody postcard and management response.</p>
            </div>
        </article>

        {"".join(region_sections_html)}
    </main>

    <footer class="site-footer">
        <p>&copy; 2026 PunFiction. All rights reserved. |
            <a href="../../">Home</a> |
            <a href="../">Play 1-Star Travel Reviews</a> |
            <a href="./index.html">Landmark Archive</a> |
            <a href="../../about.html">About Us</a> |
            <a href="../../how-to-play-travelreviews.html">How to Play</a> |
            <a href="../../privacy.html">Privacy Policy</a> |
            <a href="../../terms.html">Terms of Service</a>
        </p>
    </footer>
</body>
</html>
"""
    (landmarks_dir / "index.html").write_text(index_html, encoding="utf-8", newline="\n")
    (bo_landmarks_dir / "index.html").write_text(index_html, encoding="utf-8", newline="\n")
    print(f"Generated {len(active)} static landmark pages + index.html in {landmarks_dir} and {bo_landmarks_dir}")

    # 3. Generate robots.txt and sitemap.xml
    today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    robots_txt = """User-agent: Mediapartners-Google
Allow: /

User-agent: Googlebot
Allow: /

User-agent: *
Allow: /

Sitemap: https://punfiction.io/sitemap.xml
"""
    (ROOT_DIR / "robots.txt").write_text(robots_txt, encoding="utf-8", newline="\n")
    (BOXOFFICE_DIR / "robots.txt").write_text(robots_txt, encoding="utf-8", newline="\n")

    urls = [
        ("https://punfiction.io/", "1.0", "daily"),
        ("https://punfiction.io/travelreviews/", "1.0", "daily"),
        ("https://punfiction.io/wordvine/", "1.0", "daily"),
        ("https://punfiction.io/travelreviews/landmarks/", "0.9", "daily"),
        ("https://punfiction.io/about.html", "0.8", "monthly"),
        ("https://punfiction.io/how-to-play-travelreviews.html", "0.8", "monthly"),
        ("https://punfiction.io/how-to-play-wordvine.html", "0.8", "monthly"),
        ("https://punfiction.io/privacy.html", "0.6", "monthly"),
        ("https://punfiction.io/terms.html", "0.6", "monthly"),
    ]
    for g in active:
        urls.append((f"https://punfiction.io/travelreviews/landmarks/{g['_slug']}", "0.8", "weekly"))

    url_entries = "\n".join(
        f"""  <url>
    <loc>{loc_url}</loc>
    <lastmod>{today_iso}</lastmod>
    <changefreq>{freq}</changefreq>
    <priority>{prio}</priority>
  </url>"""
        for loc_url, prio, freq in urls
    )
    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{url_entries}
</urlset>
"""
    (ROOT_DIR / "sitemap.xml").write_text(sitemap_xml, encoding="utf-8", newline="\n")
    (BOXOFFICE_DIR / "sitemap.xml").write_text(sitemap_xml, encoding="utf-8", newline="\n")
    print(f"Generated robots.txt and sitemap.xml with {len(urls)} URLs")


if __name__ == "__main__":
    build_archive()
