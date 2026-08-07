# M1 完成後 Carry-over Feedback

- Handoff ID : `PM-OUT-2026-001-R1`
- Status : `Ready for PM delivery`
- Related Feedback : `CR-M1-II`
- Reviewed commit : `a723b4e0542de8eae0071a91a192104c686152bd`

## 結論

M1 已完成並可進入 M2；下列問題作為 carry-over 必須在後續提交中收斂，不得 regression。請以新 commit 修訂並逐項回覆；外包已修改不等於內部已確認。

## 必做事項

| ID | Priority | Required action | Acceptance |
| --- | --- | --- | --- |
| `CR-M1-II-001` | Blocking | Tester 對修訂後完整 SHA 重跑 M1 entrypoint、full regression 與高風險案例 | repo 內提交 current-SHA 的正式結果，0 Fail / 0 Blocked |
| `CR-M1-II-002` | Blocking | 移除 `/etc/hosts` fixture，改用跨平台暫存檔並真正驗證 config mismatch | Windows / Linux 指定測試與 full suite 通過 |
| `CR-M1-II-003` | Blocking | 移除 Windows pipe 上的 `select.select()`，改用具 timeout 的跨平台 readiness / IPC | Windows / Python 3.11 signal cases 與 full suite 通過 |
| `CR-M1-II-004` | Advisory | 避免 milestone wildcard re-export 導致 full suite 重複收集 | 以穩定 Test ID / 明確 nodes 呈現覆蓋，不以重複 case 數據灌水 |
| `CR-M1-II-005` | Blocking | 統一 developer progress、Tester result 與先前 feedback closure 對照 | revision、31 Test ID、自驗與逐項 closure reference 一致 |

## 回覆方式

- Response : `docs/reviews/outsource/responses/CR-M1-II.md`
- Delivery : `docs/reviews/outsource/deliveries/<new-delivery-id>.md`
- Evidence : `docs/reviews/outsource/evidence/<new-delivery-id>/`
- 請提供完整 commit SHA、每項修改檔案 / 定位、失敗跑 regression node、命令與結果、未完成事項。
