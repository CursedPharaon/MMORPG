from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
import sqlite3
import random
import hashlib

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# Подключение БД
conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц
cursor.execute('''
CREATE TABLE IF NOT EXISTS players (
    username TEXT PRIMARY KEY,
    password TEXT,
    class_name TEXT,
    level INTEGER DEFAULT 1,
    exp INTEGER DEFAULT 0,
    gold INTEGER DEFAULT 100,
    location TEXT DEFAULT 'город',
    hp INTEGER DEFAULT 100,
    mp INTEGER DEFAULT 50,
    strength INTEGER DEFAULT 10,
    defense INTEGER DEFAULT 5,
    intelligence INTEGER DEFAULT 5,
    agility INTEGER DEFAULT 8
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS inventory (
    username TEXT,
    item_name TEXT,
    quantity INTEGER
)
''')
conn.commit()

CLASSES = {
    'воин': {'hp': 120, 'mp': 30, 'strength': 15, 'defense': 10, 'intelligence': 5, 'agility': 8},
    'маг': {'hp': 70, 'mp': 100, 'strength': 5, 'defense': 5, 'intelligence': 18, 'agility': 7},
    'лучник': {'hp': 85, 'mp': 40, 'strength': 12, 'defense': 6, 'intelligence': 8, 'agility': 15},
    'лекарь': {'hp': 90, 'mp': 80, 'strength': 8, 'defense': 8, 'intelligence': 14, 'agility': 9}
}

