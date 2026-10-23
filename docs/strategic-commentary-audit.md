# Strategic commentary audit and refinement

Scope: refine commit `4a58069`, retaining document understanding → exact source resolution → independent semantic review → targeted correction → atomic publication. Stock Sort archives corporate strategy and commentary. BAV owns systematic financial extraction, modeling, forecasting and valuation; no BAV code or parent repository is changed.

## Observed live baseline

Read-only inputs: `.data/knowledge-validation-ky0xq3ej/result.json`, its `copy.sqlite3`, original document-13 Markdown/PDF, and `.data/sort-logs/8bd75361d9f249b7b5b9d05f9a08288e.jsonl`. All five operation attempts completed. The original archived files match the hashes in the committed inventory. The baseline is 22 published-ready statements, 650.570 seconds, five new requests and 339,426 prompt characters. Document-13 model-call IDs 2 and 3 predate this run; IDs 4–8 belong to it. ID 1 belongs to document 4. The old validation report included the two older document-13 calls because it selected the entire history.

The committed `document-13-recorded-operations.json` retains actual model outputs, including 34 original selections, first independent review (12), correction output (15), and independent reviews of corrections (11 and 1). The diagnostic log has 27 exclusion records; these are accumulated failed stages, not 27 distinct permanently lost propositions.

A disposable SQLite backup and the unchanged baseline code reproduce all five original prompt sizes exactly:

| Stage | Prompt characters | Observed model wall seconds | Reconstructed input |
|---|---:|---:|---|
| Understand | 58,140 | 205.705 | 135 anchors, 30,779 source characters |
| Review | 52,249 | 103.648 | PDF pages 11, 18, 12, 18, 13, 18 |
| Resolve uncertainty | 113,213 | 199.226 | 15 failures, 57 anchors, 23,468 source characters, 12 PDF pages |
| Review | 97,896 | 85.926 | PDF page 5 three times and page 6 eight times |
| Review | 17,928 | 44.510 | PDF page 21 |

Resolution and subsequent review consumed 329.661 observed seconds and 229,037 prompt characters. The recovery context included pages 2–7, 14, 17–18 and 20–22. Its PDF layout alone occupied 71,183 JSON characters. This was largely a broad source retrieval and repeated-layout problem, not evidence that the document-level architecture was fundamentally flawed.

## Coverage standard and findings

`tests/fixtures/sort/strategic-inventory.json` is the source-grounded expected-information inventory: 24 distinct strategic propositions, exact Markdown supports, why each contributes information, temporal/stance status, initial selection indices, final verification indices, duplication and wording assessments. PDF geometry is separately retained in `document-13-strategic-layout.json`. The inventory is document-specific, not a mandatory topic or KPI checklist.

The live model selected 22 of these propositions; 17 survived in its final result. These figures count propositions, not final statement count: the inventory combines the two inseparable footprint facts and excludes standalone reconciliation comparisons. Seven expected propositions were absent from the final result:

| Proposition | Selected? | Failure |
|---|---|---|
| Specific operating capabilities: cooling, modular deployment, rack density, security, interconnects | No | Selection omission; not just a demand for more metrics |
| Expansion with both existing hyperscaler customers | No | Corporate event in a terse bullet was overlooked |
| Named customer relationships | Partially | Initial selection merely listed three names; correction recovered full customer framing, then added an uncited 2025 period and failed quantity validation |
| First NVIDIA Exemplar Cloud for GB200 NVL72 | Yes | Flattened-table ambiguity; corrected version added uncited 2025 and was rejected |
| Backlog as conditional demand visibility, with customer mix and delivery constraints | Yes | References arrived out of source order and were rejected before independent review |
| Capex to scale capacity for customer demand | Yes | Same source-order rejection |
| Revenue growth attributed by management to strong platform demand | Yes | Overloaded selection appended reconciliation figures; mixed scale handling failed quantity validation |

