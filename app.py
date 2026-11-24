from flask import Flask, request, redirect, url_for, session, jsonify, render_template_string
import requests
import os
import sqlite3
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "OmegaProtocol_Super_Secret_Key_2026"
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)

BOT_URL = os.environ.get("BOT_URL", "http://127.0.0.1:3001").rstrip("/")
DB_FILE = "database.db"

# ==========================================
# ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT DEFAULT 'user')''')
    c.execute('''CREATE TABLE IF NOT EXISTS servers (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, ip TEXT, port INTEGER, nickname TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, text TEXT, time TEXT)''')
    
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        hashed_pw = generate_password_hash("omega123")
        c.execute("INSERT INTO users (username, password, role) VALUES ('admin', ?, 'admin')", (hashed_pw,))
    conn.commit()
    conn.close()

init_db()

# ==========================================
# ЗАЩИТА ОТ ПРЯМЫХ ССЫЛОК
# ==========================================
@app.before_request
def block_direct_url_access():
    # Запрещаем переход на защищенные страницы, если нет флага (например, ввели URL вручную)
    if request.endpoint in ['dashboard', 'server_console', 'admin']:
        if not session.get("logged_in"):
            return redirect(url_for('login'))
        if not session.get("auth_ok"):
            session.clear()
            return redirect(url_for('login'))
    return None

