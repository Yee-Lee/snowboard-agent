# Core Designer → LLM POC Team: Gate 1 Platform Change ACK

- **Delivery ID**: `DELIVERY-LLM-POC-M4B-GATE1-PLATFORM-CHANGE-ACK-001`
- **In response to**: `DELIVERY-002-PM-LLM-POC-GATE1-PLATFORM-CHANGE-REQUEST`
- **Affected contract**: `DELIVERY-LLM-POC-M4B-CONTRACT-001`
- **Superseded packet**: `G1-UBUNTU-PRESCREEN-003` after the replacement revision is accepted
- **From**: Core Team Designer
- **To**: LLM POC Team
- **Date**: 2026-08-19
- **Status**: `APPROVED FOR PACKET REVISION — REAL EXECUTION NOT AUTHORIZED`
- **Architecture change**: `No; test-gate platform and sequencing change only`

## 1. Decision

Core Designer approves the requested Gate 1 platform split and has revised the authoritative
`DELIVERY-LLM-POC-M4B-CONTRACT-001` delivered with this ACK.

1. **Yes.** Ubuntu 24.04 x86_64 is sufficient for the full Gate 1 portable candidate pre-screen.
   Its P4 measurements are required for harness completeness and candidate comparison, but do not
   establish Raspberry Pi acceptance performance.
2. **Yes.** Native Ubuntu aarch64 Gate 1 execution may be replaced by a bounded compatibility
   try-run on the product Raspberry Pi 5 4GB / Debian 13 aarch64 before Gate 1 submission.
3. **Yes, with complete acquired-artifact proof.** A candidate may satisfy Gate 1 aarch64
   eligibility only when authenticated x86 evidence, pinned aarch64 runtime/dependency bundle
   checksums and a Pi compatibility `PASS` all refer to the same candidate identity. Official
   metadata without acquired-bundle verification and Pi evidence is insufficient. This grants no
   Gate 2A P1–P12, performance, resource, thermal, offline-product or winner credit.
4. **Yes.** The POC Team may issue one replacement Gate 1 packet/schema/selector revision under
   the requirements below. This authorization covers repository revision and deterministic
   regression only; it does not authorize artifact acquisition or real execution.

Gate 0 R2 remains `COMPLETE`. Gate 1 remains `NOT_STARTED / BLOCKED` for real execution until the
replacement packet is committed, returned at an exact SHA, reviewed by Core, and its execution
prerequisites are separately authorized.

## 2. Binding selection sequence

The replacement packet must implement one fail-closed sequence:

1. Run the frozen full pre-screen for every approved candidate on Ubuntu 24.04 x86_64.
2. Authenticate the x86 result against the loaded lock, manifest, artifact/config identities,
   catalog, validator, runner, schemas, command and cleanup proof.
3. Rank eligible x86 candidates using the frozen comparison fields and select at most two before
   any Pi compatibility execution.
4. Run the Pi compatibility packet only for those preselected candidates.
5. Retain as Gate 1 proposed finalists only candidates whose Pi compatibility result is `PASS`.

The same selection cycle must not backfill a third-ranked candidate after a selected candidate
returns `FAIL` or `INCONCLUSIVE`; otherwise the nominal two-run cap could be bypassed. A backfill
requires a new cycle/revision and separate written authorization. Zero retained candidates is an
evidence-backed no-go/change-request outcome, not permission to expand the Pi run set.

## 3. Required replacement packet

The returned single commit must update all directly affected authoritative POC paths and include:

- A new packet ID and revision; `G1-UBUNTU-PRESCREEN-003` remains historical and must not be
  silently rewritten or reused for new evidence.
- Separate x86 full-result, Pi compatibility-result and aggregate selection schemas, plus their
  locked checksums and fail-closed loader validation.
- A distinct Gate 1 Pi compatibility Test ID and evidence namespace. Its fields must not use
  M4B-P1–P12 PASS labels.
- Candidate/acquisition identity that keeps one logical runtime version and candidate ID while
  recording the exact platform-native x86 and Pi runtime/dependency artifact SHA-256 values.
- A selector that ranks authenticated x86 evidence once, enforces the maximum of two, applies Pi
  `PASS` as a later eligibility filter and rejects result/manifest/lock drift.
- Gate 2A plan wording that requires a new run ID, independent packet/evidence namespace,
  `swap=0` and complete P1–P8/P10A/P11/P12 execution without Gate 1 carry-over.

Minimum negative regressions must prove rejection of missing or forged identities, an unapproved
platform, incomplete P4 arrays, dirty or reused evidence paths, Pi `FAIL`, Pi `INCONCLUSIVE`,
cleanup/orphan failure, a third-candidate backfill and any attempt to ingest Gate 1 compatibility
evidence as Gate 2A evidence.

## 4. Pi compatibility contract

For each of at most two preselected candidates, the immutable Pi try-run packet must verify:

- exact POC SHA, clean protected paths, approved raw evidence path and Raspberry Pi 5 4GB /
  Debian 13 aarch64 environment;
- pinned aarch64 runtime/dependency bundle checksums and isolated offline install/import;
- absence of runtime download or cloud/model fallback under network-disabled conditions;
- exact runtime version, candidate/model/config identity and bounded model load;
- READY identity, PING, one bounded minimal deterministic generation and SHUTDOWN ACK;
- exit `0`, process-group absence, orphan `0`, bounded timeout and isolated-environment cleanup;
- observed swap, memory, disk and elapsed values marked informational only.

Candidate compatibility results are limited to `PASS`, `FAIL` and `INCONCLUSIVE`. A valid runtime,
artifact, ABI, load, protocol, generation or cleanup incompatibility is `FAIL`; environment,
identity or evidence failure that prevents a valid decision is `INCONCLUSIVE`. Neither result may
be rewritten after inspecting another candidate.

## 5. Authorization boundary and return

This ACK authorizes the POC Team to revise plans, packet code, schemas, selector, locks and
deterministic tests. It does **not** authorize model/runtime download, artifact transfer or install,
real x86 candidate runs, Pi access, network switching, privilege changes, Pi compatibility runs or
Gate 2A execution. Those actions retain their existing User/owner approvals.

Return one reviewable commit with:

1. response/delivery path and changed-path list;
2. branch and complete 40-character commit SHA supplied after commit, not self-recorded in a file;
3. packet self-test and negative-regression commands with exit status and concise output;
4. a statement that no real candidate, artifact acquisition or hardware execution occurred;
5. remaining acquisition, runner, raw-path, Pi and execution-authorization blockers.

Core will intake only that exact SHA. Packet-revision acceptance will not itself start Gate 1 real
execution, select a finalist or grant Gate 2A credit.
