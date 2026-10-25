# Local proposition graph

Future proposition contextualization is governed by
[the proposition decontextualization contract](proposition-decontextualization.md).
That specification is a design for later phases; the runtime behavior below is current.

This replaces the draft's fixed 0.85 gate and Cursor equivalence requests. The
architecture is implemented, but **production rollout remains blocked by financial
recall and calibration**. Do not rebuild production document 13 to validate it.

## Models and contracts

- Retrieval: `BAAI/bge-small-en-v1.5`, 384 dimensions, FastEmbed 0.9.0 and CPU ONNX.
  Artifact repository `Qdrant/bge-small-en-v1.5-onnx-Q`, immutable revision
  `aa8f8b060edb00e03bfdd08813a2949946c8ba55`, `model_optimized.onnx`.
  Raw proposition text, tokenizer's 512-token limit, CLS pooling, float32 unit
  normalization. Exact UTF-8 text hashes identify vectors; the cache contract
  includes weights, preprocessing, pooling and dimensionality. The earlier unpinned
  draft cache is retained but not represented as reproducibly pinned data.
- Directional inference: `cross-encoder/nli-MiniLM2-L6-H768`, immutable revision
  `b95119ce93d3e065de6214e38cd4a97b0f2f2c6d`, `onnx/model.onnx`.
  Its three configured labels are contradiction, entailment, neutral. Both orders
  execute locally. Stable softmax produces scores; malformed/nonfinite scores fail
  staging. Pairs above 512 tokens remain unresolved, with no truncation.
- ONNX Runtime CPU was actually executed on this arm64 Mac with Python 3.14.0,
  FastEmbed 0.9.0, ONNX Runtime 1.31.0, NumPy 2.5.4, tokenizers 0.22.2 and
  huggingface-hub 0.36.2. Torch/Transformers are not application dependencies.
  Models download once; `HF_HUB_OFFLINE=1` verifies subsequent offline execution.

BGE remains a reasonable inexpensive retrieval model at this scale; it is not an
equivalence classifier. MiniLM was selected for small CPU cost and native three-way
NLI, rather than a generative LLM. Its general-language training does not establish
financial accuracy. Larger DeBERTa classifiers remain candidates for a future
controlled comparison, not a claimed evaluated improvement.

