import sys, os, asyncio, json
from playwright.async_api import async_playwright
BASE = 'http://127.0.0.1:8765/otk-test/'
R = []


def check(name, ok, info=''):
    R.append((name, bool(ok)))
    print(('PASS ' if ok else 'FAIL ') + name + (f'  [{info}]' if info else ''))


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel='chrome')
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, accept_downloads=True)
        pg = await ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        ev = pg.evaluate
        await pg.goto(BASE); await pg.wait_for_timeout(1500)
        # 준비: 허브 메모+사진, 앱 기록, 캐시, 다른 이름공간
        await ev('''(async()=>{
          const pid = await PhotoDB.put('data:image/png;base64,AAAA');
          localStorage.setItem(HUB_NS+'notes', JSON.stringify({'k1':{memo:'메모',photoIds:[pid]}}));
          localStorage.setItem(HUB_NS+'theme','dark');
          localStorage.setItem('ever_records', JSON.stringify([{id:1,date:'2026-11-10',time:'20:00'},{id:3,date:'2026-11-11',time:'20:00'}]));
          localStorage.setItem('ever_schedule', '[1,2,3]');
          localStorage.setItem(OTHER_NS+'apps', '[]');
          window._pid = pid; })()''')
        await ev("openSettings()"); await pg.wait_for_timeout(300)
        async with pg.expect_download() as di:
            await pg.click('button:has-text("사진까지 백업")')
        dl = await di.value
        path = os.path.join(sys.argv[1], dl.suggested_filename); await dl.save_as(path)
        d = json.load(open(path, encoding='utf-8'))
        check('파일 이름', dl.suggested_filename.startswith('mudi_backup_') and dl.suggested_filename.endswith('_photos.json'), dl.suggested_filename)
        check('허브 키는 접두어 없이', 'notes' in d['hub'] and 'theme' in d['hub'] and not any(k.startswith('hub_') or k.startswith('test_hub_') for k in d['hub']))
        check('앱 기록 O · 캐시·다른 허브 X', 'ever_records' in d['apps'] and 'ever_schedule' not in d['apps'] and not any('hub_' in k for k in d['apps']))
        check('사진 담김', d.get('photos') and len(d['photos']) >= 1)
        # 기기 상태를 바꾼다
        await ev('''localStorage.setItem('ever_records', JSON.stringify([{id:2,date:'2026-11-12',time:'20:00'},{id:9,date:'2026-11-10',time:'20:00'}]));
          localStorage.setItem(HUB_NS+'theme','light'); localStorage.removeItem(HUB_NS+'notes');''')
        # 합치기
        await pg.set_input_files('#restore-file', path); await pg.wait_for_timeout(400)
        check('복원 안내 상자', await ev("!!document.querySelector('#set-restore .rs-box')"))
        await pg.click('#set-restore button:has-text("합치기")'); await pg.wait_for_timeout(2500)
        ids = await ev("JSON.parse(localStorage.getItem('ever_records')).map(r=>r.id)")
        check('합치기: id 합집합, 같은 회차 다른 id 는 기기 유지', ids == [2, 9, 3], ids)
        check('합치기: 설정성 키는 기기 값', await ev("localStorage.getItem(HUB_NS+'theme')") == 'light')
        nid = await ev("JSON.parse(localStorage.getItem(HUB_NS+'notes')).k1.photoIds[0]")
        has = await ev(f"PhotoDB.getMany([{nid}]).then(m=>!!m[{nid}])")
        check('사진 새 id 로 바뀌고 읽힘', has, nid)
        # 되돌리기
        await ev("openSettings()"); await pg.wait_for_timeout(300)
        pg.once('dialog', lambda dg: asyncio.ensure_future(dg.accept()))
        await pg.click('#set-restore button:has-text("되돌리기")'); await pg.wait_for_timeout(2500)
        ids = await ev("JSON.parse(localStorage.getItem('ever_records')).map(r=>r.id)")
        check('되돌리기', ids == [2, 9] and await ev("localStorage.getItem(UNDO_KEY)") is None, ids)
        # 덮어쓰기
        await ev("openSettings()"); await pg.wait_for_timeout(300)
        await pg.set_input_files('#restore-file', path); await pg.wait_for_timeout(400)
        pg.once('dialog', lambda dg: asyncio.ensure_future(dg.accept()))
        await pg.click('#set-restore button:has-text("덮어쓰기")'); await pg.wait_for_timeout(2500)
        ids = await ev("JSON.parse(localStorage.getItem('ever_records')).map(r=>r.id)")
        check('덮어쓰기', ids == [1, 3] and await ev("localStorage.getItem(HUB_NS+'theme')") == 'dark', ids)
        check('다른 허브 키는 그대로', await ev("localStorage.getItem(OTHER_NS+'apps')") == '[]')

        # ── 다시 깨질 수 있는 경우 (리뷰 11/15) ──
        def write_bak(name, hub, device='other-device', apps=None):
            fp = os.path.join(sys.argv[1], name)
            json.dump({'app': 'mu:di', 'format': 1, 'at': '2026-11-15T00:00:00Z', 'device': device,
                       'hub': {k: json.dumps(v, ensure_ascii=False) for k, v in hub.items()}, 'apps': apps or {}},
                      open(fp, 'w', encoding='utf-8'), ensure_ascii=False)
            return fp

        async def restore(fp, mode):
            await ev("openSettings()"); await pg.wait_for_timeout(300)
            await pg.set_input_files('#restore-file', fp); await pg.wait_for_timeout(400)
            if mode == '덮어쓰기':
                pg.once('dialog', lambda dg: asyncio.ensure_future(dg.accept()))
            await pg.click(f'#set-restore button:has-text("{mode}")'); await pg.wait_for_timeout(2500)

        # ① 사진 없는 백업을 다른 기기에서 — 그 번호는 이 기기의 다른 사진이다. 버려야 한다
        real = await ev("PhotoDB.put('data:image/png;base64,BBBB')")
        await ev(f"localStorage.setItem(HUB_NS+'notes', JSON.stringify({{'mine':{{memo:'내 사진',photoIds:[{real}]}}}}))")
        fp = write_bak('bak_other.json', {'notes': {'k2': {'memo': '남의 메모', 'photoIds': [real]}}})
        await restore(fp, '합치기')
        n = await ev("JSON.parse(localStorage.getItem(HUB_NS+'notes'))")
        check('다른 기기 사진 없는 백업: 모르는 사진 번호는 버림', n.get('k2', {}).get('photoIds') == [] and n.get('mine', {}).get('photoIds') == [real], n)
        check('다른 기기 사진 없는 백업: 이 기기 사진은 그대로', await ev(f"PhotoDB.getMany([{real}]).then(m=>!!m[{real}])"))
        # 같은 기기 백업이면 번호를 그대로 쓴다
        dev = await ev("deviceId()")
        fp = write_bak('bak_same.json', {'notes': {'k3': {'memo': '같은 기기', 'photoIds': [real]}}}, device=dev)
        await restore(fp, '합치기')
        n = await ev("JSON.parse(localStorage.getItem(HUB_NS+'notes'))")
        check('같은 기기 사진 없는 백업: 사진 번호 유지', n.get('k3', {}).get('photoIds') == [real], n.get('k3'))

        # ② 합치기 — 같은 날 시간 없는 내 일정 두 개는 둘 다 남는다
        await ev("localStorage.setItem(HUB_NS+'custom', JSON.stringify([{id:1,date:'2026-11-20',time:'',kind:'etc',name:'출장',photoIds:[]}]))")
        fp = write_bak('bak_custom.json', {'custom': [{'id': 2, 'date': '2026-11-20', 'time': '', 'kind': 'etc', 'name': '생일', 'photoIds': []}]})
        await restore(fp, '합치기')
        names = await ev("JSON.parse(localStorage.getItem(HUB_NS+'custom')).map(e=>e.name)")
        check('합치기: 같은 날 다른 내 일정 둘 다 남음', sorted(names) == ['생일', '출장'], names)

        # ③ 되돌리기 — 복원 뒤 기록이 바뀌었으면 알린다, 하루 지나면 없어진다
        await ev("localStorage.setItem('ever_records', JSON.stringify([{id:77,date:'2026-11-21',time:'20:00'}]))")
        msgs = []
        await ev("openSettings()"); await pg.wait_for_timeout(300)
        pg.once('dialog', lambda dg: (msgs.append(dg.message), asyncio.ensure_future(dg.dismiss())))
        await pg.click('#set-restore button:has-text("되돌리기")'); await pg.wait_for_timeout(500)
        check('되돌리기: 복원 뒤 바뀐 기록 경고', msgs and '바뀐 기록' in msgs[0], msgs)
        check('되돌리기 취소하면 그대로', await ev("JSON.parse(localStorage.getItem('ever_records'))[0].id") == 77)
        await ev("(()=>{const u=JSON.parse(localStorage.getItem(UNDO_KEY)); u.at=new Date(Date.now()-25*3600e3).toISOString(); localStorage.setItem(UNDO_KEY, JSON.stringify(u)); renderRestoreBox();})()")
        check('되돌리기: 하루 지나면 상자·보관본 없음', await ev("!document.querySelector('#set-restore .rs-box') && localStorage.getItem(UNDO_KEY)===null"))
        await ev("localStorage.removeItem(HUB_NS+'custom')")
        # 정리
        await ev("Object.keys(localStorage).filter(k=>k.startsWith('ever_')||k.startsWith(OTHER_NS)||k===UNDO_KEY).forEach(k=>localStorage.removeItem(k))")
        check('페이지 오류 없음', not errs, '; '.join(errs)[:200])
        print('\nSUMMARY', sum(1 for r in R if r[1]), '/', len(R))
        await b.close()

asyncio.run(main())
