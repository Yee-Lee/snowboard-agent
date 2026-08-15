# Core Team Response: CR-AUDIO-M3-P4-REPRO-002 Decision

- **Response ID**: `RESP-AUDIO-M3-P4-REPRO-002`
- **Parent Request**: `CR-AUDIO-M3-P4-REPRO-002`
- **Requester / Decision Owner**: Core Team Designer
- **Date**: 2026-08-15
- **Status**: `RESOLVED — OPTION 2 ACCEPTED`

## 1. Decision

Core Designer 接受採用 **Option 2**：核准修正後的 artifact hashes，並要求全新 Pi build 與 A10 rerun。

基於 Core Team 處理 Python 環境的經驗，編譯期工具（如 `packaging`、`setuptools` 等）的 source distributions 或是 wheels 若未嚴格 vendor，很容易因為 PyPI 上的套件更新或被替換而導致 hashes 改變，這並不代表所選的 candidate 方案不穩定。既然目前已經無法取得與 manifest 完全相符的 retained artifacts（排除 Option 1），且重新尋找替代方案（Option 3）成本過高且無絕對必要，因此我們決定：

1. 核准使用更新後、正確的 artifact hashes。
2. POC Audio Team 必須針對這些新 hashes 進行基本的 provenance 與 license 審查，確保其為安全合法的釋出。
3. POC Audio Team 必須使用這些核准的 hashes 進行一次全新的 clean Pi build 並重跑 A10 驗證。
4. 在 A10 重新驗證通過並提供相應 evidence 之前，Core Designer 不會發出 P4 的 final selection ACK。

請 POC 團隊依據此決定繼續進行，並回交驗證結果。
