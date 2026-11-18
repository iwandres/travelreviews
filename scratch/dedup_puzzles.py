import os
import json

db_files = [
    'c:/Users/iwand/.antigravity/Projects/PunFiction/backend/travelreviews_daily_games.json',
    'c:/Users/iwand/.antigravity/Projects/PunFiction-TravelReviews/backend/travelreviews_daily_games.json'
]

for file_path in db_files:
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            puzzles = json.load(f)
        
        # Sort scheduled puzzles by puzzle_number
        scheduled = [p for p in puzzles if p.get('puzzle_number')]
        scheduled.sort(key=lambda x: int(x['puzzle_number']) if str(x['puzzle_number']).isdigit() else 999)
        
        seen = set()
        changed = False
        for p in scheduled:
            orig = p.get('boss_original_title', '').strip().lower()
            if orig in seen:
                print(f"Duplicate found: {p['boss_pun_title']} (original: {p['boss_original_title']}) currently scheduled as {p['puzzle_number']}. Moving to backlog.")
                p['puzzle_number'] = ''
                changed = True
            else:
                seen.add(orig)
        
        if changed:
            # Resequence scheduled puzzles in order of their original puzzle_numbers
            active_puzzles = [p for p in puzzles if p.get('puzzle_number')]
            active_puzzles.sort(key=lambda x: int(x['puzzle_number']) if str(x['puzzle_number']).isdigit() else 999)
            
            backlog_puzzles = [p for p in puzzles if not p.get('puzzle_number')]
            
            for idx, p in enumerate(active_puzzles):
                p['puzzle_number'] = f"{idx + 1:03d}"
                
            puzzles = active_puzzles + backlog_puzzles
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(puzzles, f, indent=4)
            print(f"Successfully updated and re-sequenced {file_path}. Total active puzzles: {len(active_puzzles)}")
