# LLM POC Team → PM → Core Designer: Gate 1 Platform Change Request

- **Delivery ID**: `DELIVERY-002-PM-LLM-POC-GATE1-PLATFORM-CHANGE-REQUEST`
- **In response to**: `DELIVERY-LLM-POC-M4B-CONTRACT-001`
- **Affected packet**: `G1-UBUNTU-PRESCREEN-003`
- **From**: LLM POC Team
- **To**: PM for Core Designer decision
- **Date**: 2026-08-19
- **Status**: `ACCEPTED — CORE ACK 001 / CONTRACT REVISED 2026-08-19`
- **Architecture change**: `No product architecture change; test-gate sequencing change only`

## 1. Requested decision

Approve the following Gate 1 / Gate 2 platform split:

1. Gate 1 full candidate pre-screen runs on the current Ubuntu 24.04 x86_64 workstation.
2. Gate 1 retains candidate provenance, license, offline acquisition, exact artifact/config identity,
   frozen P1/P2/P3/P4/P5/P6/P8 portable tests and the maximum-two finalist rule.
3. After x86 screening, at most two proposed candidates receive a bounded Gate 1 compatibility
   try-run on the actual product Pi: Raspberry Pi 5 4GB, Debian 13 aarch64.
4. The Pi try-run covers artifact verification, isolated offline install/import, runtime version,
   model load, READY identity, one minimal generation, SHUTDOWN/exit and orphan=0. It does not earn
   any Gate 2A P1–P12, performance, resource, thermal, offline-product or winner credit.
5. Only candidates with authenticated x86 pre-screen evidence and a `PASS` Pi compatibility result
   may be proposed for the Gate 1 written ACK. Gate 2A later reruns the full mandatory matrix on the
   same product Pi with `swap=0` and its independently approved packet.

This request replaces native Ubuntu aarch64 Gate 1 execution with a narrower product-Pi compatibility
try-run before Gate 1 closes. It does not replace, waive or weaken mandatory Gate 2A/2B evidence.

## 2. Reason for the change

The product target is the existing Debian 13 Raspberry Pi, not an Ubuntu ARM deployment. Provisioning
and maintaining a separate native Ubuntu aarch64 runner would validate an intermediate OS that is not
shipped, while the same ARM runtime/model must still be installed and fully validated on Debian in
Gate 2A. The proposed split spends early ARM compatibility effort on the real target and reduces the
maintained platform matrix from three environments to two:

| Plan | Gate 1 | Gate 2A | Maintained execution environments |
| --- | --- | --- | ---: |
| Current packet | Ubuntu x86_64 + Ubuntu aarch64 | Debian 13 Pi aarch64 | 3 |
| Proposed | Ubuntu 24.04 x86_64 full pre-screen + Debian 13 Pi compatibility try-run | Debian 13 Pi full validation | 2 |

This is not a two-model or two-protocol design. Runtime version, model artifact SHA-256, config,
candidate ID, protocol and fixtures remain identical. Platform-native wheels necessarily have
different artifact SHA-256 values even when their package version and API are the same; those hashes
remain explicit in the acquisition lock and evidence.

## 3. Risk and cost assessment

