// Service Worker para Escola Log PWA
const CACHE_NAME = 'escola-log-v1.1.0';
const STATIC_CACHE = 'escola-log-static-v1.1.0';
const DYNAMIC_CACHE = 'escola-log-dynamic-v1.1.0';

// Arquivos estáticos para cache
const STATIC_FILES = [
  '/manifest.json',
  '/img/favicon.png',
  '/img/metatag.png',
  '/img/logo-horizonal.png',
  '/img/logo-horizonal-branca.png',
  '/img/banner.jpg',
  '/img/banner-02.png'
];

// Instalação do Service Worker
self.addEventListener('install', (event) => {
  console.log('🔧 Service Worker: Instalando...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('📦 Service Worker: Cacheando arquivos estáticos...');
        return cache.addAll(STATIC_FILES);
      })
      .then(() => {
        console.log('✅ Service Worker: Instalação concluída');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('❌ Service Worker: Erro na instalação:', error);
      })
  );
});

// Ativação do Service Worker
self.addEventListener('activate', (event) => {
  console.log('🚀 Service Worker: Ativando...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
              console.log('🗑️ Service Worker: Removendo cache antigo:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('✅ Service Worker: Ativação concluída');
        return self.clients.claim();
      })
  );
});

// Interceptação de requisições
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  if (request.method === 'GET') {
    // HTML e rota raiz: Network First para evitar versões antigas
    if (url.pathname === '/' || url.pathname.endsWith('.html')) {
      event.respondWith(networkFirst(request));
    }
    // Arquivos estáticos: Cache First
    else if (STATIC_FILES.includes(url.pathname) || 
             url.pathname.endsWith('.css') ||
             url.pathname.endsWith('.js') ||
             url.pathname.endsWith('.png') ||
             url.pathname.endsWith('.jpg') ||
             url.pathname.endsWith('.jpeg') ||
             url.pathname.endsWith('.gif') ||
             url.pathname.endsWith('.svg')) {
      
      event.respondWith(cacheFirst(request));
    }
    // APIs: Network First
    else if (url.pathname.includes('/rest/v1/') || 
             url.pathname.includes('/functions/v1/') ||
             url.pathname.includes('/storage/v1/')) {
      
      event.respondWith(networkFirst(request));
    }
    // Outros recursos: Stale While Revalidate
    else {
      event.respondWith(staleWhileRevalidate(request));
    }
  }
});

// Estratégia Cache First
async function cacheFirst(request) {
  try {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      console.log('📦 SW: Servindo do cache:', request.url);
      return cachedResponse;
    }
    
    const networkResponse = await fetch(request);
    if (networkResponse.ok && request.url.startsWith('http')) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.error('❌ SW: Erro no cache first:', error);
    return new Response('Recurso não disponível offline', { status: 503 });
  }
}

// Estratégia Network First
async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok && request.url.startsWith('http')) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log('🌐 SW: Rede indisponível, tentando cache:', request.url);
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    return new Response('Recurso não disponível offline', { status: 503 });
  }
}

// Estratégia Stale While Revalidate
async function staleWhileRevalidate(request) {
  const cache = await caches.open(DYNAMIC_CACHE);
  const cachedResponse = await cache.match(request);
  
  const fetchPromise = fetch(request).then((networkResponse) => {
    if (networkResponse.ok && request.url.startsWith('http')) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  }).catch(() => cachedResponse);
  
  return cachedResponse || fetchPromise;
}

// Sincronização em background
self.addEventListener('sync', (event) => {
  console.log('🔄 Service Worker: Sincronização em background');
  
  if (event.tag === 'background-sync') {
    event.waitUntil(doBackgroundSync());
  }
});

async function doBackgroundSync() {
  try {
    // Aqui você pode implementar sincronização de dados offline
    console.log('🔄 SW: Executando sincronização em background');
  } catch (error) {
    console.error('❌ SW: Erro na sincronização:', error);
  }
}

// Notificações push
self.addEventListener('push', (event) => {
  console.log('📱 Service Worker: Push notification recebida');
  
  const options = {
    body: event.data ? event.data.text() : 'Nova notificação da Escola Log',
    icon: '/img/favicon.png',
    badge: '/img/favicon.png',
    vibrate: [200, 100, 200],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'open',
        title: 'Abrir',
        icon: '/img/favicon.png'
      },
      {
        action: 'close',
        title: 'Fechar',
        icon: '/img/favicon.png'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification('Escola Log', options)
  );
});

// Clique em notificação
self.addEventListener('notificationclick', (event) => {
  console.log('👆 Service Worker: Notificação clicada');
  
  event.notification.close();
  
  if (event.action === 'open') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Mensagens do cliente
self.addEventListener('message', (event) => {
  console.log('💬 Service Worker: Mensagem recebida:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
