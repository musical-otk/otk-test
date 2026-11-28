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
            "[...document.querySelectorAll('.cal-seg .seg-mode .seg-btn, .cal-seg > .seg-btn')].map(b=>b.id).join(',')") == 'seg-all,seg-mine,seg-filter')
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
        sh = await ev("['재관람카드 스페셜 더블 적립','2차 스페셜 커튼콜 위크','럭키드로우 & 막공 무대인사','하이터치 배웅회','관객과의 대화','쿠폰팩 증정 위크','멜로디카드 증정','2차 페어 폴라로이드 증정 데이','프로필 폴라로이드 데이','페어 폴라데이','전관 회차','셀카 포토카드 증정 위크'].map(evShort)")
        check('이벤트 줄임말(내 달력용)', sh == ['덥적', '2차 스콜', '럭드 & 막공 무인', '배웅회', '관대', '쿠폰팩', '멜로디카드', '2차 페폴데', '프로필 폴데', '페폴데', '전관', '셀포'], sh)
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
        check('내 달력: 날짜 누르면 그날 정리(내 일정·회차 캐스팅)', await ev("!!document.querySelector('.mc-day-box .mc-lbl') && !!document.querySelector('.mc-day-box .mc-sess .mc-cast')"))
        await pg.click('.mc-sess.mine >> nth=0'); await pg.wait_for_timeout(400)
        check('내 달력: 내 일정 줄 누르면 그 회차만(날짜 상세 아님)', await ev("document.getElementById('ov-ev').classList.contains('open') && !document.getElementById('ov-detail').classList.contains('open')"))
        await ev("closeEvSheet()")
        await pg.click('.mc-go'); await pg.wait_for_timeout(500)
        check('내 달력: 목록에서 보기 → 그날 회차로', await ev("!!document.querySelector('.srch-row.flash')"))
        await ev("""(()=>{const w=catalog('all').works.find(x=>x.id==='show_socrates2026'),rows=rowsOf(w);
          const day=rows.filter(r=>r.date===_ds).flatMap(r=>getActorFields(r).map(k=>r[k]));
          const n=rows.flatMap(r=>getActorFields(r).map(k=>r[k])).find(x=>x&&!day.includes(x));_srchActors.add(n);renderSearch();})()""")
        check('내 달력: 배우 필터에 안 맞는 그날 회차는 연하게 같이', await ev("document.querySelectorAll('.mc-day-box .mc-sess.faded').length>0 && !/숨긴 회차/.test(document.querySelector('.mc-day-box').textContent)"))
        check('내 달력: 회차 칸 이름이 이 작품 대신 작품 이름', await ev("[...document.querySelectorAll('.mc-day-box .mc-lbl')].some(l=>l.textContent.includes(catalog('all').works.find(x=>x.id==='show_socrates2026').name))"))
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
        check('막공 3일 뒤 자동 OFF (3일째까지는 보임)', await ev("""(()=>{const o=schedules['show_turing2026'];const ago=n=>{const d=new Date(todayStr+'T00:00:00');d.setDate(d.getDate()-n);return ymd(d)};
          const at=n=>{schedules['show_turing2026']=[{date:ago(n),time:'20:00'}];return autoHidden('show_turing2026')};
          const r=[at(3),at(4)];schedules['show_turing2026']=o;return r[0]===false&&r[1]===true})()"""))
        await ev("closeHearts();unheartWork('show_turing2026')")
        # ── 공연 정보 새로 받기: 새 회차가 많으면 기간으로 ──
        await ev("""localStorage.setItem(DIFF_KEY, JSON.stringify({at:Date.now(), works:[{id:'x',name:'가상',icon:'🎭',
          added:Array.from({length:12},(_,i)=>'2026-12-'+String(10+i).padStart(2,'0')+' 20:00'),gone:[],cast:[],ev:[]}]}));openSettings();""")
        await pg.wait_for_timeout(300)
        check('새 회차가 많으면 기간으로(12/10 ~ 12/21 · 12회차)', '12/10 ~ 12/21 · 12회차' in await ev("document.getElementById('set-diff').innerText"))
        await ev("localStorage.removeItem(DIFF_KEY);closeSettings()")

        # ── 내 일정: 공연/기타, 아이콘, 기간 ──
        await ev("openCustomForm('2026-12-02')"); await pg.wait_for_timeout(300)
        await pg.click('#cf-k-etc'); await pg.fill('#cf-name', '출장')
        await pg.click('#cf-icons button >> nth=0')
        check('내 일정: 기본은 하루(끝나는 날 칸 숨김)', await ev("document.getElementById('cf-end-wrap').hidden"))
        await pg.click('#cf-multi'); await pg.fill('#cf-end', '2026-12-04')
        await pg.screenshot(path=os.path.join(OUT, 'custom_form.png'))
        await ev("saveCustomEvent()"); await pg.wait_for_timeout(300)
        await ev("openCustomForm('2026-12-05')"); await pg.wait_for_timeout(300)
        await pg.fill('#cf-name', '지방 공연'); await pg.fill('#cf-seat-zone', 'C'); await pg.fill('#cf-seat-num', '7')
        await ev("saveCustomEvent()"); await pg.wait_for_timeout(300)
        got = await ev("getCustom().slice(-2).map(e=>[e.kind,e.icon||'',e.endDate||'',e.seatZone||'',e.seatNumber??''])")
        check('내 일정: 기타(아이콘·기간)와 공연(좌석) 저장', got == [['etc', '✈️', '2026-12-04', '', ''], ['show', '', '', 'C', 7]], got)
        check('내 일정: 기간 일정은 사이 날마다 걸림', await ev("['2026-12-02','2026-12-03','2026-12-04'].every(d=>customOn(getCustom(),d).some(e=>e.name==='출장')) && !customOn(getCustom(),'2026-12-05').some(e=>e.name==='출장')"))
        check('내 일정: 내 달력 아이콘(✈️·🎭)', await ev("myDayItems('2026-12-03').some(x=>x.icon==='✈️') && myDayItems('2026-12-05').some(x=>x.icon==='🎭')"))
        await ev("openCustomForm('2026-12-02', getCustom().slice(-2)[0].id)"); await pg.wait_for_timeout(300)
        await ev("currentYear=2026;currentMonth=11;setCalView('month');renderCalendar()"); await pg.wait_for_timeout(200)
        cards = await ev("[...document.querySelectorAll('#cal-grid .sess-card')].map(c=>c.textContent.replace(/\s+/g,' ').trim())")
        check('달력: 공연 일정은 이모지 없이, 기타는 이름 앞 아이콘', any('✈️ 출장' in c for c in cards) and any('지방 공연' in c and '🎭' not in c for c in cards), cards[:4])
        check('내 일정: 고치기 창에 종류·아이콘·끝날 다시 채움', await ev("document.getElementById('ov-custom').dataset.kind==='etc' && document.getElementById('cf-end').value==='2026-12-04' && _cfIcon==='✈️'"))
        await ev("closeCustomForm(); saveCustom(getCustom().slice(0,-2)); renderCalendar()")
        await ev("openSearch()"); await pg.fill('#srch-q', '페이티드'); await ev("renderSearch()"); await pg.wait_for_timeout(300)
        check('찾기: 영어 제목 작품을 한글로도 찾음 (페이티드 → FATED)', 'FATED' in ' '.join(await ev("[...document.querySelectorAll('.flt-hit-name')].map(e=>e.textContent)")))
        # 날짜 찾기에서 줄을 누르면 그 작품 그 회차 — 내 날짜 상세가 열려 예매한 작품만 보였다 (11/25)
        await pg.fill('#srch-q', '12/9'); await ev("renderSearch()"); await pg.wait_for_timeout(300)
        check('찾기: 날짜 결과에 그 회차 이벤트 이름도', await ev("""(()=>{const ds=parseQueryDate('12/9');const want=catalog('all').works.some(w=>rowsOf(w).some(s=>s.date===ds&&eventsOf(w).some(e=>e.name&&evAt(e,ds,s.time))));
          return !want || document.querySelectorAll('.srch-row .mc-ev').length>0})()"""))
        dr = await ev("""(()=>{const rows=[...document.querySelectorAll('.srch-row')].filter(r=>r.querySelector('.srch-name'));
          const r=rows[rows.length-1]; if(!r) return null; const nm=r.querySelector('.srch-name').textContent.trim(); r.click();
          const t=document.getElementById('ev-sheet-title'); return [nm, t ? t.textContent : document.getElementById('ev-sheet-body').innerHTML.slice(0,80)];})()""")
        check('찾기: 날짜 결과 줄 → 그 작품 회차 창', bool(dr) and dr[0].split(' ',1)[-1][:4] in dr[1], dr)
        await ev("closeEvSheet && closeEvSheet()")
        await pg.fill('#srch-q', '커튼콜'); await ev("renderSearch()"); await pg.wait_for_timeout(300)
        evn =await ev("_evGroups.length")
        # 특정 작품 이름은 묻지 않는다 — 그 작품 이벤트가 끝나면 데이터 따라 깨졌다(마하고니, 11/23)
        check('찾기: 이벤트는 개수 제한 없이 전부 (커튼콜 → 12개 넘게)', evn > 12, evn)
        # 동명이인(people.json) — 작품마다 다른 사람으로 받고, 캐스팅 줄엔 꼬리표 없이 (11/23)
        hm = await ev("(async()=>{await ensureCatalog(); const c=(_catalogRows['show_choirofman2026']||schedules['show_choirofman2026']||[]).flatMap(Object.values), k=(_catalogRows['show_shootthecrow2026']||schedules['show_shootthecrow2026']||[]).flatMap(Object.values); const s=(_catalogRows['show_shootthecrow2026']||[]).find(r=>Object.values(r).includes('김도현#2')); return [c.includes('김도현#1'), k.includes('김도현#2'), !c.includes('김도현') && !k.includes('김도현'), s ? castHtml({id:'show_shootthecrow2026'}, s).includes('김도현') && !castHtml({id:'show_shootthecrow2026'}, s).includes('#') && !castHtml({id:'show_shootthecrow2026'}, s).includes('슛 더 크로우') : false]})()")
        check('동명이인: 김도현 두 사람으로 나뉘고 캐스팅 줄엔 이름만', all(hm), hm)
        lb = await ev("[actorLabel('김도현#1'), actorLabel('김도현#2')]")
        check('동명이인: 이름 옆은 그 사람의 가장 최근 작품', lb == ['김도현 · 콰이어 오브 맨', '김도현 · 슛 더 크로우'], lb)
        rc = await ev("""(async()=>{await ensureCatalog(); const keep=localStorage.getItem(RECENT_Q_KEY); localStorage.setItem(RECENT_Q_KEY, JSON.stringify(['옛글자']));
          const w=catalog('all').works.find(w=>w.fullName&&w.fullName!==w.name)||catalog('all').works[0];
          const q=document.getElementById('srch-q'); q.value=w.name.slice(0,2); renderSearch(); pickSearch('work', w.id); backSearch(); q.value=''; renderSearch();
          const chips=[...document.querySelectorAll('.srch-recent .srch-chip')].map(c=>c.firstChild.textContent);
          document.querySelector('.srch-recent .srch-chip').click(); const opened=_srchSel&&_srchSel.key===w.id;
          if(keep) localStorage.setItem(RECENT_Q_KEY,keep); else localStorage.removeItem(RECENT_Q_KEY); backSearch();
          return [chips[0]===(w.icon?w.icon+' ':'')+(w.fullName||w.name), chips[1]==='옛글자', chips.length, opened]})()""")
        check('최근 검색: 친 글자 말고 누른 작품 이름, 누르면 바로 열림, 옛 기록 유지', rc == [True, True, 2, True], rc)
        xs = await ev("(()=>{const q=document.getElementById('srch-q'), b=document.querySelector('#home-search .hs-close'); q.value='김'; b.click(); const r=[q.value==='', !document.getElementById('home-search').hidden]; b.click(); r.push(document.getElementById('home-search').hidden); return r})()")
        check('찾기 ✕: 글자 있으면 지우기, 비어 있으면 달력으로', xs == [True, True, True], xs)
        await ev("closeSearch()")
        # 회차마다 설명 한 군데만 다른 같은 이벤트(하트비트 책갈피) — 공통 설명은 한 번, 다른 부분은 회차 줄에
        sp = await ev("""(()=>{const mk=(t,x)=>({name:'책갈피',startDate:'2026-11-16',endDate:'2026-11-16',times:[t],description:`유료 1매당 1개, 이 회차 책갈피: ${x} (총 3종), 매표소에서 수령`});
          const r=evSplitDesc([mk('20:00','공범이 된 목격자'),mk('16:00','심폐소생일지')]);return r&&[r.head,r.mid(mk('','고자질하는 심장').description)]})()""")
        check('이벤트: 회차마다 다른 설명은 공통 한 번 + 회차 줄에 다른 부분', sp == ['유료 1매당 1개, 이 회차 책갈피: 회차마다 다름 (아래) (총 3종), 매표소에서 수령', '고자질하는 심장'], sp)
        # 공연 정보 비교: 이름이 같은 배역 칸(게스트 여러 칸)은 묶어서 — 한 명 빠지면 그 한 명만
        cd = await ev("""(async()=>{await ensureCatalog();const w=catalog('all').works.find(x=>/정찬콘/.test(x.name)); if(!w) return 'no-work'; const ks=((infoOf(w)||{}).roles||[]).map(r=>r.key).slice(0,4);
          const mk=a=>ks.slice(0,a.length).map((k,i)=>k+'='+a[i]).join('|'), K='2026-12-31 20:00';
          return diffSnapshots({[w.id]:{sess:{[K]:mk(['가','나','다','라'])},ev:{}}},{[w.id]:{sess:{[K]:mk(['나','다','라'])},ev:{}}}).works.map(x=>x.cast.map(c=>c.t))})()""")
        check('공연 정보 비교: 같은 배역 칸은 묶어서 (게스트 한 명 빠짐)', cd == [['게스트 빠짐 가']], cd)
        # 탭 순서 — ▲▼ 로 바꾸고, 탭 없는 작품(배우 ♡로만 들어온 것)은 제자리
        to = await ev("""(()=>{const keep=localStorage.getItem(APPS_KEY);const mk=(id,v)=>({id,name:id,icon:'',color:'#888',scheduleUrl:'x'+id,appUrl:'',kind:'data',recordsKey:'k'+id,...(v?{viaActor:true}:{})});
          saveApps([mk('a'),mk('b'),mk('v',1),mk('c')]);moveTab('c',-1);const r1=getApps().map(a=>a.id).join('');
          applyTabOrder(['b','c','a']);const r2=getApps().map(a=>a.id).join('');localStorage.setItem(APPS_KEY,keep);return [r1,r2]})()""")
        check('탭 순서: 끌기로 바꾸고 탭 없는 작품은 제자리', to == ['acvb', 'bcva'], to)
        # 첫공·막공 배우 굵게 — 해당 배우만, 전원이면 전원(개막·전체 막공)
        fl = await ev("""(async()=>{await ensureCatalog();const mk=(d,t,a,b)=>({date:d,time:t,r1:a,r2:b});
          const rows=[mk('2026-12-01','20:00','가','나'),mk('2026-12-02','20:00','다','나'),mk('2026-12-03','20:00','가','다'),mk('2026-12-04','20:00','가','나')];
          const w={id:'show_fltest',kind:'data'}; schedules[w.id]=rows; dataInfo[w.id]={endDate:'2026-12-04',roles:[{key:'r1'},{key:'r2'}]};
          const out=rows.map(r=>castHtml(w,r)); delete schedules[w.id]; delete dataInfo[w.id]; return out})()""")
        check('첫공·막공 배우 굵게 (전원이면 전원)', fl == ['<b>가</b> · <b>나</b>', '<b>다</b> · 나', '가 · <b>다</b>', '<b>가</b> · <b>나</b>'], fl)
        # 공지로 먼저 알려진 막공(lastShows) — 스케줄이 끝까지 안 열려도 그 회차에서 굵게
        ls = await ev("""(async()=>{const mk=(d,t,a,b)=>({date:d,time:t,r1:a,r2:b});
          const rows=[mk('2026-12-01','20:00','가','나'),mk('2026-12-02','20:00','다','나'),mk('2026-12-03','20:00','가','다')];
          const w={id:'show_lstest',kind:'data'}; schedules[w.id]=rows; dataInfo[w.id]={endDate:'2026-12-31',lastShows:{'나':'2026-12-02 20:00'}};
          const out=rows.map(r=>castHtml(w,r)); delete schedules[w.id]; delete dataInfo[w.id]; return out})()""")
        check('공지된 막공(lastShows)은 스케줄이 덜 열려도 굵게', ls == ['<b>가</b> · <b>나</b>', '<b>다</b> · <b>나</b>', '가 · 다'], ls)
        # 관심함: 끝난 작품은 '종료된 작품 n개'로 접고, 누르면 펼친다
        hp = await ev("""(()=>{const keep=localStorage.getItem(APPS_KEY), kh=localStorage.getItem(HEARTS_KEY);
          const mk=(id,d)=>({id,name:id,icon:'',color:'#888',scheduleUrl:'x'+id,appUrl:'',kind:'data',recordsKey:'k'+id});
          saveApps([mk('show_live'),mk('show_done')]); schedules.show_live=[{date:'2099-01-01',time:'20:00'}]; schedules.show_done=[{date:'2000-01-01',time:'20:00'}];
          saveHearts({works:['show_done','show_live'],actors:[]}); _hpEndedOpen=false; document.getElementById('home-hearts').hidden=false; renderHearts();
          const t1=document.getElementById('hearts-body').innerText; _hpEndedOpen=true; renderHearts(); const t2=document.getElementById('hearts-body').innerText;
          _hpEndedOpen=false; document.getElementById('home-hearts').hidden=true; localStorage.setItem(APPS_KEY,keep||'[]'); if(kh) localStorage.setItem(HEARTS_KEY,kh); _hearts=null;
          return [t1.includes('show_live') && !t1.includes('show_done') && t1.includes('종료된 작품 1개'), t2.includes('show_done')]})()""")
        check('관심함: 끝난 작품은 접어 두고 펼치기', hp == [True, True], hp)
        # 달력 시작 요일 (요청 폼 11/12) — 2026-11-01 은 일요일
        dq = "()=>{currentYear=2026;currentMonth=10;setCalView('month');renderCalendar();return [[...document.querySelectorAll('#cal-dow .dow-cell')].map(e=>e.textContent).join(''),[...document.querySelector('#cal-days').children].findIndex(c=>c.textContent.trim().startsWith('1'))]}"
        mon = await ev(dq); await ev("setWeekStart('month','sun')"); sun = await ev(dq)
        wk = await ev("()=>{setCalView('week');weekStart=null;renderCalendar();const a=weekStart.getDay();setWeekStart('week','sun');const b=weekStart.getDay();setCalView('month');return [a,b]}")
        check('달력 시작 요일: 월간·주간 따로, 기본 월요일', mon == ['월화수목금토일', 6] and sun == ['일월화수목금토', 0] and wk == [1, 0], [mon, sun, wk])
        await ev("setWeekStart('month','mon');setWeekStart('week','mon')")
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
        # 정보만 → 전용 앱으로 바뀐 작품(리플리): 예전 항목을 빼고 ♥·필터를 앱으로. 허브 예매 기록이 있으면 그대로 둔다
        old = "({id:'show_ripley2026',kind:'data',name:'리플리',icon:'✒️',color:'#8A5A5A',scheduleUrl:location.origin+'/otk-test/shows/ripley2026.json',appUrl:'',deepLink:false,recordsKey:HUB_NS+'rec_ripley2026'})"
        for recs, label in (([], '정보만 → 앱: 예전 항목 빼고 ♥·필터를 앱으로'), ([{'date': '2026-12-23', 'time': '20:00'}], '정보만 → 앱: 허브 예매 기록이 있으면 그대로 둠')):
            await e2("localStorage.clear()")
            await e2(f"""r=>{{localStorage.setItem(APPS_KEY,JSON.stringify([{old}]));saveHearts({{...getHearts(),works:['show_ripley2026']}});
              saveFilter({{v:3,offWorks:['show_ripley2026'],offActors:[],off:[]}});saveExtraRecords(r,HUB_NS+'rec_ripley2026');}}""", recs)
            await pg2.reload(); await pg2.wait_for_timeout(7000)
            got = await e2("[getApps().map(a=>a.id).sort(), getHearts().works, getFilter().offWorks]")
            want = [['app_ripley2026'], ['app_ripley2026'], ['app_ripley2026']] if not recs else [['show_ripley2026'], ['show_ripley2026'], ['show_ripley2026']]
            check(label, got == want, got)
        # ♥ 이전 방식(탭만 있고 ♥ 비어 있음)으로 복원된 기기 — 탭 작품을 ♥ 로 옮긴다
        await e2("localStorage.clear()")
        await e2("""()=>{const mk=(id)=>({id,name:id,icon:'',color:'#888',scheduleUrl:'x'+id,appUrl:'',kind:'data',recordsKey:'k'+id});
          localStorage.setItem(APPS_KEY,JSON.stringify([mk('show_a'),{...mk('show_b'),viaActor:true}]));localStorage.setItem(HEARTS_KEY,JSON.stringify({works:[],actors:[]}));_hearts=null}""")
        check('♥ 비고 탭만 있는 옛 데이터 → 탭 작품을 ♥ 로', await e2("getHearts().works.join()") == 'show_a')
        # ♥ 없이 예매 기록만 있어도 '아직 달력에 넣은 공연이 없어요' 안내는 숨긴다 (♥ 이전 백업 복원, 11/14)
        await e2("localStorage.clear()")
        await e2("localStorage.setItem('ikkisup_records', JSON.stringify([{id:'x',date:'2026-12-01',time:'20:00',isBooked:true}]))")
        await pg2.reload(); await pg2.wait_for_timeout(8000)
        check('♥ 없이 기록만 있어도 빈 안내 숨김', await e2("getHearts().works.length===0 && document.getElementById('hub-empty').hidden"))
        # 전용 페이지에만 예매 기록이 있고 허브에 안 넣은 작품 → ♥ 없이 '예매만'으로 들어와 달력에 (요청 폼 11/13 FATED)
        await e2("localStorage.clear()")
        await e2("localStorage.setItem('fated_records', JSON.stringify([{id:'x1',date:'2026-12-01',time:'20:00',isBooked:true}]))")
        await pg2.reload(); await pg2.wait_for_timeout(8000)
        got = await e2("[getApps().map(a=>[a.id,!!a.viaActor]), getHearts().works, (getAttended()['2026-12-01']||[]).length]")
        check('예매 기록만 있는 전용 페이지 작품도 달력에 (♥ 없이)', got == [[['app_fated', True]], [], 1], got)
        # 정보만 작품이 전용 페이지로 바뀔 때 — 사진·메모만 남긴 회차가 있으면 예전 항목을 지우지 않는다 (리뷰 11/15)
        rip = "localStorage.setItem(HUB_NS+'apps', JSON.stringify([{id:'show_ripley2026',name:'리플리',icon:'🎭',color:'#888',kind:'data',scheduleUrl:SITE+'/shows/ripley2026.json',appUrl:'',recordsKey:HUB_NS+'rec_ripley2026'}]))"
        await e2("localStorage.clear()"); await e2(rip)
        await pg2.reload(); await pg2.wait_for_timeout(8000)
        dropped = await e2("!getApps().some(a=>a.id==='show_ripley2026')")
        await e2("localStorage.clear()"); await e2(rip)
        await e2("localStorage.setItem(HUB_NS+'notes', JSON.stringify({'show_ripley2026__2026-12-23__19:30':{memo:'사진만',photoIds:[]}}))")
        await pg2.reload(); await pg2.wait_for_timeout(8000)
        kept = await e2("getApps().some(a=>a.id==='show_ripley2026')")
        check('정보만→전용 페이지: 메모만 있는 작품은 남김 (메모 없으면 옮김)', dropped and kept, [dropped, kept])
        # 정보만 작품 예매 기록 → 양도글 복사 (11/17): 제목·날짜·캐스트·좌석 범위, 가격 없음, 지난 회차엔 버튼 없음
        hat = "localStorage.setItem(HUB_NS+'apps', JSON.stringify([{id:'show_hatshepsut2026',name:'하트셉수트',icon:'🌙',color:'#888',kind:'data',scheduleUrl:SITE+'/shows/hatshepsut2026.json',appUrl:'',recordsKey:HUB_NS+'rec_hatshepsut2026'}]))"
        await e2("localStorage.clear()"); await e2(hat)
        await e2("localStorage.setItem(HUB_NS+'rec_hatshepsut2026', JSON.stringify([{id:'h1',date:'2026-12-26',time:'19:00',show:'하트셉수트',seatZone:'B',seatNumber:1,price:77000,status:''}]))")
        await pg2.reload(); await pg2.wait_for_timeout(8000)
        import re
        # 회차 자세히 창(내 기록 보기 옆)에도 버튼 — 사용자가 여기서 찾음(11/17). 지난 회차·양도한 표엔 없음
        got = await e2("""(()=>{const has=()=>document.getElementById('ev-sheet-body').innerHTML.includes('양도 정보 복사');
          todayStr='2026-12-01';openEvSess('show_hatshepsut2026','2026-12-26','19:00','',0);const a=has();
          todayStr='2027-01-01';openEvSess('show_hatshepsut2026','2026-12-26','19:00','',0);const b=has();
          todayStr='2026-12-01';openEvSess('show_hatshepsut2026','2026-12-27','14:00','',0);const c=has();return [a,b,c]})()""")
        check('회차 자세히 창 양도 정보 복사 버튼', got == [True, False, False], got)
        # 월별 통계 (11/27): 앱 기록 + 내 일정 공연 출연 칸이 같은 배우로 합쳐 세짐, 양도·미정은 빼고, 동명이인 안 고르면 (?)
        got = await e2("""(()=>{const row=(schedules['show_hatshepsut2026']||[]).find(s=>s.date==='2026-12-26'&&s.time==='19:00');
          const actor=bareName(getActorFields(row).map(k=>row[k])[0]);
          localStorage.setItem(CUSTOM_KEY, JSON.stringify([
            {id:'s1',kind:'show',name:'가상 연극',date:'2026-12-05',time:'15:00',cast:actor+'(역), 김도현'},
            {id:'s2',kind:'show',name:'가상 연극',date:'2026-12-06',time:'15:00',cast:actor,tentative:true},
            {id:'s3',kind:'show',name:'가상 연극',date:'2026-12-07',time:'15:00',cast:'김도현',castIds:{'김도현':'2'}}]));
          todayStr='2026-12-10';_stMonth='2026-12';openStats();
          const t=document.getElementById('st-body').innerText;
          const chips=[...document.querySelectorAll('.st-actors span')].map(x=>x.textContent);
          return [t.includes('2회 관람')&&t.includes('예정 1회')&&t.includes('미정 1'), chips.some(c=>c.startsWith(actor)&&c.endsWith('2')),
            chips.some(c=>c==='김도현(?)1'), chips.some(c=>c.startsWith('김도현 ·')&&c.endsWith('1'))]})()""")
        await e2("localStorage.removeItem(CUSTOM_KEY);document.getElementById('ov-stats').classList.remove('open')")
        check('월별 통계: 관람·예정·미정, 출연 칸 배우가 회차 캐스팅과 합쳐짐, 동명이인', got == [True, True, True, True], got)
        got = await e2("""(()=>{const b=document.getElementById('stats-btn'), vis=()=>b.offsetParent!==null;
          const a0=vis(); openSettings(); applyStatsBtn(); document.querySelector('#stats-seg button').click(); const a1=vis();
          document.querySelectorAll('#stats-seg button')[1].click(); const a2=vis(); closeSettings(); return [a0,a1,a2]})()""")
        check('📊 버튼: 기본 숨김, 설정에서 보이기·숨기기', got == [False, True, False], got)
        # 보기 필터 (11/28): 한 줄 + 스위치, 종료된 작품은 접힘, 배우 줄 작품 이름 → 그 작품에서만 빼기(취소선), 모두 켜기는 제목 줄
        got = await e2("""(()=>{const keepH=localStorage.getItem(HEARTS_KEY), keepF=localStorage.getItem(FILTER_KEY);
          const a=getApps()[0]; if(!a) return 'no-app';
          const n=(()=>{for(const s of (schedules[a.id]||[]).filter(s=>s.date>=todayStr)){const k=getActorFields(s).find(k=>typeof s[k]==='string');if(k)return s[k]}})();
          saveHearts({...getHearts(),works:[a.id],actors:[n]}); saveFilter({v:3,offWorks:[],offActors:[],off:[]});
          openFilter(); const q=s=>document.querySelector(s);
          const r0=[!q('#fx-allon'), q('.fx-li[role=switch]').getAttribute('aria-checked')];
          q('.fx-li[role=switch]').click(); const r1=[getFilter().offWorks.includes(a.id), !q('#fx-allon'), q('.fx-li[role=switch]').classList.contains('off')];
          const w=q('.fx-w'); w.click(); const r2=[getFilter().off.length, q('.fx-w').getAttribute('aria-checked')==='false'];
          q('#fx-allon').click(); const r3=[filterActive(), !q('#fx-allon')];
          closeFilter(); if(keepH) localStorage.setItem(HEARTS_KEY,keepH); else localStorage.removeItem(HEARTS_KEY); _hearts=null;
          if(keepF) localStorage.setItem(FILTER_KEY,keepF); else localStorage.removeItem(FILTER_KEY);
          return [r0,r1,r2,r3]})()""")
        check('보기 필터: 스위치·작품별 빼기·모두 켜기', got == [[True,'true'],[True,False,True],[1,True],[False,True]], got)
        # 보기 필터 접기 (11/28): 꺼 둔 것은 안 접힘, 배우 칩 진행 중 3개 + +N(펼치면 지난 작품까지), 공연 없는 배우 접기, 보는 달에 공연 있던 작품은 앞에
        got = await e2("""(()=>{const keepH=localStorage.getItem(HEARTS_KEY), keepF=localStorage.getItem(FILTER_KEY), keepT=todayStr, keepY=currentYear, keepM=currentMonth, keepV=localStorage.getItem(CAL_VIEW_KEY);
          const R=getApps()[0]; if(!R) return 'no-app'; const A=[0,1,2,3,4,5,6].map(i=>i===5?R:{id:'fxfake'+i,name:'가짜'+i,icon:''}); const keepS=A.map(a=>schedules[a.id]);
          const row=(d,x)=>({date:d,time:'19:30',role1:x});
          A.forEach((a,i)=>schedules[a.id]= i<5 ? [row('2026-12-1'+(i+1),'가상배우')] : i===5 ? [row('2026-08-05','가상배우')] : [row('2026-09-01','가상배우'),{date:'2026-09-02',time:'19:30',role1:'가상둘'}]);
          const keepI=actorIndex; actorIndex=()=>new Map([['가상배우',A],['가상둘',[A[6]]]]);
          const keepF2=getActorFields; getActorFields=s=>Object.keys(s).filter(k=>k.startsWith('role'));
          todayStr='2026-12-10'; localStorage.setItem(CAL_VIEW_KEY,'month'); currentYear=2026; currentMonth=11;
          saveHearts({...getHearts(),works:[A[5].id],actors:['가상배우','가상둘']}); saveFilter({v:3,offWorks:[],offActors:[],off:[]});
          _fxIdleOpen=false; _fxDoneOpen=false; _fxOpenActors.clear(); openFilter();
          const q=s=>document.querySelector(s), chips=()=>[...document.querySelectorAll('.fx-w')].map(b=>b.textContent.trim()), more=()=>q('.fx-more')?.textContent;
          const r=[];
          r.push([chips().length, more(), !!q('#fx-idle'), !!q('#fx-wdone')]);                 // 3개 +4, 가상둘 접힘, 종료 작품 접힘
          q('.fx-more').click(); r.push([chips().length, more(), chips().filter(c=>c.endsWith('종료')).length]);   // 7개(지난 2개), 접기
          q('.fx-more').click(); saveFilter({v:3,offWorks:[A[5].id],offActors:[],off:[offKey(A[6].id,'가상배우'),offKey(A[6].id,'가상둘')]}); renderActorFilters();
          r.push([chips().length, more(), !!q('#fx-idle'), !!q('#fx-wdone')]);                 // 가상배우: 꺼 둔 지난 작품 + 3개, 가상둘은 꺼 둔 칩 때문에 밖으로, 꺼 둔 종료 작품도 밖에
          schedules[A[5].id]=[row('2026-12-03','가상배우')]; saveFilter({v:3,offWorks:[],offActors:[],off:[]}); renderActorFilters();
          r.push([!chips()[0].includes(A[5].name), !!q('#fx-wdone')]);   // 이번 달에 막공한 작품은 진행 중보다 앞에 안 섬, 관심 작품에서도 접힘
          schedules[A[5].id]=[row('2026-08-05','가상배우')]; currentMonth=7; renderActorFilters();
          r.push([chips()[0].startsWith(A[5].icon?A[5].icon+' '+A[5].name:A[5].name), !!q('#fx-wdone')]);   // 8월 보면 8월 작품이 맨 앞, 접히지 않음
          closeFilter(); A.forEach((a,i)=>{ if(keepS[i]===undefined) delete schedules[a.id]; else schedules[a.id]=keepS[i]; }); actorIndex=keepI; getActorFields=keepF2; todayStr=keepT; currentYear=keepY; currentMonth=keepM;
          if(keepV) localStorage.setItem(CAL_VIEW_KEY,keepV); else localStorage.removeItem(CAL_VIEW_KEY);
          if(keepH) localStorage.setItem(HEARTS_KEY,keepH); else localStorage.removeItem(HEARTS_KEY); _hearts=null;
          if(keepF) localStorage.setItem(FILTER_KEY,keepF); else localStorage.removeItem(FILTER_KEY); renderCalendar();
          return r})()""")
        check('보기 필터 접기: 꺼 둔 것 안 접힘·+N·공연 없는 배우·보는 달 우선', got == [[3,'+4',True,True],[7,'접기',2],[5,'+3',False,False],[True,True],[True,False]], got)
        # 작품 탭 줄 (11/28): 없으면 줄·칸막이 없음, 들어가면 한 줄, 넘치면 아이콘 아래 둘째 줄
        got = await e2("""(()=>{const keep=localStorage.getItem(APPS_KEY), kv=localStorage.getItem(HIDDEN_KEY);
          const mk=i=>({id:'show_fk'+i,name:'가짜'+i,icon:'',color:'#888',scheduleUrl:'xfk'+i,appUrl:'',kind:'data',recordsKey:'kfk'+i});
          const hd=document.querySelector('.header'), sep=document.querySelector('.hd-sep'), tabs=document.getElementById('app-tabs'), heart=document.querySelector('.hbtn-heart');
          const st=()=>[hd.classList.contains('tabs-wrap'), sep.offsetParent!==null, tabs.children.length?tabs.getBoundingClientRect().top>=heart.getBoundingClientRect().bottom:null, document.documentElement.scrollWidth<=innerWidth];
          localStorage.removeItem(HIDDEN_KEY);
          saveApps([]);renderTabs();const a=st();
          saveApps([0,1].map(mk));renderTabs();const b=st();
          saveApps([0,1,2,3,4,5,6,7].map(mk));renderTabs();const c=st();
          if(keep) localStorage.setItem(APPS_KEY,keep); else localStorage.removeItem(APPS_KEY);
          if(kv) localStorage.setItem(HIDDEN_KEY,kv);
          renderTabs();highlightTab(currentView);return [a,b,c]})()""")
        check('작품 탭 줄: 0개 줄 없음 · 2개 한 줄 · 8개 둘째 줄', got == [[False, False, None, True], [False, True, False, True], [True, False, True, True]], got)
        got = await e2("""(()=>{_stMonth='2026-11';openStats();const el=document.getElementById('st-body');
          const tc=(type,x)=>{const tt=new Touch({identifier:1,target:el,clientX:x,clientY:300});el.dispatchEvent(new TouchEvent(type,{touches:type==='touchstart'?[tt]:[],changedTouches:[tt],bubbles:true}))};
          tc('touchstart',300);tc('touchend',150);const a=_stMonth;tc('touchstart',100);tc('touchend',260);tc('touchstart',100);tc('touchend',260);
          const b=_stMonth;document.getElementById('ov-stats').classList.remove('open');return [a,b]})()""")
        check('통계 가로로 밀어 달 넘기기', got == ['2026-12', '2026-10'], got)
        # 내 일정 공연도 아이콘 고르기 (11/27): 공연 목록 따로, 저장, 통계·카드에 반영, 예전 공연 이름 고르면 그 아이콘
        got = await e2("""(async()=>{openCustomForm('2026-12-03');await new Promise(r=>setTimeout(r,300));
          const vis=document.getElementById('cf-icons').offsetParent!==null, first=document.querySelector('#cf-icons button').textContent;
          document.getElementById('cf-name').value='가상 콘서트';[...document.querySelectorAll('#cf-icons button')].find(b=>b.textContent==='🎤').click();
          await saveCustomEvent();const e=getCustom().find(x=>x.name==='가상 콘서트');
          openCustomForm('2026-12-04');await new Promise(r=>setTimeout(r,300));pickCfName('가상 콘서트');const again=_cfIcon;closeCustomForm();
          setCfKind('etc');const etcFirst=document.querySelector('#cf-icons button').textContent;
          localStorage.removeItem(CUSTOM_KEY);return [vis,first,e&&e.icon,customLabel(e),again,etcFirst]})()""")
        check('내 일정 공연 아이콘 고르기', got == [True,'🎭','🎤','🎤 가상 콘서트','🎤','✈️'], got)
        # 내 일정 공연 → 허브 작품 회차로 옮기기 (11/27): 이름 띄어쓰기 무시, 좌석·금액·메모 가져가고 내 일정은 지움
        got = await e2("""(async()=>{todayStr='2026-12-01';
          localStorage.setItem(CUSTOM_KEY, JSON.stringify([{id:'m1',kind:'show',name:'하트 셉수트',date:'2026-12-27',time:'14:00',seatZone:'D',seatNumber:9,price:55000,comment:'첫 관람',vendor:'NOL'},
            {id:'m2',kind:'show',name:'하트셉수트',date:'2026-12-28',time:'03:00'}]));
          await openDay('2026-12-27');const btn=[...document.querySelectorAll('#sheet-content .cu-move')];
          await openDay('2026-12-28');const none=document.querySelectorAll('#sheet-content .cu-move').length;
          if(btn.length!==1) return ['btn',btn.length];
          await moveCustomToWork('m1','show_hatshepsut2026','14:00','');await new Promise(r=>setTimeout(r,300));
          const rec=JSON.parse(localStorage.getItem(HUB_NS+'rec_hatshepsut2026')).find(r=>r.date==='2026-12-27');
          const note=getNotes()['show_hatshepsut2026__2026-12-27__14:00'];
          const left=getCustom().map(e=>e.id);localStorage.removeItem(CUSTOM_KEY);
          return [none, rec&&[rec.time,rec.seatZone,rec.seatNumber,rec.price], note&&note.memo, left]})()""")
        check('내 일정 공연 → 작품 회차로 옮기기', got == [0, ['14:00','D',9,55000], '첫 관람 · 예매처 NOL', ['m2']], got)
        # 출연 자동완성: 쉼표 뒤 이름만 찾고, 고른 동명이인은 castIds 로
        await e2("openCustomForm('2026-12-01')"); await pg2.wait_for_timeout(5000)
        got = await e2("""(()=>{const el=document.getElementById('cf-cast');el.value='최호승, 김도';cfCastInput();
          const btns=[...document.querySelectorAll('#cf-cast-sugg button')];const b=btns.find(x=>x.textContent.startsWith('김도현')&&x.querySelector('small'));
          if(!b) return 'no-btn';b.click();const v=el.value;const ids=cfCastIdsKept(v);closeCustomForm();return [v, Object.keys(ids.castIds||{})]})()""")
        check('출연 자동완성: 마지막 이름만 바꾸고 동명이인 id 남김', got == ['최호승, 김도현, ', ['김도현']], got)
        # 날짜 상세(메모·예매 수정 줄)에도 — 사용자가 여기서도 찾음(11/17)
        got = await e2("""(async()=>{closeEvSheet();todayStr='2026-12-01';await openDay('2026-12-26');
          const h=document.body.innerHTML;let t='';const o=navigator.clipboard;
          try{Object.defineProperty(navigator,'clipboard',{value:{writeText:x=>{t=x;return Promise.resolve()}},configurable:true});}catch(e){}
          copyEvTransfer('show_hatshepsut2026','2026-12-26','19:00','');await new Promise(r=>setTimeout(r,50));
          return [h.includes('📋 양도 정보 복사</button>'), t]})()""")
        check('날짜 상세 양도 정보 버튼 (좌석 1번은 1-3~1-5, 가격 없음)', got[0] and got[1].startswith('뮤지컬 하트셉수트 양도\n\n12/26(토) 19:00\n전성민 여은\n\n') and re.search(r'B열 1-[345] 중 한자리$', got[1]) and '77' not in got[1], got)
        check('예매 기록 창엔 복사 버튼 없음 (11/17)', not await e2("!!document.getElementById('xr-copy')"))
        # 전용 페이지 작품 기록도 허브 창에서 바로 (11/17) — 층·열 그대로, 캐스트는 허브가 받은 스케줄에서
        await e2("localStorage.clear()")
        sd = await e2("fetch(SITE+'/ikkisup2026/schedule.json').then(r=>r.json()).then(j=>{const s=(j.schedule||j).find(x=>x.date>='2026-11-20');return [s.date,s.time]})")
        await e2(f"localStorage.setItem('ikkisup_records', JSON.stringify([{{id:'i1',date:'{sd[0]}',time:'{sd[1]}',isBooked:true,seatFloor:'1층',seatZone:'C',seatNumber:7}}]))")
        await pg2.reload(); await pg2.wait_for_timeout(8000)
        got = await e2(f"""(async()=>{{todayStr='2026-11-01';await openDay('{sd[0]}');const h=document.body.innerHTML.includes('📋 양도 정보 복사</button>');
          let t='';try{{Object.defineProperty(navigator,'clipboard',{{value:{{writeText:x=>{{t=x;return Promise.resolve()}}}},configurable:true}});}}catch(e){{}}
          copyEvTransfer('app_ikkisup','{sd[0]}','{sd[1]}','');await new Promise(r=>setTimeout(r,50));return [h,t]}})()""")
        check('전용 페이지 작품도 허브에서 양도 정보 복사', got[0] and got[1].startswith('뮤지컬 이끼숲 양도') and re.search(r'1층 C열 \d+-\d+ 중 한자리$', got[1]) and len(got[1].split('\n')) >= 4, got)
        # 내 일정 추가 공연명 자동완성 (11/17): 별칭으로 작품이 뜨고, 고르면 회차 칩 → 그 작품 예매 기록으로 저장
        await e2("localStorage.clear()")
        await e2("localStorage.setItem(HUB_NS+'custom', JSON.stringify([{id:1,kind:'show',date:'2026-10-01',time:'19:00',name:'레미제라블',color:'#888',photoIds:[]}]))")
        await pg2.reload(); await pg2.wait_for_timeout(8000)
        got = await e2("""(async()=>{await openCustomForm('2026-12-26');await ensureCatalog();
          const n=document.getElementById('cf-name');n.value='하셉';cfNameInput();
          const sug=document.getElementById('cf-sugg').innerText;
          n.value='레미';cfNameInput();const mine=document.getElementById('cf-sugg').innerText;
          n.value='하셉';cfNameInput();await pickCfWork('show_hatshepsut2026');
          const chips=[...document.querySelectorAll('#cf-sess .chips button')].map(b=>b.textContent);
          document.getElementById('cf-time').value='19:00';renderCfSess();
          document.getElementById('cf-seat-zone').value='C';document.getElementById('cf-seat-num').value='4';
          await saveCustomEvent();await new Promise(r=>setTimeout(r,300));
          const rec=JSON.parse(localStorage.getItem(HUB_NS+'rec_hatshepsut2026')||'[]');
          return [sug.includes('하트셉수트'), mine.includes('레미제라블'), chips, rec.map(r=>[r.date,r.time,r.seatZone,r.seatNumber]), getCustom().length]})()""")
        check('공연명 자동완성 → 작품 회차 예매로 저장', got[:2] == [True, True] and got[2] == ['15:00', '19:00'] and got[3] == [['2026-12-26', '19:00', 'C', 4]] and got[4] == 1, got)
        # 그날 회차가 없으면 내 일정으로
        got = await e2("""(async()=>{await openCustomForm('2026-12-21');await ensureCatalog();
          const n=document.getElementById('cf-name');n.value='하트셉';cfNameInput();await pickCfWork('show_hatshepsut2026');
          const msg=document.getElementById('cf-sess').innerText;await saveCustomEvent();
          return [msg.includes('회차가 없어요'), getCustom().filter(e=>e.name==='하트셉수트').length]})()""")
        check('회차 없는 날은 내 일정으로', got == [True, 1], got)
        await e2("localStorage.clear()")
        # 안 넣은 전용 페이지 작품의 예매 기록 — 새 창이 아니라 허브 안 임시 탭으로 (11/18)
        await pg2.reload(); await pg2.wait_for_timeout(1500)
        got = await e2("""(async()=>{await ensureCatalog();let opened=0;window.open=()=>{opened++};
          const p=allPresets().find(x=>x.appUrl&&x.deepLink!==false&&!x.kind&&!getApps().some(a=>a.id===x.id));
          await sessTap(p.id,'2026-12-26','15:00','');await new Promise(r=>setTimeout(r,300));
          const a=getApps().find(x=>x.id===p.id)||{};const f=document.getElementById('frame-'+p.id);
          const r=[opened, a.viaActor===true, getHearts().works.includes(p.id), currentView===p.id, !!document.getElementById('btn-'+p.id), !!f&&f.src.includes('date=2026-12-26')];
          switchView('cal');await new Promise(r=>setTimeout(r,200));
          return [...r, getApps().some(x=>x.id===p.id), !!document.getElementById('btn-'+p.id)]})()""")
        check('안 넣은 전용 페이지 예매 기록 → 허브 안 임시 탭 (기록 없이 나오면 빠짐)', got == [0, True, False, True, True, True, False, False], got)
        # 찾기 자세히의 '전용 페이지 ›' 를 누르면 그 작품 탭으로 (11/18)
        got = await e2("""(async()=>{const p=allPresets().find(x=>x.appUrl&&!x.kind&&!getApps().some(a=>a.id===x.id));
          openSearch();await pickSearch('work',p.id);await new Promise(r=>setTimeout(r,500));
          const b=document.querySelector('.srch-tag.go');if(!b)return ['no btn'];b.click();await new Promise(r=>setTimeout(r,600));
          const f=document.getElementById('frame-'+p.id);
          return [currentView===p.id, !!f&&f.classList.contains('active')&&f.src!=='about:blank', document.getElementById('home-search').hidden, getHearts().works.includes(p.id)]})()""")
        check("찾기 '전용 페이지 ›' → 허브 안 그 작품 탭", got == [True, True, True, False], got)
        # 설정의 실험실 — 가져오기·붙여넣기는 그 안에 접혀 있다 (11/19)
        got = await e2("""(()=>{openSettings();const lab=document.getElementById('set-lab');const a=lab.hidden;toggleLab();
          return [a, lab.hidden, [...lab.querySelectorAll('button')].map(b=>b.textContent.trim())]})()""")
        check('실험실을 펼치면 CSV 가져오기·일정 붙여넣기', got == [True, False, ['📥 다른 앱 기록 가져오기 (CSV)', '📋 일정 붙여넣기 (JSON)']], got)
        # 일정 붙여넣기 (JSON 글) — 읽기 (11/19)
        got = await e2("""(()=>{const P=parsePaste('```json\\n[{“name”:“가상의 공연”,"date":"2026.12.26 오후 3시","seat":"1층 C열 7번","price":"55,000원",},{"이름":"레미","날짜":"2027년 1월 10일","시간":"14:00","출연":["가","나"]},{"name":"날짜없음"},{"date":"2026-12-01"},{"name":"틀린날","date":"2026-02-31"},]\\n```');
          return [P.rows.map(r=>[r['제목'],r._ds,r._time,r['좌석'],r['금액'],r['출연']]), P.errs.length, !!parsePaste('안녕').fail, parsePaste('{"list":[{"title":"x","date":"2026-12-01T19:30:00"}]}').rows.map(r=>r._ds+' '+r._time)]})()""")
        check('붙여넣기 읽기: 둥근 따옴표·끝 쉼표·한글 항목·날짜 모양, 못 읽는 항목은 따로',
              got == [[['가상의 공연', '2026-12-26', '15:00', '1층 C열 7번', '55000', ''], ['레미', '2027-01-10', '14:00', '', '', '가, 나']], 3, True, ['2026-12-01 19:30']], got)
        # 붙여넣기 → 미리보기 → 넣기: 허브 회차는 예매 기록, 없는 공연은 🎭 내 일정, 다시 붙이면 겹치지 않음
        await pg2.reload(); await pg2.wait_for_timeout(1500)
        txt = '[{"name":"하트셉수트","date":"2026-12-26","time":"19:00","seat":"B열 3번","price":66000,"memo":"붙여넣기"},{"name":"가상의 공연","date":"2026-12-27","time":"14:00","place":"어느 극장"},{"name":"빠짐"}]'
        got = await e2("""async(txt)=>{openSettings();openPaste();document.getElementById('paste-text').value=txt;await readPaste();
          const L=impPlan().list.map(x=>[x.kind,x.state]);const box=document.getElementById('set-import').innerText;const items=[...document.querySelectorAll('#set-import .imp-item')].map(e=>e.innerText.replace(/\\s+/g,' ').trim());
          const cb=document.querySelectorAll('#set-import .imp-item input');cb[1].click();const off=impPlan().list.length&&document.getElementById('set-import').innerText.match(/공연 일정으로[^\\d]*(\\d+)/)[1];document.querySelectorAll('#set-import .imp-item input')[1].click();const _r=location.reload;await applyImport();
          const rec=extraRecords(recKeyOf('show_hatshepsut2026')).map(r=>[r.date,r.time,r.seatZone,r.seatNumber,r.price]);
          const cu=getCustom().filter(c=>c.name==='가상의 공연').map(c=>[c.kind,c.date,c.time,c.place]);
          return [L, box.includes('붙여넣은 일정 2건')&&box.includes('못 읽은 항목 1건'), rec, cu, items, [cb.length, off]]}""", txt)
        check('붙여넣기 → 회차 예매 기록 + 🎭 내 일정 (미리보기에 한 줄씩)', got[:4] == [[['match', 'new'], ['show', 'new']], True, [['2026-12-26', '19:00', 'B', 3, 66000]], [['show', '2026-12-27', '14:00', '어느 극장']]] and len(got[4]) == 2 and '하트셉수트' in got[4][0] and '19:00' in got[4][0] and '예매 기록' in got[4][0] and '가상의 공연' in got[4][1] and '내 일정' in got[4][1] and got[5] == [2, '0'], got)
        await pg2.wait_for_timeout(2500)   # 넣은 뒤 새로 고침
        got = await e2("""async(txt)=>{openSettings();openPaste();document.getElementById('paste-text').value=txt;await readPaste();
          return impPlan().list.map(x=>x.state)}""", txt)
        check('같은 글을 다시 붙여도 새로 넣을 것 없음', got and all(x != 'new' for x in got), got)
        # 링크로 일정 받기 — #add=<JSON> 으로 열면 미리보기만 뜨고(저장 안 함) 주소에서 지운다 (11/19)
        import urllib.parse, base64
        js = '[{"name":"링크로 온 공연","date":"2027-02-01","time":"19:30","place":"어느 극장"}]'
        await e2("localStorage.clear()")
        await pg2.goto('about:blank'); await pg2.goto(BASE + '#add=' + urllib.parse.quote(js)); await pg2.wait_for_timeout(4000)   # 새로 여는 경우
        got = await e2("""[location.hash, document.getElementById('ov-settings').classList.contains('open'), !!_imp&&_imp.rows.map(r=>r['제목']+' '+r._ds+' '+r._time), getCustom().length]""")
        check('#add= 링크 → 미리보기 (저절로 저장 안 함, 주소에서 지움)', got == ['', True, ['링크로 온 공연 2027-02-01 19:30'], 0], got)
        await e2("location.hash='#add=" + base64.urlsafe_b64encode(js.encode()).decode().rstrip('=') + "'"); await pg2.wait_for_timeout(1500)
        got = await e2("""[location.hash, !!_imp&&_imp.rows.map(r=>r['제목'])]""")
        check('열려 있는 중에 온 링크(base64)도 받음', got == ['', ['링크로 온 공연']], got)
        # 내 일정 공연 카드 — 회차 카드와 같은 모양, 버튼은 [✏️ 수정] 하나·삭제는 수정 창 안 (A안 11/20) · 미정은 점선
        await e2("localStorage.clear()"); await pg2.reload(); await pg2.wait_for_timeout(2500)
        # 회차를 못 찾은 기록도 날짜 상세에 — 허브가 새 스케줄을 받기 전엔 '일정 없음'만 떴다 (샤이닝 2차, 11/26)
        got = await e2("""async()=>{
          saveApps([{id:'app_t',name:'시험앱',icon:'✨',color:'#555',scheduleUrl:'x',appUrl:'',kind:'data',recordsKey:'k_app_t'}]);
          schedules['app_t']=[{date:'2027-01-05',time:'20:00',a:'갑'}];
          localStorage.setItem('k_app_t', JSON.stringify([{id:1,date:'2027-01-08',time:'20:00',isBooked:false,seatZone:'C',seatNumber:3},{id:2,date:'2027-01-05',time:'20:00'}]));
          await openDay('2027-01-08'); const a=document.getElementById('sheet-content').innerText;
          await openDay('2027-01-05'); const b=document.getElementById('sheet-content').innerText;
          document.getElementById('ov-detail').classList.remove('open'); localStorage.removeItem('k_app_t'); saveApps([]); delete schedules['app_t'];
          return [a, b]}""")
        check('날짜 상세: 회차 못 찾은 기록도 보임(미정·아직 못 받음), 찾은 기록은 그대로',
              got and '시험앱' in got[0] and '미정' in got[0] and '아직 못 받았어요' in got[0] and '일정 없음' not in got[0] and '아직 못 받았어요' not in got[1], got)
        got = await e2("""async()=>{
          saveCustom([{id:7,kind:'show',date:'2026-12-21',time:'18:00',name:'알테르 에고',cast:'이재균, 손지윤',place:'예스24스테이지 3관',price:50500,vendor:'YES24',seatZone:'1',seatNumber:5,color:COLOR_PALETTE[0],photoIds:[]},
                      {id:8,kind:'show',date:'2026-12-22',time:'19:30',name:'레드북',color:COLOR_PALETTE[1],photoIds:[],tentative:true}]);
          await openDay('2026-12-21');
          const row=document.querySelector('#sheet-content .session-row');const t=row.innerText.split(String.fromCharCode(10)).join(' ').split(/ +/).join(' ');
          const btns=[...row.querySelectorAll('button')].map(b=>b.textContent.trim());
          await openCustomForm('2026-12-21',7);
          const f=[document.getElementById('cf-cast').value,document.getElementById('cf-place').value,document.getElementById('cf-price').value,document.getElementById('cf-vendor').value,
                   !document.getElementById('cf-del').hidden, document.getElementById('cf-cancel').hidden];
          document.getElementById('cf-tent').checked=true; await saveCustomEvent();
          const e7=getCustom().find(e=>e.id===7);
          await openDay('2026-12-22'); const tent=document.querySelector('#sheet-content .mark-tent')?.textContent;
          document.getElementById('ov-detail').classList.remove('open');
          currentYear=2026;currentMonth=11;if(getCalView&&getCalView()!=='month'){} renderCalendar();
          const chips=[...document.querySelectorAll('#cal-grid .sess-card.tentative')].map(c=>c.textContent.replace(/\s+/g,' ').trim());
          window.confirm=()=>true; await openCustomForm('2026-12-21',7); await deleteCustomEvent(7);
          return [t, btns, f, [e7.tentative, e7.cast, e7.place], tent, chips.length, getCustom().length, document.getElementById('ov-custom').classList.contains('open')]}""")
        check('내 일정 공연 카드: 출연·좌석·장소, 버튼은 ✏️ 수정 하나',
              got and '이재균 · 손지윤' in got[0] and '🎫 예매' in got[0] and '1열 5번' in got[0] and '예스24스테이지 3관 · 50,500원 · YES24' in got[0] and got[1] == ['✏️ 수정'], got)
        check('수정 창: 출연·장소·금액·예매처 채움, [삭제] 보이고 [취소] 숨김, 미정 저장', got and got[2] == ['이재균, 손지윤', '예스24스테이지 3관', '50500', 'YES24', True, True] and got[3] == [True, '이재균, 손지윤', '예스24스테이지 3관'], got)
        check('미정: 카드에 [미정], 달력 칩은 점선 2개', got and got[4] == '미정' and got[5] == 2, got)
        check('수정 창에서 삭제하면 지워지고 창이 닫힘', got and got[6] == 1 and got[7] is False, got)
        got = await e2("""async()=>{await ensureCatalog();openExtraRec('2026-12-26','19:00','show_hatshepsut2026','');document.getElementById('xr-tent').checked=true;await saveExtraRec();
          const r=extraRecords(recKeyOf('show_hatshepsut2026'))[0];const a=(getAttended()['2026-12-26']||[])[0];return [r&&r.tentative, a&&a.tentative]}""")
        check('허브 예매 기록 창의 미정 → 기록·달력에 미정', got == [True, True], got)
        got = await e2("""(()=>{localStorage.setItem('ikkisup_records',JSON.stringify([{id:'q',date:'2026-12-26',time:'19:00',isBooked:false,status:'관람'}]));
          return (getAttended()['2026-12-26']||[]).filter(r=>r.appId==='app_ikkisup').map(r=>r.tentative)})()""")
        check('전용 앱의 미정(예매 미확정) 기록도 허브에서 미정', got in ([True], []), got)
        got = await e2("""parsePaste('[{"name":"x","date":"2026-12-01","status":"미정"},{"name":"y","date":"2026-12-02"}]').rows.map(r=>r._tent)""")
        check('붙여넣기 "status": "미정"', got == [True, False], got)
        # 전용 페이지 작품도 내 기록이 있으면 [✏️ 수정] → 앱 수정 창(&edit=1) (사용자 에이전트 리뷰 11/20)
        got = await e2("""async()=>{await ensureCatalog();await addPresetById('app_ikkisup');renderFrames();
          const a=getApps().find(x=>x.id==='app_ikkisup');const R=(await fetch(a.scheduleUrl).then(r=>r.json())).filter(r=>r.date>=todayStr)[0];
          localStorage.setItem('ikkisup_records',JSON.stringify([{id:'e1',date:R.date,time:R.time,isBooked:false,status:'관람'}]));
          await openDay(R.date);const b=[...document.querySelectorAll('#sheet-content .jump-btn')].map(x=>x.textContent.trim());
          jumpToApp('app_ikkisup',R.date,R.time,true);const src=document.getElementById('frame-app_ikkisup').src;switchView('cal');
          return [b, /edit=1/.test(src)]}""")
        check('전용 페이지 작품 내 기록 → [✏️ 예매 수정][전용 페이지 ›], 전용 페이지는 &edit=1', got and got[0][:2] == ['✏️ 예매 수정', '전용 페이지 ›'] and got[1], got)
        # 전용 페이지 작품도 허브 기록 창으로 (11/27, 한 번만 볼 작품): 앱 기록 모양으로 저장, 고칠 때 앱 칸(별점 등)은 그대로
        got = await e2("""async()=>{const a=getApps().find(x=>x.id==='app_ikkisup');const rows=(await fetch(a.scheduleUrl).then(r=>r.json())).filter(r=>r.date>=todayStr);
          const R=rows[0], R2=rows.find(r=>r.date!==R.date);
          localStorage.setItem('ikkisup_records',JSON.stringify([{id:'e1',date:R.date,time:R.time,isBooked:false,status:'관람',rating:4,seatFloor:'1층',seatZone:'B',seatNumber:5}]));
          openExtraRec(R.date,R.time,'app_ikkisup','');const shown=document.getElementById('xr-zone').value, tent=document.getElementById('xr-tent').checked;
          document.getElementById('xr-tent').checked=false;document.getElementById('xr-price').value='60000';await saveExtraRec();
          const e1=JSON.parse(localStorage.getItem('ikkisup_records')).find(r=>r.id==='e1');
          openExtraRec(R2.date,R2.time,'app_ikkisup','');document.getElementById('xr-zone').value='';document.getElementById('xr-num').value='';await saveExtraRec();
          const n=JSON.parse(localStorage.getItem('ikkisup_records')).find(r=>r.date===R2.date);
          const roleKeys=Object.keys(R2).filter(k=>k!=='date'&&k!=='time');
          localStorage.removeItem('ikkisup_records');
          return [shown,tent,[e1.rating,e1.isBooked,e1.status,e1.seatFloor,e1.seatZone,e1.seatNumber,e1.price],
            n&&[n.isBooked,n.status,n.time===R2.time,roleKeys.every(k=>n[k]===R2[k])]]}""")
        check('전용 페이지 작품 허브 창 기록: 앱 모양·앱 칸 유지', got == ['1층 B', True, [4, True, '관람', '1층', 'B', 5, 60000], [True, '관람', True, True]], got)
        await e2("localStorage.clear()")
        check('페이지 오류 없음 (2)', not errs2, '; '.join(errs2)[:200])

        print('\nSUMMARY', sum(1 for r in R if r[1]), '/', len(R))
        await b.close()

asyncio.run(main())
