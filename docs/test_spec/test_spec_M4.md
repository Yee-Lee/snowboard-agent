# M4 test-spec routing

本檔只保留 M4 子階段路由，不再混合 Accepted 與待修訂契約。

| Scope | Authority / state | Read when |
|---|---|---|
| M4 shared memory preflight | [`test_spec_M4_common.md`](test_spec_M4_common.md) | 修改或執行 combined capacity preflight |
| M4A Audio Gate 3 | [`test_spec_M4A.md`](test_spec_M4A.md) — Accepted, read-only | 處理 M4A regression 或 provenance |
| M4B LLM Gate 3 | 尚未建立；`TR_spec_M4B_IV` deferred | MVA adoption 與 affected design review 完成後，由 Tester 建立 |
| M4B R1 historical contract | [`archive/test_spec_M4B_R1.md`](archive/test_spec_M4B_R1.md) | 只追查舊 Test ID、candidate 或 finding |
| M4C integration | 尚未啟動 | M4C entry gate 開啟後 |

Agent 不得把 archived M4B R1 spec 當成目前 Developer entry 或 acceptance authority。
