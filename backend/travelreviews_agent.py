"""
Expert Curation Agent for PunFiction: 1-Star Travel Reviews.

This module implements an autonomous, guardrail-driven curation pipeline that handles
the first four stages of the Travel Reviews Curation Hub:
  1. Global Landmark Discovery (Seed Database)
  2. Guardrail-Scored Pun Candidate Generation & Selection
  3. Progressive 3-Clue, Reviewer Handle & Sarcastic Owner Reply Generation
  4. Parodied Postcard Illustration Generation

All puzzle candidates are prepared end-to-end up to the Postcard stage and placed
in the Human Curation Queue where the human curator can:
  - Approve (compiles into the Daily Challenge Schedule)
  - Decline (marks pun as rejected and cleans up candidate assets)
  - Re-do Pun Word (picks/accepts a new pun and cascades to new Clues + Postcard)
  - Re-do Clues (regenerates progressive clues & owner reply for the current pun)
  - Re-do Postcard (regenerates postcard prompt & artwork in the chosen style)
"""

import io
import json
import os
import random
import re
import time
import urllib.parse


# ==============================================================================
# DEEP DATA ANALYSIS GUARDRAILS (Derived from 122 Approved Daily Challenges
# vs. Explicitly Rejected Clues & Unchosen Pending Puns)
# ==============================================================================

PUZZLE_GUARDRAILS = {
    "summary": (
        "Distilled from 122 human-approved daily games, 6 explicitly rejected clues, "
        "and 339 pending puns in the 1-Star Travel Reviews dataset."
    ),
    "landmark_rules": [
        "Must be a globally recognizable, iconic landmark, natural wonder, or travel destination with a distinct physical silhouette.",
        "Balance across all 7 themes: ancient_ruins, natural_wonders, historic_monuments, castles_cathedrals, bridges_canals, streets_squares, modern_skyscrapers.",
        "Exclude somber memorials, war graves, tragedy sites, or obscure local attractions (e.g., never parody Anne Frank House, Auschwitz, 9/11 Memorial, Berlin Wall Memorial).",
        "Must have phonetically rich syllables that lend themselves to concrete noun substitutions."
    ],
    "pun_positive_rules": [
        "CONCRETE TANGIBLE NOUN SUBSTITUTION: Replace a word or syllable with a tangible, everyday physical object that is hilarious to visualize and complain about.",
        "Top-performing categories from human curation: (1) Food & Drink (Waffle Tower, Sconehenge, Sangria Família, Chicken Pizza, Banana Canal, Burger Khalifa, Coleslaw Museum, Muffin Horn, Space Noodle, San Tortellini, Matcha Picchu, Ramen Forum, Blarney Casserole, Everglaze Donut Park), (2) Household Objects & Apparel (Golden Gate Fridge, Loofah Museum, Pajama Canal, Alca-trousers Island, Towel of London, Stone Hinge, Pillowstone National Park, Spandex Steps, Cleaning Tower of Pisa, My Shoe Picchu), (3) Vivid Animals & Characters (Great Whale of China, Pyramids of Geezer, Otter-Dame Cathedral, Brandenburg Goat, Gator-way Arch, Victoria's Fowls, Umpire State Building).",
        "SINGLE-TWIST PHONETIC CLARITY: Keep enough of the original landmark's phonetic cadence intact so players can deduce the pun once they recognize the real landmark.",
        "VISUAL POSTCARD TEST: Ask 'Can an illustrator draw this landmark fused with this literal object in one unmistakable image?' If yes, it passes."
    ],
    "pun_negative_examples": [
        {
            "rejected_pun": "Lover Museum",
            "original_name": "Louvre Museum",
            "approved_alternative": "Loofah Museum",
            "why_rejected": "Abstract/cliché concept ('Lover') lacks physical comedy; a giant bath sponge ('Loofah') inside a fine art gallery is concrete and hilarious."
        },
        {
            "rejected_pun": "Mount Cleverest",
            "original_name": "Mount Everest",
            "approved_alternative": "Mount Saint Melons / Mound Fudgey",
            "why_rejected": "Abstract adjective ('Cleverest') cannot be drawn as a concrete object on a postcard or experienced physically by a confused tourist."
        },
        {
            "rejected_pun": "Mount Fuzzy",
            "original_name": "Mount Fuji",
            "approved_alternative": "Mound Fudgey",
            "why_rejected": "Vague texture adjective ('Fuzzy') is weak compared to a concrete dessert ('Fudgey' chocolate mound)."
        },
        {
            "rejected_pun": "Sagrada Formula",
            "original_name": "Sagrada Família",
            "approved_alternative": "Sangria Família",
            "why_rejected": "Abstract math/science term ('Formula') is dry and unfunny compared to a pitcher of Spanish fruit wine ('Sangria')."
        },
        {
            "rejected_pun": "Golden Grate Bridge",
            "original_name": "Golden Gate Bridge",
            "approved_alternative": "Golden Gate Fridge",
            "why_rejected": "A metal grate is visually mundane and already belongs on a bridge, whereas a giant refrigerator spanning San Francisco Bay is absurd and iconic."
        },
        {
            "rejected_pun": "A Cappella-Polis of Athens",
            "original_name": "Acropolis of Athens",
            "approved_alternative": "Park the None (Parthenon)",
            "why_rejected": "Clunky multi-syllable stretch that is awkward to type and hard to deduce."
        }
    ],
    "clue_rules": [
        "BREVITY: Each of Clue 1, Clue 2, and Clue 3 MUST be a short, punchy 1-star review snippet or sentence fragment (strictly 6 to 15 words). Use '...' or '!' for comedic pacing.",
        "CLUE 1 (Geographic/Cultural Anchor + Literal Delusion): Subtle nod to the real landmark's location/setting paired with the reviewer's absurd literal expectation of the pun object.",
        "CLUE 2 (Architectural/Natural Feature + Physical Mishap): Combines a real physical feature of the landmark (e.g., marble columns, suspension cables, volcanic crater, gothic spires) with a failed attempt to eat, wear, or use the pun item.",
        "CLUE 3 (Unmistakable Wordplay Convergence): Makes both the real landmark identity and the literal pun object obvious without explicitly stating the exact original landmark name or full pun name.",
        "REVIEWER HANDLE: A clever, punny username matching the complaint (e.g., 'SyrupSlinger', 'ScrubbieDoo', 'FrostyFogger'), without the '@' symbol.",
        "OWNER REPLY: 1-2 sentences max from the sarcastic management of the ACTUAL landmark correcting the tourist's delusion by referencing the real structure's materials/history. NEVER state the exact original landmark name or pun name in the owner reply."
    ]
}

VALID_THEMES = [
    "ancient_ruins",
    "natural_wonders",
    "historic_monuments",
    "castles_cathedrals",
    "bridges_canals",
    "streets_squares",
    "modern_skyscrapers"
]

ART_STYLES = {
    "cartoon": "Comical cartoon illustration, bold lines, bright vibrant colors, humorous caricature, white postcard border.",
    "watercolor": "Whimsical watercolor and ink sketch, detailed storybook style, soft textures, pastel colors, artistically detailed.",
    "retro": "Vintage 1950s travel poster style, retro flat vector design, bold colors, screen-printed poster aesthetic.",
    "wpa": "Old school vintage travel illustration style, rooted in 1930s WPA-era silk-screened travel posters and 1960s lithographs, featuring bold shapes, muted earthy color palettes, and hand-drawn typography.",
    "vintage": "Classic distressed linen texture vintage postcard style, hand-colored photo print aesthetic, 1930s travel style.",
    "pop-art": "Vibrant Pop Art style, bold outlines, screen print dot texture, retro comic book feel, high contrast colors."
}


def normalize_name(name):
    """Normalize a landmark or pun name for deduplication checks."""
    if not name:
        return ""
    import unicodedata
    s = unicodedata.normalize("NFD", str(name).lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s)


