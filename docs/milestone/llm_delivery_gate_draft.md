# LLM POC Delivery Gate — Historical Working Draft

狀態：`SUPERSEDED FOR TRACEABILITY`

最後更新：2026-08-18

> D1–D8 的權威定義、External Gate／Internal Milestone 映射及 M4B-P1～P12
> crosswalk 已移至 [M4b Delivery Taxonomy and Traceability Crosswalk](m4b_traceability_crosswalk.md)。
> 本檔以下內容只保留為 Gate 0 前的規劃歷史，不得作為狀態或追蹤來源。

## Authority and Use

本文件把現有 `AGENTS.md`、LLM POC workflow 與 M4b task boundary 轉成可追蹤的
repo working plan。它不是 PM/Designer Income，也不代表正式 gate 已核准。

正式 `docs/pm_handoff/llm_poc_delivery_checklist.md` 收到後，Technical Lead 必須
建立逐項差異表。任何新增或改變的 blocking requirement 必須回寫 milestone index、
風險與 change request。

在本文件仍為 `NOT_FROZEN` 時：

- 可以規劃 M0 test packet、schema 與 deterministic fake。
- 不得宣告 runtime/model winner。
- 不得把 hardware run 判定為正式 milestone `PASS`。
- 不得降低或猜測 Designer 尚未核准的品質/資源門檻。

## D1 — Governance and Delivery Manifest

- [ ] Delivery ID、repo、branch、baseline SHA 與完整 40-character delivery SHA。
- [ ] Milestone entry/exit decision、owner、Test ID、finding 與 change-request index。
- [ ] Workstation/Pi environment、命令、result schema、raw/sanitized evidence location。
- [ ] 交付狀態清楚區分 `Ready for internal review` 與 `POC Accepted`。

## D2 — Reproducible Runtime and Model

- [ ] 唯一 runtime/driver、精確版本與 aarch64/Raspberry Pi 5 setup 已固定。
- [ ] Model artifact、quantization、來源、checksum、license 與再散布限制已固定。
- [ ] Context/output token limits、temperature、top-p、threads、startup/generate/cancel
      timeout 與 strict config 已固定。
- [ ] 無 runtime download、浮動版本或未核准 fallback model。
- [ ] `docs/model_spec.md` handoff content 與 winner manifest 一致。

## D3 — Prompt Boundary and Child Protocol

- [ ] PromptBuilder input、perception/capability view 與敏感內容邊界已固定。
- [ ] Output schema 只允許合法 `speak`、`tool`、`rest` action；model 不執行 tool。
- [ ] Protocol 定義 version、READY、GENERATE、RESULT、CANCEL、ERROR、SHUTDOWN、
      request ID、deadline、completion/exit proof。
- [ ] 一次只允許一個 active generation；stale/duplicate result 不污染目前 request。
- [ ] Cancel escalation 覆蓋 cooperative cancel、terminate、kill、waitpid 與 orphan=0。
- [ ] `docs/protocol.md` handoff content 與實作/schema 一致。

## D4 — Functional and Isolation Evidence

- [ ] 合法 action、malformed output、schema violation 與 P5 fallback。
- [ ] Tool/capability allowlist 與 payload validation。
- [ ] 每個 operation 使用新的 single-turn conversation；hidden history/KV state 不跨 operation。
- [ ] Crash、timeout、cancel、force-abort、rebuild、shutdown 與 repeated-session cleanup。
- [ ] 一般 log 不含 prompt、perception text、raw model output、tool payload 或 private text。

## D5 — Raspberry Pi 5 Performance and Resource Evidence

- [ ] Pi model/RAM、OS、kernel、architecture、runtime dependencies、clock、temperature
      與 throttling 狀態。
- [ ] Cold READY、cold/hot generation latency、p50/p95、tokens/s。
- [ ] Peak/steady RSS、disk、CPU、threads/processes 與 thermal behavior。
- [ ] 固定 fixture、warm-up、repetitions、sampling/config 與量測工具。
- [ ] 每次 run 記錄 candidate ID、artifact checksum、exact SHA、exit code 與 cleanup proof。

## D6 — M4a Combined Validation

- [ ] 使用活動產品 repo 明確 Accepted 的 M4a Audio HAL 完整 SHA。
- [ ] 登錄 M4a owner、acceptance reference、Test ID、取得路徑與已知限制。
- [ ] Audio models 與 LLM 同時常駐，完成至少 20 個固定 combined sessions。
- [ ] LLM timeout/cancel/crash 不重新定義 Audio 結果，也不繞過 recovery/state boundary。
- [ ] Offline run 與 failure injection 後 child/process/thread/device/resource owner 均無殘留。

## D7 — Winner or No-go Decision

- [ ] 每個 candidate 都有 advance/reject、失敗結果與理由。
- [ ] 唯一 winner 同時通過 validity、function、resource、cleanup、offline 與 combined gates；
      否則提交 evidence-backed no-go。
- [ ] 不因結果不佳而事後修改 fixture、metric 或 gate。
- [ ] Rejected candidates、已知限制、產品化建議與不可重用 POC code 已列明。

## D8 — Data, Artifact and Review Safety

- [ ] Git 不含模型、大型 raw results、private prompt/transcript、secret、endpoint 或 credential。
- [ ] Git 外 artifact 具有受控位置、checksum、license 與重現方法。
- [ ] Repo 只保存 sanitized summary/index；raw evidence 走核准的受控管道。
- [ ] 完整 SHA 交付只標記 `Ready for internal review`。
- [ ] Tester/Reviewer 關閉 blocking findings 且 Designer 核准後，才標記 `POC Accepted`。
