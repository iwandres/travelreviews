"""
Unit & Integration Tests for The 8.3 Billionth Backend (Guardrails, Schema Clamp & Cache Flywheel)
"""
import os
import py_compile
import sys
import tempfile
import unittest

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
BACKEND_DIR = os.path.dirname(DIR_PATH)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import billionth_database as bdb
import billionth_estimator as est
import promote_billionth_traits as promo


def test_python_syntax_all():
    targets = [
        "billionth_database.py",
        "billionth_estimator.py",
        "promote_billionth_traits.py",
        "admin_server.py",
        "unified_server.py"
    ]
    for fname in targets:
        py_compile.compile(os.path.join(BACKEND_DIR, fname), doraise=True)


def test_pre_guardrails():
    # PII checks
    assert est.run_pre_guardrails("My email is alice@example.com")["status"] == "rejected_pii"
    assert est.run_pre_guardrails("Call me at 415-555-0199")["status"] == "rejected_pii"
    assert est.run_pre_guardrails("I live at 742 Evergreen Terrace Drive")["status"] == "rejected_pii"
    assert est.run_pre_guardrails("I was born on 1991-07-14")["status"] == "rejected_pii"
    assert est.run_pre_guardrails("I was born on March 14, 1992")["status"] == "rejected_pii"
    assert est.run_pre_guardrails("My full name is John Jacob")["status"] == "rejected_pii"

    # Ephemeral checks
    assert est.run_pre_guardrails("I am sitting down right now")["status"] == "rejected_ephemeral"
    assert est.run_pre_guardrails("currently blinking")["status"] == "rejected_ephemeral"

    # Legitimate traits pass pre-guardrails cleanly
    assert est.run_pre_guardrails("I make homemade jalapeño relish") is None
    assert est.run_pre_guardrails("I grow carnivorous pitcher plants indoors") is None
    assert est.run_pre_guardrails("I was born in December") is None


