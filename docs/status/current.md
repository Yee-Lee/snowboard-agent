# Current handoff

- Updated: 2026-09-07
- Writer: Designer only
- Current milestone: M4
- Current stage: M4B MVA design/adoption gate
- Permanent branch: `core`
- Developer entry: **Closed**

## Current disposition

- M4A is Accepted. Its design, test spec and evidence are read-only unless a regression task names it.
- M4B DELIVERY-025 was received, but Step 6 adoption remains pending.
- `M4B-MVA-POC` and `M4B-MVA-EFFICIENCY` are Open. The efficiency request was delivered and its
  byte-identical receipt recorded.
- M4C planning exists, but implementation entry has not opened.

## Ordered exits

1. LLM POC returns the authorized efficiency result.
2. Designer selects one encoding/readiness/profile adoption and updates the affected design delta.
3. Architect/Reviewer close `AR_impl_M4B_II` and `AR_review_M4B_I`; Developer resolves
   `IR_dev_M4B_III` only against the selected contract.
4. Tester revises `TR_spec_M4B_IV` into the new `test_spec_M4B.md`; Designer confirms coverage.
5. Designer opens Developer entry and records the first active work package in `development.md`.

Until steps 1–4 complete, no M4B product implementation, coupled candidate or target acceptance starts.

## Role routing now

| Role | Read now | Action now |
|---|---|---|
| Designer | `design.md`, MVA 002 decision, active efficiency request/receipt, active review headers | wait for result; then prepare one adoption delta |
| Architect / Reviewer | exact active AR document and directly cited `arch.md` sections | review only after activation condition is met |
| Tester | `TR_spec_M4B_IV` header | deferred; do not draft the new spec yet |
| Developer | this file and `development.md` | stop at entry gate; do not preload code, R1 spec or old progress |

Historical review, delivery archive, M4A test spec, M4B R1 test spec and prior Developer checkpoints are
not background reading. Search them only when a current task names an ID, Test ID or SHA.

## Update rule

Designer 只在 gate Open/Closed、stage、Developer entry 或 next owner 已由其權威 owner/review
確認改變時更新本檔，直接替換相應列，不追加日誌。其他角色不得直接修改本檔；其完成回覆
必須指出 disposition 與 next owner，供 Designer 更新。一般交接不新增文件。
