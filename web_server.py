from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
import sqlite3
import json
import random
import threading
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# Данные игроков
online_players = {}
db = sqlite3.connect('database.db', check_same_thread=False)

# Инициализация БД
cursor = db.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS players (
    username TEXT PRIMARY KEY,
    password TEXT,
    class_name TEXT,
    level INTEGER DEFAULT 1,
    exp INTEGER DEFAULT 0,
    gold INTEGER DEFAULT 100,
    location TEXT DEFAULT 'город',
    hp INTEGER DEFAULT 100,
    mp INTEGER DEFAULT 50,
    str_base INTEGER DEFAULT 10,
    def_base INTEGER DEFAULT 5,
    int_base INTEGER DEFAULT 5,
    agi_base INTEGER DEFAULT 5
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
    username TEXT,
    item_name TEXT,
    quantity INTEGER
)''')
db.commit()

CLASSES = {
    'воин': {'hp': 120, 'mp': 30, 'str': 15, 'def': 10, 'int': 5, 'agi': 8},
    'маг': {'hp': 70, 'mp': 100, 'str': 5, 'def': 5, 'int': 18, 'agi': 7},
    'лучник': {'hp': 85, 'mp': 40, 'str': 12, 'def': 6, 'int': 8, 'agi': 15},
    'лекарь': {'hp': 90, 'mp': 80, 'str': 8, 'def': 8, 'int': 14, 'agi': 9}
}

MONSTERS = {
    'лес': [
        {'name': 'Волк', 'hp': 45, 'dmg': 8, 'exp': 30, 'gold': 15},
        {'name': 'Гоблин', 'hp': 35, 'dmg': 6, 'exp': 25, 'gold': 10},
    ],
    'пещера': [
        {'name': 'Скелет', 'hp': 55, 'dmg': 10, 'exp': 45, 'gold': 25},
        {'name': 'Призрак', 'hp': 40, 'dmg': 12, 'exp': 50, 'gold': 30},
    ],
    'замок': [
        {'name': 'Рыцарь', 'hp': 80, 'dmg': 15, 'exp': 80, 'gold': 50},
        {'name': 'Маг-отступник', 'hp': 60, 'dmg': 18, 'exp': 90, 'gold': 60},
    ]
}

LOCATIONS = ['город', 'лес', 'пещера', 'замок']

# HTML страница с Pyodide
HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>MMO RPG - Браузерная игра</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script src="https://cdn.jsdelivr.net/pyodide/v0.24.1/full/pyodide.js"></script>
    <style>
        * { box-sizing: border-box; user-select: none; }
        body {
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            color: #eee;
            font-family: 'Courier New', monospace;
            padding: 20px;
            margin: 0;
            min-height: 100vh;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: rgba(0,0,0,0.7);
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 0 20px rgba(0,0,0,0.5);
        }
        h1 {
            text-align: center;
            color: #ffd700;
            text-shadow: 2px 2px 4px #000;
            margin-top: 0;
        }
        #output {
            background: #0a0a1a;
            border: 2px solid #ffd700;
            border-radius: 10px;
            height: 400px;
            overflow-y: auto;
            padding: 10px;
            font-size: 12px;
            font-family: monospace;
            white-space: pre-wrap;
            margin-bottom: 10px;
        }
        #input-line {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }
        #command-input {
            flex: 1;
            background: #1a1a2e;
            border: 1px solid #ffd700;
            color: #0f0;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 14px;
        }
        #command-input:focus { outline: none; border-color: #0f0; }
        button {
            background: #ffd700;
            color: #000;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover { background: #ffed4a; }
        .status {
            display: flex;
            gap: 20px;
            margin-top: 10px;
            padding: 10px;
            background: #0a0a1a;
            border-radius: 10px;
            font-size: 12px;
        }
        .login-panel {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .login-panel input, .login-panel select {
            padding: 10px;
            border-radius: 5px;
            border: 1px solid #ffd700;
            background: #1a1a2e;
            color: #eee;
        }
        .error { color: #ff4444; }
        .success { color: #44ff44; }
        .system { color: #ffaa44; }
        .combat { color: #ff6644; }
    </style>
</head>
<body>
<div class="container">
    <h1>⚔️ MMO RPG ⚔️</h1>
    
    <div id="login-area">
        <div class="login-panel">
            <input type="text" id="reg-username" placeholder="Логин">
            <input type="password" id="reg-password" placeholder="Пароль">
            <select id="reg-class">
                <option value="воин">Воин</option>
                <option value="маг">Маг</option>
                <option value="лучник">Лучник</option>
                <option value="лекарь">Лекарь</option>
            </select>
            <button onclick="register()">Регистрация</button>
        </div>
        <div class="login-panel">
            <input type="text" id="login-username" placeholder="Логин">
            <input type="password" id="login-password" placeholder="Пароль">
            <button onclick="login()">Вход</button>
        </div>
    </div>
    
    <div id="game-area" style="display:none;">
        <div id="output"></div>
        <div id="input-line">
            <input type="text" id="command-input" placeholder="Введите команду... /help">
            <button onclick="sendCommand()">➤</button>
        </div>
        <div class="status" id="status">Статус: не в бою</div>
    </div>
</div>

<script>
    let socket = null;
    let username = null;
    let pyodide = null;
    
    // Загрузка Pyodide
    async function loadPyodide() {
        addOutput("Загрузка движка Python...", "system");
        pyodide = await loadPyodide();
        await pyodide.runPythonAsync(`
import js
import json

class GameClient:
    def __init__(self):
        self.username = None
    
    def handle_command(self, cmd):
        if cmd.startswith('/stats'):
            js.socket.emit('stats')
        elif cmd.startswith('/inv'):
            js.socket.emit('inventory')
        elif cmd.startswith('/use '):
            item = cmd[5:]
            js.socket.emit('use_item', item)
        elif cmd == '/fight':
            js.socket.emit('battle_start')
        elif cmd == '/attack':
            js.socket.emit('battle_action', 'attack')
        elif cmd == '/run':
            js.socket.emit('battle_action', 'run')
        elif cmd.startswith('/go '):
            loc = cmd[4:]
            js.socket.emit('move', loc)
        elif cmd == '/location':
            js.socket.emit('get_location')
        elif cmd.startswith('/chat '):
            js.socket.emit('chat', cmd[6:])
        elif cmd == '/help':
            return "/stats - характеристики\\n/inv - инвентарь\\n/use <предмет> - использовать\\n/fight - начать бой\\n/attack - атаковать\\n/run - убежать\\n/go <локация> - переместиться\\n/location - текущая локация\\n/chat <текст> - чат\\n/help - справка"
        return None

client = GameClient()
        `);
        addOutput("✅ Движок загружен!", "success");
    }
    
    function addOutput(text, type="system") {
        const output = document.getElementById('output');
        const line = document.createElement('div');
        line.className = type;
        line.textContent = text;
        output.appendChild(line);
        output.scrollTop = output.scrollHeight;
    }
    
    async function register() {
        const username = document.getElementById('reg-username').value;
        const password = document.getElementById('reg-password').value;
        const class_name = document.getElementById('reg-class').value;
        
        if (!username || !password) {
            addOutput("Заполните все поля!", "error");
            return;
        }
        
        socket.emit('register', {username, password, class_name});
    }
    
    async function login() {
        username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        
        if (!username || !password) {
            addOutput("Заполните все поля!", "error");
            return;
        }
        
        socket.emit('login', {username, password});
    }
    
    function sendCommand() {
        const input = document.getElementById('command-input');
        const cmd = input.value.trim();
        if (!cmd) return;
        
        addOutput(`> ${cmd}`, "system");
        input.value = "";
        
        if (pyodide) {
            pyodide.runPythonAsync(`
result = client.handle_command('${cmd.replace(/'/g, "\\'")}')
if result:
    js.addOutput(result, "system")
            `);
        }
    }
    
    // Подключение к серверу
    socket = io();
    
    socket.on('connect', () => {
        addOutput("🟢 Подключено к серверу", "success");
        loadPyodide();
    });
    
    socket.on('register_response', (data) => {
        if (data.success) {
            addOutput(`✅ ${data.message}`, "success");
        } else {
            addOutput(`❌ ${data.message}`, "error");
        }
    });
    
    socket.on('login_response', (data) => {
        if (data.success) {
            addOutput(`✨ Добро пожаловать, ${data.class_name}!`, "success");
            document.getElementById('login-area').style.display = 'none';
            document.getElementById('game-area').style.display = 'block';
            addOutput("Введите /help для списка команд", "system");
        } else {
            addOutput(`❌ ${data.message}`, "error");
        }
    });
    
    socket.on('stats', (data) => {
        addOutput(`📊 ХАРАКТЕРИСТИКИ\n❤️ HP: ${data.hp}  💙 MP: ${data.mp}\n⚔️ Сила: ${data.str}  🛡️ Защита: ${data.def}\n⭐ Уровень: ${data.level}  💰 Золото: ${data.gold}\n📍 Локация: ${data.location}`, "system");
    });
    
    socket.on('inventory', (data) => {
        let msg = "🎒 ИНВЕНТАРЬ\n";
        if (Object.keys(data).length === 0) msg += "Пусто";
        else for (let [item, qty] of Object.entries(data)) msg += `${item}: ${qty}\n`;
        addOutput(msg, "system");
    });
    
    socket.on('battle_response', (msg) => {
        addOutput(`⚔️ ${msg}`, "combat");
    });
    
    socket.on('chat_message', (data) => {
        addOutput(`💬 ${data.username}: ${data.message}`, "system");
    });
    
    socket.on('move_response', (data) => {
        if (data.success) addOutput(`✅ ${data.message}`, "success");
        else addOutput(`❌ ${data.message}`, "error");
    });
    
    socket.on('location', (loc) => {
        addOutput(`📍 Вы в локации: ${loc}`, "system");
    });
    
    socket.on('disconnect', () => {
        addOutput("🔴 Отключено от сервера", "error");
    });
    
    // Enter для отправки
    document.getElementById('command-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendCommand();
    });
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

# Socket.IO обработчики
@socketio.on('register')
def handle_register(data):
    # Регистрация (упрощённая версия)
    emit('register_response', {'success': True, 'message': 'Регистрация успешна! (демо-режим)'})

@socketio.on('login')
def handle_login(data):
    # Демо-режим: создаём игрока если нет
    emit('login_response', {'success': True, 'class_name': 'воин'})

@socketio.on('stats')
def handle_stats():
    emit('stats', {'hp': 100, 'mp': 50, 'str': 15, 'def': 10, 'level': 1, 'gold': 100, 'location': 'город'})

@socketio.on('inventory')
def handle_inventory():
    emit('inventory', {'Хлеб': 3, 'Зелье жизни': 2})

@socketio.on('battle_start')
def handle_battle_start():
    emit('battle_response', '⚔️ На вас напал Волк! (HP: 45)')

@socketio.on('battle_action')
def handle_battle_action(action):
    if action == 'attack':
        emit('battle_response', 'Вы нанесли 15 урона! Волк наносит 8 урона')
    elif action == 'run':
        emit('battle_response', '🏃 Вы сбежали!')

@socketio.on('move')
def handle_move(location):
    emit('move_response', {'success': True, 'message': f'Вы переместились в {location}'})

@socketio.on('get_location')
def handle_get_location():
    emit('location', 'город')

@socketio.on('chat')
def handle_chat(message):
    emit('chat_message', {'username': 'Игрок', 'message': message}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10000)