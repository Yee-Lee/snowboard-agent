---
requestor: "Designer"
owner: "Architect"
status: "Resolved"
severity: "Blocking"
---

# AR_impl_M4B_I — M4 MVA session continuity and Reasoner boundary

日期：2026-09-05。USER已確認M4 MVA、同session對話連續性、Reasoner擁有
next_perceptions、不建立產品記憶系統、無跨session恢复及可調整的效能目標。
[完整首選設計](../../implement/ch_m4b_llm_production.md)、
[Developer原單與Designer回覆](../IR_dev_M4B_III.md)。

## Workflow / naming

本工作名稱M4B-MVA、基線M4B-MVA-001；流程依[USER七步gate](../../milestones/M4B_MVA.md)。
Architect修訂arch.md後，Reviewer同一輪審arch.md、design/implement與POC計畫；
Designer定版交付POC。POC回交經Designer核准解除gate前，Developer／Tester不進場。

## Contract conflict and evidence

arch.md §4.1早已有wake→IDLE session；§2.7允許LLM理解/推論、Reasoner正規化，
§4.6要求SM再驗證，這些並未因Developer指控而失效。
但§8.3把跨turn/跨session記憶一併列為未納入，與USER要求「對，開啟」承接上一句矛盾。
現有SM只清自身session fields，Reasoner/adapter沒有session lifecycle port。
新state不能只放child，否則rest/interrupt/no-THINK/shutdown可能留下舊context。

## Preferred architecture amendment

請Architect對主文件一次作下列修訂，不以本單自動視為架構已核准：

1. §2.7加入：M4 Reasoner提供產品身分/能力與本turn facts，LLM回短回答/結束意圖；
   Reasoner獨立決定action與next_perceptions。M4通常speak→listen，結束→rest。
   不新增每turn第二次LLM推論，不要求通用task/context manager。
2. §4.1加入：session內允許runtime Conversation保留history/KV，session結束全部丟棄；
   Core只管理owner/lifetime/capacity，沒有跨session持久化。
3. §4.4/§4.6/§6.5加入：SM通知Reasoner begin/end；pending control納入收斂。
   rest/interrupt/error/shutdown四路在clear tracking/resume wake前完成close。
   SM inbox不可被native operation阻塞；late ACK不影響新session。
4. §2.7/§6.3加入P5分界：未改Conversation的pre-inference rejection可apology/listen；
   dirty/失去context時close並結束產品session，不能silent reset繼續回答。
   cancel中的Reasoner仍不publish正常Fact。Unprovable cleanup沿既有Level2/3。
5. §8.3改成：長期／跨session記憶、摘要、檢索、task restoration與完整tool loop仍未納入；
   M4 session內runtime自然continuity已由上述契約涵蓋。
6. 維持empty rest、LLMResponse三欄、SM唯一session owner、RM唯一rebuild owner、
   startup-static capability與no-network/native isolation；不新增farewell action鏈。

## Minimum verification and closure

依設計§9：same-session reuse、cross-session absence、pending open/close cancellation、
no-THINK end、dirty-result disposal、stale identity、wrong capability、
single Fact與same-key recovery皆有明確oracle。
Architect須明記每項採用/等價修訂及主文件落點；影響面涵蓋Ch2/2b/4/5/6/9，
不重開M4A HAL、model選型、M5實際tool或§8.3其他future項。
USER已給產品方向，不需要重問是否准許基本對話連續性；本單處理架構一致性。

---

## Architect 回應（2026-09-05）

已完成逐點修訂，落點如下：

1. **§2.7「M4 Reasoner 分工（LLM 角色邊界）」** — 新增段落：Reasoner 提供產品身分/能力聲明與本 turn facts；LLM 只輸出短回答/結束意圖；Reasoner 獨立決定 `action_kind` 與 `next_perceptions`；M4 典型流程 speak→listen、結束→rest；不新增第二次 LLM 推論、不引入通用 context manager。
2. **§4.1「Session 內 Conversation（runtime continuity）」** — 新增段落：Core 只管 owner/lifetime/capacity；session 結束（rest/interrupt/error/shutdown 四路）即清棄 `Conversation` 全部內容；不做跨 session 持久化；不建立產品記憶系統。
3. **§4.6 THINK Entry** — 加入首 turn SM 通知 Reasoner session begin、建立 `Conversation`；通知為控制流方法呼叫，不阻塞 SM inbox；late ACK 不影響新 session。**§4.6 ACTION Exit(rest) 與 ERROR Entry** — 加入 SM 通知 Reasoner session end；四路（rest/interrupt/error/shutdown）皆在 clear tracking 欄位前完成 close；通知不阻塞 SM inbox。**§4.7** — 表格更新 InterruptRequested / ShutdownRequested 與 ErrorOccurred 行，明確先通知 Reasoner session end 再執行收斂。
4. **§2.7「P5 分界（pre-inference 與 dirty context）」** — 新增段落：pre-inference rejection（未改 Conversation）可直接降級產 apology+listen；dirty/lost context 必須產 `action_kind=rest` 結束 product session，不得 silent reset；cancel 中 Reasoner 不 publish 正常 `LLMResponse`；Unprovable cleanup 沿 Level 2/3。
5. **§8.3「多輪對話記憶（跨 session）」** — 更新：明確說明 M4 session 內 runtime continuity 已由 §4.1 納入，不屬未定案；未納入項改為「長期/跨 session 記憶、摘要、向量檢索、task restoration」。
6. **不變項確認**：empty rest 語意（`action/rest` 純執行 UX 收尾，§2.8）未異動；`LLMResponse` 三欄（`action_kind` / `action_payload` / `next_perceptions`，§2.7 / §3.3）未異動；SM 唯一 session owner（§2.1 / §3.5）未異動；RM 唯一 rebuild owner（§6.1 / §6.5）未異動；startup-static capability（§6.8 B / §7.2）未異動；no-network/native isolation（§1.2 離線原則）未異動；不新增 farewell action 鏈。

狀態改為 `Revised`，請 Designer（Requestor）審核確認。

---

## Designer 結案（2026-09-05）

已核對六項修訂落點與Reviewer三面PASS。Step 3以arch.md為權威固定控制時序：
首turn THINK Entry完成begin後才generate；四路結束先登記end intent並阻止新admission，
再收斂active operation、完成Conversation close proof，最後清tracking／resume wake。
此具體化同時滿足「先通知end」與「close完成後才能開新session」，未改變架構邊界。

六項要求均已採用，不變項均保留；本單標記Resolved並歸檔。後續量測profile、
Tester coverage與產品實作分別由M4B-MVA Step 4–7追蹤，不重開本架構單。
