# M4 實測規格：Memory Preflight

本檔目前只固定M4 Core整合實測階段的early memory preflight。其用途是在執行昂貴的integration
loop、quality或soak前，先用相同target上的最小smoke command排除明顯的4GB容量風險；它不是
新的milestone gate，也不取代M4A-P9、M4B-P9 / P10B或產品exact-SHA acceptance。

## M4-REG-001 — Pi 5 4GB memory preflight

| 欄位 | 契約 |
| :--- | :--- |
| Platform | `RPI-NATIVE`；正式預定的Pi 5 4GB測試環境 |
| Owner | Core Tester執行與判讀；Audio / LLM POC不執行combined preflight，也不修改Core runner |
| Timing | Accepted Audio與LLM POC packages均完成Core intake，且Developer已建立Core-owned composition smoke command後、昂貴repetition / quality / soak前；integration debug或artifact / config變更後可重跑 |
| Command | `python3 scripts/m4_memory_preflight.py --max-system-used-mib 3584 --timeout-seconds <N> -- <existing-smoke-command>` |
| Primary metric | 每個sample的`system_used_kib = MemTotal - MemAvailable`；任一sample不得超過3584 MiB |
| Hard risk | swap used非零、swap-in/out增加、full memory-pressure stall增加、cgroup OOM kill增加、smoke nonzero / timeout或process group未cleanup |
| Diagnostic only | process-group sum PSS、sum RSS、最低`MemAvailable`、執行前後system counters；不得以sum RSS作容量判定 |
| Output | stdout JSON；`--output`只供當次debug / analyze選用，不要求run ID、candidate SHA、baseline packet或長期保存 |
| Result | `PREFLIGHT_OK`表示本次smoke未見上述風險；`PREFLIGHT_RISK`表示先停止昂貴測試並調整artifact / config。兩者都不是POC或milestone PASS狀態 |

POC團隊只需依既有contract交付Accepted artifact、固定設定及各自的reproduction command；不為本
測項新增工作。Core Developer完成composition smoke後，Core Tester才以本wrapper執行。單一POC
candidate或尚未intake的package不得用本測項宣稱combined capacity。正式combined residency與
20-session結果仍由M4B-P9 / P10B保存。

### Portable regression

`tests/test_m4_memory_preflight.py`使用injected snapshots固定四條行為：

1. 大量sum RSS不會取代system `MemAvailable`造成false risk；
2. full memory pressure或swap activity產生`PREFLIGHT_RISK`；
3. command結束後的process-group survivor產生`PREFLIGHT_RISK`；
4. 3584 MiB上限明確套用`MemTotal - MemAvailable`，不再使用含糊的「PSS / RSS」。
