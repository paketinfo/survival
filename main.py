import math
import asyncio
from pyscript import document
from pyodide.ffi import create_proxy

# Mengambil elemen HTML dari DOM
player = document.getElementById('player')
tree = document.getElementById('tree')
tree_hp_display = document.getElementById('tree-hp')
reset_btn = document.getElementById('reset-btn')

# Status Game
player_pos = {"x": 100, "y": 180}
move_speed = 20
is_attacking = False
is_tree_dead = False
tree_hp = 100

def render_positions():
    # Mengubah CSS left dan top dari Python
    player.style.left = f"{player_pos['x']}px"
    player.style.top = f"{player_pos['y']}px"

# Fungsi Serang Asynchronous agar efek visual berjalan lancar
async def trigger_player_attack_event():
    global is_attacking, tree_hp
    is_attacking = True
    player.classList.add('player-attack-fx')
    
    # Hitung jarak (Rumus Pythagoras)
    distance = math.sqrt((player_pos["x"] - 450)**2 + (player_pos["y"] - 160)**2)
    
    # Deteksi Hit
    if distance < 90 and not is_tree_dead:
        tree_hp -= 25
        if tree_hp <= 0:
            tree_hp = 0
            handle_tree_events('death', tree_hp)
        else:
            handle_tree_events('hurt', tree_hp)
            
    # Tunggu 150 milidetik sebelum menghapus efek serang (Non-blocking)
    await asyncio.sleep(0.15)
    player.classList.remove('player-attack-fx')
    is_attacking = False

def handle_tree_events(event_type, current_hp):
    global is_tree_dead
    tree_hp_display.innerText = str(current_hp)
    
    if event_type == 'hurt':
        tree.classList.add('tree-hurt-fx')
        # Buat task background untuk menghapus efek merah setelah 300ms
        async def remove_hurt_fx():
            await asyncio.sleep(0.3)
            tree.classList.remove('tree-hurt-fx')
        asyncio.create_task(remove_hurt_fx())
        
    elif event_type == 'death':
        is_tree_dead = True
        tree.classList.add('tree-death-fx')
        reset_btn.style.display = 'inline-block'

# Mendengarkan input dari Keyboard
def on_keydown(e):
    if is_tree_dead: return
    
    key = e.key.lower()
    if key in ['w', 'arrowup'] and player_pos['y'] > 10: 
        player_pos['y'] -= move_speed
    elif key in ['s', 'arrowdown'] and player_pos['y'] < 330: 
        player_pos['y'] += move_speed
    elif key in ['a', 'arrowleft'] and player_pos['x'] > 10: 
        player_pos['x'] -= move_speed
    elif key in ['d', 'arrowright'] and player_pos['x'] < 530: 
        player_pos['x'] += move_speed
    elif key == ' ' and not is_attacking:
        # Jalankan fungsi serang secara async
        asyncio.create_task(trigger_player_attack_event())
        
    render_positions()

# Event tombol Reset
def reset_game(e):
    global tree_hp, is_tree_dead
    tree_hp = 100
    tree_hp_display.innerText = str(tree_hp)
    is_tree_dead = False
    tree.className = 'game-object' # Bersihkan class death/hurt
    reset_btn.style.display = 'none'

# Mendaftarkan fungsi Python ke dalam Event Listener Browser menggunakan create_proxy
document.addEventListener('keydown', create_proxy(on_keydown))
reset_btn.addEventListener('click', create_proxy(reset_game))

# Eksekusi render pertama saat file diload
render_positions()