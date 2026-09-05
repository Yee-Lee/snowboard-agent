---
requestor: "Designer"
owner: "Architect"
status: "Open"
severity: "Blocking"
---

# AR_impl_M4B_I — M4 MVA session continuity and Reasoner boundary

日期：2026-09-05。USER已確認M4 MVA、同session對話連續性、Reasoner擁有
next_perceptions、不建立產品記憶系統、無跨session恢复及可調整的效能目標。
[完整首選設計](../implement/ch_m4b_llm_production.md)、
[Developer原單與Designer回覆](IR_dev_M4B_III.md)。

## Workflow / naming

本工作名稱M4B-MVA、基線M4B-MVA-001；流程依[USER七步gate](../milestones/M4B_MVA.md)。
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
