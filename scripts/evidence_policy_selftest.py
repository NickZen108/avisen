#!/usr/bin/env python3
from evidence_policy import (
    authoritative_source,
    claim_has_required_support,
    named_accused_crime_claim,
    original_wire,
    primary_or_original_wire,
)


def src(id, group, url='https://example.invalid/story', **kw):
    d = {
        'id': id,
        'source_group': group,
        'publisher_root': group.replace('host-', ''),
        'url': url,
        'type': 'news',
        'authoritative_for': 'det konkrete claim',
    }
    d.update(kw)
    return d


def check(label, want, article, ledger, claim, rows):
    got = claim_has_required_support(article, ledger, claim, {x['id']: x for x in rows})
    if got != want:
        raise SystemExit(f'{label}: expected {want}, got {got}')


a = {'title': 'Lav risiko', 'standfirst': ''}
l = {'right_of_reply': {'required': False}}
claim = {'claim': 'En almindelig oplysning', 'source_ids': ['S1']}

check('one major newsroom passes', True, a, l, claim,
      [src('S1', 'host-theguardian-com', 'https://www.theguardian.com/world/example')])
check('one unknown ordinary outlet fails', False, a, l, claim,
      [src('S1', 'host-small-example', 'https://small-example.invalid/story')])
check('one original wire passes', True, a, l, claim,
      [src('S1', 'host-reuters-com', 'https://www.reuters.com/world/example', wire_origin='reuters')])
check('one authority passes', True, a, l, claim,
      [src('S1', 'host-politi-dk', 'https://politi.dk/x', type='primary', primary_record='https://politi.dk/x')])
check('company about own affairs passes', True, a, l, claim,
      [src('S1', 'host-company-com', 'https://company.invalid/news', authority_class='company_statement')])
check('researcher in field passes', True, a, l, claim,
      [src('S1', 'host-university-edu', 'https://university.invalid/researcher', authority_class='researcher')])
check('research paper passes', True, a, l, claim,
      [src('S1', 'host-journal-org', 'https://journal.invalid/paper', type='paper')])
check('label-only public_media on unknown host fails', False, a, l, claim,
      [src('S1', 'host-blog', 'https://blog.example.invalid/post', type='public_media', authoritative_for='')])
check('expert without scope fails', False, a, l, claim,
      [src('S1', 'host-expert', 'https://example.test/expert', type='expert', authoritative_for='')])
check('expert with scope passes', True, a, l, claim,
      [src('S1', 'host-expert', 'https://example.test/expert', type='expert', authoritative_for='macroeconomics')])
check('discovery_only never evidence', False, a, l, claim,
      [src('S1', 'host-bbc-com', 'https://www.bbc.com/news/example', discovery_only=True)])
check('syndicated reuters host still wire', True, a, l, claim,
      [src('S1', 'host-reuters-com', 'https://www.reuters.com/world/example')])
check('reuters copy on local host is not original wire unless marked', False, a, l,
      {'claim': 'En almindelig oplysning', 'source_ids': ['S1']},
      [src('S1', 'host-lokalavis-dk', 'https://lokalavis.example.invalid/reuters-copy', type='news', authoritative_for='')])
assert original_wire(src('S1', 'host-lokalavis-dk', 'https://lokalavis.example.invalid/x', wire_origin='reuters'))
assert not original_wire(src('S1', 'host-lokalavis-dk', 'https://lokalavis.example.invalid/x'))
assert not authoritative_source({'url': 'https://blog.example.invalid/x', 'type': 'public_media'})
assert authoritative_source({'url': 'https://www.bbc.com/news/x'})

l3 = {'schema_version': 3, 'right_of_reply': {'required': False}}
check('v3 one major newsroom passes without any passage field', True, a, l3,
      {'claim': 'En almindelig oplysning', 'source_ids': ['S1']},
      [src('S1', 'host-bbc-com', 'https://www.bbc.com/news/example')])

h = {'title': 'Mistænkt for drab', 'standfirst': ''}
check('high risk unnamed person still verifies on major media', True, h, l,
      {'claim': 'En person er mistænkt for drab', 'source_ids': ['S1']},
      [src('S1', 'host-bbc-com', 'https://www.bbc.com/news/example')])
assert not named_accused_crime_claim({'claim': 'En person er mistænkt for drab'})
assert named_accused_crime_claim({'claim': 'Anders Jensen er sigtet for drab'})
assert not named_accused_crime_claim({'claim': 'Tyler Robinson pleads not guilty to murder'})

check('named accused on major media without primary/wire fails', False, h, l,
      {'claim': 'Anders Jensen er sigtet for drab', 'source_ids': ['S1']},
      [src('S1', 'host-bbc-com', 'https://www.bbc.com/news/example')])
check('named accused on original wire passes', True, h, l,
      {'claim': 'Anders Jensen er sigtet for drab', 'source_ids': ['S1']},
      [src('S1', 'host-reuters-com', 'https://www.reuters.com/world/example', wire_origin='reuters')])
check('named accused on primary record passes', True, h, l,
      {'claim': 'Anders Jensen er tiltalt for bedrageri', 'source_ids': ['S1']},
      [src('S1', 'host-politi-dk', 'https://politi.dk/x', type='primary', primary_record='https://politi.dk/x')])
assert primary_or_original_wire(src('S1', 'host-reuters-com', 'https://www.reuters.com/world/example'))

print('EVIDENCE POLICY SELFTEST: PASS')
