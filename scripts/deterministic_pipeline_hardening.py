#!/usr/bin/env python3
from pathlib import Path

ed = Path('cloudflare/newsdesk/src/editorial.js')
s = ed.read_text(encoding='utf-8')

marker = '''function sourceGroup(name, url = null) {
  try { if (url) return `host-${slugify(new URL(url).hostname.replace(/^www\\./, ""))}`; } catch (_) {}
  return slugify(name || "source") + "-reporting";
}
'''
insert = marker + '''function wireOrigin(item) {
  const text = `${item?.headline || ""} ${item?.description || ""} ${item?.excerpt || ""}`.toLowerCase().slice(0, 7000);
  if (/\\b(reuters|thomson reuters)\\b/.test(text)) return "wire-reuters";
  if (/\\b(associated press|ap news|the ap)\\b/.test(text)) return "wire-ap";
  if (/\\b(agence france-presse|afp)\\b/.test(text)) return "wire-afp";
  if (/\\b(ritzau|ritzau bureau)\\b/.test(text)) return "wire-ritzau";
  return null;
}
function evidenceSourceGroup(item) {
  return wireOrigin(item) || sourceGroup(item?.source, item?.final_url || item?.url);
}
'''
if marker not in s:
    raise SystemExit('sourceGroup marker missing')
s = s.replace(marker, insert, 1)

repls = [
('function evidenceGroups(items) { return [...new Set(items.filter(isEvidenceSource).map((x) => sourceGroup(x.source, x.final_url || x.url)))]; }',
 'function evidenceGroups(items) { return [...new Set(items.filter(isEvidenceSource).map(evidenceSourceGroup))]; }'),
('const independent = new Set(evidence.map((s) => sourceGroup(s.source, s.final_url || s.url)));',
 'const independent = new Set(evidence.map(evidenceSourceGroup));'),
('source_group: sourceGroup(s.source, url), authoritative_for:',
 'source_group: evidenceSourceGroup(s), authoritative_for:'),
]
for old, new in repls:
    if old not in s:
        raise SystemExit(f'editorial marker missing: {old[:80]}')
    s = s.replace(old, new, 1)
ed.write_text(s, encoding='utf-8')

idx = Path('cloudflare/newsdesk/src/index.js')
x = idx.read_text(encoding='utf-8')
old = 'const ttlHours = incoming.status === "approved" ? 36 : incoming.status === "watch" ? 2 : incoming.status === "drop" ? 12 : 6;'
new = '''const ttlHours = incoming.status === "approved" ? 36
        : incoming.status === "watch" && incoming.stage === "research" ? 18
        : incoming.status === "watch" ? 4
        : incoming.status === "drop" ? 12 : 6;'''
if old not in x:
    raise SystemExit('TTL marker missing')
x = x.replace(old, new, 1)
old = 'history.unshift({ generated_at: stampedAt, status: incoming.status, stage: incoming.stage || "approved", slug: incoming.slug || null, reason: incoming.reason || null, scan_fingerprint: incoming.scan_fingerprint || null, handled_signal_keys: incoming.handled_signal_keys || [] });'
new = '''history.unshift({ generated_at: stampedAt, status: incoming.status, stage: incoming.stage || "approved", slug: incoming.slug || null, reason: incoming.reason || null, scan_fingerprint: incoming.scan_fingerprint || null, handled_signal_keys: incoming.handled_signal_keys || [], category: incoming.audit?.assignment?.category || null, weight: incoming.audit?.assignment?.weight || null, ai_usage: incoming.ai_usage || null });'''
if old not in x:
    raise SystemExit('history marker missing')
x = x.replace(old, new, 1)
idx.write_text(x, encoding='utf-8')
print('deterministic hardening applied')
