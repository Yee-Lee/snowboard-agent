---
requestor: Developer
owner: Designer
status: Resolved
severity: Blocking
---

# IR_dev_M4_ERR_I — make M4-ERR supersession of retained M4A/M4B assertions explicit

- Date: 2026-09-20
- Scope: M4-ERR TTS backend disposition, typed cause chain, public diagnostic privacy, and the directly
  affected retained M4A/M4B regression gates
- USER disposition: on 2026-09-20 USER explicitly selected the current M4-ERR semantics for both
  conflicts below
- Unaffected work: M4-ERR fault taxonomy, other component mappings, portable implementation and the
  actual-hardware injection harness may continue; Pi verification and commit remain closed

## Blocking B1 — retained M4A requires reuse of a TTS backend that M4-ERR requires rebuilding

### Contract basis and conflicting locations

M4-ERR design §3.2 defines `REBUILD_REQUIRED` as a backend that cannot accept another admission until
Level 2 destruction and Resource Manager rebuild. Section 4.4 assigns both native TTS generation failure
and protocol/PCM/child failure to `REBUILD_REQUIRED` with the stable TTS key. M4-ERR Test Spec PI-007
maps the same typed codes, disposition and Level 2 result.

The retained `tests/test_m4a_tts_002.py` instead requires:

- `test_m4a_tts_002_persistent_error_reopen_and_next_success`: `GENERATION_REJECTED` remains an
  `AdapterRejected`, the second request succeeds, and the same child has `start_count == 1`;
- `test_m4a_tts_002_every_whitelisted_error_reopens_same_child`: every whitelisted child error permits
  another request on the same READY child.

`tests/test_m4b_reg_001.py` G05 executes the complete retained M4A files, while G06 requires every retained
definition to remain AST-identical to SHA `54c506713082b1ea95cfa331f08b7124dcfa0316`. Developer therefore
cannot align these two assertions without first changing the authority that declares them immutable.

### Reproducible evidence

On the current workstation candidate, this bounded command reproduces the conflict:

    PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 \
      .venv/bin/python -B -m pytest -p no:cacheprovider --capture=sys \
      tests/test_m4a_tts_002.py::test_m4a_tts_002_persistent_error_reopen_and_next_success \
      tests/test_m4a_tts_002.py::test_m4a_tts_002_every_whitelisted_error_reopens_same_child

All four selected cases fail because the adapter destroys the child and raises a typed
`ComponentSystemFault`: `TTS_GENERATION_FAILED` for `GENERATION_REJECTED`, and
`TTS_PROTOCOL_FAILED` for the other whitelisted errors. Each has `REBUILD_REQUIRED`, the TTS recovery
key and the original request error as `__cause__`. This is the current M4-ERR behavior, not an accidental
test-only divergence.

### Expected versus actual and impact

- Expected under the USER-selected M4-ERR contract: the fault is typed, the child is destroyed, no new
  admission occurs before recovery, Level 2 reports the exact TTS key, RM rebuilds, and only the rebuilt
  backend may return READY.
- Actual retained oracle: the failure is request-level and the same child must accept the next operation.
- Impact: either implementation violates M4-ERR backend safety or G05/G06 necessarily fail. A compatibility
  branch that reuses the poisoned child would create a false green gate and is not acceptable.

### Requested Designer disposition and minimum acceptance

Revise M4-ERR design authority to say explicitly that accepted M4A results remain immutable historical
evidence, while M4-ERR prospectively supersedes only the post-fault same-child reuse assertions above.
Route a focused Tester revision that:

1. preserves G05 coverage and G06 anti-weakening protection for every unaffected M4A definition;
2. replaces only the affected assertions with exact typed code/disposition/key, destroyed-child,
   no-admission-before-recovery, RM rebuild and next-READY-on-rebuilt-backend checks;
3. states how the new prospective baseline is bound without editing or relabelling the old SHA/evidence;
4. requires the affected portable suite and same-bytes Pi M4-ERR verification before commit.

## Blocking B2 — retained M4B suppresses `__cause__` while M4-ERR requires an identity-preserved cause chain

### Contract basis and conflicting locations

M4-ERR design §§3.1 and 3.3 require every production mapping to raise the typed fault using
`raise fault from cause`; the original exception remains in the task exception chain but not in
`ErrorOccurred` or Display. M4-ERR Test Spec PU-006 and PI-010 require object-identity preservation in
`fault.__cause__` at the real mapping sites. Design §5 separately says public canonical diagnostics are
sanitized and that a raw cause appears once only in the final Level 3 root traceback.

The retained `tests/test_m4b_p5_001.py::test_product_fatal_boundary_has_no_normal_fact_and_sanitized_traceback`
requires `error.__cause__ is None` and requires generic `traceback.format_exception(error)` not to contain
the injected private sentinel. In addition,
`tests/test_m4b_priv_001.py::test_V01_completion_callback_failure_reaches_worker_supervision` expects the
original `ObservationError`, whereas current M4-ERR mapping correctly raises a typed
`ComponentSystemFault` from it after one safe `ErrorOccurred`.