def test_schema_clamping_and_cache_flywheel():
    # Isolate local cache file inside a temporary file so tests never pollute repo state
    orig_cache_file = bdb.LOCAL_CACHE_FILE
    orig_mongo = bdb._mongo_col
    fd, temp_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(temp_path)

    try:
        bdb.LOCAL_CACHE_FILE = temp_path
        bdb._mongo_col = None

        # 1. Standard custom trait attempting implausibly tiny prevalence (1 person) must clamp to >= 1e-7 (~830)
        raw_llm = {
            "status": "accepted",
            "rejectionReason": None,
            "compoundSplit": [],
            "fermi": {
                "baseGroup": "~180M home picklers",
                "conditionalRate": "~0.0001%",
                "estimatedGlobalHumans": 2
            },
            "trait": {
                "canonicalSlug": "Makes Jalapeño Relish!!",
                "label": "I make homemade jalapeño relish",
                "shortBadge": "Jalapeño relish",
                "emoji": "🌶️",
                "category": "food_palate",
                "prevalence": 1e-11,
                "clusterTags": ["culinary_diy", "spicy_palate", "tactile_analog_ritual", "not_a_real_tag"],
                "baseGates": ["adult_15plus", "connected_urban_affluent", "fake_gate"],
                "subsumesSlugs": ["eats_spicy_daily", "nonexistent_random_slug"],
                "snarkNote": "Sweet heat.",
                "isVerifiedExtremeRarity": False
            }
        }

        sanitized = est._sanitize_accepted_payload(
            raw_llm,
            "I'm making homemade jalapeño relish!",
            active_slugs=["eats_spicy_daily"],
            active_traits=[{"slug": "eats_spicy_daily", "label": "I eat spicy chili heat almost every single day"}]
        )
        assert len(est.CLOSED_CLUSTER_TAGS) == 40
        assert len(est.CLOSED_BASE_GATES) == 4
        assert sanitized["trait"]["canonicalSlug"] == "makes_jalape_o_relish"
        assert sanitized["trait"]["prevalence"] >= 1e-7
        assert sanitized["fermi"]["estimatedGlobalHumans"] >= 830
        assert sanitized["trait"]["clusterTags"] == ["culinary_diy", "spicy_palate", "tactile_analog_ritual"]
        assert sanitized["trait"]["baseGates"] == ["adult_15plus", "connected_urban_affluent"]
        assert sanitized["cacheableTrait"]["baseGates"] == ["adult_15plus", "connected_urban_affluent"]
        assert "eats_spicy_daily" in sanitized["trait"]["subsumes"]

        # 2. Store & verify normalized cache flywheel hit
        bdb.store_cached_trait(
            "I'm making homemade jalapeño relish!",
            sanitized["cacheableTrait"],
            sanitized["fermi"]
        )
        hit = bdb.lookup_cached_trait("  i am making homemade jalapeño relish.  ")
        assert hit is not None
        assert hit["cached"] is True
        assert hit["hitCount"] == 2
        assert hit["trait"]["label"] == "I make homemade jalapeño relish"

        # 3. Verified extreme rarity allows below 1e-7 down to 1e-9
        extreme_llm = {
            "status": "accepted",
            "rejectionReason": None,
            "compoundSplit": [],
            "fermi": {
                "baseGroup": "Olympic medalists alive today",
                "conditionalRate": "100%",
                "estimatedGlobalHumans": 25000
            },
            "trait": {
                "canonicalSlug": "olympic_medalist",
                "label": "I have won an Olympic medal",
                "shortBadge": "Olympic medalist",
                "emoji": "🥇",
                "category": "sports_movement",
                "prevalence": 25000 / 8_300_000_000,
                "clusterTags": ["athletic"],
                "snarkNote": "Actual podium hardware.",
                "isVerifiedExtremeRarity": True
            }
        }
        ext_clean = est._sanitize_accepted_payload(extreme_llm, "I won an Olympic medal")
        assert ext_clean["trait"]["isVerifiedExtremeRarity"] is True
        assert abs(ext_clean["trait"]["prevalence"] - (25000 / 8_300_000_000)) < 1e-10
    finally:
        bdb.LOCAL_CACHE_FILE = orig_cache_file
        bdb._mongo_col = orig_mongo
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_promote_billionth_traits_lossless():
    import json
    orig_cache_file = bdb.LOCAL_CACHE_FILE
    orig_mongo = bdb._mongo_col
    fd_cache, temp_cache = tempfile.mkstemp(suffix=".json")
    os.close(fd_cache)
    os.remove(temp_cache)
    fd_core, temp_core = tempfile.mkstemp(suffix=".json")
    os.close(fd_core)
    fd_param, temp_param = tempfile.mkstemp(suffix=".json")
    os.close(fd_param)

    try:
        bdb.LOCAL_CACHE_FILE = temp_cache
        bdb._mongo_col = None

        seed_core = {
            "version": "2.0",
            "traits": [
                {
                    "id": "marathon_finisher",
                    "canonicalSlug": "marathon_finisher",
                    "label": "I have finished a full marathon (26.2 mi)",
                    "shortBadge": "Marathon finisher",
                    "emoji": "🎽",
                    "category": "sports_movement",
                    "prevalence": 0.0017,
                    "clusterTags": ["athletic", "endurance_sport"],
                    "snarkNote": "26.2 miles.",
                    "aliases": ["ran a marathon"],
                    "subsumes": ["runs_regularly"],
                    "baseGates": ["connected_urban_affluent"]
                },
                {
                    "id": "runs_regularly",
                    "canonicalSlug": "runs_regularly",
                    "label": "I run for fitness regularly",
                    "shortBadge": "Regular runner",
                    "emoji": "👟",
                    "category": "sports_movement",
                    "prevalence": 0.075,
                    "clusterTags": ["athletic", "endurance_sport"],
                    "snarkNote": "Runner.",
                    "aliases": ["jogger"],
                    "subsumes": [],
                    "baseGates": []
                }
            ]
        }
        with open(temp_core, "w", encoding="utf-8") as fh:
            json.dump(seed_core, fh, separators=(",", ":"))
        with open(temp_param, "w", encoding="utf-8") as fh:
            json.dump({"version": "2.0", "generators": []}, fh)

        trait_obj = {
            "id": "boston_qualifier",
            "canonicalSlug": "boston_qualifier",
            "label": "I have run a Boston-qualifying marathon time",
            "shortBadge": "Boston qualifier",
            "emoji": "🦄",
            "category": "sports_movement",
            "prevalence": 0.00018,
            "clusterTags": ["athletic", "endurance_sport", "quant_systemizer"],
            "baseGates": ["adult_15plus", "connected_urban_affluent"],
            "subsumes": ["marathon_finisher", "unknown_fake_slug"],
            "snarkNote": "Unicorn jacket territory.",
            "isVerifiedExtremeRarity": False
        }
        fermi_obj = {
            "baseGroup": "~14M marathoners",
            "conditionalRate": "~10%",
            "estimatedGlobalHumans": 1_500_000
        }
        bdb.store_cached_trait("I qualified for the Boston Marathon!", trait_obj, fermi_obj)
        bdb.store_cached_trait("I ran a BQ marathon time", trait_obj, fermi_obj)
        bdb.lookup_cached_trait("i ran a bq marathon time")  # hitCount -> 3

        dry = promo.promote_candidates(
            min_hits=3,
            write=False,
            core_path=temp_core,
            param_path=temp_param
        )
        assert dry["inspected"] == 1
        assert dry["added"] == 0

        committed = promo.promote_candidates(
            min_hits=3,
            write=True,
            core_path=temp_core,
            param_path=temp_param
        )
        assert committed["added"] == 1
        assert committed["addedSlugs"] == ["boston_qualifier"]

        with open(temp_core, "r", encoding="utf-8") as fh:
            raw_written = fh.read()
        assert "\n" not in raw_written.strip(), "Expected compact single-line JSON matching seed builder"
        written_doc = json.loads(raw_written)
        promoted = next(t for t in written_doc["traits"] if t["canonicalSlug"] == "boston_qualifier")
        assert promoted["promotedFromCache"] is True
        assert promoted["baseGates"] == ["adult_15plus", "connected_urban_affluent"]
        assert promoted["clusterTags"] == ["athletic", "endurance_sport", "quant_systemizer"]
        # Transitive closure: marathon_finisher -> runs_regularly, and unknown_fake_slug stripped
        assert promoted["subsumes"] == ["marathon_finisher", "runs_regularly"]
        assert any("qualified for the boston marathon" in a for a in promoted["aliases"])

        # Subsequent sweep skips already-promoted traits
        second = promo.promote_candidates(
            min_hits=3,
            write=False,
            core_path=temp_core,
            param_path=temp_param
        )
        assert second["inspected"] == 0
    finally:
        bdb.LOCAL_CACHE_FILE = orig_cache_file
        bdb._mongo_col = orig_mongo
        for p in (temp_cache, temp_core, temp_param):
            if os.path.exists(p):
                os.remove(p)


class TestBillionthBackend(unittest.TestCase):
    def test_all_billionth_suites(self):
        test_python_syntax_all()
        test_pre_guardrails()
        test_schema_clamping_and_cache_flywheel()
        test_promote_billionth_traits_lossless()


if __name__ == "__main__":
    test_python_syntax_all()
    test_pre_guardrails()
    test_schema_clamping_and_cache_flywheel()
    test_promote_billionth_traits_lossless()
    # Verify _call_gemini_structured source never injects activeSlugs/activeTraits into user_prompt
    import inspect
    fn_src = inspect.getsource(est._call_gemini_structured)
    assert "context_note" not in fn_src, "LLM prompt must stay 100% stateless!"
    print("[Backend Test Suite] All Python syntax, stateless cache, baseGates, promotion & clamping tests passed!")
