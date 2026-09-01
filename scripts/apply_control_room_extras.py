#!/usr/bin/env python3
from pathlib import Path

path = Path('docs/kontrolrum/index.html')
if not path.exists():
    raise SystemExit('docs/kontrolrum/index.html missing; run build_control_room.py first')
text = path.read_text(encoding='utf-8')
tag = '<script src="./control-room-tabs.js?v=1"></script>'
if tag not in text:
    if '</body>' not in text:
        raise RuntimeError('control room has no closing body tag')
    text = text.replace('</body>', tag + '</body>', 1)
    path.write_text(text, encoding='utf-8')
print('Control room management tabs attached')
