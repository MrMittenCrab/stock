# Phase 2 implementation and disposable pilot

The governing semantics remain [proposition-decontextualization.md](proposition-decontextualization.md).
This note describes implementation and limitations, not a second specification.

`stock.proposition_context` owns validation, immutable records and checked reads.
`knowledge.Operations` owns generation/review caching. `editorial` resolves exact
originals and performs both judgments in its existing independent review operation.
`sort.Cursor` only extends the existing read-only JSON transport prompts/payloads.
No legacy extraction engine, pairwise Cursor operation, model, threshold, graph
publication change, production migration or production activation is included.

## Contracts and associations

Disposable transports explicitly set **both** `contextualize=True` and
`disposable_context=True`. Default callers retain the existing workflow. This opt-in
is an execution guard, not a filesystem security boundary: callers must supply a
disposable Store and source copies, as both pilot scripts do.

Each selection retains its existing fields and adds `selection_key` and `context`.
The inline one-to-one shape makes an orphan proposal impossible; missing/duplicate
keys and unexpected fields fail protocol validation. `context` contains
`context_status`, `standalone_text`, `resolutions`, `unresolved`. Generation cannot
request `not_attempted`; that state comes from the explicit legacy adapter.
Stock resolves original wording first, including verbatim text, then validates edits
against that exact string and resolves every edit ID through existing source atoms.
Metadata is bound in the document envelope but **cannot authorize edits** in this
implementation; metadata-only resolutions must abstain. Verified metadata-field
resolutions can be added later with explicit field provenance, without inferring
issuer/period from ticker, title or publication date.

The record has exactly the governing fields:
`contract_version`, `proposition_id`, `original_text`, `source_fingerprint`,
`context_status`, `standalone_text`, `resolutions`, `unresolved`, `verification`.
Version is `stock-proposition-context-1`; resolution fields are `original_span`,
`replacement`, `purpose`, `evidence_refs`. `verification` has `original_support`,
`context_preservation`, `reason`, `artifact_id`, with the governing status vocabularies.
The existing review's `fidelity` maps to `original_support`; the second verdict and
its reason are separately named `context_preservation` and `context_reason` on the
wire. Both are produced in the **same independent review request**, after generation.
An accepted generation response is never an independent verdict.

Artifact contracts are `stock-proposition-context-1:generation-1` and
`stock-proposition-context-1:review-1`. The original-only `knowledge-2-strategic`
artifacts remain intact and cacheable. An original-only approval never supplies a
context verdict. Context review caches include rejected/unresolved outcomes to avoid
repeating failed interpretations. Full exact inputs, document provenance, proposal,
edit anchors, review output and the source fingerprint bind the context-review artifact.
Review indices and transport batches do not enter individual review identities.

`proposition_id` is the existing staging `knowledge_propositions.id` formula.
The existing evidence fingerprint is computed on the future published envelope
(including passage ID and document ID), so publishing an unchanged staging proposition
does not itself stale approval. Context record ID is `insights.digest(record)`; its JSON is independently stored in
`knowledge_artifacts` with checksum and an indexed deterministic association key.
A separate `context-selection` artifact binds generation artifact + selection key +
selection digest to the staging ID. `context-generation-input` records exact completed
source coverage so changed section packing can reuse extraction responses without
another request. Cross-section selections retain their original source envelopes.
Missing/corrupt coverage fails closed; changed document/context/source inputs require
new work. Conflicting contextual records for one original block final association.

`read` checks the record digest, current original/evidence fingerprint, proposal,
source references and independently bound verdict before returning a stored record.
Missing records adapt explicitly to `not_attempted`, unchanged original text and
`not_checked` context verification. Rejected or unresolved interpretations retain
original text and diagnostic artifacts; only supported + accepted unnecessary/resolved
records pass `eligible`. Semantic sufficiency still depends on the independent judge,
not the structural validator or the `eligible` predicate alone.

## Storage boundary and future durable association

All new JSON uses the existing operation-artifact infrastructure; no new database
schema is introduced. Nothing is inserted into `source_passages.location`, and the
passage-ID formula is unchanged. Original citation envelopes, representation and
publication checks remain in force. Context artifacts do not cause publication.

`association` builds one immutable manifest mapping future published passage IDs to
staging IDs, record IDs and evidence fingerprints, with an optional parent manifest.
It checks every entry before storing the manifest. `lookup` uses one explicit manifest
ID for an atomic, coherent read; passing a prior ID provides rollback. Tests exercise
versioned lookup, missing/legacy entries, rollback, conflicting proposals, failed
construction, unchanged published rows and retained topic corrections. There is
**no active production association head** in Phase 2.

