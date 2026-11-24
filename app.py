from flask import Flask, request, redirect, url_for, session, jsonify, render_template
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

# Если на Render задана переменная RESET_DB=true, удаляем старую базу
if os.environ.get("RESET_DB") == "true" and os.path.exists(DB_FILE):
    os.remove(DB_FILE)
    print("БАЗА ДАННЫХ СБРОШЕНА!")

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
# HTML ШАБЛОНЫ (JINJA2)
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
        input { width: 100%; padding: 12px 14px; margin-bottom: 15px; border-radius: 8px; border: 1px solid #3a3f55; background: #151a26; color: #e0e0e0; font-size: 15px; outline: none; }
        input:focus { border-color: #88ff00; box-shadow: 0 0 8px rgba(136, 255, 0, 0.3); }
        button { width: 100%; padding: 13px; border: none; border-radius: 8px; background: linear-gradient(90deg, #66cc00, #88ff00); color: #0a0f1a; font-size: 17px; font-weight: bold; cursor: pointer; transition: 0.3s; margin-bottom: 15px; }
        button:hover { filter: brightness(1.1); }
        .error { color: #ff5c5c; margin-bottom: 15px; font-size: 14px; }
        .captcha-box { display: flex; align-items: center; justify-content: flex-start; gap: 10px; margin-bottom: 20px; background: #151a26; border: 1px solid #3a3f55; padding: 10px; border-radius: 8px; cursor: not-allowed; opacity: 0.5; transition: 0.3s; }
        .captcha-box.active { cursor: pointer; opacity: 1; border-color: #88ff00; }
        .captcha-box input { width: 20px; height: 20px; margin: 0; cursor: inherit; }
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
            if (tttWon) { document.getElementById('robot-check').disabled = false; document.getElementById('robot-check').checked = true; document.getElementById('captcha-label').classList.add('active'); }
        }
    </script>
</body>
</html>
"""

BASE_LAYOUT = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}HypeMC Panel{% endblock %}</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { height: 100vh; display: flex; font-family: 'Segoe UI', sans-serif; background: #0a0c10; color: #c9d1d9; overflow: hidden; }
        .sidebar { width: 240px; background: rgba(22,27,34,0.95); border-right: 1px solid #30363d; display: flex; flex-direction: column; padding: 20px 0; z-index: 10; }
        .logo { font-size: 22px; font-weight: bold; padding: 0 20px; margin-bottom: 30px; color: #fff; }
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
    </style>
    {% block head %}{% endblock %}
</head>
<body>
    <aside class="sidebar">
        <div class="logo"><span class="hype">Hype</span><span class="mc">MC</span></div>
        <a href="/dashboard" class="nav-item {% if active_tab == 'servers' %}active{% endif %}">
            <span class="nav-icon">🖥</span><span class="nav-text">Мои сервера</span>
        </a>
        <a href="/services" class="nav-item {% if active_tab == 'services' %}active{% endif %}">
            <span class="nav-icon">💎</span><span class="nav-text">Услуги</span>
        </a>
        {% if session.get('role') == 'admin' %}
        <a href="/admin" class="nav-item {% if active_tab == 'admin' %}active{% endif %}">
            <span class="nav-icon">🛡️</span><span class="nav-text">Админ-панель</span>
        </a>
        {% endif %}
    </aside>
    <div class="content">
        <div class="topbar">
            <div style="font-size: 18px; font-weight: bold; color: #fff;">{% block header_title %}{% endblock %}</div>
            <div>
                <span class="user-info">{{ session.get('user') }} ({{ session.get('role') }})</span>
                <a class="logout" href="/logout">Выйти</a>
            </div>
        </div>
        <div class="page-body">
            {% block content %}{% endblock %}
        </div>
    </div>
    {% block scripts %}{% endblock %}
</body>
</html>
"""

DASHBOARD_HTML = """
{% extends "base" %}
{% block title %}Мои сервера — HypeMC Panel{% endblock %}
{% block header_title %}Мои сервера{% endblock %}
{% block content %}
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
{% endblock %}
{% block scripts %}
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
            document.getElementById('m-name').value = ""; document.getElementById('m-ip').value = ""; document.getElementById('m-port').value = "25565"; document.getElementById('m-nick').value = "";
        }
    }
    function closeModal() { document.getElementById('add-modal').style.display = 'none'; }
    async function loadServers() {
        const res = await fetch('/api/get_servers');
        const servers = await res.json();
        const grid = document.getElementById('servers-grid');
        grid.innerHTML = '';
        if (servers.length === 0) { grid.innerHTML = '<p style="color:#8b949e;">Нет серверов. Нажмите "+ Создать консоль".</p>'; return; }
        servers.forEach(s => {
            grid.innerHTML += `
                <div style="background: rgba(22,27,34,0.8); border: 1px solid #30363d; border-radius: 12px; padding: 15px; position: relative;">
                    <button style="position: absolute; top: 10px; right: 10px; background: none; border: none; color: #8b949e; cursor: pointer;" onclick='openModal(${JSON.stringify(s)})'>✎</button>
                    <h3 style="color: #fff; margin-bottom: 8px; font-size: 16px;">${s.name}</h3>
                    <p style="color: #8b949e; font-size: 13px; font-family: monospace; margin-bottom: 5px;">IP: ${s.ip}:${s.port}</p>
                    <p style="color: #ffb86c; font-weight: bold; margin-bottom: 12px; font-size: 13px;">Ник: ${s.nickname}</p>
                    <a href="/console/${s.id}" style="display: block; text-align: center; background: #88ff00; color: #000; text-decoration: none; padding: 10px; border-radius: 8px; font-weight: bold; font-size: 14px;">Открыть консоль</a>
                </div>
            `;
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
        if (res.ok) { closeModal(); loadServers(); } 
        else { const d = await res.json(); alert(d.message || 'Ошибка!'); }
    }
    loadServers();
</script>
{% endblock %}
"""

SERVICES_HTML = """
{% extends "base" %}
{% block title %}Услуги — HypeMC Panel{% endblock %}
{% block header_title %}Тарифы и Услуги{% endblock %}
{% block content %}
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px;" id="services-grid"></div>
{% endblock %}
{% block scripts %}
<script>
    async function loadServices() {
        const res = await fetch('/api/services');
        const services = await res.json();
        const grid = document.getElementById('services-grid');
        grid.innerHTML = '';
        services.forEach(s => {
            grid.innerHTML += `
                <div style="background: rgba(22,27,34,0.8); border: 1px solid #30363d; border-radius: 12px; padding: 25px; text-align: center; transition: 0.2s;">
                    <h3 style="color: #fff; font-size: 20px; margin-bottom: 10px;">${s.name}</h3>
                    <div style="color: #88ff00; font-size: 24px; font-weight: bold; margin-bottom: 15px;">${s.price}</div>
                    <p style="color: #8b949e; font-size: 14px; margin-bottom: 20px; min-height: 40px;">${s.description}</p>
                    <button style="width: 100%; padding: 10px; background: none; border: 1px solid #88ff00; color: #88ff00; border-radius: 8px; font-weight: bold; cursor: pointer;" onclick="alert('Для покупки напишите в Поддержку!')">Выбрать</button>
                </div>
            `;
        });
    }
    loadServices();
</script>
{% endblock %}
"""

ADMIN_HTML = """
{% extends "base" %}
{% block title %}Админ-панель — HypeMC Panel{% endblock %}
{% block header_title %}Админ-панель{% endblock %}
{% block head %}
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
{% endblock %}
{% block content %}
    <div class="admin-grid">
        <div class="panel">
            <h2>Пользователи</h2>
            <div class="add-form">
                <input type="text" id="new-user" placeholder="Логин">
                <input type="password" id="new-pass" placeholder="Пароль">
                <button onclick="addUser()">Добавить</button>
            </div>
            <table id="users-table"><thead><tr><th>Логин</th><th>Лимит</th><th>Действие</th></tr></thead><tbody></tbody></table>
        </div>
        <div class="panel">
            <h2>Управление Услугами</h2>
            <div class="add-form" style="flex-direction: column;">
                <input type="text" id="srv-name" placeholder="Название (например, VIP)">
                <input type="text" id="srv-price" placeholder="Цена (например, 100р/мес)">
                <input type="text" id="srv-desc" placeholder="Описание">
                <button onclick="addService()" style="width: 100%;">Добавить тариф</button>
            </div>
            <div id="services-list" style="max-height: 200px; overflow-y: auto;"></div>
        </div>
        <div class="panel" style="grid-column: 1 / -1;">
            <h2>Поддержка (Чаты)</h2>
            <div class="messenger">
                <div class="users-list" id="chat-users-list">
                    <div style="padding: 15px; color: #8b949e; font-size: 13px;">Выберите чат</div>
                </div>
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
{% endblock %}
{% block scripts %}
<script>
    let currentRecipient = null;
    async function loadUsers() {
        const res = await fetch('/api/admin/get_users'); const users = await res.json();
        const tbody = document.querySelector('#users-table tbody'); tbody.innerHTML = '';
        users.forEach(u => {
            tbody.innerHTML += `<tr><td>${u.username}</td><td><input type="number" value="${u.server_limit}" style="width: 50px; background: #0d1117; color: #fff; border: 1px solid #30363d; padding: 4px; border-radius: 4px;" onchange="updateLimit(${u.id}, this.value)"></td><td>${u.username !== 'admin' ? `<button class="btn-del" onclick="delUser(${u.id})">Удалить</button>` : '-'}</td></tr>`;
        });
    }
    async function updateLimit(id, limit) { await fetch('/api/admin/set_limit', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id, limit: parseInt(limit)}) }); }
    async function addUser() {
        const u = document.getElementById('new-user').value.trim(); const p = document.getElementById('new-pass').value.trim();
        if (!u || !p) return alert('Заполните поля');
        const res = await fetch('/api/admin/add_user', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: u, password: p}) });
        if (res.ok) { document.getElementById('new-user').value = ''; document.getElementById('new-pass').value = ''; loadUsers(); } else { alert('Ошибка'); }
    }
    async function delUser(id) { if (!confirm('Удалить?')) return; await fetch('/api/admin/del_user', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id}) }); loadUsers(); }
    async function loadServices() {
        const res = await fetch('/api/services'); const services = await res.json();
        document.getElementById('services-list').innerHTML = services.map(s => `<div style="display: flex; justify-content: space-between; align-items: center; padding: 8px; border-bottom: 1px solid #30363d;"><div><b style="color:#fff;">${s.name}</b> - ${s.price}</div><button class="btn-del" onclick="delService(${s.id})">X</button></div>`).join('');
    }
    async function addService() {
        const name = document.getElementById('srv-name').value.trim(); const price = document.getElementById('srv-price').value.trim(); const desc = document.getElementById('srv-desc').value.trim();
        if (!name || !price) return alert('Заполните название и цену');
        await fetch('/api/admin/add_service', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name, price, description: desc}) });
        document.getElementById('srv-name').value = ''; document.getElementById('srv-price').value = ''; document.getElementById('srv-desc').value = ''; loadServices();
    }
    async function delService(id) { if(!confirm('Удалить тариф?')) return; await fetch('/api/admin/del_service', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id}) }); loadServices(); }
    async function loadChatUsers() {
        const res = await fetch('/api/admin/get_chat_users'); const users = await res.json();
        const list = document.getElementById('chat-users-list'); list.innerHTML = '';
        if (users.length === 0) { list.innerHTML = '<div style="padding: 15px; color: #8b949e; font-size: 13px;">Нет сообщений</div>'; return; }
        users.forEach(u => {
            const div = document.createElement('div'); div.className = `user-item ${currentRecipient === u ? 'active' : ''}`; div.innerText = u;
            div.onclick = () => { currentRecipient =
