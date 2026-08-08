# docs/outsource/references/

此目錄存放**外部團隊提供給 Core Team 的技術參考文件**，包含 POC 團隊的 contract、spec draft 與設計輸入。

## 目錄說明

| 目錄 | 內容 |
|---|---|
| `poc_audio/` | Audio POC 團隊提供的 contract、capability matrix、fixture spec |
| `poc_display/` | Display POC 團隊提供的 contract、display spec draft |
| `poc_llm/` | LLM POC 團隊提供的 contract、model spec draft |

## 使用原則

- 此目錄只放**外部團隊主動交付給 Core Team 的文件**，不放 PM handoff（見 `pm_handoff/`）。
- 文件版本以**檔名或文件內 header 標明版本號**（如 `v0.1 DRAFT`、`v1.0 Accepted`）。
- 當外部團隊更新正式版時，直接在對應目錄**新增或覆蓋**版本檔案，並在 commit message 標明來源與版本。
- Core Team 採用決定記錄於 `deliveries/` 的 ACK 文件；不在本目錄內修改外部提供的原始內容。
