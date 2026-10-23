# Distinct investment insights

## Diagnosis and decision

At 17c710c extraction selects locally inside compact sections; final identity is
(text, exact references, category, speaker). Independent editorial review checks
fidelity/readability/usefulness but has no document-wide selection or proposition
comparison. Sources counts and edits passage rows. Rebuild replaces one document's
passages, so it must not be used merely to consolidate display.

Use two small additions: a cached document-wide selection plan before reconstruction,
and reversible canonical insight groups over existing immutable passage IDs. Do not
rewrite evidence to deduplicate. A text-only heuristic would miss paraphrases; a
vector service or all-pairs model comparison adds unnecessary infrastructure/cost.
Use lexical/proposition retrieval and bounded batched semantic judgments instead.

## Selection

For fresh sections, first assess source spans for materiality, specificity,
incremental knowledge, distinctness, qualifications, and reconstructability. Process
bounded source batches then assess the collected shortlist across the document;
retain exact support IDs and reasons, not generated facts. Cross-batch duplicate
context contains only already-retained representatives, preventing symmetric
omission of every occurrence. Distillation contract: `distillation-2`. No passage quota. Empty
selection is valid. Large shortlists receive a substantive second assessment, not
truncation. Existing completed/partial editorial checkpoints stay reusable, with
post-publication grouping available separately. Preserve 17c710c transport, repair,
review fingerprints, and deferred authentication.

## Identity and safeguards

Retrieve plausible duplicates using shared informative tokens and topic context,
with a bounded neighbor list and request budget. Exact matching is automatic only
when source/context identity agrees. Compare full propositions: subject, period,
actual/forecast, metric/units, scope, values, direction, qualifications, viewpoint.
Uncertain, qualified, conflicting, and changed claims stay separate. Pair judgments
contain reasons, material differences, information preservation, and support origin
(repeated assertion, independent corroboration, unknown). Independent corroboration
requires explicit origin evidence; a different document alone is insufficient.
Require complete-link equivalence within each group, avoiding transitive false merges.
Choose an existing clear verified member as canonical; never synthesize a union.
Keep all member wording, exact citations, hashes, representations, review results.

## Persistence and presentation

Versioned cached judgments and append-only group revisions store original member
IDs and decision basis. One active revision per ticker. Ungrouping creates another
revision. Unmatched/legacy passages are singleton insights. Effective topics are
computed from each member's effective passage topics; topic views include only
members assigned that topic and file views only members in that file. Canonical
wording in a filtered view comes from a visible member. Topic edits target one
explicit member; never propagate an old or new passage edit across a group.
Keyboard member navigation exposes all source identities/dates/differences/citations.
Counts show insights and support passages independently, with a distinct total.

## Staging and safety

A dedicated `stock sort TICKER --insights` stages a proposal over frozen evidence,
prints before/after counts, equivalents, differences, loss checks and manual-edit
disposition, then requires REPLACE to activate. No passage is replaced. A review-only
flag stops before activation. Snapshot checks reject stale proposals atomically.
Selective --rebuild retains its current approval and rollback contract and reviews
semantic groups for its target document before REPLACE. Its group changes commit
atomically with that document replacement; other documents are not regrouped.
Ordinary Sort still freezes once, grouping only the new document at publication;
no existing library is automatically regrouped. Cross-document consolidation is
only activated through the explicit --insights review. Archived files,
legacy checkpoints and overrides are untouched.

## Validation

Disposable SQLite, actual archived CoreWeave excerpts and recorded judgments only.
Exercise paraphrases, repeats, independence, short KPIs, qualified facts, periods,
forecast, conflicts, scope, topic edits, filtering, reversibility, stale/failed
activation and legacy fallback. Report replay calls and cache reuse separately from
unmeasured live model quality. No full extraction or production writes.
