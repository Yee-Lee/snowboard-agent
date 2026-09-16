# M4C — complete offline voice-device integration

狀態：**Design entry open；not Development Ready**。

M4C完成Button→Listen/ASR→Reasoner/LLM→Speak/TTS、Rest與基本Session Display的exact-product
composition。Camera/look與voice wake留M6，tool/MQTT留M5，完整圖形與動畫留M7。

## Accepted entry baseline

- M4A Audio與M4B LLM／Reasoner均為Accepted input；M4B的same-bytes Pi `PV`已Pass，完成commit
  `f87cfa50b9c9415430973076a59c6b1961228090`並push。
- M4C不得沿用舊M4B encoding、streaming chunk、queue、response target、context-full或session-count
  行為。這些surface由replacement M4B與後續M4C review重新定義。
- M4B已交付Audio+LLM combined memory evidence、各階段同時駐留模型／資源，以及同一monotonic
  clock的節點時間紀錄。M4C用這些資料做whole-product composition，不回頭重做subsystem breakdown。
- M4C仍負責整機State Manager／Display wiring、實體audible onset與final product SHA驗證；M4B的
  Audio first write只是一個節點，不等於聲音已可聽見。

## Entry conditions

M4C design entry所需條件已完成：

1. `M4B-DESIGN-GATE-REASONER-BEHAVIOR` Closed；
2. M4B replacement design、protocol/profile及新test coverage完成並通過必要review；
3. M4B Audio+LLM vertical slice產出可重用的memory與timing facts；
4. M4B product candidate完成，且與Accepted M4A的inheritance/delta可對齊。

上述四項已由M4B Accepted disposition滿足，因此Designer可開始M4C design。這不等於Developer
entry：仍須先完成M4C design，再直接交Tester建立Test Spec，之後才可依正常pipeline開發。

M4C不得直接把M4B觀測值固定為response-time target、resource reserve/hysteresis、streaming策略、
session soak數或其他驗收數值；只有M4C產品需求與設計可以建立這些新契約。先前M4C planning內容
只留Git history，不可取代新的Design → Test Spec流程。

Accepted M4B disposition見[`M4B_MVA.md`](M4B_MVA.md)，current owner見
[`status/current.md`](../status/current.md)。
