# Current design status

- Owner: Designer
- Scope: M4-ERR error-handling closure followed by M4C complete offline voice-device integration
- State: **M4-ERR Design entry ready；M4C scenarios recorded／M4C-SS open**
- Developer entry: **Closed；M4-ERR Accepted and M4C-SS Closed are required before M4C Test Spec／Developer entry**

## Accepted inputs

- M4A Audio is Accepted and supplies the production ASR/TTS/audio lifecycle and composition surface.
- M4B LLM / Reasoner is Accepted at commit
  `f87cfa50b9c9415430973076a59c6b1961228090` after same-bytes Raspberry Pi `PV` Pass.
- M4B supplies finite-session Audio+LLM resource estimates and monotonic stage observations. The
  558/699 MiB values are observations, not M4C release thresholds.
- M4B's declared non-claims—physical wake/display hardware, native context exhaustion, nested-
  descendant killing and full-product shutdown—remain honest evidence boundaries. M4C owns only
  the whole-product integration behavior required by its own scope.

## USER-confirmed M4C volume direction

- Include startup-static software output volume in M4C composition.
- Keep the accepted `AudioOutput` Protocol unchanged; use one decorator plus a separate future
  `VolumeControl` injection seam.
- Schema default is `100`; M4C real product config is `25`, matching the M4B Pi playback attenuation
  without adopting the runner-only wrapper as production code.
- Runtime GPIO adjustment, Display volume projection, OSD, persistence and a separate mute state are
  deferred. No `adjustments/volume` runtime module is created in this slice.
- This addition remains inside the normal M4C Design → Test Spec → Developer → Verify pipeline and
  does not open Developer entry by itself.

## USER-confirmed M4-ERR split

- Insert M4-ERR after Accepted M4A／M4B and before M4C product Test Spec／development.
- M4-ERR completes the shared error taxonomy, lossless classification, sanitized diagnostics,
  backend-usability decision, recovery and fatal-exit behavior for the generic Core and all
  production components used by M4.
- The current ASR `INFERENCE_REJECTED` mapping is a system-fault defect, not a retry interaction.
  M4-ERR also audits equivalent broad/lossy mappings in the other M4 production components.
- M4-ERR and M4C each follow `Design → Test Spec → Developer → Verify`. Accepted M4A／M4B history
  remains immutable; affected behavior is corrected append-only and reverified on Pi.
- M4C consumes the completed framework and verifies whole-product scenarios rather than repeating
  every component-level diagnostic cause.

## USER-confirmed M4C interaction and quality boundary

- M4C has no barge-in. TTS playback and Listen do not overlap; short press is the only active-Session
  interruption mechanism in this milestone.
- Existing M4A VAD／endpoint settings remain the baseline. M4C observes endpoint quality in the real
  product path and changes it only for a reproducible clipping／missing-text／excess-wait problem with
  fixed before／after evidence and affected regression.
- Voice-normal-end acceptance stays small: one explicit spoken ending must produce `end=true` and
  converge to IDLE; no application keyword parser is added.
- `M4C-SS` is a USER-defined design gate and must close before M4C Test Spec. Its disposition chooses
  exactly one of streaming B or evidence-backed abandonment to full-response A.
- M4C scenarios end at IDLE／defined process exit. Repeated sessions, soak and formal latency／memory／
  thermal targets belong to ALPHA.

## Next Designer work

Commit and push the authorized M4C design/request bytes after same-bytes Pi Verify, deliver the byte-identical
M4C-SS request to the confirmed sibling LLM POC destination, then enter M4-ERR Design. M4C whole-product scenarios
are recorded; its only open product decision is M4C-SS.
Preserve the existing milestone exclusions for camera/look, voice wake, tool/MQTT and full graphics/animation.
M4C fixes observable product behavior and scenario acceptance; M4-ERR owns the underlying lifecycle/error
routing, diagnostics, recovery and fatal-exit closure. Do not create a second volume authority or another gate.

Start with [`M4C`](../milestones/M4C.md), then load only the routed M4A §§1, 7, 10, 12 and M4B
§§1, 5–7, 9–10, 11.2 sections listed in [`current.md`](current.md). Open a focused architecture
request only if those accepted contracts cannot support the required M4C composition.
