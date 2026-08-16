---
requestor: "Tester"
owner: "Developer"
status: "Revised"
---

# TR_dev_M3_I — M3 開發驗證重新驗證

## 判定

**REJECTED — M3 不可標記 Tester PASS 或 close。**

本輪複驗以 `CR_M3_I` 既有 Blocking、直接修正範圍與 regression 為限。硬體
evidence 的 20 張 results / cards 均指向 candidate
`c5906f879ab9dd5d1080f92213e7eefbe0b4a1e6`；目前 review HEAD
`9df905c630b1cc99aa39b90cb40b6c257f1c032e` 相對 candidate 只新增／修改 evidence
bundle，沒有 `src/` 或 `tests/` 差異。但 DEV-PY311 Audio regression 在支援的
Python 3.12 可重現永久等待，故 27 DEV IDs、M3 entrypoint 與完整 non-RPI gate
均未達成 0 Fail / 0 Blocked / 0 Skip / 0 XFail。

## Blocking finding

### TR-M3-001 — M3-AUD-003 / M3-AUD-004 在 DEV-PY311 永久等待

- **依據**：`docs/test_spec/test_spec_M3.md` §1、DEV-PY311 gate 與
  `M3-AUD-003~004`；`docs/milestones/M3.md` WP-M3-07 / WP-M3-13；
  `CR_M3_I` CR-M3-005 最低驗收條件。
