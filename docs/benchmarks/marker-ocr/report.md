# Local Marker OCR comparison — 23 October 2026

Document 13: CoreWeave Q4 2025 presentation, PDF pages **4, 5, 6, 14, 15**
(Marker IDs 3, 4, 5, 13, 14). Source SHA-256:
`db716980ae8eb4eddda477d43ef2cead98419f6fa4fbec8e37ff643a98b6cbf6`.

Resumed `/tmp/stock-marker-investigation/` and reused its A baseline and rendered
references. Preserved the original blocked driver as `guarded_marker.blocked-original.py`;
removed only its local Surya backend prohibition. Retained offline caches,
loopback-only Python networking, sequential runs, separate new output directories,
and 240-second / 8 GiB sampled descendant-RSS bounds. Marker 2.0.0, Surya 0.22.1,
MPS; optional Marker LLM enhancements disabled. Local Surya's generative OCR/layout
is authorized and distinct from those enhancements. No cloud inference, document
upload, model download, archive activation or Sort operation was performed.

## Completed five-page results

| Profile | Layout / OCR | Wall seconds | Marker seconds | Peak descendant RSS MiB |
|---|---|---:|---:|---:|
| A, reused baseline | fast / automatic | 22.85 | 11.07 | 831.3 |
| B | balanced / automatic | 65.54 | 51.46 | 623.4 |
| C | fast / forced | 190.68 | 176.72 | 632.3 |
| D | balanced / forced | 113.77 | 100.71 | 629.7 |

All B/C/D returned 0, produced Markdown, retained the original source hash, and
stayed within both limits. Their sidecars show respectively pdftext for all B
pages, Surya for all C/D pages, and zero optional LLM processor requests. Files,
commands and machine-readable semantic checks are in [comparison.json](comparison.json).
Actual staged outputs/logs remain under `B_LOCAL`, `C_LOCAL`, `D_LOCAL` in the
investigation directory. Original blocked B/C/D attempts remain preserved.

These RSS figures **exclude pre-existing shared inference services and Metal/GPU
allocations**. Lower sampled RSS is not proof of lower total memory. A was measured
in the earlier session; model/server cache state and concurrent host activity were
not controlled. D was faster than C in this one run, not a general performance
claim. Balanced+forced skips preliminary layout here; forced+fast still does it.
C/D Markdown is identical after normalizing image filenames.

## Information and relationships

Review used the original rendered PDF pages, retained assets, native source text,
Markdown order and full statement context. Term-presence checks only locate
omissions; they are not evidence of diagram or column relationships.

| Page | A baseline | B balanced/automatic | C and D forced |
|---|---|---|---|
| 4, platform | Architecture flattened to image; searchable product/layer content omitted | Same major omission | Same major omission |
| 5, footprint | Values survive but heading/value order is displaced; incomplete region footnote | Restores complete region/backbone definitions but moves the main capacity block into an image, losing searchable values | Correct adjacent pairs: **850MW+ active power; 3.1GW+ contracted power; 43 active data centers; 11 added in 2025**. Retains date, illustrative-map qualification and definitions |
| 6, four columns | Broken Markdown table interleaves unrelated statements; Cognition/Cursor missing | Recovers complete customer sentence and coherent bullet groups, but several headings follow the group they should introduce | Proper heading-before-bullets order; customer wins, technology milestones, financing and other updates remain separate and readable |
| 14, backlog | Narrative/contractual caveats retained; chart image; legend renders `<24` | Narrative/caveats retained; chart and legend moved to image | Narrative/caveats retained; legend correctly reads **≤24 / 25–48 / >48 months**; series values still image-only |
| 15, capex | $8.2bn demand rationale and capex definition retained; chart image | Same substantive narrative; chart image | Same substantive narrative; chart image |

