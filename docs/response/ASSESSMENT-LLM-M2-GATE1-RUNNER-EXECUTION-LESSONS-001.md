# ASSESSMENT-LLM-M2-GATE1-RUNNER-EXECUTION-LESSONS-001

- **Status**: `DRAFT / AWAITING USER REVIEW / NOT FOR CORE DELIVERY`
- **Scope**: physical-Pi Gate 1 runner, operator and product implications
- **Evidence cutoff**: Qwen focused run `G1-QWEN-P6P7-ISOLATED-20260827T135911Z`

## 1. Evidence-backed findings

1. Full model SHA-256 must remain outside READY, but just-in-time authentication alone does not
   guarantee candidate-independent startup. Target workload history also matters.
2. Qwen with the unchanged 512-token Engine capacity can meet initial P1: after reboot, with no
   prior candidate workload, READY was `3490.826 ms`; P1, P10A 20/20, P11 and P12 passed.
3. The same run then cleanly shut down the healthy child and created a redundant second Engine only
   to enter P6. That second startup exceeded ten seconds before the P6 fixture began. The resulting
   P6/P7 Blocked state measures runner sequencing, not cancel or force-abort behavior.
4. Therefore the earlier hypothesis that Gemma alone caused Qwen failure is too narrow. The proven
   issue is that repeated Engine construction after a substantial preceding workload is not a
   stable prerequisite. The underlying mechanism—page cache, allocator state, memory pressure,
   LiteRT profiler state or another native-runtime factor—remains unproven.
5. The initial transient operator ran as root and Git rejected the user-owned checkout as dubious
   ownership before model launch. Privileged mount/swap/network operations and the unprivileged
   evidence runner must have an explicit ownership boundary.
6. `.local` resolution failure is not proof that the Pi remains offline. After the isolated run,
   direct-IP SSH reached the restored Pi while mDNS still failed. Completion monitoring must use
   status evidence plus both name and direct-address reachability.
7. This Pi generates `dev-zram0.swap` from rpi-swap configuration. A raw `swapoff` can be
   reactivated; the operator must runtime-mask the generated unit, disable swap, and later unmask,
   start and verify the restored 2 GiB priority-100 zram device.
8. Reboot removes the `/tmp` artifact bind. The operator must recreate the read-only bind from the
   persistent `/var/tmp` artifact root before offline execution and remove it during cleanup.
9. The focused P6/P7 run removed both the preceding candidate and soak workload. Its prerequisite
   READY completed in `3479.672 ms`, generation activity was observed, P6 correctly became
   `Conditional escalation`, force-abort completed, but the sole required rebuild did not emit READY
   within ten seconds. Qwen's remaining blocker is therefore P7 recovery, not initial P1.
10. The focused runner retained force-abort cleanup only in a local variable until rebuild success.
    When rebuild timed out, the sanitized `recovery` object was empty even though code, stderr,
    final process scan and operator cleanup support the failure adjudication. Future runners must
    persist each completed recovery phase immediately, including failure-path cleanup.
11. P1.1 showed that an omitted Engine capacity let LiteRT select a 4096-state target and made
    Engine construction dominate startup. A rebooted 144-state comparison reached READY in
    `0.524 s / 3.744 s`, proving the capacity choice—not model hashing—was a major startup variable,
    but generation correctly failed because the fully rendered prompts required `170/171` tokens.
12. The product envelope of 128 input plus 16 output tokens is not an Engine-capacity calculation.
    Adapter instructions, serialization, chat rendering and runtime/model-internal expansion also
    consume state. A runner must measure the fully rendered/tokenized request and respect the
    artifact's available prefill signatures before freezing `max_num_tokens`.
13. Gemma's authenticated artifact exposes `prefill_128` and `prefill_1024`, not an arbitrary
    `prefill_512` signature. Its measured rendered maximum of 169 cannot use 128; experiments at
    192 and 512 still failed model-internal prefill. Selecting the next artifact boundary, 1024,
    produced formal READY in `837.103 ms`. Qwen independently supports 512 and produced isolated
    READY in `3490.826 ms`.
14. Full model hashing remains mandatory custody/provenance work, but it is not part of a usable
    child's P1 startup. The fresh one-pass SHA receipt must be created immediately before launch,
    outside the READY clock; the child validates the small receipt/config identity and constructs
    the real Engine before emitting READY. Static artifact identity alone cannot prove that the
    staged file used by a particular run was unchanged.

## 2. Runner design consequences

- A work package must execute the minimum lifecycle required by its contract. P1/P10A may share one
  persistent Engine. P6 should use an already healthy persistent child; it does not require another
  cold Engine. P7 then force-aborts that same child and performs exactly one required rebuild.
