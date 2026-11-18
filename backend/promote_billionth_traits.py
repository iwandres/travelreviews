"""
Flywheel Admin Utility: Previews or promotes top-hit custom cached traits from
MongoDB Atlas / local cache into `the-8-billionth/data/traits-core.json`.

Usage:
  python backend/promote_billionth_traits.py --min-hits 5 [--write]
"""
import argparse
import json
import os

import billionth_database as bdb

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
CORE_JSON_PATH = os.path.abspath(
    os.path.join(DIR_PATH, "..", "the-8-billionth", "data", "traits-core.json")
)


def main():
    parser = argparse.ArgumentParser(description="Promote popular cached traits into traits-core.json")
    parser.add_argument("--min-hits", type=int, default=5, help="Minimum hitCount threshold")
    parser.add_argument("--limit", type=int, default=30, help="Max traits to inspect")
    parser.add_argument("--write", action="store_true", help="Write non-duplicate traits into traits-core.json")
    args = parser.parse_args()

    candidates = bdb.get_top_cached_traits(min_hits=args.min_hits, limit=args.limit)
    print(f"[Flywheel] Found {len(candidates)} cached traits with hitCount >= {args.min_hits}.")

    with open(CORE_JSON_PATH, "r", encoding="utf-8") as fh:
        core_doc = json.load(fh)

    existing_slugs = {t["canonicalSlug"] for t in core_doc.get("traits", [])}
    added = 0

    for entry in candidates:
        t = entry.get("trait") or {}
        slug = t.get("canonicalSlug")
        hits = entry.get("hitCount", 1)
        print(f"  • [{hits} hits] {slug}: {t.get('label')} ({t.get('prevalence', 0) * 100:.4g}%)")
        if args.write and slug and slug not in existing_slugs:
            promoted_trait = {
                "id": slug,
                "canonicalSlug": slug,
                "label": t.get("label"),
                "shortBadge": t.get("shortBadge"),
                "emoji": t.get("emoji", "✨"),
                "category": t.get("category", "daily_quirks"),
                "prevalence": t.get("prevalence"),
                "clusterTags": t.get("clusterTags", ["indoor_hobby"]),
                "snarkNote": t.get("snarkNote", ""),
                "aliases": [],
                "subsumes": []
            }
            if t.get("isVerifiedExtremeRarity"):
                promoted_trait["isVerifiedExtremeRarity"] = True
            core_doc["traits"].append(promoted_trait)
            existing_slugs.add(slug)
            added += 1

    if args.write and added > 0:
        with open(CORE_JSON_PATH, "w", encoding="utf-8") as fh:
            json.dump(core_doc, fh, indent=2, ensure_ascii=False)
        print(f"[Flywheel] Appended {added} new traits to {CORE_JSON_PATH}.")


if __name__ == "__main__":
    main()