**W&B Models, SUNK and CKS remain absent from the searchable Markdown in every
mode.** The source associates W&B Models with Model and Agent Development, Slurm
on Kubernetes (SUNK) with Runtime Acceleration, and CoreWeave Kubernetes Service
(CKS) with Infrastructure Control. Their labels survive visually in retained
images, not as recovered structured evidence. The training/inference/specialized
workload ring and Mission Control relationships still require visual analysis.

B/C/D restore **Cognition and Cursor** within the customer list with CrowdStrike,
Mercado Libre, Midjourney and Runway; the separate CrowdStrike global partnership
remains a separate update. C/D preserve the financing associations: approximately
$2.6bn inaugural convertible senior notes in an upsized offering, versus the
revolving credit facility expanded to $2.5bn for financial flexibility. Technology
milestones include NVIDIA Exemplar Cloud/GB200 NVL72, the sole Platinum ClusterMAX
rating, AI Object Storage/Zero Egress Migration, Monolith/Marimo, Mission Control
and Serverless RL with their adjacent rationales. These are readable grouped
statements, rather than merely recovered names.

All profiles retain the $66.8bn backlog/342% YoY narrative and delivery/availability
conditions and expected-recognition qualifications. None recovers structured
backlog chart associations: Q4'24 $15.1bn, **54/42/4%**; Q4'25 $66.8bn,
**42/37/21%**, in ≤24 / 25–48 / >48-month order. None structures the capex chart's
Q4'24–Q4'25 sequence **$2.4/$1.9/$2.9/$1.9/$8.2bn**. Those facts were visually
checked, not inferred from OCR. Minor duplicate bullet/footnote numbering remains
in forced output. Retained chart/map images must remain available to the reviewer.

## Implementation and safety

`python -m stock.pdf_review` implements an **explicit inactive high-fidelity review**
using D (`mode=balanced`, `force_ocr=True`, `use_llm=False`). `--profile current`
uses explicit fast/automatic settings for comparison. Archive conversion defaults
are unchanged. The command neither opens Stock's database nor registers or
activates outputs. It refuses existing destinations and destinations inside
Research, production `.data`, or the source directory; existing Markdown and old
citation offsets are untouched.

The worker blocks external TCP connections and external DNS, uses offline model
caches, disables all model-service autostarts after settings loading, and attaches
only to already-running local services. It never signals those services. The
watchdog owns only its new process group; it records sampled process-group and
shared-service RSS and cancels its own conversion on time/RSS limits. Shared RSS
can reflect other clients, and GPU allocations remain outside that measurement.
Defaults: 1,800 seconds and 8,192 MiB; maximum configurable bounds: 3,600 seconds
and 8,192 MiB. A stopped client does not forcibly terminate a shared server's
already-accepted request; its inference timeout is 120 seconds.

Outputs retain page-separated Markdown, images, Marker page_stats, source hash,
effective profile, versions and timing/RSS metrics; completed command manifests
also hash output artifacts. Marker `{n}` markers and page_stats IDs are zero-based:
PDF page is n+1. This provenance is for new staged files and does not retrofit old
citations. No claim is made that OCR validates investment facts.

The installed `pdfmd force-ocr` shortcut incorrectly preferred
`--DocumentProvider_force_ocr`, which does not configure installed `PdfProvider`.
The regression failed before the fix and passed after preferring global
`--force_ocr`, with only `--PdfProvider_force_ocr` as fallback. The active symlink
points to the corrected local `~/Documents/Developer/pdfmd/pdfmd.py`. That separate
repository has no tracked base/remote to push; the reproducible change is retained
in [pdfmd-force-ocr.patch](pdfmd-force-ocr.patch). The new Stock review command
bypasses the wrapper. Its installed-code forwarding check is preserved at
`/tmp/stock-marker-investigation/test_pdfmd_forwarding.py`.

## Contrasting ordinary digital PDF

CoreWeave Q1 2026 corrected earnings-call transcript, PDF pages **2, 3, 4**,
source SHA-256 `5e2306cfd4f4f732395049b2cdd3cdb2909a4e8c6712de3009c962b13de833ba`.
These pages contrast with presentation graphics: participant names/affiliations,
speaker headings, dense ordinary paragraphs and financial/strategic statements.
Inspected local rendered pages against both outputs and reviewed token differences
in context, rather than treating token counts as semantic validation.

