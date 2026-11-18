import json
import shutil
import os

# Define the category to theme mapping
landmark_theme_mapping = {
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

# 1. Update clues
clues_path = 'backend/travelreviews_clues.json'
with open(clues_path, 'r', encoding='utf-8') as f:
    clues = json.load(f)

for c in clues:
    orig = c.get('original_name')
    theme = landmark_theme_mapping.get(orig, "historic_monuments")
    c['page_theme'] = theme

with open(clues_path, 'w', encoding='utf-8') as f:
    json.dump(clues, f, indent=2, ensure_ascii=False)
print(f"Updated clues file: {len(clues)} entries.")

# 2. Update postcards
postcards_path = 'backend/travelreviews_postcards.json'
with open(postcards_path, 'r', encoding='utf-8') as f:
    postcards = json.load(f)

for p in postcards:
    orig = p.get('original_name')
    theme = landmark_theme_mapping.get(orig, "historic_monuments")
    p['page_theme'] = theme

with open(postcards_path, 'w', encoding='utf-8') as f:
    json.dump(postcards, f, indent=2, ensure_ascii=False)
print(f"Updated postcards file: {len(postcards)} entries.")

# 3. Copy to PunFiction portal workspace
dest_clues = 'c:/Users/iwand/.antigravity/Projects/PunFiction/backend/travelreviews_clues.json'
dest_postcards = 'c:/Users/iwand/.antigravity/Projects/PunFiction/backend/travelreviews_postcards.json'

shutil.copyfile(clues_path, dest_clues)
shutil.copyfile(postcards_path, dest_postcards)
print("Copied files to PunFiction portal repository.")
