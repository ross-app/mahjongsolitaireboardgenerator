from flask import Flask, render_template, Response, request, jsonify
import random
import re
import shutil
import time
from collections import defaultdict
from PIL import Image, ImageDraw
import os
import threading

app = Flask(__name__)
generation_lock = threading.Lock()

# -----------------------------
# Background cleanup (folders older than 1 hour)
# -----------------------------
SESSION_MAX_AGE_SECONDS = 18000  # 5 hours

def _cleanup_old_sessions():
    while True:
        time.sleep(600)  # run every 10 minutes
        try:
            now = time.time()
            for name in os.listdir(EXPORT_FOLDER):
                folder = os.path.join(EXPORT_FOLDER, name)
                if os.path.isdir(folder):
                    age = now - os.path.getmtime(folder)
                    if age > SESSION_MAX_AGE_SECONDS:
                        shutil.rmtree(folder, ignore_errors=True)
        except Exception:
            pass

_cleanup_thread = threading.Thread(target=_cleanup_old_sessions, daemon=True)
_cleanup_thread.start()

# -----------------------------
# Parameters
# -----------------------------
TILE_SIZE = 50  # pixel size for display
TILE_FOLDER = "static/images"
EXPORT_FOLDER = "static/generated"
os.makedirs(EXPORT_FOLDER, exist_ok=True)
EXPORT_FILE = os.path.join(EXPORT_FOLDER, "board.png")

