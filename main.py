import math
import asyncio
from pyscript import document
from pyodide.ffi import create_proxy

# Elemen DOM & State
player = document.getElementById('player')
player_idle_svg = document.getElementById('player-idle')
player_attack_svg = document.getElementById('player-attack')
water = document.getElementById('water')
splash_fx = document.getElementById('splash-fx')
reset_btn = document.getElementById('reset-btn')

player_pos = {"x": 200, "y": 300}
water_pos = {"x": 400, "y": 200}
is_attacking = False
is_splashing = False

# Movement Settings (Kini lebih halus, tidak kaku)
keys_pressed = set()
move_speed = 6 

# Objek Target (Tree & Grass)
targets = {
    "tree": {
        "el": document.getElementById('tree'), "pos": {"x": 600, "y": 250},
        "hp": 100, "is_dead": False,
        "ui_fill": document.getElementById('tree-hp-fill'),
        "ui_hurt": document.getElementById('tree-event-hurt'),
        "ui_death": document.getElementById('tree-event-death'),
        "svg_idle": document.getElementById('tree-idle'),
        "svg_hurt": document.getElementById('tree-hurt'),
        "svg_death": document.getElementById('tree-death')
    },
    "grass": {
        "el": document.getElementById('grass'), "pos": {"x": 250, "y": 450},
        "hp": 100, "is_dead": False,
        "ui_fill": document.getElementById('grass-hp-fill'),
        "ui_hurt": document.getElementById('grass-event-hurt'),
        "ui_death": document.getElementById('grass-event-death'),
        "svg_idle": document.getElementById('grass-idle'),
        "svg_hurt": document.getElementById('grass-hurt'),
        "svg_death": document.getElementById('grass-death')
    }
}

# -------------------------
# SISTEM DRAG & DROP
# -------------------------
drag_target = None
drag_offset = {"x": 0, "y": 0}

def on_pointerdown(e):
    global drag_target, drag_offset
    el = e.target.closest('.game-object')
    if el:
        drag_target = el.id
        # Tentukan posisi mana yang sedang digeser
        curr_pos = None
        if drag_target == 'player': curr_pos = player_pos
        elif drag_target == 'water': curr_pos = water_pos
        elif drag_target in targets: curr_pos = targets[drag_target]["pos"]
        
        if curr_pos:
            drag_offset["x"] = e.clientX - curr_pos["x"]
            drag_offset["y"] = e.clientY - curr_pos["y"]
            el.style.zIndex = "100"

def on_pointermove(e):
    if drag_target:
        curr_pos = None
        if drag_target == 'player': curr_pos = player_pos
        elif drag_target == 'water': curr_pos = water_pos
        elif drag_target in targets: curr_pos = targets[drag_target]["pos"]
        
        if curr_pos:
            # Update posisi mengikuti kursor
            curr_pos["x"] = e.clientX - drag_offset["x"]
            curr_pos["y"] = e.clientY - drag_offset["y"]

def on_pointerup(e):
    global drag_target
    if drag_target:
        document.getElementById(drag_target).style.zIndex = "10"
        drag_target = None

# Mendaftarkan event listener untuk mouse/touch
document.addEventListener('pointerdown', create_proxy(on_pointerdown))
document.addEventListener('pointermove', create_proxy(on_pointermove))
document.addEventListener('pointerup', create_proxy(on_pointerup))


# -------------------------
# SISTEM KONTROL & COLLISION
# -------------------------
def on_keydown(e):
    key = e.key.lower()
    keys_pressed.add(key)
    if key == ' ' and not is_attacking:
        asyncio.create_task(trigger_player_attack_event())

def on_keyup(e):
    key = e.key.lower()
    if key in keys_pressed:
        keys_pressed.remove(key)

document.addEventListener('keydown', create_proxy(on_keydown))
document.addEventListener('keyup', create_proxy(on_keyup))

