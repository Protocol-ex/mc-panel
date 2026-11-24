const mineflayer = require('mineflayer');
const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');

const BOT_CONFIG = {
    host: '185.9.145.186', // <--- УБЕДИТЕСЬ, ЧТО ЗДЕСЬ ПРАВИЛЬНЫЙ IP!
    port: 32351,
    username: 'MechtaAdm',
    auth: 'offline',
    version: false,
};

let bot = null;
let chatLog = [];
let lastMessage = ""; // Защита от дублей

const app = express();
app.use(cors());
app.use(bodyParser.json());

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

app.get('/chat', (req, res) => {
    res.json(chatLog.slice(-100)); // Отдаем последние 100 сообщений
});

app.listen(3001, () => {
    console.log('=== СЕРВЕР БОТА ЗАПУЩЕН НА ПОРТУ 3001 ===');
});

function createBot() {
    console.log('[BOT] Подключение...');
    bot = mineflayer.createBot(BOT_CONFIG);

    bot.on('spawn', () => {
        console.log(`\x1b[32m[BOT] ЗАШЕЛ НА СЕРВЕР КАК ${bot.username}\x1b[0m`);
        chatLog.push({ type: 'system', text: `Бот ${bot.username} зашел на сервер` });
    });

    bot.on('messagestr', (message) => {
        // Ловим ВСЕ сообщения (чат, системные, команды)
        if (message === lastMessage) return; // Пропускаем дубли
        lastMessage = message;
        
        console.log(`[ЧАТ] ${message}`);
        chatLog.push({ type: 'chat', username: 'Сервер', text: message });
    });

    bot.on('error', (err) => {
        console.log(`\x1b[31m[BOT] Ошибка: ${err.message}\x1b[0m`);
    });

    bot.on('end', () => {
        console.log('[BOT] Отключен. Ждем 5 сек...');
        setTimeout(createBot, 5000);
    });
}

createBot();