// service-worker.js

// Versión de la caché. Cámbiala para forzar la actualización del Service Worker y la caché.
const CACHE_NAME = 'la-tribu-pwa-cache-v1.0.5';

// Archivos esenciales para cachear durante la instalación.
const urlsToCache = [
    '/',
    '/offline.html', // Página para mostrar cuando no hay conexión
    '/static/manifest.json', // El manifest de la PWA
    '/static/css/main.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css',
    'https://cdn.jsdelivr.net/npm/@popperjs/core@2.11.7/dist/umd/popper.min.js',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.min.js',
    // Asegúrate de que las rutas a tus imágenes y otros assets sean correctas.
    '/static/uploads/icons/icon-192x192.jpg',
    '/static/uploads/icons/icon-512x512.jpg'
];

// Evento 'install': Se dispara cuando el Service Worker se instala.
self.addEventListener('install', (event) => {
    console.log('[Service Worker] Instalando...');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[Service Worker] Cacheando archivos esenciales');
                return cache.addAll(urlsToCache);
            })
            .catch((error) => {
                console.error('[Service Worker] Falló la caché de archivos esenciales:', error);
            })
    );
    // Forzar al nuevo Service Worker a activarse inmediatamente.
    self.skipWaiting();
});

// Evento 'activate': Se dispara cuando el Service Worker se activa.
self.addEventListener('activate', (event) => {
    console.log('[Service Worker] Activando...');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    // Elimina las cachés antiguas que no coincidan con la versión actual.
                    if (cacheName !== CACHE_NAME) {
                        console.log('[Service Worker] Eliminando caché antigua:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    // Toma el control de las páginas abiertas para que el Service Worker funcione de inmediato.
    return self.clients.claim();
});

// Evento 'fetch': Intercepta todas las solicitudes de red.
self.addEventListener('fetch', (event) => {
    // Solo procesa solicitudes GET.
    if (event.request.method !== 'GET') {
        return;
    }

    // Estrategia: Cache First, then Network, with Offline Fallback for navigation.
    event.respondWith(
        caches.match(event.request)
            .then((cachedResponse) => {
                // Si el recurso está en la caché, lo servimos desde allí.
                if (cachedResponse) {
                    // Opcional: Actualizar la caché en segundo plano (stale-while-revalidate)
                    // fetch(event.request).then(networkResponse => {
                    //     caches.open(CACHE_NAME).then(cache => cache.put(event.request, networkResponse));
                    // });
                    return cachedResponse;
                }

                // Si no está en caché, vamos a la red.
                return fetch(event.request)
                    .then((networkResponse) => {
                        // Si la respuesta es válida, la guardamos en caché para futuras solicitudes.
                        if (networkResponse && networkResponse.status === 200) {
                            const responseToCache = networkResponse.clone();
                            caches.open(CACHE_NAME)
                                .then((cache) => {
                                    cache.put(event.request, responseToCache);
                                });
                        }
                        return networkResponse;
                    });
            })
            .catch(() => {
                // Si todo falla (sin caché y sin red), mostramos la página offline.
                // Esto es crucial para las solicitudes de navegación.
                if (event.request.mode === 'navigate') {
                    return caches.match('/offline.html');
                }
                // Para otros tipos de solicitudes, puedes devolver una respuesta de error genérica.
                return new Response("Contenido no disponible sin conexión.", {
                    status: 404,
                    statusText: "Offline"
                });
            })
    );
});