Primary model documentation:
[BGE](https://huggingface.co/BAAI/bge-small-en-v1.5) and
[MiniLM NLI](https://huggingface.co/cross-encoder/nli-MiniLM2-L6-H768).

## Discovery and progressively wider review

Every incoming/incoming and incoming/existing vector pair is scored using exact
NumPy arithmetic. Unchanged vectors survive documents, rebuilds and refinement.
`source_candidate_runs` and `source_candidate_scores` retain inventories and all
scores, including deferred pairs. There is no ANN service or fixed cosine gate.

For each incoming proposition, the initial frontier uses its empirical median,
median absolute deviation, and largest upper-half neighborhood gap. Small or flat
neighborhoods compare against a versioned unrelated reference set instead of
requiring a cosine of 1. Reference embeddings and their additional comparisons are
counted separately. This is a retrieval noise reference, not financial calibration.
Low similarities do not force a fixed number of neighbors into inference.

Selected pairs are reviewed in descending similarity order. Explicit refinement
widens each empirical tail approximately geometrically from its initial observed
percentile; it does not immediately request a quarter of a large archive. Previous
material discoveries can advance two bands rather than one after at least 20
observations and majority yield. These workload heuristics are versioned and
uncalibrated; observed model predictions are not ground-truth validation. Unreviewed
inventory totals and scope-specific deferred counts are reported separately.

`stock map TICKER --refine` stages and activates a broader graph revision, without
extraction or independent source re-verification. Interrupted runs retain vector,
score and completed NLI checkpoints. Repeating the same frontier reuses completed
inference. Later refinement can inspect weak relationships; it never upgrades an
unreviewed pair to a negative logical judgment. No perfect-recall claim is made.

## Directional evidence and financial policy

Raw NLI outputs are cached by model/input contract and exact source fingerprints
separately from decisions. Changing policy can reinterpret scores without inference.
The source fingerprint includes wording, exact citation locations, attribution,
document identity and metadata. Publication dates are never treated as reporting
periods. Unknown essential entity, period and scope for detected financial/numerical
claims block automatic equivalence, entailment and contradiction.

Deterministic vetoes compare periods, issuers/counterparties, modality, capacity
state, metrics, normalized values/sign/units via Stock’s quantity parser, scope,
definitions, parenthetical numeric notation, qualifications and attribution.
Optional verified attributes belong in `location.attributes` (`issuer`, `period`,
`as_of`, `scope`, and other named material dimensions); missing attributes are not
agreement. Document metadata alone is not sufficient to fill an omitted reporting
period. Regex extraction is deliberately conservative and incomplete. It can retain
real paraphrases because notation or date phrasing differs. It does not silently
invent financial attributes to improve reduction counts.

The provisional policy requires >=0.985 entailment in both directions for
EQUIVALENT. One-way ENTAILS requires >=0.985 in one direction and >=0.95 neutrality
in reverse. CONTRADICTS requires >=0.985 contradiction both ways, compatible known
entity/metric/period and no material mismatch. Both-neutral >=0.95 can support
RELATED within a retrieved neighborhood. Everything else remains UNRESOLVED.
These thresholds are conservative engineering choices, **not empirically calibrated
probabilities or logical proofs**. Numerical changes and different periods are
usually unresolved rather than automatically called contradictions.

## Persistent graph and presentation

`source_insight_revisions` retains immutable JSON graph revisions under
`graph_contract=proposition-graph-1`; `source_insight_heads` atomically selects one.
Every original verified passage ID remains a node, with its full wording, source
identity, references, qualifications and exact citations. Each reviewed edge stores
left/right IDs, relationship kind and direction, both score vectors, pinned model
contract, decision policy, source fingerprints and provenance. Unreviewed pairs are
absent edges with retained candidate scores, not UNRESOLVED predictions or negatives.
`source_nli_cache` keeps raw completed directional inference independently of heads.

Only complete-link EQUIVALENT edges support shared presentation: every member pair
needs direct support. No similarity-chain or NLI transitive closure is used. All
member formulations and citations remain available; canonical wording is one actual
member, never a synthesis. ENTAILS leaves both nodes and both presentation rows.
RELATED and CONTRADICTS also retain both rows. Expanded Sources shows directed links,
disagreements and uncertainty. Space expands; N/P chooses equivalent members; R
follows a relationship across topic/file filters; O opens the selected member's
source; T edits its topics; U records a manual split. Existing grayscale native
Textual styling and fixed terminal alignment are retained. The named terminal
handbook was not available in this checkout; existing rendering code and tests were
used as the concrete reference.

`insights.correct_relationship(...)` records audited manual relation corrections;
manual splits and corrections survive refinement. Suppression tombstones survive
retired evidence. Retired manual edges remain in `relationship_overrides`; changed
source identity retains the prior correction for review as unresolved rather than
blindly applying old equivalence to changed wording. Historical revisions and
`source_publication_history` retain retired citations and original corrections.

## Rebuild publication

Rebuild still extracts all selected material evidence and independently verifies it
using Cursor, then prepares local vectors, candidate scores, NLI edges and validated
presentation groups. Unique exact source identities transfer manual topics/splits.
Missing or ambiguous transfers block replacement. Verified evidence and graph head
activate together inside the existing checked SQLite transaction. Source/topic/head
snapshots are checked again immediately before publication; failures roll back both.
`--rebuild` is authorization: no REPLACE or approval callback is reintroduced.
`--review-only` stages without activating. Cache writes never activate evidence.

## Reproducible commands

```sh
cd "$HOME/Documents/Developer/stock"
.venv/bin/python -m pip install -e '.[semantic,test]'
# Vector indexing only; no source/graph activation or Cursor requests:
.venv/bin/stock map CRWV.US
# Focused offline workflow/policy tests; inference is injected in pytest:
.venv/bin/python -m pytest tests/test_semantic_map.py tests/test_relationships.py tests/test_graph.py tests/test_insights.py tests/test_sources.py -q
# Real models, committed labeled excerpts and read-only published inventory:
HF_HUB_OFFLINE=1 .venv/bin/python scripts/evaluate_proposition_graph.py --inventory --output /tmp/stock-graph-evaluation.json
# Omit HF_HUB_OFFLINE on the first model download.
# Explicit local refinement; changes presentation graph only:
.venv/bin/stock map CRWV.US --refine
# Eventual authorized production rebuild, AFTER readiness blockers are resolved:
.venv/bin/stock sort CRWV.US --rebuild 13
```

The index command intentionally writes cached vectors to Stock's database. It was
not run against production during implementation. All evaluation database writes
were disposable; inventory access used SQLite `mode=ro`. No production document-13
rebuild, PR merge or production graph activation was performed.

See [measured evaluation and blockers](proposition-graph-validation.md). The previous
23,322-pair / 329-Cursor-request approach is a historical baseline, not the workload
used to manufacture a matching new pair count. Extraction and independent factual
verification can still incur Cursor requests; only semantic deduplication is zero.
