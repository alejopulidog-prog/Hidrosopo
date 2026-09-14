/* HidroSopó — Service Worker
 * Permite que la app abra sin señal y muestre la última recomendación conocida.
 * En una finca de Sopó la señal se cae. Sin esto, la app se vuelve una pantalla en blanco.
 */
const CACHE = 'hidrosopo-v2';
const ESTATICOS = [
  './', './index.html', './manifest.json',
  './iconos/icono-192.png', './iconos/icono-512.png',
  'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(ESTATICOS).catch(() => c.addAll(ESTATICOS.slice(0, 5))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = e.request.url;

  // Llamadas a la API: red primero, caché como respaldo.
  // Así el productor ve el dato más reciente que llegó a tener.
  if (url.includes('/api/v1/')) {
    e.respondWith(
      fetch(e.request)
        .then(r => {
          const copia = r.clone();
          caches.open(CACHE).then(c => c.put(e.request, copia));
          return r;
        })
        .catch(() => caches.match(e.request))
    );
    return;
  }

  // La app en sí: red primero, para que una versión nueva entre sin
  // que el productor tenga que desinstalar nada. Si no hay señal,
  // se sirve la copia guardada.
  const esLaApp = e.request.mode === 'navigate' ||
                  url.endsWith('/') || url.includes('index.html');
  if (esLaApp) {
    e.respondWith(
      fetch(e.request)
        .then(r => {
          const copia = r.clone();
          caches.open(CACHE).then(c => c.put(e.request, copia));
          return r;
        })
        .catch(() => caches.match(e.request).then(r => r || caches.match('./index.html')))
    );
    return;
  }

  // Lo demás (íconos, librerías): caché primero, es más rápido.
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});
