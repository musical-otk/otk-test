const CACHE_NAME = 'otk-schedule-v87';
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

// 매번 서버에 '바뀌었나' 물어본다 (cache: 'no-cache' — 안 바뀌었으면 304 로 가볍다).
// 그냥 fetch 하면 GitHub Pages 의 max-age=600 때문에 브라우저가 10분 동안 옛 파일을 내줘서,
// 앱을 완전히 껐다 켜도 업데이트가 안 보였다.
const fresh = req => fetch(req.mode === 'navigate' ? req.url : req, { cache: 'no-cache', credentials: 'same-origin' });

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // HTML · JSON(작품 목록·스케줄·정보만 작품·show-info) — 네트워크 우선, 끊기면 캐시.
  // JSON 을 캐시 우선으로 두면 apps.json · shows/*.json 이 허브 버전을 올리기 전까지 안 바뀐다.
  const isHtml = req.mode === 'navigate' || url.pathname === BASE + '/' || url.pathname.endsWith('.html');
  if (isHtml || url.pathname.endsWith('.json')) {
    event.respondWith(
      fresh(req)
        .then(response => {
          if (response && response.ok && url.origin === location.origin) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(req, clone));
          }
          return response;
        })
        .catch(() => caches.match(req).then(c => c || (isHtml ? caches.match(BASE + '/') : undefined)))
    );
    return;
  }

  // 나머지(아이콘 등) — 캐시 우선
  event.respondWith(
    caches.match(req).then(cached => {
      if (cached) return cached;
      return fetch(req).then(response => {
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(req, clone));
        }
        return response;
      });
    })
  );
});