class TravelReviewsCurationAgent:
    """
    Expert Agent that orchestrates Landmark Discovery, Guardrail Pun Generation,
    Progressive Clues & Owner Reply Generation, Postcard Creation, and Targeted Re-dos.
    """

    def __init__(
        self,
        landmarks_file,
        puns_file,
        clues_file,
        postcards_file,
        daily_games_file,
        cartoons_dir,
        load_json_fn,
        save_json_fn,
        get_theme_fn,
        boxoffice_root=None,
        travelreviews_root=None,
        api_key=None,
        analytics_file=None
    ):
        self.landmarks_file = landmarks_file
        self.puns_file = puns_file
        self.clues_file = clues_file
        self.postcards_file = postcards_file
        self.daily_games_file = daily_games_file
        self.cartoons_dir = cartoons_dir
        self.load_json = load_json_fn
        self.save_json = save_json_fn
        self.get_theme = get_theme_fn
        self.boxoffice_root = boxoffice_root
        self.travelreviews_root = travelreviews_root
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.analytics_file = analytics_file or os.path.join(
            os.path.dirname(self.landmarks_file), "travelreviews_analytics.json"
        )

    def _get_client(self):
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is not set.")
        from google import genai
        return genai.Client(api_key=self.api_key)

    def _delete_image_file(self, img_path):
        """Remove a generated postcard image file from disk if it exists."""
        if not img_path or not img_path.startswith("/assets/"):
            return
        clean_path = urllib.parse.unquote(img_path.strip("/"))
        roots = [r for r in [self.travelreviews_root, self.boxoffice_root] if r]
        for root in set(roots):
            candidates = [
                os.path.join(root, "travelreviews", *clean_path.split("/")),
                os.path.join(root, *clean_path.split("/"))
            ]
            for file_to_delete in candidates:
                if os.path.exists(file_to_delete) and not os.path.isdir(file_to_delete):
                    try:
                        os.remove(file_to_delete)
                        print(f"[CurationAgent] Deleted old/rejected image: {file_to_delete}")
                    except Exception as e:
                        print(f"[CurationAgent] Failed to delete {file_to_delete}: {e}")

    # ==========================================================================
    # INTERNAL QUALITY ANALYTICS & ADAPTIVE FEEDBACK PIPELINE
    # ==========================================================================
    def load_analytics(self):
        """Load the persistent curation quality analytics ledger."""
        data = self.load_json(self.analytics_file, None)
        if not isinstance(data, dict) or "events" not in data:
            data = {
                "version": 1,
                "created_at": int(time.time()),
                "events": []
            }
        return data

    def save_analytics(self, data):
        """Save the persistent curation quality analytics ledger."""
        self.save_json(self.analytics_file, data)

    def record_signal(
        self,
        signal_type,
        stage="agent_queue",
        clue_id=None,
        postcard_id=None,
        landmark_name="",
        location="",
        pun_name="",
        redo_type=None,
        old_value=None,
        new_value=None,
        art_style="",
        page_theme="",
        agent_score=None,
        redo_count_at_event=0,
        was_runner_up_selected=False,
        human_feedback=None,
        decline_reason=None
    ):
        """
        Record a quality telemetry signal from the Curation Hub:
          - signal_type == 'approve': Positive signal (+1.0 for 0-redo first-pass, +0.75 for post-redo approval)
          - signal_type == 'redo':    Correction signal (-0.5 for the targeted piece: 'pun' | 'clues' | 'postcard')
          - signal_type == 'decline': Negative signal (-1.0 for rejected puzzle candidate)
          - signal_type == 'agent_run': Batch pipeline execution telemetry
        """
        analytics = self.load_analytics()
        now_ts = int(time.time())
        iso_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ts))

        if signal_type == "approve":
            weight = 1.0 if int(redo_count_at_event or 0) == 0 else 0.75
        elif signal_type == "redo":
            weight = -0.5
        elif signal_type == "decline":
            weight = -1.0
        else:
            weight = 0.0

        event = {
            "id": f"sig_{now_ts}_{random.randint(100, 999)}",
            "timestamp": now_ts,
            "iso_time": iso_time,
            "signal_type": signal_type,
            "signal_weight": weight,
            "stage": stage,
            "redo_type": redo_type,
            "clue_id": clue_id or "",
            "postcard_id": postcard_id or "",
            "landmark_name": landmark_name or "",
            "location": location or "",
            "pun_name": pun_name or "",
            "old_value": old_value if old_value is not None else {},
            "new_value": new_value if new_value is not None else {},
            "art_style": art_style or "",
            "page_theme": page_theme or "",
            "agent_score": float(agent_score) if agent_score is not None else None,
            "redo_count_at_event": int(redo_count_at_event or 0),
            "first_pass_approval": bool(signal_type == "approve" and int(redo_count_at_event or 0) == 0),
            "was_runner_up_selected": bool(was_runner_up_selected),
            "human_feedback": (human_feedback or "").strip(),
            "decline_reason": (decline_reason or "").strip()
        }

        analytics["events"].append(event)
        # Keep ledger bounded to last 1,000 granular events
        if len(analytics["events"]) > 1000:
            analytics["events"] = analytics["events"][-1000:]

        self.save_analytics(analytics)
        return event

    def get_adaptive_learning_context(self):
        """
        Synthesize live curator feedback signals (Approved puzzles, Redo corrections,
        and Declined candidates) into dynamic few-shot prompt instructions so the Agent
        continuously self-improves puzzle generation quality.
        """
        analytics = self.load_analytics()
        events = analytics.get("events", [])
        daily_games = self.load_json(self.daily_games_file, [])
        puns = self.load_json(self.puns_file, [])

        approved_signals = [e for e in events if e.get("signal_type") == "approve"]
        redo_signals = [e for e in events if e.get("signal_type") == "redo"]
        decline_signals = [e for e in events if e.get("signal_type") == "decline"]

        # 1. Positive Signals: Recent First-Pass Approved Puzzles
        recent_positive_puns = []
        for e in reversed(approved_signals):
            if e.get("pun_name") and e.get("landmark_name"):
                entry = f"\"{e['pun_name']}\" (from \"{e['landmark_name']}\")"
                if e.get("first_pass_approval"):
                    entry += " [FIRST-PASS CLEAN HIT]"
                if entry not in recent_positive_puns:
                    recent_positive_puns.append(entry)
            if len(recent_positive_puns) >= 8:
                break

        # Fallback to latest scheduled daily games if live ledger has few approvals yet
        if len(recent_positive_puns) < 5:
            for dg in reversed(daily_games[-8:]):
                if dg.get("boss_pun_title") and dg.get("boss_original_title"):
                    entry = f"\"{dg['boss_pun_title']}\" (from \"{dg['boss_original_title']}\")"
                    if entry not in recent_positive_puns:
                        recent_positive_puns.append(entry)

        # 2. Pun Redo & Decline Signals (What wasn't quite right and how it was fixed)
        pun_corrections = []
        for e in reversed(redo_signals):
            if e.get("redo_type") == "pun":
                old_p = (e.get("old_value") or {}).get("pun_name") or e.get("pun_name")
                new_p = (e.get("new_value") or {}).get("pun_name")
                lm = e.get("landmark_name", "Landmark")
                fb = e.get("human_feedback")
                msg = f"For \"{lm}\", human curator REJECTED pun \"{old_p}\" and replaced with \"{new_p}\""
                if fb:
                    msg += f" (Curator feedback: \"{fb}\")"
                pun_corrections.append(msg)
            if len(pun_corrections) >= 6:
                break

        declined_candidates = []
        for e in reversed(decline_signals):
            if e.get("pun_name") or e.get("landmark_name"):
                reason = e.get("decline_reason") or e.get("human_feedback") or "Did not meet puzzle quality bar"
                declined_candidates.append(
                    f"DECLINED \"{e.get('pun_name', 'N/A')}\" for \"{e.get('landmark_name', 'N/A')}\" — Reason: {reason}"
                )
            if len(declined_candidates) >= 6:
                break

        # Also pull recent rejected puns from puns.json if needed
        if len(declined_candidates) < 4:
            for p in reversed(puns):
                if p.get("status") == "rejected" and p.get("pun_name") and p.get("original_name"):
                    item = f"REJECTED PUN \"{p['pun_name']}\" for \"{p['original_name']}\""
                    if item not in declined_candidates:
                        declined_candidates.append(item)
                if len(declined_candidates) >= 6:
                    break

        # 3. Clue Redo Signals (Where clues/owner reply missed the mark)
        clue_corrections = []
        for e in reversed(redo_signals):
            if e.get("redo_type") == "clues":
                pun = e.get("pun_name", "")
                lm = e.get("landmark_name", "")
                fb = e.get("human_feedback")
                old_c1 = (e.get("old_value") or {}).get("clue1", "")
                new_c1 = (e.get("new_value") or {}).get("clue1", "")
                msg = f"For \"{pun}\" ({lm}), curator triggered CLUES RE-DO"
                if fb:
                    msg += f" with feedback: \"{fb}\""
                if old_c1 and new_c1:
                    msg += f" (Replaced \"{old_c1}\" -> \"{new_c1}\")"
                clue_corrections.append(msg)
            if len(clue_corrections) >= 5:
                break

        # 4. Postcard Redo Signals & Art Style Performance
        postcard_corrections = []
        for e in reversed(redo_signals):
            if e.get("redo_type") == "postcard":
                pun = e.get("pun_name", "")
                old_style = (e.get("old_value") or {}).get("art_style", "")
                new_style = (e.get("new_value") or {}).get("art_style") or e.get("art_style", "")
                fb = e.get("human_feedback")
                msg = f"For \"{pun}\", curator triggered POSTCARD RE-DO (style {old_style} -> {new_style})"
                if fb:
                    msg += f" — Prompt note: \"{fb}\""
                postcard_corrections.append(msg)
            if len(postcard_corrections) >= 5:
                break

        return {
            "recent_positive_puns": recent_positive_puns,
            "pun_corrections": pun_corrections,
            "declined_candidates": declined_candidates,
            "clue_corrections": clue_corrections,
            "postcard_corrections": postcard_corrections
        }

    def select_weighted_art_style(self):
        """
        Select an art style using empirical approval vs. redo/decline performance
        so art styles that get approved without redos are favored automatically.
        """
        analytics = self.load_analytics()
        events = analytics.get("events", [])
        postcards = self.load_json(self.postcards_file, [])

        style_stats = {k: {"approved": 0, "redo": 0, "decline": 0} for k in ART_STYLES.keys()}

        for pc in postcards:
            st = pc.get("art_style")
            if st in style_stats:
                if pc.get("status") == "approved":
                    style_stats[st]["approved"] += 1
                elif pc.get("status") == "rejected":
                    style_stats[st]["decline"] += 1

        for e in events:
            st = e.get("art_style") or (e.get("old_value") or {}).get("art_style")
            if st in style_stats:
                if e.get("signal_type") == "approve":
                    style_stats[st]["approved"] += 2
                elif e.get("signal_type") == "redo" and e.get("redo_type") == "postcard":
                    style_stats[st]["redo"] += 2
                elif e.get("signal_type") == "decline":
                    style_stats[st]["decline"] += 1

        styles = list(ART_STYLES.keys())
        weights = []
        for st in styles:
            s = style_stats[st]
            # Laplace-smoothed win weight
            w = (s["approved"] + 3.0) / (s["approved"] + s["redo"] * 1.5 + s["decline"] + 5.0)
            weights.append(max(0.15, w))

        return random.choices(styles, weights=weights, k=1)[0]

    def get_quality_analytics(self):
        """
        Compute comprehensive quality metrics, signal rates, element redo breakdowns,
        art style win-rates, and active adaptive guardrails for the Curation Hub.
        """
        analytics = self.load_analytics()
        events = analytics.get("events", [])

        landmarks = self.load_json(self.landmarks_file, [])
        puns = self.load_json(self.puns_file, [])
        clues = self.load_json(self.clues_file, [])
        postcards = self.load_json(self.postcards_file, [])
        daily_games = self.load_json(self.daily_games_file, [])

        # Historical dataset counts
        hist_approved_puzzles = len(daily_games)
        hist_approved_puns = sum(1 for p in puns if p.get("status") == "approved")
        hist_rejected_puns = sum(1 for p in puns if p.get("status") == "rejected")
        hist_rejected_postcards = sum(1 for pc in postcards if pc.get("status") == "rejected")
        pending_agent_queue = sum(1 for pc in postcards if pc.get("status") == "pending")

        # Live signal counts from analytics ledger
        approve_events = [e for e in events if e.get("signal_type") == "approve"]
        redo_events = [e for e in events if e.get("signal_type") == "redo"]
        decline_events = [e for e in events if e.get("signal_type") == "decline"]

        live_approvals = len(approve_events)
        first_pass_approvals = sum(1 for e in approve_events if e.get("first_pass_approval", True))
        post_redo_approvals = live_approvals - first_pass_approvals

        pun_redos = sum(1 for e in redo_events if e.get("redo_type") == "pun")
        clues_redos = sum(1 for e in redo_events if e.get("redo_type") == "clues")
        postcard_redos = sum(1 for e in redo_events if e.get("redo_type") == "postcard")
        total_redos = len(redo_events)
        runner_up_rescues = sum(1 for e in redo_events if e.get("was_runner_up_selected"))

        live_declines = len(decline_events)

        # Combined puzzle-level decision totals (Historical + Live)
        total_positive_puzzles = hist_approved_puzzles + live_approvals
        total_negative_puzzles = hist_rejected_postcards + live_declines
        total_decided_puzzles = max(1, total_positive_puzzles + total_negative_puzzles)

        puzzle_approval_rate_pct = round((total_positive_puzzles / total_decided_puzzles) * 100, 1)

        # Live Agent Session First-Pass Clean Rate & Element Accuracy
        # Evaluate across all agent-curated candidates (decided + currently in queue)
        agent_candidates_total = max(1, live_approvals + live_declines + pending_agent_queue)
        if (live_approvals + live_declines) > 0:
            first_pass_clean_rate_pct = round((first_pass_approvals / (live_approvals + live_declines)) * 100, 1)
        else:
            # Before first live click, estimate from candidates with 0 redos
            zero_redo_pending = sum(1 for pc in postcards if pc.get("status") == "pending" and int(pc.get("redo_count", 0)) == 0)
            first_pass_clean_rate_pct = round((zero_redo_pending / max(1, pending_agent_queue)) * 100, 1) if pending_agent_queue else 100.0

        pun_accuracy_pct = round(max(0.0, 100.0 - (pun_redos / max(1, agent_candidates_total + pun_redos)) * 100.0), 1)
        clues_accuracy_pct = round(max(0.0, 100.0 - (clues_redos / max(1, agent_candidates_total + clues_redos)) * 100.0), 1)
        postcard_accuracy_pct = round(max(0.0, 100.0 - (postcard_redos / max(1, agent_candidates_total + postcard_redos)) * 100.0), 1)

        # Composite Quality Health Score (0 - 100)
        # Rewards high approval & first-pass clean rate, penalizes declines & heavy redos
        redo_penalty = min(25.0, (total_redos / max(1, agent_candidates_total)) * 12.0)
        decline_penalty = min(30.0, (live_declines / max(1, live_approvals + live_declines + 2)) * 35.0)
        health_score = round(max(10.0, min(100.0, 94.0 - redo_penalty - decline_penalty + min(6.0, live_approvals * 1.5))), 1)

        if health_score >= 85:
            health_status = "EXCELLENT"
        elif health_score >= 70:
            health_status = "HEALTHY"
        else:
            health_status = "NEEDS TUNING"

        # Art style leaderboard
        style_board = []
        for st_key in ART_STYLES.keys():
            st_pcs = [pc for pc in postcards if pc.get("art_style") == st_key]
            st_app = sum(1 for pc in st_pcs if pc.get("status") == "approved") + sum(
                1 for e in approve_events if e.get("art_style") == st_key
            )
            st_redo = sum(
                1 for e in redo_events
                if e.get("redo_type") == "postcard" and ((e.get("old_value") or {}).get("art_style") == st_key or e.get("art_style") == st_key)
            )
            st_dec = sum(1 for pc in st_pcs if pc.get("status") == "rejected") + sum(
                1 for e in decline_events if e.get("art_style") == st_key
            )
            st_total = len(st_pcs) + st_redo
            win_rate = round(((st_app + 2) / (st_app + st_redo + st_dec + 4)) * 100, 1)
            style_board.append({
                "art_style": st_key,
                "total_generated": st_total,
                "approved": st_app,
                "redone": st_redo,
                "declined": st_dec,
                "win_rate_pct": win_rate
            })
        style_board.sort(key=lambda x: x["win_rate_pct"], reverse=True)

        # Decline reason breakdown
        decline_reasons = {}
        for e in decline_events:
            r = e.get("decline_reason") or e.get("human_feedback") or "Unspecified Decline"
            decline_reasons[r] = decline_reasons.get(r, 0) + 1

        adaptive_ctx = self.get_adaptive_learning_context()

        return {
            "health_score": health_score,
            "health_status": health_status,
            "signals_summary": {
                "positive_approvals_total": total_positive_puzzles,
                "historical_scheduled_puzzles": hist_approved_puzzles,
                "live_session_approvals": live_approvals,
                "first_pass_approvals": first_pass_approvals,
                "post_redo_approvals": post_redo_approvals,
                "total_redos": total_redos,
                "pun_redos": pun_redos,
                "clues_redos": clues_redos,
                "postcard_redos": postcard_redos,
                "runner_up_rescues": runner_up_rescues,
                "negative_declines_total": total_negative_puzzles,
                "live_session_declines": live_declines,
                "historical_rejected_puns": hist_rejected_puns,
                "historical_approved_puns": hist_approved_puns,
                "pending_queue_count": pending_agent_queue,
                "total_landmarks_seeded": len(landmarks)
            },
            "rates": {
                "puzzle_approval_rate_pct": puzzle_approval_rate_pct,
                "first_pass_clean_rate_pct": first_pass_clean_rate_pct,
                "pun_accuracy_pct": pun_accuracy_pct,
                "clues_accuracy_pct": clues_accuracy_pct,
                "postcard_accuracy_pct": postcard_accuracy_pct,
                "avg_redos_per_candidate": round(total_redos / max(1, agent_candidates_total), 2)
            },
            "art_style_leaderboard": style_board,
            "decline_reasons": decline_reasons,
            "adaptive_learning_active": adaptive_ctx,
            "recent_signals": list(reversed(events[-25:]))
        }

    # ==========================================================================
    # STEP 1: GLOBAL LANDMARK SEED DISCOVERY
    # ==========================================================================
    def discover_landmarks(self, count=8, auto_approve=False):
        """
        Generate `count` new globally famous landmarks that are not yet in the seed database
        or daily games schedule, adhering strictly to landmark guardrails.
        """
        from google.genai import types
        client = self._get_client()

        landmarks = self.load_json(self.landmarks_file, [])
        daily_games = self.load_json(self.daily_games_file, [])

        existing_norms = set()
        existing_names_sample = []
        for lm in landmarks:
            norm = normalize_name(lm.get("name", ""))
            if norm:
                existing_norms.add(norm)
                existing_names_sample.append(lm.get("name", ""))
        for pz in daily_games:
            norm = normalize_name(pz.get("boss_original_title", ""))
            if norm:
                existing_norms.add(norm)

        # Deduplicate sample list for prompt context
        unique_existing = list(dict.fromkeys(existing_names_sample))

        prompt = f"""
You are the Lead Curation Agent for "1-Star Travel Reviews", a daily wordplay puzzle game about world-famous travel landmarks.

Your task is to discover {count + 4} NEW, globally famous landmarks or natural wonders for our Landmark Seed Database that are NOT already in our database.

EXISTING LANDMARKS TO EXCLUDE (Do NOT suggest any of these or close variants):
{json.dumps(unique_existing[:350])}

LANDMARK QUALITY GUARDRAILS:
1. Must be a household-name global landmark, UNESCO World Heritage treasure, famous natural wonder, iconic bridge/tower/palace/cathedral/square, or renowned tourist attraction.
2. Global diversity: Include famous sites across Europe, Asia, North & South America, Africa, Middle East, and Oceania.
3. Phonetic Pun Potential: Pick landmarks whose names contain words or syllables that can easily be swapped with concrete, funny everyday nouns (food, animals, household objects, clothing).
4. STRICT EXCLUSION: Never include somber memorials, war graves, concentration camps, or sites of human tragedy.

Return a JSON array of objects matching this exact schema:
[
  {{
    "name": "Famous Landmark Name",
    "location": "City/Region, Country",
    "page_theme": "One of: ancient_ruins, natural_wonders, historic_monuments, castles_cathedrals, bridges_canals, streets_squares, modern_skyscrapers",
    "pun_potential_note": "Brief example of why this landmark has great phonetic pun potential"
  }}
]
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        candidates = json.loads(response.text)
        if not isinstance(candidates, list):
            candidates = []

        added = []
        landmarks = self.load_json(self.landmarks_file, [])
        for cand in candidates:
            if len(added) >= count:
                break
            name = (cand.get("name") or "").strip()
            location = (cand.get("location") or "Unknown").strip()
            theme = cand.get("page_theme", "historic_monuments")
            if theme not in VALID_THEMES:
                theme = self.get_theme(name)

            norm = normalize_name(name)
            if not norm or norm in existing_norms:
                continue

            existing_norms.add(norm)
            new_lm = {
                "id": f"landmark_{int(time.time())}_{random.randint(100, 999)}_{len(added)}",
                "name": name,
                "location": location,
                "page_theme": theme,
                "pun_potential_note": cand.get("pun_potential_note", ""),
                "status": "approved" if auto_approve else "pending",
                "agent_generated": True
            }
            landmarks.append(new_lm)
            added.append(new_lm)

        if added:
            self.save_json(self.landmarks_file, landmarks)

        return added

    # ==========================================================================
    # STEP 2: GUARDRAIL-SCORED PUN GENERATION & SELECTION
    # ==========================================================================
    def generate_and_select_pun(self, landmark_name, location="Unknown", excluded_puns=None, human_feedback=None):
        """
        Generate pun candidates for `landmark_name`, score them against our deep-data
        guardrails, and return the best pun along with runner-up options and rationale.
        """
        from google.genai import types
        client = self._get_client()

        puns = self.load_json(self.puns_file, [])
        clues = self.load_json(self.clues_file, [])
        daily_games = self.load_json(self.daily_games_file, [])

        # Gather all existing pun names for this landmark and globally used pun words
        already_used_for_landmark = set()
        if excluded_puns:
            for ep in excluded_puns:
                already_used_for_landmark.add(ep.strip())

        for p in puns:
            if normalize_name(p.get("original_name")) == normalize_name(landmark_name):
                if p.get("status") in ("approved", "rejected"):
                    already_used_for_landmark.add(p.get("pun_name", ""))
        for c in clues:
            if normalize_name(c.get("original_name")) == normalize_name(landmark_name):
                already_used_for_landmark.add(c.get("pun_name", ""))
        for dg in daily_games:
            if normalize_name(dg.get("boss_original_title")) == normalize_name(landmark_name):
                already_used_for_landmark.add(dg.get("boss_pun_title", ""))

        # Also collect overused pun words across the entire schedule so we stay fresh
        all_scheduled_puns = [dg.get("boss_pun_title", "") for dg in daily_games]

        feedback_section = ""
        if human_feedback:
            feedback_section = f"\nCRITICAL HUMAN CURATOR DIRECTION / FEEDBACK:\n\"{human_feedback}\"\nFollow this direction closely!\n"

        adaptive_ctx = self.get_adaptive_learning_context()
        adaptive_pun_section = ""
        if adaptive_ctx["recent_positive_puns"] or adaptive_ctx["pun_corrections"] or adaptive_ctx["declined_candidates"]:
            pos_str = "\n  * ".join(adaptive_ctx["recent_positive_puns"][:6]) if adaptive_ctx["recent_positive_puns"] else "None yet"
            corr_str = "\n  * ".join(adaptive_ctx["pun_corrections"][:5]) if adaptive_ctx["pun_corrections"] else "None yet"
            dec_str = "\n  * ".join(adaptive_ctx["declined_candidates"][:5]) if adaptive_ctx["declined_candidates"] else "None yet"
            adaptive_pun_section = f"""
