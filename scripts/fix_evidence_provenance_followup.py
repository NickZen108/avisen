#!/usr/bin/env python3
from pathlib import Path
p=Path('cloudflare/newsdesk/src/editorial.js')
s=p.read_text(encoding='utf-8')
old='''function authoritativeEditorial(item) {
  const group = evidenceSourceGroup(item);
  return ["wire-reuters", "wire-ap", "wire-afp", "wire-ritzau"].includes(group);
}'''
new='''function authoritativeEditorial(item) {
  return Boolean(wireOrigin(item));
}'''
if old not in s:
    raise SystemExit('authoritativeEditorial anchor missing')
s=s.replace(old,new,1)
old='''  const sources = unique.map((item, i) => ({
    source_index: i,'''
new='''  const researchClusters = provenanceClusters(unique);
  unique.forEach((item, i) => { item.provenance_cluster = researchClusters[i]; });
  const sources = unique.map((item, i) => ({
    source_index: i,'''
if old not in s:
    raise SystemExit('research source anchor missing')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('Evidence provenance follow-up applied')
