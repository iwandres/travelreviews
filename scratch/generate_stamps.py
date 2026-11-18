import os
import shutil
import math
from PIL import Image, ImageDraw

# Define directories
src_dir = 'assets/stamps/'
dest_dir = 'c:/Users/iwand/.antigravity/Projects/PunFiction/travelreviews/assets/stamps/'

# Create directories if they do not exist
os.makedirs(src_dir, exist_ok=True)
os.makedirs(dest_dir, exist_ok=True)

# Helper to draw a circle stamp border
def draw_base_stamp(draw, color, shape='circle'):
    if shape == 'circle':
        # Outer thick border
        draw.ellipse([15, 15, 235, 235], outline=color, width=4)
        # Inner thin border
        draw.ellipse([25, 25, 225, 225], outline=color, width=1)
        # Add some stars or dots in the border area
        for i in range(12):
            angle = i * (2 * math.pi / 12)
            x = 125 + 95 * math.cos(angle)
            y = 125 + 95 * math.sin(angle)
            draw.ellipse([x-2, y-2, x+2, y+2], fill=color)
    elif shape == 'scallop':
        # Draw a scalloped border
        num_scallops = 24
        for i in range(num_scallops):
            angle = i * (2 * math.pi / num_scallops)
            x = 125 + 105 * math.cos(angle)
            y = 125 + 105 * math.sin(angle)
            draw.ellipse([x-10, y-10, x+10, y+10], fill=color)
        # Clear the inside
        draw.ellipse([30, 30, 220, 220], fill=(0,0,0,0))
        # Draw inner ring
        draw.ellipse([32, 32, 218, 218], outline=color, width=3)
        draw.ellipse([40, 40, 210, 210], outline=color, width=1)
    elif shape == 'diamond':
        # Draw a diamond shaped stamp
        draw.polygon([(125, 15), (235, 125), (125, 235), (15, 125)], outline=color, width=4)
        draw.polygon([(125, 25), (225, 125), (125, 225), (25, 125)], outline=color, width=1)

# Helper to draw a vector 'N'
def draw_letter_n(draw, x, y, w, h, color, width=3):
    draw.line([(x, y+h), (x, y)], fill=color, width=width)
    draw.line([(x, y), (x+w, y+h)], fill=color, width=width)
    draw.line([(x+w, y+h), (x+w, y)], fill=color, width=width)

# Helper to draw a vector 'S'
def draw_letter_s(draw, x, y, w, h, color, width=3):
    draw.line([(x+w, y), (x, y)], fill=color, width=width)
    draw.line([(x, y), (x, y+h/2)], fill=color, width=width)
    draw.line([(x, y+h/2), (x+w, y+h/2)], fill=color, width=width)
    draw.line([(x+w, y+h/2), (x+w, y+h)], fill=color, width=width)
    draw.line([(x+w, y+h), (x, y+h)], fill=color, width=width)

# Helper to draw a vector 'E'
def draw_letter_e(draw, x, y, w, h, color, width=3):
    draw.line([(x+w, y), (x, y)], fill=color, width=width)
    draw.line([(x, y), (x, y+h)], fill=color, width=width)
    draw.line([(x, y+h/2), (x+w*0.8, y+h/2)], fill=color, width=width)
    draw.line([(x, y+h), (x+w, y+h)], fill=color, width=width)

# Helper to draw a vector 'W'
def draw_letter_w(draw, x, y, w, h, color, width=3):
    draw.line([(x, y), (x+w*0.25, y+h)], fill=color, width=width)
    draw.line([(x+w*0.25, y+h), (x+w*0.5, y+h*0.3)], fill=color, width=width)
    draw.line([(x+w*0.5, y+h*0.3), (x+w*0.75, y+h)], fill=color, width=width)
    draw.line([(x+w*0.75, y+h), (x+w, y)], fill=color, width=width)


