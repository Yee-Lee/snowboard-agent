# LLM POC M2 ARM64 UTM to Product Pi Transition Request and Experience Handoff

- **Delivery ID**: `DELIVERY-011-PM-LLM-POC-M2-ARM64-TO-PI-TRANSITION`
- **From / via**: LLM POC Team / User-authorized Agent courier via PM
- **To**: Core Team Designer and POC Technical Lead
- **Parent authority**: `ACK-LLM-M2-ARM64-PREFLIGHT-DIAGNOSTIC-001`
- **ARM64 evidence branch**: `wip/m2-arm64-preflight`
- **Sanitized evidence head before this handoff**: `9676835d6afd47ba1d5c9c011926693ac98cb043`
- **Status**: `SCOPE ADJUSTMENT AND PI TRANSITION APPROVAL REQUESTED`
- **Architecture change**: `No product composition-root change`
- **Date**: 2026-08-23

## Requested decisions

Please approve the following bounded revision:

1. accept the completed Ubuntu 24.04 ARM64 UTM work as the primary workstation engineering
   pre-screen and comparison input, without promoting any UTM result to Gate 2 evidence;
2. waive completion of the independent x86_64 WIP track and the former two-branch merge-boundary
   dependency, because native ARM64 runtime/model evidence is more directly representative of the
   product Pi instruction set and the full mandatory gates will be rerun on the product Pi;
3. freeze `CAND-LRT-G4E2B-MOBILE-R1` and `CAND-LRT-Q25-15B-Q8-R1` as the maximum two candidates for
   the next authorized product-Pi compatibility cycle, with no third-candidate backfill;
4. accept the 1000 ms P5 workaround only as a successful timeout-mechanism observation, while
   retaining contract P5 as `INCONCLUSIVE`; authorize a Pi-specific extreme-generation fixture or
   another written P5 disposition before the Gate 2A packet is frozen;
5. allow P1/P2/P3 and all other mandatory P1–P8/P10A/P11/P12 acceptance to move to independent Pi
   packets rather than expanding the ARM64 UTM packet; and
6. retain all current milestone/gate controls: M2 and External Gate 1 do not complete, Pi execution
   is not authorized by this request, and Gate 2A requires Gate 1 finalist ACK plus its own exact-SHA
   packet and execution authorization.

If Core does not approve items 2 or 5, the fallback is to preserve the ARM64 VM and prepare the
missing workstation P2/P3 catalog packet or resume the independent x86_64 track. No result should be
silently reclassified.

## Pi transfer rule

This handoff carries engineering knowledge and immutable identities, not acceptance credit. Gate 2A
must use a clean Pi checkout, a new run ID, an independently frozen packet, and the
`evidence/m4b/2a/` namespace. It must not consume any Gate 1/UTM result as a P1–P12 PASS. Raw UTM
logs and model output remain outside Git and are referenced only by sanitized SHA-256 values.

The Pi checkout entry sequence remains:

1. fetch and checkout the exact full SHA named by the future Pi test request;
2. prove the Pi and controller worktrees are clean and identical;
3. authenticate all runtime/model/config/fixture/schema hashes before model load;
4. prove Raspberry Pi 5 4GB, Debian 13 aarch64 and `swap=0` before Gate 2A;
5. create a fresh, run-owned evidence directory and process group;
6. execute only the immutable approved command; and
7. return sanitized results plus raw evidence hashes, cleanup/waitpid proof and orphan count.

The Pi is a deployment/test worktree. Do not patch code, configs, fixtures or thresholds on it.

## Immutable runtime and candidate identities

### Runtime

| Item | Frozen identity |
| --- | --- |
| LiteRT-LM API wheel | `litert_lm_api-0.16.0-py3-none-manylinux_2_27_aarch64.whl` |
| Wheel SHA-256 | `5eb8c9faa5727730239591f8c912261ec7705512d5f30ec674586bc0005f2b00` |
| Installed native library SHA-256 | `9b3a319b4878c3fafeea16db06eea7b2f023619e5f97037eb20b8e38662875e4` |
| Native ABI | ELF 64-bit ARM aarch64; all reported dynamic dependencies resolved |
| Python dependency closure | Empty `Requires-Dist`; use the dependency-free offline wheel installer |
| Runtime bundle record | `poc_llm/fixtures/gate1/arm64-runtime-bundle-v1.json`; SHA-256 `3db299c9bdfdb8e0660428efd8f5a187138287f9a67d28f11839fe808b7fe01d` |
| Adapter binding record | `poc_llm/fixtures/gate1/arm64-adapter-binding-bundle-v1.json`; SHA-256 `d2e9ec85e0f8de2c1fe6a40b77fe95b4a5e8c6a8f3acc34234aba6b8162c3682` |
| License record | `poc_llm/fixtures/gate1/arm64-model-license-metadata-v1.json`; SHA-256 `49fefcf9d1986ff316c525b11ce6e0602885da61059fdf7e265897bc796fffef` |

