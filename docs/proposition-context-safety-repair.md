# Phase 2.6 safety repair — Phase 3 BLOCKED

The governing contract remains [proposition-decontextualization.md](proposition-decontextualization.md), with [Phase 2](proposition-context-phase2.md) and [Phase 2.5](proposition-context-validation.md) retained unchanged. This repair starts at `a82d806` on `feature/persistent-semantic-map`. It changes no semantic requirement and performs no Phase 3 work.

## Root cause and regression

Before changing code, direct validation and the disposable historical replay reproduced `cw-we`: `[4,6]` selects `We` inside `CoreWeave`, produces `CoreCoreWeaveave`, passes structural validation, and becomes eligible with the recorded positive verdict. Validation checked offset ranges, overlap, reconstruction, source-ID existence and quantities, but not whether a referential edit selected a complete expression. Source-ID existence did not establish support or applicability.

The current `stock.proposition_context` rejects this target before independent review. The same check runs before finalization writes any artifacts, on checked reads/manifests, and in the eligibility predicate, so a historical accepted verdict cannot authorize it. Prior immutable artifacts remain intact; a disposable historical-artifact regression proves lookup fails closed and cached generation is revalidated without requests or artifact changes.

Policy identifier: `stock-proposition-context-1:edit-safety-2`. Generation/review contracts retain their existing semantics and identities; completed valid work remains reusable. Every reused proposal still crosses current validation. No historical judgment is silently rewritten or converted into a new semantic judgment.

The lexical safeguard examines actual edited text, ignoring the free-text purpose. English pronouns and demonstrative/possessive-led phrases must have complete outer lexical boundaries. Unicode letters, marks, numbers, connector punctuation and format controls cannot disguise a word interior. Cuts inside combining sequences are rejected; strings and offsets remain exact Python Unicode code points without normalization. Attached contractions require the complete expression; closing quotation punctuation remains allowed. This is a bounded English lexical guard, not a general multilingual parser or proof of grammaticality.

Three distinct outcomes remain:

- Invalid coordinates, combining boundaries or incomplete referring expressions: deterministic rejection, even with a positive review.
- Structurally valid but unsupported additions: existing quantity checks reject detectable unsupported values; other unsupported content/applicability requires independent source-based rejection. Lexical evidence matching cannot establish truth conditions.
- Valid coordinates with uncertain meaning: independent semantic review remains mandatory. A wrong issuer, a sourced but inapplicable period, forecast-to-actual wording or contracted-to-active capacity can pass lexical checks and must still be rejected semantically.

## Compatibility and disposable results

[Versioned follow-up assessment](benchmarks/proposition-context-safety-repair-v1.json) records old and new outcomes separately, without regenerating the raw baseline or overwriting Phase 2.5. Of 24 previously observed cases, only `cw-we` changes deterministic acceptance. The other 23 proposals remain structurally valid; this includes the three previously opened heldout cases, which remain development evidence.

The focused compatibility set accepts **15/15** intended legitimate edits (zero observed false rejection): standalone/case-varied pronouns, punctuation, emoji/Unicode quotation boundaries, possessives, whole contractions, multiword noun phrases, name insertion, partial-token name completion, partial-token deletion and discourse-marker deletion. Twelve malformed boundary cases are each rejected under two different purpose labels. Two additional regressions reject punctuation-prefixed targets and adjacent split edits, treated as one effective replacement. An additional lexically valid wrong-referent case remains reviewable and is rejected by the injected independent verdict. Repeated identical pronouns retain exact coordinate targeting. These small authored cases establish compatibility observations, not a population false-rejection rate or semantic correctness.

The current disposable end-to-end replay retains 20 of 21 development proposals: seven unnecessary, three resolved and ten unresolved. `cw-we` is excluded before review; ten records have recorded accepted verdicts, six rejected and four unresolved. All three source runs resume with **zero requests and zero new artifacts**; exact original citations and passage identities survive checked manifests. Review verdicts are injected expectations, not human accuracy measurements. The historical 21-proposal/11-eligible replay and its test observation are preserved; the test separately checks the new 20-proposal/10-eligible behavior.

## Speaker attribution

The Microsoft Filing atom `d203:0f4e339342d4fc63:0:1132` still contains issuer narration and quotations from both Nadella and Hood. Their names and roles are present, but `speaker`/`turn` are null. Current-code replay retains all three `Unsupported speaker` exclusions. No entire paragraph is assigned to either executive.

Exact quotation-level boundaries are possible in principle without replacing the parent atom: add an external, versioned mapping of parent ID/hash to exact quotation ranges, exact attribution ranges/name/role and explicit continuation links. Validate every slice against unchanged source bytes; reject overlap, ambiguity and cross-speaker support, bind the mapping into generation/review provenance, and keep original citation identities unchanged. Selections would need an explicit checked way to cite these subranges while preserving parent references.

That is a source-envelope/selection design change, not a safe one-line parser fix. This excerpt mixes curly opening and straight closing quotation marks, postposed attribution, and a continued Nadella quotation after the attribution. Generic quote pairing or name occurrence cannot safely establish all speaker boundaries. No such mapping currently exists in the selection contract; adding guessed speakers to the existing atom would weaken attribution. Conservative rejection remains. This limits those named-speaker examples, not the ability to conduct independent human review of their exact source text.

