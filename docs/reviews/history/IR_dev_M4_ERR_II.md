---
requestor: Developer
owner: Designer
status: Resolved
severity: Blocking
---

# IR_dev_M4_ERR_II — make the PI-012 `prefix` cause oracle executable

- Date: 2026-09-20
- Scope: `M4-ERR-PI-012`, `prefix` row only
- Unaffected work: PI-011, PI-012's other seven rows, public fatal renderer, affected regressions and
  WP7 may continue; final Pi Verify and commit remain blocked by this exact oracle conflict

## Blocking B1 — the required source exception does not exist in the specified stimulus

### Contract basis and locations

`docs/test_spec/test_spec_M4_ERR.md` §7 requires the retained function
`tests/test_m4b_p5_001.py::test_product_fatal_boundary_has_no_normal_fact_and_sanitized_traceback`
to run the same eight inputs with equivalent stimuli. Its `prefix` stimulus is:

    llm.result = replace(llm.result, safe_fragments=("PRIVATE-OUTPUT-CANARY",))

Here `llm.result` is a `SemanticGeneration`; `ProductLLM.generate()` returns that object. The Reasoner
then detects the invalid prefix locally. No exception is raised by the adapter. The exact per-case table,
however, requires `fault.__cause__` to be the original `ReplaceableGenerationFailure` with modified
`safe_fragments`, by object identity.

`ReplaceableGenerationFailure` is a separate `RuntimeError` type whose constructor accepts only a stable
failure code. It has no `safe_fragments` field. Therefore the specified stimulus creates no such exception
object whose identity the assertion could retain.

### Reproducible evidence

The object types and actual source path are directly observable with:

    PYTHONPATH=src .venv/bin/python - <<'PY'
    from dataclasses import replace
    from tests.test_m4b_outcome_001 import ProductLLM
    from sbd.cognition.llm import ReplaceableGenerationFailure
    llm = ProductLLM()
    llm.result = replace(llm.result, safe_fragments=("PRIVATE-OUTPUT-CANARY",))
    print(type(llm.result).__name__)
    print(hasattr(ReplaceableGenerationFailure("INVALID_SEMANTIC"), "safe_fragments"))
    PY

The result is `SemanticGeneration` and `False`. Exercising the current test reaches the Reasoner's local
`INVALID_SEMANTIC_PREFIX` check; there is no adapter exception available to use as `__cause__`.

### Expected versus actual and impact

- Expected by the table: identity with an original `ReplaceableGenerationFailure` carrying modified
  `safe_fragments`.
- Actual equivalent stimulus: one malformed returned `SemanticGeneration` and a local prefix contract
  failure, with no source exception.
- Impact: Developer must either fabricate a cause that never occurred, change the stimulus away from the
  retained prefix case, or violate the exact table. Any of those would make PI-012 false evidence.

### Requested disposition and minimum acceptance

Please route one focused Tester correction choosing one executable oracle:

1. retain the current/equivalent malformed-`SemanticGeneration` stimulus and specify
   `fault.__cause__ is None`, consistent with a local contract check; or
2. define an actual adapter stimulus that raises a concrete, pre-created exception object, and specify
   how it represents the prefix failure while preserving object identity.

The correction must change only the `prefix` row and directly dependent wording/counts. The other seven
cause rows, product sanitized renderer, four-function G06 exemption, G05 inclusion, historical authority
and same-bytes Pi requirement remain unchanged.

## Designer disposition — Revised 2026-09-20

B1接受為Blocking。現有／等價刺激建立的是`SemanticGeneration`，Reasoner在本地檢查
`safe_fragments`後產生`INVALID_SEMANTIC_PREFIX`；此路徑沒有adapter source exception，也不存在可做
identity assertion的`ReplaceableGenerationFailure`。不得為符合測試而虛構cause或更換刺激。

採用requested disposition 1。Tester只修正`M4-ERR-PI-012`的`prefix` row及直接相依文字：

- 保留malformed `SemanticGeneration`與`safe_fragments=("PRIVATE-OUTPUT-CANARY",)`刺激；
- exact oracle改為`fault.__cause__ is None`，理由為local contract check、無chained source exception；
- acceptance的identity集合改為`untyped`／`fatal`／`proof`，`None`集合加入`prefix`；
- public sanitized renderer仍須零canary、單一safe root，responses仍為零且恰一個safe `ErrorOccurred`。

Test Spec只有兩個直接修改點，使用以下exact replacement：

1. per-case table的`prefix` row改為：

   `| prefix | __cause__ is None — malformed SemanticGeneration fails the local prefix contract; no chained source exception |`

2. Part 1 acceptance的cause集合改為：

   `__cause__ matches the per-case exact table above (object identity for untyped/fatal/proof; is None for prefix/semantic/capability/unsupported/generation).`

除此之外不得修改PI-012 context、步驟、renderer assertions、Part 2、scope note、Test ID index、WP／§6
traceability或§7.1。上述兩處完成且`rg`不再找到把`prefix`列入identity集合的文字，即滿足本review。

其他七列、PI-011、產品renderer、G05 inclusion、四function G06 exemption、Accepted歷史authority、
traceability與same-bytes Pi要求不得改動。修正完成前，PI-012 final、Pi Verify、commit與push維持關閉；
其餘Developer work可繼續。

## Designer final recheck — Resolved 2026-09-20

Tester只修改兩個核准位置：PI-012 per-case table的`prefix` row現為local contract check
`__cause__ is None`；Part 1 acceptance現將identity限定為`untyped`／`fatal`／`proof`，並把`prefix`納入
None集合。搜尋未再發現把`prefix`列入identity集合的文字；PI-012其餘內容與`test_spec_M4B.md`未變。

本review Resolved。Developer可依修正後oracle完成PI-012與affected regressions，之後執行完整
same-bytes M4-ERR Pi Verify run；通過前不得commit或push。