Do not copy the UTM `/tmp` installation tree to the Pi. Reacquire through the controlled offline
artifact channel, verify the wheel, install into a fresh Pi-owned target, then verify the native
library identity and linkage again.

### Active candidates

| Candidate | Artifact | Model SHA-256 | Size | Upstream revision | Config / manifest SHA-256 |
| --- | --- | --- | ---: | --- | --- |
| `CAND-LRT-G4E2B-MOBILE-R1` | `gemma-4-E2B-it.litertlm` | `181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c` | `2588147712` | `6b78abd019e61a1ca4cbe3b212d2c9ce8ff38a94` | config `b921cde451ee59713cc2478d56292bbb326acea032c59ea3bbb66adb9653d38a`; manifest `07fce6c22b001f21aea0880df160e55d5c026c4d77958ccaaa755ec6976fb1d4` |
| `CAND-LRT-Q25-15B-Q8-R1` | `Qwen2.5-1.5B-Instruct_multi-prefill-seq_q8_ekv4096.litertlm` | `faa60663b333290c1496c499828b21d3e3254a788cacd8cce917ce0f761a2dc9` | `1597931520` | `19edb84c69a0212f29a6ef17ba0d6f278b6a1614` | config `80ada6d80e6322e362484b855c99f4bf51c7b6e8e281ec1cb0e32b58d5559f4b`; manifest `5e47e7f945a6f818b59852d657e6b35dfd92759d21da36271b0df24f439ccb8d` |

`CAND-LRT-Q25-05B-Q8-R1` is not eligible for the Pi cycle. Its `.task` file SHA-256
`e608953f169aeb1bd7b9155fec2559825e08453fc209b84eda3a781ed0452fd2` is a MediaPipe ZIP container,
not a native `.litertlm` container accepted by the pinned v0.16 synchronous generation path. Four
failed generations are retained; do not spend Pi time retrying it without a new native `.litertlm`
artifact or an approved conversion flow.

### Source and lock identities

| Item | SHA-256 |
| --- | --- |
| ARM64 WIP lock | `153326f8f2301a9e0e8826bc98d521c7f44108c347d894a5215b8a60685c68de` |
| Canonical LiteRT child adapter | `d17c225a8d358275e6ce2b992f670ba7d8d73e35d73dc3da32b3a20a574f27ff` |
| Formal P4 runner | `ce7ef98bb6f6a8895e5c0d250565fe3aaeda5a333b87cdb02cbfb2a6befc9bc2` |
| P7 recovery runner | `9dff52da245ad398638aa50c5572c1665f3a15083236228ab3dc21b3b9571bc9` |
| Long-prompt/P8 runner | `4506242c32810fbb6e6f90c192e201dfdb280235b303b9b9a1915c2682ad665b` |
| P5 workaround runner | `2df9059fd90ca94a0c866120f03a5a7d422e735375161763d0c4157961a6ee7e` |

These are UTM reference identities. The future Pi lock must bind Pi paths, OS/runtime dependencies,
artifact locations, runner and result schemas independently. Any accepted source change requires a
new Pi lock and invalidates affected Pi results.

## Reviewed UTM findings to use as Pi planning input

