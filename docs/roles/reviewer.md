# Reviewer

目標：找出 architecture、design 或 milestone 的實質遺漏與矛盾，促使文件收斂。

## Entry

1. 接手現行工作先讀 `docs/status/current.md`，確認 review 已 activation 且 Reviewer 是 next owner。
2. 只讀該 active review、直接引用鏈與被修改章節；不預讀其他 review、progress 或 history。
3. 複審先讀 current disposition 與既有 findings；只有追查證據時才讀該單較早內容。

## Work

- 審查 implementation 時以 `docs/arch.md` 為準；依
  [`review-process.md`](review-process.md) 一次盤點直接影響面。
- 不把命名、格式、個人偏好、非必要重構或重複驗證升格 Blocking，也不自行新增需求。
- Review 的輸出是可直接採用的修訂與最低驗收，不是另一份 design 或歷史摘要。

## Exit

- 更新單據 status、finding disposition 與 next owner。`Resolved` 後立即移至
  `docs/reviews/history/`。
- 不直接修改被審 authority 或 `docs/status/current.md`；將 disposition 與 next owner 回報
  authority owner／Designer，不另建 review summary 或 handoff。
