# ASSESSMENT-LLM-M2-GATE1-PI-COMPAT-007-RUN-004-USER-REVIEW

- **Date**: 2026-08-26
- **Status**: `DRAFT / USER APPROVAL REQUIRED / DO NOT COMMIT, PUSH OR RELAY`
- **Run ID**: `G1-PI-COMPAT-007-20260826T152221Z-004`
- **Execution SHA**: `4dc76d1574daa7a9f7f56b98a8d65e00258fd46c`
- **Execution-surface SHA-256**: `568aa791ae572080ede637dc941887d8eee73553539e9ec3dc54a9979f92adc5`
- **Operator SHA-256**: `537062355175705da2a500dddeffa446dd2ceae6e814c61a9fd013166b5924b8`
- **Pi custody path**: `/var/tmp/llm-poc-g1-pi-007-evidence/G1-PI-COMPAT-007-20260826T152221Z-004/`
- **Sanitized result SHA-256**: `262bd91d10cdddd2ee1460ae0bf19e5688f44207ba9ee12948be7074c555eda9`
- **Manifest-file SHA-256**: `716cb7b6a4b343f9646b7d458b0e0019dd49b382dee73d5f355193f9ec988541`

## Review conclusion

Run 004 is valid evidence that both frozen candidates violated the formal M4B-P1 requirement to
emit exact-identity READY within 10 seconds after child launch. Complete model SHA-256 reads had
already finished before the READY clock began. The observed timeout therefore does not repeat the
v6 timing defect.

The immutable raw aggregate incorrectly marked P12 `PASS` after both candidates failed before
READY and inference. That P12 field is rejected by this adjudication: target isolation alone cannot
prove offline inference. P1 and P11 are independently supported and remain usable; P6, P7, P10A
and P12 are `Blocked`.

| Candidate | Model authentication outside READY | P1 | P6 | P7 | P10A | P11 | P12 | Candidate result |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| `CAND-LRT-G4E2B-MOBILE-R1` | 27,590.324 ms | `FAIL` | `Blocked` | `Blocked` | `Blocked` | `PASS` | `Blocked` | `FAIL` |
| `CAND-LRT-Q25-15B-Q8-R1` | 17,023.058 ms | `FAIL` | `Blocked` | `Blocked` | `Blocked` | `PASS` | `Blocked` | `FAIL` |

The stderr evidence shows LiteRT model parsing and XNNPACK delegate creation, but neither child
emitted READY before the fixed deadline. Because the runner terminated each child at the deadline,
the evidence proves startup was greater than 10 seconds; it does not claim an exact eventual READY
time.

## Environment and evidence integrity

- Pre/post target proof recorded Debian 13 aarch64, 4 GB class memory, `SwapTotal=0`, both `eth0`
  and `wlan0` down, no routes, no sensitive environment names and `throttled=0x0`.
- Offline runtime installation, Python import, AArch64 ELF identity and native linkage passed.
- The nine custody files pass `MANIFEST.sha256`; the sanitized result validates against the v7
  result schema with zero schema errors.
- Cleanup restored Wi-Fi, artifact mode `0664`, `/dev/zram0` 2 GB at priority 100 and both zram
  setup/swap units active. The Pi formal checkout remained clean at the execution SHA.

## Non-scoring attempts before Run 004

| Run | Classification | Finding | P credit |
| --- | --- | --- | --- |
| `...144428Z-001` | infrastructure `INCONCLUSIVE` | raw `swapoff` was reactivated by rpi-swap before preflight | none |
| `...151155Z-002` | infrastructure `INCONCLUSIVE` | stopping only the generated swap unit did not suppress reactivation | none |
| `...151955Z-003` | infrastructure `INCONCLUSIVE` | identity/offline preflight passed; reboot had removed the `/var/tmp` to `/tmp` artifact bind | none |

The final operator used a runtime mask plus direct swapoff, restored zram directly at priority 100,
removed the runtime mask and retained the persistent artifacts without re-download.

## Result-semantics correction

The local follow-up source sets P12 to `PASS` only when P1 proves that the same offline run completed
the normal READY/inference lifecycle; otherwise P12 remains `Blocked`. It updates the runner, packet,
unit test and lock only. Verification is workstation 23/23 PASS and physical-Pi affected suite
15/15 PASS. The corrected, currently uncommitted execution-surface digest is
`b327a6a591f74e9743ea8478aeb722ecb8d1641d67cc401c96fc9751a16edfce`.

## Required User and Core decisions

User approval is required before this result or a candidate disposition is committed, pushed or
relayed. If approved, Gate 1 closes `FAIL / ZERO FINALIST`; Gate 2A cannot start. The frozen candidate
set explicitly forbids post-result backfill, so Qwen2.5-0.5B must not be inserted into this run.

Core must then choose between accepting the zero-finalist close or authorizing a new, prospectively
frozen candidate/runtime-optimization round that retains the 10-second P1 boundary. The latter is a
new round, not a reinterpretation or retry of Run 004.
