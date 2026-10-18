# PROPOSAL-PI-WORKSPACE-CLEANUP-001: Raspberry Pi 歷史暫時工作目錄清理提案與完成回覆

- **ID**: `PROPOSAL-PI-WORKSPACE-CLEANUP-001`
- **Owner**: Designer
- **Status**: Completed — Pi retains only the current installed App under `/home/<operator>` (2026-10-18)
- **Target Environment**: `<operator>@<pi-host>` (`/home/<operator>`, `/home/<operator>/snowboard-app/releases`, `/var/tmp`)
- **Requested Action**: 已依 USER 後續指示把 Pi 縮至現行 App 所需內容；實際保留與清理結果見 §6，§3–§5 記錄先前決策過程
- **Authoritative Input**: `docs/status/development.md`（ALPHA delivery `8b4af53f433c4bcdb5b858973e10767318986554` 保留證據 locators）
- **Date**: 2026-10-18

---

## 1. 背景與問題陳述 (Background & Problem Statement)

1. **磁碟空間現況**：
   - `<operator>@<pi-host>` 根分割區 `/dev/mmcblk0p2` 總容量 `59G`，目前已使用 `40G`（`72%`），剩餘 `17G`。
   - `/home/<operator>/` 底下累積了 M4B、M4C、M4-ERR 與 ALPHA 迭代期間留下的 **約 130 個過渡開發工作樹與單次測試目錄**，另有 `~/snowboard-app/releases/` 內的 12 個舊版安裝 release。
2. **清理目標**：
   - 在進入下一階段（`M6pre → M5 → M6E`）目標機開發與驗證前，釋放 **約 10.6 GB – 14.0 GB** 的過渡空間。
   - 確保已由 USER 接受的 ALPHA 最終交付（`8b4af53f433c4bcdb5b858973e10767318986554`）、現行正式安裝入口（`~/snowboard-app/run.sh`）及 `docs/status/development.md` 直接引用的最終證據 locators 完整保留、不受影響。

---

## 2. 相依性與安全性盤點結果 (Dependency & Safety Audit)

已在 `<operator>@<pi-host>` 完成唯讀盤點，確認以下事實：

1. **正式安裝環境完全自包含**：
   - `/home/<operator>/snowboard-app/current` 指向 `/home/<operator>/snowboard-app/releases/asr-notice-20261017-r11`（3.4 GB）。
   - `current/config.local.yaml` 與頂層 `config.local.yaml` 引用的所有模型、worker、runtime python 與 native library 皆位於：
     - `/home/<operator>/snowboard-app/` 內部（`releases/asr-notice-20261017-r11/` 或頂層 `artifacts/`、`runtimes/`、`native/`、`requirements/`）
     - `/var/lib/snowboard/products/m4a/audio_m4-5694ead4-v2/`（系統層級 M4A ASR/VAD/TTS 資產）
   - `~/snowboard-app` 內無任何 symlink 指向 `/home/<operator>/m4b-*`、`~/snowboard-agent-dev` 或其他家目錄下的暫存工作區（`.venv/bin/python3` 直接指向 `/usr/bin/python3`）。

---

## 3. 原保留清單（清理前判斷；後由 USER 的最小 App 範圍取代）

### 3.1 正式安裝與系統模型資產
- `/var/lib/snowboard/products/m4a/`（全部保留）
- `/home/<operator>/snowboard-app/` 頂層與現行生效版本：
  - `run.sh`、`config.local.yaml`、`current` symlink
  - `releases/asr-notice-20261017-r11/`（**3.4 GB**，目前 `current` 指向的正式交付版本）
  - 頂層共用目錄：`artifacts/`（**3.2 GB**）、`runtimes/`（**145 MB**）、`src/`（**14 MB**）、`.venv/`（**8.0 MB**）、`logs/`、`requirements/`、`native/`、`config/`、`scripts/`

