"""
Word Vine — MongoDB Atlas Persistence & Deterministic Physics Replay Verifier (Python)
Integrates directly with the PunFiction Render Backend (admin_server.py) and MONGO_URI.
"""
import os
import json
import math
from datetime import datetime, timezone
from pymongo import MongoClient, DESCENDING

mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(mongo_uri, serverSelectionTimeoutMS=1500)

db = client["wordvine_db"]
vines_col = db["daily_vines"]
players_col = db["players"]
runs_col = db["official_runs"]

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
LOCAL_VINES_FILE = os.path.join(DIR_PATH, "wordvine_daily_vines.json")
LOCAL_RUNS_FILE = os.path.join(DIR_PATH, "wordvine_records.json")


def get_calendar_keys(date_key=None):
    """Computes UTC dateKey (YYYY-MM-DD), ISO weekKey (YYYY-Www), and monthKey (YYYY-MM)."""
    try:
        if date_key:
            dt = datetime.strptime(str(date_key)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            dt = datetime.now(timezone.utc)
    except Exception:
        dt = datetime.now(timezone.utc)

    iso_year, iso_week, _ = dt.isocalendar()
    return {
        "dateKey": dt.strftime("%Y-%m-%d"),
        "weekKey": f"{iso_year}-W{iso_week:02d}",
        "monthKey": dt.strftime("%Y-%m")
    }


def cubic_ease_out(t):
    clamped = max(0.0, min(1.0, float(t)))
    inv = 1.0 - clamped
    return 1.0 - (inv * inv * inv)


def verify_replay(vine_nodes, choices, deltas_ms, final_wait_ms=0):
    """
    Server-Side Deterministic Physics Replay Verification.
    Re-simulates [dt_1, dt_2, ...] in 5ms fixed steps using the exact Word Vine equations:
      V_cam(t) = min(280, 45 + 1.8*t + 3.5*N)
      V_creep  = 0.35 * V_cam
      Spurt    = +125u (or +185u on Zone 1 Triple-Bloom) over 180ms cubic ease-out
      Clamp    = Y_vine - Y_cam > 750u
    """
    if not isinstance(vine_nodes, list) or not isinstance(choices, list) or not isinstance(deltas_ms, list):
        return {"valid": False, "reason": "Invalid replay payload arrays"}
    if len(choices) != len(deltas_ms):
        return {"valid": False, "reason": "Mismatch between choices and deltasMs length"}
    if len(choices) > len(vine_nodes):
        return {"valid": False, "reason": "More choices submitted than nodes in daily vine"}

    status = "PLAYING"
    node_index = 0
    nodes_completed = 0
    zone_id = 1
    effective_elapsed_sec = 0.0
    y_cam = 0.0
    y_vine = 360.0
    v_cam = 45.0
    max_altitude_units = 360.0

    spurt_active = False
    spurt_elapsed_ms = 0.0
    spurt_duration_ms = 180.0
    spurt_total_delta = 0.0
    spurt_applied_delta = 0.0
    bullet_time_remaining_ms = 0.0

    score = 0
    triplet_blooms = 0
    fixed_step_ms = 5.0

    def step_sim(dt_ms):
        nonlocal status, effective_elapsed_sec, y_cam, y_vine, v_cam, max_altitude_units
        nonlocal spurt_active, spurt_elapsed_ms, spurt_applied_delta, bullet_time_remaining_ms
        if status != "PLAYING" or dt_ms <= 0:
            return

        time_scale = 1.0
        if bullet_time_remaining_ms > 0:
            bt_prog = 1.0 - (bullet_time_remaining_ms / 600.0)
            time_scale = 0.25 + 0.75 * (bt_prog * bt_prog)
            bullet_time_remaining_ms = max(0.0, bullet_time_remaining_ms - dt_ms)

        dt_sec = (dt_ms / 1000.0) * time_scale
        effective_elapsed_sec += dt_sec

        v_cam = min(280.0, 45.0 + 1.8 * effective_elapsed_sec + 3.5 * nodes_completed)
        y_cam += v_cam * dt_sec

        v_creep = 0.35 * v_cam
        dy_vine = v_creep * dt_sec

        if spurt_active:
            spurt_elapsed_ms += dt_ms
            prog = min(1.0, spurt_elapsed_ms / spurt_duration_ms)
            eased = cubic_ease_out(prog)
            target_delta = spurt_total_delta * eased
            step_delta = max(0.0, target_delta - spurt_applied_delta)
            dy_vine += step_delta
            spurt_applied_delta = target_delta
            if prog >= 1.0:
                spurt_active = False

        y_vine += dy_vine
        if y_vine > max_altitude_units:
            max_altitude_units = y_vine

        screen_y = y_vine - y_cam
        if screen_y > 750.0:
            excess = screen_y - 750.0
            y_cam += excess * min(1.0, 14.0 * (dt_ms / 1000.0))

        if y_vine <= y_cam:
            y_vine = y_cam
            status = "OUTRUN"

    for i, choice in enumerate(choices):
        try:
            dt = float(deltas_ms[i])
        except Exception:
            return {"valid": False, "reason": f"Invalid delta at index {i}"}

        if dt < 15 or dt > 30000:
            return {"valid": False, "reason": f"Implausible keystroke delta at step {i}: {dt}ms"}

        rem = dt
        while rem > 0 and status == "PLAYING":
            step = min(fixed_step_ms, rem)
            step_sim(step)
            rem -= step

        if status != "PLAYING":
            break

        curr_node = vine_nodes[node_index]
        is_correct = int(choice) == int(curr_node.get("leftRightSeed", 0))
        if not is_correct:
            status = "SNIPPED"
            break

        c_zone = int(curr_node.get("zoneId", 1))
        is_triple_bloom = c_zone == 1 and int(curr_node.get("tripletStep", 0)) == 3

        z_mult = 1 if c_zone == 1 else (2 if c_zone == 2 else 3)
        lead_bonus = int(math.floor(max(0.0, y_vine - y_cam) / 10.0))
        b_triplet = 250 if is_triple_bloom else 0
        score += (100 * z_mult) + lead_bonus + b_triplet

        if is_triple_bloom:
            triplet_blooms += 1

        spurt_impulse = 185.0 if is_triple_bloom else 125.0
        if spurt_active and spurt_total_delta > spurt_applied_delta:
            y_vine += spurt_total_delta - spurt_applied_delta

        spurt_active = True
        spurt_elapsed_ms = 0.0
        spurt_duration_ms = 210.0 if is_triple_bloom else 180.0
        spurt_total_delta = spurt_impulse
        spurt_applied_delta = 0.0

        nodes_completed += 1
        node_index += 1

        if node_index >= len(vine_nodes):
            y_vine += spurt_impulse
            max_altitude_units = max(max_altitude_units, y_vine)
            status = "COMPLETED"
            break

        next_zone = int(vine_nodes[node_index].get("zoneId", c_zone))
        if next_zone != zone_id:
            zone_id = next_zone
            bullet_time_remaining_ms = 600.0

    if status == "PLAYING" and final_wait_ms:
        rem = min(60000.0, float(final_wait_ms))
        while rem > 0 and status == "PLAYING":
            step = min(fixed_step_ms, rem)
            step_sim(step)
            rem -= step

    altitude_meters = round(max_altitude_units * 0.012, 1)
    return {
        "valid": True,
        "score": int(score),
        "nodesCompleted": int(nodes_completed),
        "zoneReached": int(zone_id),
        "tripletBlooms": int(triplet_blooms),
        "altitudeMeters": altitude_meters,
        "deathCause": "OUTRUN" if status == "PLAYING" else status
    }


def load_local_vines():
    if os.path.exists(LOCAL_VINES_FILE):
        try:
            with open(LOCAL_VINES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def get_daily_vine(date_key=None):
    keys = get_calendar_keys(date_key)
    target_date = keys["dateKey"]
    try:
        doc = vines_col.find_one({"dateKey": target_date}, {"_id": 0})
        if doc:
            return doc
    except Exception:
        pass

    local_vines = load_local_vines()
    for v in local_vines:
        if v.get("dateKey") == target_date:
            return v
    return local_vines[0] if local_vines else None


def save_daily_vines(vines_list):
    try:
        with open(LOCAL_VINES_FILE, "w", encoding="utf-8") as f:
            json.dump(vines_list, f, indent=2)
    except Exception as e:
        print(f"Error writing local vines file: {e}")

    try:
        for v in vines_list:
            vines_col.update_one(
                {"dateKey": v["dateKey"]},
                {"$set": v},
                upsert=True
            )
    except Exception as e:
        print(f"MongoDB save_daily_vines warning: {e}")
    return True


def record_run_submission(device_token, handle, date_key, choices, deltas_ms, final_wait_ms=0):
    vine = get_daily_vine(date_key)
    if not vine or "nodes" not in vine:
        return {"accepted": False, "reason": "Daily vine not found"}

    verification = verify_replay(vine["nodes"], choices, deltas_ms, final_wait_ms)
    if not verification.get("valid"):
        return {"accepted": False, "reason": verification.get("reason", "Invalid replay")}

    keys = get_calendar_keys(date_key or vine.get("dateKey"))
    clean_handle = str(handle or "BriarClimber").strip()[:20]

    run_doc = {
        "dateKey": keys["dateKey"],
        "weekKey": keys["weekKey"],
        "monthKey": keys["monthKey"],
        "deviceToken": device_token,
        "handle": clean_handle,
        "score": verification["score"],
        "nodesCompleted": verification["nodesCompleted"],
        "altitudeMeters": verification["altitudeMeters"],
        "tripletBlooms": verification["tripletBlooms"],
        "deathCause": verification["deathCause"],
        "submittedAt": datetime.now(timezone.utc).isoformat()
    }

    try:
        players_col.update_one(
            {"deviceToken": device_token},
            {
                "$set": {"handle": clean_handle, "updatedAt": datetime.now(timezone.utc)},
                "$max": {"bestSingleVineScore": verification["score"]}
            },
            upsert=True
        )
        existing = runs_col.find_one({"dateKey": keys["dateKey"], "deviceToken": device_token})
        if existing:
            return {
                "accepted": True,
                "mode": "PRACTICE_REPLAY",
                "verifiedScore": verification["score"],
                "officialScore": existing.get("score", verification["score"]),
                "verification": verification
            }
        runs_col.insert_one(dict(run_doc))
        return {
            "accepted": True,
            "mode": "OFFICIAL_LOCKED",
            "verifiedScore": verification["score"],
            "verification": verification
        }
    except Exception as e:
        print(f"MongoDB record_run_submission fallback to local file: {e}")
        records = []
        if os.path.exists(LOCAL_RUNS_FILE):
            try:
                with open(LOCAL_RUNS_FILE, "r", encoding="utf-8") as f:
                    records = json.load(f)
            except Exception:
                records = []
        for r in records:
            if r.get("dateKey") == keys["dateKey"] and r.get("deviceToken") == device_token:
                return {
                    "accepted": True,
                    "mode": "PRACTICE_REPLAY",
                    "verifiedScore": verification["score"],
                    "officialScore": r.get("score", verification["score"]),
                    "verification": verification
                }
        records.append(run_doc)
        try:
            with open(LOCAL_RUNS_FILE, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
        except Exception:
            pass
        return {
            "accepted": True,
            "mode": "OFFICIAL_LOCKED",
            "verifiedScore": verification["score"],
            "verification": verification
        }


def get_leaderboard(tier="daily", date_key=None):
    keys = get_calendar_keys(date_key)
    tier = (tier or "daily").lower()

    try:
        if tier == "daily":
            cursor = (
                runs_col.find({"dateKey": keys["dateKey"]}, {"_id": 0})
                .sort([("score", DESCENDING), ("nodesCompleted", DESCENDING), ("altitudeMeters", DESCENDING)])
                .limit(50)
            )
            entries = [
                {
                    "handle": r.get("handle", "Climber"),
                    "nodes": r.get("nodesCompleted", 0),
                    "altitude": r.get("altitudeMeters", 0),
                    "score": r.get("score", 0)
                }
                for r in cursor
            ]
            if entries:
                return {"tier": tier, "dateKey": keys["dateKey"], "entries": entries}
        else:
            match_filter = {"weekKey": keys["weekKey"]} if tier == "weekly" else {"monthKey": keys["monthKey"]}
            slice_limit = 5 if tier == "weekly" else 20
            pipeline = [
                {"$match": match_filter},
                {"$sort": {"score": -1}},
                {
                    "$group": {
                        "_id": "$deviceToken",
                        "handle": {"$first": "$handle"},
                        "scores": {"$push": "$score"},
                        "days": {"$sum": 1}
                    }
                },
                {
                    "$project": {
                        "handle": 1,
                        "days": 1,
                        "topScores": {"$slice": ["$scores", slice_limit]}
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "handle": 1,
                        "nodes": {"$concat": [{"$toString": "$days"}, "d"]},
                        "altitude": "",
                        "score": {"$sum": "$topScores"}
                    }
                },
                {"$sort": {"score": -1}},
                {"$limit": 50}
            ]
            entries = list(runs_col.aggregate(pipeline))
            if entries:
                return {"tier": tier, "entries": entries}
    except Exception as e:
        print(f"MongoDB get_leaderboard fallback: {e}")

    # Local fallback
    records = []
    if os.path.exists(LOCAL_RUNS_FILE):
        try:
            with open(LOCAL_RUNS_FILE, "r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception:
            records = []

    if tier == "daily":
        day_runs = [r for r in records if r.get("dateKey") == keys["dateKey"]]
        day_runs.sort(
            key=lambda x: (x.get("score", 0), x.get("nodesCompleted", 0), x.get("altitudeMeters", 0)),
            reverse=True
        )
        return {
            "tier": tier,
            "dateKey": keys["dateKey"],
            "entries": [
                {
                    "handle": r.get("handle", "Climber"),
                    "nodes": r.get("nodesCompleted", 0),
                    "altitude": r.get("altitudeMeters", 0),
                    "score": r.get("score", 0)
                }
                for r in day_runs[:50]
            ]
        }

    target_key = "weekKey" if tier == "weekly" else "monthKey"
    target_val = keys[target_key]
    slice_limit = 5 if tier == "weekly" else 20
    by_player = {}
    for r in records:
        if r.get(target_key) == target_val:
            tok = r.get("deviceToken")
            if tok not in by_player:
                by_player[tok] = {"handle": r.get("handle", "Climber"), "scores": []}
            by_player[tok]["scores"].append(r.get("score", 0))

    entries = []
    for tok, pdata in by_player.items():
        top = sorted(pdata["scores"], reverse=True)[:slice_limit]
        entries.append({
            "handle": pdata["handle"],
            "nodes": f"{len(top)}d",
            "altitude": "",
            "score": sum(top)
        })
    entries.sort(key=lambda x: x["score"], reverse=True)
    return {"tier": tier, "entries": entries[:50]}