# 1. stamp_airmail.png (Airmail sticker)
def make_airmail():
    img = Image.new('RGBA', (250, 250), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    color = (20, 52, 164, 255) # Royal Blue #1434A4
    
    # Rounded rectangle border
    draw.rounded_rectangle([25, 60, 225, 190], radius=15, outline=color, width=4)
    draw.rounded_rectangle([32, 67, 218, 183], radius=10, outline=color, width=1)
    
    # Draw red/blue diagonal stripes inside the margins
    # We will draw a few stripes on the left/right edges
    red_color = (200, 30, 30, 255)
    blue_color = (20, 52, 164, 255)
    
    # Left border stripes
    for i in range(4):
        y_pos = 75 + i * 25
        draw.line([(25, y_pos), (35, y_pos - 10)], fill=red_color, width=3)
        draw.line([(25, y_pos + 12), (35, y_pos + 2)], fill=blue_color, width=3)
        
    # Right border stripes
    for i in range(4):
        y_pos = 75 + i * 25
        draw.line([(215, y_pos), (225, y_pos - 10)], fill=red_color, width=3)
        draw.line([(215, y_pos + 12), (225, y_pos + 2)], fill=blue_color, width=3)
        
    # Draw envelope icon in center
    cx, cy = 125, 125
    draw.rectangle([cx-35, cy-20, cx+35, cy+20], outline=color, width=3)
    draw.line([(cx-35, cy-20), (cx, cy+5)], fill=color, width=3)
    draw.line([(cx+35, cy-20), (cx, cy+5)], fill=color, width=3)
    
    # Airmail text indicators (AirMail, Par Avion)
    # Just draw simple vector bars representing text lines for stylized watermark look
    draw.line([(cx-40, 80), (cx+40, 80)], fill=color, width=4)
    draw.line([(cx-25, 92), (cx+25, 92)], fill=color, width=2)
    draw.line([(cx-30, 160), (cx+30, 160)], fill=color, width=3)
    draw.line([(cx-15, 170), (cx+15, 170)], fill=color, width=2)
    
    img.save(os.path.join(src_dir, 'stamp_airmail.png'))


# 2. stamp_compass.png (Compass Rose)
def make_compass():
    img = Image.new('RGBA', (250, 250), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    color = (135, 54, 0, 255) # Sienna Brown
    draw_base_stamp(draw, color, 'circle')
    
    cx, cy = 125, 125
    # Inner ring
    draw.ellipse([cx-75, cy-75, cx+75, cy+75], outline=color, width=2)
    
    # Compass Points (8 points star)
    # N, S, E, W
    draw.polygon([(cx, cy), (cx-10, cy-15), (cx, cy-65), (cx+10, cy-15)], fill=color) # North point
    draw.polygon([(cx, cy), (cx-10, cy+15), (cx, cy+65), (cx+10, cy+15)], fill=color) # South point
    draw.polygon([(cx, cy), (cx-15, cy-10), (cx-65, cy), (cx-15, cy+10)], fill=color) # West point
    draw.polygon([(cx, cy), (cx+15, cy-10), (cx+65, cy), (cx+15, cy+10)], fill=color) # East point
    
    # NE, NW, SE, SW (smaller)
    draw.polygon([(cx, cy), (cx-3, cy-12), (cx-35, cy-35), (cx-12, cy-3)], fill=color)
    draw.polygon([(cx, cy), (cx+3, cy-12), (cx+35, cy-35), (cx+12, cy-3)], fill=color)
    draw.polygon([(cx, cy), (cx-3, cy+12), (cx-35, cy+35), (cx-12, cy+3)], fill=color)
    draw.polygon([(cx, cy), (cx+3, cy+12), (cx+35, cy+35), (cx+12, cy+3)], fill=color)
    
    # Vector Letters N, S, E, W
    draw_letter_n(draw, cx-6, cy-88, 12, 14, color, width=3)
    draw_letter_s(draw, cx-5, cy+72, 10, 14, color, width=3)
    draw_letter_w(draw, cx-85, cy-7, 14, 14, color, width=3)
    draw_letter_e(draw, cx+74, cy-7, 10, 14, color, width=3)
    
    img.save(os.path.join(src_dir, 'stamp_compass.png'))


# 3. stamp_globe.png (Globe / Grid)
def make_globe():
    img = Image.new('RGBA', (250, 250), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    color = (27, 79, 114, 255) # Midnight Blue
    draw_base_stamp(draw, color, 'scallop')
    
    cx, cy = 125, 125
    r = 65
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=color, width=4)
    
    # Equator and Latitude lines
    draw.line([(cx-r, cy), (cx+r, cy)], fill=color, width=3)
    draw.arc([cx-r, cy-r, cx+r, cy+r], 20, 160, fill=color, width=2)
    draw.arc([cx-r, cy-r, cx+r, cy+r], 200, 340, fill=color, width=2)
    
    # Longitude lines (ellipses)
    draw.ellipse([cx-r*0.6, cy-r, cx+r*0.6, cy+r], outline=color, width=2)
    draw.ellipse([cx-r*0.25, cy-r, cx+r*0.25, cy+r], outline=color, width=2)
    draw.line([(cx, cy-r), (cx, cy+r)], fill=color, width=2)
    
    # Tiny plane silhouette flying around it
    px, py = cx+40, cy-40
    # Wings
    draw.line([(px-15, py+8), (px+15, py-8)], fill=color, width=4)
    # Fuselage
    draw.line([(px-10, py-10), (px+10, py+10)], fill=color, width=6)
    # Tail
    draw.line([(px-13, py-3), (px-8, py-8)], fill=color, width=3)
    
    img.save(os.path.join(src_dir, 'stamp_globe.png'))


# 4. stamp_anchor.png (Nautical Anchor)
def make_anchor():
    img = Image.new('RGBA', (250, 250), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    color = (14, 102, 85, 255) # Deep Teal
    draw_base_stamp(draw, color, 'diamond')
    
    cx, cy = 125, 130
    # Center shank (vertical line)
    draw.line([(cx, cy-60), (cx, cy+50)], fill=color, width=6)
    # Stock (horizontal bar near top)
    draw.line([(cx-35, cy-40), (cx+35, cy-40)], fill=color, width=5)
    # Crown ring at top
    draw.ellipse([cx-15, cy-80, cx+15, cy-50], outline=color, width=5)
    # Curved arms
    draw.arc([cx-50, cy+10, cx+50, cy+70], 0, 180, fill=color, width=6)
    # Flukes (triangles on ends of curve)
    draw.polygon([(cx-50, cy+32), (cx-58, cy+40), (cx-42, cy+45)], fill=color)
    draw.polygon([(cx+50, cy+32), (cx+58, cy+40), (cx+42, cy+45)], fill=color)
    img.save(os.path.join(src_dir, 'stamp_anchor.png'))


# 5. stamp_luggage.png (Luggage Tag)
def make_luggage():
    img = Image.new('RGBA', (250, 250), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    color = (186, 74, 0, 255) # Terracotta Orange
    
    # Diamond/Scalloped hybrid border for visual variety
    draw_base_stamp(draw, color, 'scallop')
    
    cx, cy = 125, 125
    # Draw a rotated luggage tag silhouette in the center
    # Rotated coordinate helper
    # Center is 125,125. We will draw a rectangular tag rotated 30 degrees.
    # To keep code simple, let's draw a beautiful tag shape aligned or slightly tilted
    # Aligned luggage tag is very clean. Let's draw it tilted at 30 deg.
    # Tag corners (tilted):
    draw.polygon([
        (85, 145), (145, 85), (175, 115), (115, 175)
    ], outline=color, width=4)
    # Top triangular part of the tag
    draw.polygon([
        (85, 145), (115, 175), (80, 170)
    ], fill=color)
    
    # Hole and string
    draw.ellipse([92, 150, 102, 160], fill=(255,255,255,255), outline=color, width=2)
    draw.line([(97, 155), (70, 180)], fill=color, width=3)
    
    # Barcode lines inside tag
    # Drawing lines orthogonal to tag direction (45 deg)
    # We can draw 6 small parallel stripes
    draw.line([(115, 110), (135, 130)], fill=color, width=5)
    draw.line([(123, 118), (138, 133)], fill=color, width=2)
    draw.line([(129, 124), (144, 139)], fill=color, width=4)
    draw.line([(137, 132), (152, 147)], fill=color, width=6)
    
    img.save(os.path.join(src_dir, 'stamp_luggage.png'))


# 6. stamp_passport_entry.png (Passport entry stamp)
def make_passport_entry():
    img = Image.new('RGBA', (250, 250), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    color = (125, 60, 152, 255) # Royal Purple
    
    # Rectangular entry stamp frame
    draw.rounded_rectangle([30, 45, 220, 205], radius=15, outline=color, width=5)
    draw.rounded_rectangle([38, 53, 212, 197], radius=10, outline=color, width=1)
    
    cx, cy = 125, 125
    # Inner divider lines
    draw.line([(38, 90), (212, 90)], fill=color, width=2)
    draw.line([(38, 160), (212, 160)], fill=color, width=2)
    
    # Top Text lines (represented as vector bars for generic stamps look)
    draw.line([(60, 70), (190, 70)], fill=color, width=3)
    draw.line([(80, 80), (170, 80)], fill=color, width=2)
    
    # Middle Date "04 JUL 2026" written in clean vector lines
    # We can draw "JUL 2026" or similar
    # 0 4
    draw.line([(55, 110), (55, 140)], fill=color, width=3)
    draw.line([(55, 110), (67, 110)], fill=color, width=3)
    draw.line([(67, 110), (67, 140)], fill=color, width=3) # '0'
    
    draw.line([(78, 110), (78, 125)], fill=color, width=3)
    draw.line([(78, 125), (90, 125)], fill=color, width=3)
    draw.line([(90, 110), (90, 140)], fill=color, width=3) # '4'
    
    # J U L
    # J
    draw.line([(105, 110), (117, 110)], fill=color, width=3)
    draw.line([(111, 110), (111, 135)], fill=color, width=3)
    draw.chord([103, 125, 115, 140], 0, 180, fill=(0,0,0,0), outline=color, width=3)
    
    # U
    draw.line([(125, 110), (125, 135)], fill=color, width=3)
    draw.line([(137, 110), (137, 135)], fill=color, width=3)
    draw.arc([125, 125, 137, 140], 0, 180, fill=color, width=3)
    
    # L
    draw.line([(145, 110), (145, 140)], fill=color, width=3)
    draw.line([(145, 140), (157, 140)], fill=color, width=3)
    
    # 2 0 2 6
    # Simple line bars for the year to keep it clean
    draw.line([(168, 115), (195, 115)], fill=color, width=3)
    draw.line([(168, 127), (195, 127)], fill=color, width=3)
    draw.line([(168, 139), (195, 139)], fill=color, width=3)
    
    # Bottom section has a small star and code
    draw.ellipse([cx-6, 178, cx+6, 190], fill=color)
    draw.line([(48, 184), (105, 184)], fill=color, width=2)
    draw.line([(145, 184), (202, 184)], fill=color, width=2)
    
    img.save(os.path.join(src_dir, 'stamp_passport_entry.png'))


# 7. stamp_cancelled.png (Postage cancelled wavy lines)
def make_cancelled():
    img = Image.new('RGBA', (250, 250), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    color = (84, 110, 122, 255) # Slate Gray
    
    # A circular postmark stamp on the left side
    cx, cy = 80, 125
    draw.ellipse([cx-55, cy-55, cx+55, cy+55], outline=color, width=3)
    draw.ellipse([cx-48, cy-48, cx+48, cy+48], outline=color, width=1)
    
    # Inner details
    draw.line([(cx-35, cy), (cx+35, cy)], fill=color, width=2)
    draw.line([(cx-25, cy-15), (cx+25, cy-15)], fill=color, width=3)
    draw.line([(cx-25, cy+15), (cx+25, cy+15)], fill=color, width=3)
    
    # 5 Long wavy cancellation lines crossing from left to right across the page
    for offset_y in range(-60, 80, 30):
        # We will draw a sine wave representation with lines
        points = []
        for x in range(15, 235, 10):
            # Wave equation: y = amplitude * sin(frequency * x) + base_y
            y = cy + offset_y + 12 * math.sin(x * 0.05)
            points.append((x, y))
        draw.line(points, fill=color, width=2)
        
    img.save(os.path.join(src_dir, 'stamp_cancelled.png'))


# 8. stamp_airplane.png (Airplane Silhouette)
def make_airplane():
    img = Image.new('RGBA', (250, 250), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    color = (20, 90, 160, 255) # Ocean Blue
    draw_base_stamp(draw, color, 'circle')
    
    cx, cy = 125, 125
    # Inner dotted border
    for i in range(36):
        angle = i * (2 * math.pi / 36)
        x = cx + 80 * math.cos(angle)
        y = cy + 80 * math.sin(angle)
        draw.ellipse([x-1.5, y-1.5, x+1.5, y+1.5], fill=color)
        
    # Draw a stylized commercial passenger jet silhouette flying at 45 degrees
    # Center is cx,cy. Fuselage length: 110px. Wingspan: 100px.
    # Tilted coords
    # Nose at cx+45, cy-45. Tail at cx-55, cy+55.
    
    # Main wings (swept back)
    draw.polygon([
        (cx-10, cy+10),
        (cx-50, cy-20),
        (cx-52, cy-10),
        (cx-25, cy+25)
    ], fill=color)
    draw.polygon([
        (cx-10, cy+10),
        (cx+20, cy+50),
        (cx+10, cy+52),
        (cx-25, cy+25)
    ], fill=color)
    
    # Fuselage body (cigar shape)
    draw.polygon([
        (cx+48, cy-48), # Nose
        (cx+25, cy-15),
        (cx-55, cy+55), # Tail tip
        (cx-15, cy+25)
    ], fill=color)
    # Smooth nose shape
    draw.ellipse([cx+38, cy-48, cx+48, cy-38], fill=color)
    
    # Tailplane (horizontal stabilizers at the tail)
    draw.polygon([
        (cx-48, cy+48),
        (cx-65, cy+38),
        (cx-67, cy+42),
        (cx-53, cy+53)
    ], fill=color)
    draw.polygon([
        (cx-48, cy+48),
        (cx-38, cy+65),
        (cx-42, cy+67),
        (cx-53, cy+53)
    ], fill=color)
    
    img.save(os.path.join(src_dir, 'stamp_airplane.png'))


# Generate all 8 neutral stamps
make_airmail()
make_compass()
make_globe()
make_anchor()
make_luggage()
make_passport_entry()
make_cancelled()
make_airplane()

print("Generated 8 neutral vector travel stamps successfully.")

# Copy all new stamps to the PunFiction portal travelreviews/assets/stamps/ directory
files = os.listdir(src_dir)
copied_count = 0
for f in files:
    if f.startswith('stamp_'):
        shutil.copyfile(os.path.join(src_dir, f), os.path.join(dest_dir, f))
        copied_count += 1

print(f"Successfully copied {copied_count} stamp files to PunFiction portal repository.")