### 3.2 ALPHA 最終交付與 `docs/status/development.md` 直接引用之證據目錄（合計約 51 MB）
- `/home/<operator>/alpha-delivery-20261018-r11`（**228 KB**：最終 portable、lifecycle、recovery、`quality-02` 驗收證據）
- `/home/<operator>/asr-notice-20261017-r11`（**19 MB**：最終 r11 工作樹、`promotion-byte-comparison.json`、`installed-entry-acoustic-02`、`installed-native-notice-02`）
- `/home/<operator>/snowboard-debug`（**6.7 MB**：實機操作紀錄 `manual-26mvrheg`、`manual-9510k6gj`、`manual-zvfo51jx`、`manual-j2sg_ujx`、`manual-hhg6svjf` 等）
- `/home/<operator>/app-acoustic-20261012-r4`（**22 MB**：`development.md` 引用之 `paired-01` 雙輪效能基準）
- `development.md`「Retained failures and limitations」具名引用的 7 個小型診斷目錄（合計 **< 3 MB**）：
  - `/home/<operator>/debug-asr-failure-20261017`（72 KB）
  - `/home/<operator>/debug-asr-full-capture-20261017`（100 KB）
  - `/home/<operator>/debug-asr-level-20261017`（96 KB）
  - `/home/<operator>/app-selfplay-session-20261017-h4ibdxcl`（868 KB）
  - `/home/<operator>/app-selfplay-session-20261017-shhn3gu8`（1.1 MB）
  - `/home/<operator>/asr-recovery-acoustic-20261017-01`（412 KB）
  - `/home/<operator>/debug-fixed-entry-smoke-7ag85ymp`（12 KB）

### 3.3 使用者與系統環境隱藏檔
- `/home/<operator>/.ssh`、`~/.config`、`~/.local`、`~/.cache`、`~/.bashrc`、`~/.profile`、`~/.bash_logout`、`~/.bash_history`、`~/.gitconfig`、`~/.vim*`、`~/.vscode`、`~/.theia` 等全部保留。

---

## 4. 建議刪除清單 (Proposed Deletion Scope)

以下為原始候選清單，**不是已可直接執行的刪除清單**。其中部分目錄仍含現行文件引用的
私有證據；§5 的保存、locator 更新與逐項核對完成前，不得刪除那些目錄。實際釋放量以
最後逐項確認的內容為準，不以 §1 估算作為清理成功條件。

### 4.1 `~/snowboard-app/releases/` 下的歷史過渡版本
1. **候選清理（11 個過渡目錄 + 1 個舊腳本，合計約 150 MB）**：
   - `/home/<operator>/snowboard-app/releases/prefetch-20261011-r9`（14 MB）
   - `/home/<operator>/snowboard-app/releases/prefetch-20261011-r10`（14 MB）
   - `/home/<operator>/snowboard-app/releases/prefetch-20261011-r11`（14 MB）
   - `/home/<operator>/snowboard-app/releases/pnph-observation-20261011-r1`（14 MB）
   - `/home/<operator>/snowboard-app/releases/pnph-observation-20261011-r2`（14 MB）
   - `/home/<operator>/snowboard-app/releases/pnph-observation-20261011-r3`（14 MB）
   - `/home/<operator>/snowboard-app/releases/native-observation-20261011-r4`（14 MB）
   - `/home/<operator>/snowboard-app/releases/cold-observation-20261011-r6`（13 MB）
   - `/home/<operator>/snowboard-app/releases/focus-observation-20261011-r7`（14 MB）
   - `/home/<operator>/snowboard-app/releases/cache-diagnostic-20261011-r8`（14 MB）
   - `/home/<operator>/snowboard-app/releases/interrupt-fix-20261009`（14 MB）
   - `/home/<operator>/snowboard-app/releases/original-entry-20261009.sh`（4 KB）
2. **`releases/debug-20261017-r9`（3.4 GB）：當時採 A1 保留，後續 USER 明確核准刪除**：
   - `docs/status/development.md` 第 11 行記載：`Formal run.sh and run.sh --debug now select asr-notice-20261017-r11; previous r9 is retained.`
   - 原交付紀錄明確說明 previous r9 is retained；這是當時的保留判斷。USER 後續改定
     Pi 只保留目前可啟動 App 的最小內容，並明確核准刪除 r9；最終結果見 §6。