There were **seven** out-of-order-reference failures across the 34 initial selections (the early working estimate of eight was corrected on enumeration). Sorting already validated unique IDs preserves evidence and avoids an unnecessary model repair. Replaying the unchanged original selections through the new resolver admits 15 instead of 12 to independent review, including backlog and expansion capex. That demonstrates a deterministic admission gain, not a new semantic verdict or improved model selection.

Legitimate safeguards: label/value associations in the footprint and scrambled execution table needed original PDF layout; unsupported added period context required either a citation or narrower wording. These checks remain. Some other failures were avoidable: all reference-order failures; overlong mixed-unit financial reconstructions; reviewers mistaking “in the same list” and “on that slide” for standalone prose; treating the absence of a separate GAAP summary as reason to re-investigate clearly labeled reconciliation values.

Useful corrections recovered Zero Egress Migration, Serverless RL's faster feedback loops, Mission Control's enterprise-adoption purpose, Federal's target market, the revolver's growth-financing purpose and the scopes of Genesis Mission and CrowdStrike. Corrections to already-selected footprint facts mainly repeated earlier reasoning to obtain geometry that should have been provided before the first review. The final appendix GAAP operating-loss repair added a financial comparison with little distinct strategic explanation. Three other standalone Q4 financial comparisons were source-supported but secondary under this objective.

The positioning claims are not automatically worthless promotion: first-to-market execution, stack investment and AI workload design explain management's position. They must stay attributed. The benchmark claims and workload-design statements partly overlap but communicate different bases and capabilities. They should not be multiplied into generic innovation slogans. None of the 24 inventory propositions is a material duplicate of another; their distinct contribution is recorded individually. The baseline acquisition statement loses the source's platform-expansion rationale, and numerous final event/footprint statements depend on their neighbors for subject or caveat.

## Implemented contract and evidence changes

The new `knowledge-2-strategic` contract retains the eight topics and existing category/speaker fields. Selection prioritizes events, reasoning, execution, capabilities, constraints, intentions, forecasts and meaningful external interpretations. It preserves source certainty and distinguishes achievements, plans, targets, forecasts and competitive opinions in wording. It explicitly excludes a systematic financial inventory. Independent review checks strategic contribution and standalone readability, including attribution and material qualifications. An explicit redundant verdict is excluded rather than published or repaired. Review usefulness is intrinsic to each claim; cross-statement equivalence remains in the existing semantic grouping stage. Only valid supported/clear/useful judgments enter the per-claim cache; batch rejection judgments remain scoped to their exact batch artifacts. Narrow deterministic readability guards supplement semantic review without deciding materiality through keywords.

Damaged tables expose exact cell spans; structured tables expose exact rows. Each retains the original parent span, hash and row/column coordinates. Parent offsets resolve back to the immutable Markdown; these are Markdown coordinates, not invented original-PDF cell boundaries. Transport omits redundant local provenance. An early all-cell implementation increased IPO prompt work and was removed. Sparse ordinary financial table headers do not automatically trigger whole-document geometry preparation.

Only demonstrably fragmented table evidence receives selective original geometry during understanding. Ordinary prose never requires PDF processing. Bare numeric blocks now always require layout evidence; previously a single numeric tile could escape the guard and then fail review for missing geometry. Page location can use unique literal fragments from a damaged cell, but location alone never proves an association: geometry and independent semantic review remain required. Conflicting page matches remain unresolved. Published references remain exact Markdown; auxiliary geometry is separate.

Recovery packs complete uncertainty cases rather than splitting a source set and repeating the same failed claim across boundaries. It retrieves cited evidence, bounded neighbors and informative lexical matches; it does not fill the remaining budget with arbitrary same-speaker text. Readability corrections reuse original support and available layout. It excludes irrelevant/duplicate verdicts from repair, carries only relevant PDF pages, and never retries already accepted propositions. Independent review artifacts are keyed by exact claim/evidence and its relevant layout, not incidental batch indices or peer page matches. Changed text or evidence still needs independent review. Historical artifacts remain intact under their original contracts.

