# Display POC agent entry

Snowboard Display POC runs on Raspberry Pi 5 with the physical 128×128 SSD1351 OLED. The accepted M3
hardware baseline is preserved at tag `display_p4`; current work is the M7 UX discovery requested by Core.

## Current task

- Active authority: `docs/pm_handoff/REQUEST-DISPLAY-POC-M7-UX-DISCOVERY-001.md`
- Progress and next action: `docs/poc/milestone_plan.md`
- Reserved return ID: `DELIVERY-DISPLAY-POC-M7-UX-DISCOVERY-001`
- Owner: Display POC team

The request is discovery input for later Core M7 Design. It does not authorize this repo to change Core
architecture, declare M7 accepted, or silently turn excluded features into product requirements.

## Startup and context

1. Read this file, then the active request and only its directly relevant source/test/evidence files.
2. Do not preload `docs/pm_handoff/history/`, `reviews/`, raw evidence, or all legacy Display code.
3. Treat USER direction first, then this file, the active request, and the Core authority at its named baseline.
4. Preserve accepted P1–P4 commits, tags, evidence and decisions. M7 work is append-only from `display_p4`.
5. Search history only for a named ID, SHA, finding or decision source.

## Working rules

- Work from product decisions: compare a small number of meaningful visual/rendering directions, eliminate
  low-value experiments, and state the failure risk each retained experiment resolves.
- Keep the runtime offline and map recommendations back to Core's
  `DisplayHint → RenderModel → Renderer → DisplayArbiter → DisplayDevice` flow.
- Prototype code may be disposable. Do not present a standalone animation demo as Core integration proof.
- Do not add Progress UI, OSD, touch, LED, fullscreen preemption, raw model output or conversation history
  unless returned as an explicit focused finding for Core to decide.
- Use exact content or asset digests only at a deliberate candidate/transfer boundary. Do not add recurring
  digest checks to application startup or every test run.
- Keep credentials, SSH endpoints, private paths, raw conversation content and large media outside Git.
  Commit only sanitized summaries, small fixtures and manifests needed to evaluate the recommendation.
- Code intended for delivery must complete applicable workstation checks and Raspberry Pi/OLED validation on
  the same bytes before commit. Documentation-only changes need only applicable document checks.

## Delivery flow

Use the single flow `Discovery design → Test plan → Prototype/measure → Verify → Core delivery`. Do not add
role sign-offs, candidate authorization files or repeated review gates. Human judgment is retained only where
the physical OLED must be assessed for readability, flicker, smoothness or product fit.

The final Core-facing package uses the reserved return ID and follows section 6 of the active request. Large
videos and raw logs remain in approved external custody with neutral locators; the committed delivery contains
the recommendation, measurements, mappings, limitations and focused findings.

## Git policy

- Commit only at a meaningful milestone or after completing same-bytes target verification.
- Use subject format `{work-type}{milestone/stage}: {title}`.
- Use a concise English bullet-list body of 60–100 words.
- Before any commit, show the USER the complete subject, body and file list and obtain explicit approval.
- Do not rewrite an accepted or externally delivered candidate; append fixes in a later commit.