### 4.2 `/home/<operator>/` 下的歷史開發工作樹與過渡測試目錄（原估約 10.45 GB）

`docs/status/development.md` 與 `docs/milestones/ALPHA.md` 仍引用本節部分目錄，尤其
`alpha-prefetch-r11-20261011` 的 PH 失敗記錄、`alpha-live-20261009-VkWLZT` 的真人操作 log，
以及早期 ALPHA 診斷／測試結果。保留證據不限於 §3.2 的最終交付目錄；刪除前須先依
§5 逐個查出引用、保存所需檔案並更新 locator。程式 checkout、venv、模型與 runtime 不因
位於被引用目錄就必須整棵複製；其必要的輸入、結果、log 與失敗觀察則須可追溯。
1. **大型過渡目錄（約 8.6 GB）**：
   - `/home/<operator>/m4b-target-20260913-sLrXyC`（**3.4 GB**）
   - `/home/<operator>/app-acoustic-20261012-r3`（**3.4 GB**）
   - `/home/<operator>/snowboard-agent-dev`（**1.8 GB**，9 月份舊 POC／M4B 工作區，HEAD `9950477`）
2. **其餘 `app-acoustic-*` 過渡目錄（排除 `r4`，列名 7 個目錄，原估約 160 MB）**：
   - `/home/<operator>/app-acoustic-20261012-r{1,2,5}`
   - `/home/<operator>/app-acoustic-20261017-r{6,7,8,9}`
3. **M4B / M4C / M4-ERR 歷史測試與工作目錄（約 75 個項目，合計約 1.1 GB）**：
   - `/home/<operator>/m4b-*`（含 `m4b-dev.fLl6tj` [281M]、`m4b-test-runtimes` [271M]、`m4b-dev-user-diag-20260913` [95M]、`m4b-pv-*`、`m4b-test-*`、`m4b-tester-*`、`m4b-b2-*`、`m4b-evidence-*`、`m4b-ready-alert.py`、`run-m4b-pv-semantic-auto02.sh`）
   - `/home/<operator>/m4c-*`（含 `m4c-final-dev-20260926-A0dIDk` [116M]、`m4c-s02-*`、`m4c-s03-*`、`m4c-s04-*`、`m4c-s05-*`、`m4c-s06-*`、`m4c-formal-pv-*`、`m4c-ss-dev-*`）
   - `/home/<operator>/m4err-*`（`m4err-dev-20260920-iRHsbo` [57M]、`m4err-fix-20260921-1o4NLJ` [21M]）
4. **ALPHA 過渡期迭代目錄（排除 `alpha-delivery-20261018-r11`，列名 21 個目錄，原估約 700 MB）**：
   - `/home/<operator>/alpha-lifecycle-v2-20261003-IUveqU`（104 MB）
   - `/home/<operator>/alpha-recovery-v4-20261003-qJ7Sbh`（62 MB）
   - `/home/<operator>/alpha-performance-v3-20261003-qFdPG1`（60 MB）
   - `/home/<operator>/alpha-pnph-20261011-d4Vxz8`（54 MB）、`alpha-pnph-r2-20261011-J3Vs9R`（35 MB）、`alpha-pnph-r3-20261011-uRHDr0`（43 MB）
   - `/home/<operator>/alpha-launcher-20261009-x1EXAr`（47 MB）
   - `/home/<operator>/alpha-cold-r6-20261011-u0HIIx`（42 MB）
   - `/home/<operator>/alpha-native-r4-20261011-0qxvrW`（35 MB）、`alpha-native-r5-20261011-chETZR`（40 MB）
   - `/home/<operator>/alpha-interrupt-fix-20261009-PluRne`（40 MB）
   - `/home/<operator>/alpha-focus-r7-20261011-urAGdg`（36 MB）
   - `/home/<operator>/alpha-prefetch-r9-20261011-RYHsb5`（35 MB）、`alpha-prefetch-r10-20261011`（35 MB）、`alpha-prefetch-r11-20261011`（35 MB）
   - `/home/<operator>/alpha-cache-r8-20261011-w0Devn`（35 MB）
   - `/home/<operator>/alpha-dev-20261003-ZSKsbM`（23 MB）
   - `/home/<operator>/alpha-lifecycle-fix-20261003-BB29MH`（21 MB）
   - `/home/<operator>/alpha-manual-20261012`（1.7 MB）、`alpha-live-20261009-VkWLZT`（32 KB）
