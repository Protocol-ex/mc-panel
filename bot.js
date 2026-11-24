const mineflayer = require('mineflayer');
const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');

// Настройки по умолчанию (если не задать через сайт)
let currentConfig = {
    host: 'Eternamc.mc-join.me', // <--- Замените на ваш дефолтный IP
    port: 25565,
    username: 'MechtaAdm',        // <--- Замените на ваш дефолтный ник
    auth: 'offline'
};

let bot = null;
let chatLog = [];
let lastMessage = "";

const app = express();
app.use(cors());
app.use(bodyParser.json());

// Смена сервера
app.post('/connect', (req, res) => {
    const { host, port, username } = req.body;
    if (host) currentConfig.host = host;
    if (port) currentConfig.port = parseInt(port);
    if (username) currentConfig.username = username;

    if (bot) {
        bot.quit();
        bot = null;
    }
    
    chatLog.push({ type: 'system', text: `Переподключение к серверу ${currentConfig.host}:${currentConfig.port}...` });
    createBot();
    res.json({ status: 'ok', message: 'Подключение инициировано' });
});

// Отправка команды
app.post('/send', (req, res) => {
    const { command } = req.body;
    if (!bot || !bot.player) return res.status(503).json({ error: 'Бот не в сети' });
    try {
        bot.chat(command);
        console.log(`[ОТПРАВЛЕНО В ИГРУ] ${command}`);
        res.json({ status: 'ok' });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// Получение чата
app.get('/chat', (req, res) => {
    res.json(chatLog.slice(-100));
});

// Пинг (для cron-job.org)
app.get('/health', (req, res) => {
    res.send('OK');
});

app.listen(process.env.PORT || 3001, () => {
    console.log('=== СЕРВЕР БОТА ЗАПУЩЕН ===');
});

function createBot() {
    if (bot) bot.quit();
    
    console.log(`[BOT] Подключение к ${currentConfig.host}:${currentConfig.port}...`);
    bot = mineflayer.createBot(currentConfig);

    bot.on('spawn', () => {
        console.log(`\x1b[32m[BOT] ЗАШЕЛ НА СЕРВЕР КАК ${bot.username}\x1b[0m`);
        chatLog.push({ type: 'system', text: `Бот ${bot.username} зашел на сервер` });
    });

    bot.on('messagestr', (message) => {
        if (message === lastMessage) return;
        lastMessage = message;
        console.log(`[ЧАТ] ${message}`);
        chatLog.push({ type: 'chat', username: 'Сервер', text: message });
    });

    bot.on('error', (err) => {
        console.log(`\x1b[31m[BOT] Ошибка: ${err.message}\x1b[0m`);
        chatLog.push({ type: 'system', text: `Ошибка подключения: ${err.message}` });
    });

    bot.on('end', () => {
        console.log('[BOT] Отключен.');
    });
}

createBot();