# -----------------------------
# Adjacency table (rows)
# -----------------------------
rows = [
    ("B5", None, "C5", None),
    ("C5", "B5", "D5", None),
    ("D5", "C5", "E5", None),
    ("E5", "D5", "F5", None),
    ("F5", "E5", "G5", None),
    ("G5", "F5", "H5", None),
    ("H5", "G5", "I5", None),
    ("I5", "H5", "J5", None),
    ("J5", "I5", "K5", None),
    ("K5", "J5", "L5", None),
    ("L5", "K5", "M5", None),
    ("M5", "L5", None, None),
    ("D6", None, "E6", None),
    ("E6", "D6", "F6", "E14"),
    ("F6", "E6", "G6", "F14"),
    ("G6", "F6", "H6", "G14"),
    ("H6", "G6", "I6", "H14"),
    ("I6", "H6", "J6", "I14"),
    ("J6", "I6", "K6", "J14"),
    ("K6", "J6", None, None),
    ("C7", None, "D7", None),
    ("D7", "C7", "E7", None),
    ("E7", "D7", "F7", "E15"),
    ("F7", "E7", "G7", "F15"),
    ("G7", "F7", "H7", "G15"),
    ("H7", "G7", "I7", "H15"),
    ("I7", "H7", "J7", "I15"),
    ("J7", "I7", "K7", "J15"),
    ("K7", "J7", "L7", None),
    ("L7", "K7", None, None),
    ("A8", None, "B8", None),
    ("A8", None, "B9", None),
    ("B8", "A8", "C8", None),
    ("C8", "B8", "D8", None),
    ("D8", "C8", "E8", None),
    ("E8", "D8", "F8", "E16"),
    ("F8", "E8", "G8", "F16"),
    ("G8", "F8", "H8", "G16"),
    ("H8", "G8", "I8", "H16"),
    ("I8", "H8", "J8", "I16"),
    ("J8", "I8", "K8", "J16"),
    ("K8", "J8", "L8", None),
    ("L8", "K8", "M8", None),
    ("M8", "L8", "N8", None),
    ("N8", "M8", "O8", None),
    ("N8", "M9", "O8", None),
    ("O8", "N8", None, None),
    ("B9", "A8", "C9", None),
    ("C9", "B9", "D9", None),
    ("D9", "C9", "E9", None),
    ("E9", "D9", "F9", "E17"),
    ("F9", "E9", "G9", "F17"),
    ("G9", "F9", "H9", "G17"),
    ("H9", "G9", "I9", "H17"),
    ("I9", "H9", "J9", "I17"),
    ("J9", "I9", "K9", "J17"),
    ("K9", "J9", "L9", None),
    ("L9", "K9", "M9", None),
    ("M9", "L9", "N8", None),
    ("C10", None, "D10", None),
    ("D10", "C10", "E10", None),
    ("E10", "D10", "F10", "E18"),
    ("F10", "E10", "G10", "F18"),
    ("G10", "F10", "H10", "G18"),
    ("H10", "G10", "I10", "H18"),
    ("I10", "H10", "J10", "I18"),
    ("J10", "I10", "K10", "J18"),
    ("K10", "J10", "L10", None),
    ("L10", "K10", None, None),
    ("D11", None, "E11", None),
    ("E11", "D11", "F11", "E19"),
    ("F11", "E11", "G11", "F19"),
    ("G11", "F11", "H11", "G19"),
    ("H11", "G11", "I11", "H19"),
    ("I11", "H11", "J11", "I19"),
    ("J11", "I11", "K11", "J19"),
    ("K11", "J11", None, None),
    ("B12", None, "C12", None),
    ("C12", "B12", "D12", None),
    ("D12", "C12", "E12", None),
    ("E12", "D12", "F12", None),
    ("F12", "E12", "G12", None),
    ("G12", "F12", "H12", None),
    ("H12", "G12", "I12", None),
    ("I12", "H12", "J12", None),
    ("J12", "I12", "K12", None),
    ("K12", "J12", "L12", None),
    ("L12", "K12", "M12", None),
    ("M12", "L12", None, None),
    ("E14", None, "F14", None),
    ("F14", "E14", "G14", None),
    ("G14", "F14", "H14", None),
    ("H14", "G14", "I14", None),
    ("I14", "H14", "J14", None),
    ("J14", "I14", None, None),
    ("E15", None, "F15", None),
    ("F15", "E15", "G15", "F21"),
    ("G15", "F15", "H15", "G21"),
    ("H15", "G15", "I15", "H21"),
    ("I15", "H15", "J15", "I21"),
    ("J15", "I15", None, None),
    ("E16", None, "F16", None),
    ("F16", "E16", "G16", "F22"),
    ("G16", "F16", "H16", "G22"),
    ("H16", "G16", "I16", "H22"),
    ("I16", "H16", "J16", "I22"),
    ("J16", "I16", None, None),
    ("E17", None, "F17", None),
    ("F17", "E17", "G17", "F23"),
    ("G17", "F17", "H17", "G23"),
    ("H17", "G17", "I17", "H23"),
    ("I17", "H17", "J17", "I23"),
    ("J17", "I17", None, None),
    ("E18", None, "F18", None),
    ("F18", "E18", "G18", "F24"),
    ("G18", "F18", "H18", "G24"),
    ("H18", "G18", "I18", "H24"),
    ("I18", "H18", "J18", "I24"),
    ("J18", "I18", None, None),
    ("E19", None, "F19", None),
    ("F19", "E19", "G19", None),
    ("G19", "F19", "H19", None),
    ("H19", "G19", "I19", None),
    ("I19", "H19", "J19", None),
    ("J19", "I19", None, None),
    ("F21", None, "G21", None),
    ("G21", "F21", "H21", None),
    ("H21", "G21", "I21", None),
    ("I21", "H21", None, None),
    ("F22", None, "G22", None),
    ("G22", "F22", "H22", "G26"),
    ("H22", "G22", "I22", "H26"),
    ("I22", "H22", None, None),
    ("F23", None, "G23", None),
    ("G23", "F23", "H23", "G27"),
    ("H23", "G23", "I23", "H27"),
    ("I23", "H23", None, None),
    ("F24", None, "G24", None),
    ("G24", "F24", "H24", None),
    ("H24", "G24", "I24", None),
    ("I24", "H24", None, None),
    ("G26", None, "H26", "G29"),
    ("H26", "G26", None, "G29"),
    ("G27", None, "H27", "G29"),
    ("H27", "G27", None, "G29"),
    ("G29", None, None, None)
]

# -----------------------------
# Build adjacency map
# -----------------------------
cells = defaultdict(lambda: {"left": None, "right": None, "above": None})
for cell, left, right, above in rows:
    cells[cell]["left"] = left
    cells[cell]["right"] = right
    cells[cell]["above"] = above
cells = dict(cells)

# -----------------------------
# Coordinates for visualization
# -----------------------------
coord_map = {}
max_row = 0
max_col = 0
min_row = float('inf')
min_col = float('inf')
for cell in cells:
    m = re.match(r"([A-Z]+)(\d+)", cell)
    col_letters = m.group(1)
    row = int(m.group(2))
    col = 0
    for i, ch in enumerate(reversed(col_letters)):
        col += (ord(ch)-65+1) * (26**i)
    col -= 1
    coord_map[(row, col)] = cell
    max_row = max(max_row, row)
    max_col = max(max_col, col)
    min_row = min(min_row, row)
    min_col = min(min_col, col)

