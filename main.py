import math
import random
import asyncio
from pyscript import document
from pyodide.ffi import create_proxy
from js import window

# ==========================================
# 1. VARIABEL GLOBAL (STATE GAME)
# ==========================================
player = None
player_idle_svg = None
player_attack_svg = None
reset_btn = None
restock_btn = None

player_pos = {"x": 200, "y": 300}
is_attacking = False
keys_pressed = set()
move_speed = 6 

active_trees = []
active_grasses = []
active_waters = []
active_chests = []
id_counter = 0

drag_target = None
drag_offset = {"x": 0, "y": 0}


# ==========================================
# 2. LOGIKA PERMAINAN (FUNGSI UTAMA)
# ==========================================
def spawn_object(item_type):
    global id_counter
    id_counter += 1
    unique_id = f"obj-{item_type}-{id_counter}"
    
    # Kloning SVG dari wadah template tersembunyi
    template = document.getElementById(f"template-{item_type}")
    clone = template.content.cloneNode(True)
    el = clone.querySelector(".game-object")
    el.id = unique_id
    
    max_x = window.innerWidth - 150 if window.innerWidth > 300 else 800
    max_y = window.innerHeight - 150 if window.innerHeight > 300 else 600
    rx = random.randint(80, max(80, int(max_x)))
    ry = random.randint(80, max(80, int(max_y)))
    
    el.style.transform = f"translate({rx}px, {ry}px)"
    document.getElementById("game-area").appendChild(clone)
    
    real_el = document.getElementById(unique_id)
    item_data = {"id": unique_id, "el": real_el, "x": rx, "y": ry, "type": item_type}
    
    if item_type in ["tree", "grass"]:
        item_data.update({
            "hp": 100, "is_dead": False,
            "ui_fill": real_el.querySelector(".hp-fill"),
            "ui_hurt": real_el.querySelector(".hurt-fx"),
            "ui_death": real_el.querySelector(".death-fx"),
            "svg_idle": real_el.querySelector(".svg-idle"),
            "svg_hurt": real_el.querySelector(".svg-hurt"),
            "svg_death": real_el.querySelector(".svg-death")
        })
        if item_type == "tree": active_trees.append(item_data)
        else: active_grasses.append(item_data)
        
    elif item_type == "water":
        item_data.update({"is_splashing": False, "splash_fx": real_el.querySelector(".splash-fx")})
        active_waters.append(item_data)
        
    elif item_type == "chest":
        item_data.update({
            "is_opened": False,
            "hint_ui": real_el.querySelector(".chest-hint"),
            "event_ui": real_el.querySelector(".loot-fx"),
            "svg_closed": real_el.querySelector(".chest-closed"),
            "svg_open": real_el.querySelector(".chest-open")
        })
        active_chests.append(item_data)


def find_item_by_id(uid):
    for group in [active_trees, active_grasses, active_waters, active_chests]:
        for item in group:
            if item["id"] == uid: return item
    return None


# --- INTERAKSI DRAG & DROP ---
def on_pointerdown(e):
    global drag_target, drag_offset
    el = e.target.closest('.game-object')
    if el:
        drag_target = el.id
        curr_pos = player_pos if drag_target == 'player' else find_item_by_id(drag_target)
        if curr_pos:
            drag_offset["x"] = e.clientX - curr_pos["x"]
            drag_offset["y"] = e.clientY - curr_pos["y"]
            el.style.zIndex = "100"

def on_pointermove(e):
    if drag_target:
        curr_pos = player_pos if drag_target == 'player' else find_item_by_id(drag_target)
        if curr_pos:
            curr_pos["x"] = e.clientX - drag_offset["x"]
            curr_pos["y"] = e.clientY - drag_offset["y"]

def on_pointerup(e):
    global drag_target
    if drag_target:
        el = document.getElementById(drag_target)
        if el: el.style.zIndex = "10"
        drag_target = None


# --- INTERAKSI KEYBOARD ---
def on_keydown(e):
    key = e.key.lower()
    keys_pressed.add(key)
    if key == ' ':
        asyncio.create_task(trigger_player_space_action())

def on_keyup(e):
    key = e.key.lower()
    if key in keys_pressed: keys_pressed.remove(key)