### Reproducible evidence

Running the retained M4B fatal-boundary test on the current candidate produces eight failures at the
`error.__cause__ is None` assertion; the actual values are the original per-case exception objects. Running
the V01 test with normal pytest plugin loading produces one failure because the actual supervised exception
is `ComponentSystemFault(code="SPEAK_UNEXPECTED", backend=UNPROVEN)` raised from the original
`ObservationError`. The public event remains typed and the PCM owner is cleared.

The fatal-boundary conflict is reproducible with:

    PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 \
      .venv/bin/python -B -m pytest -p no:cacheprovider --capture=sys \
      tests/test_m4b_p5_001.py::test_product_fatal_boundary_has_no_normal_fact_and_sanitized_traceback

The V01 conflict is reproducible with:

    PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest \
      -p no:cacheprovider --capture=sys \
      tests/test_m4b_priv_001.py::test_V01_completion_callback_failure_reaches_worker_supervision

### Expected versus actual and impact

- Expected under M4-ERR: the task raises one typed fault whose `__cause__` is the exact original exception;
  public `ErrorOccurred`, ordinary canonical log and Display projection contain only safe fields.
- Actual retained oracle: the cause link must be removed, and one observer failure must escape untyped.
- Impact: satisfying the retained tests would delete mandatory supervision information. Satisfying M4-ERR
  makes the protected M4B gate fail. The existing wording also leaves the visibility of the final Level 3
  traceback underspecified: Python's normal chained traceback includes cause text, so it cannot be both a
  raw-cause traceback and a public privacy-safe diagnostic without an explicit access boundary.

### Requested Designer disposition and minimum acceptance

Revise M4-ERR authority to state that accepted M4B evidence remains historical, while M4-ERR prospectively
supersedes only the `__cause__ is None` and untyped-observer-exception expectations. Define the diagnostic
boundary precisely:

1. `fault.__cause__ is original_cause` remains mandatory inside the supervised task exception chain;
2. `ErrorOccurred`, Display, structured/public evidence and ordinary canonical logs contain no private
   sentinel, payload or raw exception text;
3. if the Level 3 root traceback may contain the raw cause, name its private storage/access boundary; if it
   is public, require a sanitized/type-only renderer rather than generic chained formatting;
4. Tester replaces only the affected retained assertions while preserving no-normal-Fact, exactly-one-safe-
   event, cancellation, cleanup and all unrelated M4B privacy/anti-weakening checks.

## Proposed authority text

Designer may adopt the following wording or an equivalent contract:

> Accepted M4A/M4B artifacts and results remain immutable historical evidence. For candidates containing
> M4-ERR, M4-ERR prospectively supersedes (a) same-child reuse after TTS generation, protocol, PCM or child
> failure and (b) suppression of a mapped system fault's `__cause__`. Directly affected retained assertions
> are migrated to the M4-ERR typed-fault, rebuild and private-cause-chain contract; every unrelated identity,
> lifecycle, cleanup, cancellation, privacy and anti-weakening assertion remains protected.

This review asks for design/test authority alignment only. It does not authorize weakening unrelated gates,
claim Pi evidence, alter historical results, commit, or push.

## Designer disposition — Revised 2026-09-20

B1與B2均接受為Blocking。`ch_m4_error_handling.md`現已明定：Accepted M4A／M4B SHA、test definitions與
結果保持歷史不可改寫；M4-ERR只前瞻性取代本單列名的same-child reuse、`__cause__ is None`及untyped
observer escape oracle。TTS system fault後必須destroy／rebuild，下一次READY來自rebuild後backend。

Cause chain邊界固定為受監督task內的private in-memory exception object；所有Event、Display、structured／
public evidence、ordinary log及public fatal output都必須sanitized。Level 3使用single first-root type/code-only
renderer，不得以generic chained formatting公開raw cause；本slice不保存raw cause artifact。

下一步由Tester只修訂直接受影響的M4-ERR及retained regression oracle，保留所有未受影響G05/G06保護，
並以candidate digest及相同bytes M4-ERR Pi Verify evidence建立prospective baseline。Developer可繼續未受
影響實作，但affected regression、Pi Verify與commit在Test Spec完成聚焦revision前維持關閉。

## Tester oracle revision v2 — 2026-09-20

已依 Designer recheck blocking 1–6 完成一次性修正（第 7 點由 Designer 已處理）：