grid = {cell: None for cell in cells}
special_assignments = {}  # cell -> PIL Image, assigned once at placement time

# -----------------------------
# Tiles
# -----------------------------
tiles = []
for g in range(1, 37):
    tiles += [g]*4
random.shuffle(tiles)

# -----------------------------
# Tile images
# -----------------------------
tile_images = {i: Image.open(f"{TILE_FOLDER}/T{i}.png").resize((TILE_SIZE,TILE_SIZE)) for i in range(1,35)}
tile_images_special = {
    35: [Image.open(f"{TILE_FOLDER}/T35{ch}.png").resize((TILE_SIZE,TILE_SIZE)) for ch in "abcd"],
    36: [Image.open(f"{TILE_FOLDER}/T36{ch}.png").resize((TILE_SIZE,TILE_SIZE)) for ch in "abcd"]
}

# -----------------------------
# Utility functions
# -----------------------------
def cell_status(cell):
    return cell is not None and grid[cell] is None

def attributes(cell):
    left = cells[cell]["left"]
    right = cells[cell]["right"]
    above = cells[cell]["above"]
    a = left is None
    b = not a and not cell_status(left)
    c = right is None
    d = not c and not cell_status(right)
    e = above is None
    f = not e and not cell_status(above)
    return a,b,c,d,e,f

def compute_range():
    r = set()
    for cell in grid:
        if not cell_status(cell):
            continue
        a,b,c,d,e,f = attributes(cell)
        if (a or b or c or d) and (e or f):
            r.add(cell)
    return r

# -----------------------------
# Visualization
# -----------------------------
EXTRA_ROWS = 0
EXTRA_COLS = 0
PADDING = 5  # pixels of padding around the board

