import http.server
import socketserver
import json
import os
import random
import time
import urllib.request
import urllib.parse
import io
import subprocess
import sys

# Import database wrappers
import database as boxoffice_database
import travelreviews_database as travelreviews_database

PORT = int(os.environ.get("PORT", 8000))
DIR_PATH = os.path.dirname(os.path.realpath(__file__))
PROJECT_ROOT = os.path.dirname(DIR_PATH)
PARENT_DIR = os.path.dirname(PROJECT_ROOT)

# Determine paths for Box Office repository (dynamic resolution)
boxoffice_root = os.path.abspath(os.path.join(PARENT_DIR, 'PunFiction-BoxOffice'))
if not os.path.exists(boxoffice_root):
    boxoffice_root = PROJECT_ROOT

boxoffice_backend = os.path.join(boxoffice_root, 'backend')
if not os.path.exists(boxoffice_backend):
    boxoffice_backend = DIR_PATH

# Determine paths for Travel Reviews repository (dynamic resolution)
travelreviews_root = os.path.abspath(os.path.join(PARENT_DIR, 'PunFiction-TravelReviews'))
if not os.path.exists(travelreviews_root):
    travelreviews_root = PROJECT_ROOT

travelreviews_backend = os.path.join(travelreviews_root, 'backend')
if not os.path.exists(travelreviews_backend):
    travelreviews_backend = DIR_PATH

# Add both backend directories to sys.path to ensure imports work regardless of CWD
if travelreviews_backend not in sys.path:
    sys.path.insert(0, travelreviews_backend)
if boxoffice_backend not in sys.path:
    sys.path.insert(0, boxoffice_backend)

# File paths - Box Office
BOXOFFICE_PUZZLES_FILE = os.path.join(boxoffice_backend, 'production_daily_games.json')
BOXOFFICE_QUOTES_FILE = os.path.join(boxoffice_backend, 'phase2_quotes.json')
BOXOFFICE_INCOMPLETE_FILE = os.path.join(boxoffice_backend, 'incomplete_quotes.json')
BOXOFFICE_PUNNED_FILE = os.path.join(boxoffice_backend, 'punned_quotes.json')
BOXOFFICE_REVIEWED_FILE = os.path.join(boxoffice_backend, 'reviewed_parodies.json')
BOXOFFICE_POSTERS_FILE = os.path.join(boxoffice_backend, 'poster_prompts_state.json')
BOXOFFICE_RECORDS_FILE = os.path.join(boxoffice_backend, 'records.json')

# File paths - 1-Star Travel Reviews
CLUES_FILE = os.path.join(travelreviews_backend, 'travelreviews_clues.json')
POSTCARDS_FILE = os.path.join(travelreviews_backend, 'travelreviews_postcards.json')
DAILY_GAMES_FILE = os.path.join(travelreviews_backend, 'travelreviews_daily_games.json')
LANDMARKS_FILE = os.path.join(travelreviews_backend, 'travelreviews_landmarks.json')

LANDMARK_THEME_MAPPING = {
    # Ancient Ruins & Archaeological Sites
    "Colosseum": "ancient_ruins",
    "Pyramids of Giza": "ancient_ruins",
    "Petra": "ancient_ruins",
    "Chichen Itza": "ancient_ruins",
    "Angkor Wat": "ancient_ruins",
    "Machu Picchu": "ancient_ruins",
    "Pantheon": "ancient_ruins",
    "Roman Forum": "ancient_ruins",
    "Stonehenge": "ancient_ruins",

    # Natural Wonders & Landscapes
    "Grand Canyon": "natural_wonders",
    "Great Barrier Reef": "natural_wonders",
    "Yellowstone National Park": "natural_wonders",
    "Loch Ness": "natural_wonders",
    "Black Forest": "natural_wonders",
    "Matterhorn": "natural_wonders",
    "Cliffs of Moher": "natural_wonders",
    "Giant's Causeway": "natural_wonders",

    # Historic Towers, Monuments & Statues
    "Eiffel Tower": "historic_monuments",
    "Taj Mahal": "historic_monuments",
    "Christ the Redeemer": "historic_monuments",
    "Big Ben": "historic_monuments",
    "Leaning Tower of Pisa": "historic_monuments",
    "Atomium": "historic_monuments",

    # Castles, Fortresses & Cathedrals
    "Tower of London": "castles_cathedrals",
    "Edinburgh Castle": "castles_cathedrals",
    "Mont Saint-Michel": "castles_cathedrals",
    "Sagrada Família": "castles_cathedrals",
    "St. Peter's Basilica": "castles_cathedrals",
    "Notre-Dame Cathedral": "castles_cathedrals",
    "Alcatraz Island": "castles_cathedrals",

    # Bridges, Canals & Historic Engineering
    "Great Wall of China": "bridges_canals",
    "Golden Gate Bridge": "bridges_canals",
    "Panama Canal": "bridges_canals",
    "Tower Bridge": "bridges_canals",
    "Grand Canal": "bridges_canals",

    # Famous Streets, Squares & Towns
    "Times Square": "streets_squares",
    "Spanish Steps": "streets_squares",
    "La Rambla": "streets_squares",
    "Santorini": "streets_squares",

    # Modern Skyscrapers & Tall Structures
    "Burj Khalifa": "modern_skyscrapers",
    "Empire State Building": "modern_skyscrapers",
    "Space Needle": "modern_skyscrapers"
}

def get_theme_for_landmark(landmark_name):
    if not landmark_name:
        return "historic_monuments"
    name = landmark_name.strip()
    return LANDMARK_THEME_MAPPING.get(name, "historic_monuments")
PUNS_FILE = os.path.join(travelreviews_backend, 'travelreviews_puns.json')
TRAVELREVIEWS_RECORDS_FILE = os.path.join(travelreviews_backend, 'travelreviews_records.json')

if os.path.exists(os.path.join(travelreviews_root, 'travelreviews')):
    CARTOONS_DIR = os.path.join(travelreviews_root, 'travelreviews', 'assets', 'cartoons')
else:
    CARTOONS_DIR = os.path.join(travelreviews_root, 'assets', 'cartoons')
os.makedirs(CARTOONS_DIR, exist_ok=True)
UNIFIED_HTML_FILE = os.path.join(DIR_PATH, 'unified_admin.html')

# Initialize Gemini API
gemini_key = os.environ.get("GEMINI_API_KEY")
gemini_available = False
if gemini_key:
    try:
        from google import genai
        from google.genai import types
        gemini_available = True
        print("Gemini API Client initialized successfully.")
    except Exception as e:
        print(f"Failed to import/initialize genai client: {e}")
