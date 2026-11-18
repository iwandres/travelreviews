import json
import os

def adjust_schedule(filepath):
    print(f"Processing: {filepath}")
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        puzzles = json.load(f)

    # Find Grand Crayon
    grand_crayon = None
    for p in puzzles:
        if p.get('boss_pun_title') == 'Grand Crayon':
            grand_crayon = p
            break

    if not grand_crayon:
        print("Grand Crayon not found in schedule!")
        return

    print(f"Found Grand Crayon currently at puzzle_number: {grand_crayon.get('puzzle_number')}")

    # Remove grand crayon from the active numbering sequence temporarily
    grand_crayon['puzzle_number'] = ''

    # Get all active daily challenges
    active = [p for p in puzzles if p.get('puzzle_number')]
    # Sort them by their current puzzle_number integer values
    active.sort(key=lambda x: int(x['puzzle_number']))

    # Re-sequence them starting from 1
    # 001: Waffle Tower, 002: Great Whale of China, 003: Taj Ma-Haul
    # 004: Pyramids of Geezer, 005: Sconehenge, etc.
    for idx, p in enumerate(active):
        p['puzzle_number'] = f"{idx + 1:03d}"
        print(f"Re-sequenced: {p['puzzle_number']}: {p['boss_pun_title']}")

    # Now append Grand Crayon to the end of the active challenges
    next_num = len(active) + 1
    grand_crayon['puzzle_number'] = f"{next_num:03d}"
    print(f"Moved Grand Crayon to the end: {grand_crayon['puzzle_number']}")

    # Re-sort the whole puzzle array: active ones first (sorted by puzzle_number), then the backlog ones (puzzle_number == '')
    active_sorted = sorted([p for p in puzzles if p.get('puzzle_number')], key=lambda x: int(x['puzzle_number']))
    backlog = [p for p in puzzles if not p.get('puzzle_number')]
    
    final_puzzles = active_sorted + backlog

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(final_puzzles, f, indent=2, ensure_ascii=False)
    print("Saved successfully!")

# Run on both repositories
adjust_schedule(r"c:\Users\iwand\.antigravity\Projects\PunFiction-TravelReviews\backend\travelreviews_daily_games.json")
adjust_schedule(r"c:\Users\iwand\.antigravity\Projects\PunFiction\backend\travelreviews_daily_games.json")