5. **未被最終結論引用的單次診斷目錄與 `/var/tmp` 暫存（約 48 MB）**：
   - `/home/<operator>/asr-fallback-20261017-r10`（31 MB）
   - `/home/<operator>/acoustic-poc-20261012`（204 KB）
   - `/home/<operator>/app-selfplay-recording-20261017-cf4dcs8h`（584 KB）、`app-selfplay-identity-20261017-an049koy`（392 KB）、`app-selfplay-session-20261017-1cs88czd`（176 KB）、`app-selfplay-session-20261017-9t9g_lml`（152 KB）
   - `/home/<operator>/debug-acoustic-r9-20261017`（292 KB）、`debug-launcher-validation-iw5dht67`（80 KB）、`debug-fixed-entry-smoke-87424zl2`（12 KB）、`debug-entry-smoke-z1014oxy`（12 KB）
   - `/var/tmp/m4c-ss-private-20260920`（9.6 MB）、`/var/tmp/llm-poc-p1-1-pi-evidence`（4 KB）、`/var/tmp/llm-poc-g1-pi-007-evidence`（4 KB）

---

## 5. Designer 中間回覆與執行方案（最終結果見 §6）

**處置：已完成 USER 明確核准的兩個大型目標；原 §4 其餘候選尚未清除。**
這是儲存維護，不是 ALPHA／M6pre 的新產品 gate。所有搬移的證據 Pi 原件仍在，原 locator
有效；已刪的是兩個不供現行安裝使用的大型 runtime／release 副本。

### 5.1 本機證據位置與容量

* 工作站保存根目錄已建立為
  `../pi-evidence/alpha-8b4af53/`（從 `core/` 根目錄起算）。它在 `core/` Git 工作樹
  **外**，僅供本機私有保存，不加入 Git、不 push。根目錄設為 owner-only（`0700`；
  檔案不開放其他使用者讀取）；不可將原始語音、對話、prompt 或 credential 搬進 repo。
* 以 `pi-home/operator/<原相對路徑>` 與 `pi-var/tmp/<原相對路徑>` 保留來源結構。搬移結果可由
  原 Pi locator 明確對應到本機路徑；只保存被現行文件引用的結果、必要輸入、私有 log／
  觀察與尚需診斷的失敗記錄，不複製大型 checkout、venv、模型或 release。
* 本機與 `core/` 共用的磁碟在本次檢查時僅剩約 **2.7 GB**。原提案的 10.45 GB
  過渡目錄不能整批搬入此位置。搬移前重新確認可用空間，分批估算所選檔案大小；不足時
  保留 Pi 原件並另選足夠容量的非 Git 本機媒體，不先刪除換空間。

### 5.2 本次唯讀盤點及已保存內容

* 清理前 Pi `/` 為 59 GB、已用 40 GB、可用 17 GB；正式 `current` 指向
  `releases/asr-notice-20261017-r11`。本機只保存**逐項列出的**結果、私有觀察、必要的
  固定輸入與 log：最終 `alpha-delivery-20261018-r11`、r11 兩個 installed 結果、
  `snowboard-debug` 真人操作、r4 paired observation、七個具名故障診斷目錄、原
  `alpha-live` log、r11 PH 失敗、PN／PH r1–r10 的具名結果、早期 L／P／R／Q 結果、
  interruption／launcher 記錄，以及舊 M4B target 與 acoustic r3 的小型診斷結果。
  大型 checkout、模型、venv 與 release 沒有複製。
