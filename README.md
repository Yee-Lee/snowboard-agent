# snowboard-agent — Audio POC

Raspberry Pi 5 離線語音 POC，驗證 VAD、ASR、TTS 三個模組在嵌入式 aarch64 環境下的可行性。
此 repo 是唯一的程式碼、測試 harness、fixture、schema 與 sanitized evidence 來源。

## 目標

在 Raspberry Pi 5 上，離線完成：

| 模組 | 目標 |
|------|------|
| VAD | 找到一個獲准的 speech endpoint baseline，或提出 evidence-backed no-go |
| ASR | 找到一個獲准的台灣華語（含中英混說）ASR baseline，或提出 evidence-backed no-go |
| TTS | 找到一個獲准的原生 PCM TTS baseline，或提出 evidence-backed no-go |

三個模組需同時常駐，完成至少 20 個固定 pipeline sessions，並通過 failure injection 與離線驗證。

## Milestones

每個正式完成的 milestone 在 `audio` branch 上對應一個不可移動的 annotated tag（`m0`、`m1`、……）。

| Tag | 說明 |
|-----|------|
| `m0` | Pi 環境 readiness gate：SSH、worktree、timeout/cancel/cleanup 就緒 |
| `m1` | 比較基線：frozen fixture、VAD timing labels、fake baseline、Option A 實作基準 |
| `m2` | VAD/ASR/TTS 候選比較完成：scorecard、shortlist、primary/fallback recipe、TTS disposition |
| `m3` | Pi 5 + pinned M3 Audio HAL 實機驗證：winner 或 evidence-backed no-go |
| `m4` | 20-session 組合驗證、failure injection、離線驗證與正式交付 |

目前進度見 [`docs/milestone/README.md`](docs/milestone/README.md)。

## Repo 結構

```
snowboard-agent/
├── poc_audio/
│   ├── src/          # POC source（harness、wrapper、schema、runner）
│   ├── tests/        # 本地 unit / smoke tests
│   ├── tools/        # 各 milestone 執行腳本
│   ├── fixtures/     # Fixture catalog（含授權邊界）
│   ├── evidence/     # Sanitized evidence index（raw 由 .gitignore 排除）
│   └── deliveries/   # Delivery manifest、ACK、change request
├── docs/
│   ├── milestone/    # Milestone 狀態（README.md 為唯一入口）
│   ├── specs/        # 交付清單、開發指引、M3 Audio 要求
│   ├── reviews/      # Reviewer 報告
│   └── pm_handoff/   # PM 授權文件（ACK、CR）
└── AGENTS.md         # Agent 工作規範（必讀）
```

> **Git 中不含**：模型、大型 raw result、私有語音、敏感 transcript、SSH config、API key 或 secret。

## 快速開始

### 環境前置確認

```sh
M0_SSH_CONFIG=/protected/path/config PI_POC_REPO=/path/to/pi-worktree \
  bash poc_audio/tools/environment_pre_test.sh <operator-alias>
```

### 本地 unit tests

```sh
PYTHONPATH=poc_audio/src \
  python3 -m unittest discover -s poc_audio/tests -v
```

### M2A packet 驗證（不執行 inference）

```sh
bash poc_audio/tools/run_m4a_m2a_packet.sh --validate-only
```

詳細操作說明見 [`poc_audio/README.md`](poc_audio/README.md)。

## 分支與 commit 規範

- 唯一永久開發分支：`audio`
- Candidate SHA 一旦送驗即不可改寫；後續修正只能 append on top
- Commit 格式：`[work_type][milestone]: concise title`，英文、60 字以內

## 角色分工

| 角色 | 責任 |
|------|------|
| Technical Lead | 規劃、evidence review、winner/no-go 建議 |
| Developer | 工作站 source、tests、文件；local tests 通過後建 candidate commit |
| Tester | Pi checkout、test packet、evidence 收集；不得在同一 run 修改 source |
| User | 硬體操作、TTS 主觀品質確認、商用/license 決策 |
| Designer | 凍結 gate、核准 winner/no-go |
| Reviewer | 審查 wrapper 邊界、lifecycle、blocking findings |

完整流程見 [`docs/audio_poc_workflow.md`](docs/audio_poc_workflow.md)。

## 重要文件

- [Milestone 狀態總覽](docs/milestone/README.md)
- [工作流程與合作方式](docs/audio_poc_workflow.md)
- [最終交付清單](docs/specs/audio_poc_delivery_checklist.md)
- [POC 開發指引](docs/specs/audio_poc_development_guide.md)
- [M3 Audio 要求](docs/specs/core_audio_m3_requirements.md)
- [Pi 操作說明](poc_audio/README.md)
- [Agent 工作規範](AGENTS.md)

## 資料來源聲明

本專案的外部驗證 fixture 使用來自 [Mozilla Common Voice](https://commonvoice.mozilla.org/) 的資料：

- **Dataset**：Common Voice Scripted Speech 26.0 — Chinese (Taiwan)（`zh-TW`）
- **版本**：26.0，發布時間 2026-06-17
- **授權**：[CC0 1.0 Universal (CC0-1.0)](https://creativecommons.org/publicdomain/zero/1.0/)
- **來源**：Mozilla Data Collective；需透過官方帳號驗證下載

音檔本身不納入此 repo；Git 中只保留 clip ID、SHA-256 checksum 與衍生 PCM 的 checksum 記錄。
