import os
from datetime import datetime, timezone
from pymongo import MongoClient

# Use the MONGO_URI from the environment, defaulting to localhost for local testing if missing
mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(mongo_uri, serverSelectionTimeoutMS=1500)

db = client["travelreviews_db"]
telemetry_pool = db["PunFiction_TravelReviews"]
user_profiles_pool = db["UserProfiles"]

def record_telemetry_event(puzzle_number, event_type, hints_used=0, attempts=1):
    """Records a telemetry event in the MongoDB collection using atomic increments."""
    update_query = {}
    if event_type == 'start':
        update_query = {"$inc": {"start": 1}}
    elif event_type == 'attempt':
        update_query = {"$inc": {"attempts": 1}}
    elif event_type == 'solve':
        hints_used = max(0, min(4, int(hints_used)))
        clamped_attempts = max(1, min(5, int(attempts)))
        update_query = {
            "$inc": {
                f"solve_{hints_used}": 1,
                f"solve_att_{clamped_attempts}": 1
            }
        }
    elif event_type in ['click_profile', 'click_stats', 'click_help', 'challenge_view']:
        update_query = {"$inc": {event_type: 1}}
        
    if update_query:
        telemetry_pool.update_one(
            {"_id": puzzle_number},
            update_query,
            upsert=True
        )

def get_telemetry_stats(puzzle_number=None):
    """Fetches aggregated telemetry stats from MongoDB."""
    if puzzle_number:
        doc = telemetry_pool.find_one({"_id": puzzle_number})
        if doc:
            return {
                "start": doc.get("start", 0),
                "attempts": doc.get("attempts", 0),
                "solve_0": doc.get("solve_0", 0),
                "solve_1": doc.get("solve_1", 0),
                "solve_2": doc.get("solve_2", 0),
                "solve_3": doc.get("solve_3", 0),
                "solve_4": doc.get("solve_4", 0),
                "solve_att_1": doc.get("solve_att_1", 0),
                "solve_att_2": doc.get("solve_att_2", 0),
                "solve_att_3": doc.get("solve_att_3", 0),
                "solve_att_4": doc.get("solve_att_4", 0),
                "solve_att_5": doc.get("solve_att_5", 0),
                "challenge_view": doc.get("challenge_view", 0)
            }
        else:
            return {
                "start": 0,
                "attempts": 0,
                "solve_0": 0,
                "solve_1": 0,
                "solve_2": 0,
                "solve_3": 0,
                "solve_4": 0,
                "solve_att_1": 0,
                "solve_att_2": 0,
                "solve_att_3": 0,
                "solve_att_4": 0,
                "solve_att_5": 0,
                "challenge_view": 0
            }
    else:
        # Fetch all stats and build mapped dictionary
        all_docs = telemetry_pool.find({})
        stats_map = {}
        for doc in all_docs:
            p_num = doc["_id"]
            stats_map[p_num] = {
                "start": doc.get("start", 0),
                "attempts": doc.get("attempts", 0),
                "solve_0": doc.get("solve_0", 0),
                "solve_1": doc.get("solve_1", 0),
                "solve_2": doc.get("solve_2", 0),
                "solve_3": doc.get("solve_3", 0),
                "solve_4": doc.get("solve_4", 0),
                "solve_att_1": doc.get("solve_att_1", 0),
                "solve_att_2": doc.get("solve_att_2", 0),
                "solve_att_3": doc.get("solve_att_3", 0),
                "solve_att_4": doc.get("solve_att_4", 0),
                "solve_att_5": doc.get("solve_att_5", 0),
                "challenge_view": doc.get("challenge_view", 0)
            }
        return stats_map

def get_user_profile(profile_id):
    """Fetches a user profile from MongoDB by profile_id."""
    try:
        profile = user_profiles_pool.find_one({"_id": profile_id})
        if profile:
            return {
                "profile_id": profile["_id"],
                "solved_puzzles": profile.get("solved_puzzles", []),
                "solved_hints": profile.get("solved_hints", {}),
                "attempted_puzzles": profile.get("attempted_puzzles", []),
                "max_streak": profile.get("max_streak", 0)
            }
    except Exception as e:
        print(f"Error fetching user profile {profile_id}: {e}")
    return None

def upsert_user_profile(profile_id, solved_puzzles, solved_hints, attempted_puzzles, max_streak):
    """Upserts user profile state to MongoDB."""
    try:
        user_profiles_pool.update_one(
            {"_id": profile_id},
            {
                "$set": {
                    "solved_puzzles": solved_puzzles,
                    "solved_hints": solved_hints,
                    "attempted_puzzles": attempted_puzzles,
                    "max_streak": max_streak,
                    "last_updated": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error upserting user profile {profile_id}: {e}")
        return False
