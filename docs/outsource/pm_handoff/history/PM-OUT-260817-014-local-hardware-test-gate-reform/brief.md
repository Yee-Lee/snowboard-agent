# 本機 / 實體測試順序與候選 Gate 改善要求

- **Handoff ID** : `PM-OUT-260817-014-local-hardware-test-gate-reform`
- **Status** : `Ready for PM`
- **Finding ID** : `OUT-PROCESS-2026-001`
- **Reviewed Core candidate** : branch `dev_agent_m3`, HEAD `c559e5cf65d20676696293f06f1e5bc2afd02ae6`

## 結論

本輪M3把async / state-machine / event schema除錯帶入Pi互動測試，並在portable版本矩陣與candidate尚未完全收斂前產生20-card evidence；後續任何 `src/` / `tests/` 修正都改變exact SHA，造成全盤重錄。Core須將「開發除錯 run」與「正式 acceptance run」分開，建立portable-first、candidate freeze、單一Pi runtime與不可混用evidence的gate。

Python 3.11 / 3.12 / 3.13 portable matrix應保留：本輪Python 3.12確實在抓到Pi 3.13未暴露的executor hang，而portable suite成本遠低於人工硬體重測。三版本不應乘到Pi實體測試；Pi只在產品正式部署runtime執行一次exact-SHA acceptance。

本handoff只改善後續開發流程，不重開已完成的M3、不要求重跑M3 20-card硬體驗證；流程以無硬體dry run驗證，並自下一個產品候選開始強制生效。

## 必做修訂

### `OUT-PROCESS-2026-001` — High — 缺少portable-first與candidate freeze gate

- 建立並文件化以下不可跳過順序：
  i. 契約 / Test ID / 事件schema檢查與靜態型別檢查。
  ii. Developer fast loop：單一主要Python執行受影響unit / integration tests。
  iii. Candidate portable gate：Python 3.11、3.12、3.13全部執行規定suite；每個async / process測試有bounded timeout，結果須為0 Fail / Blocked / Skip / XFail。
  iv. Code/Test review完成，凍結單一40-character candidate SHA；其後 `src/`、`tests/`、dependency、config contract或runner identity變更即撤銷freeze並回到portable gate。
  v. Pi preflight只驗candidate、乾淨worktree、target runtime、hardware / artifact / config identity與runner readiness，不先寫正式PASS evidence。
  vi. Pi acceptance對凍結SHA執行一次完整RPI-NATIVE gate，再由Tester核對portable matrix、Pi evidence及單一SHA一致性。
- 將硬體debug與acceptance分流：debug run可針對單卡反覆執行但不得覆寫正式bundle；acceptance run使用新且不可混用的run ID。任何中途失敗都保存FAIL evidence、停止封包、修正後以新SHA / 新run重新開始。
- 狀態機、EventBus、async cancellation、GPIO edge sequence及manual readiness先以fake / simulated fixture在portable gate驗證；Pi只保留真實kernel、device ownership、latency、thermal、signal與人工可聽 / 可視結果。
- runner必須接收外部指定candidate SHA並拒絕不符，不得自行以目前HEAD授權自己；以明確readiness handshake取代固定 `sleep`，人工觀察缺失或record command失敗必須使該card FAIL。
- evidence須記錄run ID、完整SHA、branch、dirty check、命令、平台、Python、config / artifact checksum、開始 / 結束、exit code與原始log；README、manifest、cards、results不得混用SHA或舊run。

## Python版本成本與支援政策

- Core須明列正式支援的Python minor版本，不得只用無上限的 `>=3.11` 卻只測單一版本。
- 後續候選建議以3.11（最低契約）、3.12（中間相容與本輪實際失敗版本）、3.13（目前Pi runtime）作portable candidate matrix。
- 不要求每位Developer或每台開發機同時安裝三個版本；三版本能力可由CI、容器或集中候選驗證環境提供，Developer本機只需團隊指定的主要版本。
- 日常fast loop可只跑主要開發版本；三版本矩陣只在候選freeze前、影響async / native adapter / dependency時及正式合併gate執行。若CI時間可接受，所有merge維持三版本是較安全且低成本的保險。
- Pi / 人工硬體只跑正式部署runtime，不要求3.11 / 3.12 / 3.13各跑一輪；若部署runtime改變，才重新觸發對應Pi gate。
- dependency lock / native ABI須按portable與Pi runtime分別記錄，避免把Python語意相容與硬體相容混成同一矩陣。

## 驗收方式

Core在單一候選commit提交：

- **Response** : `docs/outsource/responses/OUT-PROCESS-2026-001.md`
- **同步修訂權威workflow / test strategy、後續milestone runbook及必要CI設定**，明列每個gate的owner、entry、exit、失敗回退與evidence path；不得為此回溯修改M3 acceptance結論。
- **提供一次不接硬體的dry run**，證明SHA不符、dirty受測檔案、缺少Python matrix結果、timeout、manual observation缺失及混用run ID都能產生明確FAIL並阻止未來Pi acceptance；本項不要求執行M3硬體測試。

Response須列comparison baseline、完整candidate SHA、architecture-change聲明、逐項修改定位、預估CI時間、Pi人工時間及已接受的成本取捨。不得以流程文字取代可執行gate或failure demonstration。

Core可自行決定是否另於 `docs/outsource/deliveries/` 發布獨立workflow文件；這不是本finding的必要交付。若另發，response只引用其路徑與用途，權威流程仍以既有workflow / test strategy、runbook及CI設定為準。

## PM動作

PM只交付本 `brief.md` 給Core Team，不交付同目錄 `review_notes.md`。收到Core完整HEAD SHA後由Designer intake，必要時交Engineering Reviewer / Tester以無硬體dry run確認gate可失敗性；不得因本handoff要求重跑已完成的M3硬體驗證。
