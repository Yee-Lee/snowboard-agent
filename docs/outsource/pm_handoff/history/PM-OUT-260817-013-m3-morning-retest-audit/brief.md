# M3 2026-08-17 早晨重測過程與修正證據要求

- **Handoff ID** : `PM-OUT-260817-013-m3-morning-retest-audit`
- **Status** : `Ready for PM`
- **Finding ID** : `OUT-M3-AUDIT-2026-001`
- **Related delivery** : `DELIVERY-M3-HARDWARE-VALIDATION-001`
- **Reviewed Core range** : `a9a1ed47b50ce62ce5275009373692da41f99754..c559e5cf65d20676696293f06f1e5bc2afd02ae6`

## 結論

2026-08-17早晨在修正Python 3.12 Audio hang後，Core又提交 `c545de6ff389b56596fb7c2bb04bc3636a5863d9` 處理 pinctrl-rp1 zero-debounce，隨後新增執行腳本並對 `cab627705c341d0058e0c395e96d0be10c4c4239` 重錄20張Pi卡。修正後重測本身合理，但repo目前沒有保存 `c545de6...` 的原始失敗、觸發路徑或Test ID；既有Button使用50ms、GPIO loopback至少20ms，無法由已提交資料說明為何zero-debounce修正是本次重測所需。

本finding不預設修正錯誤；要求Core以已提交證據還原時序、失敗、決策與重測範圍，使產品團隊能判斷修正必要性及資源使用是否合理。在說明完成前，`c559e5c...` 維持候選，不因20/20自驗自動成為Accepted。

## 必做回覆

### `OUT-M3-AUDIT-2026-001` — High — 早晨重測與zero-debounce修正缺少可稽核因果

- 依台北時間列出 `a9a1ed4...` 完成後至 `c559e5c...` 提交前的實際步驟：checkout / candidate SHA、執行命令、平台與Python版本、每次PASS / FAIL / 中止、修正決策、重跑範圍及產物。
- 對 `c545de6...` 提供原始失敗證據：完整命令、Test ID或產品路徑、exception / kernel / libgpiod訊息、當時HEAD與worktree狀態、config checksum，以及哪一個呼叫實際使用 `debounce_ms=0`。
- 說明相同config checksum下，先前 `c5906f8...` 的Button 50ms / GPIO至少20ms evidence為何可通過，而早晨仍需要zero-debounce修正；若屬20-card以外路徑，明確標示來源與產品影響。
- 說明 `c545de6...` 為必要產品修正、測試工具修正、defensive change或非阻擋改善；列出受影響與不受影響的M3 Test ID，以及為何選擇在candidate重錄前納入。
- 補一個不依賴Pi人工操作、可在portable / fake-gpiod環境失敗的regression，驗證 `debounce_ms=0` 不向 `LineSettings` 傳入 `debounce_period`，正值仍原樣傳遞；若無法建立，說明限制與替代認證。
- 說明第一次bundle的 `button.xml` 為何只有 `M3-BTN-002`，以及早晨新增runner後如何保證五個Button node、人工觀察與20-card manifest不被部分覆寫或混用。
- 對齊evidence README、manifest、results與cards：目前README仍寫 `c5906f8...`，其餘資料指向 `cab627...`；所有正式聲明須使用完整40-character SHA。

## 驗收方式

Core在單一候選commit提交：

- **Response** : `docs/outsource/responses/OUT-M3-AUDIT-2026-001.md`
- **原始或去敏後證據** : `docs/outsource/evidence/DELIVERY-M3-HARDWARE-VALIDATION-001/retest-audit-20260817/`
- **regression test及必要的evidence README修訂**。

Response須包含完整audit timeline、comparison baseline、branch、完整response HEAD、被測implementation SHA、架構是否變更、dependency / config是否變更、已知限制，並逐項定位修改與證據。若原始失敗log已不存在，須明確聲明，不得以推測重建當時證據，並提供現可重現結果或不可重現原因。

Core可自行決定是否另於 `docs/outsource/deliveries/` 發布獨立audit文件；這不是本finding的必要交付。若另發，response只引用其路徑與用途，不重複內容。

## PM動作

PM只交付本 `brief.md` 給Core Team，不交付同目錄 `review_notes.md`。收到回覆後拉回repo，以branch與完整HEAD SHA通知Designer intake；需要深入code / test確認時再交Engineering Reviewer。Agent不直接寄送、上傳或修改Core repo。