Before production, the publisher must commit an association-head pointer in the same
checked SQLite transaction as evidence/head activation and correction reconciliation.
A later additive head table is preferable to a filesystem pointer spanning two
transaction systems. Recheck source hashes, expected old manifest/head, evidence
inventory and correction snapshots immediately before committing. Preserve manifests
for rollback. Continue existing unique exact-anchor/category/speaker replacement
matching; ambiguous transfers block. Same evidence IDs retain topic overrides and
split vetoes. A changed context record requires review before reusing a positive
logical manual override. Those publication/head/correction integration gates are
specified here for later work; they are not implemented or activated in this phase.

## Bounded results

Run the deterministic replay with:

```
.venv/bin/python scripts/pilot_proposition_context.py /tmp/context-replay.json
```

[Replay measurements](benchmarks/proposition-context-replay.json) cover 24 separately
versioned cases: 21 exercised, 3 anchor-validated and held out from execution. All
original fixture files and historical labels remain unchanged. Exact source IDs,
Unicode offsets, text and SHA-256 are revalidated against the selected fixture bytes.
CoreWeave sources are repository replay fixtures, not newly authenticated production
disclosures. The Microsoft excerpt was retrieved from the
[official FY2025 Q4 release](https://www.microsoft.com/en-us/Investor/earnings/FY-2025-Q4/press-release-webcast);
its source URL, retrieval date, HTML hash and extraction procedure are retained in
`tests/fixtures/proposition-context/microsoft-provenance.json`.

| Recorded transport outcome | Count |
| --- | ---: |
| Selections / proposals exercised | 21 / 21 |
| Unnecessary / resolved / unresolved records | 7 / 4 / 10 |
| Original supported / unsupported | 21 / 0 |
| Context accepted / rejected / unresolved | 11 / 6 / 4 |
| Known meaning-changing test proposals rejected | 6 |
| Eligible records / lost identities or citations | 11 / 0 |
| Extraction / review transport requests | 3 / 3 |
| Requests on full resume | 0 |
| New immutable artifacts / unchanged on resume | 96 / 96 |

Abstentions include unestablished comparison periods, ambiguous discourse scope,
fiscal-period attachment and flattened table label/value relationships. Hard negatives
change contracted to active capacity, expectation to confirmation, backlog to guaranteed
revenue, issuer, publication versus reporting date, or an illustrative-footprint caveat.
The replay's review responses are separately injected **test expectations**, not human
adjudication or measured model performance. The unsupported-original gate is also
exercised separately in integration tests.

Instruction increments are 1,808 extraction and 1,167 review characters. Recorded
context response fields total 8,913 characters; additional local review input fields
are 24,949 characters. These are serialization diagnostics, not billed token counts:
actual Cursor deduplicates source envelopes on the wire. Source-specific full input
and response lengths are in the report. Transport rebatching and interruption tests
verify reuse, including accepted and rejected independent review work.

## Authenticated observation and remaining evaluation gate

The optional live script uses the existing bounded read-only transport, disposable
files/SQLite and a hard two-request budget:

```
.venv/bin/python scripts/pilot_proposition_context_live.py /tmp/context-live.json
```

It was run **once**, without score-improvement retries. The retained
[live capture](benchmarks/proposition-context-live.json) has four generated selections
and proposals. Existing speaker-envelope validation excluded three named-speaker
selections before independent review; their original/context support is **not checked**,
not an independent semantic rejection. One original reached the separate review and
was supported, with its unnecessary context accepted. Resume made zero requests.
No live resolved rewrite or adversarial rejection was observed. Prompts were
7,626/6,412 characters and response envelopes 3,540/1,125 characters for extraction/review.
Cursor reported 11,564/11,388 input tokens and 9,415/1,638 output tokens; those are provider
usage fields, not estimates from character counts.

The capture retains historical diagnostic artifacts from before final binding
refinements. The focused test replays its exact authenticated generation and review
responses through the final pipeline, validates the current record/association,
reproduces all three exclusions and checks request-free resume. Historical capture
artifacts are not treated as active final records.

No production accuracy rate is estimated. Factual correctness, standalone sufficiency,
meaning preservation and fluency have no independently adjudicated scores here.
The governing document's human protocol remains the acceptance protocol: two independent
reviewers judge standalone sufficiency blind to source, then inspect exact originals,
edits and sources for meaning preservation, record dimension-specific disagreements,
and adjudicate with evidence. Grammar is scored separately. The three held-out cases
remain unexecuted. Phase 3 must wait for that adjudicated/held-out semantic gate and
raw baseline; automated invariants and this small live unchanged example cannot
establish financial truth-condition preservation. Production association activation
requires its own later atomicity and correction-reconciliation gate.

## Verification

The broader focused run passed **164 tests** across `test_proposition_context`,
`test_knowledge`, `test_editorial`, `test_sort_efficiency` and `test_evidence`.
After final staging/published fingerprint and compact context-reference refinements,
**56 context/transport tests** passed again. The disposable 21-case end-to-end replay
was rerun successfully, and authenticated responses also pass final-code replay.
These checks establish executable integrity invariants, not semantic correctness.
No production database, document-13 rebuild, historical fixture rewrite, semantic
model/threshold change or production context activation was performed.
