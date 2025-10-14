const express = require('express');
const cors = require('cors');
const http = require('http');
const https = require('https');

const app = express();
const PORT = 3000;

// CORS
app.use(cors());
app.use(express.json({ limit: '1mb' }));

// Anti-cache NUCLEAR para todos os arquivos
app.use((req, res, next) => {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(7);
  
  res.set({
    'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0, private',
    'Pragma': 'no-cache',
    'Expires': '0',
    'Last-Modified': new Date().toUTCString(),
    'ETag': `"${timestamp}-${random}"`,
    'X-Timestamp': timestamp.toString(),
    'X-Random': random,
    'X-No-Cache': 'true',
    'X-Cache-Buster': `${timestamp}-${random}`
  });
  
  // Log da requisição
  console.log(`🔄 ${req.method} ${req.url} - ${timestamp}`);
  next();
});

// Servir arquivos estáticos
app.use(express.static('.'));

// Script anti-cache SUPER AGRESSIVO em HTML
app.use((req, res, next) => {
  if (req.url.endsWith('.html') || req.url === '/') {
    const originalSend = res.send;
    res.send = function(data) {
      if (typeof data === 'string' && data.includes('<head>')) {
        const timestamp = Date.now();
        const script = `
          <script>
            // ANTI-CACHE NUCLEAR - DESTRÓI TUDO
            const timestamp = ${timestamp};
            const random = '${Math.random().toString(36).substring(7)}';
            
            console.log('💥 ANTI-CACHE NUCLEAR ATIVADO');
            console.log('🔄 DEV SERVER - Carregado em:', new Date().toISOString());
            console.log('🔄 DEV SERVER - Timestamp:', timestamp);
            console.log('🔄 DEV SERVER - Random:', random);
            console.log('🔄 DEV SERVER - URL:', window.location.href);
            
            // DESTRUIR TODOS OS CACHES
            if ('caches' in window) {
              caches.keys().then(names => {
                names.forEach(name => {
                  caches.delete(name);
                  console.log('💥 Cache DESTRUÍDO:', name);
                });
              });
            }
            
            // DESTRUIR SERVICE WORKERS
            if ('serviceWorker' in navigator) {
              navigator.serviceWorker.getRegistrations().then(registrations => {
                registrations.forEach(registration => {
                  registration.unregister();
                  console.log('💥 Service Worker DESTRUÍDO:', registration);
                });
              });
            }
            
            // LIMPAR TUDO DO LOCALSTORAGE
            Object.keys(localStorage).forEach(key => {
              if (key.includes('cache') || key.includes('timestamp') || key.includes('lastLoad')) {
                localStorage.removeItem(key);
                console.log('💥 localStorage LIMPO:', key);
              }
            });
            
            // LIMPAR SESSIONSTORAGE
            sessionStorage.clear();
            console.log('💥 sessionStorage LIMPO');
            
            // FORÇAR RELOAD SE CACHE DETECTADO
            const lastLoad = localStorage.getItem('lastLoad');
            const now = timestamp;
            if (lastLoad && (now - parseInt(lastLoad)) < 3000) {
              console.log('💥 CACHE DETECTADO - RELOAD FORÇADO!');
              window.location.reload(true);
            }
            localStorage.setItem('lastLoad', now.toString());
            
            // INTERCEPTAR TODAS AS REQUISIÇÕES
            const originalFetch = window.fetch;
            window.fetch = function(...args) {
              const url = new URL(args[0], window.location.origin);
              url.searchParams.set('_t', timestamp);
              url.searchParams.set('_r', random);
              url.searchParams.set('_bust', Date.now());
              args[0] = url.toString();
              console.log('🔄 Fetch interceptado:', args[0]);
              return originalFetch.apply(this, args);
            };
            
            // INTERCEPTAR XMLHttpRequest
            const originalXHR = window.XMLHttpRequest;
            window.XMLHttpRequest = function() {
              const xhr = new originalXHR();
              const originalOpen = xhr.open;
              xhr.open = function(method, url, ...args) {
                const urlObj = new URL(url, window.location.origin);
                urlObj.searchParams.set('_t', timestamp);
                urlObj.searchParams.set('_r', random);
                urlObj.searchParams.set('_bust', Date.now());
                console.log('🔄 XHR interceptado:', urlObj.toString());
                return originalOpen.call(this, method, urlObj.toString(), ...args);
              };
              return xhr;
            };
            
            // ADICIONAR TIMESTAMP A TODAS AS IMAGENS
            document.addEventListener('DOMContentLoaded', function() {
              const images = document.querySelectorAll('img');
              images.forEach(img => {
                const url = new URL(img.src, window.location.origin);
                url.searchParams.set('_t', timestamp);
                url.searchParams.set('_r', random);
                img.src = url.toString();
              });
            });
            
            console.log('💥 ANTI-CACHE NUCLEAR CONFIGURADO');
          </script>`;
        data = data.replace('</head>', script + '</head>');
      }
      originalSend.call(this, data);
    };
  }
  next();
});

// Proxy para chamadas FCGI do dispositivo, contornando CORS do navegador
app.post('/proxy/fcgi', async (req, res) => {
  try {
    const { targetUrl, payload, headers } = req.body || {};
    if (!targetUrl) {
      return res.status(400).json({ error: 'bad_request', message: 'targetUrl é obrigatório' });
    }

    const urlObj = new URL(targetUrl);
    const isHttps = urlObj.protocol === 'https:';
    const lib = isHttps ? https : http;

    const options = {
      method: 'POST',
      hostname: urlObj.hostname,
      port: urlObj.port ? parseInt(urlObj.port, 10) : (isHttps ? 443 : 80),
      path: urlObj.pathname + urlObj.search,
      headers: Object.assign({
        'contentType': 'application/json',
        'Content-Type': 'application/json'
      }, headers || {})
    };

    const reqOut = lib.request(options, (resp) => {
      let data = '';
      resp.on('data', (chunk) => { data += chunk; });
      resp.on('end', () => {
        res.status(resp.statusCode || 200)
          .set('Access-Control-Allow-Origin', '*')
          .type('application/json')
          .send(data);
      });
    });

    reqOut.on('error', (err) => {
      res.status(502).json({ error: 'proxy_error', message: err.message });
    });

    // Timeout curto para evitar travas
    reqOut.setTimeout(3000, () => {
      try { reqOut.destroy(new Error('proxy_timeout')); } catch (_) {}
    });

    reqOut.write(JSON.stringify(payload || {}));
    reqOut.end();
  } catch (e) {
    res.status(500).json({ error: 'proxy_unhandled', message: e.message });
  }
});

app.listen(PORT, () => {
  console.log(`🚀 http://localhost:${PORT}`);
  console.log('💥 ANTI-CACHE NUCLEAR ATIVO - DESTRÓI TUDO');
  console.log('🔄 Nenhum cache será mantido');
  console.log('💥 Todas as requisições são únicas');
});