=== LIVE ANALYTICS FEEDBACK LOOP (RECENT HUMAN CURATOR SIGNALS) ===
Recent Positive Approvals (Match this comedy caliber):
  * {pos_str}
Recent Human Pun Redo Corrections (Avoid the rejected style, emulate the replacement):
  * {corr_str}
Recent Declined Puns (Strictly avoid these failure modes):
  * {dec_str}
"""

        prompt = f"""
You are the Expert Comedy & Wordplay Architect for "1-Star Travel Reviews".
Your task is to craft and evaluate pun candidates for the famous landmark:
  Landmark: "{landmark_name}"
  Location: "{location}"
{feedback_section}{adaptive_pun_section}
ALREADY USED OR REJECTED PUNS FOR THIS LANDMARK (DO NOT USE ANY OF THESE):
{json.dumps(list(already_used_for_landmark))}

EXISTING SCHEDULED PUNS (Avoid repeating the exact same joke word if already heavily used):
{json.dumps(all_scheduled_puns[-60:])}

=== STRICT QUALITY GUARDRAILS (LEARNED FROM 122 HUMAN-APPROVED PUZZLES) ===
1. CONCRETE TANGIBLE NOUN SUBSTITUTION (MANDATORY):
   The pun MUST replace a word or syllable of "{landmark_name}" with a concrete, physical, everyday noun that is hilarious to visualize on a postcard and absurd for a confused tourist to complain about:
   - Food/Drink (e.g., "Waffle Tower" for Eiffel Tower, "Sconehenge" for Stonehenge, "Sangria Família" for Sagrada Família, "Chicken Pizza" for Chichen Itza, "Burger Khalifa" for Burj Khalifa, "Space Noodle" for Space Needle, "San Tortellini" for Santorini, "Matcha Picchu" for Machu Picchu, "Blarney Casserole" for Blarney Castle).
   - Household Objects/Clothing (e.g., "Golden Gate Fridge" for Golden Gate Bridge, "Loofah Museum" for Louvre Museum, "Pajama Canal" for Panama Canal, "Alca-trousers Island" for Alcatraz Island, "Towel of London" for Tower of London, "Pillowstone National Park" for Yellowstone National Park, "Spandex Steps" for Spanish Steps).
   - Funny Animals/Characters (e.g., "Great Whale of China", "Pyramids of Geezer", "Otter-Dame Cathedral", "Brandenburg Goat", "Gator-way Arch", "Victoria's Fowls").

