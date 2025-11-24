// Debug скрипт для проверки конфигурации
console.log('🔍 DEBUG: Конфигурация загружена');
console.log('📡 API BASE_URL:', CONFIG?.API?.BASE_URL);
console.log('🔑 Endpoints:', CONFIG?.API?.ENDPOINTS);

// Проверяем корректность URL
if (CONFIG?.API?.BASE_URL) {
    if (CONFIG.API.BASE_URL.includes('production-domain.com')) {
        console.error('❌ ОШИБКА: Обнаружен дублированный домен в BASE_URL!');
        console.error('Неправильный URL:', CONFIG.API.BASE_URL);
        alert('⚠️ Обнаружена ошибка в конфигурации API. Пожалуйста, очистите кеш браузера (Ctrl+Shift+R / Cmd+Shift+R)');
    } else if (CONFIG.API.BASE_URL === 'http://localhost:8880') {
        console.log('✅ BASE_URL корректен:', CONFIG.API.BASE_URL);
    } else {
        console.warn('⚠️ BASE_URL не соответствует ожидаемому продакшн URL:', CONFIG.API.BASE_URL);
    }
}

// Выводим полную информацию для отладки
window.DEBUG_CONFIG_INFO = {
    timestamp: new Date().toISOString(),
    baseUrl: CONFIG?.API?.BASE_URL,
    cacheVersion: window.CACHE_VERSION
}; 