Coverage metadata records source IDs, sections, initial selection and final verified coverage in structured logs. The main prompt checks substantive sections and terse corporate events before returning. This is diagnostic source coverage, not a claim that each unselected anchor is an omission. No additional full-document model audit is launched by default; material gaps are assessed against source-specific inventories and targeted uncertainty work.

## Demonstrated results and limitations

The offline inventory sends **human-corrected selections and human-recorded support judgments** through exact resolution, actual review transport, cache handling and publication validation. All 24 pass with exact support, including seven baseline gaps. These are corrected regression inputs, not outputs from a new model. No fresh-model recall or live speed improvement is claimed. The corrected inventory loses none of its 24 propositions. Unchanged old contextual wording is intentionally rejected by the stricter readability contract, so incomplete new model repairs could reduce live coverage; the offline result does not rule out that risk. The source-order change alone deterministically rescues backlog and capex for review without rewriting their recorded text.

Examples that pass this offline path:

- “CoreWeave launched Serverless RL to enable developers to train AI agents with faster feedback loops.”
- “CoreWeave launched CoreWeave Federal to extend its AI cloud platform to government and public-sector use cases.”
- “CoreWeave said it acquired Monolith and Marimo to expand its AI cloud platform.”
- “CoreWeave expanded its revolving credit facility to $2.5 billion to enhance financial flexibility for growth initiatives.”

The Serverless RL, Federal and acquisition references contain 122, 100 and 284 exact source characters respectively rather than the repeated 6,511-character parent table. Geometry separately resolves scrambled associations. Acquisitions' purpose is grounded in the original page, not inferred motivation.

For the **identical baseline review inputs**, deduplicating pages reduces 52,249 → 37,643 and 97,896 → 30,361 prompt characters, with the final 17,928-character review unchanged. That saves 82,141 characters (24.2% of the original total) while retaining every supplied page block. It is an isolated serialization measurement; the complete new workflow uses a different contract and evidence representation. Rebatching the corrected inventory after independent review makes zero extra model requests. Actual service latency and tokens remain unmeasured.

The separate IPO/filing/transcript/presentation replay compares `4a58069` with the new implementation using identical recorded propositions and semantic judgments. All 13 propositions and nine groups survive, including actual versus forecast capacity, contracted versus active capacity and supplier constraints. Resume makes zero requests. Total simulated requests fall 18 → 17, but serialized prompts rise 241,903 → 263,349 (+8.9%), largely from narrower table provenance and a stronger contract. This is a measured cost limitation, not an end-to-end live speed win. Offline local timings are recorded separately in `docs/benchmarks/strategic-commentary.json` and do not represent model processing time.

## Output, validation and preservation

`validate_knowledge.py` defaults to the offline inventory and prints a compact summary plus report path. `--show-statements` explicitly enables detailed output. Live mode also uses compact output, and records only model calls added during that invocation. Internal errors remain in structured diagnostics; no pager is opened. Production Sort's terminal behavior is unchanged.

All testing uses committed fixtures and disposable databases. No production CoreWeave extraction or publication was run. No source files, original hashes, published evidence, manual topics, historical checkpoints, revisions, manual ungrouping decisions, atomic publication or explicit REPLACE controls were removed or bypassed. Normal Sort's existing current-evidence idempotence and review-only safeguards remain tested. SHA-256 checks confirm 200 protected production/archive/live-artifact files remain unchanged around regression evaluation. Final verification: `361 passed in 135.56s`; two focused layout checks also pass after reusing the normalized PDF index. `git diff --check` is clean. Explicit `--show-statements` produces two summary/report lines plus 24 statements. A read-only code review and follow-up found no remaining important issue in the table and cache fixes.

Safe next validation (offline, no authentication, no publication):

```sh
.venv/bin/python scripts/validate_knowledge.py
```

Detailed offline output: append `--show-statements`. A fresh authenticated document-13 run remains subject to the user's explicit authorization; it is necessary before asserting improved live selection recall or latency.
