# Morgentidende Newsdesk source policy

## Discovery is not sourcing

Blogs, advocacy sites, opinion outlets and other feeds marked `discovery_only` may be used only to discover a potentially relevant story and to locate links to stronger evidence.

They are **never sources for Morgentidende articles**. Their text must not enter the evidence set used to establish claims, and they must not appear as evidence in Fact Check, Journalist input, published source ledgers or article attribution.

The runtime enforces this boundary deterministically. Discovery-only status is detected from feed metadata/source class and a defensive hostname list. Research removes those items before creating claims. Fact Check, Journalist and publication-ledger stages additionally hard-fail if a discovery-only item crosses the boundary.

A discovery lead can proceed only after Research has found acceptable evidence: an authoritative primary source, or sufficient genuinely independent editorial reporting under the verification rules. Discovery sites therefore improve recall without lowering the evidentiary standard.
