"""
The 8.3 Billionth — Persistent Trait Cache Flywheel & Rate Limiter (MongoDB Atlas + Local JSON Fallback)
Integrates with the PunFiction Render Backend (admin_server.py / unified_server.py) and MONGO_URI.
"""
import hashlib
import json
import os
import re
import threading
import time
from datetime import datetime, timezone

try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
except ImportError:
    MongoClient = None
    ASCENDING = 1
    DESCENDING = -1

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
LOCAL_CACHE_FILE = os.path.join(DIR_PATH, "billionth_traits_cache.json")

_lock = threading.Lock()
_rate_buckets = {}

# Initialize MongoDB connection (non-blocking 1.5s timeout for seamless offline local dev)
_mongo_col = None
_indexes_ensured = False

mongo_uri = os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URI")
if MongoClient and mongo_uri:
    try:
        _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=1500)
        _db = _client["billionth_db"]
        _mongo_col = _db["traits_cache"]
    except Exception as exc:
        print(f"[Billionth DB] Notice: MongoDB init deferred/offline ({exc}). Using local JSON fallback.")
        _mongo_col = None


def _ensure_indexes():
    global _indexes_ensured, _mongo_col
    if _indexes_ensured or _mongo_col is None:
        return
    try:
        _mongo_col.create_index([("canonicalSlug", ASCENDING)], unique=True, background=True)
        _mongo_col.create_index([("inputHashes", ASCENDING)], background=True)
        _mongo_col.create_index([("hitCount", DESCENDING)], background=True)
        _indexes_ensured = True
    except Exception as exc:
        print(f"[Billionth DB] MongoDB unreachable during index check ({exc}); falling back to local cache.")
        _mongo_col = None


def normalize_input_text(raw_input):
    """Normalizes free-text input for deterministic cache-key hashing."""
    text = str(raw_input or "").strip().lower()
    # Strip trailing punctuation and collapse internal whitespace
    text = re.sub(r"^[\s\"'“”‘’]+|[\s.!?;:,\"'“”‘’]+$", "", text)
    text = re.sub(r"\s+", " ", text)
    # Normalize common leading first-person phrasing variations so
    # "i am left handed" and "im left handed" hash identically
    text = re.sub(r"^i['’]?m\s+", "i am ", text)
    text = re.sub(r"^i['’]?ve\s+", "i have ", text)
    return text


