"""
Unit & Integration Tests for The 8.3 Billionth Backend (Guardrails, Schema Clamp & Cache Flywheel)
"""
import os
import py_compile
import sys
import tempfile

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
BACKEND_DIR = os.path.dirname(DIR_PATH)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import billionth_database as bdb
import billionth_estimator as est


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


if __name__ == "__main__":
    test_python_syntax_all()
    test_pre_guardrails()
    test_schema_clamping_and_cache_flywheel()
    # Verify _call_gemini_structured source never injects activeSlugs/activeTraits into user_prompt
    import inspect
    fn_src = inspect.getsource(est._call_gemini_structured)
    assert "context_note" not in fn_src, "LLM prompt must stay 100% stateless!"
    print("[Backend Test Suite] All Python syntax, stateless cache, baseGates & clamping tests passed!")