| Area | Gemma 4 E2B | Qwen2.5 1.5B | Pi implication |
| --- | --- | --- | --- |
| Offline/native smoke | PASS | PASS | Both can initialize and generate through LiteRT-LM v0.16 ARM64 |
| P4 hot TTFT P50/P95 | `349.678 / 356.481 ms` | `812.486 / 846.984 ms` | Re-measure on Pi; do not reuse UTM thresholds |
| P4 hot decode P50/P95 | `22.301 / 22.574 tok/s` | `16.930 / 17.190 tok/s` | Gemma was faster on UTM |
| P4 hot wall P50/P95 | `1025.415 / 1063.333 ms` | `1703.930 / 1920.652 ms` | Use only for test-duration planning |
| Peak process RSS | `2072316 KiB` | `2052192 KiB` | Nearly equal; Pi must use PSS/RSS plus system-used memory |
| Model + runtime bytes | `2634233466` | `1644017274` | Qwen has about 0.99 GB lower storage footprint |
| P6 native cancel | Nondeterministic: one `139.839 ms` PASS, later `500 ms` timeout | Repeated `500 ms` timeout | Keep both `Conditional escalation`; require P7 PASS |
| P7 Level 2/rebuild | PASS; rebuild READY `5727.829 ms` | PASS; rebuild READY `4081.878 ms` | Preserve TERM→wait→optional KILL→waitpid→rebuild barrier |
| Long prompt | PASS; prefill `106` | PASS; prefill `127` | Qwen is close to the frozen 128-input-token envelope |
| P8 five-turn isolation | PASS | PASS | Rerun with the Pi output packet; hashes are not acceptance carry-over |
| P5 15-second contract | INCONCLUSIVE | INCONCLUSIVE | Resolve fixture before Pi packet freeze |
| P5 1000 ms workaround | TIMEOUT/READY in `1437.165 ms`; clean exit | TIMEOUT/READY in `1610.816 ms`; clean exit | Mechanism works; Core must decide whether/how to formalize Pi P5 |

The UTM comparison ranks Gemma first for speed and Qwen second for smaller disk footprint. This is
not a finalist selection. Pi compatibility and Gate 2A may reverse the order because the target is a
4GB Pi with different CPU, memory pressure, kernel, cooling and storage.

### Sanitized result provenance

| Packet | Execution SHA | Gemma result SHA-256 | Qwen result SHA-256 |
| --- | --- | --- | --- |
| Initial 10-session measurement | `19aca08a83caacb19ce1fab10fa9961fe188dab2` | `25c426cb685487cf38d6f9def3cfec7de6a490f3ddd32b34d303f0489e8d0ddf` | `0f55e6b6e71cee7b2d55b00c57224a83436ba7a424fa95a33bf6d75d3de82cfc` |
| P7 recovery | Gemma `2d5b1e9ad59258272a1f4581e733456261101bf2`; Qwen `9b6c2a20f95695c26c6bb727f72d63be5c6b3860` | `7d28f5fd539a1f236bc5e14ede2d42d54a1c523b7079612b6dc3bf807d7671dc` | `96cef6bd2f2fa776cf986747770e9463cbea1d9d216bf157eb3d385ccba9322e` |
| Formal P4 | `629f6136404366afc2db4b0e496bb261e2a920d6` | `a39aadef00aadae5b494898a88666caac93f05dcd12e5f4d2f09d1679fb072bf` | `9745a6091e000a97e07961609fb63454673adac1d0c7fdfeeccd264f52ef6634` |
| Long prompt/P8 | `46de889dc4e0f9b04d0d76d6b3065f4ef586532a` | `5b78ea1b30fd450ccec49305b75d174989943612b660139eb6c2e9a0779c23ee` | `c80f0dd520a88547bd98dfff1ef82ca449ddc28c62a45fa9a470eeb529801acb` |
| Successful P5 workaround | `108d95441da1f70740ce4c5b4070aeabf5c50aec` | `639ac42fd2fbb9f2c2d210f7381abd8e97442959e9f18783e896baf5626fea6f` | `358e4a23af3cbfba5a2708a5498931778a964783dd6c9bdc3a50696207b470b3` |

The complete sanitized attempt history, including runner failures, is in
`poc_llm/evidence/gate1/arm64-candidate-preparation-001.json`. The Pi operator should not need raw UTM
files to understand or reproduce the engineering decisions.

## Engineering lessons that must be carried to Pi

### Offline install and process environment

- Ubuntu's base `/usr/bin/python3` had no `pip`. The dependency-free wheel installer succeeded and
  should be adapted for the Pi instead of assuming pip availability.
- The installed wheel is discovered through the bound `PYTHONPATH`. A workaround runner once
  dropped `env PYTHONPATH=... python3`, causing both candidates to exit before READY. Preserve and
  authenticate the complete runtime command prefix; never reconstruct it from `sys.executable`.
- Never copy a virtual environment or installation tree between machines. Install into a fresh,
  operator-owned Pi path and hash what is actually loaded.

### LiteRT-LM API binding

