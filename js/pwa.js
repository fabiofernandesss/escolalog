// PWA JavaScript - Escola Log
class EscolaLogPWA {
  constructor() {
    this.deferredPrompt = null;
    this.isOnline = navigator.onLine;
    this.installBanner = null;
    this.uiEnabled = true;
    
    this.init();
  }

  init() {
    // Detectar se UI do PWA deve ser desativada na página
    const uiDisabled = (window.disablePwaUi === true)
      || document.body.classList.contains('no-pwa-ui')
      || (document.body.dataset && document.body.dataset.pwaUi === 'off');
    this.uiEnabled = !uiDisabled;

    this.setupServiceWorker();
    if (this.uiEnabled) {
      this.setupInstallBanner();
      this.setupOfflineIndicator();
      this.setupOnlineStatus();
    }
    this.setupKeyboardShortcuts();
    this.setupThemeDetection();
  }

  // Service Worker
  async setupServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/js/sw.js');
        console.log('✅ PWA: Service Worker registrado:', registration);
        
        // Verificar atualizações
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // Forçar ativação imediata e recarregar automaticamente
              try { registration.waiting?.postMessage({ type: 'SKIP_WAITING' }); } catch (_) {}
              try { newWorker.postMessage?.({ type: 'SKIP_WAITING' }); } catch (_) {}
            }
          });
        });
        
        // Recarregar automaticamente quando o novo SW assumir controle
        navigator.serviceWorker.addEventListener('controllerchange', () => {
          console.log('🔄 PWA: Service Worker atualizado, recarregando página...');
          window.location.reload();
        });
        
      } catch (error) {
        console.error('❌ PWA: Erro ao registrar Service Worker:', error);
      }
    }
  }

  showUpdateNotification() {
    if (confirm('Nova versão disponível! Deseja atualizar?')) {
      window.location.reload();
    }
  }

  // Install Banner
  setupInstallBanner() {
    // Detectar se já está instalado
    if (window.matchMedia('(display-mode: standalone)').matches) {
      return;
    }

    // Criar banner de instalação
    const bannerHTML = `
      <div id="install-banner" class="install-banner">
        <div class="install-banner-content">
          <div class="install-banner-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" fill="currentColor"/>
            </svg>
          </div>
          <div class="install-banner-text">
            <div class="install-banner-title">Instalar Escola Log</div>
            <div class="install-banner-description">Instale no seu dispositivo para acesso rápido</div>
          </div>
        </div>
        <div class="install-banner-actions">
          <button id="install-btn" class="install-btn">Instalar</button>
          <button id="install-dismiss" class="install-dismiss">Agora não</button>
        </div>
      </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', bannerHTML);
    this.installBanner = document.getElementById('install-banner');
    
    // Event listeners
    document.getElementById('install-btn').addEventListener('click', () => {
      this.installApp();
    });
    
    document.getElementById('install-dismiss').addEventListener('click', () => {
      this.dismissInstallBanner();
    });
    
    // Mostrar banner após delay (apenas se habilitado)
    setTimeout(() => {
      this.showInstallBanner();
    }, 5000);
  }

  showInstallBanner() {
    if (this.installBanner && !localStorage.getItem('install-banner-dismissed')) {
      this.installBanner.classList.add('show');
    }
  }

  dismissInstallBanner() {
    if (this.installBanner) {
      this.installBanner.classList.remove('show');
      localStorage.setItem('install-banner-dismissed', 'true');
    }
  }

  async installApp() {
    if (this.deferredPrompt) {
      this.deferredPrompt.prompt();
      const { outcome } = await this.deferredPrompt.userChoice;
      console.log('PWA: Instalação:', outcome);
      this.deferredPrompt = null;
      this.dismissInstallBanner();
    }
  }

  // Offline Indicator
  setupOfflineIndicator() {
    const indicatorHTML = `
      <div id="offline-indicator" class="offline-indicator">
        📡 Você está offline. Algumas funcionalidades podem estar limitadas.
      </div>
    `;
    
    document.body.insertAdjacentHTML('afterbegin', indicatorHTML);
    this.offlineIndicator = document.getElementById('offline-indicator');
  }

  showOfflineIndicator() {
    if (this.offlineIndicator) {
      this.offlineIndicator.classList.add('show');
    }
  }

  hideOfflineIndicator() {
    if (this.offlineIndicator) {
      this.offlineIndicator.classList.remove('show');
    }
  }

  // Online Status
  setupOnlineStatus() {
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.hideOfflineIndicator();
      this.showOnlineNotification();
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
      this.showOfflineIndicator();
    });
  }

  showOnlineNotification() {
    // Mostrar notificação de reconexão
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('Escola Log', {
        body: 'Conexão restaurada!',
        icon: '/img/favicon.png'
      });
    }
  }

  // Keyboard Shortcuts
  setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      // Ctrl/Cmd + K para busca
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        this.focusSearch();
      }
      
      // Ctrl/Cmd + N para novo item
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        this.openNewItem();
      }
      
      // Escape para fechar modais
      if (e.key === 'Escape') {
        this.closeModals();
      }
    });
  }

  focusSearch() {
    const searchInput = document.querySelector('input[type="search"], input[placeholder*="buscar"], input[placeholder*="pesquisar"]');
    if (searchInput) {
      searchInput.focus();
    }
  }

  openNewItem() {
    const newButton = document.querySelector('button[onclick*="openModal"], button[onclick*="add"], .btn-primary');
    if (newButton) {
      newButton.click();
    }
  }

  closeModals() {
    const modals = document.querySelectorAll('.modal, .modal-overlay');
    modals.forEach(modal => {
      if (modal.style.display !== 'none') {
        modal.style.display = 'none';
      }
    });
  }

  // Theme Detection
  setupThemeDetection() {
    // Detectar preferência do sistema
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
    
    // Aplicar tema inicial
    this.applyTheme(prefersDark.matches ? 'dark' : 'light');
    
    // Escutar mudanças
    prefersDark.addEventListener('change', (e) => {
      this.applyTheme(e.matches ? 'dark' : 'light');
    });
  }

  applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }

  // Utility Methods
  showLoading() {
    const loadingHTML = `
      <div id="loading-overlay" class="loading-overlay">
        <div class="loading-spinner"></div>
      </div>
    `;
    document.body.insertAdjacentHTML('beforeend', loadingHTML);
  }

  hideLoading() {
    const loading = document.getElementById('loading-overlay');
    if (loading) {
      loading.remove();
    }
  }

  // Notifications
  async requestNotificationPermission() {
    if ('Notification' in window) {
      const permission = await Notification.requestPermission();
      return permission === 'granted';
    }
    return false;
  }

  showNotification(title, body, icon = '/img/favicon.png') {
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(title, {
        body,
        icon,
        badge: '/img/favicon.png',
        tag: 'escola-log'
      });
    }
  }

  // Share API
  async shareContent(data) {
    if (navigator.share) {
      try {
        await navigator.share(data);
      } catch (error) {
        console.log('PWA: Compartilhamento cancelado');
      }
    } else {
      // Fallback para navegadores sem Share API
      this.fallbackShare(data);
    }
  }

  fallbackShare(data) {
    const text = `${data.title}\n${data.text}\n${data.url || ''}`;
    navigator.clipboard.writeText(text).then(() => {
      alert('Link copiado para a área de transferência!');
    });
  }
}

// Inicializar PWA quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
  window.escolaLogPWA = new EscolaLogPWA();
});

// Event listener para beforeinstallprompt
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  window.escolaLogPWA.deferredPrompt = e;
});

// Event listener para appinstalled
window.addEventListener('appinstalled', () => {
  console.log('✅ PWA: App instalado com sucesso!');
  if (window.escolaLogPWA.installBanner) {
    window.escolaLogPWA.installBanner.remove();
  }
});

// Exportar para uso global
window.EscolaLogPWA = EscolaLogPWA;
