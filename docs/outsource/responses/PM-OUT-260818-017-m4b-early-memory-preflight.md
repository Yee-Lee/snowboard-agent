# Response: PM-OUT-260818-017 — M4 Memory Preflight

- **Handoff**: `PM-OUT-260818-017-m4b-early-memory-preflight`
- **Finding label supplied by PM**: `OUT-M4B-2026-007`（與015已結案的`007-A～D`重號；本response以handoff 017作唯一追蹤鍵）
- **Status**: `Implementation complete — target-stage use pending`
- **Owner**: Core Team Designer（spec）／Core Tester（execution）
- **Architecture change**: `No`
- **Core baseline before implementation**: `2efe13f6aca13be8b224d7276c7caf04c8fcdee4`
- **Tested implementation SHA**: `Pending USER-approved commit; this response does not self-reference its future SHA`

## 1. Disposition and scope correction

Core接受017「提早發現Pi 5 4GB容量風險」的目的，但依USER裁決縮小實作：不把它做成
ResourceManager產品機制、不建立跨POC執行流程，也不保存某次Pi baseline作為新的放行證據。
017落為Core Tester在Accepted Audio與LLM POC packages完成intake後可重跑的單一preflight
test；它包住Core-owned composition smoke並排在昂貴integration repetition、quality與soak之前，
但不是新的Gate，不產生POC或milestone PASS狀態。

因此`Architecture change: No`：production process owner、resource lifecycle、RM startup / recovery、
public product contract與POC repository皆未改變。

## 2. Authoritative implementation

| 路徑 | 作用 |
| :--- | :--- |
| `scripts/m4_memory_preflight.py` | 包住一條既有smoke command，以bounded sampling收集system與process-group memory、處理timeout並收斂child process group |
| `tests/test_m4_memory_preflight.py` | injected snapshot regression；不需Pi或真實POC artifact |
| `docs/test_spec/test_spec_M4.md` | `M4-REG-001`平台、owner、命令、判定與非Gate邊界 |
| `docs/milestones/M4.md` | 固定實測順序及P9 / P10B不被取代 |
| Audio / LLM M4 contracts | 固定POC與Core Tester責任，並消除M4B-P9的PSS / RSS歧義 |

標準命令形狀：

```bash
python3 scripts/m4_memory_preflight.py \
  --max-system-used-mib 3584 \
  --timeout-seconds <bounded-seconds> \
  -- <existing-core-owned-smoke-command>
```

stdout永遠輸出JSON摘要；`--output`只在debug / analyze需要時選用。執行不需要candidate SHA、run
ID、baseline ID、surrogate revision或evidence directory。

## 3. Ownership and POC integration

- Audio / LLM POC不執行combined preflight、不整合Core runner，也不宣告preflight結果。
- POC只交付其Accepted artifact、固定runtime設定及各自的reproduction command；這些原本就是各自
  contract的回交項目，不新增跨repo schema或runner工作。
- Core Developer在兩份Accepted packages完成intake後建立composition smoke；Core Tester只在此時
  執行wrapper。單一POC candidate或尚未intake的package不得用本測項宣稱combined capacity。
- Core Designer維護3584 MiB system-used上限與判定語意；若產品日後要改數字，再走既有contract
  change，不以某次量測自動改門檻。

## 4. Measurement and decision

Primary capacity metric固定為每個sample的：

```text
system_used_kib = MemTotal - MemAvailable
system_used_kib <= 3584 MiB
```

process-group PSS與RSS只供debug / attribution；sum RSS可能重複計算shared pages，不參與容量判定。
任一swap used、swap-in/out增加、full memory-pressure stall增加、cgroup OOM kill增加、command
nonzero / timeout或process-group cleanup失敗，都輸出`PREFLIGHT_RISK`及非零exit。其餘輸出
`PREFLIGHT_OK`。這兩個字串只屬當次測項，不是Gate或acceptance狀態。

正式M4B-P9仍在Accepted Audio package與LLM共同常駐時保存combined residency evidence；P10B
仍執行20-session combined test。017的preflight不取代、降低或提前宣告兩者。

## 5. Verification

```text
PYTHONPATH=src python3 -m pytest -q tests/test_m4_memory_preflight.py
4 passed

PYTHONPYCACHEPREFIX=/tmp/m4_preflight_pycache \
  python3 -m py_compile scripts/m4_memory_preflight.py tests/test_m4_memory_preflight.py
PASS

python3 scripts/m4_memory_preflight.py \
  --max-system-used-mib 999999 --timeout-seconds 5 -- python3 -c 'pass'
status=PREFLIGHT_OK; post_exit_pids=[]; cleanup_unreconciled_pids=[]
```

實體Pi 5 4GB結果刻意不在本response內：機制只在兩份Accepted POC intake後針對當前Core
composition smoke重跑，不以某次歷史run作為017完成或未來候選放行條件。
