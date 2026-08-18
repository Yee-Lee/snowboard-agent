# LLM POC Team → PM → Core Designer: M4b Gate 0 Receipt R2

- **Delivery ID**: `DELIVERY-001-PM-LLM-POC-GATE0-RECEIPT-R2`
- **In Response To**: `DELIVERY-LLM-POC-M4B-CONTRACT-001`
- **Core revision**: `2026-08-17 / PM-OUT-260817-015`
- **Finding IDs**: `OUT-M4B-2026-002` through `OUT-M4B-2026-007`
- **From**: LLM POC Team
- **To**: PM for Core Designer recording
- **Date**: 2026-08-18
- **Status**: `R2 REVISION 001 RESUBMITTED — PENDING CORE DESIGNER EXACT-SHA REVIEW`

本 receipt 不包含 delivery commit SHA。PM 拉回約定 branch 後自行記錄實際 HEAD，再交
Core Designer 登錄。POC Team 不以 branch 名稱、內部 ACK 或本 receipt 自行宣告 Gate 0
`COMPLETE`。

## 1. Contract Receipt and Boundary Confirmation

LLM POC Team 確認已閱讀並承接 `DELIVERY-LLM-POC-M4B-CONTRACT-001` 的
2026-08-17 revision（包含 `OUT-M4B-2026-002～006`）：

- POC 範圍為 runtime/model/quantization 探索、Ubuntu pre-screen、persistent-child
  reference wrapper、Pi 5 M4B-P1～P12 validation 與可重現 evidence。
- Core Designer 保留 candidate/finalist、model baseline、protocol、Gate 1、Gate 2A/2B 與
  final winner/no-go 的核准權。
- POC Team self-test、Technical Lead review 與本團隊 ACK 不能取代 Core Designer ACK；
  正式 POC acceptance 另需 Internal Tester confirmation。
- Model weights、大型 raw results、private prompt/output、endpoint、credential、secret 與
  SSH 設定不進 Git。

## 2. Gate and Milestone State

| State type | Current state | Recorder / approver |
| --- | --- | --- |
| External Gate 0 | `SUBMITTED R2` | Core Designer 對 R2 exact SHA intake 後才 `COMPLETE` |
| Internal M0 | `NOT_STARTED` | Entry review、User/Pi 授權、immutable packet 核准後才可開始 |
| External Gate 1 | `NOT_STARTED / BLOCKED` | Ubuntu pre-screen 完成後由 Core Designer 書面確認 |
| External Gate 2A | `NOT_STARTED / BLOCKED` | Gate 1 ACK 後才可執行 LLM-only；僅 provisional finalist |
| External Gate 2B | `NOT_STARTED / BLOCKED` | Accepted Audio package + 2A ACK 後；通過才可 final winner |

Core 對 `1d3444009a1edbf63e1b24a5e6977cbdb7203c80` 提出的
`DELIVERY-LLM-POC-M4B-GATE0-R2-REVISION-001` 已收件。POC 已針對唯一 blocker
`OUT-M4B-2026-007` 以 `G1-UBUNTU-PRESCREEN-002` 修正；在 Core 複驗新 exact SHA 前，
Gate 0 R2 仍未完成，015 仍未關閉。

Gate 0 行政收件與 Internal M0 readiness 完全分離。Receipt 提交不代表 Pi 存取、安裝、
下載、網路切換、Ubuntu benchmark 或 Gate 2A/2B hardware run 已獲准。

## 3. Submitted Initial Manifest

實際 Gate 0 manifest：

`poc_llm/deliveries/POC-llm-DEL-2026-001-R2.md`

Manifest 記錄 repo/branch、環境與 runner 狀態、artifact/evidence 狀態、真實存在路徑、
blockers 及下一個獲准工作；未執行項目只標 `Pending` 或 `Blocked`。規劃中的目錄樹不再
被當成 manifest。

唯一 taxonomy 與 External Gate／Internal Milestone／D1–D8／M4B-P1～P12 crosswalk：

`docs/milestone/m4b_traceability_crosswalk.md`

Authoritative Gate 1／2A／2B work-package plan：

`docs/milestone/m4b_execution_plan.md`

Authoritative Gate 1 executable packet：

`poc_llm/tests/gate1/GATE1-PACKET-002.md`

## 4. Gate 1 Preparation Boundary

Gate 0 登錄後，POC Team 可依序準備：

1. 完成 Internal M0 entry review 與核准的 readiness run。
2. 固定 runtime/model/quantization/config pairing ID、license、source/artifact checksum、
   offline method 與 aarch64 compatibility preflight。
3. 凍結 Ubuntu x86/arm64 packet、metrics、淘汰規則與重跑上限。
4. 執行獲准的 Ubuntu pre-screen，最多提出兩個 Pi candidates。
5. 等待 Core Designer Gate 1 書面確認；在此之前不執行 Gate 2A。
6. Gate 2A 只產生 provisional finalist；Gate 2B P9/P10B 與 regression 通過後才可
   由 Core Designer 決定 final winner。

## 5. Requested PM Action

請 PM：

1. 拉回約定 branch 並自行記錄實際 branch HEAD。
2. 確認本 receipt、readiness response、Initial Manifest 與其中列出的相對路徑存在。
3. 將 receipt 交 Core Designer 登錄 External Gate 0。
4. 對本次新 commit exact SHA 複驗；Gate 1 未經書面確認不得啟動 Gate 2A，Accepted
   Audio package 未到位不得啟動 Gate 2B。