# Игроки онлайн
online_players = {}
player_battles = {}

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>MMO RPG - Онлайн игра</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { box-sizing: border-box; }
        body {
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            color: #eee;
            font-family: 'Courier New', monospace;
            padding: 20px;
            margin: 0;
            min-height: 100vh;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: rgba(0,0,0,0.8);
            border-radius: 20px;
            padding: 20px;
        }
        h1 {
            text-align: center;
            color: #ffd700;
            text-shadow: 2px 2px 4px #000;
        }
        #output {
            background: #0a0a1a;
            border: 2px solid #ffd700;
            border-radius: 10px;
            height: 400px;
            overflow-y: auto;
            padding: 10px;
            font-size: 13px;
            white-space: pre-wrap;
            margin-bottom: 10px;
        }
        .input-area {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }
        #command-input {
            flex: 1;
            background: #1a1a2e;
            border: 1px solid #ffd700;
            color: #0f0;
            padding: 12px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 14px;
        }
        button {
            background: #ffd700;
            color: #000;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover { background: #ffed4a; }
        .login-panel {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        .login-panel input, .login-panel select {
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #ffd700;
            background: #1a1a2e;
            color: #eee;
            font-size: 14px;
        }
        .status-bar {
            display: flex;
            gap: 20px;
            margin-top: 10px;
            padding: 10px;
            background: #0a0a1a;
            border-radius: 10px;
            font-size: 12px;
        }
        .error { color: #ff6666; }
        .success { color: #66ff66; }
        .combat { color: #ffaa66; }
        .info { color: #66aaff; }
    </style>
</head>
<body>
<div class="container">
    <h1>⚔️ MMO RPG ⚔️</h1>
    
    <div id="loginScreen">
        <div class="login-panel">
            <h3>Регистрация</h3>
            <input type="text" id="reg-user" placeholder="Логин">
            <input type="password" id="reg-pass" placeholder="Пароль">
            <select id="reg-class">
                <option value="воин">⚔️ Воин</option>
                <option value="маг">🔮 Маг</option>
                <option value="лучник">🏹 Лучник</option>
                <option value="лекарь">💚 Лекарь</option>
            </select>
            <button onclick="register()">Зарегистрироваться</button>
        </div>
        <div class="login-panel">
            <h3>Вход</h3>
            <input type="text" id="login-user" placeholder="Логин">
            <input type="password" id="login-pass" placeholder="Пароль">
            <button onclick="login()">Войти</button>
        </div>
    </div>
    
    <div id="gameScreen" style="display:none;">
        <div id="output"></div>
        <div class="input-area">
            <input type="text" id="command-input" placeholder="Введите команду... /help">
            <button onclick="sendCommand()">➤</button>
        </div>
        <div class="status-bar" id="statusBar">
            📍 Загрузка...
        </div>
    </div>
</div>

<script>
    let socket = io();
    let currentUsername = null;
    
    function addMessage(text, type = "info") {
        const output = document.getElementById('output');
        if (!output) return;
        const div = document.createElement('div');
        div.className = type;
        div.textContent = text;
        output.appendChild(div);
        output.scrollTop = output.scrollHeight;
    }
    
    function register() {
        const username = document.getElementById('reg-user').value.trim();
        const password = document.getElementById('reg-pass').value;
        const class_name = document.getElementById('reg-class').value;
        
        if (!username || !password) {
            addMessage("❌ Заполните все поля!", "error");
            return;
        }
        
        socket.emit('register', {username, password, class_name});
    }
    
    function login() {
        const username = document.getElementById('login-user').value.trim();
        const password = document.getElementById('login-pass').value;
        
        if (!username || !password) {
            addMessage("❌ Заполните все поля!", "error");
            return;
        }
        
        socket.emit('login', {username, password});
    }
    
    function sendCommand() {
        const input = document.getElementById('command-input');
        const cmd = input.value.trim();
        if (!cmd) return;
        
        addMessage(`> ${cmd}`, "info");
        input.value = "";
        
        socket.emit('command', {command: cmd});
    }
    
    socket.on('register_result', (data) => {
        if (data.success) {
            addMessage(`✅ ${data.message}`, "success");
        } else {
            addMessage(`❌ ${data.message}`, "error");
        }
    });
    
    socket.on('login_result', (data) => {
        if (data.success) {
            currentUsername = data.username;
            addMessage(`✨ Добро пожаловать, ${data.class_name} ${data.username}! ✨`, "success");
            addMessage(`🏆 Уровень ${data.level} | 💰 ${data.gold} золота`, "info");
            addMessage(`💡 Введите /help для списка команд`, "info");
            document.getElementById('loginScreen').style.display = 'none';
            document.getElementById('gameScreen').style.display = 'block';
        } else {
            addMessage(`❌ ${data.message}`, "error");
        }
    });
    
    socket.on('game_message', (data) => {
        addMessage(data.text, data.type);
    });
    
    socket.on('update_status', (data) => {
        const statusBar = document.getElementById('statusBar');
        if (statusBar) {
            statusBar.innerHTML = `❤️ HP: ${data.hp} | 💙 MP: ${data.mp} | ⭐ Ур.${data.level} | 💰 ${data.gold}💰 | 📍 ${data.location}`;
        }
    });
    
    socket.on('disconnect', () => {
        addMessage("🔴 Потеряно соединение с сервером!", "error");
    });
    
    document.getElementById('command-input')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendCommand();
    });
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@socketio.on('register')
def handle_register(data):
    username = data['username']
    password = hashlib.md5(data['password'].encode()).hexdigest()
    class_name = data['class_name']
    
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM players WHERE username=?", (username,))
    if cursor.fetchone():
        emit('register_result', {'success': False, 'message': 'Игрок с таким именем уже существует'})
        return
    
    stats = CLASSES.get(class_name, CLASSES['воин'])
    cursor.execute('''
        INSERT INTO players (username, password, class_name, hp, mp, strength, defense, intelligence, agility)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (username, password, class_name, stats['hp'], stats['mp'], 
          stats['strength'], stats['defense'], stats['intelligence'], stats['agility']))
    
    cursor.execute("INSERT INTO inventory VALUES (?, 'Хлеб', 3)", (username,))
    cursor.execute("INSERT INTO inventory VALUES (?, 'Малая зелье жизни', 2)", (username,))
    conn.commit()
    
    emit('register_result', {'success': True, 'message': f'{class_name.capitalize()} {username}, вы зарегистрированы! Теперь войдите.'})

@socketio.on('login')
def handle_login(data):
    username = data['username']
    password = hashlib.md5(data['password'].encode()).hexdigest()
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players WHERE username=? AND password=?", (username, password))
    player = cursor.fetchone()
    
    if not player:
        emit('login_result', {'success': False, 'message': 'Неверный логин или пароль'})
        return
    
    if username in online_players:
        emit('login_result', {'success': False, 'message': 'Этот игрок уже в игре!'})
        return
    
    # Загружаем данные игрока
    player_data = {
        'username': player[0],
        'class_name': player[2],
        'level': player[3],
        'exp': player[4],
        'gold': player[5],
        'location': player[6],
        'hp': player[7],
        'mp': player[8],
        'strength': player[9],
        'defense': player[10],
        'intelligence': player[11],
        'agility': player[12]
    }
    
    online_players[username] = player_data
    emit('login_result', {
        'success': True, 
        'username': username,
        'class_name': player_data['class_name'],
        'level': player_data['level'],
        'gold': player_data['gold']
    })
    emit('update_status', {'hp': player_data['hp'], 'mp': player_data['mp'], 
                           'level': player_data['level'], 'gold': player_data['gold'], 
                           'location': player_data['location']})

@socketio.on('command')
def handle_command(data):
    username = None
    for u in online_players:
        if u in request.sid:
            username = u
            break
    
    if not username:
        emit('game_message', {'text': '❌ Вы не авторизованы!', 'type': 'error'})
        return
    
    cmd = data['command'].strip()
    player = online_players[username]
    
    if cmd == '/help':
        help_text = '''📜 ДОСТУПНЫЕ КОМАНДЫ:
/stats - характеристики
/inv - инвентарь
/use [предмет] - использовать предмет
/fight - начать бой
/attack - атаковать в бою
/run - сбежать
/go [локация] - переместиться (город, лес, пещера, замок)
/location - текущая локация
/chat [текст] - написать в чат
/help - справка'''
        emit('game_message', {'text': help_text, 'type': 'info'})
    
    elif cmd == '/stats':
        text = f'''📊 ХАРАКТЕРИСТИКИ {username}
❤️ HP: {player['hp']}  💙 MP: {player['mp']}
⚔️ Сила: {player['strength']}  🛡️ Защита: {player['defense']}
🔮 Интеллект: {player['intelligence']}  🏃 Ловкость: {player['agility']}
⭐ Уровень: {player['level']}  📈 Опыт: {player['exp']}/{player['level']*100}
💰 Золото: {player['gold']}  📍 Локация: {player['location']}'''
        emit('game_message', {'text': text, 'type': 'info'})
    
    elif cmd == '/inv':
        cursor = conn.cursor()
        cursor.execute("SELECT item_name, quantity FROM inventory WHERE username=?", (username,))
        items = cursor.fetchall()
        if not items:
            emit('game_message', {'text': '🎒 Инвентарь пуст', 'type': 'info'})
        else:
            text = '🎒 ИНВЕНТАРЬ:\n' + '\n'.join([f'{i[0]}: {i[1]}' for i in items])
            emit('game_message', {'text': text, 'type': 'info'})
    
    elif cmd.startswith('/use '):
        item = cmd[5:]
        if item == 'Малая зелье жизни':
            cursor = conn.cursor()
            cursor.execute("SELECT quantity FROM inventory WHERE username=? AND item_name=?", (username, item))
            row = cursor.fetchone()
            if row and row[0] > 0:
                new_hp = min(player['hp'] + 30, CLASSES[player['class_name']]['hp'] + (player['level']-1)*5)
                player['hp'] = new_hp
                cursor.execute("UPDATE inventory SET quantity=? WHERE username=? AND item_name=?", (row[0]-1, username, item))
                conn.commit()
                emit('game_message', {'text': f'✨ Вы восстановили 30 HP! Текущее HP: {player["hp"]}', 'type': 'success'})
                emit('update_status', {'hp': player['hp'], 'mp': player['mp'], 'level': player['level'], 'gold': player['gold'], 'location': player['location']})
            else:
                emit('game_message', {'text': '❌ У вас нет этого предмета!', 'type': 'error'})
        else:
            emit('game_message', {'text': '❌ Нельзя использовать этот предмет', 'type': 'error'})
    
    elif cmd == '/fight':
        if player['location'] == 'город':
            emit('game_message', {'text': '🏰 В городе нет монстров! Идите в лес, пещеру или замок.', 'type': 'error'})
        else:
            monsters = {
                'лес': ['Волк (45 HP, 8 дмг)', 'Гоблин (35 HP, 6 дмг)'],
                'пещера': ['Скелет (55 HP, 10 дмг)', 'Призрак (40 HP, 12 дмг)'],
                'замок': ['Рыцарь (80 HP, 15 дмг)', 'Маг (60 HP, 18 дмг)']
            }
            monster = random.choice(monsters.get(player['location'], ['Монстр (50 HP, 10 дмг)']))
            emit('game_message', {'text': f'⚔️ На вас напал {monster}! Введите /attack чтобы атаковать, /run чтобы убежать.', 'type': 'combat'})
    
    elif cmd == '/attack':
        dmg = random.randint(8, 20) + player['strength']//2
        emit('game_message', {'text': f'⚔️ Вы нанесли {dmg} урона! Монстр атакует в ответ.', 'type': 'combat'})
        player['hp'] -= random.randint(5, 12)
        if player['hp'] <= 0:
            player['hp'] = CLASSES[player['class_name']]['hp'] // 2
            emit('game_message', {'text': f'💀 Вы погибли! Вас воскресили в городе с {player["hp"]} HP', 'type': 'error'})
            player['location'] = 'город'
        emit('update_status', {'hp': player['hp'], 'mp': player['mp'], 'level': player['level'], 'gold': player['gold'], 'location': player['location']})
    
    elif cmd == '/run':
        if random.random() < 0.5:
            emit('game_message', {'text': '🏃 Вы успешно сбежали!', 'type': 'success'})
        else:
            player['hp'] -= random.randint(5, 15)
            emit('game_message', {'text': '🏃 Побег не удался! Монстр наносит удар.', 'type': 'error'})
            emit('update_status', {'hp': player['hp'], 'mp': player['mp'], 'level': player['level'], 'gold': player['gold'], 'location': player['location']})
    
    elif cmd.startswith('/go '):
        loc = cmd[4:]
        if loc in ['город', 'лес', 'пещера', 'замок']:
            player['location'] = loc
            emit('game_message', {'text': f'✅ Вы переместились в {loc}', 'type': 'success'})
            emit('update_status', {'hp': player['hp'], 'mp': player['mp'], 'level': player['level'], 'gold': player['gold'], 'location': player['location']})
        else:
            emit('game_message', {'text': '❌ Неверная локация! Доступно: город, лес, пещера, замок', 'type': 'error'})
    
    elif cmd == '/location':
        emit('game_message', {'text': f'📍 Вы в локации: {player["location"]}', 'type': 'info'})
    
    elif cmd.startswith('/chat '):
        msg = cmd[6:]
        emit('game_message', {'text': f'💬 {username}: {msg}', 'type': 'info'}, broadcast=True)
    
    else:
        emit('game_message', {'text': '❌ Неизвестная команда. Введите /help', 'type': 'error'})
    
    # Сохраняем изменения в БД
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE players SET hp=?, mp=?, location=?, gold=?, level=?, exp=?
        WHERE username=?
    ''', (player['hp'], player['mp'], player['location'], player['gold'], player['level'], player['exp'], username))
    conn.commit()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10000)
