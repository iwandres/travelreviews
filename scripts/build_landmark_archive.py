import html
import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT_DIR = Path(__file__).resolve().parent.parent
BOXOFFICE_DIR = ROOT_DIR.parent / "PunFiction-BoxOffice"
NEW_BATCH_SCRATCH_DIR = Path(
    r"C:\Users\iwand\.gemini\antigravity\brain\51884bdc-9a25-4bb7-ba9d-402c41e9d16c\scratch"
)

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


def compute_current_live_count(max_puzzle: int) -> int:
    try:
        pt = ZoneInfo("America/Los_Angeles")
        now_pt = datetime.now(pt)
        now_naive_utc = datetime(
            now_pt.year, now_pt.month, now_pt.day, now_pt.hour, now_pt.minute, now_pt.second
        )
        start_naive_utc = datetime(2026, 7, 4, 2, 0, 0)
        days_elapsed = max(0, int((now_naive_utc - start_naive_utc).total_seconds() // 86400))
    except Exception:
        # Fallback UTC-7 offset matching START_DATE_PT = 2026-07-04T02:00:00-07:00
        start_utc = datetime(2026, 7, 4, 9, 0, 0, tzinfo=timezone.utc)
        now_utc = datetime.now(timezone.utc)
        days_elapsed = max(0, int((now_utc - start_utc).total_seconds() // 86400))
    return min(max_puzzle, max(1, days_elapsed + 1))


def format_unlock_date_str(puzzle_num: int) -> str:
    unlock_dt = datetime(2026, 7, 4) + timedelta(days=puzzle_num - 1)
    return f"{unlock_dt.strftime('%B')} {unlock_dt.day}, {unlock_dt.year} at 2:00 AM PT"


def load_and_merge_histories(expected_total: int) -> dict:
    hist_path = ROOT_DIR / "backend" / "travelreviews_landmark_histories.json"
    merged = {}
    if hist_path.exists():
        existing = json.loads(hist_path.read_text(encoding="utf-8"))
        for k, v in existing.items():
            merged[str(int(k)).zfill(3)] = v

    # Merge any newly generated batch files if present
    if NEW_BATCH_SCRATCH_DIR.exists():
        for batch_file in sorted(NEW_BATCH_SCRATCH_DIR.glob("essays_*.json")):
            data = json.loads(batch_file.read_text(encoding="utf-8"))
            for k, v in data.items():
                merged[str(int(k)).zfill(3)] = v

    if len(merged) < expected_total:
        missing = [
            str(n).zfill(3)
            for n in range(1, expected_total + 1)
            if str(n).zfill(3) not in merged
        ]
        raise RuntimeError(
            f"Expected {expected_total} essay entries, found {len(merged)}. Missing: {missing[:15]}"
        )

    # Sort deterministically and validate word counts & anti-AI rules
    ordered = {}
    for pnum in sorted(merged.keys(), key=lambda x: int(x)):
        item = merged[pnum]
        full_text = f"{item.get('p1', '')} {item.get('p2', '')} {item.get('p3', '')}"
        words = full_text.split()
        if len(words) < 300:
            raise ValueError(f"Challenge #{pnum} essay has only {len(words)} words (< 300)")
        lower_all = f"{item.get('headline', '')} {full_text} {item.get('visitor_tip', '')}".lower()
        for phrase in BANNED_AI_PHRASES:
            if phrase in lower_all:
                raise ValueError(f"Challenge #{pnum} contains banned phrase '{phrase}'")
        ordered[pnum] = item

    hist_path.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    if (BOXOFFICE_DIR / "backend").exists():
        shutil.copy2(hist_path, BOXOFFICE_DIR / "backend" / "travelreviews_landmark_histories.json")
    print(f"Saved and validated {len(ordered)} landmark histories in {hist_path}")
    return ordered


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
.badge-today {
    background: #00AA6C;
    color: #FFFFFF;
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
.related-card.future-locked,
.related-card.peer-overflow {
    display: none !important;
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
.landmark-locked-notice {
    display: none;
    text-align: center;
    padding: 36px 28px;
}
html.landmark-locked .landmark-live-content {
    display: none !important;
}
html.landmark-locked .landmark-locked-notice {
    display: block !important;
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


def build_schedule_js(active: list) -> str:
    max_puzzle = max(int(g["puzzle_number"]) for g in active)
    manifest = [
        [int(g["puzzle_number"]), g["_pnum"], g["_slug"], g["boss_original_title"]]
        for g in active
    ]
    manifest_json = json.dumps(manifest, ensure_ascii=False)
    return f"""/**
 * PunFiction Landmark Field Guides — Daily Live Release Sync
 * Synchronizes landmark availability 1:1 with 1-Star Travel Reviews daily challenges
 * (New puzzle + landmark unlock together daily at 2:00 AM America/Los_Angeles, epoch 2026-07-04).
 */
(function () {{
    var MAX_LANDMARK_PUZZLE = {max_puzzle};
    var MANIFEST = {manifest_json};

    function getDaysElapsedSinceStart() {{
        try {{
            var now = new Date();
            var parts = new Intl.DateTimeFormat("en-US", {{
                timeZone: "America/Los_Angeles",
                year: "numeric",
                month: "numeric",
                day: "numeric",
                hour: "numeric",
                minute: "numeric",
                second: "numeric",
                hour12: false
            }}).formatToParts(now);
            var val = function (t) {{
                return parseInt(parts.find(function (p) {{ return p.type === t; }}).value, 10);
            }};
            var nowPTUtc = Date.UTC(
                val("year"),
                val("month") - 1,
                val("day"),
                val("hour") % 24,
                val("minute"),
                val("second")
            );
            var startPTUtc = Date.UTC(2026, 6, 4, 2, 0, 0);
            return Math.max(0, Math.floor((nowPTUtc - startPTUtc) / 86400000));
        }} catch (e) {{
            var start = new Date("2026-07-04T02:00:00-07:00");
            return Math.max(0, Math.floor((Date.now() - start.getTime()) / 86400000));
        }}
    }}

    function pad3(n) {{
        return String(n).padStart(3, "0");
    }}

    var liveCount = Math.min(MAX_LANDMARK_PUZZLE, Math.max(1, getDaysElapsedSinceStart() + 1));
    var livePadded = pad3(liveCount);

    // 1. Update total live landmark counters across header/pagination/locked notice
    var totalEls = document.querySelectorAll(".live-landmark-total");
    for (var i = 0; i < totalEls.length; i++) {{
        totalEls[i].textContent = String(liveCount);
    }}

    var rangeEls = document.querySelectorAll(".live-landmark-max-padded");
    for (var r = 0; r < rangeEls.length; r++) {{
        rangeEls[r].textContent = "#" + livePadded;
    }}

    // 2. Directory Index Hub (/travelreviews/landmarks/index.html)
    var hubMain = document.getElementById("landmarks-hub-main");
    if (hubMain) {{
        document.title =
            "World Landmark Field Guides & 1-Star Travel Review Archive (Challenges #001\\u2013#" +
            livePadded +
            ") | PunFiction";
        var cards = hubMain.querySelectorAll(".related-card[data-puzzle]");
        for (var c = 0; c < cards.length; c++) {{
            var card = cards[c];
            var pnum = parseInt(card.getAttribute("data-puzzle"), 10);
            var isLive = pnum <= liveCount;
            card.classList.toggle("future-locked", !isLive);
            var todayBadge = card.querySelector(".card-today-pill");
            if (pnum === liveCount) {{
                if (!todayBadge) {{
                    var badgeRow = card.querySelector(".card-top-row");
                    if (badgeRow) {{
                        var pill = document.createElement("span");
                        pill.className = "badge badge-today card-today-pill";
                        pill.style.fontSize = "0.65rem";
                        pill.style.padding = "2px 6px";
                        pill.textContent = "Today";
                        badgeRow.appendChild(pill);
                    }}
                }}
            }} else if (todayBadge) {{
                todayBadge.remove();
            }}
        }}

        var sections = hubMain.querySelectorAll(".region-section");
        for (var s = 0; s < sections.length; s++) {{
            var sec = sections[s];
            var secCards = sec.querySelectorAll(".related-card[data-puzzle]");
            var visCount = 0;
            for (var k = 0; k < secCards.length; k++) {{
                if (!secCards[k].classList.contains("future-locked")) visCount++;
            }}
            var countSpan = sec.querySelector(".region-live-count");
            if (countSpan) {{
                countSpan.textContent = visCount + (visCount === 1 ? " Landmark Guide" : " Landmark Guides");
            }}
            sec.style.display = visCount > 0 ? "" : "none";
        }}
        return;
    }}

    // 3. Individual Landmark Field Guide Page
    var pagePuzzleAttr = document.documentElement.getAttribute("data-puzzle-num");
    if (!pagePuzzleAttr) return;
    var thisPuzzleNum = parseInt(pagePuzzleAttr, 10);

    if (thisPuzzleNum > liveCount) {{
        document.documentElement.classList.add("landmark-locked");
        document.title = "Challenge #" + pad3(thisPuzzleNum) + " \\u2014 Unlocks Soon | PunFiction";
        return;
    }} else {{
        document.documentElement.classList.remove("landmark-locked");
    }}

    // Sync Prev / Next buttons so navigation wraps cleanly within 1..liveCount
    var liveItems = [];
    for (var m = 0; m < MANIFEST.length; m++) {{
        if (MANIFEST[m][0] <= liveCount) liveItems.push(MANIFEST[m]);
    }}
    var currIdx = -1;
    for (var idx = 0; idx < liveItems.length; idx++) {{
        if (liveItems[idx][0] === thisPuzzleNum) {{
            currIdx = idx;
            break;
        }}
    }}
    if (currIdx !== -1 && liveItems.length > 0) {{
        var prevItem = currIdx > 0 ? liveItems[currIdx - 1] : liveItems[liveItems.length - 1];
        var nextItem = currIdx + 1 < liveItems.length ? liveItems[currIdx + 1] : liveItems[0];
        var prevEl = document.getElementById("nav-prev-landmark");
        var nextEl = document.getElementById("nav-next-landmark");
        if (prevEl) {{
            prevEl.href = "./" + prevItem[2];
            prevEl.textContent = "\\u2190 Prev: #" + prevItem[1] + " " + prevItem[3];
        }}
        if (nextEl) {{
            nextEl.href = "./" + nextItem[2];
            nextEl.textContent = "Next: #" + nextItem[1] + " " + nextItem[3] + " \\u2192";
        }}
    }}

    // Filter related region cards so only live landmarks (<= liveCount) appear (max 6)
    var relGrid = document.getElementById("related-region-grid");
    if (relGrid) {{
        var relCards = relGrid.querySelectorAll(".related-card[data-puzzle]");
        var shown = 0;
        for (var rc = 0; rc < relCards.length; rc++) {{
            var rcNum = parseInt(relCards[rc].getAttribute("data-puzzle"), 10);
            if (rcNum <= liveCount && shown < 6) {{
                relCards[rc].classList.remove("future-locked", "peer-overflow");
                shown++;
            }} else {{
                relCards[rc].classList.add(rcNum > liveCount ? "future-locked" : "peer-overflow");
            }}
        }}
    }}
}})();
"""


INLINE_EARLY_LOCK_SNIPPET = """<script>
    (function(){
        try {
            var p = parseInt(document.documentElement.getAttribute("data-puzzle-num"), 10);
            if (!p) return;
            var parts = new Intl.DateTimeFormat("en-US", {
                timeZone: "America/Los_Angeles",
                year: "numeric", month: "numeric", day: "numeric",
                hour: "numeric", minute: "numeric", second: "numeric", hour12: false
            }).formatToParts(new Date());
            var v = function(t){ return parseInt(parts.find(function(x){return x.type===t;}).value, 10); };
            var days = Math.max(0, Math.floor((Date.UTC(v("year"), v("month")-1, v("day"), v("hour")%24, v("minute"), v("second")) - Date.UTC(2026, 6, 4, 2, 0, 0)) / 86400000));
            var live = Math.max(1, days + 1);
            if (p > live) document.documentElement.classList.add("landmark-locked");
            else document.documentElement.classList.remove("landmark-locked");
        } catch (e) {}
    })();
    </script>"""


def sync_max_puzzle_constants(max_puzzle: int, build_live_count: int):
    # Keep MAX_LANDMARK_GUIDE_PUZZLE in app.js and MAX_LANDMARKS in BoxOffice/index.html synced
    for app_js_path in [
        ROOT_DIR / "app.js",
        BOXOFFICE_DIR / "travelreviews" / "app.js",
    ]:
        if app_js_path.exists():
            txt = app_js_path.read_text(encoding="utf-8")
            updated = re.sub(
                r"const MAX_LANDMARK_GUIDE_PUZZLE = \d+;",
                f"const MAX_LANDMARK_GUIDE_PUZZLE = {max_puzzle};",
                txt,
            )
            if updated != txt:
                app_js_path.write_text(updated, encoding="utf-8", newline="\n")

    bo_index = BOXOFFICE_DIR / "index.html"
    if bo_index.exists():
        txt = bo_index.read_text(encoding="utf-8")
        updated = re.sub(r"var MAX_LANDMARKS = \d+;", f"var MAX_LANDMARKS = {max_puzzle};", txt)
        updated = re.sub(
            r'(<span id="portal-live-landmark-count">)\d+(</span>)',
            rf"\g<1>{build_live_count}\g<2>",
            updated,
        )
        updated = re.sub(
            r'(<span id="portal-live-landmark-btn-count">)\d+(</span>)',
            rf"\g<1>{build_live_count}\g<2>",
            updated,
        )
        if updated != txt:
            bo_index.write_text(updated, encoding="utf-8", newline="\n")


def build_archive():
    games_path = ROOT_DIR / "backend" / "travelreviews_daily_games.json"
    games = json.loads(games_path.read_text(encoding="utf-8"))

    approved_all = [
        g for g in games if g.get("status") == "approved" and int(g.get("puzzle_number", 0)) >= 1
    ]
    approved_all.sort(key=lambda x: int(x["puzzle_number"]))
    max_puzzle = max(int(g["puzzle_number"]) for g in approved_all)

    histories = load_and_merge_histories(expected_total=max_puzzle)

    active = [g for g in approved_all if str(int(g["puzzle_number"])).zfill(3) in histories]
    build_live_count = compute_current_live_count(max_puzzle)
    build_live_padded = str(build_live_count).zfill(3)
    print(f"Building {len(active)} total landmark guides (currently live today: {build_live_count})")

    # Assign deterministic filenames & metadata
    for g in active:
        pnum_int = int(g["puzzle_number"])
        pnum = str(pnum_int).zfill(3)
        g["_pnum_int"] = pnum_int
        g["_pnum"] = pnum
        g["_slug"] = f"challenge-{pnum}-{slugify(g['boss_original_title'])}.html"
        g["_region"] = classify_region(float(g.get("lat") or 0), float(g.get("lng") or 0))
        g["_diff"] = difficulty_label(int(g.get("difficulty_tier") or 2))

    landmarks_dir = ROOT_DIR / "landmarks"
    landmarks_dir.mkdir(parents=True, exist_ok=True)
    bo_landmarks_dir = BOXOFFICE_DIR / "travelreviews" / "landmarks"
    bo_landmarks_dir.mkdir(parents=True, exist_ok=True)

    # Clean old challenge-*.html files so no stale filenames remain
    for old_f in list(landmarks_dir.glob("challenge-*.html")) + list(
        bo_landmarks_dir.glob("challenge-*.html")
    ):
        old_f.unlink()

    # Write shared landmark-schedule.js
    schedule_js = build_schedule_js(active)
    schedule_version = "v=2"
    (landmarks_dir / "landmark-schedule.js").write_text(schedule_js, encoding="utf-8", newline="\n")
    (bo_landmarks_dir / "landmark-schedule.js").write_text(schedule_js, encoding="utf-8", newline="\n")

    # Group by region for related links & directory index
    by_region = {}
    for g in active:
        by_region.setdefault(g["_region"], []).append(g)

    live_at_build = [g for g in active if g["_pnum_int"] <= build_live_count]

    # 1. Generate each of the 181 individual landmark HTML pages
    for i, g in enumerate(active):
        pnum_int = g["_pnum_int"]
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
        unlock_date_str = format_unlock_date_str(pnum_int)
        html_locked_class = ' class="landmark-locked"' if pnum_int > build_live_count else ""

        # Default Prev/Next within live_at_build (updated dynamically every day by landmark-schedule.js)
        if pnum_int <= build_live_count and live_at_build:
            live_idx = next(
                (idx for idx, item in enumerate(live_at_build) if item["_pnum_int"] == pnum_int), 0
            )
            prev_g = live_at_build[live_idx - 1] if live_idx > 0 else live_at_build[-1]
            next_g = (
                live_at_build[live_idx + 1]
                if live_idx + 1 < len(live_at_build)
                else live_at_build[0]
            )
        else:
            prev_g = active[i - 1] if i > 0 else active[-1]
            next_g = active[i + 1] if i + 1 < len(active) else active[0]

        # Candidate peers in region: place live peers first so 6 are always ready, plus future peers for later days
        region_peers_all = [p for p in by_region[region] if p["_pnum"] != pnum]
        live_peers = [p for p in region_peers_all if p["_pnum_int"] <= build_live_count]
        future_peers = [p for p in region_peers_all if p["_pnum_int"] > build_live_count]
        if live_peers:
            s_idx = (i * 3) % len(live_peers)
            rotated_live = (live_peers[s_idx:] + live_peers[:s_idx])[:8]
        else:
            rotated_live = []
        if future_peers:
            f_idx = (i * 2) % len(future_peers)
            rotated_future = (future_peers[f_idx:] + future_peers[:f_idx])[:6]
        else:
            rotated_future = []
        related_candidates = rotated_live + rotated_future

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

        related_cards_list = []
        vis_so_far = 0
        for r in related_candidates:
            r_int = r["_pnum_int"]
            extra_cls = ""
            if r_int > build_live_count:
                extra_cls = " future-locked"
            elif vis_so_far >= 6:
                extra_cls = " peer-overflow"
            else:
                vis_so_far += 1
            related_cards_list.append(
                f"""<a href="./{r['_slug']}" class="related-card{extra_cls}" data-puzzle="{r_int}">
                <span class="related-card-num">Challenge #{r['_pnum']} • {html.escape(r['_diff'])}</span>
                <span class="related-card-title">{html.escape(r['boss_original_title'])}</span>
                <span class="related-card-sub">📍 {html.escape(r.get('location') or '')} — &ldquo;{html.escape(r.get('review_title') or '')}&rdquo;</span>
            </a>"""
            )
        related_cards_html = "\n".join(related_cards_list)

        poster_img_html = (
            f'<img src="{html.escape(poster_src)}" alt="{html.escape(pun_title)} parody postcard of {html.escape(orig_title)}" class="postcard-img" loading="lazy">'
            if poster_src
            else ""
        )

        page_html = f"""<!DOCTYPE html>
<html lang="en" data-puzzle-num="{pnum_int}"{html_locked_class}>
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
    {INLINE_EARLY_LOCK_SNIPPET}
</head>
<body>
    <header class="site-header">
        <a href="../" class="brand-link">
            <span class="brand-title">Pun<span class="accent">Fiction</span></span>
            <span class="brand-sub">Landmark Field Guides</span>
        </a>
        <nav class="header-nav" aria-label="Primary Navigation">
            <a href="./index.html" class="nav-pill">📚 All <span class="live-landmark-total">{build_live_count}</span> Landmarks</a>
            <a href="../?challenge={pnum}" class="nav-pill primary landmark-live-content">🎮 Play Challenge #{pnum}</a>
        </nav>
    </header>

    <nav class="breadcrumbs" aria-label="Breadcrumb">
        <a href="../../">Home</a> &rsaquo;
        <a href="../">1-Star Travel Reviews</a> &rsaquo;
        <a href="./index.html">Landmark Field Guides</a> &rsaquo;
        <span class="landmark-live-content">Challenge #{pnum}: {html.escape(orig_title)}</span>
        <span class="landmark-locked-notice" style="padding:0; display:none;">Challenge #{pnum} (Unlocks Soon)</span>
    </nav>

    <main class="container">
        <section class="neo-card landmark-locked-notice" aria-live="polite">
            <div class="meta-row" style="justify-content:center;">
                <span class="badge badge-challenge">🔒 Upcoming Daily Landmark • Challenge #{pnum}</span>
            </div>
            <h1 class="page-title">This Landmark Unlocks With Challenge #{pnum}!</h1>
            <p class="page-deck" style="max-width:620px; margin:0 auto 18px auto;">
                Each Landmark Field Guide releases on the exact same day its daily puzzle goes live (<strong>{html.escape(unlock_date_str)}</strong>), so there are always the same number of landmarks to explore as puzzles available.
            </p>
            <div style="display:flex; flex-wrap:wrap; gap:12px; justify-content:center; margin-top:20px;">
                <a href="../" class="nav-pill primary">🎮 Play Today&rsquo;s Live Challenge</a>
                <a href="./index.html" class="nav-pill">📚 Browse All <span class="live-landmark-total">{build_live_count}</span> Live Landmarks</a>
            </div>
        </section>

        <div class="landmark-live-content">
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
                <a id="nav-prev-landmark" href="./{prev_g['_slug']}" class="nav-pill">&larr; Prev: #{prev_g['_pnum']} {html.escape(prev_g['boss_original_title'])}</a>
                <a href="./index.html" class="nav-pill">🗂️ All <span class="live-landmark-total">{build_live_count}</span> Landmark Guides</a>
                <a id="nav-next-landmark" href="./{next_g['_slug']}" class="nav-pill">Next: #{next_g['_pnum']} {html.escape(next_g['boss_original_title'])} &rarr;</a>
            </nav>

            <section class="neo-card" aria-labelledby="heading-related">
                <h2 id="heading-related" class="section-heading">🧭 More Landmark Guides in {html.escape(region)}</h2>
                <div id="related-region-grid" class="related-grid">
                    {related_cards_html}
                </div>
            </section>
        </div>
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
    <script src="./landmark-schedule.js?{schedule_version}"></script>
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
        live_in_reg = sum(1 for g in items if g["_pnum_int"] <= build_live_count)
        cards_list = []
        for g in items:
            p_int = g["_pnum_int"]
            locked_cls = " future-locked" if p_int > build_live_count else ""
            today_pill_html = (
                '<span class="badge badge-today card-today-pill" style="font-size:0.65rem; padding:2px 6px;">Today</span>'
                if p_int == build_live_count
                else ""
            )
            cards_list.append(
                f"""<a href="./{g['_slug']}" class="related-card{locked_cls}" data-puzzle="{p_int}">
                <div class="card-top-row" style="display:flex; justify-content:space-between; align-items:center; gap:6px; flex-wrap:wrap;">
                    <span class="related-card-num">Challenge #{g['_pnum']}</span>
                    <span style="display:inline-flex; gap:4px; align-items:center;">
                        {today_pill_html}
                        <span class="badge badge-{g['_diff'].lower()}" style="font-size:0.68rem; padding:2px 7px;">{html.escape(g['_diff'])}</span>
                    </span>
                </div>
                <span class="related-card-title">{html.escape(g['boss_original_title'])}</span>
                <span class="related-card-sub">📍 {html.escape(g.get('location') or '')}</span>
                <span class="related-card-sub" style="color:var(--text-primary); font-style:italic;">&ldquo;{html.escape(g.get('review_title') or '')}&rdquo;</span>
            </a>"""
            )
        cards = "\n".join(cards_list)
        label_word = "Landmark Guide" if live_in_reg == 1 else "Landmark Guides"
        region_sections_html.append(
            f"""<section class="neo-card region-section" data-region="{html.escape(reg)}">
                <h2 class="section-heading">🌍 {html.escape(reg)} (<span class="region-live-count">{live_in_reg} {label_word}</span>)</h2>
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
    <title>World Landmark Field Guides &amp; 1-Star Travel Review Archive (Challenges #001–#{build_live_padded}) | PunFiction</title>
    <meta name="description" content="Browse real-world monument histories, travel field notes, and unhinged 1-star tourist reviews released daily alongside each live PunFiction challenge.">
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
        <span>World Landmark Field Guides (#001–<span class="live-landmark-max-padded">#{build_live_padded}</span>)</span>
    </nav>

    <main id="landmarks-hub-main" class="container">
        <article class="neo-card">
            <div class="meta-row">
                <span class="badge badge-today">📅 <span class="live-landmark-total">{build_live_count}</span> Live Landmarks • New Guide Released Daily at 2:00 AM PT</span>
            </div>
            <h1 class="page-title">World Landmark Field Guides &amp; 1-Star Review Archive</h1>
            <p class="page-deck">Every monument has a real architectural story, an exhausting queue for the gift shop, and at least one traveler who showed up expecting a pancake house.</p>
            <div class="essay-prose">
                <p>Welcome to the live landmark archive of <strong>PunFiction: 1-Star Travel Reviews</strong>. A new Landmark Field Guide unlocks every single day on the exact same schedule as its daily puzzle—so across Challenges #001 through <span class="live-landmark-max-padded">#{build_live_padded}</span>, there are always the exact same number of landmarks to explore (<strong class="live-landmark-total">{build_live_count}</strong>) as puzzles available to play.</p>
                <p style="margin-bottom:0;">Select any live landmark below to read a 300-word historical and comedic field guide to the real destination, inspect the full 1-star tourist dossier, jump straight into the interactive wordplay puzzle, or reveal the illustrated parody postcard and management response.</p>
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
    <script src="./landmark-schedule.js?{schedule_version}"></script>
</body>
</html>
"""
    (landmarks_dir / "index.html").write_text(index_html, encoding="utf-8", newline="\n")
    (bo_landmarks_dir / "index.html").write_text(index_html, encoding="utf-8", newline="\n")
    print(f"Generated {len(active)} static landmark pages + index.html + landmark-schedule.js")

    # Sync constants across app.js and BoxOffice/index.html
    sync_max_puzzle_constants(max_puzzle=max_puzzle, build_live_count=build_live_count)

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
