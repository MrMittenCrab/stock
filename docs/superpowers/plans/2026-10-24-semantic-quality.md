# Semantic quality correction plan

**Goal:** Recover justified semantic relationships without false financial merges.
**Spec:** User's semantic-quality requirements; production document 13 stays untouched and PR #1 stays draft.
**Architecture:** Keep embeddings and raw NLI contract unchanged. Separate observed conflicts, absent context, and canonical notation. Evaluate both policies on identical raw scores and evaluate retrieval separately.

- [x] Trace every labeled positive through retrieval, extraction, scores, and vetoes before implementation.
- [x] Add failing regressions for compatible notation, reporting periods versus publication, missing context, attribution, and genuine financial differences.
- [x] Implement bounded semantic attribute normalization with auditable context provenance; preserve raw inference cache keys.
- [x] Evaluate original CoreWeave labels and an independent issuer-diverse financial challenge set, with untouched held-out cases and per-class denominators.
- [x] Run focused and full tests, disposable pipeline replay, cache reuse checks, and review invariants.
- [x] Record measured results, limitations and costs, then commit and push feature branch; verify draft PR status.

Review focus: reporting year versus point-in-time date; qualifications in source notes; forecast clauses attached to actual KPIs; unknown issuer or scope; raw-cache reuse across policy revisions. Never infer issuer from publisher or reporting period from publication date. No model replacement or threshold reduction without comparative evidence.

Evidence and limitations: [semantic-quality audit](../../semantic-quality.md); paired original-score traces, independent financial sets and disposable replay are in docs/benchmarks/semantic-quality*.json. No production rebuild.
