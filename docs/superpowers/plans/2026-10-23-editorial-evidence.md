# Editorial evidence implementation plan

Goal: preserve useful fragments and publish explicitly represented, source-grounded evidence.
Architecture: retain v3 IDs and transactional storage; add a versioned evidence envelope inside location JSON. Stock resolves exact references, Cursor proposes editorial text and separately reviews factual fidelity, readability and relevance. Unresolved claims remain audited staging data, never published facts.
Spec: user's source-grounded reconstruction requirements; diagnosis and final decisions in docs/evidence-quality-repair.md.

- [x] Add failing reconstruction tests using frozen document 13 and exact source slices.
- [x] Implement representations, multi-reference resolution, numeric guards and semantic review gate in stock/editorial.py; preserve legacy exact records.
- [x] Retain heading/table/image anchors, adjacent batch context, optional read-only original PDF layout inspection; version checkpoints and revalidate resumed output.
- [x] Extend rebuild review and Sources inline inspection; match manual edits by references and block ambiguous transfers.
- [x] Run focused evidence/Sources tests, review the diff, verify production read-only snapshot unchanged, document limitations, commit and push origin/main.

Constraints: Python 3.11; fixed eight topics/three categories; no production writes or automatic rebuild; no parent repository changes; explicit REPLACE remains mandatory.
Review focus: semantic approval cannot prove equivalence; numeric signs/units and qualifiers need review; flattened columns cannot establish mappings; checkpoint resumes must not bypass source checks; changed editorial wording must not silently lose manual topics.
Execution: native, autonomous as explicitly requested. No worktree needed: clean dedicated stock repository, all work must remain inside this directory.

Independent review found and corrected original-file checkpoint binding and premature rejection of explicit numeric mappings. Focused verification and live smoke details: docs/editorial-evidence.md.
