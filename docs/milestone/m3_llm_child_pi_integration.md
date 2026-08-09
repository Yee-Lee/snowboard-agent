# LLM M3：Persistent Child and Pi Integration Baseline

狀態：`NOT_STARTED`

## 目標與交付貢獻

固定唯一 POC winner（或確認 no-go），完成 reference child/client、strict config 與
failure lifecycle，證明其可在 Pi 5 長時間、可取消、可清理且不跨 operation 保留
history。主要推進 D2、D3、D4、D5、D7。

## Entry Conditions

- M2 `COMPLETE` 且 finalist/winner recommendation 已由 Designer 接受；或 no-go 已進 gate review。
- Runtime/model/artifact/config 與 protocol versions 均已固定。
- Reasoner boundary fixtures 可用，但產品 composition root 不在本 POC 修改範圍。
- M4 所需 accepted M4a SHA dependency 已有 owner、取得路徑與風險狀態。

## Work Packet

- 實作/固定 reference persistent child 與 client，使用 versioned framed protocol。
- 驗證 READY gate、bounded request、唯一 active generation 與 request-ID correlation。
- 驗證 cooperative cancel；逾時後 terminate、kill、waitpid，並拒絕 stale/duplicate result。
- 驗證 child crash/rebuild、shutdown/restart、strict config、offline 與 repeated generation。
- 使用固定 Pi packet 重跑 latency/resource/thermal 並檢查 process/thread/RSS 累積。
- 產出 `model_spec.md`、`protocol.md` 所需 handoff material，但不直接修改產品 composition root。

## Exit Gate

- 唯一 winner 的 artifact/config/protocol 與 manifest 完全一致；否則正式 no-go。
- Success、timeout、cancel、force-abort、crash、rebuild、shutdown 均有 completion/exit proof。
- History isolation、log hygiene、strict config、offline 與 orphan=0 均通過。
- Pi performance/resource gates 通過，或未通過項目已形成 change request/no-go。
- M4 combined packet、M4a dependency與 acceptance criteria 已可執行。

## Necessary Evidence

- Reference child/client source、tests、schema、fixtures 與 reproducible commands。
- Winner manifest、artifact checksum/license/source、Pi metrics 與 fault matrix。
- Exit/orphan proof、known limits、M4 test request 與 M4a dependency record。

## Prohibited in M3

- 不把 POC wrapper 視為已完成主線產品化。
- 不繞過 Reasoner validator、StateManager 或 recovery boundary。
- 不以隱式 fallback runtime/model 掩蓋 winner failure。
