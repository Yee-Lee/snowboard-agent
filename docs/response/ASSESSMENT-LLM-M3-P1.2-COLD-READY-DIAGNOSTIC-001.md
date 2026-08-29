# ASSESSMENT — M3 P1.2 Qwen Cold READY Diagnostic 001

- Date: 2026-08-29
- Status: `USER-DIRECTED RECORD / SUPPLEMENTAL / NO GATE CREDIT`
- Candidate: `CAND-LRT-Q25-15B-Q8-R1`
- Execution source observed: `ed7aaca2e187b2287d442d6841e1ab2610b67570`
- Raw evidence: controlled `/var/tmp` paths on the authorized Pi; not committed

## Finding

The preserved Gate 2A observation stopped before the first Qwen READY at the unchanged 10-second
deadline. Two reboot-separated, non-scoring diagnostics reused the immutable receipt and performed
zero full model hashes. They observed READY at `19199.925 ms` and `19205.439 ms`. Stage attribution
assigned `19023.107 ms` to native `Engine()` construction; config/receipt was `2.325 ms`, LiteRT import
`32.969 ms`, protocol validation `0.169 ms`, sampler `0.014 ms`, READY emission `0.062 ms`, and
spawn-to-adapter-main `144.745 ms`.

Both diagnostic children produced the expected READY identity, answered PING, acknowledged SHUTDOWN,
exited zero and left no process group. The environment remained offline with swap zero and no
throttling. The finding is startup latency, not a hang, artifact mismatch or protocol failure.

## Evidence custody

| Record | Path on Pi | Size | SHA-256 |
| --- | --- | ---: | --- |
| Frozen Gate 2A observation | `/var/tmp/llm-poc-g2a-002-evidence/G2A-PI-QWEN-001/gate2a-sanitized.json` | 2028 | `9260e4f1d6ea4643f07a2297a07be48abd8b75b2093089392ba17f229b822714` |
| P1.2 diagnostic 001 | `/var/tmp/llm-poc-qwen-cold-ready-diagnostic-001/sanitized.json` | 815 | `0e86a7cb5c9967a17c6f5eb83ec8109c316980019a587ab2f03a3345d76fd6c4` |
| P1.2 diagnostic 002 | `/var/tmp/llm-poc-qwen-cold-ready-diagnostic-002/sanitized.json` | 987 | `f2bd0e340327a5eb4898ef52149c33f018666edc6ce25e81116e4081a823cee5` |

## Disposition

P1.2 cause-isolation is deferred. No cache, storage or capacity cause is claimed from the current
evidence. The historical P1 receipt is not overwritten, but its cache-conditioned startup method is
not treated as proof of true cold boot. For the current Gate 2A continuation only, User authorizes a
Qwen operational READY observation window of 30 seconds. The 10-second P1 contract remains recorded;
the workaround produces no P1/P1.2 credit and cannot by itself support a finalist proposal.
