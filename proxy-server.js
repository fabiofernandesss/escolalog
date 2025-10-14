const express = require('express');
const cors = require('cors');
const fetch = require('node-fetch');

const app = express();
const PORT = 3001;

// Middleware
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.raw({ type: 'application/octet-stream', limit: '50mb' }));

// Proxy endpoint para requisições FCGI
app.post('/proxy/fcgi', async (req, res) => {
    try {
        const { url, method, headers, body } = req.body;
        
        console.log(`🔄 Proxy: ${method} ${url}`);
        
        let requestBody;
        
        // Se o body é um array (ArrayBuffer convertido), converter de volta
        if (Array.isArray(body)) {
            requestBody = Buffer.from(body);
        } else if (typeof body === 'string') {
            requestBody = body;
        } else {
            requestBody = JSON.stringify(body);
        }
        
        const response = await fetch(url, {
            method: method || 'GET',
            headers: headers || {},
            body: method !== 'GET' ? requestBody : undefined,
            timeout: 15000
        });
        
        const responseData = await response.json();
        
        console.log(`✅ Proxy: ${response.status} ${response.statusText}`);
        
        res.status(response.status).json(responseData);
        
    } catch (error) {
        console.error('❌ Erro no proxy:', error.message);
        res.status(500).json({ 
            error: 'Erro no proxy', 
            message: error.message 
        });
    }
});

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'ok', message: 'Proxy server is running' });
});

app.listen(PORT, () => {
    console.log(`🚀 Servidor proxy rodando em http://localhost:${PORT}`);
    console.log(`📡 Endpoint: http://localhost:${PORT}/proxy/fcgi`);
    console.log(`🏥 Health check: http://localhost:${PORT}/health`);
});