- Use synchronous `conversation.send_message()`. The v0.16 async streaming call failed for the
  tested Qwen `.task` path and is not the accepted adapter binding.
- Do not map the product input/output envelope onto Engine `max_num_tokens`; that value controls KV
  capacity. Leave the model's KV-cache default intact and enforce `max_output_tokens` on each new
  conversation.
- Create a fresh conversation for every single-turn request. Reusing the Engine is intended;
  reusing conversation history is not.
- Treat `ADAPTER_DIAGNOSTIC` as a fail-closed signal. Diagnostics may include only stage, exception
  class and message hash, never the exception message, prompt or model output.

### Network isolation

- A new network namespace may still show `enp0s1` and `lo`. Interface presence is not proof of a
  route. Validate that `/proc/net/route` has no IPv4 route and `/proc/net/ipv6_route` has no
  non-loopback IPv6 route.
- An entirely empty `/proc/net/route` is valid; do not require a header line. Do not require sysfs to
  show loopback only. Both assumptions caused retained runner-defect `INCONCLUSIVE` attempts.
- Gate 2A P12 must additionally prove the target Pi's real offline state and no external API/token
  transmission; a UTM namespace is not P12 evidence.

### Lifecycle, metrics and cleanup

- Start each candidate in a new process group. On failure use bounded TERM→wait→KILL-if-needed→wait,
  then prove the process group absent. Never call SIGTERM/SIGKILL “Level 3”.
- P6 cancellation is nondeterministic on both active candidates. Preserve native results and use the
  contract's conditional escalation only when the full P7 termination/waitpid/rebuild/READY proof
  passes.
- Preserve samples, summary and RSS even when a later probe fails. An early-finalization defect once
  hid Qwen RSS despite ten valid sessions.
- Formal P4 uses one persistent process, three discarded warmups, three cold samples and twenty hot
  samples at the frozen token envelope. Record raw samples plus P50/P95; do not extrapolate UTM
  performance to Pi.
- P10A is not “twenty generations happened.” Sample per-session PSS/RSS/system memory, process and
  thread ownership, history isolation, memory slope and final cleanup on the 4GB `swap=0` Pi.

### Evidence hygiene

- Keep models, wheel/install trees, raw stderr/results and model text outside Git.
- Git may retain only source/version/license/checksums, schemas, non-sensitive fixtures and sanitized
  summaries. The frozen scanner must inspect runner-owned stderr and captured protocol output; do
  not trust candidate-declared hygiene.
- Every rerun uses a fresh path and preserves the unsuccessful attempt. Never overwrite or relabel a
  runner failure as a candidate finding.

## Gate 1 compatibility versus Gate 2A

The proposed transition does not skip Gate 1 Pi compatibility. The next authorized Pi work should
first execute a small, separate Gate 1 compatibility packet for the fixed maximum-two candidates.
Only Pi `PASS` candidates may receive Core's Gate 1 finalist ACK; no failed/inconclusive candidate is
replaced by Qwen 0.5B or another third model.

After the ACK, Gate 2A starts from zero in a different namespace:

| Work package | Gates | Pi-specific required proof |
| --- | --- | --- |
| Provenance | P11 | clean setup, OS/kernel/Python/runtime/model/config/license identities |
| Lifecycle | P1/P5/P6/P7 | READY/framing/shutdown; approved timeout fixture; native cancel; Level 2/waitpid/rebuild and fatal outcome |
| Output | P2/P3/P8 | frozen 20-case catalog ×3, exact product schema/fallback/log hygiene, five-turn isolation |
| Performance/soak/offline | P4/P10A/P12 | Pi raw/P50/P95, per-session memory slope and cleanup, real offline proof |

P4 remains negotiable performance; P1/P2/P3/P5/P7/P8/P10A/P11/P12 are mandatory. P6 is conditional
only with P7 PASS. Gate 2A may produce a provisional finalist, never a final winner.

## State and remaining blockers

- This request does not change `docs/milestone/README.md` gate or milestone statuses.
- External Gate 1 and Pi access/execution remain blocked pending their named approvals.
- Formal P5 fixture/disposition remains unresolved.
- The x86 waiver and removal of the former merge-boundary dependency remain pending Core approval.
- Gate 2B remains blocked by the Core-recorded Accepted M4a Audio final SHA/package and P9/P10B.
- The ARM64 VM and controlled artifacts should be retained until Core accepts this transition, but no
  further UTM command is currently pending.
