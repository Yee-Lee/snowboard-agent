# P1 Independent Review Request

狀態：`READY_FOR_EXTERNAL_REVIEW`

## Current identity

| Field | Value |
|---|---|
| Branch | `dev_display_p1` |
| Baseline HEAD | `c262924471895dd3106410f79c48b565fc58085d` |
| Candidate commit | `PENDING_REVIEW` |
| Worktree | intentionally dirty with the review target; no candidate SHA exists yet |
| Pi network/preflight | `PENDING` |
| Core M3 | locked; P4 ACK not received |

Baseline HEAD 是本次未提交 diff 的比較基準，不是 candidate SHA。

## Authoritative progress

- P0：完成。
- P0.5：coding/config remediation 已放行；Pi evidence 與 Core ACK 已分離到 P2–P4。
- P1：host checks PASS；獨立 review、candidate commit、manifest checksums 尚未完成。
- P2：Pi 網路待恢復，read-only preflight 尚未執行。
- P3：Pi capability/evidence 尚未執行。
- P4：尚未提交 Core re-review；沒有 `Accepted as M3 design input` ACK。

進度仍以 `docs/poc/milestone_plan.md` checkbox 為唯一權威。

## Review target

請審查 baseline HEAD 到目前 worktree 的下列四個檔案：

- `src/sbd/core/display/tests/conftest.py`
- `src/sbd/core/display/tests/test_starry_night.py`
- `docs/poc/milestone_plan.md`
- `poc_display/deliveries/manifest_001.md`

建議入口：

```bash
git diff --check
git diff -- \
  src/sbd/core/display/tests/conftest.py \
  src/sbd/core/display/tests/test_starry_night.py \
  docs/poc/milestone_plan.md \
  poc_display/deliveries/manifest_001.md
```

## Claimed host verification

- Full display suite：`26 passed, 8 skipped`。
- Explicit shared option run：`4 passed` with `--hardware=mock`。
- Python `compileall`：PASS。
- Compatibility service lifecycle：PASS。
- C11 public-header syntax check：PASS。
- Host stub-linked SSD1351 build and native ABI negative paths：PASS。

八個 skipped tests 是 Pi-only／optional fixture；上述結果不得視為 Pi evidence。

## Required review questions

1. `--hardware` 移到共用 `conftest.py` 後，pytest collection 與 fixture scope 是否正確？
2. 改用 `asyncio.run()` 的四個 scenario 是否保留原測試語意、隔離 lifecycle 並可靠 cleanup？
3. 是否有掩蓋 runtime failure、降低 assertion、或讓 hardware path 誤用 mock 的風險？
4. Milestone 是否準確區分 P0.5 放行、P1 host PASS、P2/P3 pending 與 P4 ACK？
5. Manifest 是否只陳述實際執行的 host checks，且沒有暗示 Pi PASS？
6. 是否存在阻止 candidate commit 的 correctness、reproducibility 或 gate finding？

## Required output

請只將 feedback 寫入 `reviews/P1_REVIEW_FEEDBACK.md`，保留具體檔案與行號、重現命令、finding severity，以及最後 `APPROVE` 或 `BLOCK` 結論。不要修改 review target 或建立 commit。
