#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'; CFG=ROOT/'config'/'site.json'; OLD='https://nickzen108.github.io/avisen'
def main():
    base=json.loads(CFG.read_text(encoding='utf-8'))['base_url'].rstrip('/')
    for p in [DOCS/'index.html',DOCS/'sitemap.xml',DOCS/'news-sitemap.xml',*sorted((DOCS/'artikler').glob('*.html'))]:
        if not p.exists(): continue
        text=p.read_text(encoding='utf-8').replace(OLD,base)
        p.write_text(text,encoding='utf-8')
    (DOCS/'robots.txt').write_text(f'User-agent: *\nAllow: /\nDisallow: /kontrolrum/\nSitemap: {base}/sitemap.xml\nSitemap: {base}/news-sitemap.xml\n',encoding='utf-8')
    print('SEO surface fixed for',base)
if __name__=='__main__': main()
