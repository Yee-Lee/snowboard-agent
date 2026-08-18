# LLM POC Team → PM → Core Designer: M4b Gate 0 Receipt R1

- **Delivery ID**: `DELIVERY-001-PM-LLM-POC-GATE0-RECEIPT-R1`
- **In Response To**: `DELIVERY-LLM-POC-M4B-CONTRACT-001`
- **Correction**: `PM-POC-LLM-20260817-001`
- **Finding IDs**: `POC-LLM-GOV-2026-001` through `POC-LLM-BOUNDARY-2026-005`
- **From**: LLM POC Team
- **To**: PM for Core Designer recording
- **Date**: 2026-08-18
- **Status**: `SUBMITTED — PENDING PM RECEIPT / CORE DESIGNER RECORDING`

本 receipt 不包含 delivery commit SHA。PM 拉回約定 branch 後自行記錄實際 HEAD，再交
Core Designer 登錄。POC Team 不以 branch 名稱、內部 ACK 或本 receipt 自行宣告 Gate 0
`COMPLETE`。

## 1. Contract Receipt and Boundary Confirmation

LLM POC Team 確認已閱讀並承接 `DELIVERY-LLM-POC-M4B-CONTRACT-001`：

- POC 範圍為 runtime/model/quantization 探索、Ubuntu pre-screen、persistent-child
  reference wrapper、Pi 5 M4B-P1～P12 validation 與可重現 evidence。
- Core Designer 保留 candidate/finalist、model baseline、protocol、Gate 1、Gate 2 與
  final winner/no-go 的核准權。
- POC Team self-test、Technical Lead review 與本團隊 ACK 不能取代 Core Designer ACK；
  正式 POC acceptance 另需 Internal Tester confirmation。
- Model weights、大型 raw results、private prompt/output、endpoint、credential、secret 與
  SSH 設定不進 Git。

## 2. Gate and Milestone State

| State type | Current state | Recorder / approver |
| --- | --- | --- |
| External Gate 0 | `SUBMITTED` | PM 記錄實際 HEAD；Core Designer 登錄後才 `COMPLETE` |
| Internal M0 | `NOT_STARTED` | Entry review、User/Pi 授權、immutable packet 核准後才可開始 |
| External Gate 1 | `NOT_STARTED / BLOCKED` | Ubuntu pre-screen 完成後由 Core Designer 書面確認 |
| External Gate 2 | `NOT_STARTED / BLOCKED` | Gate 1 ACK 後才可開始 Pi candidate validation |

Gate 0 行政收件與 Internal M0 readiness 完全分離。Receipt 提交不代表 Pi 存取、安裝、
下載、網路切換、Ubuntu benchmark 或 Gate 2 hardware run 已獲准。

## 3. Submitted Initial Manifest

實際 Gate 0 manifest：

`poc_llm/deliveries/POC-llm-DEL-2026-001-R1.md`

Manifest 記錄 repo/branch、環境與 runner 狀態、artifact/evidence 狀態、真實存在路徑、
blockers 及下一個獲准工作；未執行項目只標 `Pending` 或 `Blocked`。規劃中的目錄樹不再
被當成 manifest。

唯一 taxonomy 與 External Gate／Internal Milestone／D1–D8／M4B-P1～P12 crosswalk：

`docs/milestone/m4b_traceability_crosswalk.md`

## 4. Gate 1 Preparation Boundary

Gate 0 登錄後，POC Team 可依序準備：

1. 完成 Internal M0 entry review 與核准的 readiness run。
2. 固定 runtime/model/quantization/config pairing ID、license、source/artifact checksum、
   offline method 與 aarch64 compatibility preflight。
3. 凍結 Ubuntu x86/arm64 packet、metrics、淘汰規則與重跑上限。
4. 執行獲准的 Ubuntu pre-screen，最多提出兩個 Pi finalists。
5. 等待 Core Designer Gate 1 書面確認；在此之前不執行 Gate 2 Pi candidate validation。

## 5. Requested PM Action

請 PM：

1. 拉回約定 branch 並自行記錄實際 branch HEAD。
2. 確認本 receipt、readiness response、Initial Manifest 與其中列出的相對路徑存在。
3. 將 receipt 交 Core Designer 登錄 External Gate 0。
4. 回傳 Gate 0 recording 與 pending `PM-OUT-260817-015`；Gate 1 未經書面確認不得啟動
   Pi 5 Gate 2。
