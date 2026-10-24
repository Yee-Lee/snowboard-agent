# M1 開發與驗收 Runbook

本文件只說明如何操作 M1；驗收行為與 Pass gate 以 [`test_spec_M1.md`](../test_spec/test_spec_M1.md) 為準。

## 範圍

M1 是無硬體、無網路的純 Python 核心驗證。預設程式使用 `m1_composition.py` 註冊 deterministic workers，只驗證啟動、生命週期、supervision 與 shutdown；它不是 M2 mock backend，也不是 Raspberry Pi 部署。

## 建立開發環境

需求：Python 3.11 以上。

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
python --version
```

Windows 啟用環境時使用 `.venv\Scripts\activate`。

## 執行測試

```bash
python -m pytest -v tests/milestones/test_m1_foundation.py
python -m pytest -v
```

兩條命令均須通過，且 M1 對應測試不得使用 skip 或 xfail。測試數量會隨實作調整，不以固定 case 數作為 Pass gate。

## 本機啟停 Smoke

```bash
python -m sbd.main
```

看到 `M1 runtime ready` 後按 Ctrl+C；正常 shutdown 的 process exit code 應為 `0`。若沒有 `config.local.yaml` 或 `.env`，loader 使用程式預設值；需要覆寫時可由 `config.example.yaml`、`.env.example` 複製後修改。

Exit code：

| Code | 意義 |
|---:|---|
| 0 | 正常關機 |
| 2 | Config 錯誤 |
| 3 | Startup 錯誤 |
| 4 | Runtime fatal |

## M1 不包含

- Raspberry Pi、Pi-only dependency 或真實硬體驗證
- systemd、開機自啟、restart policy 或產品部署
- 網路、credential、模型檔與 M2 concrete modules
