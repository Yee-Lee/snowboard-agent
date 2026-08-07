# M1 測試平台矩陣與交付證據澄清

* **Handoff ID** : `PM-OUT-260806-003-m1-test-platform-scope`
* **Legacy ID** : `PM-OUT-2026-001-R2`
* **Status** : `Ready for PM`
* **Related Feedback** : `CR-M1-II`
* **Related handoff** : `PM-OUT-260805-001-m1-carryover-feedback`
* **Supersedes** : `Windows full-suite / POSIX signal requirement`
* **Intake candidate** : `af890249d8634df11b1a30a27aaee1720f5a8b67`

## 結論

內部確認外包已完成 `/etc/hosts` fixture、Windows pipe readiness 與 wildcard collection 修訂。R1 要求 Windows 也通過 POSIX `SIGINT` / `SIGTERM` 是內部測試範圍過度擴張；本輪正式撤回，不得為此修改 production signal architecture。

本輪只需固定 Windows portable / Linux process 測試矩陣，並補交被測 implementation SHA 的 Linux 結果、正式 response / delivery / evidence。

## 必須回覆確認的共識

外包收到本 handoff 後，須在 repo response 開頭明確確認：

1. Windows 平台只要要求 portable 純 Python / mock / config 與適用的 subprocess tests。
2. Windows 專屬或不適用的 POSIX `SIGINT` / `SIGTERM` 驗證不再要求。
3. 不會為了 Windows POSIX signal 測試修改 production signal architecture。
4. Linux / Raspberry Pi 仍是 POSIX process signal、native lifecycle 與正式 runtime 的權威平台。

只有上述確認已 commit 在指定 response 路徑，才視為雙方測試範圍共識完成。

## 必做事項

| ID | Priority | Required action | Acceptance |
| --- | --- | --- | --- |
| `CR-M1-II-001` | Blocking | 依新矩陣提交被測 implementation SHA 的正式結果 | Windows portable suite 0 Fail；Linux / Python 3.11 M1 entrypoint、full suite及 POSIX signal cases 0 Fail；logs 已 commit |
| `CR-M1-II-003` | High / scope correction | 先逐項確認新平台共識，再將 portable 與 Linux process 測項分流；不得新增 Windows POSIX signal 產品支援 | Response 開頭逐項確認四點共識；`docs/test_spec.md` 拆分 portable / Linux process 平台；M1 test spec、milestone、pytest marker與 signal nodes一致 |
| `CR-M1-II-005` | High | 修正 response / delivery 的被測 SHA 與 evidence 索引 | 正式檔案位於 `docs/outsource/`；逐項引用一致且能定位 committed logs |
| `CR-M1-II-004` | Advisory | 保留已完成的 wildcard removal；說明 nested pytest 是否延後最佳化 | 不以 collection / 執行次數當額外 coverage；此項不阻擋產品 code completeness |

`CR-M1-II-002` 已由內部在 Windows / Python 3.11 驗證 `16 passed`，不要求額外產品修訂。

## 測試平台決策

* **Windows** : Python 3.11+ 純 Python、mock、config 與 portable subprocess tests；明確 deselect Linux process signal nodes。
* **Linux / Raspberry Pi** : POSIX `SIGINT` / `SIGTERM`、native lifecycle 與正式產品執行的權威平台。
* **Architecture change** : `No` 。除非 Linux 測試發現真正產品問題，否則本輪只修訂 tests / test docs / delivery evidence。

## 回覆方式

* **Response** : `docs/outsource/responses/CR-M1-II.md`
* **Delivery** : `docs/outsource/deliveries/<new-delivery-id>.md`
* **Evidence** : `docs/outsource/evidence/<new-delivery-id>/`
* Response / delivery 請列被測 implementation SHA、comparison baseline、平台、命令、結果、架構變更聲明與未完成事項；PM 拉回後另通知 repo HEAD 完整 SHA。
