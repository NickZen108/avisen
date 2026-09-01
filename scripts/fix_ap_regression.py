#!/usr/bin/env python3
from pathlib import Path
p=Path('cloudflare/newsdesk/src/editorial.js')
s=p.read_text(encoding='utf-8')
old='''  if (host === "apnews.com" || host.endsWith(".apnews.com") || ["ap", "associated press", "ap news"].includes(source)) return "ap";'''
new='''  if (host === "apnews.com" || host.endsWith(".apnews.com") || source === "ap" || source === "associated press" || source === "ap news") return "ap";'''
if old not in s:
    raise SystemExit('AP wire anchor missing')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('AP regression compatibility applied')