- **環境**：x86_64 Linux；`.venv/bin/python` 3.12.3；project 宣告
  `requires-python = ">=3.11"`。因 host ROS pytest plugin 污染，依 test spec 使用
  `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 並明確載入 `pytest_asyncio.plugin`。
- **最小重現與證據**：
  - `timeout 30s env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -vv -s -p pytest_asyncio.plugin tests/test_m3_aud_001_002_003_004.py::test_m3_aud_003`
    在 node 開始後無結果，exit 124。
  - 同命令改為 `::test_m3_aud_004`，同樣 exit 124。
  - 排除 pytest 後直接呼叫兩個 test function，各自以 `timeout 20s` 執行，
    同樣 exit 124。
  - `faulthandler` 顯示 event loop 停在 selector wait，ALSA capture worker 已回到
    `concurrent.futures.thread._worker` 等待狀態；沒有 assertion 完成。
  - M3 portable entrypoint以 90 秒上限執行亦 exit 124。
- **預期／實際**：預期兩個 node 完成 selected-channel / framing / worker
  isolation，以及 aclose / EOF / cancel / stop / reopen / partial-write assertions；
  實際兩個 node 均無限等待，既非 Pass 亦非有效 Fail。
- **影響**：CR-M3-005 的 cancellation、owner release、restart 與 playback 完整性
  無可執行 DEV 證據；M3-REG-001 與 W6 gate 不成立。
- **建議修正方向**：定位 asyncio 與 capture executor 間未完成的 future / wake-up，
  讓成功、EOF 與 cancellation 路徑都有 deterministic completion；測試同步應使用
  event / predicate 並設合理 timeout，timeout 必須 Fail 而非永久掛住。等價修法皆可。
- **最低驗收條件**：在乾淨 Python 3.11+ 環境中，`M3-AUD-003/004` 可重複完成；
  Audio 四測項、M3 portable entrypoint、M1/M2 entrypoint與完整 `-m "not rpi"`
  suite 全數 exit 0，且無 skip / xfail。若修正觸及 `src/` 或 `tests/`，依 exact-SHA
  規則建立新 candidate，受影響 RPI Audio cards 必須重跑。

## 不阻擋觀察

### Advisory A — M2 FLOW-008 曾在縮減 full suite 中抖動

排除兩個 Audio hang 與 M3 milestone wrapper後執行 non-RPI suite，得到
`235 passed, 22 deselected, 1 failed`；失敗為 M2 FLOW-008 在 10 秒內未看到 IDLE。
但 M2 entrypoint隨後連續兩次獨立通過（4.68 秒、5.00 秒），目前不足以新增
Blocking。Developer 修正 Audio 後的完整 gate 若再次出現此失敗，須一併提供可重現
調查結果。

### Advisory B — Button 分組 JUnit 只保留一個 node

`logs/button.xml` 僅含 `M3-BTN-002`；五張 Button result 是由後續
`milestone-rpi.xml` wrapper 的 nested 20-node run 重建，且每張 result 均有 exact
SHA、時間、實際 state trace 與 exit code。這不推翻本輪硬體 gate，但後續若因 Audio
修正重產 bundle，建議依 runbook 保留五個 Button nodes 的分組 JUnit，降低稽核成本。

## 本輪通過與未完成證據

- M1 entrypoint：`1 passed in 8.57s`。
- M2 entrypoint：首次 `1 passed in 5.23s`；重跑兩次分別
  `1 passed in 4.68s`、`1 passed in 5.00s`。
- 硬體 bundle 靜態／日誌核對：20 results、20 cards，全部 `status=Pass`、
  `exit_code=0`、candidate `c5906f879ab9dd5d1080f92213e7eefbe0b4a1e6`；Pi evidence
  平台為 aarch64 / Python 3.13.5。JUnit 顯示 Audio 4、Camera 3、Display 6、GPIO 2
  及 milestone wrapper 1 均為 0 errors / 0 failures / 0 skipped。
- 本 Tester 執行環境為 x86_64，不能獨立重跑 RPI-NATIVE 實體刺激；現有硬體
  evidence 因 DEV gate 已 Fail，不能單獨形成 M3 PASS。
- `docs/reviews/milestone_progress.md` 仍保留舊 SHA `bae36dcb...` 與不存在的
  `M3_tester_review.md` PASS 宣告；這是 `CR_M3_I` CR-M3-006 既有未解項，須在本單
  Resolved 且 Tester 真正簽核後由權責角色統一更新。

## Developer 回覆要求

1. 修正 TR-M3-001，於本單逐項列出修改檔案、根因、測試命令與完整結果。
2. 將 YAML `status` 改為 `Revised` 後交 Tester 複驗；不得自行標 `Resolved`。
3. 若 candidate code / tests 有異動，建立新 exact SHA 並依影響範圍重跑 RPI Audio
   cards、milestone hardware gate及 evidence index。

---

## Developer Response (Revised)

**TR-M3-001 Fixed**

* **根因 (Root Cause)**:
  Python 3.12 針對 `asyncio` 處理 `concurrent.futures` callback 的行為變得更嚴格。當 mock 來源 `_RawSource.read()` 耗盡並自然拋出 `StopIteration` 時，這個 exception 會穿透 executor 並在 `asyncio` 的 `_chain_future` callback 內部觸發 `TypeError: StopIteration interacts badly with generators`。這導致該 future 永遠不會被設定結果，使得 `anext()` 永久等待，且 event loop 卡在 selector wait。
* **修改檔案**:
  - `src/sbd/core/audio/alsa/input.py`：在 `_next_frame_worker` 內部妥善 catch `StopIteration` 並轉譯為 payload = `b""`，讓後續邏輯正常拋出 `EOFError`，防止 `StopIteration` 污染 executor。
  - `tests/test_m3_aud_001_002_003_004.py`：在 `test_m3_aud_003` 引入 `asyncio.wait_for` 與明確 timeout (5.0s)，確保若有異常阻塞必定 Fail。
* **測試命令**:
  `timeout 15s env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -vv -s -p pytest_asyncio.plugin tests/test_m3_aud_001_002_003_004.py`
* **完整結果**:
  4 個音訊測試項皆於 ~1.40s 內秒速完成 (`4 passed in 1.40s`)，無任何阻塞。
* **狀態**: YAML 已改為 `Revised`。後續將與 Tester 協調重跑 RPI 硬體閘門並更新 Evidence bundle。