# ==========================================
# HTML ШАБЛОНЫ (АДАПТИРОВАННЫЕ)
# ==========================================

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Вход — HypeMC Panel</title>
    <style>
        * { box-sizing: border-box; }
        body { margin: 0; height: 100vh; display: flex; align-items: center; justify-content: center; font-family: 'Segoe UI', Arial, sans-serif; background: radial-gradient(circle at 30% 20%, #1b2735, #090a0f); color: #e0e0e0; padding: 15px; }
        .login-card { background: rgba(30, 34, 50, 0.9); padding: 30px; border-radius: 16px; box-shadow: 0 0 40px rgba(136, 255, 0, 0.15); border: 1px solid rgba(136, 255, 0, 0.2); width: 100%; max-width: 400px; text-align: center; }
        h1 { font-weight: 600; letter-spacing: 1px; margin-bottom: 20px; font-size: 28px; }
        .hype { color: #ffffff; } .mc { color: #88ff00; }
        label { display: block; margin-bottom: 6px; font-size: 14px; color: #9aa5b1; text-align: left; }
        input { width: 100%; padding: 12px 14px; margin-bottom: 15px; border-radius: 8px; border: 1px solid #3a3f55; background: #151a26; color: #e0e0e0; font-size: 15px; outline: none; transition: 0.3s; }
        input:focus { border-color: #88ff00; box-shadow: 0 0 8px rgba(136, 255, 0, 0.3); }
        button { width: 100%; padding: 13px; border: none; border-radius: 8px; background: linear-gradient(90deg, #66cc00, #88ff00); color: #0a0f1a; font-size: 17px; font-weight: bold; cursor: pointer; transition: 0.3s; margin-bottom: 15px; }
        button:hover { filter: brightness(1.1); }
        .error { color: #ff5c5c; margin-bottom: 15px; font-size: 14px; }
        .captcha-box { display: flex; align-items: center; justify-content: flex-start; gap: 10px; margin-bottom: 20px; background: #151a26; border: 1px solid #3a3f55; padding: 10px; border-radius: 8px; cursor: pointer; }
        .captcha-box input { width: 20px; height: 20px; margin: 0; cursor: pointer; }
        .captcha-box span { font-size: 14px; color: #9aa5b1; }
        .ttt-wrapper { margin-bottom: 20px; background: #151a26; border: 1px solid #3a3f55; padding: 15px; border-radius: 8px; }
        .ttt-wrapper p { font-size: 13px; color: #9aa5b1; margin-bottom: 10px; }
        .ttt-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px; width: 140px; margin: 0 auto; }
        .ttt-cell { width: 43px; height: 43px; background: #0a0c10; border: 1px solid #30363d; border-radius: 4px; display: flex; justify-content: center; align-items: center; font-size: 20px; font-weight: bold; cursor: pointer; color: #c9d1d9; font-family: 'Consolas', monospace; }
        .ttt-cell.x { color: #88ff00; }
    </style>
</head>
<body>
    <div class="login-card">
        <h1><span class="hype">Hype</span><span class="mc">MC</span></h1>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <label>Логин</label>
            <input type="text" name="username" required autocomplete="off">
            <label>Пароль</label>
            <input type="password" name="password" required>
            <div class="ttt-wrapper">
                <p>Пройдите капчу (поставьте 3 X в ряд)</p>
                <div class="ttt-grid" id="ttt-grid">
                    <div class="ttt-cell" onclick="tttClick(this)"></div>
                    <div class="ttt-cell" onclick="tttClick(this)"></div>
                    <div class="ttt-cell" onclick="tttClick(this)"></div>
                    <div class="ttt-cell" onclick="tttClick(this)"></div>
                    <div class="ttt-cell" onclick="tttClick(this)"></div>
                    <div class="ttt-cell" onclick="tttClick(this)"></div>
                    <div class="ttt-cell" onclick="tttClick(this)"></div>
                    <div class="ttt-cell" onclick="tttClick(this)"></div>
                    <div class="ttt-cell" onclick="tttClick(this)"></div>
                </div>
            </div>
            <label class="captcha-box" onclick="toggleCheck()">
                <input type="checkbox" id="robot-check" name="robot_check" onclick="event.stopPropagation()">
                <span>Я не робот</span>
            </label>
            <button type="submit">Войти</button>
        </form>
    </div>
    <script>
        let tttWon = false;
        function tttClick(cell) {
            if (tttWon || cell.innerText !== "") return;
            cell.innerText = "X"; cell.classList.add("x"); checkTTTWin();
        }
        function checkTTTWin() {
            const cells = document.querySelectorAll('.ttt-cell');
            const b = Array.from(cells).map(c => c.innerText);
            const wins = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];
            for (let w of wins) {
                if (b[w[0]] === "X" && b[w[1]] === "X" && b[w[2]] === "X") {
                    tttWon = true;
                    cells.forEach(c => { if(c.innerText === "") { c.innerText = "X"; c.classList.add("x"); }});
                    break;
                }
            }
            document.getElementById('robot-check').checked = tttWon;
        }
        function toggleCheck() {
            if (tttWon) { const chk = document.getElementById('robot-check'); chk.checked = !chk.checked; }
        }
    </script>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Сервера — HypeMC Panel</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { height: 100vh; display: flex; flex-direction: column; font-family: 'Segoe UI', sans-serif; background: #0a0c10; color: #c9d1d9; overflow: hidden; }
        body::before { content: ''; position: fixed; inset: 0; z-index: -1; background: radial-gradient(circle at 20% 20%, rgba(136,255,0,0.06), transparent 50%), radial-gradient(circle at 80% 80%, rgba(0,140,255,0.05), transparent 50%); animation: bgPulse 12s ease-in-out infinite alternate; }
        @keyframes bgPulse { 0%{opacity:0.6} 100%{opacity:1} }
        
        header { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; padding: 14px 20px; background: rgba(22,27,34,0.85); border-bottom: 1px solid rgba(136,255,0,0.15); gap: 10px; }
        h1 { font-size: 20px; color: #fff; } .hype { color: #ffffff; } .mc { color: #88ff00; }
        .user-info { color: #8b949e; font-size: 13px; } .user-info b { color: #88ff00; }
        .logout { color: #ff7b72; text-decoration: none; padding: 6px 12px; border: 1px solid rgba(255,123,114,0.4); border-radius: 6px; transition: 0.25s; font-size: 13px; margin-left: 10px; }
        .logout:hover { background: rgba(255,123,114,0.15); border-color: #ff7b72; }
        
        .main { flex: 1; padding: 20px; overflow-y: auto; position: relative; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; }
        .server-card { background: rgba(22,27,34,0.8); border: 1px solid #30363d; border-radius: 12px; padding: 15px; position: relative; transition: 0.2s; }
        .server-card:hover { border-color: #88ff00; box-shadow: 0 0 15px rgba(136,255,0,0.1); }
        .server-card h3 { color: #fff; margin-bottom: 8px; font-size: 16px; }
        .server-card p { color: #8b949e; font-size: 13px; margin-bottom: 5px; font-family: 'Consolas', monospace; }
        .server-card .nick { color: #ffb86c; margin-bottom: 12px; font-weight: bold; }
        .btn-connect { display: block; text-align: center; background: linear-gradient(90deg, #66cc00, #88ff00); color: #0a0f1a; text-decoration: none; padding: 10px; border-radius: 8px; font-weight: bold; transition: 0.2s; font-size: 14px; }
        .btn-connect:hover { filter: brightness(1.1); }
        .btn-edit { position: absolute; top: 12px; right: 12px; background: none; border: 1px solid #30363d; color: #8b949e; padding: 4px 8px; border-radius: 6px; cursor: pointer; font-size: 12px; transition: 0.2s; }
        .btn-edit:hover { border-color: #88ff00; color: #88ff00; }
        
        .btn-add { position: fixed; bottom: 20px; left: 20px; background: #88ff00; color: #0a0f1a; border: none; padding: 12px 24px; border-radius: 50px; font-size: 15px; font-weight: bold; cursor: pointer; box-shadow: 0 4px 15px rgba(136,255,0,0.4); transition: 0.2s; z-index: 100; }
        .btn-add:hover { transform: scale(1.05); }

        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); justify-content: center; align-items: center; z-index: 1000; padding: 15px; }
        .modal-content { background: #161b22; border: 1px solid #30363d; padding: 20px; border-radius: 12px; width: 100%; max-width: 400px; text-align: center; }
        .modal-content h2 { margin-bottom: 15px; color: #88ff00; font-size: 18px; }
        .modal-content input { width: 100%; padding: 12px; margin-bottom: 12px; border-radius: 8px; border: 1px solid #30363d; background: #0d1117; color: #fff; outline: none; }
        .modal-content input:focus { border-color: #88ff00; }
        .modal-content button { width: 100%; padding: 12px; background: #88ff00; color: #000; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; margin-bottom: 8px; }
        .modal-content .cancel { background: #30363d; color: #fff; }

        .chat-btn { position: fixed; bottom: 20px; right: 20px; background: #79c0ff; color: #0a0f1a; border: none; padding: 15px; border-radius: 50%; width: 55px; height: 55px; font-size: 22px; cursor: pointer; box-shadow: 0 4px 15px rgba(121,192,255,0.4); z-index: 100; display: flex; justify-content: center; align-items: center; }
        .chat-window { position: fixed; bottom: 85px; right: 20px; width: 300px; max-width: calc(100vw - 40px); height: 400px; background: #161b22; border: 1px solid #30363d; border-radius: 12px; display: none; flex-direction: column; z-index: 100; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
        .chat-header { padding: 10px 15px; background: #0d1117; border-bottom: 1px solid #30363d; font-weight: bold; color: #79c0ff; border-radius: 12px 12px 0 0; display: flex; justify-content: space-between; }
        .chat-header span { cursor: pointer; color: #ff7b72; }
        .chat-messages { flex: 1; padding: 15px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
        .chat-input { display: flex; padding: 10px; border-top: 1px solid #30363d; }
        .chat-input input { flex: 1; padding: 8px; border-radius: 6px; border: none; background: #0d1117; color: #fff; outline: none; }
        .chat-input button { background: #79c0ff; border: none; padding: 0 15px; margin-left: 5px; border-radius: 6px; cursor: pointer; font-weight: bold; }
    </style>
</head>
<body>
    <header>
        <h1><span class="hype">Hype</span><span class="mc">MC</span> Panel</h1>
        <div style="display:flex; align-items:center;">
            <span class="user-info">{{ user }} ({{ role }})</span>
            {% if role == 'admin' %}
                <a href="{{ url_for('admin') }}" style="color:#88ff00; margin-left: 10px; font-size: 13px; text-decoration: none;">Админка</a>
            {% endif %}
            <a class="logout" href="{{ url_for('logout') }}">Выйти</a>
        </div>
    </header>

    <div class="main">
        <div class="grid" id="servers-grid"></div>
    </div>

    <button class="btn-add" onclick="openModal()">+ Создать</button>

    <div class="modal" id="add-modal">
        <div class="modal-content">
            <h2 id="modal-title">Новый сервер</h2>
            <input type="hidden" id="edit-id">
            <input type="text" id="m-name" placeholder="Название" required>
            <input type="text" id="m-ip" placeholder="IP сервера" required>
            <input type="number" id="m-port" placeholder="Порт" value="25565" required>
            <input type="text" id="m-nick" placeholder="Ник бота" required>
            <button onclick="saveServer()">Сохранить</button>
            <button class="cancel" onclick="closeModal()">Отмена</button>
        </div>
    </div>

    <button class="chat-btn" onclick="toggleChat()">💬</button>
    <div class="chat-window" id="chat-window">
        <div class="chat-header">Поддержка <span onclick="toggleChat()">✖</span></div>
        <div class="chat-messages" id="chat-messages">
            <p style="color:#8b949e; font-size: 13px;">Напишите нам. Ответ придет в ближайшее время.</p>
        </div>
        <div class="chat-input">
            <input type="text" id="chat-input-text" placeholder="Сообщение..." onkeypress="if(event.key==='Enter') sendMsg()">
            <button onclick="sendMsg()">></button>
        </div>
    </div>

    <script>
        function openModal(server = null) {
            document.getElementById('add-modal').style.display = 'flex';
            if (server) {
                document.getElementById('modal-title').innerText = "Редактировать";
                document.getElementById('edit-id').value = server.id;
                document.getElementById('m-name').value = server.name;
                document.getElementById('m-ip').value = server.ip;
                document.getElementById('m-port').value = server.port;
                document.getElementById('m-nick').value = server.nickname;
            } else {
                document.getElementById('modal-title').innerText = "Новый сервер";
                document.getElementById('edit-id').value = "";
                document.getElementById('m-name').value = "";
                document.getElementById('m-ip').value = "";
                document.getElementById('m-port').value = "25565";
                document.getElementById('m-nick').value = "";
            }
        }
        function closeModal() { document.getElementById('add-modal').style.display = 'none'; }

        async function loadServers() {
            const res = await fetch('/api/get_servers');
            const servers = await res.json();
            const grid = document.getElementById('servers-grid');
            grid.innerHTML = '';
            
            if (servers.length === 0) {
                grid.innerHTML = '<p style="color:#8b949e; font-size: 14px;">Нет серверов. Нажмите "+ Создать".</p>';
                return;
            }
            servers.forEach(s => {
                const card = document.createElement('div');
                card.className = 'server-card';
                card.innerHTML = `
                    <button class="btn-edit" onclick='openModal(${JSON.stringify(s)})'>✎</button>
                    <h3>${s.name}</h3>
                    <p>IP: ${s.ip}:${s.port}</p>
                    <p class="nick">Ник: ${s.nickname}</p>
                    <a href="/console/${s.id}" class="btn-connect">Открыть</a>
                `;
                grid.appendChild(card);
            });
        }

        async function saveServer() {
            const id = document.getElementById('edit-id').value;
            const name = document.getElementById('m-name').value.trim();
            const ip = document.getElementById('m-ip').value.trim();
            const port = document.getElementById('m-port').value.trim();
            const nick = document.getElementById('m-nick').value.trim();
            if (!name || !ip || !port || !nick) return alert('Заполните все поля');
            const url = id ? '/api/edit_server' : '/api/add_server';
            const res = await fetch(url, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id, name, ip, port, nickname: nick}) });
            if (res.ok) { closeModal(); loadServers(); } else { alert('Ошибка сохранения'); }
        }

        function toggleChat() {
            const cw = document.getElementById('chat-window');
            cw.style.display = cw.style.display === 'flex' ? 'none' : 'flex';
        }

        async function sendMsg() {
            const text = document.getElementById('chat-input-text').value.trim();
            if (!text) return;
            document.getElementById('chat-input-text').value = '';
            await fetch('/api/send_chat', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text}) });
            const msgs = document.getElementById('chat-messages');
            const div = document.createElement('div');
            div.className = 'msg my'; 
            div.style = "background: #79c0ff; color: #000; align-self: flex-end; padding: 8px 12px; border-radius: 8px; font-size: 13px; max-width: 80%;";
            div.innerHTML = `<b>Вы:</b><br>${text}`;
            msgs.appendChild(div);
            msgs.scrollTop = msgs.scrollHeight;
        }
        loadServers();
    </script>
</body>
</html>
"""

CONSOLE_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Консоль — HypeMC Panel</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { height: 100vh; display: flex; flex-direction: column; font-family: 'Consolas', 'Courier New', monospace; background: #0a0c10; color: #c9d1d9; overflow: hidden; }
        header { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; padding: 12px 20px; background: rgba(22,27,34,0.85); border-bottom: 1px solid rgba(136,255,0,0.15); gap: 10px; }
        h1 { font-size: 18px; color: #fff; } .hype { color: #ffffff; } .mc { color: #88ff00; }
        .back-btn { color: #8b949e; text-decoration: none; font-size: 13px; margin-right: 10px; padding: 6px 10px; border: 1px solid #30363d; border-radius: 6px; transition: 0.2s; }
        .back-btn:hover { border-color: #88ff00; color: #88ff00; }
        .info { font-size: 12px; color: #8b949e; }
        
        .main { flex: 1; display: flex; flex-direction: column; padding: 15px 20px; overflow: hidden; }
        #console-output { flex: 1; overflow-y: auto; background: rgba(10,12,16,0.85); border: 1px solid #21262d; border-radius: 10px; padding: 15px; font-size: 13px; line-height: 1.6; scroll-behavior: smooth; }
        .line { margin-bottom: 5px; white-space: pre-wrap; word-break: break-all; }
        .line .prompt { color: #88ff00; user-select: none; }
        .line .cmd { color: #79c0ff; }
        .line .resp { color: #7ee787; }
        .line .err { color: #ff7b72; }
        .line .system { color: #8b949e; font-style: italic; }
        .line .time { color: #484f58; font-size: 11px; margin-right: 6px; }
        .line .chat-user { color: #ffb86c; font-weight: bold; }
        .line .chat-msg { color: #f8f8f2; }
        
        .input-row { display: flex; margin-top: 10px; gap: 8px; }
        #cmd-input { flex: 1; padding: 12px 14px; border-radius: 10px; border: 1px solid #30363d; background: rgba(22,27,34,0.9); color: #c9d1d9; font-family: 'Consolas', monospace; font-size: 14px; outline: none; }
        #cmd-input:focus { border-color: #88ff00; box-shadow: 0 0 10px rgba(136,255,0,0.18); }
        #send-btn { padding: 0 20px; border: none; border-radius: 10px; cursor: pointer; background: linear-gradient(135deg, #66cc00, #88ff00); color: #0a0f1a; font-weight: bold; font-size: 14px; transition: 0.2s; }
        #send-btn:hover { filter: brightness(1.1); }
    </style>
</head>
<body>
    <header>
        <div style="display:flex; align-items:center;">
            <a href="/dashboard" class="back-btn">← Назад</a>
            <h1>Консоль: {{ server.name }}</h1>
        </div>
        <div class="info">
            <span style="color:#88ff00;">{{ server.ip }}:{{ server.port }}</span> | 
            <span style="color:#ffb86c;">{{ server.nickname }}</span>
        </div>
    </header>

    <div class="main">
        <div id="console-output">
            <div class="line"><span class="system">Подключение...</span></div>
        </div>
        <form class="input-row" id="cmd-form">
            <input type="text" id="cmd-input" placeholder="Введите команду..." autocomplete="off" autofocus>
            <button type="submit" id="send-btn">➤</button>
        </form>
    </div>
    <script>
        const output = document.getElementById('console-output');
        const form = document.getElementById('cmd-form');
        const input = document.getElementById('cmd-input');
        let lastChatLength = -1;
        let botOfflineReported = false;

        function now() { const d = new Date(); return d.toLocaleTimeString('ru-RU', {hour:'2-digit', minute:'2-digit', second:'2-digit'}); }
        function appendLine(html, isError = false) {
            const div = document.createElement('div');
            div.className = 'line';
            div.innerHTML = `<span class="time">${now()}</span> ` + html;
            output.appendChild(div);
            output.scrollTop = output.scrollHeight;
        }

        window.onload = async () => {
            appendLine(`<span class="system">Запрос боту на подключение к {{ server.ip }}:{{ server.port }}...</span>`);
            await fetch('/api/connect', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ host: "{{ server.ip }}", port: "{{ server.port }}", username: "{{ server.nickname }}" }) });
        };

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const cmd = input.value.trim();
            if (!cmd) return;
            input.value = '';
            appendLine(`<span class="prompt">></span> <span class="cmd">${cmd}</span>`);
            try {
                const res = await fetch('/api/command', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ command: cmd }) });
                const data = await res.json();
                if (data.status === 'ok') { appendLine(`<span class="resp">${data.response}</span>`); } 
                else { appendLine(`<span class="err">${data.message || 'Ошибка'}</span>`, true); }
            } catch (err) { appendLine(`<span class="err">Ошибка сети: ${err.message}</span>`, true); }
        });

        async function fetchChat() {
            try {
                const res = await fetch('/api/chat');
                const messages = await res.json();
                if (messages.length === 0 && !botOfflineReported) {
                    appendLine(`<span class="err">[ОШИБКА] Сайт не может получить данные от бота.</span>`, true);
                    botOfflineReported = true; return;
                }
                if (messages.length > lastChatLength) {
                    let newMessages = lastChatLength === -1 ? [] : messages.slice(lastChatLength);
                    newMessages.forEach(msg => {
                        if (msg.type === 'chat') { appendLine(`<span class="chat-user">[Сервер]</span> <span class="chat-msg">${msg.text}</span>`); }
                        else if (msg.type === 'system') { appendLine(`<span class="system">[Система] ${msg.text}</span>`); }
                    });
                    lastChatLength = messages.length;
                    botOfflineReported = false;
                }
            } catch (err) {}
        }
        setInterval(fetchChat, 1000);
    </script>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Админ — HypeMC Panel</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { height: 100vh; display: flex; flex-direction: column; font-family: 'Segoe UI', sans-serif; background: #0a0c10; color: #c9d1d9; }
        header { display: flex; justify-content: space-between; align-items: center; padding: 14px 20px; background: rgba(22,27,34,0.85); border-bottom: 1px solid rgba(255,123,114,0.4); }
        h1 { font-size: 20px; color: #ff7b72; }
        .back-btn { color: #8b949e; text-decoration: none; font-size: 13px; margin-right: 10px; padding: 6px 10px; border: 1px solid #30363d; border-radius: 6px; }
        
        .container { padding: 20px; display: flex; flex-direction: column; gap: 20px; max-width: 900px; margin: 0 auto; width: 100%; }
        .panel { background: rgba(22,27,34,0.8); border: 1px solid #30363d; border-radius: 12px; padding: 15px; }
        .panel h2 { margin-bottom: 12px; color: #88ff00; font-size: 16px; border-bottom: 1px solid #30363d; padding-bottom: 8px; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #30363d; font-size: 13px; }
        th { color: #8b949e; }
        
        .add-form { display: flex; flex-direction: column; gap: 8px; margin-bottom: 15px; }
        .add-form input { width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #30363d; background: #0d1117; color: #fff; outline: none; }
        .add-form input:focus { border-color: #88ff00; }
        .add-form button { padding: 10px; background: #88ff00; color: #000; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; }
        
        .btn-del { background: #ff7b72; color: #000; border: none; padding: 4px 8px; border-radius: 5px; cursor: pointer; font-weight: bold; font-size: 12px; }
        .chat-msg { padding: 10px; background: #0d1117; border: 1px solid #30363d; border-radius: 8px; margin-bottom: 8px; font-size: 13px; }
    </style>
</head>
<body>
    <header>
        <div style="display:flex; align-items:center;">
            <a href="/dashboard" class="back-btn">← Назад</a>
            <h1>Админ-панель</h1>
        </div>
    </header>

    <div class="container">
        <div class="panel">
            <h2>Пользователи</h2>
            <div class="add-form">
                <input type="text" id="new-user" placeholder="Логин">
                <input type="password" id="new-pass" placeholder="Пароль">
                <button onclick="addUser()">Добавить</button>
            </div>
            <table id="users-table">
                <thead><tr><th>ID</th><th>Логин</th><th>Роль</th><th>Действие</th></tr></thead>
                <tbody></tbody>
            </table>
        </div>

        <div class="panel">
            <h2>Чат поддержки</h2>
            <div id="admin-chat-list" style="max-height: 400px; overflow-y: auto;"></div>
        </div>
    </div>

    <script>
        async function loadUsers() {
            const res = await fetch('/api/admin/get_users');
            const users = await res.json();
            const tbody = document.querySelector('#users-table tbody');
            tbody.innerHTML = '';
            users.forEach(u => {
                tbody.innerHTML += `
                    <tr>
                        <td>${u.id}</td>
                        <td>${u.username}</td>
                        <td style="color:${u.role==='admin'?'#ff7b72':'#88ff00'}">${u.role}</td>
                        <td>${u.username !== 'admin' ? `<button class="btn-del" onclick="delUser(${u.id})">Удалить</button>` : '-'}</td>
                    </tr>
                `;
            });
        }
        async function addUser() {
            const u = document.getElementById('new-user').value.trim();
            const p = document.getElementById('new-pass').value.trim();
            if (!u || !p) return alert('Заполните поля');
            const res = await fetch('/api/admin/add_user', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: u, password: p}) });
            if (res.ok) { document.getElementById('new-user').value = ''; document.getElementById('new-pass').value = ''; loadUsers(); } 
            else { alert('Ошибка (возможно, такой логин уже есть)'); }
        }
        async function delUser(id) {
            if (!confirm('Удалить пользователя и все его сервера?')) return;
            await fetch('/api/admin/del_user', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id}) });
            loadUsers();
        }
        async function loadChat() {
            const res = await fetch('/api/get_chat');
            const msgs = await res.json();
            const list = document.getElementById('admin-chat-list');
            list.innerHTML = '';
            msgs.forEach(m => { list.innerHTML += `<div class="chat-msg"><b>${m.sender} (${m.time}):</b><br>${m.text}</div>`; });
        }
        loadUsers();
        setInterval(loadChat, 3000);
    </script>
</body>
</html>
"""

# ==========================================
# МАРШРУТЫ FLASK
# ==========================================

@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = request.form.get("username")
        pwd = request.form.get("password")
        robot = request.form.get("robot_check")
        
        if not robot:
            error = "Подтвердите, что вы не робот."
        else:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE username=?", (user,))
            row = c.fetchone()
            conn.close()
            
            if row and check_password_hash(row[2], pwd):
                session.clear()
                session["logged_in"] = True
                session["auth_ok"] = True # Флаг для обхода защиты прямых ссылок
                session["user"] = row[1]
                session["role"] = row[3]
                return redirect(url_for("dashboard"))
            else:
                error = "Неверный логин или пароль"
                
    return render_template_string(LOGIN_HTML, error=error)

@app.route("/dashboard")
def dashboard():
    return render_template_string(DASHBOARD_HTML, user=session["user"], role=session["role"])

@app.route("/console/<int:server_id>")
def server_console(server_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if session["role"] == 'admin':
        c.execute("SELECT id, name, ip, port, nickname FROM servers WHERE id=?", (server_id,))
    else:
        c.execute("SELECT id, name, ip, port, nickname FROM servers WHERE id=? AND user_id=(SELECT id FROM users WHERE username=?)", (server_id, session["user"]))
    server = c.fetchone()
    conn.close()
    
    if not server: return "Сервер не найден или нет доступа", 403
    server_dict = {"id": server[0], "name": server[1], "ip": server[2], "port": server[3], "nickname": server[4]}
    return render_template_string(CONSOLE_HTML, server=server_dict)

@app.route("/admin")
def admin():
    if session.get("role") != 'admin': return "Доступ запрещен", 403
    return render_template_string(ADMIN_HTML)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ==========================================
# API МАРШРУТЫ
# ==========================================

@app.route("/api/get_servers")
def api_get_servers():
    if not session.get("logged_in"): return jsonify([])
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if session["role"] == 'admin':
        c.execute("SELECT id, name, ip, port, nickname FROM servers")
    else:
        c.execute("SELECT id, name, ip, port, nickname FROM servers WHERE user_id=(SELECT id FROM users WHERE username=?)", (session["user"],))
    servers = [{"id": r[0], "name": r[1], "ip": r[2], "port": r[3], "nickname": r[4]} for r in c.fetchall()]
    conn.close()
    return jsonify(servers)

@app.route("/api/add_server", methods=["POST"])
def api_add_server():
    if not session.get("logged_in"): return jsonify({"error": "no auth"}), 401
    data = request.get_json()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=?", (session["user"],))
    user_id = c.fetchone()[0]
    c.execute("INSERT INTO servers (user_id, name, ip, port, nickname) VALUES (?, ?, ?, ?, ?)", (user_id, data['name'], data['ip'], data['port'], data['nickname']))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/edit_server", methods=["POST"])
def api_edit_server():
    if not session.get("logged_in"): return jsonify({"error": "no auth"}), 401
    data = request.get_json()
    sid = data.get("id")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if session["role"] != 'admin':
        c.execute("SELECT id FROM servers WHERE id=? AND user_id=(SELECT id FROM users WHERE username=?)", (sid, session["user"]))
        if not c.fetchone():
            conn.close()
            return jsonify({"error": "access denied"}), 403
    c.execute("UPDATE servers SET name=?, ip=?, port=?, nickname=? WHERE id=?", (data['name'], data['ip'], data['port'], data['nickname'], sid))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/get_chat")
def api_get_chat():
    if not session.get("logged_in"): return jsonify([])
    # Сообщения могут читать только админы
    if session.get("role") != 'admin': return jsonify([])
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT sender, text, time FROM messages ORDER BY id ASC")
    msgs = [{"sender": r[0], "text": r[1], "time": r[2]} for r in c.fetchall()]
    conn.close()
    return jsonify(msgs)

@app.route("/api/send_chat", methods=["POST"])
def api_send_chat():
    if not session.get("logged_in"): return jsonify({"error": "no auth"}), 401
    text = request.get_json().get("text")
    if not text: return jsonify({"error": "empty"}), 400
    now = datetime.datetime.now().strftime("%H:%M")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO messages (sender, text, time) VALUES (?, ?, ?)", (session["user"], text, now))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/admin/get_users")
def api_admin_get_users():
    if session.get("role") != 'admin': return jsonify([]), 403
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, username, role FROM users")
    users = [{"id": r[0], "username": r[1], "role": r[2]} for r in c.fetchall()]
    conn.close()
    return jsonify(users)

@app.route("/api/admin/add_user", methods=["POST"])
def api_admin_add_user():
    if session.get("role") != 'admin': return jsonify({"error": "no auth"}), 403
    data = request.get_json()
    u = data.get("username")
    p = data.get("password")
    if not u or not p: return jsonify({"error": "empty"}), 400
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        hashed = generate_password_hash(p)
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'user')", (u, hashed))
        conn.commit()
    except sqlite3.IntegrityError: return jsonify({"error": "exists"}), 400
    finally: conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/admin/del_user", methods=["POST"])
def api_admin_del_user():
    if session.get("role") != 'admin': return jsonify({"error": "no auth"}), 403
    uid = request.get_json().get("id")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (uid,))
    c.execute("DELETE FROM servers WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/command", methods=["POST"])
def api_command():
    if not session.get("logged_in"): return jsonify({"status": "error", "message": "Не авторизован"}), 401
    cmd = request.get_json().get("command", "").strip()
    if not cmd: return jsonify({"status": "error", "message": "Пустая команда"}), 400
    try:
        resp = requests.post(f"{BOT_URL}/send", json={"command": cmd}, timeout=10)
        if resp.status_code == 200: response_text = "Команда отправлена."
        else: response_text = f"Ошибка бота: {resp.json().get('error')}"
    except: response_text = "Ошибка: Бот недоступен."
    return jsonify({"status": "ok", "response": response_text, "command": cmd})

@app.route("/api/connect", methods=["POST"])
def api_connect():
    if not session.get("logged_in"): return jsonify({"status": "error", "message": "Не авторизован"}), 401
    data = request.get_json()
    try:
        resp = requests.post(f"{BOT_URL}/connect", json=data, timeout=10)
        if resp.status_code == 200: return jsonify({"status": "ok"})
        else: return jsonify({"status": "error", "message": "Ошибка бота"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/chat")
def api_chat():
    if not session.get("logged_in"): return jsonify([]), 401
    try:
        resp = requests.get(f"{BOT_URL}/chat", timeout=10)
        return jsonify(resp.json())
    except:
        return jsonify([])

if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000)