# --- SISTEM SERANGAN & KOLEKSI ---
async def trigger_player_space_action():
    global is_attacking
    
    chest_collected = False
    for c in active_chests:
        if not c["is_opened"]:
            dist = math.sqrt((player_pos["x"] - c["x"])**2 + (player_pos["y"] - c["y"])**2)
            if dist < 70:
                c["is_opened"] = True
                c["hint_ui"].classList.add('hidden')
                c["svg_closed"].classList.add('hidden')
                c["svg_open"].classList.remove('hidden')
                c["event_ui"].classList.remove('hidden')
                
                async def destroy_chest_delayed(target_chest):
                    await asyncio.sleep(2.5)
                    if target_chest["el"] and target_chest["el"].parentNode:
                        target_chest["el"].remove()
                    if target_chest in active_chests:
                        active_chests.remove(target_chest)
                asyncio.create_task(destroy_chest_delayed(c))
                
                chest_collected = True
                break
                
    if not chest_collected and not is_attacking:
        is_attacking = True
        player_idle_svg.classList.add('hidden')
        player_attack_svg.classList.remove('hidden')
        
        for t in active_trees:
            if t["is_dead"]: continue
            if math.sqrt((player_pos["x"] - t["x"])**2 + (player_pos["y"] - t["y"])**2) < 140:
                t["hp"] -= 35
                if t["hp"] <= 0:
                    t["hp"] = 0
                    handle_target_events(t, 'death')
                else:
                    handle_target_events(t, 'hurt')
                    
        for g in active_grasses:
            if g["is_dead"]: continue
            if math.sqrt((player_pos["x"] - g["x"])**2 + (player_pos["y"] - g["y"])**2) < 140:
                g["hp"] -= 35
                if g["hp"] <= 0:
                    g["hp"] = 0
                    handle_target_events(g, 'death')
                else:
                    handle_target_events(g, 'hurt')
                    
        await asyncio.sleep(0.2)
        player_attack_svg.classList.add('hidden')
        player_idle_svg.classList.remove('hidden')
        is_attacking = False

def handle_target_events(t, event_type):
    t["ui_fill"].style.width = f"{t['hp']}%"
    
    if event_type == 'hurt':
        t["svg_idle"].classList.add('hidden')
        t["svg_hurt"].classList.remove('hidden')
        t["ui_hurt"].classList.remove('hidden')
        t["ui_hurt"].style.animation = 'none'
        t["ui_hurt"].offsetHeight 
        t["ui_hurt"].style.animation = None
        
        async def revert_hurt(target):
            await asyncio.sleep(0.4)
            if not target["is_dead"]:
                target["svg_hurt"].classList.add('hidden')
                target["svg_idle"].classList.remove('hidden')
            target["ui_hurt"].classList.add('hidden')
        asyncio.create_task(revert_hurt(t))
        
    elif event_type == 'death':
        t["is_dead"] = True
        t["svg_idle"].classList.add('hidden')
        t["svg_hurt"].classList.add('hidden')
        t["svg_death"].classList.remove('hidden')
        t["ui_death"].classList.remove('hidden')
        reset_btn.classList.remove('hidden')
        
        async def destroy_object_delayed(target_obj):
            await asyncio.sleep(3.0)
            if target_obj["el"] and target_obj["el"].parentNode:
                target_obj["el"].remove()
            if target_obj in active_trees: active_trees.remove(target_obj)
            elif target_obj in active_grasses: active_grasses.remove(target_obj)
        asyncio.create_task(destroy_object_delayed(t))


# --- FUNGSI RESET MANUAL ---
def manual_restock_chests(e):
    while len(active_chests) < 5:
        spawn_object("chest")

def manual_revive_all_game(e):
    while len(active_trees) < 5: spawn_object("tree")
    while len(active_grasses) < 5: spawn_object("grass")
    
    for t in active_trees:
        t["hp"] = 100
        t["ui_fill"].style.width = "100%"
    for g in active_grasses:
        g["hp"] = 100
        g["ui_fill"].style.width = "100%"
        
    manual_restock_chests(None)
    reset_btn.classList.add('hidden')


