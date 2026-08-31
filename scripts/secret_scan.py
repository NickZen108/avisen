#!/usr/bin/env python3
"""Fail CI on high-confidence credentials committed to tracked text files."""
from __future__ import annotations
import re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PATTERNS=[
 ('private key',re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
 ('github token',re.compile(r'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b')),
 ('github fine-grained token',re.compile(r'\bgithub_pat_[A-Za-z0-9_]{40,}\b')),
 ('slack token',re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{20,}\b')),
 ('secret assignment',re.compile(r'(?i)\b(?:SUPABASE_SECRET_KEY|CLOUDFLARE_API_TOKEN|CLOUDFLARE_ACCOUNT_TOKEN|SERVICE_ROLE_KEY)\s*[:=]\s*["\']?[A-Za-z0-9._-]{18,}')),
]
SKIP_SUFFIX={'.png','.jpg','.jpeg','.webp','.gif','.ico','.zip','.pdf'}
def main():
 files=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).split(b'\0');hits=[]
 for raw in files:
  if not raw:continue
  rel=raw.decode('utf-8','replace');p=ROOT/rel
  if p.suffix.lower() in SKIP_SUFFIX or not p.is_file() or p.stat().st_size>2_000_000:continue
  try:text=p.read_text(encoding='utf-8')
  except Exception:continue
  for name,pat in PATTERNS:
   for m in pat.finditer(text):
    line=text.count('\n',0,m.start())+1;hits.append(f'{rel}:{line}: {name}')
 if hits:
  print('SECRET SCAN: FAIL');[print('-',x) for x in hits];return 1
 print('SECRET SCAN: PASS');return 0
if __name__=='__main__':sys.exit(main())
