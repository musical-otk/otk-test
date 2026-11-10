import sys, os, asyncio, json
from playwright.async_api import async_playwright
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
BASE = 'http://127.0.0.1:8765/otk-test/'
R = []
def check(name, ok, info=''):
    R.append((name, bool(ok), info)); print(('PASS ' if ok else 'FAIL ') + name + (f'  [{info}]' if info else ''))

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel='chrome')
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
        pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
        ev = pg.evaluate
        async def fresh():
            await pg.goto(BASE); await pg.wait_for_timeout(300)
            await ev("localStorage.clear()"); await pg.reload(); await pg.wait_for_timeout(1500)
            await ev("discoverApps(true)"); await pg.wait_for_timeout(5000)
        await fresh()
        pid = lambda n: f"allPresets().find(p=>p.name==='{n}').id"

        # 1. 처음 쓰는 사람 안내
        check('처음 사용자: 안내 보임', await ev("!document.getElementById('hub-empty').hidden || getHearts().works.length>0"),
              json.dumps(await ev("getHearts()"), ensure_ascii=False))

        # 2. 정보만 작품 — 찾기에서 회차 눌렀다 닫기 → 안 들어감, 저장 → 들어감
        await ev("openSearch()"); await pg.fill('#srch-q', '소크'); await pg.wait_for_timeout(2500); await ev("renderSearch()")
        await pg.click('.flt-hit:has-text("소크라테스")')
        await pg.click('.srch-sess .srch-row >> nth=0'); await pg.wait_for_timeout(400)
        check('회차 상세 창 — 캐스팅·기록 버튼', await ev("document.getElementById('ov-ev').classList.contains('open') && !!document.querySelector('#ev-sheet-body .ev-cast-row') && !!document.querySelector('#ev-sheet-body .ev-foot .ev-btn')"))
        await pg.screenshot(path=os.path.join(OUT, 'sess_sheet.png'))
        await pg.click('#ev-sheet-body .ev-foot .ev-btn'); await pg.wait_for_timeout(400)
        check('예매 창 열림(달력에 없는 작품)', await ev("document.getElementById('ov-extra-rec').classList.contains('open')"))
        await ev("closeExtraRec()")
        check('닫기만 하면 달력에 안 들어감', not await ev("getApps().some(a=>a.name==='소크라테스 패러독스')"))
        await pg.click('.srch-sess .srch-row >> nth=0'); await pg.wait_for_timeout(300)
        await pg.click('#ev-sheet-body .ev-foot .ev-btn'); await pg.wait_for_timeout(300)
        await pg.fill('#xr-zone', 'C'); await pg.fill('#xr-num', '3')
        await ev("saveExtraRec()"); await pg.wait_for_timeout(3000)
        check('저장하면 기록 (♥ 없이)', await ev("!getHearts().works.includes('show_socrates2026') && extraRecords(recKeyOf('show_socrates2026')).length===1"))
        check('찾기 회차에 🎫 표시', '예매' in await ev("document.getElementById('srch-results').innerText"))
        # 양도 → 달력 반영
        first = await ev("extraRecords(recKeyOf('show_socrates2026'))[0]")
        await ev(f"openExtraRec('{first['date']}','{first['time']}','show_socrates2026')"); await pg.wait_for_timeout(300)
        await pg.check('#xr-trans'); await ev("saveExtraRec()"); await pg.wait_for_timeout(800)
        check('양도로 바꾸면 transferred', await ev(f"(getAttended()['{first['date']}']||[]).some(r=>r.appId==='show_socrates2026'&&r.transferred)"))
        await ev(f"openExtraRec('{first['date']}','{first['time']}','show_socrates2026')"); await pg.wait_for_timeout(300)
        await ev("deleteExtraRec()"); await pg.wait_for_timeout(500)
        check('기록 삭제', await ev("extraRecords(recKeyOf('show_socrates2026')).length===0"))
        await ev("closeSearch()")

        # 3. 기타 — 기본으로 꺼져 있다 / 넣은 뒤 같은 날 같은 시각 두 공연이 섞이지 않는지
        check('기타는 기본으로 꺼져 있음', not await ev("getApps().some(a=>a.id===EXTRA_ID)"))
        await ev("addExtraApp()"); await pg.wait_for_timeout(2000)
        await ev("""(() => { const r = schedules[EXTRA_ID];
          r.push({date:'2026-12-31',time:'20:00',cast1:'가',_show:'A콘',_showId:'aaa'}, {date:'2026-12-31',time:'20:00',cast1:'나',_show:'B콘',_showId:'bbb'}); })()""")
        await ev("openExtraRec('2026-12-31','20:00',EXTRA_ID,'aaa')"); await ev("saveExtraRec()"); await pg.wait_for_timeout(800)
        hitA = await ev("(getAttended()['2026-12-31']||[]).some(r=>recHit(r,EXTRA_ID,{time:'20:00',_showId:'aaa'}))")
        hitB = await ev("(getAttended()['2026-12-31']||[]).some(r=>recHit(r,EXTRA_ID,{time:'20:00',_showId:'bbb'}))")
        check('기타: A만 예매로 표시, B는 아님', hitA and not hitB, f'A={hitA} B={hitB}')
        await ev("closeOverlays()")

        # 4. 필터 끈 상태 + 내 기록 모드 + 주간
        await ev(f"heartWork({pid('V에버애프터')})"); await pg.wait_for_timeout(2500)
        await ev("localStorage.setItem('ever_records', JSON.stringify([{id:'r1',date:'2026-11-14',time:'15:00'}]))")
        await ev(f"toggleWorkOn({pid('V에버애프터')})")
        await ev("setCalMode('mine'); setCalView('week'); weekStart = sundayOf(new Date('2026-11-14T00:00:00')); renderCalendar()")
        wk = await ev("document.getElementById('cal-week').innerText")
        check('필터로 꺼도 내 기록 회차는 주간에 남음', '15:00' in wk and 'V에버' in wk)
        await ev("openDay('2026-11-14')"); await pg.wait_for_timeout(500)
        check('날짜 상세에도 남음', 'V에버' in await ev("document.getElementById('sheet-content').innerText"))
        await ev("closeOverlays(); clearFilter(); setCalMode('all'); setCalView('month')")

        # 5. 사진만 있는 회차 (필터 밖) — 날짜 상세에 보이는지
        await ev(f"toggleWorkOn({pid('V에버애프터')})")
        await ev(f"(() => {{ const n = getNotes(); n[noteKeyFor({pid('V에버애프터')}, '2026-11-15', {{time:'14:00'}})] = {{memo:'', photoIds:[999]}}; saveNotes(n); }})()")
        await ev("openDay('2026-11-15')"); await pg.wait_for_timeout(500)
        check('사진만 있는 회차가 날짜 상세에 나옴', '14:00' in await ev("document.getElementById('sheet-content').innerText"))
        await ev("closeOverlays(); clearFilter()")

        # 6. 앱 딥링크
        await ev(f"jumpToApp({pid('V에버애프터')}, '2026-11-14', '15:00')"); await pg.wait_for_timeout(500)
        src = await ev(f"document.getElementById('frame-'+{pid('V에버애프터')}).src")
        check('앱에서 보기: 그 회차 주소로 열림', 'date=2026-11-14' in src and 'time=15' in src, src[-40:])
        await pg.click('.header-title'); await pg.wait_for_timeout(300)
        check('m.diary → 달력', await ev("currentView==='cal'"))

        # 7. 종료 작품 — 탭 자동 숨김, +N 에서 열기
        await ev(f"heartWork({pid('아웃캐스트')})"); await pg.wait_for_timeout(3000)
        tabs = await ev("[...document.querySelectorAll('#app-tabs .app-btn')].map(b=>b.textContent.trim())")
        check('종료 작품은 탭에 없음, +N 있음', not any('아웃캐스트' in x for x in tabs) and any(x.startswith('+') for x in tabs), str(tabs))
        await ev("openHiddenApps()"); await pg.wait_for_timeout(200)
        check('+N 목록에 아웃캐스트', '아웃캐스트' in await ev("document.getElementById('hidden-app-list').innerText"))
        await ev("closeHiddenApps()")

        # 8. '기타' 빼기 → 다시 열어도 안 살아남 / 찾기에서 다시 넣기
        await ev("unheartWork(EXTRA_ID)"); await pg.reload(); await pg.wait_for_timeout(3500)
        # 앞에서 기타 예매를 하나 저장했으니 ♥ 를 빼도 예매 회차만 남는다(탭·♥ 없이) — 11/7 결정과 같게
        check('기타 ♥ 빼면 예매 회차만 남음', await ev("(getApps().find(a=>a.id===EXTRA_ID)||{}).viaActor===true && !getHearts().works.includes(EXTRA_ID)"))
        await ev("heartWork(EXTRA_ID)"); await pg.wait_for_timeout(1500)
        check('기타 다시 넣기', await ev("getApps().some(a=>a.id===EXTRA_ID) && getHearts().works.includes(EXTRA_ID)"))

        # 9. 동기화
        await ev("syncNow(true)"); await pg.wait_for_timeout(4000)
        check('동기화 후 오류 없음', not errs, '; '.join(errs)[:120])

        # 10. v1 필터 옮기기
        await ev(f"""(() => {{ localStorage.removeItem(HUB_NS+'hearts'); _hearts=null;
          localStorage.setItem(HUB_NS+'filter', JSON.stringify({{actors:['이한솔'], apps:[]}})); }})()""")
        h = await ev("getHearts()")
        check('v1 필터 → 관심 배우', '이한솔' in h['actors'], json.dumps(h, ensure_ascii=False))

        # 11. 밝은 테마 화면
        await ev("applyTheme('light'); goToToday()"); await pg.wait_for_timeout(400)
        await pg.screenshot(path=f'{OUT}/full_light_month.png')
        await ev("setCalView('week')"); await pg.wait_for_timeout(300)
        await pg.screenshot(path=f'{OUT}/full_light_week.png', full_page=True)

        # 12. 관심함 → 자세히 → 하트 빼기 → 목록 복귀
        await ev("showHearts()"); await pg.wait_for_timeout(1000)
        await pg.click(".hp-row:has-text('V에버애프터')"); await pg.wait_for_timeout(400)
        await pg.click('#srch-results .srch-heart'); await pg.wait_for_timeout(600)
        check('자세히에서 빼면 목록으로', await ev("_srchSel===null || document.getElementById('srch-results').innerText.includes('♡')"))

        # 설정 (⚙️)
        await ev("closeSearch && closeSearch()"); await pg.wait_for_timeout(200)
        check('상단 ⚙️ 있고 🔄 없음', await ev("!!document.getElementById('set-btn') && !document.querySelector('.header #sync-btn')"))
        await pg.click('#set-btn'); await pg.wait_for_timeout(300)
        check('설정 시트 열림', await ev("document.getElementById('ov-settings').classList.contains('open')"))
        t0 = await ev("getTheme()"); await pg.click('#ov-settings .set-row'); await pg.wait_for_timeout(200)
        check('설정에서 테마 바뀜', await ev("getTheme()") != t0)
        await pg.click('#ov-settings .set-row'); await pg.wait_for_timeout(200)
        await pg.wait_for_timeout(500)
        check('설정에 버전 표시', 'mu:di v' in (await ev("document.getElementById('set-ver').textContent")))
        await pg.screenshot(path=os.path.join(OUT, 'settings.png'), full_page=True)
        pg.once('popup', lambda pp: None)
        async with pg.context.expect_page() as npi:
            await pg.click('#ov-settings button:has-text("요청")')
        np_ = await npi.value
        check('요청 폼 새 창', 'docs.google.com/forms' in np_.url, np_.url[:80]); await np_.close()
        await pg.click('#ov-settings button:has-text("기록 새로고침")'); await pg.wait_for_timeout(300)
        await pg.click('#sync-btn'); await pg.wait_for_timeout(3000)
        check('공연 정보 새로 받기 끝남', await ev("!_syncing"))
        await pg.wait_for_timeout(4000)
        check('첫 받기 → 비교 기준 저장', await ev("!!localStorage.getItem(SNAP_KEY) && JSON.parse(localStorage.getItem(DIFF_KEY)).first===true"))
        # 지난 지문을 일부러 바꿔 둔다: 한 작품 캐스팅 1칸, 한 회차 빼기, 이벤트 1개 빼기, 한 작품 통째로 빼기(새 작품)
        info = await ev('''(()=>{const S=JSON.parse(localStorage.getItem(SNAP_KEY));const ids=Object.keys(S).filter(i=>Object.keys(S[i].sess).length>2&&Object.keys(S[i].ev).length);
          const a=ids[0],b=ids[1];const ks=Object.keys(S[a].sess);S[a].sess[ks[0]]=S[a].sess[ks[0]].replace(/=([^|]+)/,'=옛배우');delete S[a].sess[ks[1]];
          delete S[a].ev[Object.keys(S[a].ev)[0]];delete S[b];localStorage.setItem(SNAP_KEY,JSON.stringify(S));return [a,b];})()''')
        await pg.click('#sync-btn'); await pg.wait_for_timeout(6000)
        d = await ev("JSON.parse(localStorage.getItem(DIFF_KEY))")
        w = (d.get('works') or [{}])[0]
        check('비교: 캐스팅·새 회차·새 이벤트', w.get('id')==info[0] and len(w.get('cast',[]))==1 and len(w.get('added',[]))==1 and len(w.get('ev',[]))==1, json.dumps(w, ensure_ascii=False)[:200])
        check('비교: 새 작품 섹션', info[1] in await ev("Object.keys(JSON.parse(localStorage.getItem(NEWW_KEY)))") and await ev("!!document.querySelector('#set-new .sd-new')"))
        await pg.screenshot(path=os.path.join(OUT, 'settings_diff.png'), full_page=True)
        check('페이지 오류 없음', not errs, '; '.join(errs)[:200])
        print('\nSUMMARY', sum(1 for r in R if r[1]), '/', len(R))
        await b.close()

asyncio.run(main())
