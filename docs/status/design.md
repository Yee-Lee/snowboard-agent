# Current design status

- Owner: Designer
- Scope: M4C complete offline voice-device integration
- State: **Design entry open; M4C design delta not yet authored**
- Developer entry: **Closed pending Design → Test Spec**

## Accepted inputs

- M4A Audio is Accepted and supplies the production ASR/TTS/audio lifecycle and composition surface.
- M4B LLM / Reasoner is Accepted at commit
  `f87cfa50b9c9415430973076a59c6b1961228090` after same-bytes Raspberry Pi `PV` Pass.
- M4B supplies finite-session Audio+LLM resource estimates and monotonic stage observations. The
  558/699 MiB values are observations, not M4C release thresholds.
- M4B's declared non-claims—physical wake/display hardware, native context exhaustion, nested-
  descendant killing and full-product shutdown—remain honest evidence boundaries. M4C owns only
  the whole-product integration behavior required by its own scope.

## Next Designer work

Author the M4C design delta for Button → Listen/ASR → Reasoner/LLM → Speak/TTS, Rest and the basic
Session Display composition. Preserve the existing milestone exclusions for camera/look, voice wake,
tool/MQTT and full graphics/animation. Fix observable behavior, ownership, lifecycle/error routing,
resource composition and verification boundaries before handing the result directly to Test Spec.

Start with [`M4C`](../milestones/M4C.md), then load only the routed M4A §§1, 7, 10, 12 and M4B
§§1, 5–7, 9–10, 11.2 sections listed in [`current.md`](current.md). Open a focused architecture
request only if those accepted contracts cannot support the required M4C composition.
