#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / 'cloudflare' / 'newsdesk' / 'src' / 'editorial.js'
s = p.read_text(encoding='utf-8')

anchor = '''function evidenceSourceGroup(item) {
  return sourceGroup(item?.source, item?.final_url || item?.url);
}
function provenanceClusters(items) {'''
replacement = r'''function evidenceSourceGroup(item) {
  return sourceGroup(item?.source, item?.final_url || item?.url);
}
function metaContent(html, key) {
  const safe = String(key || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const patterns = [
    new RegExp(`<meta\\b[^>]*(?:name|property)=["']${safe}["'][^>]*content=["']([^"']+)["'][^>]*>`, "i"),
    new RegExp(`<meta\\b[^>]*content=["']([^"']+)["'][^>]*(?:name|property)=["']${safe}["'][^>]*>`, "i"),
  ];
  for (const pattern of patterns) { const m = String(html || "").match(pattern); if (m?.[1]) return stripHtml(m[1]).trim(); }
  return null;
}
function canonicalUrl(html, baseUrl) {
  const m = String(html || "").match(/<link\\b[^>]*rel=["'][^"']*canonical[^"']*["'][^>]*href=["']([^"']+)["'][^>]*>/i)
    || String(html || "").match(/<link\\b[^>]*href=["']([^"']+)["'][^>]*rel=["'][^"']*canonical[^"']*["'][^>]*>/i);
  if (!m?.[1]) return null;
  try { return new URL(m[1], baseUrl).href; } catch (_) { return null; }
}
function jsonLdField(html, field) {
  const blocks = String(html || "").match(/<script\\b[^>]*type=["']application\\/ld\\+json["'][^>]*>[\\s\\S]*?<\\/script>/gi) || [];
  for (const block of blocks.slice(0, 8)) {
    const text = block.replace(/^.*?>/s, "").replace(/<\\/script>.*$/s, "");
    try {
      const raw = JSON.parse(text); const nodes = Array.isArray(raw) ? raw : (raw?.['@graph'] || [raw]);
      for (const node of nodes) {
        const value = node?.[field];
        if (typeof value === "string" && value.trim()) return value.trim();
        if (value && typeof value === "object" && typeof value.name === "string") return value.name.trim();
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
function metadataWireOrigin(item) {
  const text = `${item?.provenance_meta?.byline || ""} ${item?.provenance_meta?.publisher || ""}`;
  const n = normalizedOriginName(text);
  if (/\\b(thomson )?reuters\\b/.test(n)) return "reuters";
  if (/\\bassociated press\\b|\\bap news\\b/.test(n)) return "ap";
  if (/\\bagence france presse\\b|\\bafp\\b/.test(n)) return "afp";
  if (/\\britzau( bureau)?\\b/.test(n)) return "ritzau";
  return null;
}
function pressReleaseService(item) {
  const host = hostOf(item?.final_url || item?.url || "");
  const n = normalizedOriginName(`${item?.provenance_meta?.publisher || ""} ${item?.provenance_meta?.byline || ""}`);
  if (host.endsWith("prnewswire.com") || /\\bpr newswire\\b/.test(n)) return "prnewswire";
  if (host.endsWith("businesswire.com") || /\\bbusiness wire\\b/.test(n)) return "businesswire";
  if (host.endsWith("globenewswire.com") || /\\bglobe newswire\\b/.test(n)) return "globenewswire";
  if (host.endsWith("cision.com") || /\\bcision\\b/.test(n)) return "cision";
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
function provenanceClusters(items) {'''
if anchor not in s:
    raise SystemExit('provenance anchor missing')
s = s.replace(anchor, replacement, 1)