* 本機目前有 **647 個一般檔案、18,791,555 bytes**（磁碟占用約 21 MB）。operator
  在搬移邊界主動做一次獨立內容核對：647 個檔案均與 Pi 原件一致、需重傳檔案數 **0**。
  這不是產品測項，也沒有自動加入 startup。被保存的 Pi 證據原件與原有 locator 仍有效。
* 已刪除的兩個精確目標：`m4b-target-20260913-sLrXyC/input` 約 3.4 GB，主要是舊
  LLM runtime、模型與 cache；`app-acoustic-20261012-r3/release` 約 3.4 GB，是過渡
  安裝副本。兩者均未被現行 `snowboard-app` config／launcher 引用，`current` 不指向它們；
  對應小型診斷結果已保存並核對。刪除後兩個精確路徑均不存在；原目錄中的小型
  `user-diagnostic-site` 與 `acoustic-01` 至 `acoustic-04` 等未刪，Pi 整體可用空間
  從約 **17 GB** 增至 **23 GB**（`df -h /`），正式 `current` 仍指向 r11。
* 清理後正式 `/home/<operator>/snowboard-app/run.sh` 經 45 秒 timeout 的啟動／SIGINT 停止
  檢查，**exit 0**；近期 application log 已更新，音訊／顯示設備沒有殘留占用。
* `snowboard-agent-dev` 不能整棵視為暫存：其 `.bare` Git 儲存庫仍服務
  `m4b-test-*`、`m4c-ss-dev-*`、`core`、`poc_llm` 等 linked worktrees。這 1.8 GB
  暫不列為可刪目標。多個 ALPHA `repo/` 含 5–21 個未提交／未追蹤路徑，不能因
  結果已保存就直接刪除其 source 工作樹；其他廣域 `m4b-*`／`m4c-*`／`m4err-*`
  亦須另行逐項清點。

### 5.3 剩餘候選及處理邊界

* §4.1 的 11 個舊 release（約 150 MB）與 `original-entry-20261009.sh` 均**仍在 Pi**。
  它們不是目前 `current` 版本，但這次明確核准的刪除範圍僅含 §5.2 的兩個 3.4 GB
  路徑；擴大刪除時再逐項確認目標。`debug-20261017-r9` 按 A1 保留。
* 2026-10-18 再盤點：`/home/<operator>` 有 **151 個頂層目錄**，Pi `/` 可用約 **23 GB**。
  七個其餘 `app-acoustic-*` 目錄合計約 **157 MB**；其中的 `repo/` 並非 Git 工作樹，
  不能以空白 `git status` 認定無本地資料。其頂層仍有 `acoustic-01/`、
  `manual-entry-smoke/`、回歸／安裝 log、私有測試腳本與設定。現行 status／milestone
  未直接引用這七個目錄，但刪除前仍須逐項判斷哪些觀察或失敗紀錄需要保存。
* §4.2 其餘候選保留。`snowboard-agent-dev` 為共用 Git 工作樹來源，ALPHA 各 `repo/`
  有未提交內容；即使歷史結果已局部搬移，也不將這些 source／Git 資料視為可刪證據副本。
  原提案 **10.6–14.0 GB** 的釋放估算不再是本輪完成量。

若後續需進一步清理：

1. 其餘候選仍須在 Pi 以**唯讀**方式核對每個明確路徑的存在、symlink／mount 邊界、
   大小、執行中程序與 Git 工作樹的未提交／未追蹤內容。以現行 authority／status 的
   引用搜尋列出實際需保存的檔案。不得以廣域 `m4b-*`、
   `m4c-*`、`m4err-*` 或 `app-acoustic-*` glob 當作刪除命令。
2. 其餘被引用的證據再逐檔複製到 §5.1 的私有位置。每批 transfer 完成後由 operator 主動做**一次**
   獨立內容與可讀性核對，確認來源、目的與必要的檔案數／大小；此檢查不進產品測項，
   也不在 application startup 重複執行。保留 Pi 原件直到核對完成。
