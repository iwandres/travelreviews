"""
Flywheel Admin Utility: Previews or promotes top-hit custom cached traits from
MongoDB Atlas / local cache into `the-8-billionth/data/traits-core.json`.

Usage:
  # Preview top candidates with 5+ hits:
  python backend/promote_billionth_traits.py --min-hits 5

  # Sweep all qualifying candidates into traits-core.json and mark promoted in DB:
  python backend/promote_billionth_traits.py --min-hits 5 --write

  # Cherry-pick specific slugs from a preview:
  python backend/promote_billionth_traits.py --min-hits 3 --slugs makes_sourdough,plays_mahjong --write
"""
import argparse
import json
import os
import re
import sys

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
if DIR_PATH not in sys.path:
    sys.path.insert(0, DIR_PATH)

import billionth_database as bdb
import billionth_estimator as est

DEFAULT_CORE_PATH = os.path.abspath(
    os.path.join(DIR_PATH, "..", "the-8-billionth", "data", "traits-core.json")
)
DEFAULT_PARAM_PATH = os.path.abspath(
    os.path.join(DIR_PATH, "..", "the-8-billionth", "data", "traits-parametric.json")
)


def _norm_key(text):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]+", " ", str(text or "").lower())).strip()


def _extract_aliases(entry, trait_obj, max_aliases=6):
    """Builds clean Omnibox search aliases from user samplePhrasings without duplicating label/badge."""
    label_norm = _norm_key(trait_obj.get("label"))
    badge_norm = _norm_key(trait_obj.get("shortBadge"))
    seen = {label_norm, badge_norm}
    out = []

    raw_pool = list(trait_obj.get("aliases") or []) + list(entry.get("samplePhrasings") or [])
    for phrase in raw_pool:
        cleaned = str(phrase or "").strip()
        if not cleaned:
            continue
        variants = [cleaned]
        # Also offer concise stem when user typed "i am ..." / "i have ..." / "i ..."
        stem = re.sub(r"^(?:i\s+am\s+(?:a|an)\s+|i\s+am\s+|i\s+have\s+|i\s+)", "", cleaned, flags=re.I).strip()
        if 3 <= len(stem) < len(cleaned):
            variants.append(stem)
        for v in variants:
            vk = _norm_key(v)
            if len(vk) < 3 or len(v) > 64 or vk in seen:
                continue
            seen.add(vk)
            out.append(v)
            if len(out) >= max_aliases:
                return out
    return out


def _build_known_prevalence_map(core_doc, param_doc):
    """Maps all known L1+L2 slugs -> (prevalence, subsumes[]) for strict subset & transitive closure checks."""
    known = {}
    for t in core_doc.get("traits", []):
        slug = t.get("canonicalSlug")
        if slug:
            known[slug] = (float(t.get("prevalence") or 0), list(t.get("subsumes") or []))
    for gen in (param_doc or {}).get("generators", []):
        for opt in gen.get("options", []):
            slug = opt.get("canonicalSlug")
            if slug:
                known[slug] = (float(opt.get("prevalence") or 0), list(opt.get("subsumes") or []))
    return known


def _sanitize_promoted_trait(entry, known_map):
    t = entry.get("trait") or {}
    slug = re.sub(r"[^a-z0-9_]+", "_", str(t.get("canonicalSlug") or "").lower()).strip("_")[:56]
    if not slug or not t.get("label"):
        return None

    cat = str(t.get("category") or "daily_quirks").strip()
    if cat not in est.CLOSED_CATEGORIES:
        cat = "daily_quirks"

    tags = []
    for tag in t.get("clusterTags") or []:
        ts = str(tag or "").strip()
        if ts in est.CLOSED_CLUSTER_TAGS and ts not in tags:
            tags.append(ts)
            if len(tags) == 4:
                break
    if not tags:
        tags = ["indoor_hobby"]

    gates = []
    for g in t.get("baseGates") or []:
        gs = str(g or "").strip()
        if gs in est.CLOSED_BASE_GATES and gs not in gates:
            gates.append(gs)
            if len(gates) == 4:
                break

    is_extreme = bool(t.get("isVerifiedExtremeRarity"))
    min_prev = est.EXTREME_MIN_PREVALENCE if is_extreme else est.DEFAULT_MIN_PREVALENCE
    prev = max(min_prev, min(0.95, float(t.get("prevalence") or 0.001)))

    # Validate subsumes against known L1+L2 items & enforce P(child) < P(parent) + transitive closure
    valid_subs = []
    queue = list(t.get("subsumes") or [])
    while queue:
        parent_slug = str(queue.pop(0) or "").strip()
        if not parent_slug or parent_slug == slug or parent_slug in valid_subs:
            continue
        if parent_slug in known_map:
            parent_prev, parent_subs = known_map[parent_slug]
            if prev < parent_prev:
                valid_subs.append(parent_slug)
                for grand in parent_subs:
                    if grand not in valid_subs:
                        queue.append(grand)

    promoted = {
        "id": slug,
        "canonicalSlug": slug,
        "label": str(t.get("label")).strip(),
        "shortBadge": str(t.get("shortBadge") or t.get("label")).strip()[:36],
        "emoji": str(t.get("emoji") or "✨").strip()[:6],
        "category": cat,
        "prevalence": prev,
        "clusterTags": tags,
        "snarkNote": str(t.get("snarkNote") or "").strip()[:165],
        "aliases": _extract_aliases(entry, t),
        "subsumes": valid_subs,
        "baseGates": gates,
        "promotedFromCache": True
    }
    if is_extreme:
        promoted["isVerifiedExtremeRarity"] = True
    return promoted


