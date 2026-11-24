const mineflayer = require('mineflayer');
const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');

// Настройки по умолчанию
let currentConfig = {
    host: 'mc.hypemc.pro',
    port: 25565,
    username: 'MechtaAdm', // Твой ник
    auth: 'offline',
    version: '1.21.11',    // Жестко заданная версия
};

let bot = null;
let chatLog = [];
let lastMessage = "";
let reconnectTimeout = null;
let afkInterval = null;

const app = express();
app.use(cors());
app.use(bodyParser.json());

// API для получения данных с сайта
app.post('/connect', (req, res) => {
    const { host, port, username } = req.body;
    if (host) currentConfig.host = host;
    if (port) currentConfig.port = parseInt(port);
    if (username) currentConfig.username = username;

    chatLog.push({ type: 'system', text: `Запрос на подключение к ${currentConfig.host}...` });
    startBot();
    res.json({ status: 'ok' });
});

app.post('/reconnect', (req, res) => {
    chatLog.push({ type: 'system', text: `Принудительный перезапуск...` });
    startBot();
    res.json({ status: 'ok' });
});

app.post('/send', (req, res) => {
    const { command } = req.body;
    if (!bot || !bot.player) return res.status(503).json({ error: 'Бот не в сети' });
    try {
        bot.chat(command);
        res.json({ status: 'ok' });
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.get('/chat', (req, res) => { res.json(chatLog.slice(-100)); });
app.get('/health', (req, res) => { res.send('OK'); });

// Запуск веб-сервера для Render
app.listen(process.env.PORT || 3001, () => { console.log('=== СЕРВЕР БОТА ЗАПУЩЕН ==='); });

// Функция запуска бота (с защитой от дублирования)
function startBot() {
    // Очищаем старые таймеры и отключаем текущего бота
    if (reconnectTimeout) clearTimeout(reconnectTimeout);
    if (afkInterval) clearInterval(afkInterval);
    if (bot) {
        try { bot.quit(); } catch(e){}
        bot = null;
    }

    console.log(`[BOT] Подключение к ${currentConfig.host}:${currentConfig.port}...`);
    chatLog.push({ type: 'system', text: `Подключение к ${currentConfig.host}...` });

    try {
        bot = mineflayer.createBot(currentConfig);
    } catch (err) {
        console.log(`[BOT] Ошибка создания: ${err.message}`);
        chatLog.push({ type: 'system', text: `Ошибка создания бота: ${err.message}` });
        return;
    }

    // Успешный вход
    bot.on('spawn', () => {
        console.log(`[BOT] УСПЕШНО ЗАШЕЛ КАК ${bot.username}`);
        chatLog.push({ type: 'system', text: `Бот ${bot.username} успешно зашел на сервер` });

        // Простая имитация активности, чтобы не выкинуло за АФК
        afkInterval = setInterval(() => {
            if (bot && bot.entity) {
                // Прыжок
                bot.setControlState('jump', true);
                setTimeout(() => { if(bot) bot.setControlState('jump', false); }, 500);
                // Поворот головы
                bot.look(Math.random() * Math.PI * 2, 0, false);
            }
        }, 5000);
    });

    // Ловим чат
    bot.on('messagestr', (message) => {
        if (message === lastMessage) return;
        lastMessage = message;
        chatLog.push({ type: 'chat', username: 'Сервер', text: message });
    });

    // Ловим ошибки
    bot.on('error', (err) => {
        console.log(`[BOT] Ошибка: ${err.message}`);
        chatLog.push({ type: 'system', text: `Ошибка: ${err.message}` });
    });

    // Ловим кик
    bot.on('kicked', (reason) => {
        let reasonStr = typeof reason === 'object' ? JSON.stringify(reason) : reason;
        console.log(`[BOT] КИКНУТ: ${reasonStr}`);
        chatLog.push({ type: 'system', text: `Бот кикнут: ${reasonStr}` });
    });

    // Переподключение при обрыве связи
    bot.on('end', () => {
        console.log(`[BOT] Отключен от сервера.`);
        chatLog.push({ type: 'system', text: `Бот отключен. Перезаход через 15 секунд...` });
        
        if (afkInterval) clearInterval(afkInterval);
        
        // Перезаходим только через 15 секунд, чтобы не забанили
        reconnectTimeout = setTimeout(() => {
            startBot();
        }, 15000);
    });
}

// Первый запуск при старте сервера
startBot();
