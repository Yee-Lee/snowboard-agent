# Display 團隊修改清單

本文檔是 POC handoff 摘要；正式契約以核心專案 `docs/` 為準。整合方式是「抽取並適配」，不整包合併。

## 元件處置

| POC 元件 | M3 處置 |
| --- | --- |
| Native driver / C ABI | 修正後採用 |
| ctypes HAL / panel profile | 適配核心 `DisplayDevice` 後採用 |
| Pillow renderer / RGB565 converter | 包成 Ch 8 renderer 後採用 |
| elapsed-time 動畫 | 保留為 M7 候選 |
| `Displayservice` `API` `queue` `overlay` `media` `IPC` `video` | M3 不採用 |

## 必要修改

| ID | 修改項目 | 完成條件 |
| --- | --- | --- |
| DSP-01 | 補齊 active native 目錄的 vendor source/header；Makefile 改用 `dev_config_runtime.c` | Pi 5 可由 clean checkout 產生 `.so` |
| DSP-02 | Header 與 driver 統一 `display_open(const DisplayConfig *)`；不得忽略 config | SPI/GPIO 設定確實傳入 driver，錯誤碼一致 |
| DSP-03 | 初始化失敗時釋放已取得的 SPI/GPIO；記錄 vendor 版本與授權 | bad config / missing device 可重複失敗且無資源殘留 |
| DSP-04 | HAL 改為 `start/stop/clear/write_pixels/show/size` | `clear/write_pixels` 只改 back buffer，`show` 才 flush |
| DSP-05 | 移除公開 async `present()` 模型；`present_rect()` 最多保留 backend-private | 公開介面完全符合核心 Ch 2a |
| DSP-06 | 實作 `DisplayRenderer.validate/render` 與六個 Baseline templates | 固定輸入可產生合法、deterministic buffer |
| DSP-07 | Bundle 固定雜線字型；中文與長字串依 pixel width 換行 / 截斷 | 不依主機字型、不溢出畫面 |
| DSP-08 | Runtime render/HAL failure 交由 arbiter latch disabled | 不發布 `ErrorOccurred`、不影響 session / exit code |
| DSP-09 | 修正 pytest option：移至 `conftest.py`；正式測試用 Python 3.11 | mock測試可直接執行，Pi測試有明確 marker |

六個 M3 templates： `status.text` 、 `status.state` 、 `main.text` 、 `main.progress` 、 `fullscreen.text` 、 `fullscreen.blank` 。

## Handoff 必要產出

| 類別 | 產出 |
| --- | --- |
| 硬體 | chip / 面板料號、resolution、orientation、pixel format、接線表 |
| Build | clean build命令、compiler / lgpio版本、`.so` checksum |
| Native | source、Makefile、ABI、vendor revision / license |
| Diagnostic | black / white / RGB / gradient / clear / open-close結果 |
| 效能 | full-frame flush p50 / p95 / max、可用SPI speed、閃爍觀察 |
| 風險 | 未驗證項目、已知限制、需要核心裁定之問題 |

## M3 明確延後

- 獨立 Display process / Unix socket 。
- `set_status/notify/show_alert/play_media` API 。
- Overlay 、 alert preemption 、 fullscreen queue 。
- Animation scheduler 、 frame queue 、 ffmpeg / video 、 touch 、 LED 、 OSD 。
