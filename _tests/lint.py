# index.html 의 큰 <script> 를 꺼내 deno lint 로 정적 검사한다. 줄 번호는 index.html 그대로.
# 실행: python _tests/lint.py   (deno 필요)
import re, subprocess, sys, tempfile
from pathlib import Path

html = (Path(__file__).parent.parent / 'index.html').read_text(encoding='utf-8')
body = max(re.finditer(r'<script>(.*?)</script>', html, re.S), key=lambda m: len(m.group(1)))
js = '\n' * html[:body.start(1)].count('\n') + body.group(1)
with tempfile.TemporaryDirectory() as d:
    f = Path(d) / 'hub.js'; f.write_text(js, encoding='utf-8')
    # 허브는 함수 선언을 전역에 두고 onclick 에서 부른다 — 쓰지 않는 변수·빈 catch 같은 건 일부러 끈다
    r = subprocess.run(['deno', 'lint', '--rules-exclude=no-unused-vars,no-inner-declarations,no-empty,prefer-const,no-window,no-window-prefix', str(f)],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    print(re.sub(r'\x1b\[[0-9;]*m', '', r.stdout + r.stderr).replace(str(f), 'index.html'))
    sys.exit(r.returncode)
