# mu:di 허브 — 다른 앱 기록(CSV) 가져오기 검사. 실행: python _tests/pw_import.py <스크린샷 폴더>
# 샘플은 가짜 데이터(_tests/import_sample.csv) — 실제 기록 파일은 개인 정보라 저장소에 넣지 않는다.
# 이끼숲 앱 src(D:\workspace\ikkisup2026)를 같은 로컬 서버에서 열어 앱 쪽 기록도 본다.
import asyncio, json, os, sys
from playwright.async_api import async_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
CSV = os.path.join(HERE, 'import_sample.csv')
R = []
def check(n, ok, info=''):
    R.append(ok); print(('PASS ' if ok else 'FAIL ') + n + (f'  [{info}]' if info else ''))


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel='chrome')
        ctx = await b.new_context(viewport={'width': 390, 'height': 900})
        pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
        ev = pg.evaluate
        await pg.goto('http://127.0.0.1:8765/otk-test/'); await pg.wait_for_timeout(1000)
        await ev("localStorage.clear()"); await pg.reload(); await pg.wait_for_timeout(4000)
        await ev("openSettings()"); await pg.wait_for_timeout(300)
        await pg.set_input_files('#import-file', CSV); await pg.wait_for_timeout(6000)
        check('기본 기간은 올해부터', await ev("_imp.range") == 'year')
        await ev("_imp.range='all';renderImport()"); await pg.wait_for_timeout(300)
        await (await pg.query_selector('#set-import')).screenshot(path=os.path.join(OUT, 'import_preview.png'))
        plan = await ev("impPlan().list.map(x=>[x.r['제목'],x.ds,x.kind,x.state,x.w?x.w.id:''])")
        m = [x for x in plan if x[2] == 'match']
        check('빈 줄 3개는 넣지 않음', await ev("impPlan().empty") == 3)
        check('이끼숲·소크라테스·사춘기는 회차에 맞춤', {'이끼숲', '소크라테스 패러독스', '뮤지컬 〈사춘기〉'} <= {x[0] for x in m}, m)
        check('같은 작품 다른 시즌(곤 투모로우 2016·2023)은 공연 일정', all(x[2] == 'show' for x in plan if x[0] == '곤 투모로우'))
        check('띄어쓰기 다른 제목도 작품 인식(여신님이 보고계셔)', any(x[0] == '여신님이 보고계셔' and x[4] for x in plan))
        check('아직 확인 안 한 전용 앱(V에버애프터)은 공연 일정', any(x[0] == 'V 에버 애프터' and x[2] == 'show' for x in plan))
        await ev("_imp.range='year';renderImport()")
        check('올해부터 고르면 지난해 줄은 기간 밖', await ev("impPlan().out") > 0)
        await ev("_imp.range='all';renderImport()")
        await pg.click('#set-import .rs-btns .pri'); await pg.wait_for_timeout(5000)
        ik = await ev("JSON.parse(localStorage.getItem('ikkisup_records')||'[]')")
        check('이끼숲 앱 기록에 들어감(좌석·가격·메모·캐스팅)', any(r['date'] == '2026-12-09' and r.get('seatZone') == 'A' and r.get('seatNumber') == 16
                                                    and r.get('price') == 45000 and '두 번째 관람' in r.get('memo', '') and r.get('marco') for r in ik))
        check('1층 B구역 2열 7번 → 앱 1층 2열 7번 + 메모 B구역', any(r.get('seatFloor') == '1층' and r.get('seatZone') == '2' and r.get('seatNumber') == 7 and 'B구역' in r.get('memo', '') for r in ik))
        so = await ev("extraRecords(recKeyOf('show_socrates2026'))")
        check('정보만 작품(소크라테스) 예매 기록 + 메모', any(r['date'] == '2026-11-28' and r.get('seatZone') == 'D' and r.get('seatNumber') == 12 for r in so)
              and '친구 양도' in json.dumps(await ev("getNotes()"), ensure_ascii=False))
        check('예매만으로는 ♥ 안 누름', not await ev("getHearts().works.includes('show_socrates2026')"))
        cu = await ev("getCustom()")
        g = next((c for c in cu if c['name'] == '가상의 연극'), {})
        check('없는 작품은 🎭 공연 일정(좌석·여러 줄 메모)', g.get('kind') == 'show' and g.get('seatZone') == 'B' and '여러 줄 메모도' in g.get('comment', ''), g)
        check('못 읽는 좌석은 메모에 원문', any(c['name'] == '없는 뮤지컬' and '비지정 3열 중앙' in c.get('comment', '') for c in cu))
        # 다시 가져오기
        await ev("openSettings()"); await pg.set_input_files('#import-file', CSV); await pg.wait_for_timeout(6000)
        await ev("_imp.range='all';renderImport()")
        st = await ev("(()=>{const L=impPlan().list;return {nw:L.filter(x=>x.state==='new').length, again:L.filter(x=>x.state==='again').length}})()")
        check('같은 파일 다시 가져오면 새로 넣을 것 0', st['nw'] == 0 and st['again'] > 0, st)
        await ev("saveCustom(getCustom().filter(c=>c.name!=='가상의 연극'))")
        await ev("_imp.take.again=false;applyImport()"); await pg.wait_for_timeout(500)
        check('지운 것은 저절로 안 살아남', not await ev("getCustom().some(c=>c.name==='가상의 연극')"))
        check('가져오기 되돌리기 보관', await ev("!!localStorage.getItem(UNDO_KEY)"))
        # 직접 넣어 둔 같은 회차는 '이미 기록 있음'
        await ev("localStorage.removeItem(IMPORT_KEY)")
        await ev("_imp.range='all';renderImport()")
        check('직접 입력과 같은 회차는 이미 기록 있음', await ev("impPlan().list.filter(x=>x.state==='have').length") > 0)
        await ev("saveCustom(getCustom().concat([{id:1,kind:'show',date:'2021-10-03',time:'19:00',name:'없는 뮤지컬',color:'#888',photoIds:[]}]))")
        check('내 일정에 같은 날·시간·이름이 있으면 건너뜀', await ev("impPlan().list.find(x=>x.r['제목']==='없는 뮤지컬').state") == 'have')
        await ev("saveCustom(getCustom().concat([{id:2,kind:'show',date:'2025-05-25',time:'14:00',name:'가상콘서트',color:'#888',photoIds:[]},{id:3,kind:'show',date:'2018-05-07',time:'14:00',name:'가상의 연극!',color:'#888',photoIds:[]}]))")
        check('띄어쓰기만 다르면 같은 이름(가상 콘서트=가상콘서트)', await ev("impPlan().list.find(x=>x.r['제목']==='가상 콘서트').state") == 'have')
        check('띄어쓰기 말고 다르면 다른 이름(가상의 연극≠가상의 연극!)', await ev("impPlan().list.find(x=>x.r['제목']==='가상의 연극').state") != 'have')
        await ev("saveCustom(getCustom().filter(e=>!(e.date==='2016-08-13')).concat([{id:4,kind:'show',date:'2016-08-13',time:'19:00',name:'곤 투모로우',color:'#888',photoIds:[]}]))")
        check('같은 날 같은 이름이라도 시간이 다르면(낮·밤) 다른 공연', await ev("impPlan().list.find(x=>x.r['제목']==='곤 투모로우'&&x.ds==='2016-08-13').state") != 'have')
        # 이끼숲 앱을 직접 열어 본다 (같은 주소라 같은 저장소)
        ap = await ctx.new_page(); aerr = []; ap.on('pageerror', lambda e: aerr.append(str(e)))
        await ap.goto('http://127.0.0.1:8765/ikkisup2026/'); await ap.wait_for_timeout(3000)
        check('이끼숲 앱이 오류 없이 열림', not aerr, '; '.join(aerr)[:200])
        check('이끼숲 앱 화면에 가져온 좌석', 'A열 16번' in await ap.evaluate("document.body.innerText"))
        await ap.screenshot(path=os.path.join(OUT, 'ikkisup_after_import.png'))
        await ev("localStorage.clear()")
        check('허브 페이지 오류 없음', not errs, '; '.join(errs)[:200])
        print('\nSUMMARY', sum(R), '/', len(R))
        await b.close()
asyncio.run(main())
