#!/usr/bin/env python3
"""Hard pre-publish media-safety checks for Morgentidende.

This gate is article-specific. Shared UI/design behaviour (dark mode, sticky header,
viewport, CSS object-fit, etc.) is deliberately NOT checked for every article; it
belongs to design-change CI. A news article must not be blocked by unrelated UI state.
"""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ARTICLES=ROOT/'content'/'articles'
ALLOWED_AI_PEOPLE_STYLES={'editorial_illustration','pencil_sketch','pencil_hatching','line_art','collage','silhouette','flat_vector','watercolor','woodcut','ink_drawing'}
PHOTOREAL_STYLE_TERMS={'photorealistic','photo_realistic','realistic_photo','documentary_photo','cinematic_photo'}
def check_ai_people_style(label,image,faults):
 if not image.get('ai_generated'): return
 if image.get('image_type')!='illustration': faults.append(f'{label}: AI-genereret grafik skal være mærket illustration')
 contains=image.get('contains_people')
 if not isinstance(contains,bool): faults.append(f'{label}: AI-grafik skal deklarere contains_people true|false'); return
 if not contains:return
 style=str(image.get('people_style') or '').strip().lower()
 if not style:faults.append(f'{label}: AI-grafik med mennesker mangler people_style'); return
 if style in PHOTOREAL_STYLE_TERMS or image.get('photorealistic') is True:faults.append(f'{label}: fotorealistiske AI-personer er ikke tilladt')
 elif style not in ALLOWED_AI_PEOPLE_STYLES:faults.append(f'{label}: ikke-godkendt AI-personstil {style!r}')
def load(path):return json.loads(path.read_text(encoding='utf-8'))
def main():
 faults=[]
 for path in sorted(ARTICLES.glob('*.json')):
  if path.name.startswith('_'):continue
  article=load(path)
  if article.get('status') not in {'ready','published'}:continue
  image=article.get('image'); origin=article.get('automation_origin')
  if origin=='cloudflare-workers-ai':
   if not isinstance(image,dict):faults.append(f'{path.name}: autonom artikel mangler hero');continue
   if image.get('placement','lead')!='lead':faults.append(f'{path.name}: autonom artikel har ikke lead-hero')
   image_type=image.get('image_type'); context=str(image.get('context_type') or '').strip().lower(); pending=image.get('pending_image') is True; ai=image.get('ai_generated') is True
   if image_type in {'photo','video_still'}:
    if pending or ai:faults.append(f'{path.name}: dokumentarisk foto/still må ikke være pending eller AI-genereret')
    if context not in {'event','place','person','object','archive'}:faults.append(f'{path.name}: ugyldig context_type for dokumentarisk hero')
    if context!='event' and not str(image.get('caption') or '').strip():faults.append(f'{path.name}: ikke-hændelsesfoto kræver synlig arkiv-/kontekst-caption')
    source_url=str(image.get('source_url') or '').lower()
    if image_type=='video_still' and ('youtube.com' in source_url or 'youtu.be' in source_url) and not str(image.get('rights_basis') or '').strip():faults.append(f'{path.name}: YouTube-video-still kræver dokumenteret rights_basis')
    if image.get('discovery_only_source') is True and image.get('independent_license') is not True:faults.append(f'{path.name}: discovery_only må ikke være billedkilde uden selvstændig licens')
   elif image_type=='graphic':
    if pending or ai:faults.append(f'{path.name}: dokumentarisk grafik må ikke være pending eller AI-genereret')
    if context not in {'map','satellite','archive'}:faults.append(f'{path.name}: ugyldig context_type for dokumentarisk grafik')
    if not str(image.get('caption') or '').strip():faults.append(f'{path.name}: dokumentarisk grafik kræver synlig kontekst-caption')
    if image.get('discovery_only_source') is True and image.get('independent_license') is not True:faults.append(f'{path.name}: discovery_only må ikke være grafikkilde uden selvstændig licens')
   elif image_type=='illustration':
    if not pending or not ai:faults.append(f'{path.name}: nyhedsillustration skal være pending og AI-genereret')
    if context!='illustration':faults.append(f'{path.name}: pending illustration skal have context_type=illustration')
    if str(image.get('caption') or '').strip().lower()!='illustration':faults.append(f"{path.name}: pending illustration skal have synlig caption 'Illustration'")
    if image.get('photorealistic') is True:faults.append(f'{path.name}: pending illustration må ikke være fotorealistisk')
   else:faults.append(f'{path.name}: ugyldig autonom hero-type {image_type!r}')
   for key in ('src','alt','credit','license','source_url'):
    if not str(image.get(key) or '').strip():faults.append(f'{path.name}: hero mangler {key}')
   src=str(image.get('src') or '')
   if src.lower().endswith('.svg'):faults.append(f'{path.name}: autonom hero må ikke være rå SVG')
   if src.startswith('/img/') and not (ROOT/'docs'/src.lstrip('/')).exists():faults.append(f'{path.name}: lokal hero findes ikke: {src}')
  if isinstance(image,dict):check_ai_people_style(path.name,image,faults)
  if isinstance(image,dict) and image.get('src') and image.get('placement','lead')=='lead':
   if not str(image.get('alt') or '').strip():faults.append(f'{path.name}: lead-billede mangler alt-tekst')
   if not str(image.get('credit') or '').strip():faults.append(f'{path.name}: lead-billede mangler kredit')
   if image.get('image_type') in {'photo','graphic'} and not str(image.get('license') or '').strip():faults.append(f'{path.name}: foto/grafik mangler licens')
  for i,block in enumerate(article.get('body') or []):
   if block.get('type')!='figure':continue
   if not str(block.get('src') or '').strip():faults.append(f'{path.name}: figur {i} mangler src')
   if not str(block.get('alt') or '').strip():faults.append(f'{path.name}: figur {i} mangler alt-tekst')
   check_ai_people_style(f'{path.name}: figur {i}',block,faults)
 if faults:
  print('PREPUBLISH MEDIA SAFETY: FAIL')
  for fault in faults:print('-',fault)
  return 1
 print('PREPUBLISH MEDIA SAFETY: PASS');return 0
if __name__=='__main__':raise SystemExit(main())