async def trigger_player_attack_event():
    global is_attacking
    is_attacking = True
    player_idle_svg.classList.add('hidden')
    player_attack_svg.classList.remove('hidden')
    
    for key, t in targets.items():
        if t["is_dead"]: continue
        
        # Jangkauan serang (radius lebih besar untuk pohon)
        dist = math.sqrt((player_pos["x"] - t["pos"]["x"])**2 + (player_pos["y"] - t["pos"]["y"])**2)
        if dist < 140:
            t["hp"] -= 35
            if t["hp"] <= 0:
                t["hp"] = 0
                handle_target_events(key, 'death')
            else:
                handle_target_events(key, 'hurt')
            
    await asyncio.sleep(0.2)
    player_attack_svg.classList.add('hidden')
    player_idle_svg.classList.remove('hidden')
    is_attacking = False

def handle_target_events(target_key, event_type):
    t = targets[target_key]
    t["ui_fill"].style.width = f"{t['hp']}%"
    
    if event_type == 'hurt':
        t["svg_idle"].classList.add('hidden')
        t["svg_hurt"].classList.remove('hidden')
        
        # Reset animasi UI hurt dengan trik menghapus & menambah ulang class
        t["ui_hurt"].classList.remove('hidden')
        t["ui_hurt"].style.animation = 'none'
        t["ui_hurt"].offsetHeight # Trigger Reflow browser
        t["ui_hurt"].style.animation = None
        
        async def revert_hurt():
            await asyncio.sleep(0.4)
            if not t["is_dead"]:
                t["svg_hurt"].classList.add('hidden')
                t["svg_idle"].classList.remove('hidden')
            t["ui_hurt"].classList.add('hidden')
        asyncio.create_task(revert_hurt())
        
    elif event_type == 'death':
        t["is_dead"] = True
        t["svg_idle"].classList.add('hidden')
        t["svg_hurt"].classList.add('hidden')
        t["svg_death"].classList.remove('hidden')
        t["ui_death"].classList.remove('hidden')
        reset_btn.classList.remove('hidden')


# -------------------------
# GAME LOOP (PERGERAKAN HALUS)
# -------------------------
async def game_loop():
    global is_splashing
    
    while True:
        # 1. Update Pergerakan (Jika tidak sedang di-drag)
        if drag_target != 'player':
            if 'w' in keys_pressed or 'arrowup' in keys_pressed: player_pos['y'] -= move_speed
            if 's' in keys_pressed or 'arrowdown' in keys_pressed: player_pos['y'] += move_speed
            if 'a' in keys_pressed or 'arrowleft' in keys_pressed: player_pos['x'] -= move_speed
            if 'd' in keys_pressed or 'arrowright' in keys_pressed: player_pos['x'] += move_speed

        # 2. Cek Collision (Player menyentuh Genangan Air)
        water_dist = math.sqrt((player_pos["x"] - water_pos["x"])**2 + (player_pos["y"] - water_pos["y"])**2)
        if water_dist < 60 and not is_splashing:
            is_splashing = True
            splash_fx.classList.remove('hidden')
            
            async def hide_splash():
                await asyncio.sleep(0.5)
                splash_fx.classList.add('hidden')
                await asyncio.sleep(0.5) # Cooldown sebelum bisa nyiprat lagi
                global is_splashing
                is_splashing = False
            asyncio.create_task(hide_splash())

        # 3. Render Posisi Semua Objek
        player.style.transform = f"translate({player_pos['x']}px, {player_pos['y']}px)"
        water.style.transform = f"translate({water_pos['x']}px, {water_pos['y']}px)"
        for t in targets.values():
            t["el"].style.transform = f"translate({t['pos']['x']}px, {t['pos']['y']}px)"

        # Tunggu sekitar 1/60 detik (60 FPS)
        await asyncio.sleep(0.016)

# Fungsi Reset
def reset_game(e):
    for key, t in targets.items():
        t["hp"] = 100
        t["is_dead"] = False
        t["ui_fill"].style.width = "100%"
        t["svg_death"].classList.add('hidden')
        t["svg_hurt"].classList.add('hidden')
        t["svg_idle"].classList.remove('hidden')
        t["ui_death"].classList.add('hidden')
        t["ui_hurt"].classList.add('hidden')
    reset_btn.classList.add('hidden')

reset_btn.addEventListener('click', create_proxy(reset_game))

# Memulai Mesin Game Loop
asyncio.create_task(game_loop())