old = '''function provenanceClusters(items) {
  const clusters = [];
  for (let i = 0; i < items.length; i++) {
    let cluster = null;
    for (let j = 0; j < i; j++) {
      const a = `${items[i]?.headline || ""} ${items[i]?.excerpt || items[i]?.description || ""}`;
      const b = `${items[j]?.headline || ""} ${items[j]?.excerpt || items[j]?.description || ""}`;
      if (lexicalSimilarity(a, b) >= 0.90) { cluster = clusters[j]; break; }
    }
    clusters[i] = cluster || `pc-${i + 1}`;
  }
  return clusters;
}'''
new = '''function provenanceClusters(items) {
  const clusters = [];
  const origins = items.map(structuredUpstreamOrigin);
  for (let i = 0; i < items.length; i++) {
    let cluster = null;
    for (let j = 0; j < i; j++) {
      if (origins[i] && origins[i] === origins[j]) { cluster = clusters[j]; break; }
      const a = `${items[i]?.headline || ""} ${items[i]?.excerpt || items[i]?.description || ""}`;
      const b = `${items[j]?.headline || ""} ${items[j]?.excerpt || items[j]?.description || ""}`;
      if (lexicalSimilarity(a, b) >= 0.90) { cluster = clusters[j]; break; }
    }
    clusters[i] = cluster || `pc-${i + 1}`;
  }
  return clusters;
}'''
if old not in s:
    raise SystemExit('cluster function missing')
s = s.replace(old, new, 1)

old = '''function evidenceAtom(item) {
  if (authoritativePrimary(item)) return `primary:${item?.final_url || item?.url || evidenceSourceGroup(item)}`;
  const wire = wireOrigin(item); if (wire) return `wire:${wire}`;
  if (item?.provenance_cluster) return `cluster:${item.provenance_cluster}`;
  return `publisher:${evidenceSourceGroup(item)}`;
}'''
new = '''function evidenceAtom(item) {
  if (authoritativePrimary(item)) return `primary:${item?.final_url || item?.url || evidenceSourceGroup(item)}`;
  const upstream = item?.upstream_origin || structuredUpstreamOrigin(item); if (upstream) return `upstream:${upstream}`;
  const wire = wireOrigin(item); if (wire) return `wire:${wire}`;
  if (item?.provenance_cluster) return `cluster:${item.provenance_cluster}`;
  return `publisher:${evidenceSourceGroup(item)}`;
}'''
if old not in s:
    raise SystemExit('evidenceAtom missing')
s = s.replace(old, new, 1)

old = '''    const html = await response.text();
    const text = stripHtml(html).slice(0, 12000);
    return { ...signal, excerpt: text || signal.description || "", fetched: Boolean(text), fetch_status: response.status, final_url: response.url, outbound_links: type.includes("html") ? extractOutboundLinks(html, response.url) : [] };'''
new = '''    const html = await response.text();
    const text = stripHtml(html).slice(0, 12000);
    const provenance_meta = type.includes("html") ? provenanceMetadata(html, response.url) : null;
    return { ...signal, excerpt: text || signal.description || "", fetched: Boolean(text), fetch_status: response.status, final_url: response.url, outbound_links: type.includes("html") ? extractOutboundLinks(html, response.url) : [], provenance_meta };'''
if old not in s:
    raise SystemExit('fetchExcerpt html return missing')
s = s.replace(old, new, 1)

old = '''  const researchClusters = provenanceClusters(unique);
  unique.forEach((item, i) => { item.provenance_cluster = researchClusters[i]; });'''
new = '''  const researchClusters = provenanceClusters(unique);
  unique.forEach((item, i) => {
    item.provenance_cluster = researchClusters[i];
    item.upstream_origin = structuredUpstreamOrigin(item);
  });'''
if old not in s:
    raise SystemExit('research cluster assignment missing')
s = s.replace(old, new, 1)

old = '''    source_strength: authoritativePrimary(item) ? "primary" : authoritativeEditorial(item) ? "wire" : strongEditorialSource(item) ? "strong_editorial" : "standard",
    feed_summary_only: Boolean(item.feed_summary_only),'''
new = '''    source_strength: authoritativePrimary(item) ? "primary" : authoritativeEditorial(item) ? "wire" : strongEditorialSource(item) ? "strong_editorial" : "standard",
    upstream_origin: item.upstream_origin || null,
    byline: item.provenance_meta?.byline || null,
    publisher: item.provenance_meta?.publisher || null,
    canonical_url: item.provenance_meta?.canonical_url || null,
    feed_summary_only: Boolean(item.feed_summary_only),'''