- Initial P1 READY and P7 recovery READY are distinct events. A runner must not silently apply one
  field to both merely because current configuration values happen to match; each timeout must be
  selected and reported by operation semantics.
- READY is a semantic readiness barrier, not a place to hide expensive checks or defer required
  initialization. Keep full artifact authentication before the clock, but retain Engine creation,
  exact small-receipt/config validation and READY emission inside it. Do not emit READY before the
  child can immediately accept a valid request.
- Treat protocol token limits, rendered prompt size, prefill signature and total Engine/KV capacity
  as four separate quantities. Tests and manifests must name each one explicitly; byte length and
  tokenizer count must not be substituted for one another.
- Capacity experiments must validate READY, PING, one real frozen generation, SHUTDOWN and orphan
  absence. A fast READY followed by runtime `ERROR`, as with the 144/171-token mismatch, is not a
  viable startup optimization.
- Candidate comparison requires either an independently reset target per candidate or explicit
  evidence that predecessor state cannot affect the measured item. Fixed candidate ordering alone
  is not isolation.
- Infrastructure attempts that fail before adapter launch do not consume a candidate observation,
  but they still require retained operator logs and a new run ID. Once a valid candidate workload
  begins, its result is immutable and must not be retried to select a favorable sample.
- Result schemas must accept partial cumulative receipts only for their declared P items and must
  reject a candidate PASS if any mandatory item in that focused scope is missing.

## 3. Gate 2 implications

- Gate 2A P2/P3/P4/P5/P8 should use one intentionally managed persistent Engine where the contract
  permits. It must not insert cold reloads between quality, performance, timeout and history work
  merely for runner convenience.
- P4 cold-start samples require prospectively declared reset conditions; they must not be mixed with
  hot/soak history or used as prerequisites for unrelated tests.
- Gate 2A must inherit Gemma's frozen 1024-state capacity unless a separately reviewed change is
  necessary. It must not restore the implicit 4096 default, infer 512 support from another Gemma
  variant, or equate the 144-token protocol envelope with Engine capacity.
- P5 must test the timeout and same-child health path directly. Any required rebuild belongs to its
  recovery proof, not to an extra pre-test Engine churn.
- Gate 2B has only the accepted finalist but adds Audio process history. The combined operator must
  declare launch order, target reset, process ownership and memory sampling boundaries so Audio
  warm-up or teardown cannot silently condition LLM evidence.
- Gate transition does not itself require rerunning accepted P items, but an actual lifecycle,
  timeout, config or operator change invalidates the affected evidence and must be called out.

## 4. Product implementation implications

- The evidence strengthens the product requirement for a persistent LiteRT-LM child. Recreating an
  Engine between sessions is both expensive and timing-variable even when model/config identity is
  unchanged.
- Product configuration should bind Engine capacity to the exact model artifact and rendered prompt
  contract. `prefill_1024` is an observed signature of this Gemma artifact, not a universal Gemma 4
  family rule and not a reason to increase the product input/output limits.
- Resource Manager recovery must terminate, wait and verify process-group absence before rebuilding.
  It should expose initial-start and rebuild timings separately so operational policy can distinguish
  deployment startup from recovery behavior.
- No production timeout change is recommended from this experiment. The focused P7 run tested the
  existing ten-second rebuild bound without redundant pre-P6 startup and failed that bound.
- mDNS is an operator convenience, not a health signal. Product or test automation should rely on
  explicit process/status receipts and a stable connection strategy.

## 5. Open questions

- Which native stage makes post-workload Qwen Engine construction variable?
- What product recovery disposition should Core use when Qwen initial READY passes but rebuild
  READY exceeds the existing ten-second bound?
- Does Gate 2A's current runner introduce any unnecessary Engine churn similar to Gate 1 v7?

These questions do not rewrite the retained evidence. The native-stage question requires a separate
non-scoring diagnostic only if it remains delivery-relevant after Gate 1 closure.

## 6. Post-review correction: P6.1/P7.1

Official LiteRT-LM v0.16 source review found that `CancelProcess()` is documented for asynchronous
inference and leaves the Conversation/session poisoned and unsupported for reuse. The legacy
synchronous `send_message()` plus cross-thread `cancel_process()` P6 method is therefore discarded
for P credit. Its immediately following P7 also cannot isolate process recovery from the cancel-
conditioned state.

The prospective replacement is `GATE1-P6.1-P7.1-REDESIGN-001`: P6.1 uses the official Python async
stream, one native cancel, terminal correlation, poisoned-Conversation disposal and same-Engine
new-Conversation health. P7.1 runs after an independent reboot, never invokes native cancel, records
abort-to-absence separately, retains the ten-second product READY SLA and continues only a
non-scoring diagnostic observation to 30 seconds. No legacy P6/P7 candidate credit is final while
these replacements are pending.