def visualize_grid(grid, diff_range=None, range_available=None, save_path=None):
    num_rows = max_row - min_row + 1
    num_cols = max_col - min_col + 1
    WIDTH = num_cols * TILE_SIZE + PADDING * 2
    HEIGHT = (num_rows + 1) * TILE_SIZE + PADDING * 2  # +1 row for half-tile offsets

    canvas = Image.new('RGBA', (WIDTH, HEIGHT), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas, 'RGBA')

    # Use stable special tile assignments (set during placement)
    special_cells = {}
    for tile_num in (35, 36):
        for cell, val in grid.items():
            if val == tile_num:
                if cell not in special_assignments:
                    special_assignments[cell] = random.choice(tile_images_special[tile_num])
                special_cells[cell] = special_assignments[cell]

    # Visual-only pixel offsets for specific cells (half-tile shifts)
    # Does not affect game logic — purely cosmetic repositioning
    visual_offsets = {
        "A8":  (0,              TILE_SIZE // 2),
        "N8":  (0,              TILE_SIZE // 2),
        "O8":  (0,              TILE_SIZE // 2),
        "G29": (TILE_SIZE // 2, 0),
    }

    for r in range(min_row, max_row + 2):
        for c in range(min_col, max_col + 1):
            cell = coord_map.get((r, c), None)
            if cell is None:
                continue

            dx, dy = visual_offsets.get(cell, (0, 0))
            # Offset by min_row/min_col so board starts at top-left + padding
            x1 = (c - min_col) * TILE_SIZE + dx + PADDING
            y1 = (r - min_row) * TILE_SIZE + dy + PADDING
            x2 = x1 + TILE_SIZE
            y2 = y1 + TILE_SIZE

            # Tile images
            if grid[cell] is not None and grid[cell] < 35:
                canvas.paste(tile_images[grid[cell]], (x1, y1))
            elif grid[cell] in (35, 36):
                canvas.paste(special_cells[cell], (x1, y1))

            # Cell border
            draw.rectangle([x1, y1, x2 - 1, y2 - 1], outline=(0, 0, 0, 255), width=1)

    if save_path:
        canvas.save(save_path)
    else:
        canvas.show()

# -----------------------------
# Placement function
# -----------------------------
def place_tiles_pairwise(save_intermediates=False, intermediate_folder=None):
    global special_assignments
    special_assignments.clear()
    for cell in grid:
        grid[cell] = None
    tiles_copy = tiles[:]

    step = 1
    while tiles_copy:
        tile1 = tiles_copy.pop()
        tile2 = tile1
        tiles_copy.remove(tile1)

        range_available = compute_range()
        if not range_available:
            continue  # fallback, will retry next iteration

        first_cell = random.choice(list(range_available))
        grid[first_cell] = tile1

        second_candidates = range_available - {first_cell}
        if not second_candidates:
            second_candidates = {c for c in grid if grid[c] is None} - {first_cell}

        second_cell = random.choice(list(second_candidates))
        grid[second_cell] = tile2

        # Assign special tile variants once, stably
        for cell in (first_cell, second_cell):
            if grid[cell] in (35, 36) and cell not in special_assignments:
                special_assignments[cell] = random.choice(tile_images_special[grid[cell]])

        if save_intermediates and intermediate_folder:
            # Build a temporary grid showing only the two tiles placed this step
            step_grid = {cell: None for cell in grid}
            step_grid[first_cell] = tile1
            step_grid[second_cell] = tile2
            path = os.path.join(intermediate_folder, f"board-{step}.png")
            visualize_grid(step_grid, save_path=path)
            step += 1

# -----------------------------
# FLASK ROUTES HERE
# -----------------------------

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/board")
def board():
    session_id = request.args.get("session_id", "")
    if not session_id or not re.fullmatch(r"[0-9a-f\-]{36}", session_id):
        return render_template("index.html")
    folder = os.path.join(EXPORT_FOLDER, session_id)
    if not os.path.isdir(folder):
        return render_template("index.html")
    return render_template("result.html",
                           image=f"generated/{session_id}/board.png",
                           session_id=session_id)

@app.route("/result")
def result():
    import uuid
    session_id = str(uuid.uuid4())
    session_folder = os.path.join(EXPORT_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)

    acquired = generation_lock.acquire(blocking=False)
    if not acquired:
        return render_template("busy.html"), 503

    try:
        place_tiles_pairwise(save_intermediates=True, intermediate_folder=session_folder)
        export_file = os.path.join(session_folder, "board.png")
        visualize_grid(grid, save_path=export_file)
    finally:
        generation_lock.release()

    return render_template("result.html",
                           image=f"generated/{session_id}/board.png",
                           session_id=session_id)

@app.route("/steps")
def steps():
    session_id = request.args.get("session_id", "")
    if not session_id:
        return "Missing session ID. Please generate a board first.", 400

    session_folder = os.path.join(EXPORT_FOLDER, session_id)
    if not os.path.isdir(session_folder):
        return "Session not found. Please generate a new board.", 404

    step_files = sorted(
        [f for f in os.listdir(session_folder) if f.startswith("board-") and f.endswith(".png")],
        key=lambda f: int(f.replace("board-", "").replace(".png", ""))
    )
    total = len(step_files)
    if total == 0:
        return "No steps found. Please generate a board first.", 404

    requested = request.args.get("step", 1, type=int)
    requested = max(1, min(requested, total))

    image_filename = f"generated/{session_id}/board-{requested}.png"

    return render_template("steps.html",
                           image=image_filename,
                           step=requested,
                           total=total,
                           session_id=session_id)

@app.route("/googlea921428778131bd1.html")
def google_verify():
    return app.send_static_file("googlea921428778131bd1.html")

@app.route('/sitemap.xml')
def sitemap():
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset
      xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9
            http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">
<url>
  <loc>https://mahjongsolitaireboardgenerator.onrender.com/</loc>
  <lastmod>2026-04-20</lastmod>
  <priority>1.00</priority>
</url>
<url>
  <loc>https://mahjongsolitaireboardgenerator.onrender.com/result</loc>
  <lastmod>2026-04-20</lastmod>
  <priority>0.80</priority>
</url>
</urlset>'''
    return Response(xml, mimetype='application/xml')

@app.route("/delete_session", methods=["POST"])
def delete_session():
    session_id = request.json.get("session_id", "")
    # Sanitize: only allow UUID-shaped strings (hex + dashes, 36 chars)
    if session_id and re.fullmatch(r"[0-9a-f\-]{36}", session_id):
        folder = os.path.join(EXPORT_FOLDER, session_id)
        if os.path.isdir(folder):
            shutil.rmtree(folder, ignore_errors=True)
    return jsonify({"ok": True})

# -----------------------------
# RUN APP
# -----------------------------

import os

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
