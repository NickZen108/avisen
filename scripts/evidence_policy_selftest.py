#!/usr/bin/env python3
from evidence_policy import claim_has_required_support


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

l3 = {'schema_version': 3, 'right_of_reply': {'required': False}}
check('v3 missing support passage fails', False, a, l3,
      {'claim': 'En almindelig oplysning', 'source_ids': ['S1'], 'support_passages': []},
      [src('S1', 'host-bbc-com', 'https://www.bbc.com/news/example')])
check('v3 verified support passage passes', True, a, l3,
      {'claim': 'En almindelig oplysning', 'source_ids': ['S1'], 'support_passages': [{'source_id': 'S1', 'quote': 'En almindelig oplysning fremgår her.', 'match_verified': True}]},
      [src('S1', 'host-bbc-com', 'https://www.bbc.com/news/example')])

h = {'title': 'Mistænkt for drab', 'standfirst': ''}
check('high risk major newsroom still verifies claim', True, h, l,
      {'claim': 'En person er mistænkt for drab', 'source_ids': ['S1']},
      [src('S1', 'host-bbc-com', 'https://www.bbc.com/news/example')])

print('EVIDENCE POLICY SELFTEST: PASS')
