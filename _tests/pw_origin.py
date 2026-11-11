# mu:di 허브 — 다른 주소(도메인)에서 열어도 허브·앱이 그 주소 안에서만 도는지. 실행: python _tests/pw_origin.py
# 먼저 주소가 다른 두 번째 로컬 서버: (D:\workspace 에서) python -m http.server 8766 --bind 127.0.0.2
import asyncio
R = []
def check(n, ok, info=''):
    R.append(ok); print(('PASS ' if ok else 'FAIL ') + n + (f'  [{info}]' if info else ''))
from playwright.async_api import async_playwright
B='http://127.0.0.2:8766'
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(channel='chrome'); ctx=await b.new_context(); pg=await ctx.new_page()
        errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
        out=[]; pg.on('request', lambda r: out.append(r.url) if 'musical-otk.github.io' in r.url else None)
        await pg.goto(B+'/otk-test/'); await pg.wait_for_timeout(1000)
        # 옛 주소로 저장된 앱(백업 복원한 상황)
        await pg.evaluate("""localStorage.setItem(APPS_KEY, JSON.stringify([{id:'app_ikkisup',name:'이끼숲',icon:'🌿',color:'#1A6B72',kind:'app',scheduleUrl:'https://musical-otk.github.io/ikkisup2026/schedule.json',appUrl:'https://musical-otk.github.io/ikkisup2026/',recordsKey:'ikkisup_records',deepLink:true}]));
          localStorage.setItem('ikkisup_records', JSON.stringify([{id:'r1',date:'2026-12-09',time:'20:00',status:'관람'}]))""")
        await pg.reload(); await pg.wait_for_timeout(4000)
        check('사이트 주소 = 지금 열린 주소', await pg.evaluate("SITE") == B)
        check('옛 주소로 저장된 앱도 지금 주소로 읽음', all(u.startswith(B) for u in await pg.evaluate("getApps().flatMap(a=>[a.scheduleUrl,a.appUrl])")))
        check('작품 목록 주소도 지금 주소', all(u.startswith(B) for u in await pg.evaluate("PRESET_APPS.map(p=>p.appUrl)")))
        check('앱 기록 읽음', await pg.evaluate("(getAttended()['2026-12-09']||[]).length") == 1)
        check('앱 스케줄 읽음', await pg.evaluate("(schedules['app_ikkisup']||[]).length") > 0)
        await pg.evaluate("switchView('app_ikkisup')"); await pg.wait_for_timeout(2500)
        check('앱 화면도 지금 주소에서 열림', (await pg.evaluate("(document.getElementById('frame-app_ikkisup')||{}).src")).startswith(B))
        check('옛 주소로 나가는 요청 0', not out, out[:3])
        check('페이지 오류 없음', not errs, '; '.join(errs)[:200])
        print('
SUMMARY', sum(R), '/', len(R))
        await b.close()
asyncio.run(main())