2. HARD BAN ON ABSTRACT ADJECTIVES & WEAK SUBSTITUTIONS (Human Rejected Examples):
   - NEVER use abstract concepts like "Lover Museum" (Rejected! "Loofah Museum" was approved).
   - NEVER use abstract adjectives like "Mount Cleverest" or "Mount Fuzzy" (Rejected! "Mound Fudgey" was approved).
   - NEVER use dry academic words like "Sagrada Formula" (Rejected! "Sangria Família" was approved).
   - NEVER use mundane/similar objects like "Golden Grate Bridge" (Rejected! "Golden Gate Fridge" was approved).
   - NEVER mutate every single word into an unrecognizable tongue-twister (e.g., "A Cappella-Polis of Athens" was rejected). Keep ONE clear, punchy phonetic substitution so players can deduce the answer!

Generate 4 distinct, high-potential pun candidates for "{landmark_name}", score each one from 1.0 to 10.0 against the guardrails above, and select the #1 best candidate.

Return a JSON object matching this exact schema:
{{
  "selected_pun": "The single best Pun Name",
  "agent_score": 9.4,
  "agent_rationale": "1-2 sentences explaining the phonetic match, concrete tangible noun used, and why it makes a hilarious postcard and 1-star review.",
  "candidates": [
    {{
      "pun_name": "Candidate 1",
      "score": 9.4,
      "tangible_noun": "The concrete object/food/animal introduced",
      "rationale": "Why it works"
    }}
  ]
}}
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        result = json.loads(response.text)
        selected_pun = (result.get("selected_pun") or "").strip()
        candidates = result.get("candidates") or []
        if not selected_pun and candidates:
            selected_pun = candidates[0].get("pun_name", "").strip()

        runner_ups = [
            c.get("pun_name").strip()
            for c in candidates
            if c.get("pun_name") and c.get("pun_name").strip().lower() != selected_pun.lower()
        ]

        return {
            "pun_name": selected_pun,
            "agent_score": float(result.get("agent_score", 9.0)),
            "agent_rationale": result.get("agent_rationale", "Strong phonetic match with concrete visual noun."),
            "runner_up_puns": runner_ups[:3],
            "all_candidates": candidates
        }

    # ==========================================================================
    # STEP 3: PROGRESSIVE CLUES, REVIEWER HANDLE & OWNER REPLY GENERATOR
    # ==========================================================================
    def generate_clues_and_reply(
        self,
        landmark_name,
        location,
        pun_name,
        previous_clues=None,
        human_feedback=None
    ):
        """
        Generate 3 progressive 1-star review clues, a thematic reviewer username,
        a review title, and a sarcastic Owner Reply adhering to all guardrails.
        """
        from google.genai import types
        client = self._get_client()

        prev_section = ""
        if previous_clues:
            prev_section = f"""
PREVIOUS CLUES / OWNER REPLY TO IMPROVE UPON (Write a fresh, funnier, sharper take — do NOT repeat these lines):
  Previous Title: {previous_clues.get('review_title', '')}
  Previous Clue 1: {previous_clues.get('clue1', '')}
  Previous Clue 2: {previous_clues.get('clue2', '')}
  Previous Clue 3: {previous_clues.get('clue3', '')}
  Previous Owner Reply: {previous_clues.get('owner_response', '')}
"""
        feedback_section = ""
        if human_feedback:
            feedback_section = f"\nCRITICAL HUMAN CURATOR FEEDBACK FOR CLUES:\n\"{human_feedback}\"\n"

        adaptive_ctx = self.get_adaptive_learning_context()
        adaptive_clue_section = ""
        if adaptive_ctx["clue_corrections"]:
            c_corr = "\n  * ".join(adaptive_ctx["clue_corrections"][:5])
            adaptive_clue_section = f"\nLIVE ANALYTICS CLUE CORRECTIONS (Learn from recent human clue redos):\n  * {c_corr}\n"

        prompt = f"""
You are the Head Comedy Writer for "1-Star Travel Reviews".
A clueless tourist visited the world-famous landmark "{landmark_name}" (located in {location}),
but because they misread the brochure, they genuinely believed they were visiting the literal pun:
  TARGET PUN NAME: "{pun_name}"
  ACTUAL LANDMARK: "{landmark_name}" ({location})
{prev_section}{feedback_section}{adaptive_clue_section}
=== STRICT GUARDRAILS (LEARNED FROM 122 APPROVED DAILY CHALLENGES) ===
1. PROGRESSIVE 3-CLUE FUNNEL & ULTRA-PUNCHY LENGTH:
   - Each clue (`clue1`, `clue2`, `clue3`) MUST be a short, hilarious 1-star review snippet or sentence fragment: **strictly 6 to 14 words per clue**.
   - Use `...` or `!` for punchy comedic delivery (e.g., "Flew to Paris for breakfast... not a drop of maple syrup on these iron girders!").
   - **Clue 1 (Setting + Delusion)**: Hints at the real geographic/cultural location ({location}) while introducing the reviewer's absurd literal expectation of the pun object—giving clever players a fair shot on Clue 1.
   - **Clue 2 (Architecture/Nature + Mishap)**: Connects a signature physical feature of "{landmark_name}" (its material, shape, history, or surroundings) with the tourist's failed attempt to eat, wear, or use the literal pun object.
   - **Clue 3 (The Convergence)**: Makes both the real landmark and the pun wordplay unmistakable and laugh-out-loud funny.
   - **NO DIRECT SPOILERS**: Do NOT state the full exact name "{landmark_name}" or the full exact pun name "{pun_name}" in the clues.

2. THEMATIC REVIEWER USERNAME (`reviewer_name`):
   - A clever, alliterative or punny username matching the complaint (e.g., `SyrupSlinger`, `FrostyFogger`, `ScrubbieDoo`, `SoggyBatter`).
   - Do NOT include `@` in the `reviewer_name` field.

3. SARCASTIC OWNER REPLY (`owner_response`):
   - Written from the POV of the management of the ACTUAL landmark ("{landmark_name}").
   - 1 to 2 punchy sentences maximum.
   - Directly address `@<reviewer_name>` (or `Dear @<reviewer_name>,` / `Listen, @<reviewer_name>,`).
   - Sarcastically correct the reviewer's absurd complaint by contrasting their literal pun delusion with what your landmark actually is (e.g., "10,000 tons of 19th-century wrought iron", "a 4,500-year-old limestone pharaoh's tomb", "a 2,000-year-old Roman amphitheater").
   - CRITICAL SPOILER BAN: In the game, the Owner Reply is shown as a hint BEFORE the player solves the puzzle! Therefore, NEVER mention the exact words of the landmark's proper name ("{landmark_name}") or the pun name ("{pun_name}") inside `owner_response`!

Return a JSON object matching this exact schema:
{{
  "reviewer_name": "CleverHandle",
  "review_title": "Short punchy 1-star review headline!",
  "clue1": "Short 6-14 word snippet hinting at location + pun...",
  "clue2": "Short 6-14 word snippet combining landmark feature + pun mishap...",
  "clue3": "Short 6-14 word snippet making the landmark + pun intersection obvious!",
  "owner_response": "Sarcastic 1-2 sentence reply from actual management addressing @CleverHandle without naming the landmark.",
  "page_theme": "One of: ancient_ruins, natural_wonders, historic_monuments, castles_cathedrals, bridges_canals, streets_squares, modern_skyscrapers"
}}
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        generated = json.loads(response.text)

        reviewer_name = (generated.get("reviewer_name") or "ConfusedTourist").lstrip("@").strip()
        review_title = (generated.get("review_title") or "1 Star! Total false advertising!").strip()
        clue1 = (generated.get("clue1") or "").strip()
        clue2 = (generated.get("clue2") or "").strip()
        clue3 = (generated.get("clue3") or "").strip()
        owner_response = (generated.get("owner_response") or "").strip()

        # Guardrail Self-Check: Ensure owner_response doesn't accidentally contain the full original_name
        if landmark_name and len(landmark_name) > 3:
            pattern = re.compile(re.escape(landmark_name), re.IGNORECASE)
            if pattern.search(owner_response):
                owner_response = pattern.sub("our historic site", owner_response)

        theme = generated.get("page_theme")
        if theme not in VALID_THEMES:
            theme = self.get_theme(landmark_name)

        return {
            "reviewer_name": reviewer_name,
            "review_title": review_title,
            "clue1": clue1,
            "clue2": clue2,
            "clue3": clue3,
            "owner_response": owner_response,
            "page_theme": theme
        }

    # ==========================================================================
    # STEP 4: PARODIED POSTCARD PROMPT & IMAGE GENERATION
    # ==========================================================================
    def generate_postcard_for_clue(self, clue_obj, art_style="random", custom_prompt=None):
        """
        Generate a vivid parodied postcard prompt and render the .webp image
        using `gemini-3.1-flash-image` for a given `clue_obj`.
        """
        from google.genai import types
        client = self._get_client()

        # Clean any legacy "no text or lettering" phrase if present in custom_prompt
        if custom_prompt and custom_prompt.strip():
            cleaned_custom = re.sub(
                r",?\s*(with\s+|utterly\s+)?(no|free of any)\s+text(\s+or\s+lettering)?\.?",
                "",
                custom_prompt.strip(),
                flags=re.IGNORECASE
            ).strip()
        else:
            cleaned_custom = ""

        if cleaned_custom:
            image_prompt = cleaned_custom
            style_key = art_style if art_style in ART_STYLES else self.select_weighted_art_style()
            style_prompt = ART_STYLES.get(style_key, "")
        else:
            if not art_style or art_style == "random" or art_style not in ART_STYLES:
                style_key = self.select_weighted_art_style()
            else:
                style_key = art_style
            style_prompt = ART_STYLES[style_key]

            adaptive_ctx = self.get_adaptive_learning_context()
            pc_corr_section = ""
            if adaptive_ctx["postcard_corrections"]:
                pc_corr_str = "\n  * ".join(adaptive_ctx["postcard_corrections"][:4])
                pc_corr_section = f"\nRECENT POSTCARD RE-DO LESSONS FROM CURATOR:\n  * {pc_corr_str}\n"

            prompt_gen = f"""