else:
    print("WARNING: GEMINI_API_KEY environment variable is not set. Generation APIs will fail.")

def load_json(filepath, default_val=None):
    if default_val is None:
        default_val = []
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
    return default_val

def sanitize_travelreviews_puzzles(puzzles):
    if not isinstance(puzzles, list):
        return puzzles
    # Sort scheduled puzzles by puzzle_number
    scheduled = [p for p in puzzles if p.get('puzzle_number')]
    scheduled.sort(key=lambda x: int(x['puzzle_number']) if str(x['puzzle_number']).isdigit() else 999)
    
    seen = set()
    changed = False
    for p in scheduled:
        orig = p.get('boss_original_title', '').strip().lower()
        if orig in seen:
            p['puzzle_number'] = ''
            changed = True
        else:
            seen.add(orig)
            
    if changed:
        # Resequence scheduled puzzles
        active_puzzles = [p for p in puzzles if p.get('puzzle_number')]
        active_puzzles.sort(key=lambda x: int(x['puzzle_number']) if str(x['puzzle_number']).isdigit() else 999)
        
        backlog_puzzles = [p for p in puzzles if not p.get('puzzle_number')]
        
        for idx, p in enumerate(active_puzzles):
            p['puzzle_number'] = f"{idx + 1:03d}"
            
        puzzles = active_puzzles + backlog_puzzles
    return puzzles

