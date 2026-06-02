const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

// Initialize the WhatsApp client with local session caching
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        handleSIGINT: false,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

// Generate and display the QR Code in the terminal
client.on('qr', (qr) => {
    console.log('--- SCAN THIS QR CODE WITH YOUR WHATSAPP LINKED DEVICES ---');
    qrcode.generate(qr, { small: true });
});

// Confirm successful authentication
client.on('ready', () => {
    console.log('🚀 WhatsApp Bridge is active and listening for your expenses!');
});

// Intercept incoming messages
client.on('message', async (msg) => {
    // Replace '91XXXXXXXXXX' with your own phone number with country code
    // This ensures your tracker only processes messages sent BY YOU to YOURSELF
    if (msg.fromMe || msg.from.includes('8547992180')) { 
        console.log(`Received text: "${msg.body}"`);
        
        try {
            // Forward the payload directly to your local FastAPI backend
            await axios.post('http://127.0.0.1:8000/webhook/whatsapp', null, {
                params: {
                    Body: msg.body,
                    From: msg.from
                }
            });
            console.log('✅ Successfully forwarded to Python backend.');
        } catch (error) {
            console.error('❌ Failed to forward message to FastAPI backend. Is main.py running?');
        }
    }
});

client.initialize();