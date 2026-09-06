# CR-AUDIO-PI-PRIVATE-EVIDENCE-ROOT-001

- Date: 2026-09-06
- From: Audio POC Team
- To: Core
- Related status: `PI-MIGRATION-STATUS-001`
- Status: `BLOCKING CROSS-TEAM INTERFACE DECISION REQUIRED`

## Conflict

Core's private-evidence runbook requires raw audio, transcripts, content-bearing
logs, private comments, and identifying environment output to remain outside Git
and shared evidence-export roots. Audio therefore stages a READY bundle only at
`PI_AUDIO_PRIVATE/<bundle-id>` with owner-only permissions.

The current Core downloader invokes the Audio exporter with
`PI_DEV_ROOT/evidence-export/audio` as its ready root. Because the Audio exporter
allows payloads only below the supplied ready root, satisfying that interface
would place private payload bytes in a shared export root and violate the privacy
boundary. No READY Audio bundle currently exists, so no disclosure or copy has
occurred.

## Requested Core decision

1. Supply the Audio private ready root through operator-local configuration or a
   command argument that is never persisted in Git, logs, receipts, or public
   manifests.
2. Keep `PI_DEV_ROOT/evidence-export/audio` limited to sanitized projections and
   sealed non-private transfers.
3. Add one integration test joining Audio `list-ready`/`stream` output to Core
   archive verification and receipt creation.
4. Do not download a private bundle until the approved Audio source change is
   available in the canonical Pi worktree and the selected bundle directory is
   verified owner-only.

Audio's cleanup verifier now consumes Core's existing receipt field names,
`archive_sha256` and `archive_bytes`. Core still needs to decide the canonical
owner-only ready-root layout and ensure any receipt source locator is logical
and non-sensitive; it must not record the Pi's physical private path.

The layout decision must also reconcile Core's runbook bundle directory
(`<private-root>/<bundle-id>/manifest.private.json`) with the current Audio
exporter's collection interface (`<ready-root>/*.private.json`). Audio will not
guess or stage a second private copy while that contract remains undecided.

## Preserved boundary

This request does not authorize a bundle build or download, source deployment,
product materialization, hold movement, cleanup, commit, or push. The cleanup
dry-run remains empty until a valid nonempty receipt and all reference conditions
are independently verified.