You are an Art Director for "1-Star Travel Reviews" postcards.
Create a single-sentence descriptive text-to-image prompt for a parodied travel postcard based on the location pun "{clue_obj['pun_name']}" (derived from "{clue_obj['original_name']}" in {clue_obj.get('location', '')}).
The prompt should describe a funny, comical visual mashup scene matching this art style: "{style_prompt}", and feature classic travel postcard / vintage travel poster title typography displaying "{clue_obj['pun_name']}" (or "Greetings from {clue_obj['pun_name']}").
{pc_corr_section}
Examples:
- "A comical travel postcard featuring the 'Waffle Tower,' a towering structure built from golden-brown waffles with syrup cascading down and butter pats on top in a whimsical Parisian landscape, with vintage postcard lettering reading 'WAFFLE TOWER', rendered in {style_prompt}"
- "A whimsical travel poster depicting three enormous, grumpy old men with long white beards posing majestically as the 'Pyramids of Geezer' in a vast desert, with bold hand-drawn travel poster typography reading 'PYRAMIDS OF GEEZER', rendered in {style_prompt}"

Return a JSON object matching this exact schema:
{{
  "image_prompt": "A single vivid sentence describing the visual mashup scene and its vintage travel postcard title typography for '{clue_obj['pun_name']}'."
}}
"""
            prompt_res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_gen,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            prompt_data = json.loads(prompt_res.text)
            image_prompt = prompt_data.get(
                "image_prompt",
                f"A humorous travel postcard of '{clue_obj['pun_name']}' at {clue_obj['original_name']}, featuring bold vintage travel postcard title lettering reading '{clue_obj['pun_name']}', {style_prompt}"
            )

        safe_slug = re.sub(r"[^a-z0-9_]", "", clue_obj["pun_name"].lower().replace(" ", "_").replace("-", "_"))
        if not safe_slug:
            safe_slug = "postcard"
        safe_filename = f"{safe_slug}_{int(time.time())}_{random.randint(10, 99)}.webp"
        image_path = f"/assets/cartoons/{safe_filename}"
        local_image_path = os.path.join(self.cartoons_dir, safe_filename)

        print(f"[CurationAgent] Generating postcard for '{clue_obj['pun_name']}' in style '{style_key}'...")
        full_render_prompt = (
            f"{style_prompt} {image_prompt} "
            f"Include bold, legible vintage travel postcard title typography reading \"{clue_obj['pun_name']}\"."
        ).strip()
        response = client.models.generate_content(
            model="gemini-3.1-flash-image",
            contents=full_render_prompt,
            config=types.GenerateContentConfig(
                response_modalities=[types.Modality.IMAGE],
            )
        )

        saved_image = False
        for candidate in (response.candidates or []):
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if part.inline_data:
                        image_bytes = part.inline_data.data
                        from PIL import Image
                        image = Image.open(io.BytesIO(image_bytes))
                        image.save(local_image_path, "WEBP", quality=95)
                        print(f"[CurationAgent] Saved generated postcard: {local_image_path}")

                        # Mirror to Box Office repository if separate
                        if self.boxoffice_root and self.travelreviews_root and self.boxoffice_root != self.travelreviews_root:
                            if os.path.exists(os.path.join(self.boxoffice_root, "travelreviews")):
                                bo_cartoons_dir = os.path.join(self.boxoffice_root, "travelreviews", "assets", "cartoons")
                            else:
                                bo_cartoons_dir = os.path.join(self.boxoffice_root, "assets", "cartoons")
                            os.makedirs(bo_cartoons_dir, exist_ok=True)
                            bo_image_path = os.path.join(bo_cartoons_dir, safe_filename)
                            try:
                                image.save(bo_image_path, "WEBP", quality=95)
                            except Exception as bo_e:
                                print(f"[CurationAgent] Mirror image save warning: {bo_e}")

                        saved_image = True
                        break
                if saved_image:
                    break

        if not saved_image:
            raise RuntimeError("No image returned from gemini-3.1-flash-image")

        postcards = self.load_json(self.postcards_file, [])
        existing_idx = next((i for i, p in enumerate(postcards) if p.get("clue_id") == clue_obj["id"]), None)

        # Delete old image file if replacing an existing postcard
        if existing_idx is not None:
            old_img = postcards[existing_idx].get("image_path")
            if old_img and old_img != image_path:
                self._delete_image_file(old_img)

        preserved_status = "pending"
        if existing_idx is not None:
            preserved_status = postcards[existing_idx].get("status", "pending")

        postcard_entry = {
            "id": f"postcard_{clue_obj['id']}_{int(time.time())}" if existing_idx is None else postcards[existing_idx]["id"],
            "clue_id": clue_obj["id"],
            "pun_id": clue_obj.get("pun_id", ""),
            "pun_name": clue_obj["pun_name"],
            "original_name": clue_obj["original_name"],
            "location": clue_obj.get("location", "Unknown"),
            "image_prompt": image_prompt,
            "image_path": image_path,
            "art_style": style_key,
            "owner_response": clue_obj.get("owner_response", ""),
            "page_theme": clue_obj.get("page_theme", self.get_theme(clue_obj["original_name"])),
            "status": preserved_status,
            "agent_curated": True,
            "agent_score": clue_obj.get("agent_score", 9.0),
            "agent_rationale": clue_obj.get("agent_rationale", ""),
            "runner_up_puns": clue_obj.get("runner_up_puns", []),
            "redo_count": clue_obj.get("redo_count", 0),
            "redo_history": clue_obj.get("redo_history", [])
        }

        if existing_idx is not None:
            postcards[existing_idx] = postcard_entry
        else:
            postcards.append(postcard_entry)

        self.save_json(self.postcards_file, postcards)

        # Also sync boss_poster_url in daily_games if this puzzle is already scheduled
        daily_games = self.load_json(self.daily_games_file, [])
        dg_updated = False
        for dg in daily_games:
            if dg.get("puzzle_id") == clue_obj["id"]:
                dg["boss_poster_url"] = image_path
                dg_updated = True
        if dg_updated:
            self.save_json(self.daily_games_file, daily_games)

        return postcard_entry

    # ==========================================================================
    # END-TO-END AUTONOMOUS PIPELINE (Landmarks -> Puns -> Clues -> Postcards)
    # ==========================================================================
    def build_single_puzzle_for_landmark(self, landmark_obj, art_style="random", custom_pun=None):
        """
        Run the complete agent pipeline for one landmark:
          Landmark -> Pun Candidate Selection -> Clues & Owner Reply -> Postcard Image.
        Returns the assembled candidate bundle ready for Human Approval/Decline/Re-do.
        """
        lm_name = landmark_obj["name"]
        lm_loc = landmark_obj.get("location", "Unknown")

        # Mark landmark approved in landmarks.json
        landmarks = self.load_json(self.landmarks_file, [])
        for lm in landmarks:
            if lm.get("id") == landmark_obj.get("id") or normalize_name(lm.get("name")) == normalize_name(lm_name):
                lm["status"] = "approved"
        self.save_json(self.landmarks_file, landmarks)

        # 1. Generate & Select Best Guardrail-Verified Pun (or reuse an existing in-progress agent pun)
        puns = self.load_json(self.puns_file, [])
        clues = self.load_json(self.clues_file, [])
        postcards = self.load_json(self.postcards_file, [])
        existing_pc_pun_ids = {pc.get("pun_id") for pc in postcards}

        reused_pun_entry = None
        if not (custom_pun and custom_pun.strip()):
            reused_pun_entry = next(
                (p for p in reversed(puns)
                 if normalize_name(p.get("original_name")) == normalize_name(lm_name)
                 and p.get("status") == "approved"
                 and p.get("agent_curated")
                 and p.get("id") not in existing_pc_pun_ids),
                None
            )

        if reused_pun_entry:
            pun_entry = reused_pun_entry
            pun_id = pun_entry["id"]
            pun_name = pun_entry["pun_name"]
            pun_result = {
                "pun_name": pun_name,
                "agent_score": pun_entry.get("agent_score", 9.2),
                "agent_rationale": pun_entry.get("agent_rationale", ""),
                "runner_up_puns": pun_entry.get("runner_up_puns", [])
            }
        else:
            if custom_pun and custom_pun.strip():
                pun_result = {
                    "pun_name": custom_pun.strip(),
                    "agent_score": 9.5,
                    "agent_rationale": "Custom pun word specified by human curator.",
                    "runner_up_puns": []
                }
            else:
                pun_result = self.generate_and_select_pun(lm_name, lm_loc)

            pun_name = pun_result["pun_name"]
            pun_id = f"pun_{re.sub(r'[^a-z0-9_]', '', lm_name.lower().replace(' ', '_'))}_{int(time.time())}_{random.randint(100, 999)}"

            pun_entry = {
                "id": pun_id,
                "original_name": lm_name,
                "location": lm_loc,
                "pun_name": pun_name,
                "status": "approved",
                "agent_curated": True,
                "agent_score": pun_result["agent_score"],
                "agent_rationale": pun_result["agent_rationale"],
                "runner_up_puns": pun_result["runner_up_puns"]
            }
            puns.append(pun_entry)
            self.save_json(self.puns_file, puns)

        # 2. Generate Progressive Clues, Reviewer Handle & Sarcastic Owner Reply (or reuse existing clue for pun_id)
        clues = self.load_json(self.clues_file, [])
        existing_clue = next((c for c in clues if c.get("pun_id") == pun_id), None)
        if existing_clue:
            existing_clue["status"] = "approved"
            existing_clue["agent_curated"] = True
            existing_clue["agent_score"] = pun_result["agent_score"]
            existing_clue["agent_rationale"] = pun_result["agent_rationale"]
            existing_clue["runner_up_puns"] = pun_result["runner_up_puns"]
            clue_entry = existing_clue
            self.save_json(self.clues_file, clues)
        else:
            clue_data = self.generate_clues_and_reply(lm_name, lm_loc, pun_name)
            clue_id = f"clue_{re.sub(r'[^a-z0-9_]', '', pun_name.lower().replace(' ', '_'))}_{int(time.time())}_{random.randint(100, 999)}"

            clue_entry = {
                "id": clue_id,
                "pun_id": pun_id,
                "original_name": lm_name,
                "location": lm_loc,
                "pun_name": pun_name,
                "reviewer_name": clue_data["reviewer_name"],
                "review_title": clue_data["review_title"],
                "clue1": clue_data["clue1"],
                "clue2": clue_data["clue2"],
                "clue3": clue_data["clue3"],
                "owner_response": clue_data["owner_response"],
                "page_theme": landmark_obj.get("page_theme") if landmark_obj.get("page_theme") in VALID_THEMES else clue_data["page_theme"],
                "status": "approved",
                "agent_curated": True,
                "agent_score": pun_result["agent_score"],
                "agent_rationale": pun_result["agent_rationale"],
                "runner_up_puns": pun_result["runner_up_puns"]
            }
            clues.append(clue_entry)
            self.save_json(self.clues_file, clues)

        # 3. Generate Postcard Illustration
        postcard_entry = self.generate_postcard_for_clue(clue_entry, art_style=art_style)

        return {
            "landmark": landmark_obj,
            "pun": pun_entry,
            "clue": clue_entry,
            "postcard": postcard_entry
        }

    def run_pipeline(self, count=3, discover_new_landmarks=True, art_style="random", landmark_id=None):
        """
        Autonomous Agent Pipeline:
        - If `landmark_id` is provided, runs the full pipeline for that specific landmark.
        - Otherwise, optionally discovers new global landmarks, or picks fresh unused landmarks,
          and takes `count` puzzles all the way through Landmarks -> Puns -> Clues -> Postcards.
        """
        landmarks = self.load_json(self.landmarks_file, [])
        postcards = self.load_json(self.postcards_file, [])
        daily_games = self.load_json(self.daily_games_file, [])

        # Identify landmarks that already have an active pending postcard or scheduled daily game
        active_landmark_norms = set()
        for pc in postcards:
            if pc.get("status") in ("pending", "approved"):
                active_landmark_norms.add(normalize_name(pc.get("original_name")))
        for dg in daily_games:
            active_landmark_norms.add(normalize_name(dg.get("boss_original_title")))

        target_landmarks = []
        discovered_landmarks = []

        if landmark_id:
            found = next((lm for lm in landmarks if lm.get("id") == landmark_id), None)
            if not found:
                raise ValueError(f"Landmark ID '{landmark_id}' not found.")
            target_landmarks = [found]
        else:
            if discover_new_landmarks:
                discovered_landmarks = self.discover_landmarks(count=max(count, 4), auto_approve=False)
                for dlm in discovered_landmarks:
                    if len(target_landmarks) < count:
                        target_landmarks.append(dlm)

            if len(target_landmarks) < count:
                landmarks = self.load_json(self.landmarks_file, [])
                puns = self.load_json(self.puns_file, [])
                existing_pc_pun_ids = {pc.get("pun_id") for pc in postcards}
                in_progress_lm_norms = {
                    normalize_name(p.get("original_name"))
                    for p in puns
                    if p.get("agent_curated") and p.get("status") == "approved" and p.get("id") not in existing_pc_pun_ids
                }
                # Prefer unused landmarks not yet in daily_games or pending postcards, prioritizing in-progress agent puns then agent_discovered
                unused_pool = [
                    lm for lm in landmarks
                    if normalize_name(lm.get("name")) not in active_landmark_norms
                    and lm not in target_landmarks
                ]
                random.shuffle(unused_pool)
                unused_pool.sort(key=lambda x: (
                    0 if normalize_name(x.get("name")) in in_progress_lm_norms else (1 if x.get("agent_discovered") else 2)
                ))
                for lm in unused_pool:
                    if len(target_landmarks) >= count:
                        break
                    target_landmarks.append(lm)

            # Fallback if all landmarks have been used at least once: pick iconic landmarks for a second fresh pun
            if len(target_landmarks) < count:
                landmarks = self.load_json(self.landmarks_file, [])
                fallback_pool = [lm for lm in landmarks if lm not in target_landmarks]
                random.shuffle(fallback_pool)
                for lm in fallback_pool:
                    if len(target_landmarks) >= count:
                        break
                    target_landmarks.append(lm)

        created_puzzles = []
        errors = []
        for lm in target_landmarks[:count]:
            try:
                bundle = self.build_single_puzzle_for_landmark(lm, art_style=art_style)
                created_puzzles.append(bundle)
            except Exception as e:
                print(f"[CurationAgent] Error building puzzle for '{lm.get('name')}': {e}")
                errors.append({"landmark": lm.get("name"), "error": str(e)})

        if created_puzzles:
            avg_score = sum(p.get("pun", {}).get("agent_score", 9.0) for p in created_puzzles) / len(created_puzzles)
            self.record_signal(
                signal_type="agent_run",
                stage="agent_queue",
                agent_score=round(avg_score, 2),
                new_value={
                    "generated_count": len(created_puzzles),
                    "discovered_landmarks_count": len(discovered_landmarks),
                    "puns": [p.get("pun", {}).get("pun_name") for p in created_puzzles]
                }
            )

        return {
            "discovered_landmarks_count": len(discovered_landmarks),
            "discovered_landmarks": discovered_landmarks,
            "generated_puzzles_count": len(created_puzzles),
            "generated_puzzles": created_puzzles,
            "errors": errors
        }

    # ==========================================================================
    # TARGETED RE-DO ENGINE (Pun Word / Clues / Postcard)
    # ==========================================================================
    def redo_puzzle_piece(
        self,
        clue_id,
        redo_type,
        custom_pun=None,
        human_feedback=None,
        art_style="random",
        custom_prompt=None
    ):
        """
        Re-do a specific piece of a candidate puzzle:
          - redo_type == 'pun':
              Marks the old pun as rejected (or replaces it with `custom_pun`),
              generates a brand-new guardrail-verified pun for the same landmark,
              regenerates the 3 clues + reviewer + owner reply, AND regenerates the postcard!
          - redo_type == 'clues':
              Keeps the landmark and current `pun_name`, regenerates the 3 progressive clues,
              review title, reviewer handle, and sarcastic owner reply, and syncs to the postcard.
          - redo_type == 'postcard':
              Keeps the landmark, `pun_name`, and clues, and regenerates the postcard image
              (using optional `art_style` and/or `custom_prompt`).
        """
        clues = self.load_json(self.clues_file, [])
        postcards = self.load_json(self.postcards_file, [])
        puns = self.load_json(self.puns_file, [])
        landmarks = self.load_json(self.landmarks_file, [])

        clue_idx = next((i for i, c in enumerate(clues) if c.get("id") == clue_id), None)
        pc_idx = next((i for i, p in enumerate(postcards) if p.get("clue_id") == clue_id or p.get("id") == clue_id), None)

        if clue_idx is None and pc_idx is not None:
            # Rehydrate clue entry if missing
            pc = postcards[pc_idx]
            clue_id = pc["clue_id"]
            clue_idx = next((i for i, c in enumerate(clues) if c.get("id") == clue_id), None)

        if clue_idx is None:
            raise ValueError(f"Candidate puzzle clue '{clue_id}' not found.")

        clue_obj = clues[clue_idx]
        lm_name = clue_obj["original_name"]
        lm_loc = clue_obj.get("location")
        if not lm_loc or lm_loc == "Unknown":
            lm_match = next((lm for lm in landmarks if normalize_name(lm.get("name")) == normalize_name(lm_name)), None)
            lm_loc = lm_match.get("location", "Unknown") if lm_match else "Unknown"
            clue_obj["location"] = lm_loc

        # Track redo_count & redo_history on candidate
        clue_obj["redo_count"] = int(clue_obj.get("redo_count", 0)) + 1
        if not isinstance(clue_obj.get("redo_history"), list):
            clue_obj["redo_history"] = []

        if redo_type == "pun":
            old_pun_name = clue_obj["pun_name"]
            old_runner_ups = [rp.lower() for rp in clue_obj.get("runner_up_puns", [])]
            was_runner_up = bool(custom_pun and custom_pun.strip().lower() in old_runner_ups)

            # Mark the old pun as rejected in puns.json so the agent learns not to reuse it
            for p in puns:
                if p.get("id") == clue_obj.get("pun_id") or p.get("pun_name") == old_pun_name:
                    p["status"] = "rejected"

            if custom_pun and custom_pun.strip():
                pun_result = {
                    "pun_name": custom_pun.strip(),
                    "agent_score": 9.5,
                    "agent_rationale": f"Custom pun word '{custom_pun.strip()}' selected by human curator (replaced '{old_pun_name}').",
                    "runner_up_puns": [ rp for rp in clue_obj.get("runner_up_puns", []) if rp.lower() != custom_pun.strip().lower() ]
                }
            else:
                pun_result = self.generate_and_select_pun(
                    lm_name,
                    lm_loc,
                    excluded_puns=[old_pun_name],
                    human_feedback=human_feedback
                )

            new_pun_name = pun_result["pun_name"]
            new_pun_id = f"pun_{re.sub(r'[^a-z0-9_]', '', lm_name.lower().replace(' ', '_'))}_{int(time.time())}_{random.randint(100, 999)}"
            new_pun_entry = {
                "id": new_pun_id,
                "original_name": lm_name,
                "location": lm_loc,
                "pun_name": new_pun_name,
                "status": "approved",
                "agent_curated": True,
                "agent_score": pun_result["agent_score"],
                "agent_rationale": pun_result["agent_rationale"],
                "runner_up_puns": pun_result["runner_up_puns"]
            }
            puns.append(new_pun_entry)
            self.save_json(self.puns_file, puns)

            # Cascade 1: Regenerate Clues & Owner Reply for the new pun
            new_clues = self.generate_clues_and_reply(
                lm_name,
                lm_loc,
                new_pun_name,
                human_feedback=human_feedback
            )
            clue_obj["pun_id"] = new_pun_id
            clue_obj["pun_name"] = new_pun_name
            clue_obj["reviewer_name"] = new_clues["reviewer_name"]
            clue_obj["review_title"] = new_clues["review_title"]
            clue_obj["clue1"] = new_clues["clue1"]
            clue_obj["clue2"] = new_clues["clue2"]
            clue_obj["clue3"] = new_clues["clue3"]
            clue_obj["owner_response"] = new_clues["owner_response"]
            clue_obj["page_theme"] = new_clues["page_theme"]
            clue_obj["agent_score"] = pun_result["agent_score"]
            clue_obj["agent_rationale"] = pun_result["agent_rationale"]
            clue_obj["runner_up_puns"] = pun_result["runner_up_puns"]
            clue_obj["redo_history"].append({
                "redo_type": "pun",
                "timestamp": int(time.time()),
                "old_pun": old_pun_name,
                "new_pun": new_pun_name,
                "was_runner_up": was_runner_up,
                "human_feedback": human_feedback or ""
            })
            clues[clue_idx] = clue_obj
            self.save_json(self.clues_file, clues)

            # Cascade 2: Regenerate Postcard for the new pun & clues
            postcard_entry = self.generate_postcard_for_clue(clue_obj, art_style=art_style)

            # Record Analytics Signal: REDO PUN
            self.record_signal(
                signal_type="redo",
                stage="pun",
                redo_type="pun",
                clue_id=clue_obj["id"],
                postcard_id=postcard_entry.get("id"),
                landmark_name=lm_name,
                location=lm_loc,
                pun_name=new_pun_name,
                old_value={"pun_name": old_pun_name},
                new_value={"pun_name": new_pun_name},
                art_style=postcard_entry.get("art_style", ""),
                page_theme=clue_obj.get("page_theme", ""),
                agent_score=pun_result["agent_score"],
                redo_count_at_event=clue_obj["redo_count"],
                was_runner_up_selected=was_runner_up,
                human_feedback=human_feedback
            )

            return {
                "redo_type": "pun",
                "old_pun_name": old_pun_name,
                "new_pun_name": new_pun_name,
                "clue": clue_obj,
                "postcard": postcard_entry
            }

        elif redo_type == "clues":
            old_clues_snapshot = {
                "review_title": clue_obj.get("review_title", ""),
                "clue1": clue_obj.get("clue1", ""),
                "clue2": clue_obj.get("clue2", ""),
                "clue3": clue_obj.get("clue3", ""),
                "owner_response": clue_obj.get("owner_response", "")
            }
            new_clues = self.generate_clues_and_reply(
                lm_name,
                lm_loc,
                clue_obj["pun_name"],
                previous_clues=clue_obj,
                human_feedback=human_feedback
            )
            clue_obj["reviewer_name"] = new_clues["reviewer_name"]
            clue_obj["review_title"] = new_clues["review_title"]
            clue_obj["clue1"] = new_clues["clue1"]
            clue_obj["clue2"] = new_clues["clue2"]
            clue_obj["clue3"] = new_clues["clue3"]
            clue_obj["owner_response"] = new_clues["owner_response"]
            clue_obj["redo_history"].append({
                "redo_type": "clues",
                "timestamp": int(time.time()),
                "human_feedback": human_feedback or ""
            })
            clues[clue_idx] = clue_obj
            self.save_json(self.clues_file, clues)

            # Sync owner_response & redo metadata to the matching postcard
            postcards = self.load_json(self.postcards_file, [])
            pc_entry = None
            for pc in postcards:
                if pc.get("clue_id") == clue_obj["id"]:
                    pc["owner_response"] = clue_obj["owner_response"]
                    pc["redo_count"] = clue_obj["redo_count"]
                    pc["redo_history"] = clue_obj["redo_history"]
                    pc_entry = pc
            self.save_json(self.postcards_file, postcards)

            # Record Analytics Signal: REDO CLUES
            self.record_signal(
                signal_type="redo",
                stage="clues",
                redo_type="clues",
                clue_id=clue_obj["id"],
                postcard_id=pc_entry.get("id") if pc_entry else "",
                landmark_name=lm_name,
                location=lm_loc,
                pun_name=clue_obj["pun_name"],
                old_value=old_clues_snapshot,
                new_value={
                    "review_title": clue_obj["review_title"],
                    "clue1": clue_obj["clue1"],
                    "clue2": clue_obj["clue2"],
                    "clue3": clue_obj["clue3"],
                    "owner_response": clue_obj["owner_response"]
                },
                art_style=pc_entry.get("art_style", "") if pc_entry else "",
                page_theme=clue_obj.get("page_theme", ""),
                agent_score=clue_obj.get("agent_score", 9.0),
                redo_count_at_event=clue_obj["redo_count"],
                human_feedback=human_feedback
            )

            return {
                "redo_type": "clues",
                "clue": clue_obj,
                "postcard": pc_entry
            }

        elif redo_type == "postcard":
            old_pc = postcards[pc_idx] if pc_idx is not None else {}
            old_style = old_pc.get("art_style", "")
            old_prompt = old_pc.get("image_prompt", "")

            clue_obj["redo_history"].append({
                "redo_type": "postcard",
                "timestamp": int(time.time()),
                "old_style": old_style,
                "requested_style": art_style,
                "human_feedback": custom_prompt or human_feedback or ""
            })
            clues[clue_idx] = clue_obj
            self.save_json(self.clues_file, clues)

            postcard_entry = self.generate_postcard_for_clue(
                clue_obj,
                art_style=art_style,
                custom_prompt=custom_prompt
            )

            # Record Analytics Signal: REDO POSTCARD
            self.record_signal(
                signal_type="redo",
                stage="postcard",
                redo_type="postcard",
                clue_id=clue_obj["id"],
                postcard_id=postcard_entry.get("id"),
                landmark_name=lm_name,
                location=lm_loc,
                pun_name=clue_obj["pun_name"],
                old_value={"art_style": old_style, "image_prompt": old_prompt},
                new_value={"art_style": postcard_entry.get("art_style", ""), "image_prompt": postcard_entry.get("image_prompt", "")},
                art_style=old_style or postcard_entry.get("art_style", ""),
                page_theme=clue_obj.get("page_theme", ""),
                agent_score=clue_obj.get("agent_score", 9.0),
                redo_count_at_event=clue_obj["redo_count"],
                human_feedback=custom_prompt or human_feedback
            )

            return {
                "redo_type": "postcard",
                "clue": clue_obj,
                "postcard": postcard_entry
            }

        else:
            raise ValueError(f"Unsupported redo_type: '{redo_type}'. Expected 'pun', 'clues', or 'postcard'.")