## Human review and packet usability

**Zero human reviews or adjudications have occurred.** Both existing 28-case packets remain unchanged and their source hashes were checked. Stage 1 remains blinded and unfilled; stage 2 and adjudication fields remain pending. Human review can proceed now; no authenticated model access is needed for it.

Verification found an existing packet anchor typo in the four historical live examples, in both reviewers' stage 2: reference `[0,1132]` contains the full 1,133-code-point file including its final newline. The [versioned stage-two erratum](benchmarks/proposition-context-review-packet-errata-v1.json) supplies the exact 1,132-code-point reference text while preserving IDs, offsets, source bytes and judgments. Give this erratum only with stage 2, after stage 1 is locked. Full source context remains available at the recorded source path/hash.

`cw-we` (`case-003` in both packets) requires renewed acceptance-policy evaluation: its historical candidate remains reviewable evidence of failure but is ineligible under current code. Any corrected standalone candidate needs fresh blinded sufficiency assessment and source-based meaning-preservation review by both humans; no corrected candidate is substituted into these packets. The remaining cases still need their original pending human reviews; their deterministic policy outcomes did not change. The four live source references require the erratum, not fabricated semantic reassessment.

All three opened heldout cases remain observed development evidence. If untouched evaluation is subsequently required, independently select new source passages excluding all opened fixture/live examples, freeze exact anchors and criteria before outputs or tuning, and obtain two independent blinded reviews plus evidence-based adjudication. No new untouched set is claimed here. The frozen baseline must remain unchanged.

## Transport

The retained authenticated attempt used a hard four-request budget, attempted one request, and timed out after about 117.65 seconds (effective process timeout 117.62 seconds), with zero stdout/stderr and no response artifacts or provider usage. This is a transport completion failure; there is no semantic output to score.

`Budget` shares request deadlines across retries and bounds document/command time. `DeferredCursor` counts requests before starting the transport. `sort_process.run` terminates the process group on timeout, escalating to kill if needed. Cursor uses an empty disposable workspace, ask mode, JSON output and denied shell/read/write/web/MCP permissions. Authentication/preflight time uses the same remaining request budget. `Operations.extract` marks failed attempts and stores responses only after completed schema validation and source recheck. Claim-review caching requires complete, validated batches; failures cannot create partial approvals or completed coverage.

Focused tests cover partial stdout on a real disposable Python child timeout, both process-timeout and budget-timeout failures at generation and review, and retry/resume: incomplete generation is requested again; a failed review reuses only completed generation; completed final resume makes no calls. No transport runtime change was needed. **No new authenticated requests were made.** A future separately authorized bounded demonstration still needs an actual resolved edit, separate source review and successful request-free resume; recorded replay cannot supply it.

## Verification and evidence integrity

The initial safety regression failed against the old validator before implementation. A serial focused run passed **246 tests** across context, Phase 2.5 validation, new repair, knowledge, editorial, transport efficiency, evidence and budget tests. After adding timeout/packet assertions and review-discovered boundary regressions, the final serial run of those same eight focused files passed **254 tests**. A separate read-only software review found no remaining important issues; it is not human semantic adjudication. An earlier overlapping pytest run had a temporary-file setup error because both processes used the repository's fixed `.data/test-tmp`; it was rerun serially. This was test-directory contention, not a semantic or production failure.

Reproduce without authentication or production writes:

```sh
.venv/bin/python -m pytest tests/test_proposition_context_safety_repair.py tests/test_proposition_context.py tests/test_proposition_context_validation.py tests/test_sort_budget.py -q
.venv/bin/python scripts/pilot_proposition_context.py /tmp/context-repair-replay.json
```

The separately versioned assessment script refuses to overwrite its outputs. The frozen baseline remains available with SHA-256 `599599f06d2f7842435d70b3f72d5d0d8732d4ef22dd648362130814f79461e1`. Historical assessments, captured Cursor responses, original fixtures, gold labels and prior immutable context artifacts are unchanged. The final read-only snapshot matches all 245 production SQLite/archive files, with no additions or deletions. Existing focused tests retain checked manifest lookup/rollback, cache/rebatch/resume behavior, manual topic/split corrections and historical publication behavior. No production Store was opened, document 13 rebuilt, context records activated, embeddings/NLI/graph changed, or production/archived evidence rewritten. PR #1 remains draft and unmerged.

## Readiness gates

| Gate | Result |
| --- | --- |
| A. Deterministic safety | PASS within tested scope: known malformed edit rejected; legitimate edits preserved. Lexical checks do not prove meaning. |
| B. Semantic validation | BLOCKED: two independent human reviews and adjudication remain absent. |
| C. Retrieval baseline | AVAILABLE, frozen and hash intact; not regenerated or tuned. |
| D. Authenticated resolved demonstration | NOT COMPLETED: historical success was unnecessary text; later request timed out. |

**Phase 3: BLOCKED.** The focused deterministic repair is technically tested. Human semantic acceptance and the authenticated resolved-edit demonstration remain unsatisfied. No perfect resolved-proposition count is required, and no Phase 3 work is begun.
