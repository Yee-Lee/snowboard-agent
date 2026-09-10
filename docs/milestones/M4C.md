# M4C — complete offline voice-device integration

狀態：**Blocked by M4B replacement design；not Development Ready**。

M4C完成Button→Listen/ASR→Reasoner/LLM→Speak/TTS、Rest與基本Session Display的exact-product
composition。Camera/look與voice wake留M6，tool/MQTT留M5，完整圖形與動畫留M7。

## Boundary while M4B is redesigned

- M4A Audio保持Accepted；M4B目前不是Accepted input，也沒有可供M4C實作的產品seam。
- M4C不得沿用舊M4B encoding、streaming chunk、queue、response target、context-full或session-count
  行為。這些surface由replacement M4B與後續M4C review重新定義。
- M4B必須先交付Audio+LLM combined memory budget、各階段同時駐留模型／資源，以及同一monotonic
  clock的節點時間紀錄。M4C用這些資料做whole-product composition，不回頭重做subsystem breakdown。
- M4C仍負責整機State Manager／Display wiring、實體audible onset與final product SHA驗證；M4B的
  Audio first write只是一個節點，不等於聲音已可聽見。

## Entry conditions

M4C design與development entry至少等待：

1. `M4B-DESIGN-GATE-REASONER-BEHAVIOR` Closed；
2. M4B replacement design、protocol/profile及新test coverage完成並通過必要review；
3. M4B Audio+LLM vertical slice產出可重用的memory與timing facts；
4. M4B product candidate完成，且與Accepted M4A的inheritance/delta可對齊。

在上述條件完成前，本檔不固定response-time target、resource reserve/hysteresis、streaming策略、
session soak數或其他驗收數值。先前M4C planning內容只留Git history，不可解除任何entry gate。

Current M4B gate見[`M4B_MVA.md`](M4B_MVA.md)，current owner見
[`status/current.md`](../status/current.md)。
