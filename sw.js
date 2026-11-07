const CACHE_NAME = 'otk-schedule-v68';
// 테스트 사본(/otk-test/)에서도 그대로 돌게 sw.js 위치에서 구한다
const BASE = self.location.pathname.replace(/\/sw\.js$/, '');

const PRECACHE_URLS = [
  BASE + '/',
  BASE + '/index.html',
  BASE + '/manifest.json',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // schedule.json — 네트워크 우선 (최신 스케줄), 실패 시 캐시
  if (url.pathname.endsWith('schedule.json')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // HTML — 네트워크 우선, 실패하면 캐시.
  // 캐시 우선으로 두면 CACHE_NAME 을 손으로 올리기 전까지 새 버전이 영원히 안 뜬다.
  // 앱 코드가 통째로 index.html 한 장에 있어서 특히 티가 크다.
  const isHtml = event.request.mode === 'navigate' ||
                 url.pathname === BASE + '/' ||
                 url.pathname.endsWith('.html');
  if (isHtml) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          return response;
        })
        .catch(() => caches.match(event.request).then(c => c || caches.match(BASE + '/')))
    );
    return;
  }

  // 나머지 — 캐시 우선
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(response => {
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      });
    })
  );
});
