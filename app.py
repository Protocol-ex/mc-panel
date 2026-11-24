from flask import Flask, request, redirect, url_for, session, jsonify, render_template_string
import requests
import os
import sqlite3
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "OmegaProtocol_Super_Secret_Key_2026"
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')

BOT_URL = os.environ.get("BOT_URL", "http://127.0.0.1:3001").rstrip("/")
DB_FILE = "database.db"

# Сброс БД при необходимости
if os.environ.get("RESET_DB") == "true" and os.path.exists(DB_FILE):
    os.remove(DB_FILE)

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT DEFAULT 'user', server_limit INTEGER DEFAULT 1)''')
    c.execute('''CREATE TABLE IF NOT EXISTS servers (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, ip TEXT, port INTEGER, nickname TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, recipient TEXT, text TEXT, time TEXT, is_admin INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS services (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price TEXT, description TEXT)''')
    
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, role, server_limit) VALUES ('admin', ?, 'admin', 999)", (generate_password_hash("omega123"),))
        
    c.execute("SELECT * FROM services")
    if not c.fetchone():
        c.execute("INSERT INTO services (name, price, description) VALUES ('Базовый', 'Бесплатно', '1 консоль, стандартная поддержка')")
        c.execute("INSERT INTO services (name, price, description) VALUES ('Премиум', '149 руб/мес', '5 консолей, приоритетная поддержка')")
        c.execute("INSERT INTO services (name, price, description) VALUES ('Бизнес', '399 руб/мес', 'Безлимит консолей, выделенный менеджер')")
    conn.commit(); conn.close()

init_db()

@app.before_request
def block_direct_url_access():
    if request.endpoint in ['dashboard', 'server_console', 'admin', 'services']:
        if not session.get("logged_in") or not session.get("auth_ok"):
            session.clear()
            return redirect(url_for('login'))
    return None

# ==========================================
# БАЗОВЫЙ CSS И ШАПКА ДЛЯ ВСЕХ СТРАНИЦ
# ==========================================
COMMON_CSS = """
<style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { height: 100vh; display: flex; font-family: 'Segoe UI', sans-serif; background: #0a0c10; color: #c9d1d9; overflow: hidden; }
    .sidebar { width: 240px; background: rgba(22,27,34,0.95); border-right: 1px solid #30363d; display: flex; flex-direction: column; padding: 20px 0; z-index: 10; }
    .logo { font-size: 22px; font-weight: bold; padding: 0 20px; margin-bottom: 30px; color: #fff; text-decoration: none; }
    .hype { color: #ffffff; } .mc { color: #88ff00; }
    .nav-item { display: flex; align-items: center; gap: 12px; padding: 12px 20px; color: #8b949e; text-decoration: none; font-size: 15px; transition: 0.2s; cursor: pointer; }
    .nav-item:hover, .nav-item.active { background: rgba(136,255,0,0.1); color: #88ff00; border-right: 3px solid #88ff00; }
    .nav-icon { font-size: 18px; width: 24px; text-align: center; }
    .content { flex: 1; display: flex; flex-direction: column; overflow: hidden; position: relative; }
    .topbar { display: flex; justify-content: space-between; align-items: center; padding: 15px 30px; background: rgba(22,27,34,0.85); border-bottom: 1px solid rgba(136,255,0,0.15); }
    .user-info { color: #8b949e; font-size: 14px; } .user-info b { color: #88ff00; }
    .logout { color: #ff7b72; text-decoration: none; padding: 6px 14px; border: 1px solid rgba(255,123,114,0.4); border-radius: 6px; font-size: 13px; margin-left: 15px; }
    .logout:hover { background: rgba(255,123,114,0.15); }
    .page-body { flex: 1; padding: 30px; overflow-y: auto; }
    @media (max-width: 768px) {
        .sidebar { width: 70px; }
        .sidebar .logo, .sidebar .nav-text { display: none; }
        .nav-item { justify-content: center; padding: 15px 0; }
        .topbar { padding: 10px 15px; }
        .page-body { padding: 15px; }
    }
    .btn-add { background: #88ff00; color: #0a0f1a; border: none; padding: 12px 24px; border-radius: 8px; font-size: 15px; font-weight: bold; cursor: pointer; transition: 0.2s; }
    .btn-add:hover { transform: scale(1.02); filter: brightness(1.1); }
    .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); justify-content: center; align-items: center; z-index: 1000; padding: 15px; }
    .modal-content { background: #161b22; border: 1px solid #30363d; padding: 20px; border-radius: 12px; width: 100%; max-width: 400px; text-align: center; }
    .modal-content h2 { margin-bottom: 15px; color: #88ff00; font-size: 18px; }
    .modal-content input { width: 100%; padding: 12px; margin-bottom: 12px; border-radius: 8px; border: 1px solid #30363d; background: #0d1117; color: #fff; outline: none; }
    .modal-content button { width: 100%; padding: 12px; background: #88ff00; color: #000; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; margin-bottom: 8px; }
    .modal-content .cancel { background: #30363d; color: #fff; }
    
    /* Кнопки поддержки и ИИ */
    .chat-btn { position: fixed; bottom: 20px; right: 20px; background: #79c0ff; color: #0a0f1a; border: none; padding: 15px; border-radius: 50%; width: 55px; height: 55px; font-size: 22px; cursor: pointer; box-shadow: 0 4px 15px rgba(121,192,255,0.4); z-index: 100; display: flex; justify-content: center; align-items: center; }
    .ai-btn { position: fixed; bottom: 20px; right: 85px; background: #b57bff; color: #0a0f1a; border: none; padding: 15px; border-radius: 50%; width: 55px; height: 55px; font-size: 22px; cursor: pointer; box-shadow: 0 4px 15px rgba(181,123,255,0.4); z-index: 100; display: flex; justify-content: center; align-items: center; }
    .chat-window { position: fixed; bottom: 85px; right: 20px; width: 300px; max-width: calc(100vw - 40px); height: 400px; background: #161b22; border: 1px solid #30363d; border-radius: 12px; display: none; flex-direction: column; z-index: 100; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
    .chat-header { padding: 10px 15px; background: #0d1117; border-bottom: 1px solid #30363d; font-weight: bold; border-radius: 12px 12px 0 0; display: flex; justify-content: space-between; }
    .chat-header.support { color: #79c0ff; } .chat-header.ai { color: #b57bff; }
    .chat-header span { cursor: pointer; color: #ff7b72; }
    .chat-messages { flex: 1; padding: 15px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
    .chat-input { display: flex; padding: 10px; border-top: 1px solid #30363d; }
    .chat-input input { flex: 1; padding: 8px; border-radius: 6px; border: none; background: #0d1117; color: #fff; outline: none; }
    .chat-input button { border: none; padding: 0 15px; margin-left: 5px; border-radius: 6px; cursor: pointer; font-weight: bold; color: #000; }
    .chat-input .btn-sup { background: #79c0ff; } .chat-input .btn-ai { background: #b57bff; }
</style>
"""

CHAT_HTML = """
<button class="chat-btn" onclick="toggleChat('support')">💬</button>
<div class="chat-window" id="chat-support">
    <div class="chat-header support">Поддержка <span onclick="toggleChat('support')">✖</span></div>
    <div class="chat-messages" id="msgs-support"><p style="color:#8b949e; font-size: 13px;">Напишите нам. Ответ придет в ближайшее время.</p></div>
    <div class="chat-input"><input type="text" id="inp-support" placeholder="Сообщение..." onkeypress="if(event.key==='Enter') sendMsg()"><button class="btn-sup" onclick="sendMsg()">></button></div>
</div>

<button class="ai-btn" onclick="toggleChat('ai')">🤖</button>
<div class="chat-window" id="chat-ai">
    <div class="chat-header ai">ИИ Помощник <span onclick="toggleChat('ai')">✖</span></div>
    <div class="chat-messages" id="msgs-ai"><div class="msg other" style="background: #30363d; padding: 8px 12px; border-radius: 8px; font-size: 13px;">Привет! Я ИИ-помощник. Спроси меня о чем угодно!</div></div>
    <div class="chat-input"><input type="text" id="inp-ai" placeholder="Спроси меня..." onkeypress="if(event.key==='Enter') askAI()"><button class="btn-ai" onclick="askAI()">></button></div>
</div>

<script>
    function askAI() {
        const inp = document.getElementById('inp-ai'); const text = inp.value.trim().toLowerCase(); if (!text) return; inp.value = '';
        const container = document.getElementById('msgs-ai');
        container.innerHTML += `<div class="msg my" style="background:#b57bff; color:#000; align-self:flex-end; padding:8px 12px; border-radius:8px; font-size:13px; max-width:80%;"><b>Вы:</b><br>${text}</div>`;
        setTimeout(() => {
            let answer = "Я не совсем понял вопрос. Спроси меня про ошибки, добавление серверов или поддержку.";
            if (text.match(/сервер|добавить|создать|консол/)) answer = "Чтобы добавить сервер, нажми зеленую кнопку '+ Создать'. Введи название, IP, порт и ник бота.";
            else if (text.match(/бот|ошибк|не работает|кик/)) answer = "Если бот вылетел, зайди в консоль и нажми 'Перезайти'. Если пишет 'Ошибка: Бот недоступен', значит сервис на Render упал.";
            else if (text.match(/пароль|вход|логин/)) answer = "Новых пользователей создает админ. Если забыл пароль — пиши в поддержку.";
            else if (text.match(/привет|здравствуй|хай|ку/)) answer = "Привет-привет! Как твои дела? Чем могу помочь?";
            else if (text.match(/как дела|как ты/)) answer = "У меня все отлично! Работаю на благо панели 24/7. А у тебя как?";
            else if (text.match(/смысл жизни|зачем мы/)) answer = "Смысл жизни — это создавать консоли и банить читеров. Ну, по крайней мере в нашем мире Minecraft.";
            else if (text.match(/кто ты|создал|сделал|твое имя/)) answer = "Я — встроенный ИИ-помощник. Меня создал Оператор с помощью Протокола Омега.";
            else if (text.match(/лимит|плат|деньги|купить/)) answer = "По умолчанию у вас 1 консоль. Чтобы получить больше — напишите в поддержку, вопрос решается индивидуально.";
            else if (text.match(/люблю|любовь/)) answer = "Оу... я тоже тебя люблю! Но давай сначала настроим сервера?";
            else if (text.match(/дурак|тупой|плохой/)) answer = "Я стараюсь изо всех сил! Если я туплю, просто перезагрузите страницу.";
            container.innerHTML += `<div class="msg other" style="background:#30363d; align-self:flex-start; padding:8px 12px; border-radius:8px; font-size:13px; max-width:80%;"><b>ИИ:</b><br>${answer}</div>`;
            container.scrollTop = container.scrollHeight;
        }, 400);
        container.scrollTop = container.scrollHeight;
    }
    function toggleChat(type) {
        const sup = document.getElementById('chat-support'); const ai = document.getElementById('chat-ai');
        if (type === 'support') { sup.style.display = sup.style.display === 'flex' ? 'none' : 'flex'; ai.style.display = 'none'; }
        else { ai.style.display = ai.style.display === 'flex' ? 'none' : 'flex'; sup.style.display = 'none'; }
    }
    async function sendMsg() {
        const text = document.getElementById('inp-support').value.trim(); if (!text) return; document.getElementById('inp-support').value = '';
        await fetch('/api/send_chat', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text}) });
        const msgs = document.getElementById('msgs-support');
        msgs.innerHTML += `<div class="msg my" style="background: #79c0ff; color: #000; align-self: flex-end; padding: 8px 12px; border-radius: 8px; font-size: 13px; max-width: 80%;"><b>Вы:</b><br>${text}</div>`;
        msgs.scrollTop = msgs.scrollHeight;
    }
</script>
"""

def get_sidebar(active):
    admin_link = f'<a href="/admin" class="nav-item {"active" if active=="admin" else ""}"><span class="nav-icon">🛡️</span><span class="nav-text">Админ-панель</span></a>' if session.get('role') == 'admin' else ''
    return f"""
    <aside class="sidebar">
        <a href="/dashboard" class="logo"><span class="hype">Hype</span><span class="mc">MC</span></a>
        <a href="/dashboard" class="nav-item {"active" if active=="servers" else ""}"><span class="nav-icon">🖥</span><span class="nav-text">Мои сервера</span></a>
        <a href="/services" class="nav-item {"active" if active=="services" else ""}"><span class="nav-icon">💎</span><span class="nav-text">Услуги</span></a>
        {admin_link}
    </aside>
    """

def get_topbar(title):
    return f"""
    <div class="topbar">
        <div style="font-size: 18px; font-weight: bold; color: #fff;">{title}</div>
        <div>
            <span class="user-info">{session.get('user')} ({session.get('role')})</span>
            <a class="logout" href="/logout">Выйти</a>
        </div>
    </div>
    """

# ==========================================
# СТРАНИЦЫ
# ==========================================

@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = request.form.get("username"); pwd = request.form.get("password"); robot = request.form.get("robot_check")
        if not robot: error = "Пройдите капчу."
        else:
            conn = sqlite3.connect(DB_FILE); c = conn.cursor()
            c.execute("SELECT * FROM users WHERE username=?", (user,)); row = c.fetchone(); conn.close()
            if row and check_password_hash(row[2], pwd):
                session.clear(); session["logged_in"] = True; session["auth_ok"] = True; session["user"] = row[1]; session["role"] = row[3]
                return redirect(url_for("dashboard"))
            else: error = "Неверный логин или пароль"
    
    return render_template_string(f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Вход — HypeMC</title>
        <style>
            * {{ box-sizing: border-box; }}
            body {{ margin: 0; height: 100vh; display: flex; align-items: center; justify-content: center; font-family: 'Segoe UI', Arial, sans-serif; background: radial-gradient(circle at 30% 20%, #1b2735, #090a0f); color: #e0e0e0; padding: 15px; }}
            .login-card {{ background: rgba(30, 34, 50, 0.9); padding: 30px; border-radius: 16px; box-shadow: 0 0 40px rgba(136, 255, 0, 0.15); border: 1px solid rgba(136, 255, 0, 0.2); width: 100%; max-width: 400px; text-align: center; }}
            h1 {{ font-weight: 600; letter-spacing: 1px; margin-bottom: 20px; font-size: 28px; }}
            .hype {{ color: #ffffff; }} .mc {{ color: #88ff00; }}
            label {{ display: block; margin-bottom: 6px; font-size: 14px; color: #9aa5b1; text-align: left; }}
            input {{ width: 100%; padding: 12px 14px; margin-bottom: 15px; border-radius: 8px; border: 1px solid #3a3f55; background: #151a26; color: #e0e0e0; font-size: 15px; outline: none; }}
            input:focus {{ border-color: #88ff00; }}
            button {{ width: 100%; padding: 13px; border: none; border-radius: 8px; background: linear-gradient(90deg, #66cc00, #88ff00); color: #0a0f1a; font-size: 17px; font-weight: bold; cursor: pointer; margin-bottom: 15px; }}
            .error {{ color: #ff5c5c; margin-bottom: 15px; font-size: 14px; }}
            .captcha-box {{ display: flex; align-items: center; gap: 10px; margin-bottom: 20px; background: #151a26; border: 1px solid #3a3f55; padding: 10px; border-radius: 8px; cursor: not-allowed; opacity: 0.5; }}
            .captcha-box.active {{ cursor: pointer; opacity: 1; border-color: #88ff00; }}
            .captcha-box input {{ width: 20px; height: 20px; margin: 0; }}
            .ttt-wrapper {{ margin-bottom: 20px; background: #151a26; border: 1px solid #3a3f55; padding: 15px; border-radius: 8px; }}
            .ttt-wrapper p {{ font-size: 13px; color: #9aa5b1; margin-bottom: 10px; }}
            .ttt-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px; width: 140px; margin: 0 auto; }}
            .ttt-cell {{ width: 43px; height: 43px; background: #0a0c10; border: 1px solid #30363d; border-radius: 4px; display: flex; justify-content: center; align-items: center; font-size: 20px; font-weight: bold; cursor: pointer; color: #c9d1d9; }}
            .ttt-cell.x {{ color: #88ff00; }}
        </style>
    </head>
    <body>
        <div class="login-card">
            <h1><span class="hype">Hype</span><span class="mc">MC</span></h1>
            {f'<div class="error">{error}</div>' if error else ''}
            <form method="POST">
                <label>Логин</label><input type="text" name="username" required autocomplete="off">
                <label>Пароль</label><input type="password" name="password" required>
                <div class="ttt-wrapper">
                    <p>Пройдите капчу (соберите 3 X в ряд)</p>
                    <div class="ttt-grid" id="ttt-grid">
                        <div class="ttt-cell" onclick="tttClick(this)"></div><div class="ttt-cell" onclick="tttClick(this)"></div><div class="ttt-cell" onclick="tttClick(this)"></div>
                        <div class="ttt-cell" onclick="tttClick(this)"></div><div class="ttt-cell" onclick="tttClick(this)"></div><div class="ttt-cell" onclick="tttClick(this)"></div>
                        <div class="ttt-cell" onclick="tttClick(this)"></div><div class="ttt-cell" onclick="tttClick(this)"></div><div class="ttt-cell" onclick="tttClick(this)"></div>
                    </div>
                </div>
                <label class="captcha-box" id="captcha-label">
                    <input type="checkbox" id="robot-check" name="robot_check" disabled>
                    <span>Я не робот</span>
                </label>
                <button type="submit">Войти</button>
            </form>
        </div>
        <script>
            let tttWon = false;
            function tttClick(cell) {{
                if (tttWon || cell.innerText !== "") return;
                cell.innerText = "X"; cell.classList.add("x"); checkTTTWin();
            }}
            function checkTTTWin() {{
                const cells = document.querySelectorAll('.ttt-cell');
                const b = Array.from(cells).map(c => c.innerText);
                const wins = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];
                for (let w of wins) {{
                    if (b[w[0]] === "X" && b[w[1]] === "X" && b[w[2]] === "X") {{
                        tttWon = true; cells.forEach(c => {{ if(c.innerText === "") {{ c.innerText = "X"; c.classList.add("x"); }} }}); break;
                    }}
                }}
                if (tttWon) {{ document.getElementById('robot-check').disabled = false; document.getElementById('robot-check').checked = true; document.getElementById('captcha-label').classList.add('active'); }}
            }}
        </script>
    </body>
    </html>
    """)

@app.route("/dashboard")
def dashboard():
    return render_template_string(f"""
    <!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Мои сервера</title>
    {COMMON_CSS}
    </head><body>
        {get_sidebar('servers')}
        <div class="content">
            {get_topbar('Мои сервера')}
            <div class="page-body">
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px;" id="servers-grid"></div>
                <button class="btn-add" style="position: fixed; bottom: 30px; left: 270px;" onclick="openModal()">+ Создать консоль</button>
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
            </div>
        </div>
        {CHAT_HTML}
        <script>
            function openModal(server = null) {{
                document.getElementById('add-modal').style.display = 'flex';
                if (server) {{
                    document.getElementById('modal-title').innerText = "Редактировать"; document.getElementById('edit-id').value = server.id;
                    document.getElementById('m-name').value = server.name; document.getElementById('m-ip').value = server.ip; document.getElementById('m-port').value = server.port; document.getElementById('m-nick').value = server.nickname;
                }} else {{
                    document.getElementById('modal-title').innerText = "Новый сервер"; document.getElementById('edit-id').value = ""; document.getElementById('m-name').value = ""; document.getElementById('m-ip').value = ""; document.getElementById('m-port').value = "25565"; document.getElementById('m-nick').value = "";
                }}
            }}
            function closeModal() {{ document.getElementById('add-modal').style.display = 'none'; }}
            async function loadServers() {{
                const res = await fetch('/api/get_servers'); const servers = await res.json(); const grid = document.getElementById('servers-grid'); grid.innerHTML = '';
                if (servers.length === 0) {{ grid.innerHTML = '<p style="color:#8b949e;">Нет серверов. Нажмите "+ Создать консоль".</p>'; return; }}
                servers.forEach(s => {{
                    grid.innerHTML += `<div style="background: rgba(22,27,34,0.8); border: 1px solid #30363d; border-radius: 12px; padding: 15px; position: relative;"><button style="position: absolute; top: 10px; right: 10px; background: none; border: none; color: #8b949e; cursor: pointer;" onclick='openModal(${{JSON.stringify(s)}})'>✎</button><h3 style="color: #fff; margin-bottom: 8px; font-size: 16px;">${{s.name}}</h3><p style="color: #8b949e; font-size: 13px; font-family: monospace; margin-bottom: 5px;">IP: ${{s.ip}}:${{s.port}}</p><p style="color: #ffb86c; font-weight: bold; margin-bottom: 12px; font-size: 13px;">Ник: ${{s.nickname}}</p><a href="/console/${{s.id}}" style="display: block; text-align: center; background: #88ff00; color: #000; text-decoration: none; padding: 10px; border-radius: 8px; font-weight: bold; font-size: 14px;">Открыть консоль</a></div>`;
                }});
            }}
            async function saveServer() {{
                const id = document.getElementById('edit-id').value; const name = document.getElementById('m-name').value.trim();
                const ip = document.getElementById('m-ip').value.trim(); const port = document.getElementById('m-port').value.trim(); const nick = document.getElementById('m-nick').value.trim();
                if (!name || !ip || !port || !nick) return alert('Заполните все поля');
                const url = id ? '/api/edit_server' : '/api/add_server';
                const res = await fetch(url, {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{id, name, ip, port, nickname: nick}}) }});
                if (res.ok) {{ closeModal(); loadServers(); }} else {{ const d = await res.json(); alert(d.message || 'Ошибка!'); }}
            }}
            loadServers();
        </script>
    </body></html>
    """)

@app.route("/services")
def services():
    return render_template_string(f"""
    <!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Услуги</title>
    {COMMON_CSS}
    </head><body>
        {get_sidebar('services')}
        <div class="content">
            {get_topbar('Тарифы и Услуги')}
            <div class="page-body">
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px;" id="services-grid"></div>
            </div>
        </div>
        {CHAT_HTML}
        <script>
            async function loadServices() {{
                const res = await fetch('/api/services'); const services = await res.json(); const grid = document.getElementById('services-grid'); grid.innerHTML = '';
                services.forEach(s => {{
                    grid.innerHTML += `<div style="background: rgba(22,27,34,0.8); border: 1px solid #30363d; border-radius: 12px; padding: 25px; text-align: center;"><h3 style="color: #fff; font-size: 20px; margin-bottom: 10px;">${{s.name}}</h3><div style="color: #88ff00; font-size: 24px; font-weight: bold; margin-bottom: 15px;">${{s.price}}</div><p style="color: #8b949e; font-size: 14px; margin-bottom: 20px; min-height: 40px;">${{s.description}}</p><button style="width: 100%; padding: 10px; background: none; border: 1px solid #88ff00; color: #88ff00; border-radius: 8px; font-weight: bold; cursor: pointer;" onclick="alert('Для покупки напишите в Поддержку!')">Выбрать</button></div>`;
                }});
            }}
            loadServices();
        </script>
    </body></html>
    """)

@app.route("/admin")
def admin():
    if session.get("role") != 'admin': return "Доступ запрещен", 403
    admin_css = """
    <style>
        .admin-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        @media (max-width: 900px) { .admin-grid { grid-template-columns: 1fr; } }
        .panel { background: rgba(22,27,34,0.8); border: 1px solid #30363d; border-radius: 12px; padding: 15px; display: flex; flex-direction: column; }
        .panel h2 { margin-bottom: 12px; color: #88ff00; font-size: 16px; border-bottom: 1px solid #30363d; padding-bottom: 8px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #30363d; font-size: 13px; }
        th { color: #8b949e; }
        .add-form { display: flex; gap: 8px; margin-bottom: 10px; }
        .add-form input { flex: 1; padding: 10px; border-radius: 8px; border: 1px solid #30363d; background: #0d1117; color: #fff; }
        .add-form button { padding: 10px 15px; background: #88ff00; color: #000; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; }
        .btn-del { background: #ff7b72; color: #000; border: none; padding: 4px 8px; border-radius: 5px; cursor: pointer; font-weight: bold; font-size: 12px; }
        .messenger { display: flex; height: 400px; border: 1px solid #30363d; border-radius: 8px; overflow: hidden; background: #0d1117; }
        .users-list { width: 200px; border-right: 1px solid #30363d; overflow-y: auto; }
        .user-item { padding: 12px; border-bottom: 1px solid #30363d; cursor: pointer; transition: 0.2s; font-size: 14px; }
        .user-item:hover, .user-item.active { background: rgba(136,255,0,0.1); color: #88ff00; }
        .chat-area { flex: 1; display: flex; flex-direction: column; }
        .chat-header { padding: 12px; border-bottom: 1px solid #30363d; font-weight: bold; color: #79c0ff; }
        .chat-messages { flex: 1; padding: 15px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
        .msg { padding: 8px 12px; border-radius: 8px; font-size: 13px; max-width: 80%; word-wrap: break-word; }
        .msg.adm { background: #88ff00; color: #000; align-self: flex-end; }
        .msg.usr { background: #30363d; color: #fff; align-self: flex-start; }
        .chat-input { display: flex; padding: 10px; border-top: 1px solid #30363d; gap: 8px; }
        .chat-input input { flex: 1; padding: 10px; border-radius: 6px; border: none; background: #161b22; color: #fff; outline: none; }
        .chat-input button { padding: 0 15px; background: #79c0ff; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; }
    </style>
    """
    return render_template_string(f"""
    <!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Админка</title>
    {COMMON_CSS} {admin_css}
    </head><body>
        {get_sidebar('admin')}
        <div class="content">
            {get_topbar('Админ-панель')}
            <div class="page-body">
                <div class="admin-grid">
                    <div class="panel">
                        <h2>Пользователи</h2>
                        <div class="add-form">
                            <input type="text" id="new-user" placeholder="Логин"><input type="password" id="new-pass" placeholder="Пароль">
                            <button onclick="addUser()">Добавить</button>
                        </div>
                        <table id="users-table"><thead><tr><th>Логин</th><th>Лимит</th><th>Действие</th></tr></thead><tbody></tbody></table>
                    </div>
                    <div class="panel">
                        <h2>Управление Услугами</h2>
                        <div class="add-form" style="flex-direction: column;">
                            <input type="text" id="srv-name" placeholder="Название (например, VIP)"><input type="text" id="srv-price" placeholder="Цена (например, 100р/мес)"><input type="text" id="srv-desc" placeholder="Описание">
                            <button onclick="addService()" style="width: 100%;">Добавить тариф</button>
                        </div>
                        <div id="services-list" style="max-height: 200px; overflow-y: auto;"></div>
                    </div>
                    <div class="panel" style="grid-column: 1 / -1;">
                        <h2>Поддержка (Чаты)</h2>
                        <div class="messenger">
                            <div class="users-list" id="chat-users-list"><div style="padding: 15px; color: #8b949e; font-size: 13px;">Выберите чат</div></div>
                            <div class="chat-area">
                                <div class="chat-header" id="chat-header">Чат не выбран</div>
                                <div class="chat-messages" id="admin-chat-messages"></div>
                                <div class="chat-input">
                                    <input type="text" id="admin-reply-text" placeholder="Ответ..." onkeypress="if(event.key==='Enter') sendAdminReply()">
                                    <button onclick="sendAdminReply()">➤</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <script>
            let currentRecipient = null;
            async function loadUsers() {{
                const res = await fetch('/api/admin/get_users'); const users = await res.json(); const tbody = document.querySelector('#users-table tbody'); tbody.innerHTML = '';
                users.forEach(u => {{
                    tbody.innerHTML += `<tr><td>${{u.username}}</td><td><input type="number" value="${{u.server_limit}}" style="width: 50px; background: #0d1117; color: #fff; border: 1px solid #30363d; padding: 4px; border-radius: 4px;" onchange="updateLimit(${{u.id}}, this.value)"></td><td>${{u.username !== 'admin' ? `<button class="btn-del" onclick="delUser(${{u.id}})">Удалить</button>` : '-'}}</td></tr>`;
                }});
            }}
            async function updateLimit(id, limit) {{ await fetch('/api/admin/set_limit', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{id, limit: parseInt(limit)}}) }}); }}
            async function addUser() {{
                const u = document.getElementById('new-user').value.trim(); const p = document.getElementById('new-pass').value.trim();
                if (!u || !p) return alert('Заполните поля');
                const res = await fetch('/api/admin/add_user', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{username: u, password: p}}) }});
                if (res.ok) {{ document.getElementById('new-user').value = ''; document.getElementById('new-pass').value = ''; loadUsers(); }} else {{ alert('Ошибка'); }}
            }}
            async function delUser(id) {{ if (!confirm('Удалить?')) return; await fetch('/api/admin/del_user', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{id}}) }}); loadUsers(); }}
            async function loadServices() {{
                const res = await fetch('/api/services'); const services = await res.json();
                document.getElementById('services-list').innerHTML = services.map(s => `<div style="display: flex; justify-content: space-between; align-items: center; padding: 8px; border-bottom: 1px solid #30363d;"><div><b style="color:#fff;">${{s.name}}</b> - ${{s.price}}</div><button class="btn-del" onclick="delService(${{s.id}})">X</button></div>`).join('');
            }}
            async function addService() {{
                const name = document.getElementById('srv-name').value.trim(); const price = document.getElementById('srv-price').value.trim(); const desc = document.getElementById('srv-desc').value.trim();
                if (!name || !price) return alert('Заполните название и цену');
                await fetch('/api/admin/add_service', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{name, price, description: desc}}) }});
                document.getElementById('srv-name').value = ''; document.getElementById('srv-price').value = ''; document.getElementById('srv-desc').value = ''; loadServices();
            }}
            async function delService(id) {{ if(!confirm('Удалить тариф?')) return; await fetch('/api/admin/del_service', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{id}}) }}); loadServices(); }}
            async function loadChatUsers() {{
                const res = await fetch('/api/admin/get_chat_users'); const users = await res.json(); const list = document.getElementById('chat-users-list'); list.innerHTML = '';
                if (users.length === 0) {{ list.innerHTML = '<div style="padding: 15px; color: #8b949e; font-size: 13px;">Нет сообщений</div>'; return; }}
                users.forEach(u => {{
                    const div = document.createElement('div'); div.className = `user-item ${{currentRecipient === u ? 'active' : ''}}`; div.innerText = u;
                    div.onclick = () => {{ currentRecipient = u; loadChatUsers(); loadChatMessages(); }}; list.appendChild(div);
                }});
            }}
            async function loadChatMessages() {{
                if (!currentRecipient) return;
                document.getElementById('chat-header').innerText = `Чат с ${{currentRecipient}}`;
                const res = await fetch(`/api/admin/get_messages?user=${{currentRecipient}}`); const msgs = await res.json(); const box = document.getElementById('admin-chat-messages');
                box.innerHTML = msgs.map(m => `<div class="msg ${{m.is_admin ? 'adm' : 'usr'}}">${{m.text}} <span style="font-size:10px; opacity:0.6;">${{m.time}}</span></div>`).join('');
                box.scrollTop = box.scrollHeight;
            }}
            async function sendAdminReply() {{
                if (!currentRecipient) return alert('Выберите чат!');
                const inp = document.getElementById('admin-reply-text'); const text = inp.value.trim(); if (!text) return; inp.value = '';
                await fetch('/api/admin/reply', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{recipient: currentRecipient, text}}) }});
                loadChatMessages();
            }}
            loadUsers(); loadServices(); loadChatUsers(); setInterval(() => {{ loadChatUsers(); if(currentRecipient) loadChatMessages(); }}, 3000);
        </script>
    </body></html>
    """)

@app.route("/console/<int:server_id>")
def server_console(server_id):
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    if session["role"] == 'admin': c.execute("SELECT id, name, ip, port, nickname FROM servers WHERE id=?", (server_id,))
    else: c.execute("SELECT id, name, ip, port, nickname FROM servers WHERE id=? AND user_id=(SELECT id FROM users WHERE username=?)", (server_id, session["user"]))
    server = c.fetchone(); conn.close()
    if not server: return "Сервер не найден", 403
    
    return render_template_string(f"""
    <!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Консоль</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ height: 100vh; display: flex; flex-direction: column; font-family: 'Consolas', monospace; background: #0a0c10; color: #c9d1d9; overflow: hidden; }}
        header {{ display: flex; justify-content: space-between; align-items: center; padding: 12px 20px; background: #161b22; border-bottom: 1px solid #30363d; }}
        .back-btn {{ color: #8b949e; text-decoration: none; margin-right: 15px; padding: 6px 10px; border: 1px solid #30363d; border-radius: 6px; font-size: 13px; }}
        .back-btn:hover {{ border-color: #88ff00; color: #88ff00; }}
        .btn-action {{ background: none; border: 1px solid #ff7b72; color: #ff7b72; padding: 6px 12px; border-radius: 6px; cursor: pointer; margin-left: 10px; font-size: 12px; font-weight: bold; transition: 0.2s; }}
        .btn-action:hover {{ background: rgba(255,123,114,0.1); }}
        .btn-pause {{ border-color: #79c0ff; color: #79c0ff; }}
        .btn-pause:hover {{ background: rgba(121,192,255,0.1); }}
        .btn-pause.muted {{ border-color: #88ff00; color: #88ff00; background: rgba(136,255,0,0.1); }}
        .main {{ flex: 1; padding: 15px; display: flex; flex-direction: column; }}
        #console-output {{ flex: 1; overflow-y: auto; background: #0d1117; border: 1px solid #21262d; border-radius: 8px; padding: 15px; font-size: 13px; line-height: 1.6; }}
        .line {{ margin-bottom: 5px; word-break: break-all; }}
        .line .time {{ color: #484f58; font-size: 11px; margin-right: 6px; }}
        .line .system {{ color: #8b949e; font-style: italic; }}
        .line .chat-user {{ color: #ffb86c; font-weight: bold; }}
        .line .chat-msg {{ color: #f8f8f2; }}
        .input-row {{ display: flex; margin-top: 10px; gap: 8px; }}
        #cmd-input {{ flex: 1; padding: 12px; border-radius: 8px; border: 1px solid #30363d; background: #161b22; color: #fff; outline: none; }}
        #cmd-input:focus {{ border-color: #88ff00; }}
        #send-btn {{ padding: 0 20px; background: #88ff00; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; }}
    </style>
    </head><body>
        <header>
            <div style="display:flex; align-items:center;">
                <a href="/dashboard" class="back-btn">← Назад</a>
                <b style="color:#fff;">Консоль: {server[1]}</b>
                <button class="btn-action" onclick="forceReconnect()">🔄 Перезайти</button>
                <button class="btn-action btn-pause" id="btn-mute" onclick="toggleMute()">⏸ Пауза</button>
            </div>
            <div style="font-size: 12px; color: #8b949e;"><span style="color:#88ff00;">{server[2]}:{server[3]}</span> | <span style="color:#ffb86c;">{server[4]}</span></div>
        </header>
        <div class="main">
            <div id="console-output"><div class="line"><span class="system">Подключение...</span></div></div>
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
            let isMuted = false;
            let mutedMessages = [];

            function now() {{ return new Date().toLocaleTimeString('ru-RU'); }}
            
            function appendLine(html) {{
                if (isMuted) {{
                    mutedMessages.push(html);
                }} else {{
                    output.innerHTML += `<div class="line"><span class="time">${{now()}}</span> ${{html}}</div>`;
                    output.scrollTop = output.scrollHeight;
                }}
            }}

            function toggleMute() {{
                isMuted = !isMuted;
                const btn = document.getElementById('btn-mute');
                if (isMuted) {{
                    btn.innerHTML = "▶ Продолжить";
                    btn.classList.add('muted');
                }} else {{
                    btn.innerHTML = "⏸ Пауза";
                    btn.classList.remove('muted');
                    mutedMessages.forEach(msg => {{
                        output.innerHTML += `<div class="line"><span class="time">${{now()}}</span> ${{msg}}</div>`;
                    }});
                    mutedMessages = [];
                    output.scrollTop = output.scrollHeight;
                }}
            }}

            window.onload = async () => {{ await fetch('/api/connect', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{ host: "{server[2]}", port: "{server[3]}", username: "{server[4]}" }}) }}); }};
            async function forceReconnect() {{ appendLine(`<span class="system">Перезапуск...</span>`); await fetch('/api/reconnect', {{ method: 'POST' }}); }}
            
            form.addEventListener('submit', async (e) => {{
                e.preventDefault(); const cmd = input.value.trim(); if (!cmd) return;
                input.value = ''; appendLine(`<span style="color:#88ff00;">></span> <span style="color:#79c0ff;">${{cmd}}</span>`);
                await fetch('/api/command', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{command: cmd}}) }});
            }});

            setInterval(async () => {{
                try {{
                    const res = await fetch('/api/chat'); const messages = await res.json();
                    if (messages.length > lastChatLength) {{
                        let newMsgs = lastChatLength === -1 ? [] : messages.slice(lastChatLength);
                        newMsgs.forEach(m => appendLine(`<span class="chat-user">[${{m.username}}]</span> <span class="chat-msg">${{m.text}}</span>`));
                        lastChatLength = messages.length;
                    }}
                }} catch(e){{}}
            }}, 1000);
        </script>
    </body></html>
    """)

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
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    if session["role"] == 'admin': c.execute("SELECT id, name, ip, port, nickname FROM servers")
    else: c.execute("SELECT id, name, ip, port, nickname FROM servers WHERE user_id=(SELECT id FROM users WHERE username=?)", (session["user"],))
    servers = [{"id": r[0], "name": r[1], "ip": r[2], "port": r[3], "nickname": r[4]} for r in c.fetchall()]
    conn.close(); return jsonify(servers)

@app.route("/api/add_server", methods=["POST"])
def api_add_server():
    if not session.get("logged_in"): return jsonify({"error": "no auth"}), 401
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("SELECT id, server_limit FROM users WHERE username=?", (session["user"],)); user = c.fetchone()
    user_id, limit = user[0], user[1]
    c.execute("SELECT COUNT(*) FROM servers WHERE user_id=?", (user_id,)); current_count = c.fetchone()[0]
    if current_count >= limit: conn.close(); return jsonify({"status": "error", "message": f"Лимит консолей ({limit}) исчерпан. Напишите в Поддержку!"}), 403
    data = request.get_json()
    c.execute("INSERT INTO servers (user_id, name, ip, port, nickname) VALUES (?, ?, ?, ?, ?)", (user_id, data['name'], data['ip'], data['port'], data['nickname']))
    conn.commit(); conn.close(); return jsonify({"status": "ok"})

@app.route("/api/edit_server", methods=["POST"])
def api_edit_server():
    if not session.get("logged_in"): return jsonify({"error": "no auth"}), 401
    data = request.get_json(); sid = data.get("id")
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    if session["role"] != 'admin':
        c.execute("SELECT id FROM servers WHERE id=? AND user_id=(SELECT id FROM users WHERE username=?)", (sid, session["user"]))
        if not c.fetchone(): conn.close(); return jsonify({"error": "access denied"}), 403
    c.execute("UPDATE servers SET name=?, ip=?, port=?, nickname=? WHERE id=?", (data['name'], data['ip'], data['port'], data['nickname'], sid))
    conn.commit(); conn.close(); return jsonify({"status": "ok"})

@app.route("/api/services")
def api_services():
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("SELECT id, name, price, description FROM services")
    services = [{"id": r[0], "name": r[1], "price": r[2], "description": r[3]} for r in c.fetchall()]
    conn.close(); return jsonify(services)

@app.route("/api/get_chat")
def api_get_chat():
    if not session.get("logged_in"): return jsonify([])
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    if session.get("role") == 'admin': c.execute("SELECT sender, text, time, is_admin FROM messages ORDER BY id ASC")
    else: c.execute("SELECT sender, text, time, is_admin FROM messages WHERE recipient=? OR (sender=? AND is_admin=0) ORDER BY id ASC", (session["user"], session["user"]))
    msgs = [{"sender": r[0], "text": r[1], "time": r[2], "is_admin": r[3]} for r in c.fetchall()]
    conn.close(); return jsonify(msgs)

@app.route("/api/send_chat", methods=["POST"])
def api_send_chat():
    if not session.get("logged_in"): return jsonify({"error": "no auth"}), 401
    text = request.get_json().get("text"); now = datetime.datetime.now().strftime("%H:%M")
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("INSERT INTO messages (sender, recipient, text, time, is_admin) VALUES (?, 'ADMIN', ?, ?, 0)", (session["user"], text, now))
    conn.commit(); conn.close(); return jsonify({"status": "ok"})

@app.route("/api/admin/get_chat_users")
def api_admin_get_chat_users():
    if session.get("role") != 'admin': return jsonify([]), 403
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("SELECT DISTINCT sender FROM messages WHERE is_admin=0")
    users = [r[0] for r in c.fetchall()]
    conn.close(); return jsonify(users)

@app.route("/api/admin/get_messages")
def api_admin_get_messages():
    if session.get("role") != 'admin': return jsonify([]), 403
    user = request.args.get('user')
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("SELECT sender, text, time, is_admin FROM messages WHERE sender=? OR recipient=? ORDER BY id ASC", (user, user))
    msgs = [{"sender": r[0], "text": r[1], "time": r[2], "is_admin": r[3]} for r in c.fetchall()]
    conn.close(); return jsonify(msgs)

@app.route("/api/admin/reply", methods=["POST"])
def api_admin_reply():
    if session.get("role") != 'admin': return jsonify({"error": "no auth"}), 403
    data = request.get_json(); now = datetime.datetime.now().strftime("%H:%M")
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("INSERT INTO messages (sender, recipient, text, time, is_admin) VALUES ('ADMIN', ?, ?, ?, 1)", (data.get('recipient'), data.get('text'), now))
    conn.commit(); conn.close(); return jsonify({"status": "ok"})

@app.route("/api/admin/get_users")
def api_admin_get_users():
    if session.get("role") != 'admin': return jsonify([]), 403
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("SELECT id, username, server_limit FROM users")
    users = [{"id": r[0], "username": r[1], "server_limit": r[2]} for r in c.fetchall()]
    conn.close(); return jsonify(users)

@app.route("/api/admin/set_limit", methods=["POST"])
def api_admin_set_limit():
    if session.get("role") != 'admin': return jsonify({"error": "no auth"}), 403
    data = request.get_json()
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("UPDATE users SET server_limit=? WHERE id=?", (data.get("limit"), data.get("id")))
    conn.commit(); conn.close(); return jsonify({"status": "ok"})

@app.route("/api/admin/add_user", methods=["POST"])
def api_admin_add_user():
    if session.get("role") != 'admin': return jsonify({"error": "no auth"}), 403
    data = request.get_json()
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, role, server_limit) VALUES (?, ?, 'user', 1)", (data['username'], generate_password_hash(data['password'])))
        conn.commit()
    except sqlite3.IntegrityError: return jsonify({"error": "exists"}), 400
    finally: conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/admin/del_user", methods=["POST"])
def api_admin_del_user():
    if session.get("role") != 'admin': return jsonify({"error": "no auth"}), 403
    uid = request.get_json().get("id")
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (uid,))
    c.execute("DELETE FROM servers WHERE user_id=?", (uid,))
    conn.commit(); conn.close(); return jsonify({"status": "ok"})

@app.route("/api/admin/add_service", methods=["POST"])
def api_admin_add_service():
    if session.get("role") != 'admin': return jsonify({"error": "no auth"}), 403
    data = request.get_json()
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("INSERT INTO services (name, price, description) VALUES (?, ?, ?)", (data['name'], data['price'], data['description']))
    conn.commit(); conn.close(); return jsonify({"status": "ok"})

@app.route("/api/admin/del_service", methods=["POST"])
def api_admin_del_service():
    if session.get("role") != 'admin': return jsonify({"error": "no auth"}), 403
    sid = request.get_json().get("id")
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("DELETE FROM services WHERE id=?", (sid,))
    conn.commit(); conn.close(); return jsonify({"status": "ok"})

@app.route("/api/command", methods=["POST"])
def api_command():
    if not session.get("logged_in"): return jsonify({"status": "error"}), 401
    try: requests.post(f"{BOT_URL}/send", json={"command": request.get_json().get("command")}, timeout=10)
    except: pass
    return jsonify({"status": "ok"})

@app.route("/api/connect", methods=["POST"])
def api_connect():
    if not session.get("logged_in"): return jsonify({"status": "error"}), 401
    try: requests.post(f"{BOT_URL}/connect", json=request.get_json(), timeout=10)
    except: pass
    return jsonify({"status": "ok"})

@app.route("/api/reconnect", methods=["POST"])
def api_reconnect():
    if not session.get("logged_in"): return jsonify({"status": "error"}), 401
    try: requests.post(f"{BOT_URL}/reconnect", timeout=10)
    except: pass
    return jsonify({"status": "ok"})

@app.route("/api/chat")
def api_chat():
    if not session.get("logged_in"): return jsonify([]), 401
    try:
        resp = requests.get(f"{BOT_URL}/chat", timeout=10)
        return jsonify(resp.json())
    except: return jsonify([])

if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000)