def promote_candidates(
    min_hits=5,
    limit=30,
    only_slugs=None,
    write=False,
    core_path=DEFAULT_CORE_PATH,
    param_path=DEFAULT_PARAM_PATH
):
    candidates = bdb.get_top_cached_traits(min_hits=min_hits, limit=limit)
    if only_slugs:
        allow = {s.strip() for s in only_slugs if s.strip()}
        candidates = [c for c in candidates if (c.get("canonicalSlug") or (c.get("trait") or {}).get("canonicalSlug")) in allow]

    with open(core_path, "r", encoding="utf-8") as fh:
        core_doc = json.load(fh)
    param_doc = {}
    if param_path and os.path.exists(param_path):
        with open(param_path, "r", encoding="utf-8") as fh:
            param_doc = json.load(fh)

    known_map = _build_known_prevalence_map(core_doc, param_doc)
    by_slug = {t["canonicalSlug"]: t for t in core_doc.get("traits", []) if t.get("canonicalSlug")}
    by_label = {_norm_key(t.get("label")): t for t in core_doc.get("traits", []) if t.get("label")}

    added_traits = []
    merged_existing_slugs = []
    promoted_db_slugs = []

    print(f"[Flywheel] Found {len(candidates)} unpromoted cached trait(s) with hitCount >= {min_hits}.")

    for entry in candidates:
        t = entry.get("trait") or {}
        raw_slug = entry.get("canonicalSlug") or t.get("canonicalSlug") or ""
        hits = int(entry.get("hitCount", 1))
        sanitized = _sanitize_promoted_trait(entry, known_map)
        if not sanitized:
            continue

        slug = sanitized["canonicalSlug"]
        existing = by_slug.get(slug) or by_label.get(_norm_key(sanitized["label"]))
        est_humans = round(sanitized["prevalence"] * est.WORLD_POPULATION)

        if existing:
            print(
                f"  • [{hits} hits] {slug} -> ALREADY IN CORE as '{existing['canonicalSlug']}' "
                f"(merging any new aliases & marking promoted)"
            )
            if write:
                cur_aliases = list(existing.get("aliases") or [])
                cur_norms = {_norm_key(a) for a in cur_aliases} | {
                    _norm_key(existing.get("label")),
                    _norm_key(existing.get("shortBadge"))
                }
                for a in sanitized["aliases"]:
                    if _norm_key(a) not in cur_norms and len(cur_aliases) < 10:
                        cur_aliases.append(a)
                        cur_norms.add(_norm_key(a))
                existing["aliases"] = cur_aliases
                merged_existing_slugs.append(existing["canonicalSlug"])
                promoted_db_slugs.append(raw_slug)
            continue

        gates_str = ",".join(sanitized["baseGates"]) if sanitized["baseGates"] else "none"
        tags_str = ",".join(sanitized["clusterTags"])
        alias_str = ", ".join(f'"{a}"' for a in sanitized["aliases"][:3]) or "none"
        print(
            f"  • [{hits} hits] {slug}: {sanitized['label']} "
            f"(~{est_humans:,} | {sanitized['prevalence'] * 100:.4g}% | tags=[{tags_str}] | gates=[{gates_str}] | aliases={alias_str})"
        )

        if write:
            core_doc["traits"].append(sanitized)
            by_slug[slug] = sanitized
            by_label[_norm_key(sanitized["label"])] = sanitized
            known_map[slug] = (sanitized["prevalence"], sanitized["subsumes"])
            added_traits.append(sanitized)
            promoted_db_slugs.append(raw_slug)

    if write and (added_traits or merged_existing_slugs):
        with open(core_path, "w", encoding="utf-8") as fh:
            json.dump(core_doc, fh, separators=(",", ":"), ensure_ascii=False)
        bdb.mark_traits_promoted(promoted_db_slugs)
        print(
            f"[Flywheel] Added {len(added_traits)} new trait(s) and updated {len(merged_existing_slugs)} existing trait(s) "
            f"in {core_path} (marked {len(promoted_db_slugs)} promoted in cache)."
        )
    elif not write and candidates:
        print("[Flywheel] Dry-run only. Re-run with --write to commit into traits-core.json.")

    return {
        "inspected": len(candidates),
        "added": len(added_traits),
        "mergedExisting": len(merged_existing_slugs),
        "addedSlugs": [t["canonicalSlug"] for t in added_traits]
    }


def main():
    parser = argparse.ArgumentParser(description="Promote popular cached traits into traits-core.json")
    parser.add_argument("--min-hits", type=int, default=5, help="Minimum hitCount threshold (default: 5)")
    parser.add_argument("--limit", type=int, default=30, help="Max traits to inspect (default: 30)")
    parser.add_argument(
        "--slugs",
        type=str,
        default="",
        help="Optional comma-separated canonicalSlugs to cherry-pick"
    )
    parser.add_argument("--write", action="store_true", help="Write promoted traits into traits-core.json")
    args = parser.parse_args()

    only_slugs = [s.strip() for s in args.slugs.split(",") if s.strip()] if args.slugs else None
    promote_candidates(
        min_hits=args.min_hits,
        limit=args.limit,
        only_slugs=only_slugs,
        write=args.write
    )


if __name__ == "__main__":
    main()