# --- GAME ENGINE LOOP ---
async def game_loop():
    while True:
        if drag_target != 'player':
            if 'w' in keys_pressed or 'arrowup' in keys_pressed: player_pos['y'] -= move_speed
            if 's' in keys_pressed or 'arrowdown' in keys_pressed: player_pos['y'] += move_speed
            if 'a' in keys_pressed or 'arrowleft' in keys_pressed: player_pos['x'] -= move_speed
            if 'd' in keys_pressed or 'arrowright' in keys_pressed: player_pos['x'] += move_speed

        player.style.transform = f"translate({player_pos['x']}px, {player_pos['y']}px)"
        
        for w in active_waters:
            w["el"].style.transform = f"translate({w['x']}px, {w['y']}px)"
            water_dist = math.sqrt((player_pos["x"] - w["x"])**2 + (player_pos["y"] - w["y"])**2)
            if water_dist < 60 and not w["is_splashing"]:
                w["is_splashing"] = True
                w["splash_fx"].classList.remove('hidden')
                async def hide_splash(water_obj):
                    await asyncio.sleep(0.5)
                    water_obj["splash_fx"].classList.add('hidden')
                    await asyncio.sleep(0.5)
                    water_obj["is_splashing"] = False
                asyncio.create_task(hide_splash(w))
                
        for c in active_chests:
            c["el"].style.transform = f"translate({c['x']}px, {c['y']}px)"
            chest_dist = math.sqrt((player_pos["x"] - c["x"])**2 + (player_pos["y"] - c["y"])**2)
            if chest_dist < 70 and not c["is_opened"]:
                c["hint_ui"].classList.remove('hidden')
            else:
                c["hint_ui"].classList.add('hidden')
                
        for t in active_trees: t["el"].style.transform = f"translate({t['x']}px, {t['y']}px)"
        for g in active_grasses: g["el"].style.transform = f"translate({g['x']}px, {g['y']}px)"

        await asyncio.sleep(0.016)


async def auto_spawn_and_restock_loop():
    while True:
        await asyncio.sleep(12)
        if len(active_trees) < 5: spawn_object("tree")
        if len(active_grasses) < 5: spawn_object("grass")
        if len(active_waters) < 5: spawn_object("water")
        if len(active_chests) < 5: spawn_object("chest")


# ==========================================
# 3. FUNGSI LOADING & INITIALIZER
# ==========================================
async def init_game():
    global player, player_idle_svg, player_attack_svg, reset_btn, restock_btn
    
    # --- PROSES PENGAMBILAN SVG EKSTERNAL ---
    response = await window.fetch("svgs.html")
    html_data = await response.text()
    
    # Suntikkan template ke wadah tersembunyi
    document.getElementById("svg-assets").innerHTML = html_data
    # Suntikkan SVG Player ke tempat utamanya
    document.getElementById("player").innerHTML = document.getElementById("player-assets").innerHTML
    
    # --- MENGIKAT ELEMEN HTML KE VARIABEL ---
    player = document.getElementById('player')
    player_idle_svg = document.getElementById('player-idle')
    player_attack_svg = document.getElementById('player-attack')
    reset_btn = document.getElementById('reset-btn')
    restock_btn = document.getElementById('restock-btn')
    
    # --- MEMASANG EVENT LISTENER MOUSE & KEYBOARD ---
    document.addEventListener('pointerdown', create_proxy(on_pointerdown))
    document.addEventListener('pointermove', create_proxy(on_pointermove))
    document.addEventListener('pointerup', create_proxy(on_pointerup))
    document.addEventListener('keydown', create_proxy(on_keydown))
    document.addEventListener('keyup', create_proxy(on_keyup))
    restock_btn.addEventListener('click', create_proxy(manual_restock_chests))
    reset_btn.addEventListener('click', create_proxy(manual_revive_all_game))
    
    # --- MEMULAI SPAWN PERTAMA ---
    for _ in range(2):
        spawn_object("tree")
        spawn_object("grass")
        spawn_object("water")
        spawn_object("chest")

    # --- MENJALANKAN MESIN GAME ---
    asyncio.create_task(game_loop())
    asyncio.create_task(auto_spawn_and_restock_loop())


# Pemicu Eksekusi Paling Awal
asyncio.create_task(init_game())