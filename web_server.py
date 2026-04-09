from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
import sqlite3
import hashlib
import random

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# База данных
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users 
             (username TEXT PRIMARY KEY, password TEXT, class TEXT, level INT, gold INT, hp INT, location TEXT)''')
conn.commit()

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>MMO RPG</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        body { background: #0a0a1a; color: #0f0; font-family: monospace; padding: 20px; max-width: 800px; margin: 0 auto; }
        .log { background: #000; border: 2px solid #ff0; height: 400px; overflow-y: auto; padding: 10px; margin: 10px 0; }
        input, select, button { padding: 10px; margin: 5px; background: #222; color: #0f0; border: 1px solid #ff0; }
        button { cursor: pointer; }
        .error { color: #f00; }
        .success { color: #0f0; }
        .combat { color: #fa0; }
        h1 { color: #ff0; text-align: center; }
    </style>
</head>
<body>
<h1>⚔️ MMO RPG ⚔️</h1>

<div id="auth">
    <h3>📝 Регистрация</h3>
    <input type="text" id="regUser" placeholder="Логин"><br>
    <input type="password" id="regPass" placeholder="Пароль"><br>
    <select id="regClass">
        <option>воин</option><option>маг</option><option>лучник</option><option>лекарь</option>
    </select><br>
    <button onclick="register()">Зарегистрироваться</button>
    
    <h3>🔐 Вход</h3>
    <input type="text" id="loginUser" placeholder="Логин"><br>
    <input type="password" id="loginPass" placeholder="Пароль"><br>
    <button onclick="login()">Войти</button>
</div>

<div id="game" style="display:none;">
    <div class="log" id="log"></div>
    <input type="text" id="cmd" placeholder="Введите /help" style="width: 80%;">
    <button onclick="sendCmd()">Отправить</button>
</div>

<script>
const socket = io();
let username = "";

function addMsg(text, type="info") {
    const log = document.getElementById('log');
    if(log) {
        let div = document.createElement('div');
        div.className = type;
        div.innerHTML = text;
        log.appendChild(div);
        log.scrollTop = log.scrollHeight;
    }
}

function register() {
    let user = document.getElementById('regUser').value;
    let pass = document.getElementById('regPass').value;
    let cls = document.getElementById('regClass').value;
    if(!user || !pass) { alert("Заполните все поля!"); return; }
    socket.emit('register', {user, pass, class: cls});
}

function login() {
    username = document.getElementById('loginUser').value;
    let pass = document.getElementById('loginPass').value;
    if(!username || !pass) { alert("Заполните все поля!"); return; }
    socket.emit('login', {user: username, pass});
}

function sendCmd() {
    let cmd = document.getElementById('cmd').value;
    if(!cmd) return;
    addMsg("> " + cmd);
    socket.emit('cmd', {cmd, user: username});
    document.getElementById('cmd').value = "";
}

socket.on('register_ok', (msg) => { alert(msg); });
socket.on('register_fail', (msg) => { alert(msg); });

socket.on('login_ok', (data) => {
    document.getElementById('auth').style.display = 'none';
    document.getElementById('game').style.display = 'block';
    addMsg("✨ Добро пожаловать, " + data.class + " " + username + "!", "success");
    addMsg("🏆 Уровень " + data.level + " | 💰 " + data.gold + " золота", "success");
    addMsg("📜 Введите /help для списка команд", "info");
});

socket.on('login_fail', (msg) => { alert(msg); });

socket.on('message', (data) => { addMsg(data.text, data.type); });
socket.on('status', (data) => { document.title = "❤️" + data.hp + " | 💰" + data.gold; });

document.getElementById('cmd').addEventListener('keypress', function(e) {
    if(e.key === 'Enter') sendCmd();
});
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML)

@socketio.on('register')
def register(data):
    user = data['user']
    pwd = hashlib.md5(data['pass'].encode()).hexdigest()
    cls = data['class']
    
    c.execute("SELECT * FROM users WHERE username=?", (user,))
    if c.fetchone():
        emit('register_fail', '❌ Игрок уже существует')
        return
    
    stats = {'воин': (120, 15), 'маг': (70, 5), 'лучник': (85, 12), 'лекарь': (90, 8)}
    hp, dmg = stats.get(cls, (100, 10))
    
    c.execute("INSERT INTO users VALUES (?, ?, ?, 1, 100, ?, 'город')", (user, pwd, cls, hp))
    conn.commit()
    emit('register_ok', f'✅ {cls} {user}, вы зарегистрированы! Теперь войдите.')

@socketio.on('login')
def login(data):
    user = data['user']
    pwd = hashlib.md5(data['pass'].encode()).hexdigest()
    
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (user, pwd))
    row = c.fetchone()
    if not row:
        emit('login_fail', '❌ Неверный логин или пароль')
        return
    
    emit('login_ok', {'class': row[2], 'level': row[3], 'gold': row[4]})

@socketio.on('cmd')
def cmd(data):
    user = data['user']
    cmd_text = data['cmd'].strip()
    
    c.execute("SELECT * FROM users WHERE username=?", (user,))
    row = list(c.fetchone())
    if not row: return
    
    if cmd_text == '/help':
        msg = "/stats - характеристики\n/inv - инвентарь\n/fight - бой\n/attack - атаковать\n/run - убежать\n/go [город/лес/пещера/замок]\n/chat [текст]"
        emit('message', {'text': msg, 'type': 'info'})
    
    elif cmd_text == '/stats':
        msg = f"📊 {user}\n❤️ HP: {row[5]}\n⭐ Уровень: {row[3]}\n💰 Золото: {row[4]}\n📍 Локация: {row[6]}"
        emit('message', {'text': msg, 'type': 'info'})
    
    elif cmd_text == '/inv':
        emit('message', {'text': "🎒 Хлеб x3, Малая зелье жизни x2", 'type': 'info'})
    
    elif cmd_text == '/fight':
        if row[6] == 'город':
            emit('message', {'text': "🏰 В городе нет монстров! Идите в лес /go лес", 'type': 'error'})
        else:
            emit('message', {'text': "⚔️ На вас напал Волк! Введите /attack", 'type': 'combat'})
    
    elif cmd_text == '/attack':
        dmg = random.randint(10, 25)
        new_hp = row[5] - random.randint(5, 15)
        if new_hp <= 0:
            new_hp = 50
            emit('message', {'text': f"💀 Вы погибли! Возрождение в городе с {new_hp} HP", 'type': 'error'})
            row[6] = 'город'
        else:
            emit('message', {'text': f"⚔️ Вы нанесли {dmg} урона! Монстр атакует. У вас {new_hp} HP", 'type': 'combat'})
        row[5] = new_hp
        c.execute("UPDATE users SET hp=?, location=? WHERE username=?", (row[5], row[6], user))
        conn.commit()
        emit('status', {'hp': row[5], 'gold': row[4]})
    
    elif cmd_text == '/run':
        emit('message', {'text': "🏃 Вы сбежали с поля боя!", 'type': 'success'})
    
    elif cmd_text.startswith('/go '):
        loc = cmd_text[4:]
        if loc in ['город', 'лес', 'пещера', 'замок']:
            c.execute("UPDATE users SET location=? WHERE username=?", (loc, user))
            conn.commit()
            emit('message', {'text': f"✅ Вы переместились в {loc}", 'type': 'success'})
        else:
            emit('message', {'text': "❌ Неверная локация", 'type': 'error'})
    
    elif cmd_text.startswith('/chat '):
        msg = cmd_text[6:]
        emit('message', {'text': f"💬 {user}: {msg}", 'type': 'info'}, broadcast=True)
    
    else:
        emit('message', {'text': "❌ Неизвестная команда. /help", 'type': 'error'})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10000)
