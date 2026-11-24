from flask import Flask, request, redirect, url_for, session, jsonify, render_template_string
import requests
import os

app = Flask(__name__)
app.secret_key = "OmegaProtocol_Secret_Key_ChangeMe"

USERNAME = "admin"
PASSWORD = "omega123"
console_log = []

# Если переменная BOT_URL не задана (например, на локальном ПК), используем localhost
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
        header { display: flex; justify-content: space-between; align-items: center; padding: 14px 28px; background: rgba(22,27,34,0.85); backdrop-filter: blur(6px); border-bottom: 1px solid rgba(136,255,0,0.15); }
        header h1 { font-size: 22px; font-family: 'Segoe UI', sans-serif; letter-spacing: 1px; display: flex; align-items: center; gap: 10px; }
        .hype { color: #ffffff; } .mc { color: #88ff00; }
        header h1 .dot { width: 10px; height: 10px; border-radius: 50%; background: #88ff00; box-shadow: 0 0 10px #88ff00; animation: blink 2s infinite; }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.4} }
        header .right { display: flex; align-items: center; gap: 18px; font-family: 'Segoe UI', sans-serif; font-size: 14px; }
        header .user-info { color: #8b949e; } header .user-info b { color: #88ff00; }
        header a.logout { color: #ff7b72; text-decoration: none; padding: 6px 14px; border: 1px solid rgba(255,123,114,0.4); border-radius: 6px; transition: 0.25s; }
        header a.logout:hover { background: rgba(255,123,114,0.15); border-color: #ff7b72; }
        .main { flex: 1; display: flex; gap: 18px; padding: 18px 28px; overflow: hidden; }
        .sidebar { width: 210px; display: flex; flex-direction: column; gap: 10px; overflow-y: auto; flex-shrink: 0; }
        .sidebar h3 { font-family: 'Segoe UI', sans-serif; font-size: 13px; text-transform: uppercase; letter-spacing: 1.5px; color: #6e7681; margin-bottom: 4px; }
        .quick-btn { background: rgba(22,27,34,0.8); border: 1px solid #30363d; border-radius: 8px; padding: 10px 12px; color: #c9d1d9; font-family: 'Consolas', monospace; font-size: 13px; cursor: pointer; text-align: left; transition: 0.2s; display: flex; align-items: center; gap: 8px; }
        .quick-btn:hover { border-color: #88ff00; background: rgba(136,255,0,0.08); transform: translateX(3px); color: #88ff00; }
        .quick-btn .icon { font-size: 15px; width: 20px; text-align: center; }
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
    </style>
</head>
<body>
    <header>
        <h1><span class="dot"></span> <span class="hype">Hype</span><span class="mc">MC</span> Panel — Консоль</h1>
        <div class="right">
            <span class="user-info">Вы вошли как <b>{{ user }}</b></span>
            <a class="logout" href="{{ url_for('logout') }}">Выйти</a>
        </div>
    </header>
    <div class="main">
        <aside class="sidebar">
            <h3>Быстрые команды</h3>
            <button class="quick-btn" data-cmd="list"><span class="icon">📋</span> list</button>
            <button class="quick-btn" data-cmd="ban "><span class="icon">🔨</span> ban &lt;ник&gt;</button>
            <button class="quick-btn" data-cmd="kick "><span class="icon">👢</span> kick &lt;ник&gt;</button>
            <button class="quick-btn" data-cmd="op "><span class="icon">⭐</span> op &lt;ник&gt;</button>
            <button class="quick-btn" data-cmd="say "><span class="icon">💬</span> say &lt;текст&gt;</button>
        </aside>
        <section class="console-area">
            <div id="console-output">
                <div class="line"><span class="system">Ожидание подключения к боту...</span></div>
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

        async function fetchChat() {
            try {
                const res = await fetch('/api/chat');
                const messages = await res.json();
                
                if (messages.length === 0 && !botOfflineReported) {
                    appendLine(`<span class="err">[ОШИБКА] Сайт не может получить данные от бота. Проверьте, запущен ли сервис mc-bot на Render.</span>`, true);
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
                    appendLine(`<span class="err">[ОШИБКА] Бот не отвечает. Убедитесь, что сервис mc-bot запущен на Render.</span>`, true);
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
        response_text = "Ошибка: Бот не запущен или недоступен. Проверьте сервис mc-bot на Render."
    except Exception as e:
        response_text = f"Ошибка: {str(e)}"

    console_log.append({"command": cmd, "response": response_text})
    return jsonify({"status": "ok", "response": response_text, "command": cmd})

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
