const mineflayer = require('mineflayer');
const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');

let currentConfig = {
    host: 'mc.hypemc.pro',
    port: 25565,
    username: 'ТВОЙ_НИК',
    auth: 'offline',
    version: '1.21.11' // Автоопределение
};

let bot = null;
let chatLog = [];
let lastMessage = "";

const app = express();
app.use(cors());
app.use(bodyParser.json());

app.post('/connect', (req, res) => {
    const { host, port, username } = req.body;
    if (host) currentConfig.host = host;
    if (port) currentConfig.port = parseInt(port);
    if (username) currentConfig.username = username;

    if (bot) { try { bot.quit(); } catch(e){} bot = null; }
    chatLog.push({ type: 'system', text: `Переподключение к ${currentConfig.host}...` });
    setTimeout(() => createBot(), 1000);
    res.json({ status: 'ok' });
});

app.post('/reconnect', (req, res) => {
    if (bot) { try { bot.quit(); } catch(e){} bot = null; }
    chatLog.push({ type: 'system', text: `Принудительный перезапуск...` });
    setTimeout(() => createBot(), 1000);
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

app.listen(process.env.PORT || 3001, () => { console.log('=== БОТ ЗАПУЩЕН ==='); });

function createBot() {
    if (bot) { try { bot.quit(); } catch(e){} }
    console.log(`[BOT] Подключение к ${currentConfig.host}:${currentConfig.port}...`);
    
    bot = mineflayer.createBot(currentConfig);
    
    bot.on('spawn', () => {
        console.log(`[BOT] ЗАШЕЛ НА СЕРВЕР как ${bot.username}`);
        chatLog.push({ type: 'system', text: `Бот ${bot.username} зашел на сервер` });
    });
    
    bot.on('messagestr', (message) => {
        if (message === lastMessage) return;
        lastMessage = message;
        chatLog.push({ type: 'chat', username: 'Сервер', text: message });
    });
    
    bot.on('error', (err) => { 
        console.log(`[BOT] Ошибка: ${err.message}`);
        chatLog.push({ type: 'system', text: `Ошибка: ${err.message}` }); 
    });
    
    bot.on('kicked', (reason) => { 
        let reasonStr = typeof reason === 'object' ? JSON.stringify(reason) : reason;
        console.log(`[BOT] КИКНУТ: ${reasonStr}`);
        chatLog.push({ type: 'system', text: `КИКНУТ: ${reasonStr}` }); 
    });
    
    bot.on('end', () => {
        chatLog.push({ type: 'system', text: `Бот отключен. Перезаход через 10 сек...` });
        setTimeout(createBot, 10000);
    });
}

createBot();
