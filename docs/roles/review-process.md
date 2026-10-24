# Review process

僅在建立、回覆或結案跨角色 review 時讀取。

## 單據與狀態

- 只有跨角色 authority 矛盾／驗收退回確實需要 owner 回覆，而且同 scope 沒有 active review
  時才建立新單；一般建議、狀態回報與任務交接不開 review。
- 命名：`AR_review`（Reviewer→Architect）、`AR_impl`（Designer→Architect）、
  `IR_review`（Reviewer→Designer）、`IR_dev`（Developer→Designer）、
  `MR_review`（Reviewer→Designer）、`TR_spec_M{x}`（Designer→Tester）、
  `TR_dev_M{x}`（Tester→Developer）、`CR_M{x}`（Designer→Developer）。
- Frontmatter：`requestor`、`owner`、`status`；狀態只用
  `Open → Revised → Rejected/Revised → Resolved`。
- `Resolved` 後移至 `docs/reviews/history/`；新議題另開新 round，不改寫舊紀錄。

## 收斂標準

- Finding 分 `Blocking` 與 `Advisory`。只有違反已核准契約／acceptance criteria、
  安全或資料風險、跨模組不一致、假綠燈或高回歸風險可 Blocking。
- 首輪應盤點完整直接影響面並合併同根因。Blocking 必須包含依據、位置、可重現證據、
  預期／實際、影響、首選修正與最低驗收；方向明確時提供可直接採用的文字、骨架或命令。
- 複審只核對既有 finding、直接影響與新 regression，不加入原先即可發現的偏好或新門檻。
  新 Blocking 必須說明先前不可識別的原因。
- 接受符合相同契約與驗收條件的等價解法。Advisory、風格偏好、重複測試與非必要重構
  不得阻擋 `Resolved`。
