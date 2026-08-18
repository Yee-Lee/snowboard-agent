# LLM M3：Gate 2A LLM-only Pi Validation

狀態：`NOT_STARTED`

## 目標與交付貢獻

對 Gate 1 核准的最多兩個 candidates 執行 Gate 2A：Pi 5 LLM-only P1～P8、P10A、
P11、P12。2A 只能提出 provisional finalist 或 no-go，不能決定 final winner。
主要推進 D2、D3、D4、D5、D6、D7、D8。

## Entry Conditions

- M2 `COMPLETE`，且 External Gate 1 finalists 已取得 Core Designer 書面 ACK。
- Runtime/model/artifact/config 與 protocol versions 均已固定。
- Reasoner boundary fixtures 可用，但產品 composition root 不在本 POC 修改範圍。
- M4 所需 accepted M4a SHA dependency 已有 owner、取得路徑與風險狀態。

## Work Packet

- 實作/固定 reference persistent child 與 client，使用 versioned framed protocol。
- 驗證 READY gate、bounded request、唯一 active generation 與 request-ID correlation。
- 驗證 cooperative cancel；逾時後 terminate、kill、waitpid，並拒絕 stale/duplicate result。
- 驗證 child crash/rebuild、shutdown/restart、strict config、offline 與 repeated generation。
- 使用 4GB mandatory、swap=0 Pi packet；8GB 只作 identical-config informational run。
- 依權威 crosswalk 執行 P1～P8、P10A、P11、P12；P4 採 fixed cold/hot method，P6
  採 conditional escalation，其他 mandatory gate 不得降低。
- 產出 `model_spec.md`、`protocol.md` 所需 handoff material，但不直接修改產品 composition root。

## Exit Gate

- Provisional finalist 的 artifact/config/protocol 與 manifest 完全一致；否則正式 no-go。
- Success、timeout、cancel、force-abort、crash、rebuild、shutdown 均有 completion/exit proof。
- History isolation、log hygiene、strict config、offline 與 orphan=0 均通過。
- Pi performance/resource gates 通過，或未通過項目已形成 change request/no-go。
- Gate 2A work packages 全部依 `m4b_execution_plan.md` 結案；Core Designer 只發
  provisional finalist ACK。Gate 2B 所需 Accepted Audio dependency 已明列，缺件維持 Blocked。

## Necessary Evidence

- Reference child/client source、tests、schema、fixtures 與 reproducible commands。
- Provisional manifest、artifact checksum/license/source、Pi metrics 與 fault matrix。
- Exit/orphan proof、known limits、M4 test request 與 M4a dependency record。

## Prohibited in M3

- 不把 POC wrapper 視為已完成主線產品化。
- 不把 Gate 2A provisional finalist 稱為 final winner 或產品 baseline。
- 不繞過 Reasoner validator、StateManager 或 recovery boundary。
- 不以隱式 fallback runtime/model 掩蓋 winner failure。
