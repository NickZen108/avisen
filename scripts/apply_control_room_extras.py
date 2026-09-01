#!/usr/bin/env python3
import json
from pathlib import Path

page_path = Path('docs/kontrolrum/index.html')
script_path = Path('docs/kontrolrum/control-room-tabs.js')
feedback_path = Path('reports/editorial/pipeline-feedback.json')
if not page_path.exists():
    raise SystemExit('docs/kontrolrum/index.html missing; run build_control_room.py first')
if not script_path.exists():
    raise SystemExit('docs/kontrolrum/control-room-tabs.js missing')
text = page_path.read_text(encoding='utf-8')
script = script_path.read_text(encoding='utf-8')
feedback = {}
if feedback_path.exists():
    try: feedback = json.loads(feedback_path.read_text(encoding='utf-8'))
    except Exception: feedback = {}
marker = '<!-- CONTROL_ROOM_TABS -->'
if marker not in text:
    if '</body>' not in text:
        raise RuntimeError('control room has no closing body tag')
    payload = json.dumps(feedback, ensure_ascii=False).replace('</', '<\\/')
    inline = f'{marker}<script>window.__MT_PIPELINE_FEEDBACK__={payload};</script><script>\n{script}\n</script>'
    text = text.replace('</body>', inline + '</body>', 1)
    page_path.write_text(text, encoding='utf-8')
print('Control room management tabs and pipeline feedback attached inline')
