# P1 Independent Review Feedback

狀態：`COMPLETE`

> 本檔案由獨立 reviewer process 填寫。Implementation process 不得代填審核結論。

## Review identity

| Field | Value |
|---|---|
| Reviewer/process | Antigravity AI (Claude Sonnet 4.6 Thinking) |
| Reviewed at UTC | 2026-08-12T12:25Z |
| Baseline HEAD (committed) | `c262924471895dd3106410f79c48b565fc58085d` (branch `dev_display_p1`) |
| Review base (prior baseline) | `ecc6a6c` (branch `display`) — P0/P0.5 已提交變更 |
| Reviewed working-tree diff | 4 個未提交檔案（見 Required Review Questions） |
| `git diff --check` | PASS（無 whitespace 問題） |

---

## Findings

| # | Severity | File : line | Finding | Evidence / reproduction | Required action |
|---|---|---|---|---|---|
| F1 | `low` | `conftest.py` : 全文 | `profile` fixture 未加 `scope` 參數，預設為 `function`；`test_starry_night.py` 每個 test 各自建立一個 `asyncio.run()` event loop，與 fixture scope 行為一致，無衝突。但若後續測試需 session-scope hardware，需改 `scope="session"`。 | `PYTHONPATH=src python3 -m pytest src/sbd/core/display/tests/ --hardware=mock -v` → 26 passed, 8 skipped（function-scope 下 4 個 starry_night tests 全 PASS）。 | 現階段無需修改；建議在 Pi run 前評估是否需 session-scope 以節省硬體 start/stop 次數。 |
| F2 | `low` | `test_starry_night.py` : 35–46 | `_run_scenario` 中 `service.stop()` 只在 `finally` 執行，但若 `service.start()` 本身拋出例外，`stop()` 仍會被呼叫，可能導致雙重錯誤訊息蓋過真正 root cause。 | `start()` 失敗場景目前在 mock 下不會觸發，Pi run 時若硬體初始化失敗才會出現。 | 接受現狀（POC 範圍可接受）；建議 P3 Pi run 前加 `if service._running` guard 或分離 `start` 與 `stop` 的例外鏈。 |
| F3 | `low` | `manifest_001.md` : 11–12 | `Delivery source SHA` 仍為 `PENDING`；manifest 使用 `working-tree snapshot` checksum，非 immutable commit SHA。 | 此為 P1 完成條件中 `[ ] 以完整 40-character Git SHA 凍結` 尚未達成的已知狀態，manifest 已明確標示 `IN_PROGRESS / not immutable / not Accepted`。 | **P1 candidate commit 後必須更新 SHA**；現階段屬於已知待辦，非 blocker。 |
| F4 | `none` | — | 其餘所有項目：`--hardware` option 已正確移入共用 `conftest.py`，無 duplicate `pytest_addoption` 衝突；`asyncio.run()` lifecycle 隔離正確；manifest host-verification section 未暗示 Pi PASS；milestone checkbox 精確區分 P0.5 放行、P1 host gate、P2/P3 pending。 | 見下方 Verification performed。 | 無。 |

Severity 定義：`blocking` > `high` > `medium` > `low` > `none`。

---

## Verification performed

| Command/check | Result |
|---|---|
| `git diff --check` | PASS — 無 whitespace error |
| `git diff origin/display..HEAD --stat` | PASS — 6 個已提交檔案（docs/pm_handoff 重組 + brief.md + milestone_plan 新增 P0.5 章節）符合預期 |
| `git status` | 4 個 unstaged 修改為 review target，working tree 有已知 dirty 狀態，未提交是預期行為（P1 尚未凍結） |
| `PYTHONPATH=src python3 -m pytest src/sbd/core/display/tests/ -v --tb=short` | **26 passed, 8 skipped** — 全套測試 PASS；skipped 均為 Pi/optional fixture |
| `PYTHONPATH=src python3 -m pytest src/sbd/core/display/tests/ --hardware=mock -v` | **26 passed, 8 skipped** — `profile` fixture 正確傳入 `"mock"`，無衝突 |
| `pytest_addoption` 重複檢查 | PASS — `--hardware` 與 `--display-config` 均只在 `conftest.py` 定義；`test_starry_night.py` 已移除 local `pytest_addoption` |
| `asyncio.run()` lifecycle 語意確認 | PASS — 每個 test 建立獨立 event loop，`finally` 確保 `stop()` 執行；與原 `@pytest.mark.asyncio` + fixture yield 語意等效 |
| Milestone P0.5 checkbox 狀態 | PASS — 已提交 diff 中 D1–D5 checkbox 全部 `[x]`；unstaged diff 中也正確更新為 `[x]` |
| Manifest host verification section | PASS — `2026-08-12` 段落只記錄 host checks，未聲稱 Pi PASS；`PENDING_PI_RUN` 仍保留 |
| `finding_disposition_v0.3.md` 一致性 | PASS — D3/D4/D5 `Partially resolved` 狀態與 milestone 吻合，未超標聲稱 |

---

## Gate conclusion

結論：**APPROVE**

沒有 `blocking` 或 `high` finding。所有三個 `low` finding 均為已知待辦或 POC 範圍可接受的邊界情況：

1. **conftest.py / profile fixture scope**：function-scope 在目前用法下正確，無誤。
2. **`_run_scenario` start 失敗下的 stop() 副作用**：mock 下不觸發，Pi run 前可選擇性加固。
3. **manifest SHA PENDING**：這正是 P1 仍待完成的 `[ ]` checkbox，candidate commit 後補即可。

`APPROVE` 代表：review target 的 4 個檔案沒有 correctness、reproducibility 或 gate 問題，可進入 candidate commit 流程。**不代表 P2/P3 PASS、P4 ACK 或 Core M3 解鎖。**

---

## P1 next steps（僅供參考，非 review 結論）

1. `git add` 四個 review target 檔案並形成 clean commit → 取得 40-character SHA。
2. 以 immutable SHA 更新 `manifest_001.md` 的 `Delivery source SHA` 欄位與所有 `(working-tree snapshot)` checksum。
3. Pi 網路恢復後按 P2 → P3 流程執行；P3 完成後進入 P4 Core re-review。

---

## Follow-up review

（若 implementation process 根據 finding 修改 review target，請在此附加複審記錄，不得覆蓋以上內容。）