def save_json(filepath, data):
    try:
        # Write to the primary file path first
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        # Mirror to the other repository's backend directory if applicable
        filename = os.path.basename(filepath)
        primary_dir = os.path.abspath(os.path.dirname(filepath))
        
        # If we are saving in travelreviews_backend, mirror to boxoffice_backend
        if primary_dir == os.path.abspath(travelreviews_backend) and boxoffice_backend != travelreviews_backend:
            mirror_path = os.path.join(boxoffice_backend, filename)
            try:
                with open(mirror_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                print(f"Mirrored save of {filename} to Box Office repository backend.")
            except Exception as e:
                print(f"Failed to mirror {filename} to Box Office: {e}")
                
        # If we are saving in boxoffice_backend, mirror to travelreviews_backend
        elif primary_dir == os.path.abspath(boxoffice_backend) and boxoffice_backend != travelreviews_backend:
            mirror_path = os.path.join(travelreviews_backend, filename)
            try:
                with open(mirror_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                print(f"Mirrored save of {filename} to Travel Reviews repository backend.")
            except Exception as e:
                print(f"Failed to mirror {filename} to Travel Reviews: {e}")
                
        return True
    except Exception as e:
        print(f"Error saving {filepath}: {e}")
        return False

class UnifiedRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def is_travelreviews_context(self, req_path):
        """Determine if request is for 1-Star Travel Reviews based on prefix or Referer header."""
        if '/travelreviews/' in req_path:
            return True
        referer = self.headers.get('Referer', '')
        if '/travelreviews/' in referer:
            return True
        return False

    def do_GET(self):
        req_path = self.path.split('?')[0]
        
        # 1. Admin Page
        if req_path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            with open(UNIFIED_HTML_FILE, 'rb') as f:
                self.wfile.write(f.read())
            return

        # 2. Unified File Router based on paths
        is_tt = self.is_travelreviews_context(req_path)
        
        # --- Shared APIs (puzzles, records, user) ---
        if req_path in ['/api/puzzles', '/api/boxoffice/puzzles', '/api/travelreviews/puzzles']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            file = DAILY_GAMES_FILE if (is_tt or 'travelreviews' in req_path) else BOXOFFICE_PUZZLES_FILE
            data = load_json(file, [])
            self.wfile.write(json.dumps(data).encode('utf-8'))
            return
            
        elif req_path in ['/api/records', '/api/boxoffice/records', '/api/travelreviews/records']:
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            puzzle_number = query_params.get('puzzle_number', [None])[0]
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            use_tt_db = is_tt or 'travelreviews' in req_path
            db_module = travelreviews_database if use_tt_db else boxoffice_database
            rec_file = TRAVELREVIEWS_RECORDS_FILE if use_tt_db else BOXOFFICE_RECORDS_FILE
            
            try:
                if puzzle_number:
                    stats = db_module.get_telemetry_stats(puzzle_number)
                else:
                    stats = db_module.get_telemetry_stats()
                    save_json(rec_file, stats)
                self.wfile.write(json.dumps(stats).encode('utf-8'))
            except Exception as e:
                print(f"Database error: {e}, falling back to local file")
                telemetry = load_json(rec_file, {})
                if puzzle_number:
                    self.wfile.write(json.dumps(telemetry.get(puzzle_number, {
                        "start": 0, "attempts": 0, "solve_0": 0, "solve_1": 0, "solve_2": 0, "solve_3": 0, "solve_4": 0,
                        "solve_att_1": 0, "solve_att_2": 0, "solve_att_3": 0, "solve_att_4": 0, "solve_att_5": 0
                    })).encode('utf-8'))
                else:
                    self.wfile.write(json.dumps(telemetry).encode('utf-8'))
            return
        elif req_path in ['/api/user', '/api/boxoffice/user', '/api/travelreviews/user']:
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            profile_id = query_params.get('profile_id', [None])[0]
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            use_tt_db = is_tt or 'travelreviews' in req_path
            db_module = travelreviews_database if use_tt_db else boxoffice_database
            
            if profile_id:
                try:
                    profile = db_module.get_user_profile(profile_id)
                    if profile:
                        self.wfile.write(json.dumps(profile).encode('utf-8'))
                    else:
                        self.wfile.write(json.dumps({"error": "Profile not found"}).encode('utf-8'))
                except Exception as e:
                    self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            else:
                self.wfile.write(json.dumps({"error": "profile_id is required"}).encode('utf-8'))
            return

        # --- Box Office Specific APIs ---
        elif req_path in ['/api/quotes', '/api/boxoffice/quotes']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(load_json(BOXOFFICE_QUOTES_FILE, [])).encode('utf-8'))
            return
        elif req_path in ['/api/incomplete_quotes', '/api/boxoffice/incomplete_quotes']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(load_json(BOXOFFICE_INCOMPLETE_FILE, [])).encode('utf-8'))
            return
        elif req_path in ['/api/punned_quotes', '/api/boxoffice/punned_quotes']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(load_json(BOXOFFICE_PUNNED_FILE, [])).encode('utf-8'))
            return
        elif req_path in ['/api/reviewed_parodies', '/api/boxoffice/reviewed_parodies']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(load_json(BOXOFFICE_REVIEWED_FILE, [])).encode('utf-8'))
            return
        elif req_path in ['/api/posters_state', '/api/boxoffice/posters_state']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(load_json(BOXOFFICE_POSTERS_FILE, [])).encode('utf-8'))
            return

        # --- 1-Star Travel Reviews Specific APIs ---
        elif req_path in ['/api/landmarks', '/api/travelreviews/landmarks']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(load_json(LANDMARKS_FILE, [])).encode('utf-8'))
            return
        elif req_path in ['/api/puns', '/api/travelreviews/puns']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(load_json(PUNS_FILE, [])).encode('utf-8'))
            return
        elif req_path in ['/api/clues', '/api/travelreviews/clues']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(load_json(CLUES_FILE, [])).encode('utf-8'))
            return
        elif req_path in ['/api/postcards', '/api/travelreviews/postcards']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(load_json(POSTCARDS_FILE, [])).encode('utf-8'))
            return

        # --- Static Assets and Client Files Router ---
        elif req_path.startswith('/travelreviews/') or req_path.startswith('/assets/'):
            clean_path = urllib.parse.unquote(req_path.strip('/'))
            
            # Smart asset directory check
            if req_path.startswith('/assets/'):
                # Try 1-Star Travel Reviews folder first
                file_path_tt = os.path.join(travelreviews_root, 'travelreviews', *clean_path.split('/'))
                file_path_root = os.path.join(travelreviews_root, *clean_path.split('/'))
                if os.path.exists(file_path_tt) and not os.path.isdir(file_path_tt):
                    file_path = file_path_tt
                elif os.path.exists(file_path_root) and not os.path.isdir(file_path_root):
                    file_path = file_path_root
                else:
                    # Fallback to Box Office assets folder
                    file_path_bo_assets = os.path.join(boxoffice_root, *clean_path.split('/'))
                    file_path_bo_backend = os.path.join(boxoffice_backend, *clean_path.split('/'))
                    if os.path.exists(file_path_bo_assets) and not os.path.isdir(file_path_bo_assets):
                        file_path = file_path_bo_assets
                    elif os.path.exists(file_path_bo_backend) and not os.path.isdir(file_path_bo_backend):
                        file_path = file_path_bo_backend
                    else:
                        file_path = os.path.join(DIR_PATH, *clean_path.split('/'))
            else:
                # Regular travelreviews files
                parts = clean_path.split('/')
                if parts and parts[0] == 'travelreviews' and not os.path.exists(os.path.join(travelreviews_root, 'travelreviews')):
                    parts = parts[1:]
                file_path = os.path.join(travelreviews_root, *parts)
                
            if os.path.exists(file_path) and not os.path.isdir(file_path):
                self.send_response(200)
                if file_path.endswith('.html'):
                    self.send_header('Content-type', 'text/html')
                elif file_path.endswith('.js'):
                    self.send_header('Content-type', 'application/javascript')
                elif file_path.endswith('.css'):
                    self.send_header('Content-type', 'text/css')
                elif file_path.endswith('.png'):
                    self.send_header('Content-type', 'image/png')
                elif file_path.endswith('.webp'):
                    self.send_header('Content-type', 'image/webp')
                elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
                    self.send_header('Content-type', 'image/jpeg')
                self.end_headers()
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404)
            return

        else:
            # Let standard SimpleHTTPRequestHandler handle other static content (like Box Office client)
            super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        req_path = self.path.split('?')[0]
        
        is_tt = self.is_travelreviews_context(req_path)
        
        # --- Shared POST Save APIs ---
        if req_path in ['/api/puzzles', '/api/boxoffice/puzzles', '/api/travelreviews/puzzles']:
            file = DAILY_GAMES_FILE if (is_tt or 'travelreviews' in req_path) else BOXOFFICE_PUZZLES_FILE
            try:
                data = json.loads(post_data.decode('utf-8'))
                if file == DAILY_GAMES_FILE and isinstance(data, list):
                    data = sanitize_travelreviews_puzzles(data)
                save_json(file, data)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return
            
        elif req_path in ['/api/records', '/api/boxoffice/records', '/api/travelreviews/records']:
            use_tt_db = is_tt or 'travelreviews' in req_path
            db_module = travelreviews_database if use_tt_db else boxoffice_database
            rec_file = TRAVELREVIEWS_RECORDS_FILE if use_tt_db else BOXOFFICE_RECORDS_FILE
            
            try:
                payload = json.loads(post_data.decode('utf-8'))
                event = payload.get('event')
                puzzle_number = payload.get('puzzle_number')
                hints_used = int(payload.get('hints_used', 0))
                attempts = int(payload.get('attempts', 1))
                
                if not puzzle_number:
                    raise ValueError("puzzle_number is required")
                
                db_success = True
                try:
                    db_module.record_telemetry_event(puzzle_number, event, hints_used, attempts)
                    # Sync copy
                    try:
                        all_stats = db_module.get_telemetry_stats()
                        save_json(rec_file, all_stats)
                    except Exception as sync_e:
                        print(f"Error syncing local telemetry: {sync_e}")
                except Exception as db_e:
                    print(f"Database write failed, writing locally. Error: {db_e}")
                    db_success = False
                    
                    # Local fallback update
                    telemetry_data = load_json(rec_file, {})
                    if puzzle_number not in telemetry_data:
                        telemetry_data[puzzle_number] = {
                            "start": 0, "attempts": 0, "solve_0": 0, "solve_1": 0, "solve_2": 0, "solve_3": 0, "solve_4": 0,
                            "solve_att_1": 0, "solve_att_2": 0, "solve_att_3": 0, "solve_att_4": 0, "solve_att_5": 0,
                            "click_profile": 0, "click_stats": 0, "click_help": 0, "challenge_view": 0
                        }
                    if event == 'start':
                        telemetry_data[puzzle_number]["start"] += 1
                    elif event == 'attempt':
                        telemetry_data[puzzle_number]["attempts"] += 1
                    elif event == 'solve':
                        clamped_hints = max(0, min(4, int(hints_used)))
                        telemetry_data[puzzle_number][f"solve_{clamped_hints}"] += 1
                        clamped_attempts = max(1, min(5, attempts))
                        telemetry_data[puzzle_number][f"solve_att_{clamped_attempts}"] = telemetry_data[puzzle_number].get(f"solve_att_{clamped_attempts}", 0) + 1
                    elif event in ['click_profile', 'click_stats', 'click_help', 'challenge_view']:
                        telemetry_data[puzzle_number][event] = telemetry_data[puzzle_number].get(event, 0) + 1
                    save_json(rec_file, telemetry_data)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "db_connected": db_success}).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return
            
        elif req_path in ['/api/user', '/api/boxoffice/user', '/api/travelreviews/user']:
            use_tt_db = is_tt or 'travelreviews' in req_path
            db_module = travelreviews_database if use_tt_db else boxoffice_database
            
            try:
                payload = json.loads(post_data.decode('utf-8'))
                profile_id = payload.get('profile_id')
                solved_puzzles = payload.get('solved_puzzles', [])
                solved_hints = payload.get('solved_hints', {})
                attempted_puzzles = payload.get('attempted_puzzles', [])
                max_streak = int(payload.get('max_streak', 0))
                
                if not profile_id:
                    raise ValueError("profile_id is required")
                
                success = db_module.upsert_user_profile(
                    profile_id, solved_puzzles, solved_hints, attempted_puzzles, max_streak
                )
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": success}).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return

        # --- Box Office Specific POST Save APIs ---
        elif req_path in ['/api/quotes', '/api/boxoffice/quotes']:
            try:
                data = json.loads(post_data.decode('utf-8'))
                save_json(BOXOFFICE_QUOTES_FILE, data)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return
        elif req_path in ['/api/incomplete_quotes', '/api/boxoffice/incomplete_quotes']:
            try:
                data = json.loads(post_data.decode('utf-8'))
                save_json(BOXOFFICE_INCOMPLETE_FILE, data)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return
        elif req_path in ['/api/punned_quotes', '/api/boxoffice/punned_quotes']:
            try:
                data = json.loads(post_data.decode('utf-8'))
                save_json(BOXOFFICE_PUNNED_FILE, data)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return
        elif req_path in ['/api/reviewed_parodies', '/api/boxoffice/reviewed_parodies']:
            try:
                data = json.loads(post_data.decode('utf-8'))
                save_json(BOXOFFICE_REVIEWED_FILE, data)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return
        elif req_path in ['/api/posters_state', '/api/boxoffice/posters_state']:
            try:
                new_data = json.loads(post_data.decode('utf-8'))
                if os.path.exists(BOXOFFICE_POSTERS_FILE):
                    old_data = load_json(BOXOFFICE_POSTERS_FILE, [])
                    old_dict = {item['pun_id']: item for item in old_data}
                    for item in new_data:
                        if item.get('status') == 'rejected':
                            old_item = old_dict.get(item['pun_id'])
                            if old_item and old_item.get('image_path'):
                                old_path = old_item['image_path']
                                if old_path and old_path.startswith('/assets/'):
                                    clean_path = urllib.parse.unquote(old_path.strip('/'))
                                    file_to_delete_bo = os.path.join(boxoffice_backend, *clean_path.split('/'))
                                    file_to_delete_root = os.path.join(boxoffice_root, *clean_path.split('/'))
                                    file_to_delete = file_to_delete_bo if os.path.exists(file_to_delete_bo) else file_to_delete_root
                                    if os.path.exists(file_to_delete):
                                        try:
                                            os.remove(file_to_delete)
                                            print(f"Deleted Box Office rejected poster: {file_to_delete}")
                                        except Exception as delete_e:
                                            print(f"Failed to delete {file_to_delete}: {delete_e}")
                save_json(BOXOFFICE_POSTERS_FILE, new_data)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return

        # --- Box Office Generator Scripts ---
        elif req_path in ['/api/generate_parodies', '/api/boxoffice/generate_parodies']:
            try:
                script_path = os.path.join(boxoffice_backend, 'thematic_generator.py')
                print(f"Running Box Office Parodies generator: {script_path}")
                result = subprocess.run([sys.executable, script_path], cwd=boxoffice_backend, capture_output=True, text=True)
                print("Generator output:", result.stdout)
                if result.returncode != 0:
                    raise Exception(result.stderr)
                count = 0
                for line in result.stdout.split('\n'):
                    if "Successfully generated" in line:
                        try:
                            count = int(line.split()[-2])
                        except:
                            pass
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "generated_count": count or 5}).encode('utf-8'))
            except Exception as e:
                print(f"Error running generate_parodies: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return
        elif req_path in ['/api/generate_posters', '/api/boxoffice/generate_posters']:
            try:
                script_path = os.path.join(boxoffice_backend, 'generate_posters.py')
                print(f"Running Box Office Posters generator: {script_path}")
                result = subprocess.run([sys.executable, script_path], cwd=boxoffice_backend, capture_output=True, text=True)
                print("Generator output:", result.stdout)
                if result.returncode != 0:
                    raise Exception(result.stderr)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "generated_count": 5}).encode('utf-8'))
            except Exception as e:
                print(f"Error running generate_posters: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return

        # --- 1-Star Travel Reviews Specific POST Save APIs ---
        elif req_path in ['/api/landmarks', '/api/travelreviews/landmarks']:
            try:
                data = json.loads(post_data.decode('utf-8'))
                save_json(LANDMARKS_FILE, data)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return
        elif req_path in ['/api/puns', '/api/travelreviews/puns']:
            try:
                data = json.loads(post_data.decode('utf-8'))
                save_json(PUNS_FILE, data)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return
        elif req_path in ['/api/clues', '/api/travelreviews/clues']:
            try:
                data = json.loads(post_data.decode('utf-8'))
                save_json(CLUES_FILE, data)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return
        elif req_path in ['/api/postcards', '/api/travelreviews/postcards']:
            try:
                data = json.loads(post_data.decode('utf-8'))
                if os.path.exists(POSTCARDS_FILE):
                    old_data = load_json(POSTCARDS_FILE, [])
                    old_dict = {item['id']: item for item in old_data}
                    new_ids = {item['id'] for item in data}
                    for item in old_data:
                        if item['id'] not in new_ids or next((x for x in data if x['id'] == item['id']), {}).get('status') == 'rejected':
                            img_path = item.get('image_path')
                            if img_path and img_path.startswith('/assets/'):
                                clean_path = urllib.parse.unquote(img_path.strip('/'))
                                if os.path.exists(os.path.join(travelreviews_root, 'travelreviews')):
                                    file_to_delete = os.path.join(travelreviews_root, 'travelreviews', *clean_path.split('/'))
                                else:
                                    file_to_delete = os.path.join(travelreviews_root, *clean_path.split('/'))
                                if os.path.exists(file_to_delete):
                                    try:
                                        os.remove(file_to_delete)
                                        print(f"Deleted 1-Star Travel Reviews rejected/removed image: {file_to_delete}")
                                    except Exception as delete_e:
                                        print(f"Failed to delete {file_to_delete}: {delete_e}")
                                        
                                # Also delete copy from Box Office repository if different
                                if boxoffice_root != travelreviews_root:
                                    if os.path.exists(os.path.join(boxoffice_root, 'travelreviews')):
                                        bo_file_to_delete = os.path.join(boxoffice_root, 'travelreviews', *clean_path.split('/'))
                                    else:
                                        bo_file_to_delete = os.path.join(boxoffice_root, *clean_path.split('/'))
                                    if os.path.exists(bo_file_to_delete):
                                        try:
                                            os.remove(bo_file_to_delete)
                                            print(f"Deleted 1-Star Travel Reviews rejected/removed image copy from Box Office: {bo_file_to_delete}")
                                        except Exception as bo_delete_e:
                                            print(f"Failed to delete Box Office copy {bo_file_to_delete}: {bo_delete_e}")
                save_json(POSTCARDS_FILE, data)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return

        # --- 1-Star Travel Reviews Gemini Inline Generation Routines ---
        elif req_path in ['/api/generate_puns', '/api/travelreviews/generate_puns']:
            if not gemini_available:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "GEMINI_API_KEY environment variable missing"}).encode('utf-8'))
                return
                
            try:
                landmarks = load_json(LANDMARKS_FILE, [])
                puns = load_json(PUNS_FILE, [])
                approved_landmarks = [lm for lm in landmarks if lm.get('status') == 'approved']
                existing_puns_landmarks = {p['original_name'] for p in puns}
                new_landmarks = [lm for lm in approved_landmarks if lm['name'] not in existing_puns_landmarks]
                
                if not new_landmarks:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": True, "generated_count": 0, "message": "No new approved landmarks to process"}).encode('utf-8'))
                    return
                
                client = genai.Client(api_key=gemini_key)
                new_puns_count = 0
                for lm in new_landmarks[:5]:
                    prompt = f"""
                    Create a list of 2-3 funny, clever wordplay puns based on the famous historical landmark or travel destination "{lm['name']}" (located in {lm.get('location', 'Unknown')}).
                    A location pun should sound very similar to the original name but replace parts of it with a funny word (e.g. Waffle Tower instead of Eiffel Tower, Lover Museum instead of Louvre Museum, St. Peter's Bazooka instead of St. Peter's Basilica).
                    
                    Return a JSON array of strings exactly matching this schema:
                    [
                      "Pun Name 1",
                      "Pun Name 2"
                    ]
                    """
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json"
                        )
                    )
                    pun_candidates = json.loads(response.text)
                    # Reload the latest puns list from disk to avoid overwriting concurrent edits
                    puns = load_json(PUNS_FILE, [])
                    for candidate in pun_candidates:
                        puns.append({
                            "id": f"pun_{lm['name'].lower().replace(' ', '_')}_{int(time.time())}_{random.randint(100,999)}",
                            "original_name": lm['name'],
                            "location": lm.get('location', 'Unknown'),
                            "pun_name": candidate,
                            "status": "pending"
                        })
                        new_puns_count += 1
                    save_json(PUNS_FILE, puns)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "generated_count": new_puns_count}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return
            
        elif req_path in ['/api/generate_clues', '/api/travelreviews/generate_clues']:
            if not gemini_available:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "GEMINI_API_KEY environment variable missing"}).encode('utf-8'))
                return
                
            try:
                puns = load_json(PUNS_FILE, [])
                clues = load_json(CLUES_FILE, [])
                approved_puns = [p for p in puns if p.get('status') == 'approved']
                existing_clues_puns = {c['pun_name'] for c in clues}
                new_puns = [p for p in approved_puns if p['pun_name'] not in existing_clues_puns]
                
                if not new_puns:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": True, "generated_count": 0, "message": "No new approved puns to process"}).encode('utf-8'))
                    return
                
                client = genai.Client(api_key=gemini_key)
                new_clues_count = 0
                for p in new_puns[:5]:
                    prompt = f"""
                    We are building a comedy travel puzzle game. 
                    The player needs to guess a location pun.
                    The target location pun name is: "{p['pun_name']}" (which is a pun on the real landmark "{p['original_name']}").
                    
                    Your job is to generate 3 progressive clues (reviews) complaining about this location in an unhinged, comedic way.
                    CRITICAL CONSTRAINT: Each clue MUST be a very short snippet, phrase, or sentence fragment (under 12-15 words). You can use sentence fragments noted/separated using '...' or similar punctuation (e.g., 'So drafty... holes everywhere... completely non-functional!'). Do NOT write long paragraphs or multiple full sentences.
                    - Clue 1: An absurd, comical snippet or sentence fragment that includes a subtle, clever hint referencing both the original landmark/location and the wordplay of the pun, giving players a fair chance to solve the puzzle on the very first clue.
                    - Clue 2: Another short comical snippet or sentence fragment providing additional details/hints about either the original landmark's actual features/location or the wordplay behind the pun.
                    - Clue 3: A final short comical snippet or sentence fragment that makes the connection between the original landmark and the pun name very obvious (without explicitly naming either).
                    
                    Also generate a funny review title.
                    Also generate a funny Reviewer Username (reviewer_name) that is thematically related to the parodied location or the complaint (e.g., 'SyrupSlinger' for Waffle Tower, 'SoggySouffle' for Eiffel Shower, 'BitterSingle' for Lover Museum). Do not include the '@' symbol in the JSON value.
                    
                    Also generate a 'Response from the Owner' (flavor text reply from management).
                    CRITICAL: The Owner's POV is the manager of the ACTUAL historical landmark (e.g. the Eiffel Tower, the Louvre Museum, etc.). You are responding to a ridiculous 1-star TripAdvisor review from a traveler who has confused your actual historical landmark with a silly, literal pun name (e.g., Eiffel Towel, Waffle Tower, Lover Museum).
                    The response must be short (under 2 sentences), highly sarcastic, and punchy, correcting the reviewer's absurd confusion by pointing out the actual nature of your landmark (e.g. that it is a 300-meter iron monument, a fine art museum, etc.) and why their complaint makes no sense.
                    To bolster the response and make it highly contextual, the owner can directly reference a specific notable complaint or mistake made by the reviewer in the clues (e.g., trying to dry off with wrought iron, complaining about square indentations or wanting maple syrup on the girders). Do NOT mention the original landmark name in the response itself.
                    The owner should occasionally reference the reviewer's username (reviewer_name) directly in their reply prefixed with '@' (e.g. 'Listen here, @DampCroissant...', 'Dear @DampCroissant...'), but vary it sometimes with general greetings like 'Dear Traveler' or 'Dear Adventurer'.
                    Example of the tone:
                    Actual Landmark: Eiffel Tower
                    Pun Name: Eiffel Towel
                    Reviewer Username: DampCroissant
                    Reviewer Complaint: "Too drafty... holes everywhere... tried to dry off after my shower but it's made of wrought iron!"
                    Response from the Owner: "Listen, @DampCroissant, if you are using 10,000 tons of 19th-century iron to dry your hair, you have significantly bigger problems than a slight draft."
                    
                    Return a JSON object matching exactly this schema:
                    {{
                      "reviewer_name": "Username",
                      "review_title": "Avoid at all costs!",
                      "clue1": "Clue 1 text",
                      "clue2": "Clue 2 text",
                      "clue3": "Clue 3 text",
                      "owner_response": "Owner response here",
                      "page_theme": "The most appropriate travel theme name for this location out of: ancient_ruins, natural_wonders, historic_monuments, castles_cathedrals, bridges_canals, streets_squares, modern_skyscrapers"
                    }}
                    """
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json"
                        )
                    )
                    generated = json.loads(response.text)
                    # Reload the latest clues list from disk to avoid overwriting concurrent edits
                    clues = load_json(CLUES_FILE, [])
                    clues.append({
                        "id": f"clue_{p['pun_name'].lower().replace(' ', '_')}_{int(time.time())}",
                        "original_name": p['original_name'],
                        "pun_name": p['pun_name'],
                        "reviewer_name": generated.get("reviewer_name", "Anonymous"),
                        "review_title": generated.get("review_title", "Terrible!"),
                        "clue1": generated.get("clue1", ""),
                        "clue2": generated.get("clue2", ""),
                        "clue3": generated.get("clue3", ""),
                        "owner_response": generated.get("owner_response", ""),
                        "page_theme": get_theme_for_landmark(p['original_name']),
                        "status": "pending"
                    })
                    new_clues_count += 1
                    save_json(CLUES_FILE, clues)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "generated_count": new_clues_count}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return
            
        elif req_path in ['/api/generate_postcards', '/api/travelreviews/generate_postcards']:
            if not gemini_available:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "GEMINI_API_KEY environment variable missing"}).encode('utf-8'))
                return
                
            try:
                payload = {}
                try:
                    payload = json.loads(post_data.decode('utf-8'))
                except:
                    pass
                selected_style = payload.get('art_style', 'random')
                
                styles_dict = {
                    "cartoon": "Comical cartoon illustration, bold lines, bright vibrant colors, humorous caricature, white postcard border.",
                    "watercolor": "Whimsical watercolor and ink sketch, detailed storybook style, soft textures, pastel colors, artistically detailed.",
                    "retro": "Vintage 1950s travel poster style, retro flat vector design, bold colors, screen-printed poster aesthetic.",
                    "wpa": "Old school vintage travel illustration style, rooted in 1930s WPA-era silk-screened travel posters and 1960s lithographs, featuring bold shapes, muted earthy color palettes, and hand-drawn typography.",
                    "vintage": "Classic distressed linen texture vintage postcard style, hand-colored photo print aesthetic, 1930s travel style.",
                    "pop-art": "Vibrant Pop Art style, bold outlines, screen print dot texture, retro comic book feel, high contrast colors."
                }
                
                clues = load_json(CLUES_FILE, [])
                postcards = load_json(POSTCARDS_FILE, [])
                target_clue_id = payload.get('clue_id')
                
                if target_clue_id:
                    approved_clues = [c for c in clues if c['id'] == target_clue_id]
                    if not approved_clues:
                        # Fallback to constructing a temporary clue object from postcards if clue has been cleaned up/deleted
                        fallback_pc = next((p for p in postcards if p['clue_id'] == target_clue_id), None)
                        if fallback_pc:
                            approved_clues = [{
                                'id': fallback_pc['clue_id'],
                                'pun_name': fallback_pc['pun_name'],
                                'original_name': fallback_pc['original_name'],
                                'owner_response': fallback_pc['owner_response'],
                                'page_theme': fallback_pc.get('page_theme', 'road_trip'),
                                'status': fallback_pc.get('status', 'pending')
                            }]
                else:
                    existing_clues_in_postcards = {p['clue_id'] for p in postcards}
                    approved_clues = [c for c in clues if c.get('status') == 'approved' and c['id'] not in existing_clues_in_postcards]
                client = genai.Client(api_key=gemini_key)
                new_postcards_count = 0
                for c in approved_clues[:5]:
                    custom_prompt = payload.get('prompt')
                    if custom_prompt:
                        image_prompt = custom_prompt
                        style_prompt = ""
                        style_key = "custom"
                    else:
                        style_key = random.choice(list(styles_dict.keys()))
                        style_prompt = styles_dict[style_key]
                        
                        prompt_gen = f"""
                        Create a single-sentence descriptive text-to-image prompt for a parodied travel postcard based on the location pun "{c['pun_name']}" (derived from "{c['original_name']}").
                        The prompt should describe a funny, comical scene matching this art style: "{style_prompt}".
                        Example for "The Grand Crayon":
                        "A giant yellow crayon laying inside the rocky Grand Canyon, comical cartoon illustration."
                        
                        Return a JSON object exactly matching this schema:
                        {{
                          "image_prompt": "A giant yellow crayon laying inside the rocky Grand Canyon, comical cartoon illustration."
                        }}
                        """
                        prompt_res = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=prompt_gen,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json"
                            )
                        )
                        prompt_data = json.loads(prompt_res.text)
                        image_prompt = prompt_data.get("image_prompt", f"A funny cartoon of {c['pun_name']}, comical illustration.")
                    
                    safe_filename = c['pun_name'].lower().replace(' ', '_').replace('-', '_').replace(':', '') + f"_{int(time.time())}.webp"
                    image_path = f"/assets/cartoons/{safe_filename}"
                    local_image_path = os.path.join(CARTOONS_DIR, safe_filename)
                    
                    print(f"Generating postcard for '{c['pun_name']}' in style '{style_key}' using imagen-4.0-generate-001...")
                    response = client.models.generate_images(
                        model='imagen-4.0-generate-001',
                        prompt=f"{style_prompt} {image_prompt}".strip(),
                        config=types.GenerateImagesConfig(
                            number_of_images=1,
                            output_mime_type="image/png",
                            aspect_ratio="4:3"
                        )
                    )
                    
                    saved_image = False
                    for generated_image in response.generated_images:
                        image_bytes = generated_image.image.image_bytes
                        from PIL import Image
                        image = Image.open(io.BytesIO(image_bytes))
                        image.save(local_image_path, 'WEBP', quality=95)
                        print(f"Saved generated image: {local_image_path}")
                        
                        # Also save copy to Box Office repository if different
                        if boxoffice_root != travelreviews_root:
                            if os.path.exists(os.path.join(boxoffice_root, 'travelreviews')):
                                bo_cartoons_dir = os.path.join(boxoffice_root, 'travelreviews', 'assets', 'cartoons')
                            else:
                                bo_cartoons_dir = os.path.join(boxoffice_root, 'assets', 'cartoons')
                            os.makedirs(bo_cartoons_dir, exist_ok=True)
                            bo_image_path = os.path.join(bo_cartoons_dir, safe_filename)
                            try:
                                image.save(bo_image_path, 'WEBP', quality=95)
                                print(f"Saved generated image copy to Box Office: {bo_image_path}")
                            except Exception as bo_save_e:
                                print(f"Failed to save copy of generated image to Box Office: {bo_save_e}")
                                
                        saved_image = True
                        break
                    if not saved_image:
                        raise Exception("No image returned in response parts from imagen-4.0-generate-001")
                        
                    # Reload the latest postcards list from disk to avoid overwriting concurrent edits
                    postcards = load_json(POSTCARDS_FILE, [])
                    existing_idx = next((i for i, p in enumerate(postcards) if p['clue_id'] == c['id']), None)
                    postcard_entry = {
                        "id": f"postcard_{c['id']}_{int(time.time())}" if existing_idx is None else postcards[existing_idx]["id"],
                        "clue_id": c['id'],
                        "pun_name": c['pun_name'],
                        "original_name": c['original_name'],
                        "image_prompt": image_prompt,
                        "image_path": image_path,
                        "art_style": style_key,
                        "owner_response": c['owner_response'],
                        "page_theme": c.get('page_theme', 'road_trip'),
                        "status": "pending" if existing_idx is None else postcards[existing_idx].get("status", "pending")
                    }
                    
                    if existing_idx is not None:
                        postcards[existing_idx] = postcard_entry
                    else:
                        postcards.append(postcard_entry)
                    new_postcards_count += 1
                    save_json(POSTCARDS_FILE, postcards)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "generated_count": new_postcards_count}).encode('utf-8'))
            except Exception as e:
                print(f"Error generating postcard images: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return
            
        elif req_path in ['/api/regenerate_owner_reply', '/api/travelreviews/regenerate_owner_reply']:
            if not gemini_available:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "GEMINI_API_KEY env variable missing"}).encode('utf-8'))
                return
                
            try:
                payload = {}
                try:
                    payload = json.loads(post_data.decode('utf-8'))
                except:
                    pass
                clue_id = payload.get('clue_id')
                if not clue_id:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": False, "error": "clue_id is required"}).encode('utf-8'))
                    return
                    
                clues = load_json(CLUES_FILE, [])
                postcards = load_json(POSTCARDS_FILE, [])
                
                c = next((cl for cl in clues if cl['id'] == clue_id), None)
                if not c:
                    self.send_response(404)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": False, "error": "Clue not found"}).encode('utf-8'))
                    return
                    
                client = genai.Client(api_key=gemini_key)
                prompt = f"""
                You are the owner/manager of the ACTUAL historical landmark (the real place behind the pun "{c['pun_name']}", which has original landmark features of "{c['original_name']}").
                Your POV is that of the real, actual landmark. You are responding to a ridiculous 1-star TripAdvisor review from a traveler named "{c['reviewer_name']}" who has confused your famous landmark with a silly, literal pun name (the "{c['pun_name']}").
                Complaints:
                - Clue 1: "{c['clue1']}"
                - Clue 2: "{c['clue2']}"
                - Clue 3: "{c['clue3']}"
                
                Write a short (under 2 sentences), highly sarcastic, and punchy owner response correcting the reviewer's absurd confusion by pointing out the actual nature of your landmark (e.g., that it is a giant iron structure, a historic fine art museum, etc.) and why their complaint makes no sense.
                To bolster the response and make it highly contextual, the owner can directly reference a specific notable complaint or mistake made by the reviewer in the clues (e.g. drying hair on iron, eating waffles, complaining about public romance). Do NOT mention the original landmark name in the response itself.
                Reference their username directly in the reply prefixed with '@' (e.g., 'Listen, @{c['reviewer_name']}...', 'Dear @{c['reviewer_name']}...'), or use general terms like 'Dear Adventurer' or 'Dear Traveler' for variation.
                
                Return a JSON object matching exactly this schema:
                {{
                  "owner_response": "Response text here"
                }}
                """
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                data = json.loads(response.text)
                new_reply = data.get('owner_response', '')
                
                c['owner_response'] = new_reply
                save_json(CLUES_FILE, clues)
                
                for p in postcards:
                    if p['clue_id'] == clue_id:
                        p['owner_response'] = new_reply
                save_json(POSTCARDS_FILE, postcards)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "owner_response": new_reply}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return

        else:
            self.send_error(404)

