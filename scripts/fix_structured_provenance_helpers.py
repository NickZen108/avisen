#!/usr/bin/env python3
from pathlib import Path

p = Path('cloudflare/newsdesk/src/editorial.js')
s = p.read_text(encoding='utf-8')
start = s.index('function metaContent(')
end = s.index('function provenanceClusters(', start)
block = r'''function metaContent(html, key) {
  const wanted = String(key || "").toLowerCase();
  const tags = String(html || "").match(/<meta[^>]*>/gi) || [];
  for (const tag of tags) {
    const lower = tag.toLowerCase();
    const names = [`name="${wanted}"`, `name='${wanted}'`, `property="${wanted}"`, `property='${wanted}'`];
    if (!names.some((x) => lower.includes(x))) continue;
    const m = tag.match(/content=["']([^"']+)["']/i);
    if (m?.[1]) return stripHtml(m[1]).trim();
  }
  return null;
}
function canonicalUrl(html, baseUrl) {
  const tags = String(html || "").match(/<link[^>]*>/gi) || [];
  for (const tag of tags) {
    if (!tag.toLowerCase().includes("canonical")) continue;
    const m = tag.match(/href=["']([^"']+)["']/i);
    if (!m?.[1]) continue;
    try { return new URL(m[1], baseUrl).href; } catch (_) {}
  }
  return null;
}
function jsonLdField(html, field) {
  const rawHtml = String(html || "");
  const lower = rawHtml.toLowerCase();
  let cursor = 0;
  for (let count = 0; count < 8; count++) {
    const open = lower.indexOf("<script", cursor); if (open < 0) break;
    const tagEnd = lower.indexOf(">", open); if (tagEnd < 0) break;
    const close = lower.indexOf("</script>", tagEnd + 1); if (close < 0) break;
    const tag = lower.slice(open, tagEnd + 1);
    cursor = close + 9;
    if (!tag.includes("application/ld+json")) continue;
    try {
      const raw = JSON.parse(rawHtml.slice(tagEnd + 1, close));
      const nodes = Array.isArray(raw) ? raw : (raw?.['@graph'] || [raw]);
      for (const node of nodes) {
        const value = node?.[field];
        if (typeof value === "string" && value.trim()) return value.trim();
        if (Array.isArray(value)) {
          for (const x of value) if (typeof x?.name === "string" && x.name.trim()) return x.name.trim();
        }
        if (value && typeof value === "object" && typeof value.name === "string" && value.name.trim()) return value.name.trim();
      }
    } catch (_) {}
  }
  return null;
}
function provenanceMetadata(html, pageUrl) {
  const byline = metaContent(html, "author") || metaContent(html, "article:author") || metaContent(html, "parsely-author") || metaContent(html, "dc.creator") || jsonLdField(html, "author");
  const publisher = metaContent(html, "publisher") || metaContent(html, "article:publisher") || jsonLdField(html, "publisher");
  const canonical_url = canonicalUrl(html, pageUrl);
  return { byline: byline || null, publisher: publisher || null, canonical_url };
}
function normalizedOriginName(value) {
  return String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}
function containsOriginToken(value, token) {
  return ` ${normalizedOriginName(value)} `.includes(` ${token} `);
}
function metadataWireOrigin(item) {
  const text = `${item?.provenance_meta?.byline || ""} ${item?.provenance_meta?.publisher || ""}`;
  const n = normalizedOriginName(text);
  if (containsOriginToken(n, "reuters") || n.includes("thomson reuters")) return "reuters";
  if (n.includes("associated press") || n.includes("ap news")) return "ap";
  if (n.includes("agence france presse") || containsOriginToken(n, "afp")) return "afp";
  if (containsOriginToken(n, "ritzau") || n.includes("ritzau bureau")) return "ritzau";
  return null;
}
function pressReleaseService(item) {
  const host = hostOf(item?.final_url || item?.url || "");
  const n = normalizedOriginName(`${item?.provenance_meta?.publisher || ""} ${item?.provenance_meta?.byline || ""}`);
  if (host.endsWith("prnewswire.com") || n.includes("pr newswire")) return "prnewswire";
  if (host.endsWith("businesswire.com") || n.includes("business wire")) return "businesswire";
  if (host.endsWith("globenewswire.com") || n.includes("globe newswire")) return "globenewswire";
  if (host.endsWith("cision.com") || containsOriginToken(n, "cision")) return "cision";
  return null;
}
function headlineFingerprint(item) {
  return [...new Set(words(item?.headline || ""))].slice(0, 10).sort().join("-") || slugify(item?.headline || "release");
}
function structuredUpstreamOrigin(item) {
  const directWire = wireOrigin(item) || metadataWireOrigin(item);
  if (directWire) return `wire:${directWire}`;
  const release = pressReleaseService(item);
  if (release) return `press-release:${release}:${headlineFingerprint(item)}`;
  const canonical = item?.provenance_meta?.canonical_url;
  if (canonical) {
    const pageHost = hostOf(item?.final_url || item?.url || "");
    const canonicalHost = hostOf(canonical);
    if (canonicalHost && pageHost && canonicalHost !== pageHost) return `canonical:${canonical.replace(/[?#].*$/, "")}`;
  }
  return null;
}
'''
s = s[:start] + block + s[end:]
p.write_text(s, encoding='utf-8')
print('Structured provenance helper syntax fixed')
