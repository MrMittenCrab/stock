# Proposition decontextualization contract

Status: governing design, Phase 1; contract `stock-proposition-context-1`.
Repository baseline: `51768c8`, `feature/persistent-semantic-map`.
This document specifies future behavior; it does not describe an implemented feature.

## Authority and scope

This is the single authoritative specification for making Stock investment-research
propositions independently interpretable. Extraction, independent verification,
semantic retrieval, local inference and presentation must use this contract rather
than define separate meanings of context. Existing runtime contracts remain in force
until the bounded migration below passes its gates. Historical plans are not authority
for this feature. Changes to the semantic requirements require a new contract version;
editorial clarifications that do not change behavior may retain this version.

**A contextualized proposition must be independently interpretable while preserving
the truth-conditional meaning of the original proposition in its verified source
context.** Here, “contextualization” names Stock's workflow; its output operation is
decontextualization. It is not permission to enrich an investment thesis.

The reader may know ordinary financial terminology, but must not need an adjacent
proposition, a document title, the current ticker, or the date of reading to determine
the assertion's material referents. Definitions peculiar to the source still need
support. Financial expertise does not resolve ambiguous source evidence.

## Research basis and attribution boundaries

Primary reference: Eunsol Choi et al. (2021), [Decontextualization: Making Sentences
Stand-Alone](https://aclanthology.org/2021.tacl-1.27/), TACL 9:447–461,
[original PDF](https://aclanthology.org/2021.tacl-1.27.pdf),
[DOI 10.1162/tacl_a_00377](https://doi.org/10.1162/tacl_a_00377).
The original paper was accessed for this specification.

Adopted research concepts (paraphrased):

- §2, Definition 1 (pp. 448–449): standalone interpretability and preservation of
  truth conditions; implicatures are excluded. Its formal context is preceding
  sentences; extralinguistic circumstances are assumed preserved.
- §3.1 (p. 449), §5.1 (p. 453): feasibility includes unchanged sentences;
  UNNECESSARY identifies those needing no edits. Difficult cases may be infeasible.
- §3.2 and Table 1 (pp. 449–450): reference replacement, name completion, discourse
  marker removal, bridging and global scoping; background addition is optional.
- §§3.3–3.4 (pp. 450–452): valid rewrites vary; Wikipedia limits generalization.
- §4 (p. 452): annotators inspect documents, judge feasibility, then edit;
  annotation quality separates content from fluency.
- §5.2.1–§5.2.2 (pp. 453–455): evaluate feasibility and generation separately;
  multiple references, edit metrics and human sufficiency/correctness judgments
  complement each other. Exact match rewards copying; SARI is not accuracy.
- §§6.1–6.2 (pp. 455–457): preliminary presentation and retrieval applications
  motivate downstream evaluation, without establishing financial reliability.

Everything below is a **Stock extension**, except the governing correctness
principle and adopted concepts identified above. In particular the authors do not
prescribe independent source verification, financial safeguards, JSON fields, caches,
Cursor, NLI policies, graph grouping or migration gates. Stock deliberately requires
only necessary contextual edits, excluding optional background enrichment. Stock
also supports anchored headings, tables, footnotes and relevant later passages,
and makes time/perspective explicit when needed for durable archival reading,
rather than assuming the original extralinguistic circumstances persist.

## Operations that must remain distinct

| Operation | Meaning in Stock |
|---|---|
| Decontextualization | Resolve the original assertion's interpretation without changing its truth conditions. |
| Summarization | Select or compress content; may omit information and is not this operation. |
| Research synthesis | Combine assertions or derive conclusions; requires separate provenance and is outside this contract. |
| Semantic equivalence | Two assertions preserve information in both directions under compatible interpretations. |
| Logical entailment | A directional relation; a more informative assertion can entail another without equivalence. |
| Candidate similarity | A retrieval signal identifying pairs worth examining; no logical decision. |
| Thematic relationship | Shared subject matter, represented by RELATED where justified; no entailment claim. |
| Presentation grouping | A reversible graph view over retained evidence nodes. |

Source support means that a source supports an attributed assertion, not that the
assertion is objectively true. Decontextualization cannot turn management's claim
into independent confirmation. Even two verified standalone assertions are not
thereby equivalent. NLI scores are fallible model outputs, not proofs of truth or
truth-conditional equivalence.

## Current architecture and compatibility audit

Paths below are relative to this document. This audit describes baseline behavior,
not changes delivered in Phase 1.

| Module / contract | Existing behavior and consequence |
|---|---|
| [sort.py](../stock/sort.py) | Cursor transport and historical section/quotation helpers remain. Current Sort delegates extraction through evidence; do not build a second context engine in the old helpers. |
| [evidence.py](../stock/evidence.py), [knowledge.py](../stock/knowledge.py) | `evidence.extract` delegates to knowledge. `knowledge-2-strategic` uses exact atoms, headings, speaker turns, table structure, operation artifacts/checksums and per-claim review reuse. `knowledge_propositions` and `knowledge_supports` separate wording from anchors; publication is a compatibility projection. |
| [editorial.py](../stock/editorial.py) | Selections contain `ids`, `topics`, `category`, `speaker`, `representation`, `text`, `ambiguities`; representations are `verbatim`, `edited_quotation`, `source_grounded_statement`. Resolved references include document/source IDs, hashes, offsets/text, evidence version, paths, section/turn and available PDF/table provenance. Review separately records fidelity, readability, relevance, warnings and reason, with an intact review fingerprint required for publication. Context evidence cannot substitute for selected citations. |
| [sources.py](../stock/sources.py) | Published `text` and `location` are frozen evidence. `passage_id` hashes document ID, serialized **entire location**, and text; adding a context property to location would change identity. `sources.passages` supports legacy exact-source records and effective topic overrides. |
| [rebuild.py](../stock/rebuild.py) | `match_key` reconciles exact source anchors plus category/speaker, including contiguous-span normalization. Missing or ambiguous manual transfer blocks replacement. Retired rows/topics/overrides enter `source_publication_history`. Hash/snapshot checks and checked transaction protect evidence/head activation and rollback. |
| [insights.py](../stock/insights.py) | `passage_fingerprint` includes evidence wording/location, attribution, dates and document metadata. Immutable JSON revisions and atomic heads are distinct from the original passage ID. Topics, splits and corrections have retained history. |
| [semantic_map.py](../stock/semantic_map.py) | Pinned BGE raw-text embeddings are keyed by exact UTF-8 text hash and encoder contract. Candidate runs/scores retain inventory and deferred work; incremental refinement widens review. Raw vectors are not proof of equivalence. |
| [relationships.py](../stock/relationships.py) | Pinned local MiniLM runs both directions without silent truncation. Current raw inference key uses model contract and ordered exact texts; older source-keyed cache fallback remains. Decision policy is separate and receives current source/context data. |
| [semantic_attributes.py](../stock/semantic_attributes.py) | `with_context` recovers narrowly selected issuer/deictic-period/note attributes and provenance; financial parsing and compatibility vetoes operate separately. This heuristic `semantic_context` is **not** a verified standalone-text contract. Missing dimensions do not establish agreement. |
| [proposition_graph.py](../stock/proposition_graph.py) | `proposition-graph-1` retains evidence nodes, directional edges, manual overrides and suppression tombstones. Complete-link equivalence supports grouping; one-way entailment keeps both rows. Revisions are immutable. |

The new contract extends the existing extraction/review workflow and graph, not their
replacement. Existing documentation such as [semantic-map.md](semantic-map.md) and
[semantic-correctness.md](semantic-correctness.md) describes current runtime models
and policies. This document governs future context semantics; it changes no model,
threshold, extraction selection policy or production readiness determination.

## Minimal proposition-context representation

Preserve both the original proposition and an explicit standalone rendering. Concise
resolution metadata is useful for audit and financial checks but is not interchangeable
with a complete sentence: concatenating a generic summary or a bag of attributes can
change attachment, scope and modality.

Use an additive context record outside frozen `source_passages.location` and outside
the passage ID computation. The logical shape below is normative; physical storage
is not a new database schema in this phase. Phase 2 uses versioned JSON operation
artifacts in disposable storage. A published association/storage design must preserve
this identity boundary before production use.

| Field | Required semantics |
|---|---|
| `contract_version` | Exact `stock-proposition-context-1`. Unknown versions must not be treated as verified. |
| `proposition_id` | Existing published passage ID, or a staging proposition key explicitly mapped to that ID at publication. Never an embedding identity. |
| `original_text` | Exact pre-contextualization proposition `text`, including its representation and attribution in the bound evidence envelope. It may already be reconstructed; it is not necessarily a verbatim source quotation. |
| `source_fingerprint` | Existing evidence fingerprint, binding original wording, source references, attribution and document context. The context record does not recursively enter this fingerprint. |
| `context_status` | `unnecessary`, `resolved`, `unresolved`, or `not_attempted`, with rules below. |
| `standalone_text` | Exact original text for unnecessary/unresolved/not_attempted; approved minimal rewrite for resolved. No partial rewrite promoted as standalone. |
| `resolutions` | Ordered array of `{original_span, replacement, purpose, evidence_refs}`. Span is a half-open Unicode code-point range into original text (the same string-index convention as Python); insertion has equal endpoints, deletion has empty replacement. Nonoverlapping edits reproduce standalone text. Purpose explains the reference/scope resolved, not an investment inference. |
| `unresolved` | Array of specific missing/ambiguous referents or material dimensions and reasons. No unexplained empty context. |
| `verification` | `{original_support, context_preservation, reason, artifact_id}`. Original support: `supported`, `unsupported`, `unresolved`, `not_checked`. Context preservation: `accepted`, `rejected`, `unresolved`, `not_checked`. Artifact ID binds the independent review inputs/output, reviewer workflow contract and provenance. |

`evidence_refs` resolve Stock-owned source IDs to the existing exact reference envelope:
document ID, Markdown hash, start/end and exact text, original hash/evidence version,
and available layout/table provenance. Reuse existing references by ID; newly needed
headings/notes get the same exact anchor validation. Also bind any necessary verified
metadata field by document identity, field path, exact value and its verification
provenance in the review artifact. A ticker label, publisher or unverified filename
is not issuer evidence. Context reference ordering/roles must distinguish original
assertion support from support for a particular edit. One anchor can serve both.

No parallel mandatory issuer/date/metric taxonomy is introduced. Necessary semantic
dimensions appear in the sentence and edit evidence; optional existing structured
attributes may be projected only from independently accepted resolutions, with
provenance and conflict checks. They must never silently become a second meaning.

Context record identity is a digest of the canonical serialized record (excluding its
own identifier). Use existing deterministic packing/digest conventions; store exact
strings without lossy normalization. A verification artifact must bind original text,
evidence fingerprint, proposed text, edits, unresolved items and all relied-on source
or metadata evidence. Editing any of these invalidates that approval. A pending or
rejected proposal can be retained in its generation artifact, not exposed as accepted
standalone text.

### States and invariants

| State | Research mapping | Consumer behavior |
|---|---|---|
| `unnecessary` | UNNECESSARY; included in broad feasible category | Verified judgment that no contextual edits are necessary. Standalone equals original byte for byte; resolutions/unresolved empty. |
| `resolved` | FEASIBLE with edits | Nonempty resolutions, no unresolved items; independently accepted, supported interpretation. |
| `unresolved` | Operational abstention, including INFEASIBLE | Original text retained; nonempty reasons, no accepted resolutions. This may reflect unavailable evidence or a failed attempt, not an intrinsic impossibility claim. |
| `not_attempted` | No paper category | Legacy/default adapter or pending generation. Original retained; no claim that it stands alone. |

Only unnecessary/resolved with `original_support=supported` and
`context_preservation=accepted` are eligible for the verified contextual input path.
Unresolved context may coexist with supported original evidence; these are independent
judgments. A rejected rewrite becomes unresolved with a reason and retains its rejected
artifact. “No edits necessary” is an affirmative reviewed result, never inferred from
an empty string/list, absent record or successful extraction alone.

An unsupported original must not be newly published through this contract. If an
original is supported but no standalone interpretation can be verified, retain it in
staging/audit and keep historical evidence readable. Do not weaken existing editorial
publication checks: a new fragment or unresolved material ambiguity remains ineligible
for new publication. Existing usable originals need not be discarded because a proposed
rewrite failed; they require an accepted unnecessary judgment to enter the new path.

## Meaning-preserving edits in financial research

Resolve only what is necessary for this assertion. Do not automatically complete a
financial template, import the latest known company facts, mix periods, add causal
explanations, derive valuation conclusions or aggregate neighboring assertions.
Every contextual edit needs explicit source support **and** evidence that the support
applies to this proposition. A true fact elsewhere is insufficient.

| Dimension | Required handling and evidence |
|---|---|
| Issuer/counterparty | Resolve pronouns using anchored speaker/turn and entity evidence. Distinguish issuer, customer, lender, subsidiary and document publisher. The document's main company does not resolve every “it.” |
| Deixis | Resolve “we,” “this facility,” “here,” “last year” only with source-local referents. Preserve ambiguity if multiple candidates survive. |
| Reporting/comparison periods | Preserve both observation and comparison windows, quarter/year and duration. An annual source can discuss earlier quarters or future years. |
| As-of/publication dates | A dated note can scope a chart if applicability is established. Publication date cannot substitute for the measurement date. Preserve historical utterance time for forecasts and “currently.” |
| Fiscal/calendar periods | Keep source convention. Do not infer fiscal year end from calendar year or silently convert FY to calendar year. Explicit source definitions can support a conversion, with the original convention retained. |
| Actual/target/forecast/conditional | Preserve tense, uncertainty, scenario, conditions and forecast horizon. “Expects to bring online” cannot become “operates.” A target is not a forecast or achieved result. |
| Metrics | Revenue, bookings, remaining performance obligations, backlog and capacity are distinct. Carry source definitions when essential; do not substitute a familiar accounting definition. |
| Capacity state | Active, energized, contracted, under construction and planned remain distinct, including gross/net or customer-available bases. Contracted capacity does not assert active capacity. |
| Quantities | Preserve sign, currency, scale, rounding, approximations, inequalities, percentage versus percentage-point changes, denominator and comparison base. Unit conversion needs exact source-backed meaning and no added precision. Missing units are not guessed. |
| Geography/segment | Resolve only the relevant entity/segment/location. Consolidated issuer scope is not automatic; a local statement cannot become global. |
| Measurement basis | Preserve GAAP/non-GAAP, adjusted measures, gross/net, recognition rules and source-specific exclusions. Matching numbers alone cannot establish same metric. |
| Footnotes/qualifications | Attach material limitations to the assertion they constrain, with exact note/label/value association. Retain attribution and illustrative/estimate limitations. Neighboring footnotes do not all apply automatically. |

Quotation remains quotation only with disclosed changes consistent with existing
`edited_quotation` rules; a free rewrite is a source-grounded rendering and must be
shown as such. The context record must not relabel the frozen original representation.
Source quotations/citations stay available separately. Necessary attribution must be
explicit in standalone text; an adjacent category badge cannot repair an otherwise
misleading unqualified sentence. Preserve the scope of quoted
speech, named speaker, management/investor/media perspective, hedges, negation,
comparatives and material causal wording already asserted. Removing a discourse marker
is allowed only if no asserted causal/conditional relation or qualification is lost.

Seemingly harmless edits can change truth conditions: inserting “2025” can turn an
undated historical observation into a different claim; replacing “capacity” with
“active capacity” asserts operational status; expanding “backlog” to “guaranteed future
revenue” removes recognition conditions; dropping “management expects” changes both
modality and attribution. Necessary clarification is not license for these changes.

### Fixture-based illustrations, not authenticated financial claims

The following are design examples derived from
[semantic-coreweave.json](../tests/fixtures/sort/semantic-coreweave.json), particularly
`power-intro`, `power-execution`, `power-presentation` and `centers-presentation`, and
[document-12.md](../tests/fixtures/sort/document-12.md) /
[document-13.md](../tests/fixtures/sort/document-13.md). The JSON explicitly describes
hand-recorded judgments. These examples do not certify archived-source anchors or
live financial facts; future evaluation must revalidate offsets, hashes and layout
before treating them as evidence. No fixture labels are changed here.

- An already explicit issuer/active-power/year-end proposition remains exactly as
  written after independent review. No document summary is appended.
- An illustrative input “We ended the year with more than 850 megawatts of active
  power” can become “CoreWeave ended 2025 with more than 850 megawatts of active
  power” only if speaker identity and the referenced year are separately anchored.
  The surrounding passage also discusses contracted capacity and a prospective
  online date; neither belongs in this rewrite.
- The fixture's presentation power tile needs its active/contracted labels and
  applicable as-of note. A nearby publication date cannot supply the as-of date.
  Its illustrative-footprint qualification must be assessed for materiality, not
  silently dropped to match transcript wording.
- An illustrative “We expect virtually all of it to come online by the end of 2027”
  needs a verified antecedent for “it.” Even if the antecedent is contracted power,
  the result remains management's expectation; it does not assert active capacity
  in 2025 or guaranteed delivery in 2027.
- An issuer document quoting a customer's “we” is a hard negative for defaulting
  every first-person reference to CoreWeave. Ambiguous speaker evidence requires
  abstention, even if issuer metadata is present.

## Cursor generation and independent verification

Required future flow:

`existing extraction → per-proposition context proposal in that workflow → independent
source verification → verified context record → local retrieval and inference`.

Extend a single understanding response with a context proposal per existing selection,
using its stable selection key/index. Each includes the proposed status, standalone
text, edits with source IDs and unresolved reasons. Stock supplies original text from
the resolved selection; Cursor cannot overwrite it or invent anchor coordinates.
Batching many propositions is transport only. Each gets its own context and verdict;
a shared document summary is not an acceptable substitute. Long-document sectioning
and targeted source/layout retrieval remain available; missing cross-section evidence
requires abstention rather than filling gaps from another proposition's context.

The existing independent review operation must check two distinct matters:

1. Does the selected exact evidence support the original proposition, including
   attribution, qualifications and material financial dimensions?
2. Is the proposed standalone interpretation sufficiently clear, and does each
   replacement/insertion/deletion preserve the original contextual meaning? Does
   each edit's explicit evidence support both its content and its applicability?

The verifier sees original text/representation, attribution, exact original support,
proposed standalone text, edits and their supporting anchors/verified metadata. It
must be able to reject fluent but meaning-changing output. Generation's confidence
is not verification; a separate review call/work item is required, not self-certification
inside the generation response. Independence here means separate source-based review,
not a claim of statistically independent model errors or a requirement for a new model.

Deterministic checks validate response shape, one-to-one selection mapping, exact
source IDs/spans/hashes, edit application, byte preservation for unnecessary results
and version/fingerprint integrity. Human/model semantic judgment remains necessary
for meaning and sufficiency. Uncertain table/footnote associations use existing
original-layout evidence when necessary; converter descriptions alone are insufficient.

Review may retrieve missing support in the existing bounded repair workflow, followed
by independent review of changed proposals. If it still cannot establish a safe
interpretation, record unresolved and retain original/audit evidence. Do not accept
an almost-standalone sentence, discard an inconvenient qualification, or repeatedly
rewrite until it passes a similarity score. No Cursor calls for pairwise deduplication
are introduced. Context generation is not a pairwise semantic operation.

## Semantic inputs, caches and graph consumption

During migration and evaluation, retain raw embeddings alongside a separately named
contextual view. Compare raw retrieval, contextual retrieval and their candidate union
on the same inventory. A missing/unresolved context keeps the raw retrieval route;
it is not encoded as an empty sentence. Contextual candidates can improve discovery
but cannot bypass financial compatibility checks or authorize an edge by themselves.
Production retention of both indexes after evaluation is an open cost/recall choice.

For an eligible record the contextual embedding input is **exact standalone_text**,
without concatenated document summaries, neighboring propositions or hidden metadata.
The encoder contract identifies the input-view version and existing model/tokenizer,
preprocessing, pooling, dimensions and length policy. Raw and contextual views can
reuse identical numeric vectors only when exact input and effective encoder behavior
match; provenance must still identify which view was requested. Do not silently
change the current raw encoder contract's meaning.

Local NLI similarly consumes exact eligible standalone sentences in both orders.
Record the per-side input-view/context record association on the decision. Mixed
legacy/contextual comparisons may be inspected locally, but unresolved essential
interpretation must block automatic positive equivalence, entailment or contradiction.
Raw-only evidence remains usable for discovery, manual inspection and existing valid
historical views. Absence of context does not invalidate every historical decision;
new contextual decisions must not pretend those decisions were verified under this
contract. Keep unknown/unreviewed distinct from a reviewed UNRESOLVED edge.

Use distinct dependency identities: original evidence fingerprint, context record
revision, exact semantic input digest, model contract, decision policy and presentation
revision. Do not overload the passage ID or expand all cache keys with every field.

| Change | Required invalidation / reuse |
|---|---|
| Exact standalone bytes or selected raw/contextual input changes | Affected contextual vector/input mapping and ordered NLI inputs are stale; recompute missing artifacts only. Existing artifacts keyed to previous inputs remain valid historical work. Re-evaluate affected pair decisions and dependent presentation. |
| Context contract version changes | New context interpretation/review and view association required; decisions cannot be carried forward as approvals. If the exact text and effective model-input contract remain identical, numeric vectors/raw NLI outputs can be reused, with new associations. A version change altering actual model inputs/preprocessing requires new model artifacts. |
| Context status, resolutions, unresolved reasons, relied-on metadata, source support, attribution, qualifications or verification artifact changes | Revalidate context eligibility and affected decisions/presentation. Approval is stale if its bound inputs changed. Unchanged exact model inputs can retain numeric vectors/raw scores; evidence changes cannot be hidden by a text cache hit. |
| Original text, references, source hashes/versions or material document metadata changes | Existing source fingerprint changes under baseline rules; old context cannot attach without fresh binding/review. Retain prior evidence history. Reconcile manual corrections conservatively. Reuse only model computations whose exact inputs/contracts still match. |
| Encoder weights/revision, tokenizer/preprocessing, pooling, normalization, dimensions or effective length policy changes | Recompute vectors under the changed encoder contract and dependent candidate scores/frontiers. Do not invalidate unrelated NLI with identical inputs/model contract. |
| NLI weights/revision, tokenizer, pair formatting/order, length policy or score/label semantics changes | New inference contract; affected raw inference and downstream decisions stale. Reverse input order must never be mistaken for the same directional output. Embeddings remain valid. |
| Financial parser/safeguards, accepted context-to-attribute projection or relationship policy changes | Re-evaluate affected decisions using current approved evidence/context and retained compatible raw inference. No automatic model rerun merely for a threshold/policy change. |
| Candidate inventory, retrieval policy or refinement frontier changes | New affected candidate run/scores/coverage accounting. Preserve valid previously reviewed edges and raw artifacts; deferred pairs stay unreviewed. Do not rerun unrelated unchanged–unchanged inference during replacement. |
| Manual relation/split/topic correction or presentation policy/filter changes | New relevant presentation revision/view and decision reconciliation where applicable. No vector/NLI invalidation unless semantic inputs changed. Topics do not authorize equivalence. |

Relationship decisions depend on both current source fingerprints, accepted context
record identities/eligibility, exact input associations, raw inference contract/output,
financial decision policy and manual corrections. Presentation revisions depend on
the evidence/context inventory, current decisions, suppression/override state,
canonical-selection/grouping policy and checked publication snapshot. Updating those
dependencies creates a new immutable revision; never edit an old revision in place.
A stale component must not silently remain active as a newly verified result. Failure
leaves the previous complete active revision available for rollback.

Similarity selects candidates. Mutual entailment may support EQUIVALENT only after
material dimensions and both directions pass the applicable validated policy;
probabilities alone cannot establish equivalence. One-way ENTAILS retains direction,
both underlying statements and both presentation rows, including the less informative
statement's independent source/presentation value. CONTRADICTS requires compatible
entity/metric/period/scope and an actual incompatible assertion; different numbers or
periods alone are insufficient. RELATED preserves thematic association without logical
claims. UNRESOLVED preserves uncertainty. No similarity chains or transitive NLI closure
establish equivalence.

Continue complete-link supported equivalence grouping with original member IDs and
all formulations/citations accessible. Canonical display wording must be an actual
member's approved rendering with its original available, never a synthesized group
claim. Context revisions may split groups; manual splits remain vetoes. Grouping is
reversible and cannot delete evidence. Do not force a target group count.

## Smallest coherent migration

1. Add the context response/review contract within current knowledge operations, in
   disposable databases/artifacts first. Retain original selection schemas and
   representation semantics; explicitly version changed generation/review inputs so
   old artifacts cannot masquerade as context approvals. Preserve intact unchanged
   claim-review work where its exact inputs still satisfy the old task; a new context
   judgment is separate work, not an excuse to erase earlier verification.
2. Associate immutable context JSON records with staging/published proposition IDs
   outside frozen passage locations. Existing JSON artifacts can carry the disposable
   pilot; evaluate durable association/lookup before production. Do not repurpose a
   graph revision as the sole evidence store: context must survive graph regeneration.
   No immediate archive-wide backfill is required.
3. Add an explicit read adapter: absent records return `not_attempted`, original text,
   no accepted edits and `not_checked` context review. Sources continues to show exact
   original evidence/citations; future UI can expose original/standalone/context status
   separately. Historical `legacy_exact_source` does not become a new context approval.
4. Add versioned contextual retrieval and local inference views in shadow mode.
   Preserve raw caches, existing graph heads, exact passage IDs and original anchors.
   Replace heuristic `semantic_context` assumptions only with verified projections;
   reject inconsistencies rather than union attributes from every supporting paragraph.
5. Only after evaluation, activate the chosen context association, verified evidence
   and dependent graph/presentation head in one checked publication boundary. Preserve
   existing hash/snapshot checks, review-only behavior, history, incremental replacement
   and refinement. Context-only updates must not rewrite original passage identity.

Manual relationship corrections, split tombstones and topic overrides remain audited.
An unchanged exact evidence identity retains corrections. If meaning-bearing context
changes under the same evidence ID, retain the correction record but require review
before reusing a positive logical override; do not let an old equivalence override
new ambiguity. Keep presentation split vetoes unless explicitly corrected. For an
actual evidence replacement, continue unique exact anchor/category/speaker matching;
ambiguous transfer blocks publication and retains old evidence/corrections for review.

Staging, cache writes and partial context completion do not activate evidence or a
partial presentation. Recheck evidence, context selection, corrections and head snapshots
immediately before atomic publication. A source-file change, stale review or concurrent
correction aborts activation. Rollback selects a prior coherent evidence/context/head
association; immutable historical revisions/artifacts remain readable. The durable
association must support that atomicity before production adoption, even if a later
additive schema change is needed. No schema change is specified or performed here.

## Acceptance and evaluation design

Evaluate correctness before retrieval gains. A fluent rewrite or increased reduction
count is insufficient. Separate human semantic judgments from executable invariants.

### Human review criteria

Reviewers first see the candidate alone, without the source title or neighboring
claims, to judge whether all material referents are understandable. They then inspect
original wording in exact source context, edits and supporting evidence to assess:

- Same truth conditions, including speaker/perspective, quantifiers, modality,
  negation, causal scope and material qualifications; no new investment inference.
- Every necessary reference resolved and every addition/deletion applicable and
  supported; no unrelated summary facts or neighboring-claim leakage.
- Correct issuer/counterparty, reporting/comparison/as-of periods and fiscal basis;
  publication dates do not leak into measurement dates.
- Preserved metric definitions, measurement basis, quantity/unit/rounding, segment,
  geography, footnotes and active versus prospective status.
- Appropriate unchanged result or abstention; unresolved reasons identify the actual
  missing evidence rather than merely calling the text low confidence.
- Pair decisions preserve meaningful one-way entailment, disagreements and distinct
  provenance; groups remain useful without hiding less informative statements.

Use two independent reviewers for the small pilot, record disagreement and adjudicate
with source evidence; permit multiple valid rewrites. Review content correctness and
standalone sufficiency separately from grammar/conciseness. Blinded raw/contextual
comparisons reduce preference for the new method. These are Stock pilot procedures,
not claims that the paper prescribed this financial review protocol.

### Automatically testable invariants for subsequent phases

- One context result per selection; no unknown/duplicate IDs. Exact original bytes,
  representation, source identity and citation offsets/hashes survive round trips.
- Edit ranges are valid/nonoverlapping, apply to the bound original and reproduce
  standalone text. Every edit has resolvable evidence; deterministic validation cannot
  certify that the evidence is semantically sufficient.
- Unnecessary preserves exact text with no edits; unresolved retains original with
  specific reasons; absent legacy records adapt to not_attempted. Unsupported or
  pending/rejected review cannot enter the verified contextual path.
- Context generation/review cache reuse requires exact bound inputs/contracts.
  Altered issuer, period, unit, qualification or evidence breaks approval even when
  fluent text survives. Transport rebatching alone preserves valid per-claim work.
- Targeted mutation tests exercise each dependency in the invalidation table; unchanged
  unrelated vectors, raw NLI outputs, corrections and revisions survive. Identical
  texts with changed evidence reuse computation but cannot reuse stale decisions.
- Context updates preserve passage IDs and original citation opening. Legacy archives
  remain readable without backfill. No context record gets written into frozen
  `location` as an incidental convenience.
- Stale source/head/context/correction snapshots, interruptions and publication failures
  activate nothing partial; resume reuses completed work and rollback restores a
  coherent view. Manual correction transfer ambiguity blocks replacement.
- Both NLI directions and exact input versions are recorded; overlength inputs follow
  explicit existing failure/unresolved policy, never silent truncation. Absent pairs
  are unreviewed, not negatives. ENTAILS retains both nodes/rows; grouping and ungrouping
  preserve every original citation and manual split veto.

No automatic invariant alone proves truth-condition preservation. Use deliberately
mutated prospective/actual, entity, period and metric pairs to test safeguards against
unsafe merges; retain human adjudication for semantic acceptance.

### Pilot dataset and measurements

Design a small, separately versioned pilot of approximately 24 source-context cases,
with several associated pair comparisons; do not generate or label it in Phase 1.
Select from existing CoreWeave transcript/presentation fixtures and a second issuer
source to expose main-company bias. Revalidate exact anchors against the chosen
fixture version; archived production provenance requires its own checks. Keep replay
fixtures, newly adjudicated source examples and actual-inventory shadow results
separate. Existing labels remain untouched.

Balance unchanged, resolvable and abstention cases. Cover pronouns, quoted customer
identity, year-end/quarter comparisons, publication versus as-of dates, fiscal/calendar
ambiguity, actual/forecast/conditional capacity, revenue versus backlog/bookings,
GAAP/non-GAAP, approximate quantities, footnotes, table label association and mixed
neighboring issuers/periods. Include hard negatives that differ in just one material
dimension, genuine paraphrases with low lexical overlap, a more/less informative
entailment pair, thematic-only pairs and genuinely unavailable/ambiguous evidence.

Each case stores original text/representation, source snapshot and exact evidence,
necessary dimensions, feasible state with reasons, allowed interpretations/edits and
review/adjudication history. Pair labels are separately reviewed and directional;
contextualization labels do not imply pair equivalence. Keep a small held-out subset
separate from prompt/policy tuning and report case counts, exclusions and disagreements.
Do not choose only examples that the current model already handles.

Report standalone sufficiency, meaning preservation, unsupported-edit frequency,
unnecessary-edit rate, correct abstention and financial-dimension errors separately,
with counts and uncertainty. Length/edit rates and optional multi-reference edit metrics
are diagnostics, not safety gates or desired edit quotas. For retrieval, compare raw,
contextual and union recall of adjudicated relevant/entailing pairs at matched review
budgets, alongside candidate workload and missed hard positives. Report unsafe logical
decisions/groupings independently; no claimed gain from a smaller group count. Evaluate
preservation of one-way entailment and distinct presentation rows explicitly.

Mandatory fixture gates are zero known unsupported additions, meaning-changing accepted
rewrites, unsafe merges, lost citations/identities or lost corrections; all designated
unchanged and abstention cases must behave as adjudicated. This small-pilot gate is
not a statistical production-safety claim. Empirical recall/calibration targets and
acceptable workload must be set from baseline measurements before inspecting held-out
results; they are not arbitrary thresholds established in this specification.

## Bounded implementation roadmap and remaining choices

Mandatory architecture is original evidence preservation, proposition-specific minimal
edits, independent source review, explicit abstention, separate model/decision identities,
local pair inference, reversible graph views and atomic publication. Storage/index
optimizations and broader model experiments are optional and cannot weaken these rules.

| Phase | Entry criteria | Work and exit gate |
|---|---|---|
| 2: extraction and verification pilot | This version committed; disposable storage and authenticated source evidence isolated from production; pilot protocol fixed. | Extend existing multi-selection generation and independent review with context proposals/records; implement legacy adapter and exact evidence/edit binding. Demonstrate all context-state and financial safety cases, original identity preservation, resume and stale-review rejection. Use disposable evidence only; publish no production migration. Define/test a durable context association plan before advancing. |
| 3: contextual retrieval and local NLI | Phase 2 integrity gate passes; small adjudicated/held-out pilot exists with raw baseline. | Add explicit contextual input views, parallel raw evaluation, verified attribute projections and dependency-specific cache reuse. Demonstrate invalidation matrix, both directions, abstention safeguards, retained one-way relations and complete-link reversible views. Report matched-budget recall/workload and unsafe-decision counts; no model/threshold change justified solely by grouping yield. |
| 4: inventory shadow and controlled migration | Phase 3 passes; measured targets fixed and existing financial rollout blockers explicitly reviewed. | Evaluate actual inventory without activating changed evidence/head; stratify historical missing context and source/layout ambiguity. Establish rollback/atomic association, correction reconciliation and incremental/backfill policy on disposable copies. Production adoption requires explicit authorized scope and passing measured integrity, semantic and presentation gates. Migrate bounded cohorts; no blanket archive reprocessing. |

Resolved decisions: explicit standalone text plus original and edit evidence; unchanged
text preservation; separate support/preservation judgments and abstention; no generic
summary or automatic financial-field completion; identity-external context records;
raw/contextual coexistence for evaluation; no Cursor pairwise deduplication; existing
graph and atomic replacement architecture retained.

Open engineering choices, with decision criteria:

- **Durable context association:** reuse versioned JSON artifact payloads with an
  atomic association versus a later additive context table. Choose the smallest
  approach demonstrating lookup, historical retention, checked activation/rollback,
  stable IDs and incremental updates. Phase 2 must not solve this by altering location.
- **Context breadth and repair cost:** current heading-aware source packing versus
  selectively broader source retrieval. Compare unresolved/incorrect-context rates
  and request cost on cross-section examples; never truncate necessary evidence to
  hit a call quota. No new arbitrary global-context length is mandated here.
- **Long-term retrieval view:** contextual alone versus raw/contextual union. Choose
  using held-out recall, ambiguity coverage and workload, preserving raw historical
  artifacts and evidence identity in either case.
- **Financial policy calibration and optional model changes:** existing probabilities
  remain uncalibrated. Separate experiments must establish directional error behavior
  on financial hard negatives and paraphrases before changing policy/models. This
  contract chooses neither new models nor thresholds.
- **Production acceptance targets and cohort size:** set from measured baseline,
  reviewer agreement and operational rollback capacity before rollout; the pilot's
  zero-known-integrity-error gate alone cannot justify production readiness.

Meaning preservation and evidence integrity take precedence over retrieval reduction,
latency targets and any predetermined number of presentation groups. A subsequent
implementation must satisfy this version or explicitly revise the governing contract;
it must not redefine contextualization independently in extraction, inference or UI.
