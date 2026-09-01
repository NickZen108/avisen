#!/usr/bin/env python3
from evidence_policy import claim_has_required_support

def src(id, group, **kw):
 d={'id':id,'source_group':group,'publisher_root':group.replace('host-',''),'type':'news','authoritative_for':'x'}; d.update(kw); return d

def check(label, want, article, ledger, claim, rows):
 got=claim_has_required_support(article, ledger, claim, {x['id']:x for x in rows})
 if got != want: raise SystemExit(f'{label}: expected {want}, got {got}')

a={'title':'Lav risiko','standfirst':''}; l={'right_of_reply':{'required':False}}
check('one ordinary outlet fails',False,a,l,{'claim':'En almindelig oplysning','source_ids':['S1']},[src('S1','host-theguardian-com')])
check('two publishers pass',True,a,l,{'claim':'En almindelig oplysning','source_ids':['S1','S2']},[src('S1','host-theguardian-com'),src('S2','host-bbc-com')])
check('same provenance cluster fails',False,a,l,{'claim':'En almindelig oplysning','source_ids':['S1','S2']},[src('S1','host-theguardian-com',provenance_cluster='pc-x'),src('S2','host-bbc-com',provenance_cluster='pc-x')])
check('same upstream origin fails',False,a,l,{'claim':'En almindelig oplysning','source_ids':['S1','S2']},[src('S1','host-site-a-com',upstream_origin='wire:reuters'),src('S2','host-site-b-com',upstream_origin='wire:reuters')])
check('wire low risk passes',True,a,l,{'claim':'En almindelig oplysning','source_ids':['S1']},[src('S1','host-reuters-com',wire_origin='reuters')])
h={'title':'Mistænkt for drab','standfirst':''}
check('wire high risk alone fails',False,h,l,{'claim':'En person er mistænkt for drab','source_ids':['S1']},[src('S1','host-reuters-com',wire_origin='reuters')])
check('primary high risk passes',True,h,l,{'claim':'En person er mistænkt for drab','source_ids':['S1']},[src('S1','host-politi-dk',type='primary',primary_record='https://politi.dk/x')])
print('EVIDENCE POLICY SELFTEST: PASS')