3. Pi 原件刪除前，把 `docs/status/development.md`、`docs/milestones/ALPHA.md` 等現行文件中的
   相關 locator 指到已核對的本機副本；未刪的原件仍按原路徑定位。失敗結果與歷史執行事實不改寫。
   不把私有內容、完整路徑清單或檔案 payload 提交 Git。
4. 對每個候選刪除目錄再確認無未保存的引用、未提交資料、正在使用的 process 或安裝相依；
   僅以已解析的**明確路徑**分批清理。保留 §3 全部內容及 r9；若某項仍有疑點即保留。
   刪除動作及目標須另由實際執行者根據當時 Pi 狀態確認，不能直接複製原提案清單執行。
5. 每次新增清理目標後檢查 `df -h /`、`current` 指向與正式安裝入口的 config／runtime／模型路徑，
   並做一次有 timeout 的正常啟動、到待命及停止檢查。`run.sh --help` 僅印使用說明，
   不能證明產品可啟動。不重跑 ALPHA 全套驗收；保留更新後的證據 locators。

## 6. USER 指定最小 App 範圍後的處理結果（2026-10-18）

* USER 改定只保留現行 App 可啟動所需內容，並明確同意刪除
  `snowboard-agent-dev`（包括不另存的舊 POC 未提交修改）與 `releases/` 中除
  `asr-notice-20261017-r11` 外的 12 個舊版目錄和舊腳本。這取代 §3／§4.1 的早期保留判斷。
* 工作站私有、非 Git 的 ALPHA 證據根目錄為
  `../pi-evidence/alpha-8b4af53/pi-home/operator/`（從 `core/` 起算）。先前選出的
  **693 個一般檔案、18,957,563 bytes** 在 Pi 原件刪除前做一次獨立內容核對，
  需重傳檔案數 **0**。另把 `snowboard-app/logs/application.log`（99,741 bytes）
  單獨保存並核對，需重傳檔案數亦為 **0**；本機合計 **694 個一般檔案、19,057,304 bytes**。
  `docs/status/development.md` 與 `docs/milestones/ALPHA.md` 給出新 locator／轉換規則；
  原始錄音、private log、結果 payload 不進 Git。
* 已移除 `/home/<operator>` 中 143 個歷史頂層工作／測試目錄及三個舊 M4B helper 檔案；
  非隱藏頂層目錄只剩 `snowboard-app`。七個使用者環境隱藏目錄保持原狀。
  `snowboard-agent-dev` 不是現行入口、設定或 release 的依賴，其舊 Git refs 的提交物件
  在工作站 repo 均可定位；其中未提交 POC 修改依 USER 指示不備份。
* `snowboard-app/releases/` 已只留下目前 `current` 指向的
  `asr-notice-20261017-r11`。舊 11 個小型 release、`debug-20261017-r9` 和
  `original-entry-20261009.sh` 已刪，不能再從 Pi 直接回退到那些目錄。
  正式入口在清理外部歷史工作樹後完成限時正常啟動與 SIGINT 停止，exit **0**。
* USER 另明確核准刪除 `snowboard-app` 頂層約 3.4 GB 的舊安裝副本：`artifacts/`、
  `runtimes/`、`src/`、`.venv/`、`native/`、`requirements/`、`config/`、`scripts/`、
  `config.local.yaml`、`logs/`。目前頂層只剩 `run.sh`、`current` symlink 與 `releases/`；
  `releases/` 只含現行 r11。正式入口經 45 秒界限的正常啟動／SIGINT 停止，exit **0**，
  後續沒有殘留音訊／顯示裝置占用。Pi `/` 最終為 59 GB 總量、23 GB 已用、
  **34 GB 可用（41%）**。舊 release 和頂層舊安裝副本已不可在 Pi 原地回退，
  如需重建，須用工作站 repo、部署輸入與裝置的 `/var/lib/snowboard/products` 資產。
* `/var/tmp` 三個具名舊 POC 暫存目錄亦已刪；systemd 私有執行目錄未觸碰。