def hash_normalized_input(raw_input):
    norm = normalize_input_text(raw_input)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def _load_local_cache():
    if not os.path.exists(LOCAL_CACHE_FILE):
        return {}
    try:
        with open(LOCAL_CACHE_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_local_cache(cache_dict):
    try:
        with open(LOCAL_CACHE_FILE, "w", encoding="utf-8") as fh:
            json.dump(cache_dict, fh, indent=2, ensure_ascii=False)
    except Exception as exc:
        print(f"[Billionth DB] Local cache write warning: {exc}")


def check_rate_limit(client_ip, max_per_minute=25):
    """Sliding 60-second IP rate limiter for uncached Gemini calls."""
    now = time.time()
    ip_key = str(client_ip or "anon")
    with _lock:
        timestamps = _rate_buckets.get(ip_key, [])
        cutoff = now - 60.0
        timestamps = [ts for ts in timestamps if ts > cutoff]
        if len(timestamps) >= max_per_minute:
            _rate_buckets[ip_key] = timestamps
            return False
        timestamps.append(now)
        _rate_buckets[ip_key] = timestamps
        return True


def lookup_cached_trait(raw_input):
    """
    Looks up a previously estimated custom trait by normalized SHA-256 hash.
    Returns dict with status='accepted', trait, fermi, cached=True on hit, or None on miss.
    """
    norm = normalize_input_text(raw_input)
    if not norm:
        return None
    input_hash = hashlib.sha256(norm.encode("utf-8")).hexdigest()

    # 1. Try MongoDB Atlas first
    _ensure_indexes()
    if _mongo_col is not None:
        try:
            doc = _mongo_col.find_one_and_update(
                {"inputHashes": input_hash},
                {"$inc": {"hitCount": 1}, "$set": {"lastHitAt": datetime.now(timezone.utc).isoformat()}},
                projection={"_id": 0}
            )
            if doc and doc.get("trait"):
                return {
                    "status": "accepted",
                    "rejectionReason": None,
                    "compoundSplit": [],
                    "fermi": doc.get("fermi"),
                    "trait": doc.get("trait"),
                    "cached": True,
                    "hitCount": doc.get("hitCount", 1) + 1
                }
        except Exception as exc:
            print(f"[Billionth DB] MongoDB read fallback ({exc})")

    # 2. Local JSON fallback
    with _lock:
        cache = _load_local_cache()
        for slug, entry in cache.items():
            if input_hash in entry.get("inputHashes", []):
                entry["hitCount"] = int(entry.get("hitCount", 1)) + 1
                entry["lastHitAt"] = datetime.now(timezone.utc).isoformat()
                _save_local_cache(cache)
                return {
                    "status": "accepted",
                    "rejectionReason": None,
                    "compoundSplit": [],
                    "fermi": entry.get("fermi"),
                    "trait": entry.get("trait"),
                    "cached": True,
                    "hitCount": entry["hitCount"]
                }

    return None


def store_cached_trait(raw_input, trait_obj, fermi_obj):
    """
    Stores a newly estimated custom trait by canonicalSlug and adds its normalizedInputHash
    to inputHashes[], creating a permanent zero-cost flywheel for future lookups.
    """
    if not trait_obj or not trait_obj.get("canonicalSlug"):
        return
    slug = str(trait_obj["canonicalSlug"]).strip()
    input_hash = hash_normalized_input(raw_input)
    now_iso = datetime.now(timezone.utc).isoformat()

    _ensure_indexes()
    if _mongo_col is not None:
        try:
            _mongo_col.update_one(
                {"canonicalSlug": slug},
                {
                    "$setOnInsert": {
                        "canonicalSlug": slug,
                        "trait": trait_obj,
                        "fermi": fermi_obj,
                        "promotedToCore": False,
                        "createdAt": now_iso
                    },
                    "$set": {"lastHitAt": now_iso},
                    "$addToSet": {"inputHashes": input_hash},
                    "$inc": {"hitCount": 1}
                },
                upsert=True
            )
            return
        except Exception as exc:
            print(f"[Billionth DB] MongoDB write fallback ({exc})")

    with _lock:
        cache = _load_local_cache()
        existing = cache.get(slug)
        if existing:
            hashes = set(existing.get("inputHashes", []))
            hashes.add(input_hash)
            existing["inputHashes"] = sorted(hashes)
            existing["hitCount"] = int(existing.get("hitCount", 1)) + 1
            existing["lastHitAt"] = now_iso
        else:
            cache[slug] = {
                "canonicalSlug": slug,
                "inputHashes": [input_hash],
                "trait": trait_obj,
                "fermi": fermi_obj,
                "hitCount": 1,
                "promotedToCore": False,
                "createdAt": now_iso,
                "lastHitAt": now_iso
            }
        _save_local_cache(cache)


def get_top_cached_traits(min_hits=3, limit=50):
    """Returns top community-cached custom traits eligible for promotion to traits-core.json."""
    _ensure_indexes()
    if _mongo_col is not None:
        try:
            cursor = (
                _mongo_col.find(
                    {"promotedToCore": {"$ne": True}, "hitCount": {"$gte": int(min_hits)}},
                    {"_id": 0}
                )
                .sort("hitCount", DESCENDING)
                .limit(int(limit))
            )
            return list(cursor)
        except Exception:
            pass

    with _lock:
        cache = _load_local_cache()
        items = [
            v
            for v in cache.values()
            if not v.get("promotedToCore") and int(v.get("hitCount", 0)) >= int(min_hits)
        ]
        items.sort(key=lambda x: int(x.get("hitCount", 0)), reverse=True)
        return items[: int(limit)]
