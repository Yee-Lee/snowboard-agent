# Snowboard maintenance and gate scripts

`scripts/`只放可重跑的產品工具、candidate gate與明確標示的diagnostic。正式acceptance結果仍由
Tester寫入`docs/outsource/evidence/`；Developer工具輸出不得改名為正式PASS。

## Active candidate and M4 tools

| Script | Scope |
| :--- | :--- |
| `candidate_gate.py` | M4+ portable matrix、target preflight、acceptance與debug runner |
| `m4a_audio_product.py` | M4a locked offline build／install／preflight |
| `m4_audio_runtime_closure.py` | M4a runtime wheel closure create／verify |
| `m4a_inheritance.py` | M4a inheritance template／validator；formal output仍由Tester建立 |
| `m4a_target_metrics.py` | M4a target collector的pure parser helpers |
| `m4a_developer_pi_check.py` | Developer-only Pi diagnostic；不是formal acceptance |
| `m4_memory_preflight.py` | M4 composition smoke的bounded memory preflight；不是M4b PASS |

## Hardware diagnostics

| Script | Scope |
| :--- | :--- |
| `hw_diag/hw_diag.py` | Zero-interaction Audio acoustic loopback、Display transaction、Camera signal與GPIO driver/line診斷 |
| `hw_diag/run_diag.sh` | 全自動Pi執行捷徑；零參數時使用repo `.venv`與`config.m3.local.yaml` |
| `hw_diag/run_button.py` | 獨立manual conversation-button測試；不併入automated summary |
| `hw_diag/run_button.sh` | Manual button執行捷徑；零參數時使用repo `.venv`與`config.m3.local.yaml` |

兩個shell捷徑預設使用repo root的`config.m3.local.yaml`，日常操作不需提供參數；只有改用其他
config時才傳入`--config PATH`。`hw_diag.py`的GPIO測項會自動開啟gpiochip、request設定中的
conversation input line，套用edge/debounce後釋放；不要求jumper或按鍵，但也不claim實體pin電位或
按鍵電路PASS。OLED沒有readback，因此只可能claim ABI/SPI transaction，不claim visual panel PASS。

Audio speaker會播放0.5秒440 Hz tone。全自動診斷範例：

```bash
timeout 90s scripts/hw_diag/run_diag.sh
```

`run_diag.sh`不改寫config；未傳`--config`時才注入repo預設檔。`--component`、timeout與output
參數都原樣傳給Python CLI。

只跑特定component可重複傳入`--component`。輸出預設寫到`/tmp/snowboard-hw-diag-*`，包含
sanitized summary、Audio baseline/tone capture及Camera capture；這些是local diagnostic artifacts，
不是formal evidence。

實體conversation button另跑：

```bash
timeout 70s scripts/hw_diag/run_button.sh
```

## M3 history

舊`run_m3_button.sh`與`run_m3_others.sh`含Accepted M3專用evidence path／operator流程，已從current
HEAD移除，immutable `core_m3` tag仍保留原版。`record_m3_observation.py`只為M3 manual observation
schema與既有runbook保留，不得用於M4+ formal acceptance。

## Generated files

`__pycache__/`、`*.pyc`與`.pytest_cache/`皆由`.gitignore`排除，可隨時刪除，不屬交付內容。
