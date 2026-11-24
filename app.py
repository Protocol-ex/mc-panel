from flask import Flask, request, redirect, url_for, session, jsonify, render_template_string
import requests
import os

app = Flask(__name__)
app.secret_key = "OmegaProtocol_Secret_Key_ChangeMe"

USERNAME = "admin"
PASSWORD = "omega123"
console_log = []

BOT_URL = os.environ.get("BOT_URL", "http://127.0.0.1:3001").rstrip("/")

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Вход — HypeMC Panel</title>
    <style>
        * { box-sizing: border-box; }
        body { margin: 0; height: 100vh; display: flex; align-items: center; justify-content: center; font-family: 'Segoe UI', Arial, sans-serif; background: radial-gradient(circle at 30% 20%, #1b2735, #090a0f); color: #e0e0e0; }
        .login-card { background: rgba(30, 34, 50, 0.9); padding: 40px 50px; border-radius: 16px; box-shadow: 0 0 40px rgba(136, 255, 0, 0.15), 0 0 5px rgba(136, 255, 0, 0.3); border: 1px solid rgba(136, 255, 0, 0.2); width: 380px; }
        h1 { text-align: center; font-weight: 600; letter-spacing: 1px; margin-bottom: 30px; font-size: 28px; }
        .hype { color: #ffffff; } .mc { color: #88ff00; }
        label { display: block; margin-bottom: 6px; font-size: 14px; color: #9aa5b1; }
        input { width: 100%; padding: 12px 14px; margin-bottom: 20px; border-radius: 8px; border: 1px solid #3a3f55; background: #151a26; color: #e0e0e0; font-size: 15px; outline: none; transition: 0.3s; }
        input:focus { border-color: #88ff00; box-shadow: 0 0 8px rgba(136, 255, 0, 0.3); }
        button { width: 100%; padding: 13px; border: none; border-radius: 8px; background: linear-gradient(90deg, #66cc00, #88ff00); color: #0a0f1a; font-size: 17px; font-weight: bold; cursor: pointer; transition: 0.3s; }
        button:hover { filter: brightness(1.1); }
        .error { color: #ff5c5c; text-align: center; margin-top: 12px; font-size: 14px; }
    </style>
</head>
<body>
    <div class="login-card">
        <h1><span class="hype">Hype</span><span class="mc">MC</span></h1>
        <form method="POST">
            <label for="username">Логин</label>
            <input type="text" id="username" name="username" placeholder="admin" autocomplete="off" required>
            <label for="password">Пароль</label>
            <input type="password" id="password" name="password" placeholder="••••••••" required>
            <button type="submit">Войти</button>
        </form>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
    </div>
</body>
</html>
"""

CONSOLE_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Консоль — HypeMC Panel</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { height: 100vh; display: flex; flex-direction: column; font-family: 'Consolas', 'Courier New', monospace; background: #0a0c10; color: #c9d1d9; overflow: hidden; }
        body::before { content: ''; position: fixed; inset: 0; z-index: -1; background: radial-gradient(circle at 20% 20%, rgba(136,255,0,0.06), transparent 50%), radial-gradient(circle at 80% 80%, rgba(0,140,255,0.05), transparent 50%); animation: bgPulse 12s ease-in-out infinite alternate; }
        @keyframes bgPulse { 0%{opacity:0.6} 100%{opacity:1} }
        
        /* --- Шапка --- */
        header { display: flex; justify-content: space-between; align-items: center; padding: 14px 28px; background: rgba(22,27,34,0.85); backdrop-filter: blur(6px); border-bottom: 1px solid rgba(136,255,0,0.15); }
        .logo-area { display: flex; align-items: center; gap: 10px; }
        .menu-btn { background: none; border: 1px solid #30363d; color: #c9d1d9; font-size: 20px; padding: 4px 10px; border-radius: 6px; cursor: pointer; transition: 0.2s; margin-right: 15px; }
        .menu-btn:hover { border-color: #88ff00; color: #88ff00; }
        .logo-area h1 { font-size: 22px; font-family: 'Segoe UI', sans-serif; letter-spacing: 1px; display: flex; align-items: center; gap: 10px; }
        .hype { color: #ffffff; } .mc { color: #88ff00; }
        .logo-area .dot { width: 10px; height: 10px; border-radius: 50%; background: #88ff00; box-shadow: 0 0 10px #88ff00; animation: blink 2s infinite; }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.4} }
        
        .right-side { display: flex; align-items: center; gap: 20px; font-family: 'Segoe UI', sans-serif; font-size: 14px; }
        .user-info { color: #8b949e; } .user-info b { color: #88ff00; }
        .action-btns { display: flex; gap: 8px; }
        .top-btn { background: rgba(136,255,0,0.1); border: 1px solid #88ff00; color: #88ff00; padding: 6px 12px; border-radius: 6px; font-size: 13px; cursor: pointer; transition: 0.2s; }
        .top-btn:hover { background: #88ff00; color: #0a0f1a; }
        .logout { color: #ff7b72; text-decoration: none; padding: 6px 14px; border: 1px solid rgba(255,123,114,0.4); border-radius: 6px; transition: 0.25s; }
        .logout:hover { background: rgba(255,123,114,0.15); border-color: #ff7b72; }

        /* --- Панель статистики --- */
        .stats-panel { display: flex; gap: 15px; padding: 15px 28px 0 28px; }
        .stat-card { flex: 1; background: rgba(22,27,34,0.6); border: 1px solid #21262d; border-radius: 10px; padding: 12px 15px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.2); }
        .stat-info h4 { color: #8b949e; font-size: 12px; text-transform: uppercase; margin-bottom: 4px; font-family: 'Segoe UI', sans-serif; }
        .stat-info .value { font-size: 18px; font-weight: bold; color: #ffffff; }
        .stat-icon { font-size: 24px; opacity: 0.8; }

        .main { flex: 1; display: flex; gap: 18px; padding: 18px 28px; overflow: hidden; }
        .sidebar { width: 230px; display: flex; flex-direction: column; gap: 10px; overflow-y: auto; flex-shrink: 0; }
        .sidebar h3 { font-family: 'Segoe UI', sans-serif; font-size: 13px; text-transform: uppercase; letter-spacing: 1.5px; color: #6e7681; margin-bottom: 4px; margin-top: 10px; }
        .quick-btn { background: rgba(22,27,34,0.8); border: 1px solid #30363d; border-radius: 8px; padding: 10px 12px; color: #c9d1d9; font-family: 'Consolas', monospace; font-size: 13px; cursor: pointer; text-align: left; transition: 0.2s; display: flex; align-items: center; gap: 8px; }
        .quick-btn:hover { border-color: #88ff00; background: rgba(136,255,0,0.08); transform: translateX(3px); color: #88ff00; }
        .quick-btn .icon { font-size: 15px; width: 20px; text-align: center; }
        
        .server-form { display: flex; flex-direction: column; gap: 6px; background: rgba(22,27,34,0.6); padding: 10px; border-radius: 8px; border: 1px solid #30363d; }
        .server-form input { padding: 8px; border-radius: 6px; border: 1px solid #30363d; background: #0d1117; color: #c9d1d9; font-family: 'Consolas', monospace; font-size: 13px; outline: none; }
        .server-form input:focus { border-color: #88ff00; }
        .server-form button { padding: 8px; border-radius: 6px; border: none; background: #88ff00; color: #0a0f1a; font-weight: bold; cursor: pointer; font-size: 13px; margin-top: 4px; }
        .server-form button:hover { filter: brightness(1.1); }

        .console-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        #console-output { flex: 1; overflow-y: auto; background: rgba(10,12,16,0.85); border: 1px solid #21262d; border-radius: 10px; padding: 18px; font-size: 14px; line-height: 1.7; scroll-behavior: smooth; }
        #console-output::-webkit-scrollbar { width: 8px; }
        #console-output::-webkit-scrollbar-track { background: transparent; }
        #console-output::-webkit-scrollbar-thumb { background: #30363d; border-radius: 4px; }
        #console-output::-webkit-scrollbar-thumb:hover { background: #88ff00; }
        .line { margin-bottom: 5px; white-space: pre-wrap; word-break: break-all; }
        .line .prompt { color: #88ff00; user-select: none; }
        .line .cmd { color: #79c0ff; }
        .line .resp { color: #7ee787; }
        .line .err { color: #ff7b72; }
        .line .system { color: #8b949e; font-style: italic; }
        .line .time { color: #484f58; font-size: 12px; margin-right: 6px; }
        .line .chat-user { color: #ffb86c; font-weight: bold; }
        .line .chat-msg { color: #f8f8f2; }
        .input-row { display: flex; margin-top: 12px; gap: 10px; }
        #cmd-input { flex: 1; padding: 14px 16px; border-radius: 10px; border: 1px solid #30363d; background: rgba(22,27,34,0.9); color: #c9d1d9; font-family: 'Consolas', monospace; font-size: 15px; outline: none; transition: 0.25s; }
        #cmd-input:focus { border-color: #88ff00; box-shadow: 0 0 14px rgba(136,255,0,0.18); background: #161b22; }
        #send-btn { padding: 0 28px; border: none; border-radius: 10px; cursor: pointer; background: linear-gradient(135deg, #66cc00, #88ff00); color: #0a0f1a; font-weight: bold; font-size: 15px; font-family: 'Segoe UI', sans-serif; transition: 0.2s; box-shadow: 0 0 18px rgba(136,255,0,0.25); }
        #send-btn:hover { filter: brightness(1.12); box-shadow: 0 0 26px rgba(136,255,0,0.4); }
        #send-btn:active { transform: scale(0.97); }

        /* --- Выезжающая панель (Сайдбар) --- */
        .slide-panel { position: fixed; top: 0; left: -350px; width: 320px; height: 100vh; background: rgba(13,17,23,0.95); backdrop-filter: blur(10px); border-right: 1px solid #30363d; z-index: 1000; transition: left 0.3s ease; padding: 20px; display: flex; flex-direction: column; gap: 20px; box-shadow: 5px 0 30px rgba(0,0,0,0.5); }
        .slide-panel.open { left: 0; }
        .panel-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.5); z-index: 999; display: none; }
        .panel-overlay.open { display: block; }
        .close-btn { position: absolute; top: 15px; right: 15px; background: none; border: none; color: #8b949e; font-size: 20px; cursor: pointer; }
        .close-btn:hover { color: #ff7b72; }
        
        .profile-section { background: rgba(22,27,34,0.8); border: 1px solid #30363d; border-radius: 10px; padding: 15px; text-align: center; }
        .profile-nick { font-size: 20px; font-weight: bold; color: #88ff00; margin-bottom: 5px; font-family: 'Segoe UI', sans-serif; }
        .profile-ip { font-size: 13px; color: #8b949e; font-family: 'Consolas', monospace; }
        
        .ttt-section { background: rgba(22,27,34,0.8); border: 1px solid #30363d; border-radius: 10px; padding: 15px; text-align: center; flex: 1; }
        .ttt-section h3 { color: #ffffff; margin-bottom: 10px; font-size: 16px; font-family: 'Segoe UI', sans-serif; }
        .ttt-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px; width: 150px; margin: 0 auto 15px auto; }
        .ttt-cell { width: 46px; height: 46px; background: #0a0c10; border: 1px solid #30363d; border-radius: 5px; display: flex; justify-content: center; align-items: center; font-size: 24px; font-weight: bold; cursor: pointer; transition: 0.2s; color: #c9d1d9; font-family: 'Consolas', monospace; }
        .ttt-cell:hover { background: rgba(136,255,0,0.1); border-color: #88ff00; }
        .ttt-cell.x { color: #88ff00; }
        .ttt-cell.o { color: #ff7b72; }
        .ttt-status { font-size: 14px; color: #8b949e; margin-bottom: 10px; height: 20px; }
        .ttt-reset { background: #30363d; border: none; color: #fff; padding: 6px 12px; border-radius: 5px; cursor: pointer; font-size: 12px; }
        .ttt-reset:hover { background: #8b949e; }

    </style>
</head>
<body>
    <!-- Выдвижная панель -->
    <div class="panel-overlay" id="panel-overlay" onclick="togglePanel()"></div>
    <div class="slide-panel" id="slide-panel">
        <button class="close-btn" onclick="togglePanel()">✖</button>
        
        <div class="profile-section">
            <div class="profile-nick">Steve_Bot</div>
            <div class="profile-ip">mc.hypemc.pro:25565</div>
        </div>

        <div class="ttt-section">
            <h3>Крестики-Нолики</h3>
            <div class="ttt-status" id="ttt-status">Твой ход (X)</div>
            <div class="ttt-grid" id="ttt-grid">
                <div class="ttt-cell" data-index="0"></div>
                <div class="ttt-cell" data-index="1"></div>
                <div class="ttt-cell" data-index="2"></div>
                <div class="ttt-cell" data-index="3"></div>
                <div class="ttt-cell" data-index="4"></div>
                <div class="ttt-cell" data-index="5"></div>
                <div class="ttt-cell" data-index="6"></div>
                <div class="ttt-cell" data-index="7"></div>
                <div class="ttt-cell" data-index="8"></div>
            </div>
            <button class="ttt-reset" onclick="resetTTT()">Заново</button>
        </div>
    </div>

    <header>
        <div class="logo-area">
            <button class="menu-btn" onclick="togglePanel()">☰</button>
            <h1><span class="dot"></span> <span class="hype">Hype</span><span class="mc">MC</span> Panel</h1>
        </div>
        <div class="right-side">
            <div class="action-btns">
                <button class="top-btn" onclick="fakeAction('Сервер перезагружается...')">🔄 Перезагрузка</button>
                <button class="top-btn" onclick="fakeAction('Резервная копия создана!')">💾 Бэкап</button>
            </div>
            <span class="user-info">Вы вошли как <b>{{ user }}</b></span>
            <a class="logout" href="{{ url_for('logout') }}">Выйти</a>
        </div>
    </header>

    <div class="stats-panel">
        <div class="stat-card">
            <div class="stat-info">
                <h4>Игроков онлайн</h4>
                <div class="value" id="stat-online">124 / 500</div>
            </div>
            <div class="stat-icon">👥</div>
        </div>
        <div class="stat-card">
            <div class="stat-info">
                <h4>Пинг сервера</h4>
                <div class="value" id="stat-ping">12 ms</div>
            </div>
            <div class="stat-icon">📶</div>
        </div>
        <div class="stat-card">
            <div class="stat-info">
                <h4>Аптайм (Uptime)</h4>
                <div class="value">99.9%</div>
            </div>
            <div class="stat-icon">⚡</div>
        </div>
        <div class="stat-card">
            <div class="stat-info">
                <h4>TPS (Тики)</h4>
                <div class="value">19.8</div>
            </div>
            <div class="stat-icon">⚙️</div>
        </div>
    </div>

    <div class="main">
        <aside class="sidebar">
            <h3>Быстрые команды</h3>
            <button class="quick-btn" data-cmd="list"><span class="icon">📋</span> list</button>
            <button class="quick-btn" data-cmd="ban "><span class="icon">🔨</span> ban &lt;ник&gt;</button>
            <button class="quick-btn" data-cmd="kick "><span class="icon">👢</span> kick &lt;ник&gt;</button>
            <button class="quick-btn" data-cmd="op "><span class="icon">⭐</span> op &lt;ник&gt;</button>
            <button class="quick-btn" data-cmd="say "><span class="icon">💬</span> say &lt;текст&gt;</button>

            <h3>Настройки сервера</h3>
            <div class="server-form">
                <input type="text" id="srv-host" placeholder="IP или домен" value="mc.hypemc.pro">
                <input type="number" id="srv-port" placeholder="Порт" value="25565">
                <button id="btn-connect">Подключиться</button>
            </div>
        </aside>
        <section class="console-area">
            <div id="console-output">
                <div class="line"><span class="system">Добро пожаловать в консоль HypeMC Panel. Ожидание команд...</span></div>
            </div>
            <form class="input-row" id="cmd-form">
                <input type="text" id="cmd-input" placeholder="Введите команду..." autocomplete="off" autofocus>
                <button type="submit" id="send-btn">Отправить</button>
            </form>
        </section>
    </div>
    <script>
        const output = document.getElementById('console-output');
        const form = document.getElementById('cmd-form');
        const input = document.getElementById('cmd-input');
        let lastChatLength = -1;
        let botOfflineReported = false;

        function now() {
            const d = new Date();
            return d.toLocaleTimeString('ru-RU', {hour:'2-digit', minute:'2-digit', second:'2-digit'});
        }

        function appendLine(html, isError = false) {
            const div = document.createElement('div');
            div.className = 'line';
            div.innerHTML = `<span class="time">${now()}</span> ` + html;
            output.appendChild(div);
            output.scrollTop = output.scrollHeight;
        }

        function fakeAction(text) {
            appendLine(`<span class="system">[СИСТЕМА] ${text}</span>`);
        }

        // ==== Управление панелью ====
        function togglePanel() {
            document.getElementById('slide-panel').classList.toggle('open');
            document.getElementById('panel-overlay').classList.toggle('open');
        }

        // ==== Крестики-Нолики ====
        let board = ["", "", "", "", "", "", "", "", ""];
        let currentPlayer = "X";
        let gameActive = true;
        const winningConditions = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8], // Rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8], // Cols
            [0, 4, 8], [2, 4, 6]             // Diags
        ];

        document.querySelectorAll('.ttt-cell').forEach(cell => {
            cell.addEventListener('click', handleCellClick);
        });

        function handleCellClick(e) {
            const clickedCell = e.target;
            const clickedCellIndex = parseInt(clickedCell.getAttribute('data-index'));

            if (board[clickedCellIndex] !== "" || !gameActive || currentPlayer !== "X") return;

            makeMove(clickedCell, clickedCellIndex, "X");
            if (gameActive) {
                currentPlayer = "O";
                document.getElementById('ttt-status').innerText = "Ход бота (O)...";
                setTimeout(botMove, 500);
            }
        }

        function makeMove(cell, index, player) {
            board[index] = player;
            cell.innerText = player;
            cell.classList.add(player.toLowerCase());
            checkResult();
        }

        function botMove() {
            if (!gameActive) return;
            let emptyCells = board.map((val, index) => val === "" ? index : null).filter(val => val !== null);
            if (emptyCells.length === 0) return;
            
            // Простой ИИ: случайный ход
            const randomIndex = emptyCells[Math.floor(Math.random() * emptyCells.length)];
            const cell = document.querySelector(`.ttt-cell[data-index="${randomIndex}"]`);
            
            makeMove(cell, randomIndex, "O");
            if (gameActive) {
                currentPlayer = "X";
                document.getElementById('ttt-status').innerText = "Твой ход (X)";
            }
        }

        function checkResult() {
            let roundWon = false;
            for (let i = 0; i <= 7; i++) {
                const winCondition = winningConditions[i];
                let a = board[winCondition[0]];
                let b = board[winCondition[1]];
                let c = board[winCondition[2]];
                if (a === '' || b === '' || c === '') continue;
                if (a === b && b === c) {
                    roundWon = true;
                    break;
                }
            }

            if (roundWon) {
                document.getElementById('ttt-status').innerText = `Победили ${currentPlayer === "X" ? "Крестики" : "Нолики"}!`;
                gameActive = false;
                return;
            }

            if (!board.includes("")) {
                document.getElementById('ttt-status').innerText = "Ничья!";
                gameActive = false;
                return;
            }
        }

        function resetTTT() {
            board = ["", "", "", "", "", "", "", "", ""];
            gameActive = true;
            currentPlayer = "X";
            document.getElementById('ttt-status').innerText = "Твой ход (X)";
            document.querySelectorAll('.ttt-cell').forEach(cell => {
                cell.innerText = "";
                cell.classList.remove('x', 'o');
            });
        }

        // ==== Остальные функции ====
        setInterval(() => {
            const online = Math.floor(Math.random() * 20) + 120;
            document.getElementById('stat-online').innerText = `${online} / 500`;
            const ping = Math.floor(Math.random() * 15) + 10;
            document.getElementById('stat-ping').innerText = `${ping} ms`;
        }, 5000);

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const cmd = input.value.trim();
            if (!cmd) return;
            input.value = '';
            appendLine(`<span class="prompt">></span> <span class="cmd">${cmd}</span>`);
            try {
                const res = await fetch('/api/command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: cmd })
                });
                const data = await res.json();
                if (data.status === 'ok') {
                    appendLine(`<span class="resp">${data.response}</span>`);
                } else {
                    appendLine(`<span class="err">${data.message || 'Ошибка'}</span>`, true);
                }
            } catch (err) {
                appendLine(`<span class="err">Сетевая ошибка: ${err.message}</span>`, true);
            }
        });

        document.querySelectorAll('.quick-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                input.value = btn.dataset.cmd;
                input.focus();
                if (!btn.dataset.cmd.endsWith(' ')) form.dispatchEvent(new Event('submit', { cancelable: true }));
            });
        });

        document.getElementById('btn-connect').addEventListener('click', async () => {
            const host = document.getElementById('srv-host').value.trim();
            const port = document.getElementById('srv-port').value.trim();
            if (!host) return alert('Введите IP сервера');
            appendLine(`<span class="system">Отправка команды переподключения на ${host}:${port}...</span>`);
            try {
                const res = await fetch('/api/connect', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ host, port })
                });
                const data = await res.json();
                if (data.status === 'ok') {
                    appendLine(`<span class="resp">Сервер изменен. Бот переподключается...</span>`);
                    lastChatLength = -1; 
                    botOfflineReported = false;
                } else {
                    appendLine(`<span class="err">Ошибка: ${data.message}</span>`, true);
                }
            } catch (err) {
                appendLine(`<span class="err">Ошибка сети: ${err.message}</span>`, true);
            }
        });

        async function fetchChat() {
            try {
                const res = await fetch('/api/chat');
                const messages = await res.json();
                
                if (messages.length === 0 && !botOfflineReported) {
                    appendLine(`<span class="err">[ОШИБКА] Сайт не может получить данные от бота. Проверьте сервис mc-bot.</span>`, true);
                    botOfflineReported = true;
                    return;
                }

                if (messages.length > lastChatLength) {
                    let newMessages = lastChatLength === -1 ? [] : messages.slice(lastChatLength);
                    newMessages.forEach(msg => {
                        if (msg.type === 'chat') {
                            appendLine(`<span class="chat-user">[Сервер]</span> <span class="chat-msg">${msg.text}</span>`);
                        } else if (msg.type === 'system') {
                            appendLine(`<span class="system">[Система] ${msg.text}</span>`);
                        }
                    });
                    lastChatLength = messages.length;
                    botOfflineReported = false;
                }
            } catch (err) {
                if (!botOfflineReported) {
                    appendLine(`<span class="err">[ОШИБКА] Бот не отвечает.</span>`, true);
                    botOfflineReported = true;
                }
            }
        }

        setInterval(fetchChat, 1000);
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = request.form.get("username")
        pwd = request.form.get("password")
        if user == USERNAME and pwd == PASSWORD:
            session["logged_in"] = True
            session["user"] = user
            return redirect(url_for("console"))
        else:
            error = "Неверный логин или пароль"
    return render_template_string(LOGIN_HTML, error=error)

@app.route("/console")
def console():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template_string(CONSOLE_HTML, user=session["user"])

@app.route("/api/command", methods=["POST"])
def api_command():
    if not session.get("logged_in"):
        return jsonify({"status": "error", "message": "Не авторизован"}), 401
    data = request.get_json()
    cmd = data.get("command", "").strip()
    if not cmd:
        return jsonify({"status": "error", "message": "Пустая команда"}), 400

    try:
        resp = requests.post(f"{BOT_URL}/send", json={"command": cmd}, timeout=10)
        if resp.status_code == 200:
            response_text = f"Команда отправлена в Minecraft."
        else:
            response_text = f"Ошибка бота: {resp.json().get('error', 'Бот не ответил')}"
    except requests.exceptions.ConnectionError:
        response_text = "Ошибка: Бот не запущен или недоступен."
    except Exception as e:
        response_text = f"Ошибка: {str(e)}"

    console_log.append({"command": cmd, "response": response_text})
    return jsonify({"status": "ok", "response": response_text, "command": cmd})

@app.route("/api/connect", methods=["POST"])
def api_connect():
    if not session.get("logged_in"):
        return jsonify({"status": "error", "message": "Не авторизован"}), 401
    data = request.get_json()
    host = data.get("host", "").strip()
    port = data.get("port", 25565)
    
    if not host:
        return jsonify({"status": "error", "message": "Пустой IP"}), 400

    try:
        resp = requests.post(f"{BOT_URL}/connect", json={"host": host, "port": port}, timeout=10)
        if resp.status_code == 200:
            return jsonify({"status": "ok", "message": "Подключение инициировано"})
        else:
            return jsonify({"status": "error", "message": "Ошибка бота"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/chat")
def api_chat():
    if not session.get("logged_in"):
        return jsonify([]), 401
    try:
        resp = requests.get(f"{BOT_URL}/chat", timeout=10)
        return jsonify(resp.json())
    except:
        return jsonify([])

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000)
