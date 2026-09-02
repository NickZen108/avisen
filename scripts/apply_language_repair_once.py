#!/usr/bin/env python3
from pathlib import Path
import json,re

ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'cloudflare/newsdesk/src/editorial.js'
s=p.read_text(encoding='utf-8')

if 'async function polishArticleLanguage(' not in s:
    anchor='function deterministicFinalReview(assignment, dossier, article) {'
    if anchor not in s:
        raise SystemExit('deterministicFinalReview anchor not found')
    fn=r'''async function polishArticleLanguage(env, assignment, dossier, article) {
  const sourceLanguage = String(assignment?.story_location?.primary_language_code || assignment?.story_location?.primary_language || "").toLowerCase();
  const system = `Du er Morgentidendes eksisterende sprogredaktør. Gennemlæs HELE den færdige artikel og returnér hele artiklen i samme schema på idiomatisk, naturligt dansk. Dette er et repair/polish-step, IKKE en ny gate og må ikke kræve nye kilder. Bevar alle verificerede fakta, attributioner, citater, tal, URL'er, vinkel og betydning; tilføj ingen nye claims. Ret svensk, norsk, engelsk eller andet kildesprog, der er gledet ind i titel, standfirst, brødtekst eller SEO. Når kildesproget er svensk eller norsk, skal alle almindelige ord og bøjningsformer oversættes til dansk; egennavne og egentlige citater bevares. Sørg også for, at standfirst er en rigtig kort manchet og ikke blot et kildenavn. Forklar egennavne kort første gang, når forklaringen allerede kan udledes sikkert af det verificerede materiale; opfind ikke baggrundsoplysninger. Skriv ikke kilde- eller redaktionsnoter ind, medmindre de allerede er en del af artiklen. Returnér kun den reparerede artikel.`;
  return aiJson(env, system, JSON.stringify({
    source_language: sourceLanguage,
    assignment,
    verified_claims: dossier.claims.filter((c) => c.status === "verified"),
    article,
  }), articleSchema, assignment.weight === "A" || assignment.weight === "B" ? 2400 : 1600, FAST_TEXT_MODEL, assignment.weight === "A" || assignment.weight === "B" ? STRONG_TEXT_MODEL : null);
}

'''
    s=s.replace(anchor,fn+anchor,1)

if 'article = await polishArticleLanguage(env, assignment, dossier, article);' not in s:
    pat=re.compile(r'(\blet\s+article\s*=\s*await\s+writeArticle\(env,\s*assignment,\s*dossier\);)')
    m=pat.search(s)
    if not m:
        raise SystemExit('article write call not found')
    s=s[:m.end()]+'\n  article = await polishArticleLanguage(env, assignment, dossier, article);'+s[m.end():]

p.write_text(s,encoding='utf-8')

slug='2026-09-02-dykolycka-i-lerkils-hamn-en-person-er-blevet-allvarligt-skadet'
article_path=ROOT/'content/articles'/f'{slug}.json'
approval_path=ROOT/'reports/editorial/approvals'/f'{slug}.json'
article=json.loads(article_path.read_text(encoding='utf-8'))
article['title']='Dykkerulykke i Lerkils havn: En person alvorligt kvæstet'
article['standfirst']='To dykkere blev reddet op af vandet efter en ulykke i Lerkils havn. Den ene blev kørt på hospitalet med alvorlige skader, oplyser SVT, Sveriges public service-tv.'
article['seo']['title']=article['title']
article['seo']['description']='To dykkere blev reddet op af vandet efter en dykkerulykke i Lerkils havn i Kungsbacka. Den ene blev kørt på hospitalet med alvorlige skader.'
if article.get('image'):
    article['image']['alt']='Illustration til: Dykkerulykke i Lerkils havn: En person alvorligt kvæstet'
article['body']=[
    {'type':'p','text':'En person er blevet alvorligt kvæstet efter en dykkerulykke i Lerkils havn i Kungsbacka. Alarmen om ulykken kom klokken 20.20, efter at en forbipasserende opdagede to dykkere i vandet og slog alarm. To personer blev reddet op af vandet, og den ene blev kørt på hospitalet med ambulance.'},
    {'type':'p','text':'Kilde: SVT, Sveriges public service-tv.'},
    {'type':'p','text':'Læs mere hos SVT: https://www.svt.se/nyheter/lokalt/halland/en-person-till-sjukhus-efter-dykolycka-i-lerkils-hamn'},
]
article_path.write_text(json.dumps(article,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

approval=json.loads(approval_path.read_text(encoding='utf-8'))
snap=json.loads(json.dumps(article))
for key in ['status','published_at','updated_at','scheduled_for','released_from_schedule_at','release_requested','publication','manual_review_completed','workflow_state']:
    snap.pop(key,None)
approval['editorial_snapshot']=snap
approval['checked_at']=article.get('published_at') or approval.get('checked_at')
approval_path.write_text(json.dumps(approval,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

print('language repair migration applied')
