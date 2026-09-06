# ASSESSMENT-LLM-M4B-MVA-EFFICIENCY-SCOPE-EXPANSION-001

- Date：2026-09-06
- Trigger：User要求說明D/H風險，並指示POC在P不支援時不得只停止，須擴大實驗找出可行solution
- Governing Income：`REQUEST-LLM-POC-M4B-MVA-EFFICIENCY-002`
- Status：`USER SCOPE EXPANSION / SOLUTION DISCOVERY AUTHORIZED / CORE BASELINE REVISION REQUIRED FOR FORMAL FALLBACK COMPARISON`

## Readiness experiment risk statement

D/H不是單純量「提前open快多少」。H將native Conversation從request-owned短生命週期改為未claim的
held resource，會新增下列需要target evidence的產品風險：

1. **Identity adoption**：held Conversation可能綁到過期或不同的SessionFacts、capabilities、locale、
   profile或generation；錯誤adoption會把錯誤政策或history帶入新session。
2. **Cancellation race**：request可能在open完成前到達，或open與cancel/end同時發生；late native
   return不得被下一個session接走，也不得產生stale success。
3. **Ownership/concurrency**：background open、request adoption與timeout close須single-flight；任一時間
   最多一個live Conversation，不能double bind、double close或把unclaimed object漏掉。
4. **Idle resource cost**：H在沒有user work時持有KV/native allocation；須量30秒holding PSS、
   MemAvailable、temperature與close後回收，不能只報request latency gain。
5. **Readiness truthfulness**：Engine READY不等於interaction READY。所有prepare時間須保留，且H失敗或
   已timeout時必須bounded fallback到D，不能讓caller無限等候或隱藏startup cost。
6. **Isolation/recovery**：end、dirty output、cancel或facts mismatch後不得沿用held Conversation；新session
   必須KV/history乾淨，cleanup失敗則停止而不是自動再open形成loop。

因此B實驗保留。它的採用標準同時要求request-path benefit、holding cost、lifecycle/isolation及cleanup
成立；只看到latency較短不足以選H。

## Scope conflict and handling

現行Income要求selected runtime無法可靠constraint P時回`UNSUPPORTED`並保留J，且禁止另造candidate。
User最新指示提高了POC責任：`UNSUPPORTED`不再是solution discovery的終點。POC可以在workstation進行
bounded capability研究與fallback prototype，但任何新增encoding進入正式Pi matched comparison前，
Core Designer仍須發出revision，固定candidate、唯一變因、case count與selection rule。這可避免把
User授權誤寫成POC自行修改Designer-owned contract。

## Bounded solution funnel

### S0 — exact runtime capability inventory

- 先從exact LiteRT-LM 0.16.0 aarch64 wheel記錄public Python symbols、underlying C API constraint types、
  provider availability及rejected feature；不以upstream `main`推定frozen wheel能力。
- 在Pi前可用官方source/docs形成候選清單，但target import/load/one-output仍是唯一runtime proof。

### S1 — native constrained P（首選）

- 優先嘗試frozen Python public API可用的regex/grammar response format，精確限制
  `S\n<nonblank UTF-8 text>`或exact `E`並要求正常terminal。
- 若Python wrapper未expose、但同一frozen runtime有documented C/C++ LLGuidance regex/Lark path，
  建立POC-only thin adapter驗證可行性、維護成本與cleanup；不修改Core產品或runtime artifact。
- public API與lower-level path分開記錄，不把private/unstable FFI冒充production-ready solution。

### S2 — constrained J with incremental semantic extraction（安全fallback）

- 保留目前已證實的JSON Schema constraint與exact terminal relation；新增streaming JSON string decoder，
  在完整解析`text`字串內容後逐段提供provisional text，final object通過`text/end` validation才成功。
- decoder須正確處理chunk split、escape、Unicode escape/surrogate、key ordering、duplicate/unknown key、
  invalid UTF-8、overflow、cancel與late-invalid terminal。terminal failure取消downstream並close dirty context。
- 此solution主要改善first usable text；不宣稱減少JSON output token cost。

### S3 — compact constrained JSON（成本fallback）

- 若exact v0.16.0 JSON subset可可靠表達，評估一個固定compact schema；internal output仍映射為
  `SemanticGeneration(text,end)`，Reasoner contract不變。
- exact shape須由tokenizer count與schema feasibility決定後交User/Core review；在核准前不凍結
  `t/e` object、tuple或其他具體wire，也不做prompt tuning search。
- 目標是同時降低frame tokens並允許安全incremental extraction；若schema subset拒絕即淘汰。

### S4 — unconstrained P diagnostic（最後手段、預設不建議採用）

- 只用單一frozen instruction與strict parser量格式遵循、控制失敗與fail-closed行為；不repair、不retry。
- 因缺少token-level guarantee，結果只作diagnostic。除非User/Core另行接受明確的control-risk gate，
  不把它選為formal product candidate。

## Down-selection and measurement rule

- Funnel依`S1 → S2 → S3 → S4`進行；一旦有符合control boundary的低風險solution，仍完成已承諾的
  feasibility比較，但不展開無限制prompt/schema搜尋。
- 正式matched Pi measurement維持baseline J，最多加入兩個經User review、Core revision凍結的eligible
  solutions。每個candidate各五個fresh-child two-turn samples；若候選數改變，Core revision須重算
  fixed order與idle spacing，不能沿用舊J/P packet名稱冒充。
- 功能／控制測試先於性能；任何parser、constraint、terminal、isolation或cleanup failure使candidate
  不具效能選擇資格。性能只報paired deltas、median/range與所有regression。
- B readiness使用最終保留的安全encoding，並與encoding comparison分開判定。

## Immediate authorized work and open approval

POC可立即進行S0 source/API inventory及S1～S4 deterministic parser/constraint work。依User更新後的
general rule，可直接在Pi POC workspace開發、測試、除錯exact frozen aarch64 wheel與model path，所有結果
先標`ENGINEERING / NON-FORMAL`；完成後帶回受控diff，由workstation審查、完成plan/packet、commit
並push。新增fallback若要
取得formal comparison credit，須先由User審閱具體candidate，再由Core Designer更新baseline/request，
且在push後以clean exact SHA/frozen packet重跑。POC self-selection不解除任何gate。
