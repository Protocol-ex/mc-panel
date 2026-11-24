const mineflayer = require('mineflayer');
const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');

let currentConfig = {
    host: 'mc.hypemc.pro', // Если сервер локальный (на вашем ПК), тут должно быть 127.0.0.1 или IP сервера
    port: 25565,
    username: 'MechtaAdm',
    auth: 'offline',
    version: '1.21.11'
};

let bot = null;
let chatLog = [];
let lastMessage = "";
let reconnectTimeout = null;
let afkInterval = null;

const app = express();
app.use(cors());
app.use(bodyParser.json());

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
    try { bot.chat(command); res.json({ status: 'ok' }); } 
    catch (e) { res.status(500).json({ error: e.message }); }
});

app.get('/chat', (req, res) => { res.json(chatLog.slice(-100)); });
app.get('/health', (req, res) => { res.send('OK'); });
app.listen(process.env.PORT || 3001, () => { console.log('=== СЕРВЕР БОТА ЗАПУЩЕН ==='); });

function startBot() {
    if (reconnectTimeout) clearTimeout(reconnectTimeout);
    if (afkInterval) clearInterval(afkInterval);
    if (bot) { try { bot.quit(); } catch(e){} bot = null; }

    console.log(`[BOT] Подключение к ${currentConfig.host}:${currentConfig.port}...`);
    chatLog.push({ type: 'system', text: `Подключение к ${currentConfig.host}...` });

    try {
        bot = mineflayer.createBot({
            ...currentConfig,
            physicsEnabled: false // Отключаем физику при старте
        });
    } catch (err) {
        console.log(`[BOT] Ошибка создания: ${err.message}`);
        return;
    }

    bot.on('spawn', () => {
        console.log(`[BOT] УСПЕШНО ЗАШЕЛ КАК ${bot.username}`);
        chatLog.push({ type: 'system', text: `Бот ${bot.username} успешно зашел на сервер` });

        // Включаем физику через 5 секунд, когда бот полностью загрузится
        setTimeout(() => {
            if (bot && bot.physicsEnabled !== undefined) {
                bot.physicsEnabled = true;
                console.log(`[BOT] Физика включена.`);
            }
        }, 5000);

        // Легкая имитация АФК (прыжок раз в 15 секунд)
        afkInterval = setInterval(() => {
            if (bot && bot.entity) {
                bot.setControlState('jump', true);
                setTimeout(() => { if(bot) bot.setControlState('jump', false); }, 500);
            }
        }, 15000); 
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
        chatLog.push({ type: 'system', text: `Бот кикнут: ${reasonStr}` });
    });

    bot.on('end', () => {
        console.log(`[BOT] Отключен от сервера.`);
        chatLog.push({ type: 'system', text: `Бот отключен. Перезаход через 15 секунд...` });
        if (afkInterval) clearInterval(afkInterval);
        
        reconnectTimeout = setTimeout(() => {
            startBot();
        }, 15000);
    });
}

startBot();