| Profile | Result | Wall seconds | Peak own group / observed shared RSS MiB |
|---|---|---:|---:|
| Current, fast/automatic | Complete, all three pages pdftext | 14.67 | 515.7 / 790.3 |
| D, balanced/forced, first 240s bound | Timed out; no Markdown, not a completed quality result | 240.21 | 556.5 / 1235.1 |
| D, balanced/forced, retry with 600s bound | Complete, all three pages Surya | 229.57 | 595.2 / 1154.1 |

The retry used a new inactive directory; no completed result was overwritten.
Variability/cache state means the timeout and faster retry are both reported.
These are sampled process RSS observations, not total physical/GPU memory or
isolated service allocation attributable to one job. Shared services retained the
same pre-existing PIDs throughout. Successful D cost about **15.6x** current-mode
wall time on this sample and produced no material strategic-information gain.

Both completed modes preserve participant/speaker relationships, customer names
and the sampled quantitative statements: >$40bn bookings, nearly $100bn backlog,
approximately $2.1bn revenue, 32% QoQ/112% YoY, 1GW active power, >3.5GW contracted
power, >400MW added, >$20bn capital raised, Anthropic/Claude, Meta/$21bn, Jane
Street/$6bn, Hudson River Trading, World Labs, PhysicsX and Sunday Robotics;
10 customers/$1bn commitments, >90% using at least two products, >75% using three
or more, and businesses expected to exceed $100m ARR. Qualifications remain with
their statements. The customer examples and speaker association were checked in
context, not inferred from name recovery.

D introduces actual regressions: the original/current-mode
`investors.coreweave.com` becomes an incorrect `www.coreweave.com` hyperlink, and
“AI diffusion” / “AI workloads” become “Al diffusion” / “Al workloads”. It also
retains extra small image assets and changes near-term word joining. Current
mode already retains the page-4 SUNK Anywhere product statement, so forced OCR
adds no benefit there. Thus even mostly accurate OCR is unnecessary and can
corrupt a clean digital text layer.

## Decision, verification and exact document-13 command

Keep Stock's existing archive default. Select **D only as the explicit staged
high-fidelity review profile for documents with demonstrated extraction problems**.
It offers C's improvements at a lower observed deck cost, while the ordinary-PDF
regressions and cost rule out forcing OCR globally. It remains a candidate
extraction, requiring visual review before facts become evidence. It does not
solve diagram semantics, multi-series charts, map topology, or the missing
searchable W&B Models/SUNK/CKS labels on presentation page 4.

Focused verification: **20 tests passed**, covering archive conversion regressions,
non-overwrite boundaries, page numbering, inactive success/failure manifests,
source/output hashes, interpreter symlink preservation, external connection/DNS
blocking and cancellation without stopping an unrelated process. Independent code
review found no actionable issues. The installed wrapper forwarding regression
passes. All 13 previously registered original/Markdown/asset hashes match
`archive-before.json`; no production Sort data or archived citation offsets were
modified. The ordinary PDF's source hash is also unchanged. Full 24-page D
conversion was **not** run; the command below performs that next, separately.

From the Stock checkout, convert document 13 alongside its preserved archive:

```sh
.venv/bin/python -m stock.pdf_review \
  Research/CRWV.US/Archive/2026-02-26--presentation--Q4-2025.pdf \
  "$(mktemp -d /tmp/stock-doc13-review.XXXXXX)/conversion" \
  --profile high-fidelity --seconds 1800 --rss-mib 8192
```

The final JSON line reports the new output directory. It remains staged and
inactive. Add `--pages 4,5,6,14,15 --seconds 240` to limit a subsequent review to
the original sample. Existing installed local model services must be running;
missing services fail rather than start new ones. The new tool is independent
of temporary investigative scripts and never changes the archived baseline.