1. **公開 renderer**：PI-012 改為呼叫產品 sanitized first-root renderer，斷言其輸出 canary-free；明確要求不使用 `traceback.format_exception` 作為 public renderer。
2. **Exact oracle**：`semantic`/`capability`/`unsupported`/`generation` 改為精確 `__cause__ is None`（無 source exception 的 local contract check）；`untyped`/`fatal`/`proof`/`prefix` 改為 object identity assertion。以 per-case 表格列明。
3. **G05 coverage 恢復**：兩個 M4A TTS functions 保留在 G05 執行（不排除）；G05 rationale 須列出其更新 oracle。§7.1 改標題為「G06 AST-identity exemption」並在 PI-011 context 明確標注「included in G05」。
4. **`test_spec_M4B.md` 恢復**：移除上次誤加入的 M4-ERR exemption 條款；G05/G06 恢復原始文字。prospective overlay 只放在本 spec §7。
5. **數量精確**：§7 開頭以表格列出四個函數、三類舊 expectation、兩個 Test ID，消除「three retained oracle functions」/「six function names」/「four nodes excluded」矛盾。
6. **Traceability**：PI-012 WP 改為 `WP1/WP4/WP5`；WP4 coverage 加入 PI-012；§6 加入兩條 prospective supersession rows。PI-011 exact code mapping 表格（`GENERATION_REJECTED → TTS_GENERATION_FAILED`，`INVALID_TEXT`/`INVALID_PCM → TTS_PROTOCOL_FAILED`）。
7. **Status**：§1 反映 focused revision in progress；affected regression/Pi Verify/commit closed；IR status 由 Designer 已維持 Rejected/Revised，Tester 不再更動。

**修訂文件**：[`test_spec_M4_ERR.md`](../test_spec/test_spec_M4_ERR.md)（§1、§4、§5、§6、§7、§7.1）。
**未修改**：[`test_spec_M4B.md`](../test_spec/test_spec_M4B.md)（已恢復原始 G05/G06）。

Next owner：Designer 確認 blocking 全部清除。

## Designer recheck — Rejected/Revised 2026-09-20

Tester revision的方向正確，但尚有下列blocking；一次修正後再交Designer確認，不擴大scope：

1. **Public traceback oracle與Design §5矛盾。** `M4-ERR-PI-012`仍要求
   `traceback.format_exception(error)`在保留含canary的`__cause__`時輸出無canary；Python generic chained
   formatter必然展開cause，且Design已明定它不是public renderer。改為直接呼叫產品的sanitized
   first-root renderer並檢查type／safe code、single root及零sentinel；另以object identity檢查private
   `__cause__`。測試須證明public path沒有使用generic chained formatter，不得把generic formatter輸出
   當成public output。
2. **Cause oracle不是exact。** `semantic`、`capability`、`unsupported`、`generation`目前寫成「assert
   whichever implementation produces」。這不構成可執行判定。逐case固定預期；沒有source exception的
   local contract／state fault須明定`__cause__ is None`，有source exception的mapping則必須對原物件做
   identity assertion，不允許二選一。
3. **G05 coverage被錯誤移除。** 兩個M4A TTS functions必須仍由G05執行，只把其assertions更新為
   `M4-ERR-PI-011` oracle；不得從G05 selector排除。G06只對四個具名functions解除舊SHA的AST identity，
   其餘definition維持完整保護。`docs/test_spec/test_spec_M4B.md`是Accepted歷史authority，本次新增的
   M4-ERR exemption必須回復；prospective overlay只放在`test_spec_M4_ERR.md`，既有G06的「upstream
   approved authority explicitly replaces it」已足以引用本Design。
4. **名稱／數量不一致。** 本次是四個具名functions、三類舊expectation、兩個新Test IDs。把「three
   retained oracle functions」、「six function names」及G05「four nodes excluded」等敘述全部改成精確
   數量；§7.1只列四個functions。
5. **Traceability少WP4及prospective row。** `M4-ERR-PI-012`同時覆蓋Reasoner／LLM與Speak，因此WP欄、
   Test ID index及WP table須為`WP1/WP4/WP5`；§6另加prospective supersession row，映射
   `M4-ERR-PI-011`、`M4-ERR-PI-012`。PI-011並須明列三個exact code mapping：
   `GENERATION_REJECTED → TTS_GENERATION_FAILED`，`INVALID_TEXT`／`INVALID_PCM → TTS_PROTOCOL_FAILED`。
6. **狀態不得提前宣稱complete。** 上述blocking清除前，文件頂部須反映focused revision in progress，
   affected regression／Pi Verify／commit closed；全部修正後才恢復Test Spec complete與Developer route。
7. **Review狀態值無效。** review process只允許`Open → Revised → Rejected/Revised → Resolved`；Tester不得
   寫`Closed`或自行宣告owner review完成。本次已由Designer改回`Rejected/Revised`。

其餘prospective history boundary、TTS destruction／no-admission／RM rebuild／replacement READY、單一safe
`ErrorOccurred`、unaffected assertions保留及same-bytes Pi evidence要求已接受，不需重寫。

## Designer final recheck — Resolved 2026-09-20

Tester revision v2清除全部七項blocking。`M4-ERR-PI-012`改用產品sanitized first-root renderer並固定八個
case的exact cause oracle；兩個M4A TTS functions保留在G05；Accepted `test_spec_M4B.md`已恢復；四個
具名functions／三類expectation／兩個Test IDs、WP1/WP4/WP5及§6 traceability一致；PI-011三個native
code mapping完整。§1所述pending final alignment由本disposition滿足。

本review Resolved。Developer須依修訂後Test Spec完成PI-011／PI-012、所有affected regression與完整
same-bytes M4-ERR Pi Verify run；未有通過證據前不得commit或push。