def pipeline_listener():
    import threading
    import time
    
    print("[Pipeline Listener] Background thread started.")
    
    while True:
        # Check environment variable
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_key:
            time.sleep(10)
            continue
            
        try:
            # 1. Puns Generation Curation Cycle
            landmarks = load_json(LANDMARKS_FILE, [])
            puns = load_json(PUNS_FILE, [])
            approved_landmarks = [lm for lm in landmarks if lm.get('status') == 'approved']
            existing_puns_landmarks = {p['original_name'] for p in puns}
            new_landmarks = [lm for lm in approved_landmarks if lm['name'] not in existing_puns_landmarks]
            
            if new_landmarks:
                print(f"[Pipeline Listener] Found {len(new_landmarks)} pending approved landmarks. Generating puns in a batch of 5...")
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=gemini_key)
                new_puns_count = 0
                for lm in new_landmarks[:5]:
                    prompt = f"""
                    Create a list of 2-3 funny, clever wordplay puns based on the famous historical landmark or travel destination "{lm['name']}" (located in {lm.get('location', 'Unknown')}).
                    A location pun should sound very similar to the original name but replace parts of it with a funny word (e.g. Waffle Tower instead of Eiffel Tower, Lover Museum instead of Louvre Museum, St. Peter's Bazooka instead of St. Peter's Basilica).
                    
                    Return a JSON array of strings exactly matching this schema:
                    [
                      "Pun Name 1",
                      "Pun Name 2"
                    ]
                    """
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json"
                        )
                    )
                    pun_candidates = json.loads(response.text)
                    for candidate in pun_candidates:
                        puns.append({
                            "id": f"pun_{lm['name'].lower().replace(' ', '_')}_{int(time.time())}_{random.randint(100,999)}",
                            "original_name": lm['name'],
                            "location": lm.get('location', 'Unknown'),
                            "pun_name": candidate,
                            "status": "pending"
                        })
                        new_puns_count += 1
                save_json(PUNS_FILE, puns)
                print(f"[Pipeline Listener] Successfully generated {new_puns_count} puns.")
                time.sleep(3) # Cool down
                continue # Re-evaluate immediately
                
            # 2. Clues/Reviews Generation Curation Cycle
            puns = load_json(PUNS_FILE, [])
            clues = load_json(CLUES_FILE, [])
            approved_puns = [p for p in puns if p.get('status') == 'approved']
            existing_clues_puns = {c['pun_name'] for c in clues}
            new_puns = [p for p in approved_puns if p['pun_name'] not in existing_clues_puns]
            
            if new_puns:
                print(f"[Pipeline Listener] Found {len(new_puns)} pending approved puns. Generating reviews/clues in a batch of 5...")
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=gemini_key)
                new_clues_count = 0
                for p in new_puns[:5]:
                    prompt = f"""
                    We are building a comedy travel puzzle game. 
                    The player needs to guess a location pun.
                    The target location pun name is: "{p['pun_name']}" (which is a pun on the real landmark "{p['original_name']}").
                    
                    Your job is to generate 3 progressive clues (reviews) complaining about this location in an unhinged, comedic way.
                    CRITICAL CONSTRAINT: Each clue MUST be a very short snippet, phrase, or sentence fragment (under 12-15 words). You can use sentence fragments noted/separated using '...' or similar punctuation (e.g., 'So drafty... holes everywhere... completely non-functional!'). Do NOT write long paragraphs or multiple full sentences.
                    - Clue 1: An absurd, comical snippet or sentence fragment that includes a subtle, clever hint referencing both the geographical/cultural location of the original landmark (e.g. Paris/France for Eiffel Tower) and the wordplay of the pun, giving players a fair chance to solve the puzzle on the very first clue.
                    - Clue 2: Another short comical snippet or sentence fragment providing additional details/hints about either the original landmark's actual features/location or the wordplay behind the pun.
                    - Clue 3: A final short comical snippet or sentence fragment that makes the connection between the original landmark and the pun name very obvious (without explicitly naming either).
                    
                    Also generate a funny review title.
                    Also generate a funny Reviewer Username (reviewer_name) that is thematically related to the parodied location or the complaint (e.g., 'SyrupSlinger' for Waffle Tower, 'SoggySouffle' for Eiffel Shower, 'BitterSingle' for Lover Museum). Do not include the '@' symbol in the JSON value.
                    
                    Also generate a 'Response from the Owner' (flavor text reply from management).
                    CRITICAL: The Owner's POV is the manager of the ACTUAL historical landmark (e.g. the Eiffel Tower, the Louvre Museum, etc.). You are responding to a ridiculous 1-star TripAdvisor review from a traveler who has confused your actual historical landmark with a silly, literal pun name (e.g., Eiffel Towel, Waffle Tower, Lover Museum).
                    The response must be short (under 2 sentences), highly sarcastic, and punchy, correcting the reviewer's absurd confusion by pointing out the actual nature of your landmark (e.g. that it is a 300-meter iron monument, a fine art museum, etc.) and why their complaint makes no sense.
                    To bolster the response and make it highly contextual, the owner can directly reference a specific notable complaint or mistake made by the reviewer in the clues (e.g., trying to dry off with wrought iron, complaining about square indentations or wanting maple syrup on the girders). Do NOT mention the original landmark name in the response itself.
                    The owner should occasionally reference the reviewer's username (reviewer_name) directly in their reply prefixed with '@' (e.g. 'Listen here, @DampCroissant...', 'Dear @DampCroissant...'), but vary it sometimes with general greetings like 'Dear Traveler' or 'Dear Adventurer'.
                    
                    Return a JSON object matching exactly this schema:
                    {{
                      "reviewer_name": "Username",
                      "review_title": "Avoid at all costs!",
                      "clue1": "Clue 1 text",
                      "clue2": "Clue 2 text",
                      "clue3": "Clue 3 text",
                      "owner_response": "Owner response here",
                      "page_theme": "The most appropriate travel theme name for this location out of: ancient_ruins, natural_wonders, historic_monuments, castles_cathedrals, bridges_canals, streets_squares, modern_skyscrapers"
                    }}
                    """
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json"
                        )
                    )
                    generated = json.loads(response.text)
                    clues.append({
                        "id": f"clue_{p['id']}_{int(time.time())}_{random.randint(100,999)}",
                        "pun_id": p['id'],
                        "pun_name": p['pun_name'],
                        "original_name": p['original_name'],
                        "reviewer_name": generated.get("reviewer_name", "Anonymous"),
                        "review_title": generated.get("review_title", "Avoid at all costs!"),
                        "clue1": generated.get("clue1", ""),
                        "clue2": generated.get("clue2", ""),
                        "clue3": generated.get("clue3", ""),
                        "clue4": generated.get("clue4", ""),
                        "owner_response": generated.get("owner_response", ""),
                        "page_theme": get_theme_for_landmark(p['original_name']),
                        "status": "pending"
                    })
                    new_clues_count += 1
                save_json(CLUES_FILE, clues)
                print(f"[Pipeline Listener] Successfully generated {new_clues_count} clues.")
                time.sleep(3) # Cool down
                continue # Re-evaluate immediately
                
        except Exception as e:
            print(f"[Pipeline Listener] Error in generation cycle: {e}")
            
        time.sleep(10) # check every 10 seconds if idle

if __name__ == '__main__':
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    import threading
    t = threading.Thread(target=pipeline_listener, daemon=True)
    t.start()
    with socketserver.ThreadingTCPServer(("", PORT), UnifiedRequestHandler) as httpd:
        print(f"Serving Consolidated Curation Server at http://localhost:{PORT}")
        httpd.serve_forever()

