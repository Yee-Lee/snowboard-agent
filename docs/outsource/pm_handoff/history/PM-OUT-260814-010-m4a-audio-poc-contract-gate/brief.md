# M4a Audio POC Contract / Gate 協調要求

- **Handoff ID** : `PM-OUT-260814-010-m4a-audio-poc-contract-gate`
- **Status** : `Ready for PM`
- **Finding ID** : `OUT-M4A-2026-001`
- **Related handoff** : `PM-OUT-260805-002-m3-m4-poc-planning`
- **Reviewed Core candidate** : branch `dev_agent_m3` , HEAD `fb144bf4b8f530a98189feb5467546c398e96a41`

## 結論

Core目前已定義M4a產品範圍並等待Accepted Audio POC winner，但尚未建立可由PM正式交付Audio POC Team的M4a候選 / fixture / gate contract，也未指定contract owner、發出時點、逐gate ACK與回交路徑。這會形成Core等待winner、POC卻依自身roadmap先排M2 ~ M4的循環。現行M3 Option A P4-A01 ~ A10可依既有contract繼續；Audio POC後續candidate比較與組合驗證在新contract交付前不得視為已授權。

## 必做修訂

### `OUT-M4A-2026-001` —— Blocking —— 缺M4a Audio POC後續contract與gate owner

- Core Designer建立一份PM-ready的M4a Audio POC contract，明列目標、範圍、核准候選、100-item fixture / 資料授權與metric freeze、VAD / ASR / TTS品質門檻、Pi資源與thermal budget、HAL整合、組合 / offline / failure gate、必要evidence、winner / no-go及完整SHA要求。
- 明確區分既有M3條件：P1維持 `FAIL`、P2為 `PASS`、P4為當前Option A implementation gate；P3是M4a候選選型輸出，不得用POC自排roadmap預先視為已授權或已完成。
- 建立逐gate責任與溝通順序：Core contract owner → PM正式轉交Audio POC Team → POC exact-SHA delivery → Core review / ACK；列出每個gate的entry、exit、owner、阻擋範圍與下一動作。
- 在contract交付前，Audio POC repo的M2 ~ M4只可標示 `Proposed` / `Not authorized`；不得把預排工作、口頭結果或branch HEAD當成Core接受的contract或gate evidence。

## 驗收方式

- Core在單一候選commit提交：
  - Contract : `docs/outsource/deliveries/DELIVERY-AUDIO-POC-M4A-CONTRACT-001.md`
  - Response : `docs/outsource/responses/OUT-M4A-2026-001.md`
  - 同步修訂 `docs/milestones/M4.md` 與 `docs/reviews/milestone_progress.md` ，使contract發出時點、owner、PM relay、POC return與Core ACK一致。
- Response列出comparison baseline、完整candidate SHA、architecture-change聲明、逐項修改定位、未決產品門檻需要User / PM決定的項目。
- PM拉回Core repo並通知完整HEAD SHA完成intake後，才把contract package正式轉交Audio POC Team；Audio POC Team以自己的repo完整SHA與manifest回交。

## PM動作

PM只交付本 `brief.md` 給Core Team，不交付同目錄的 `review_notes.md` 。收到Core exact-SHA contract package後，PM再依其內容建立對Audio POC Team的正式交付與receipt；Agent不直接寄送或跨repo代寫。