if old not in s:
    raise SystemExit('source payload anchor missing')
s = s.replace(old, new, 1)

old = '''    const publisher = evidenceSourceGroup(s);
    const wire = wireOrigin(s);
    return { id: `S${i + 1}`, name: s.source, url, published_at: s.published_at || null, accessed_at: accessedAt, type: primary ? "primary" : "news", source_group: publisher, publisher_root: publisher.replace(/^host-/, ""), wire_origin: wire, provenance_type: primary ? "primary_record" : wire ? "wire_original" : "reporting", provenance_cluster: clusters[i], primary_record: primary ? url : null, authoritative_for: primary ? (s.headline || "Primary record") : (s.headline || "Independent coverage"), discovery_only: Boolean(s.discovery_only) };'''
new = '''    const publisher = evidenceSourceGroup(s);
    const wire = wireOrigin(s) || metadataWireOrigin(s);
    const upstream = s.upstream_origin || structuredUpstreamOrigin(s);
    return { id: `S${i + 1}`, name: s.source, url, published_at: s.published_at || null, accessed_at: accessedAt, type: primary ? "primary" : "news", source_group: publisher, publisher_root: publisher.replace(/^host-/, ""), wire_origin: wire, upstream_origin: upstream, provenance_type: primary ? "primary_record" : wire ? "wire_original" : upstream?.startsWith("press-release:") ? "press_release" : upstream?.startsWith("canonical:") ? "syndicated" : "reporting", provenance_cluster: clusters[i], provenance_basis: upstream ? "structured_metadata" : "publisher_or_similarity", byline: s.provenance_meta?.byline || null, publisher_name: s.provenance_meta?.publisher || null, canonical_url: s.provenance_meta?.canonical_url || null, primary_record: primary ? url : null, authoritative_for: primary ? (s.headline || "Primary record") : (s.headline || "Independent coverage"), discovery_only: Boolean(s.discovery_only) };'''
if old not in s:
    raise SystemExit('ledger source anchor missing')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')

# Canonical Python gate: explicit upstream origin outranks local publisher/cluster.
p = ROOT / 'scripts' / 'evidence_policy.py'
e = p.read_text(encoding='utf-8')
old = '''    wire = str(source.get("wire_origin") or "").strip().lower()
    if wire:
        return "wire:" + wire
    cluster = str(source.get("provenance_cluster") or "").strip()'''
new = '''    upstream = str(source.get("upstream_origin") or "").strip().lower()
    if upstream:
        return "upstream:" + upstream
    wire = str(source.get("wire_origin") or "").strip().lower()
    if wire:
        return "wire:" + wire
    cluster = str(source.get("provenance_cluster") or "").strip()'''
if old not in e:
    raise SystemExit('python evidence atom anchor missing')
e = e.replace(old, new, 1)
p.write_text(e, encoding='utf-8')

# Golden tests: two publishers with same structured upstream are one atom.
p = ROOT / 'scripts' / 'evidence_policy_selftest.py'
t = p.read_text(encoding='utf-8')
needle = "check('same provenance cluster fails',False,a,l,{'claim':'En almindelig oplysning','source_ids':['S1','S2']},[src('S1','host-theguardian-com',provenance_cluster='pc-x'),src('S2','host-bbc-com',provenance_cluster='pc-x')])\n"
insert = needle + "check('same upstream origin fails',False,a,l,{'claim':'En almindelig oplysning','source_ids':['S1','S2']},[src('S1','host-site-a-com',upstream_origin='wire:reuters'),src('S2','host-site-b-com',upstream_origin='wire:reuters')])\n"
if needle not in t:
    raise SystemExit('selftest anchor missing')
t = t.replace(needle, insert, 1)
p.write_text(t, encoding='utf-8')
print('Structured provenance migration applied')
