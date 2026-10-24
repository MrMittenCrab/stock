# Persistent global semantic map (experimental)

## Algorithm

Stock uses **persistent normalized sentence embeddings** as a candidate-retrieval
index, not as factual authority. The chosen method is a **Gaussian-kernel,
high-recall neighborhood graph** feeding Stock's existing **verified complete-link
grouping**. Gaussian mixtures and density-based clusters are inappropriate for
equivalence: related financial claims are not necessarily duplicates, and one
dense semantic topic can contain many conflicting dates, numbers or forecasts.

For normalized vectors, cosine similarity and the Gaussian kernel

    K(a,b) = exp((cosine(a,b)-1) / sigma^2)

have the same ordering. The kernel is used for closeness, *not* equivalence
probability. The production candidate policy currently includes every incoming-
incoming pair, the 24 closest historical neighbors of each incoming proposition,
all historical passages with cosine similarity >= 0.72, and the existing
lexical-retrieval candidates. Every historical proposition is numerically scored.
This is not an exhaustive pairwise model judgment and does not guarantee recall
for remote paraphrases. Do **not** interpret screened-out edges as negatives.

Only the separate Cursor judgment can declare two claims equivalent. It checks
reporting periods, modality, numerical definitions, source perspective, scope and
qualifications. Complete-link grouping requires a directly verified positive edge
between every two members. An embedding, a Gaussian score, or a theme never merges
claims. An uncertain judgment keeps the statements separate. Existing manual split
and correction safeguards, verified extraction and atomic unattended replacement
remain mandatory and unchanged.

## Persistent state

The SQLite `source_semantic_vectors` table stores float32, unit-length 384D
vectors keyed by exact UTF-8 statement text SHA-256 and the explicit embedding
model contract. Duplicated text reuses its vector even if cited by several
documents. Rebuilding a document computes only uncached embeddings; old source
identities and source citations do not belong to the vector cache.

The reference local model is FastEmbed's `BAAI/bge-small-en-v1.5` (ONNX).
The model's weights download on first use to
`.data/embedding-models`; subsequent requests reuse the local model cache.
Text is encoded locally, not sent to an embedding API. Each batch is committed
only if its outputs have the expected finite shape; corrupt stored vectors fail
closed. The semantic model contract must be versioned again on model or
preprocessing changes. Source content can still be sent to the separate
authenticated Cursor agent for *verified equivalence judgments*, as before.

Install once in Stock's existing environment:

```sh
cd "$HOME/Documents/Developer/stock"
.venv/bin/python -m pip install -e '.[semantic]'
```

Build the initial company-wide index once (no Cursor calls and no publication):

```sh
.venv/bin/stock map CRWV.US
```

Then an authorized `stock sort TICKER --rebuild DOCUMENT` reuses its cached
historical vectors and embeds only new statement text. For an archive of more
than 64 propositions it uses the local map for candidate discovery. Smaller archives use exhaustive
comparison to avoid model initialization for trivial workloads. The absence of
the embedding dependency causes large rebuilds to **stop without publication**;
it never silently falls back to 23,000 costly Cursor comparisons.

## Validation requirements and limits

Offline tests use deterministic fake vectors and exercise full-library scans,
candidate discovery, content-hash cache reuse, invalid-vector refusal and
large-library rebuild integration. No model download, real CoreWeave embedding
inference, or live Cursor deduplication has yet been performed by this branch.
The numeric 0.72 threshold and 24-neighbor floor are *initial heuristics*, **not
empirically validated recall settings**. They require calibration using the actual
CoreWeave corpus, held-out known duplicates, difficult negative examples and
low-overlap paraphrases before this design should replace the production algorithm.

A full numeric similarity scan for 13 new statements against 1,788 historical
statements is only 23,244 local dot products; that is inexpensive. The number
of actual Cursor verification calls depends on the observed candidate set and
prompt packing, and is not claimed here. Historical-only unreviewed pairs remain
historical backlog, not certified negatives. Old completed positive judgments
and complete-link manual controls continue to apply.

The Gaussian map is deliberately not visualized as an arbitrary 2D projection:
reducing a 384D semantic space to a chart could distort nearest-neighbor
relationships. Inspect pair scores and retrieval-recall diagnostics instead.

**Do not run a production document-13 rebuild until this branch passes the
Mac-local focused tests and CoreWeave candidate-recall audit.**
