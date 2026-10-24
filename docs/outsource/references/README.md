# docs/outsource/references/

此目錄存放外部技術輸入的**可重現定位資訊**。POC source、tests、harness、evidence snapshot與binary留在各自repository，不複製進Core Git。

## 目錄說明

| 目錄 | 內容 |
|---|---|
| `poc_audio/` | Audio POC repository URL、exact SHA、authority path與取得指令 |
| `poc_display/` | Display POC repository URL、exact SHA、authority path與取得指令 |
| `poc_llm/` | LLM POC repository URL、exact SHA、authority path與取得指令 |

## 使用原則

- 不放PM handoff（見`pm_handoff/`），也不vendor外部repository的tracked tree。
- 每筆定位資訊至少包含canonical Git URL、完整40-character SHA、authority path、版本／狀態與取得後的SHA驗證方式；branch HEAD、tag或口頭版本不能作為baseline。
- Developer需要參考時，以`mktemp -d`在OS temporary directory clone，detached checkout exact SHA；不得clone至Core tree、不得複製POC source / test / binary回Core reference。
- Private repository access是Developer執行環境的read-only prerequisite；Core不保存credential、token、SSH config或持久local clone。
- `.so`、wheel及target build output不進Git；只在ACK / manifest記錄source SHA、artifact checksum、license、build command與target runtime identity。
- Core採用決定記錄於`deliveries/` ACK；外部內容更新時只更新locator與ACK，不在Core修改或重新發布原文。
