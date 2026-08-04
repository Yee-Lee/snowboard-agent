# 核心 Designer 修改清單

M3 維持既有 `DisplayDevice -> DisplayRenderer -> DisplayArbiter -> owners` 架構；Designer負責規格與milestone，不寫產品程式或正式測試結果。

## 是否需要 Architect

| 決定 | 處置 |
| --- | --- |
| SSD1351 OLED + 現行同步 Ch 8 ownership | 不需改 `arch.md` |
| ST7789 LCD 取代主要 OLED | 交 Architect |
| 獨立 process / IPC、async frame service、專用 I/O thread改公開契約 | 交 Architect |
| Overlay、preemption、fullscreen queue、新Display角色 | 交 Architect |

需交 Architect 時，由 Designer 建立 `docs/reviews/arch_review_impl_II.md` ；裁定前不改 implement 契約。

## Designer 文件修改

| ID | 文件 | 必要修改 |
| --- | --- | --- |
| DES-01 | `implement/ch02a_core_hal.md` | 固定chip backend、HAL/native映射、resolution、pixel format、byte order、rotation、buffer驗證與build規則 |
| DES-02 | `implement/ch05_resource_manager.md` | 定義device->renderer->arbiter->owners資源圖、resource key、phase、NullDisplay fallback與reverse stop |
| DES-03 | `implement/ch08_display_arbiter.md` | 補實際注入關係、Baseline renderer factory、startup/shutdown owner與failure latch；四動作不變 |
| DES-04 | `implement/ch10_config.md` | 定義strict driver / 尺寸 / 格式 / rotation / SPI / GPIO schema及cross validation |
| DES-05 | `display_spec.md` | 固定resolution、三區域、字型、字級、換行 / 截斷、progress及靜態開關機畫面 |
| DES-06 | `milestone.md` | M3加入selected profile、clean native build、real->null、atomic flush、Baseline與Pi驗收；明列POC進階功能排除 |
| DES-07 | `reviews/impl_progress.md` | 受影響章節改回草稿，記錄跨章gate；review確認後恢復定稿 |
| DES-08 | `reviews/milestone_progress.md` | 維護M3 gate、阻擋、owner、下一動作與定案狀態 |

`DisplayConfig` 至少需決定： `driver` 、 `width / height` 、 `pixel format` 、 `rotation` 、 `SPI bus / chip / speed / mode` 、 `GPIO chip` 、 `DC / RST / BL`及manual CS ownership。產品設定走 `config.local.yaml` ，不沿用任意 `DISPLAY_*` 環境變數。

## Milestone 規劃

- 不新增M3a / M3b；保留單一M3。
- 以下為Developer工作包，寫入 `development_progress.md` ，不進入 `milestone.md` ：
  i. Native / HAL 。
  ii. Baseline renderer / arbiter 。
  iii. RM / lifecycle / owner接線。
  iv. Pi hardware驗證與Tester handoff。
- 星空、fade、chat、video、scheduler、overlay、IPC仍屬M7或另案。

## 文件 Owner 邊界

| 文件 / 範圍 | Owner | Designer動作 |
| --- | --- | --- |
| `arch.md` | Architect | 提finding，不直接改架構 |
| `test_spec.md` 、 `test_progress.md` | Tester | 確認需求可驗證，讀取正式結果 |
| `development_progress.md` 、 `src/` 、 `tests/` | Developer | 審核估點 / 範圍，不代寫 |
| `implement` 、 `Display profile` 、 `milestone` 、 `dashboard` | Designer | 修訂並完成review / gate |

## 完成順序

1. 使用者固定硬體；Designer判定是否需Architect。
2. 修訂Ch 2a / 5 / 8 / 10與 `display_spec.md` ，完成Reviewer確認。
3. 同步 `milestone.md` ；Tester完成M3 test spec。
4. Developer完成估點 / 工作包；Designer核對後送使用者批准M3。
5. 所有gate通過後，dashboard才標示M3「已定案」。