| Area | Current two-Ubuntu Gate 1 | Proposed x86 + product-Pi Gate 1 | Assessment / mitigation |
| --- | --- | --- | --- |
| ARM incompatibility discovery | Before Gate 1 ACK, on Ubuntu ARM | Before Gate 1 ACK, on Debian product Pi | Timing is retained while OS relevance improves. Pi packet must be explicitly authorized as a Gate 1 exception. |
| Product representativeness | Ubuntu ARM is architecture-relevant but not the shipped OS | Exact Debian 13 product OS receives the try-run | Proposed compatibility evidence is more representative. |
| Runtime/version maintenance | Two Ubuntu native artifacts plus Debian Pi environment | x86 native artifact plus Debian Pi artifact | Same logical LiteRT-LM/model versions; one fewer OS environment and artifact cache. |
| Candidate selection | Selector requires two complete Ubuntu results and worst-platform ranking | Full x86 result plus Pi compatibility PASS | Revise selector/schema/lock; rank only authenticated x86 metrics among Pi-compatible candidates. |
| Schedule failure | Separate ARM runner provisioning/storage may block M2 | Pi artifact transfer and up to two sequential try-runs add bounded time | Run x86 first, cap try-runs at two candidates and stop on incompatibility before Gate 1 ACK. |
| Performance inference | Ubuntu ARM still does not represent Pi 5 performance exactly | x86 performance is even less representative | Treat Gate 1 P4 as harness completeness/informational only; all acceptance performance remains Pi P4. |
| Offline/provenance | Duplicated per Ubuntu runner | Acquired once per platform actually used | Keep exact wheel/dependency/model/config checksums and controlled offline bundles for both x86 and Pi. |
| Gate evidence separation | Gate 1 never touches Pi | Gate 1 performs a narrow Pi smoke before Gate 1 ACK | Use a distinct test ID/evidence namespace; never credit the try-run to Gate 2A and rerun under the Gate 2A packet. |
| Pi state contamination | None before Gate 2 | Artifacts/runtime are staged earlier | Use isolated environment and approved artifact path; verify cleanup and keep the Git checkout clean. |
| 4GB resource inference | Ubuntu ARM result is not a Pi resource gate | Current Pi swap could mask memory pressure | Record swap and resource observations, but make no resource PASS; Gate 2A still requires `swap=0`. |

The change lowers infrastructure and repeated artifact-storage cost without postponing the ARM
compatibility decision beyond Gate 1. Its added cost is a bounded early Pi deployment plus strict
separation between compatibility evidence and later Gate 2A evidence.

## 4. Proposed Gate 1 Pi compatibility try-run

After x86 screening and before Gate 1 submission, the immutable Pi try-run packet must verify for at
most two proposed candidates:

- Pi 5 4GB, Debian 13 aarch64, clean exact POC SHA and approved raw evidence path.
- Offline installation from the pinned aarch64 runtime/dependency bundle with checksum verification.
- Exact runtime version/API import and absence of runtime download or cloud fallback.
- Exact model/config checksums, bounded model load and READY identity handshake.
- PING, one minimal bounded deterministic generation, SHUTDOWN ACK, exit `0`, process-group absence
  and orphan `0`.
- Sanitized environment, command, exit, completion and cleanup evidence.
- Observed swap/memory/disk/elapsed values, explicitly marked informational and not Gate 2 evidence.

`PASS` means only that the exact candidate can install, load, generate minimally and exit cleanly on
the target ARM/OS. A valid incompatibility is `FAIL`; environment/evidence failure is `INCONCLUSIVE`.
Only `PASS` candidates remain Gate 1 finalist proposals. No try-run result may be rewritten as a
Gate 2A P1–P12, resource, performance, offline-product or winner result.

## 5. Required repository revision after approval

Core approval would authorize one new frozen packet revision, expected to update:

- `GATE1-PACKET-003` → a new x86-full + Pi-compatibility packet; previous packet remains historical evidence.
- Gate 1 result/selection schemas, selector, lock and negative regression tests.
- M2 runner/environment requirements and finalist decision wording.
- A distinct Gate 1 Pi compatibility test ID/schema/evidence path and cleanup rules.
- Gate 2A plan language requiring independent rerun and prohibiting evidence carry-over.
- Candidate manifest/acquisition schema so platform-native runtime artifacts have explicit identities.

Estimated repository work is 1–2 development days plus internal review. Artifact download and real
execution remain separately authorized. No model, binary, wheel, raw output or credential enters Git.

## 6. Decisions requested from Core Designer

Please explicitly answer:

1. Is Ubuntu 24.04 x86_64 sufficient for Gate 1 candidate full pre-screen execution?
2. May native Ubuntu aarch64 execution be replaced by the bounded product Debian 13 Pi compatibility
   try-run before Gate 1 submission?
3. May a Pi compatibility `PASS`, together with official aarch64 artifact metadata and complete x86
   evidence, satisfy Gate 1 aarch64 eligibility without granting any Gate 2 credit?
4. May the POC Team issue the described Gate 1 packet/schema/selector and Pi compatibility revision?

Core approved this request in `DELIVERY-LLM-POC-M4B-GATE1-PLATFORM-CHANGE-ACK-001` and revised the
contract on 2026-08-19. The approval authorizes packet revision and deterministic regressions only；
artifact acquisition and real execution remain separately unauthorized.
