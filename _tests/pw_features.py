# mu:di 허브 — 요청별 기능 검사 (2026-11-10~11 요청분). 실행: python _tests/pw_features.py <스크린샷 폴더>
# 로컬 서버가 먼저 떠 있어야 한다: D:\workspace 에서 python -m http.server 8765 --bind 127.0.0.1
import sys, os, asyncio, json
from playwright.async_api import async_playwright
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
BASE = 'http://127.0.0.1:8765/otk-test/'
R = []
def check(name, ok, info=''):
    R.append((name, bool(ok), info)); print(('PASS ' if ok else 'FAIL ') + name + (f'  [{info}]' if info else ''))


async def page(b, touch=False):
    ctx = await b.new_context(viewport={'width': 390, 'height': 844}, has_touch=touch, is_mobile=touch)
    pg = await ctx.new_page()
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
    await pg.goto(BASE); await pg.wait_for_timeout(1500)
    return pg, errs


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel='chrome')
        pg, errs = await page(b, touch=True)
        ev = pg.evaluate
        lab = lambda: ev("document.getElementById('cal-month-label').textContent")

        # ── 달력 ──
        check('달력 버튼 순서 [전체 회차][내 기록]', await ev(
            "[...document.querySelectorAll('.cal-seg > .seg-btn')].map(b=>b.id).join(',')") == 'seg-all,seg-mine,seg-filter')
        async def swipe(id, x1, x2, y1=500, y2=500):
            await ev("""([id,x1,x2,y1,y2])=>{const el=document.getElementById(id);const mk=(x,y)=>new Touch({identifier:1,target:el,clientX:x,clientY:y});
              el.dispatchEvent(new TouchEvent('touchstart',{touches:[mk(x1,y1)],changedTouches:[mk(x1,y1)],bubbles:true}));
              el.dispatchEvent(new TouchEvent('touchend',{touches:[],changedTouches:[mk(x2,y2)],bubbles:true}));}""", [id, x1, x2, y1, y2])
            await pg.wait_for_timeout(300)
        m0 = await lab(); await swipe('cal-grid', 300, 100); m1 = await lab(); await swipe('cal-grid', 100, 300)
        check('스와이프 왼쪽 → 다음 달, 오른쪽 → 돌아옴', m1 != m0 and await lab() == m0, f'{m0}→{m1}')
        await swipe('cal-grid', 200, 230, 300, 600)
        check('세로로 밀면 안 넘어감', await lab() == m0)
        await ev("setCalView('week')"); await pg.wait_for_timeout(200); w0 = await lab(); await swipe('cal-week', 300, 100)
        check('주간 스와이프는 한 주', await lab() != w0); await ev("setCalView('month')")
        await pg.click('.cal-nav .nav-btn >> nth=1'); await pg.wait_for_timeout(60)
        check('‹ › 누르면 미끄러지는 효과', await ev("getComputedStyle(document.getElementById('cal-grid')).transform") != 'none')
        check('미끄러질 때 가로 스크롤 안 생김', await ev("document.documentElement.scrollWidth") <= 390)
        await pg.wait_for_timeout(400); await pg.click('.cal-nav .nav-btn >> nth=0')
        check('눈금 안내 문구', '날짜를 눌러 확인해 주세요' in await ev("document.documentElement.innerHTML"))

        # ── 사진만 있는 회차 ──
        await ev("heartWork('show_socrates2026')"); await pg.wait_for_timeout(2500)
        await ev("""(()=>{const s=schedules['show_socrates2026'].find(r=>r.date>=todayStr);window._t=s;
          const n=getNotes();n[noteKeyFor('show_socrates2026',s.date,s)]={memo:'',photoIds:[999999]};saveNotes(n);
          currentYear=+s.date.slice(0,4);currentMonth=+s.date.slice(5,7)-1;renderCalendar();})()""")
        check('사진만 있는 회차는 칠하지 않음·사진 점 없음', await ev(
            "!document.querySelector('#cal-grid .sess-card-pic') && ![...document.querySelectorAll('#cal-grid .sess-card')].some(c=>c.textContent.includes(sessName(getApps().find(a=>a.id==='show_socrates2026'),_t)) && c.textContent.includes(fmtTime(_t.time)))"))

        # ── 날짜 상세 이벤트 · 이벤트 설명 ──
        await ev("openDay('2026-11-11')"); await pg.wait_for_timeout(500)
        if await ev("!!document.querySelector('#ov-detail .ev-tap')"):
            await pg.click('#ov-detail .ev-tap >> nth=0'); await pg.wait_for_timeout(300)
            check('날짜 상세 이벤트 → 이벤트 창', await ev("document.getElementById('ov-ev').classList.contains('open')"))
            await ev("closeEvSheet();closeOverlays()")
        else:
            check('날짜 상세 이벤트 → 이벤트 창 (11/11 소크라테스 이벤트 필요)', False, '이벤트 없음')
        d = await ev("evDescLines('적립. 분할 불가(단 새 카드 가능). 운영 시간 내에만 — 시작 전 / 종료 후. M4. 노래 · <이끼숲>')")
        check('이벤트 설명 줄바꿈(문장 끝·—·/), 숫자 뒤 점은 그대로', d.count('\n') == 5 and 'M4. 노래' in d, d.replace('\n', '⏎'))
        check('설명 속 꺾쇠가 보이게', '&lt;이끼숲&gt;' in d)
        n = await ev("getNotes()"); await ev("unheartWork('show_socrates2026')")

        # ── 찾기 ──
        await ev("openSearch()"); await pg.wait_for_timeout(4000); await ev("renderSearch()"); await pg.wait_for_timeout(300)
        secs = await pg.eval_on_selector_all('#srch-results .flt-sec', 'e=>e.map(x=>x.textContent)')
        check('찾기 목록: 공연 중 / 공연 예정', any(s.startswith('공연 중') for s in secs) and any(s.startswith('공연 예정') for s in secs), secs)
        await ev("pickSearch('work','show_socrates2026')"); await pg.wait_for_timeout(400)
        cnt = lambda: ev("document.querySelectorAll('.srch-sess .srch-row').length")
        c0 = await cnt(); await pg.click('.srch-past-btns button >> nth=0'); await pg.wait_for_timeout(200); c1 = await cnt()
        await pg.click('.srch-past-btns button >> nth=0'); await pg.wait_for_timeout(200); c2 = await cnt()
        check('지난 회차 10개씩 펼치기', c1 == c0 + 10 and c2 == c1 + 10, f'{c0}→{c1}→{c2}')
        await pg.click('.srch-past-btns button:has-text("접기")'); await pg.wait_for_timeout(200)
        check('지난 회차 접기', await cnt() == c0)
        await ev("backSearch ? backSearch() : 0"); await ev("""(()=>{const g=getAttended;getAttended=()=>{const a={...g()};
          a['2099-01-01']=Array.from({length:12},()=>({appId:'show_turing2026',date:'2099-01-01',time:'20:00'}));return a;}})()""")
        await ev("document.getElementById('srch-q').value='';_srchSel=null;renderSearch()"); await pg.wait_for_timeout(300)
        check('예매 수 오른쪽 정렬·두 칸 폭', await ev(
            "(()=>{const e=document.querySelector('.flt-hit-bk .n');return !!e && getComputedStyle(e).minWidth!=='0px' && getComputedStyle(e.parentNode).marginLeft!=='0px'})()"))
        await ev("closeSearch()")

        # ── 찾기 작품 상세 '내 달력' ──
        await ev("openSearch()"); await pg.wait_for_timeout(1500)
        await ev("""(()=>{const g=getAttended;window._g=g;const s=rowsOf(catalog('all').works.find(w=>w.id==='show_socrates2026')).find(r=>r.date>=todayStr);
          window._ds=s.date;getAttended=()=>{const a={...g()};a[s.date]=[{appId:'show_turing2026',date:s.date,time:'20:00'}];return a;}})()""")
        await ev("pickSearch('work','show_socrates2026')"); await pg.wait_for_timeout(300)
        check('내 달력: 처음엔 접힘', await ev("!document.querySelector('.mycal') && !!document.querySelector('.mycal-btn')"))
        await pg.click('.mycal-btn'); await pg.wait_for_timeout(300)
        check('내 달력: 회차 없는 날은 흐리게(테두리 없음)', await ev("document.querySelectorAll('.mycal .mc-day.off').length>0 && !document.querySelector('.mycal .mc-day.on')"))
        check('내 달력: 내 일정 있는 날에 작품 아이콘', await ev("[...document.querySelectorAll('.mycal .mc-day b')].some(b=>b.textContent.trim())"))
        await ev("myCalPick(_ds)"); await pg.wait_for_timeout(300)
        await pg.screenshot(path=os.path.join(OUT, 'mycal.png'))
        check('내 달력: 날짜 누르면 그날 정리(내 일정·회차 캐스팅)', await ev("!!document.querySelector('.mc-day-box .mc-mine') && !!document.querySelector('.mc-day-box .mc-sess .mc-cast')"))
        await pg.click('.mc-go'); await pg.wait_for_timeout(500)
        check('내 달력: 목록에서 보기 → 그날 회차로', await ev("!!document.querySelector('.srch-row.flash')"))
        await ev("""(()=>{const w=catalog('all').works.find(x=>x.id==='show_socrates2026'),rows=rowsOf(w);
          const day=rows.filter(r=>r.date===_ds).flatMap(r=>getActorFields(r).map(k=>r[k]));
          const n=rows.flatMap(r=>getActorFields(r).map(k=>r[k])).find(x=>x&&!day.includes(x));_srchActors.add(n);renderSearch();})()""")
        check('내 달력: 배우 필터면 그날 회차 숨김 수 표시', await ev("/배우 필터로 숨긴 회차/.test(document.querySelector('.mc-day-box').textContent)"))
        await ev("_srchActors.clear();renderSearch()")
        await ev("pickSearch('work','show_turing2026')"); await pg.wait_for_timeout(300)
        check('내 달력: 다른 작품에서도 펼친 채', await ev("!!document.querySelector('.mycal')"))
        await ev("toggleMyCal(); getAttended=_g; closeSearch()")

        # ── 관심함 ON/OFF ──
        await ev("heartWork('show_turing2026')"); await pg.wait_for_timeout(2000)
        await ev("openHearts()"); await pg.wait_for_timeout(400)
        btn = '.hp-vis >> nth=0'
        t0 = await pg.inner_text(btn); await pg.click(btn); await pg.wait_for_timeout(200)
        t1 = await pg.inner_text(btn); await pg.click(btn); await pg.wait_for_timeout(200); t2 = await pg.inner_text(btn)
        check('관심함 ON/OFF 토글', (t0, t1, t2) == ('ON', 'OFF', 'ON'), f'{t0} {t1} {t2}')
        check('같은 값이면 자동으로 되돌림(저장 없음)', await ev("Object.keys(getVisibility()).length") == 0)
        check('막공 1주 뒤 자동 OFF', await ev("""(()=>{const o=schedules['show_turing2026'];schedules['show_turing2026']=[{date:'2000-01-01',time:'20:00'}];
          const r=autoHidden('show_turing2026');schedules['show_turing2026']=o;return r})()"""))
        await ev("closeHearts();unheartWork('show_turing2026')")
        check('페이지 오류 없음 (1)', not errs, '; '.join(errs)[:200])

        # ── 기타 ──
        pg2, errs2 = await page(b)
        e2 = pg2.evaluate
        for recs, want, label in (([], ['none', False], '기타 정리: 기록 없으면 뺌'),
                                   ([{'date': '2026-12-31', 'time': '20:00', 'showId': 'x'}], [True, False], '기타 정리: 기록 있으면 ♥ 없이 예매 회차만')):
            await e2("""r=>{localStorage.removeItem(HUB_NS+'extra_tidied');addExtraApp();saveExtraRecords(r);}""", recs)
            await pg2.reload(); await pg2.wait_for_timeout(2500)
            got = await e2("[getApps().find(a=>a.id===EXTRA_ID)?.viaActor ?? 'none', getHearts().works.includes(EXTRA_ID)]")
            check(label, got == want, got)
            await e2("saveExtraRecords([]);saveApps(getApps().filter(a=>a.id!==EXTRA_ID))")
        await e2("""()=>{localStorage.setItem(HUB_NS+'extra_tidied','1');const a=getApps();a.push({...EXTRA_APP,viaActor:true});saveApps(a);
          saveExtraRecords([{date:'2026-12-18',time:'20:00',show:'H.WINTER',showId:'hwinter2026',seat:'B열 3번'}]);
          const n=getNotes();n[noteKeyFor(EXTRA_ID,'2026-12-18',{time:'20:00',_showId:'hwinter2026'})]={memo:'메모',photoIds:[]};saveNotes(n);}""")
        await pg2.reload(); await pg2.wait_for_timeout(6000)
        got = await e2("""({extra:extraRecords().length, show:extraRecords(recKeyOf('show_hwinter2026')).map(r=>r.seat),
           note:(getNotes()[noteKeyFor('show_hwinter2026','2026-12-18',{time:'20:00'})]||{}).memo, hasExtra:getApps().some(a=>a.id===EXTRA_ID)})""")
        check('기타 → 작품으로 옮긴 공연(H.WINTER): 예매·좌석·메모가 따라옴', got == {'extra': 0, 'show': ['B열 3번'], 'note': '메모', 'hasExtra': False}, got)
        await e2("localStorage.clear()")
        check('페이지 오류 없음 (2)', not errs2, '; '.join(errs2)[:200])

        print('\nSUMMARY', sum(1 for r in R if r[1]), '/', len(R))
        await b.close()

asyncio.run(main())
