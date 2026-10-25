# Phase 2.5 validation: BLOCKED

The single normative source remains [proposition-decontextualization.md](proposition-decontextualization.md).
A standalone proposition must be independently interpretable while preserving the
original proposition’s truth-conditional meaning in its source context. This validation
changes no model, threshold, candidate frontier, financial policy or production path.
The research authority remains [Choi et al. (2021)](https://aclanthology.org/2021.tacl-1.27/);
its standalone/meaning-preservation definition does not establish financial reliability.

**Phase 3 is BLOCKED.** Independent human adjudication is missing, the opened heldout
assessment is recorded replay rather than independent semantic acceptance, and a known
unsafe rewrite is accepted by the historical recorded judge. The additional authenticated
attempt timed out before producing a proposal. Passing software tests does not close
these gaps. No Phase 3 work was started.

## Evidence and provenance

[Machine-readable summary](benchmarks/proposition-context-validation/summary.json)
separates deterministic checks, recorded simulation, authenticated observations, human
conclusions and unresolved claims. [Per-case assessment](benchmarks/proposition-context-validation/assessment.json)
contains all 24 originals, proposals, exact edit substrings, supporting atoms, source
references, resulting records and pending dimension-specific human forms.

The original pilot comprises 12 transcript cases, six presentation cases and six
Microsoft release cases (including the three reserved cases). CoreWeave source bytes
are repository fixtures, **not newly authenticated issuer disclosures**. Microsoft’s
existing [provenance](../tests/fixtures/proposition-context/microsoft-provenance.json)
records the official release URL, extraction procedure and hashes. All three source
hashes and every original/edit anchor were rechecked against exact fixture bytes.
The twelve new [financial counterfactuals](../tests/fixtures/proposition-context/phase25-safety.json)
are separately authored development data, not historical relabeling or authenticated facts.

The Phase 2 results reconcile: 24 cases, 21 exercised, three reserved; seven unnecessary,
four resolved, ten unresolved; 11 recorded accepted, six rejected, four unresolved reviews.
All 21 originals were recorded supported. Completed resume made zero transport requests.
A fresh focused run reproduced **164 passed**. These are executable recorded-response
expectations, not model accuracy or human adjudication.

## Frozen raw retrieval baseline

The protocol and baseline were written and committed as `c41a044` **before opening
heldout outcomes**. This timing applies to this validation run; the fixtures necessarily
contain historical proposals and expectations authored in Phase 2. No prompts or rules
were tuned against the opened cases.

[Protocol](benchmarks/proposition-context-validation/protocol.json),
[baseline](benchmarks/proposition-context-validation/raw-baseline.json),
[SHA-256](benchmarks/proposition-context-validation/raw-baseline.sha256):

```
599599f06d2f7842435d70b3f72d5d0d8732d4ef22dd648362130814f79461e1
```

The existing pinned BGE contract, cosine scoring, empirical-tail-plus-structured-v3
candidate discovery and **frontier 0** were unchanged. Each development inventory
was evaluated separately with all its IDs incoming, on fresh disposable SQLite.
The local NLI model and financial decision policy were identified but not invoked:
this measures retrieval, not final equivalence classification.

| Development inventory | Statements | Scored pairs | Default candidates | Material labels retrieved |
| --- | ---: | ---: | ---: | --- |
| Existing CoreWeave grouped fixture | 13 | 78 | 13 | 5/5 equivalent |
| Existing authored financial challenge | 32 | 496 | 93 | 2/2 equivalent; 2/2 one-way entails; 2/2 contradicts |

Default material misses: none under these existing development labels. This is not
population recall or newly adjudicated label correctness. CoreWeave’s other eight
retrieved pairs have existing non-equivalence expectations; they are not thereby
proven unrelated. The challenge’s one explicitly RELATED pair was **not retrieved**;
most other candidate pairs are unlabeled and cannot be counted as false positives.
Similarity does not distinguish equivalence from thematic relationship. One-way
entailment coverage means retrieving the labeled pair; no inference direction was
verified by this retrieval measurement.

Review budgets were fixed at 10, 25, 50 and 100 before opening heldout outcomes.
Candidates are ranked by persisted cosine with lexical ID tie breaks, within the
unchanged default candidate set; budget is a maximum, not forced extra retrieval.

| Inventory/budget | Actually reviewed | Equivalent | One-way entails | Contradicts | Material recall |
| --- | ---: | --- | --- | --- | --- |
| CoreWeave / 10 | 10 | 4/5 | n/a | n/a | 4/5 |
| CoreWeave / 25, 50, 100 | 13 | 5/5 | n/a | n/a | 5/5 |
| Challenge / 10 | 10 | 1/2 | 0/2 | 0/2 | 1/6 |
| Challenge / 25 | 25 | 2/2 | 1/2 | 0/2 | 3/6 |
| Challenge / 50 | 50 | 2/2 | 2/2 | 0/2 | 4/6 |
| Challenge / 100 | 93 | 2/2 | 2/2 | 2/2 | 6/6 |

The baseline persisted 40 unique 384-dimensional vectors (61,440 vector bytes):
13 computed in the first inventory and 27 in the second; five duplicate texts
within the challenge inventory share vector computation. Local elapsed time including immediate cache checks was approximately 2.54 s;
embedding work was 2.23 s and 0.11 s respectively, including model initialization in
the first run. The numeric model files were already locally cached. Both resumes
computed zero vectors and zero pair similarities. No Cursor/NLI calls or billed
embedding service costs. No arbitrary merge-count or recall acceptance target is imposed.

## Speaker diagnosis

The historical authenticated capture generated four proposals. Three failed
`Unsupported speaker` before independent review; one unchanged announcement reached
a separate model review and was accepted. Current-code replay reproduces this.

All three exclusions bind **the same atom**, `d203:0f4e339342d4fc63:0:1132`.
Its exact bytes contain issuer narration, Nadella’s two quoted assertions and Hood’s
quote. There are no transcript participant headers or speaker turns. `prepare_atoms`
correctly retains the entire Filing paragraph, but its structured `speaker`, `role`
and `turn` are null. `editorial.resolve_selection` requires the supplied name to match
every substantive selected atom’s speaker. Neither executive can be assigned to the
whole mixed atom.

| Selection | Exact source attribution | Diagnosis |
| --- | --- | --- |
| Cloud/AI positioning | “said Satya Nadella” and Microsoft CEO role | Name is correct in source; structured identity unavailable in mixed atom |
| Azure annual revenue | Same Nadella quotation and role | Same envelope limitation; also explicit unresolved “this year” ambiguity |
| Cloud fiscal-year close | “said Amy Hood” and Microsoft CFO role | Name is correct in source; structured identity unavailable in mixed atom |

Thus A (incorrect model name) is not evidenced. B applies to the available structured
atoms; C applies to attribution granularity lost between exact quote text and the
speaker envelope, **not loss of source bytes or citations**. D describes a representational
limitation for inline quoted Filing speech, but bypassing it without finer anchored
quote boundaries is unsafe. E is not established for these names; period/attachment
ambiguities still require their own review. The checks do not establish the full
propositions’ support. Rejection is conservative and appropriate for this envelope.
No speaker rule was weakened and no runtime speaker-parser correction was justified
by a safe tested boundary mapping in this phase. Regressions explicitly reproduce the
mixed-atom exclusions and distinguish analyst turns from management and issuer identity.
A future correction must anchor each quotation and its attribution separately.

## Semantic assessment and a failed integrity gate

**`cw-we` is a known unsafe accepted replay result.** Original:

```
CoreWeave management said: We contracted close to 2 gigawatts of additional power in 2025.
```

The fixture edit `[4,6] -> CoreWeave` targets `We` **inside the issuer’s name**, not
the pronoun. It produces:

```
CoreCoreWeaveave management said: We contracted close to 2 gigawatts of additional power in 2025.
```

The malformed entity is absent from the source. Exact offsets, edit application and
source-ID existence all pass, and the injected recorded review accepts it, so current
`pc.eligible` returns true. That is a demonstrated limitation of trusting a positive
semantic verdict, not proof that the live model generated or accepted this error.
The assessment records one known unsupported/meaning-changing accepted rewrite and
excludes **all unadjudicated records** from the validation-approved downstream set.
There is no production downstream integration to activate. No historical fixture or
judgment was changed, and no universal prohibition on substring edits was invented.
A lexical-boundary audit flag identifies the defect for review without claiming to
solve semantic preservation generally.

Deterministic completion covers all 24 cases: source hashes, exact anchors, original
bytes, edit reconstruction, identity preservation, checked review binding, coherent
manifest lookup and completed resume. These properties do not supply semantic passes.
For standalone sufficiency, truth preservation, applicability of edit evidence,
financial fidelity and fluency, the human counts are **zero completed and 24 pending**,
not zero correct. Codex source inspection identifies the malformed issuer failure;
other semantic pass counts and reviewer agreement remain unestablished. Recorded
accepted/unresolved/rejected totals must not be aggregated into an accuracy percentage.

## Opened heldout results

The three cases were executed once as a separate disposable replay after freeze,
using the existing proposal and verification policy, with recorded responses.
Each source had one extraction/review pair and zero requests on completed resume.
Originals, exact evidence, unchanged outputs, missing information and stored verdicts
are in the assessment. There are no edits or newly added words in these three outputs.

| Case | Interpretation / recorded result | Independent human result / downstream safety |
| --- | --- | --- |
| `cw-heldout-qualification` | Original management-attributed latent revenue statement retained; unnecessary, recorded accepted; “as built and delivered” retained | Pending; not established safe |
| `cw-heldout-table` | Original label-list statement retained; unresolved label/value association needs original layout | Pending; ineligible |
| `ms-heldout-customer` | Original Nadella-attributed Azure statement retained; unresolved fiscal/calendar “this year” | Pending; ineligible |

No unsupported addition or changed meaning is mechanically introduced by these
unchanged outputs; correctness of the original reconstruction still requires review.
The last case’s historical ID is misleading: it contains a CEO quote, not customer
speech. The new customer-speaker counterfactual covers that separate development risk.
There was no fresh authenticated generation/review of heldout cases. Recorded execution
is not the missing independent semantic gate. All three are now opened and cannot be
reused as untouched test cases after corrections. Three cases cannot establish a
reliable population-level error rate.

## Human reviewer materials

Two separate packets cover 24 fixture cases plus all four historical authenticated
proposals, including excluded proposals. No human reviewer was available in this run;
no reviewer decisions, confidence, agreement or adjudications have been invented.

- Reviewer A: [stage 1](benchmarks/proposition-context-validation/reviewer-A/stage1.json), [stage 2](benchmarks/proposition-context-validation/reviewer-A/stage2.json).
- Reviewer B: [stage 1](benchmarks/proposition-context-validation/reviewer-B/stage1.json), [stage 2](benchmarks/proposition-context-validation/reviewer-B/stage2.json).
- [Adjudication form](benchmarks/proposition-context-validation/adjudication.json).

Give each reviewer only their stage 1 first. It contains opaque IDs and proposed
statements without sources, originals, expectations or outcome-bearing case names.
Lock sufficiency, fluency, confidence and reasons before releasing stage 2. Stage 2
contains source paths/hashes, exact originals, references and edits, with individual
fields for A–E and financial dimensions. Reviewers must consult full referenced source
context. After both reviews are locked, an adjudicator records dimension-specific
disagreements and evidence-based resolutions. A null field is pending, never agreement.
Grammar/conciseness and content correctness are separate.

## Additional authenticated attempt and costs

[Capture](benchmarks/proposition-context-validation/authenticated.json) retains exact
source slice offsets, payload, prompt hash, process diagnostics and production DB hashes.
The source is a disposable concatenation of unchanged transcript slices: participant
identity, executive turn header and genuinely context-dependent execution paragraph.
It remains repository fixture evidence, not a newly authenticated CoreWeave disclosure.
A targeting instruction requested a verbatim original; governing generation/review
prompts and acceptance rules were unchanged. Cursor ran through the existing read-only
transport with a disposable empty workspace and source/database copies.

A hard four-request phase budget was set. **One** new request was attempted; it timed
out after approximately **117.65 s**, with zero stdout bytes and no response artifacts.
No further attempt was made. Prompt: **7,650 characters**. Provider token usage and
billing were unavailable, **not zero**. No live resolved edit, source-grounded resolution,
separate verification, accepted/rejected record or completed-resume chain was observed.
There was no completed generation artifact to reuse. That limitation is not repaired
by claiming the successful recorded replay as authenticated success.

Historical Phase 2 usage remains separate: extraction 11,564 input / 9,415 output tokens;
review 11,388 input / 1,638 output. Those are previously captured provider fields,
not costs incurred here. Historical authenticated-response replay continues to verify
request-free completed resume on current code. Pairwise Cursor deduplication requests: zero.

## Financial safety and integrity

Twelve new counterfactual regressions cover neighboring issuer, customer versus management,
fiscal/calendar year, publication/measurement date, forecast/actual, contracted/active,
bookings/revenue/caveats, currency/scale/inequality/rounding, GAAP/adjusted definitions,
footnote attachment, missing comparison periods and multiple antecedents. Where the
quantitative validator cannot reject mechanically, a **recorded rejecting verdict**
exercises safe abstention and original retention. These do not establish actual model
discrimination. A supported original remains supported when its contextual proposal is
rejected; no rejected proposal becomes an eligible accepted record.

The existing and new focused checks establish unchanged exact source citations, original
text and passage IDs; rejected-proposal audit retention; legacy `not_attempted` behavior;
changed evidence/edit/speaker/metadata invalidation; generation/per-claim review cache
reuse; interrupted review and partial-generation resume; immutable association lookup
and rollback without a production head. Additional tests mutate nine document metadata
fields, including issuer-related ticker/publisher/provenance and source paths/hashes.
Existing disposable tests cover publication history, topic overrides, split corrections,
replacement reconciliation and rollback. No new source location field or schema was added.

The additional authenticated attempt’s before/after production SQLite SHA-256 matches.
A subsequent 245-file database/archive snapshot also matches after validation work;
individual hashes are in the machine summary. That snapshot was taken after the live
attempt, so it is not misrepresented as an earlier archive-wide snapshot. The live
attempt only used copied slices and disposable SQLite; production was never opened by
a Store. Existing source fixtures and labels have no diff. No production document-13
rebuild, association activation, evidence revision, topic/group correction or head write
was performed. PR #1 was verified OPEN and draft.

## Reproduction and next actions

Fresh commands run:

```sh
.venv/bin/python -m pytest tests/test_proposition_context.py tests/test_knowledge.py tests/test_editorial.py tests/test_sort_efficiency.py tests/test_evidence.py -q
# 164 passed
.venv/bin/python -m pytest tests/test_proposition_context_validation.py -q
# 26 passed
```

The frozen measurement was created with `scripts/validate_proposition_context.py freeze`.
It refuses to overwrite the committed baseline. The all-case assessment was generated
once with `scripts/assess_proposition_context.py`, which also refuses to overwrite its
heldout capture. To reproduce a baseline independently without disturbing the frozen
artifact, use a temporary output directory (timings and hashes will differ):

```sh
.venv/bin/python - <<'PY'
import sys, tempfile
from pathlib import Path
sys.path.insert(0, 'scripts')
import validate_proposition_context as validation
with tempfile.TemporaryDirectory(prefix='stock-baseline-reproduce-') as tmp:
    validation.OUT = Path(tmp)
    validation.freeze()
PY
```

The replay script and new regression tests supply a disposable end-to-end replay;
regression tests inspect the committed heldout capture without rerunning its outcomes.
The live script refuses a second capture; do not rerun it for score improvement.
No repeated full-suite run was necessary. A separate model code/evidence review found
no critical or important new issues; two minor findings about packet completeness and
regression cardinality assertions were corrected. This was not human semantic review.

Smallest actions to close the gaps:

1. Have two independent humans complete the ready packets, then adjudicate every
   disagreement using exact source evidence. Another model run cannot substitute.
2. Quarantine `cw-we` from approved inputs. Preserve the historical record; investigate
   the wrong-target edit and semantic verification on **new development examples**.
   Any proposed deterministic guard must be tested for legitimate edits, not tuned
   into a blanket substring ban. Use a fresh heldout set after policy changes.
3. Investigate the transport timeout without repeated score-seeking calls. A future
   separately bounded pilot must demonstrate an actual edit, grounded resolution,
   independent review and request-free completed resume; this run did not.

These are semantic evidence gaps and a known recorded-verdict safety failure, separate
from the Filing speaker-envelope limitation. The raw baseline is available and integrity
checks pass within their tested scope, but the mandatory zero-known-unsafe-acceptance
condition fails. **Decision: BLOCKED. Phase 3 must not begin.**
