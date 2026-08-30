# ASR Postprocess POC 研議筆記

- **Note ID**: `NOTE-ASR-POSTPROCESS-POC-001`
- **日期**: 2026-08-30
- **狀態**: **Under Consideration / 研議中**
- **範圍**: ASR transcript 交付 LLM 前是否需要獨立 postprocess POC

## 目前判斷

產品中的 ASR transcript 只供 LLM 消費。Unicode、全半形、空白、標點、簡繁體、
台灣用字、數字、英文字母與技術詞彙格式差異，原則上交由 LLM 理解；目前不預設建立
通用文字正規化層。此類規則可能移除原始辨識線索或造成不必要的語意改寫。

現階段維持以下最小路徑：

```text
ASR raw transcript -> protocol / safety validation -> LLM
```

## 啟動 POC 的條件

只有在實際產品測試出現可重現、可量化，而且 LLM 無法可靠吸收的 ASR 缺陷時，才評估
啟動窄範圍 postprocess POC。可能的觀察項目包括：

- 靜音或噪音造成固定型態的幻覺文字；
- 重複句段或固定 runtime 標記污染 transcript；
- VAD / endpoint 截斷造成可辨識的輸入異常；
- 關鍵實體錯誤對產品任務成功率造成穩定影響。

優先處理來源仍是 VAD、endpoint、Whisper prompt / decoder 或 LLM clarification；不得以
postprocess 推測缺字、補寫句子或進行無證據的語意修正。

## 若後續核准：worktree 工作方法

POC 應使用現有 `snowboard-agent` repository 的 Git worktree，不重新 clone。暫定方式為：

```bash
git worktree add \
  /home/yee/workspace/poc_asr_postprocess \
  -b poc/asr-postprocess \
  origin/audio
```

工作原則如下：

- 以 `origin/audio` 為起點，重用既有 Audio POC 的 tracked fixtures、reference transcript、
  CER / task scoring 與測試工具；不從目前有未提交變更的 `core` worktree 複製檔案。
- 新 worktree 與主 repository 共用 Git objects，避免再次 clone 及重複 `.git` 儲存成本。
- `poc/asr-postprocess` 是短期實驗分支，不是新的永久 Core 開發分支；未另行確認前不 push、
  不送正式驗證，也不建立 candidate SHA。
- 初始 POC 只使用 tracked 文字 fixture。除非測試設計證明必要，不複製或下載大型 ASR model、
  runtime、source checkout 或 raw evidence。
- 實驗結果若證明有產品價值，先收斂可重現案例、metric 與最小介面，再將必要實作移植到
  `core`；不直接把整個 POC 歷史併入 Core。
- 結案後以標準 `git worktree` 命令檢查並移除短期 worktree；在確認 tracked 資產與必要證據
  已有保留位置前，不處理既有 `poc_audio` checkout。

本 note 不構成 POC 啟動、branch push、產品設計變更或測試授權。
