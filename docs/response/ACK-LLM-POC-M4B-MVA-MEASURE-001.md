# ACK-LLM-POC-M4B-MVA-MEASURE-001 — POC intake and design mapping

- Income：`REQUEST-LLM-POC-M4B-MVA-MEASURE-001`
- Work / baseline / gate：`M4B-MVA` / `M4B-MVA-001` / `M4B-MVA-POC`
- Income SHA-256：`5afb24e8ec7ad67853745ec290672c6b48a174819928936609556fefd184a2c2`
- Frozen Core source：`034a50f260e7434e586dddf64ef500da3b1b2b4e`
- Core receipt source：`492f022c06962eb93b37fa0e93765f43690be1b2`
- POC intake baseline：`llm` / `b5ce101d1f75889bfcc1bf6f38ed563f59c2d9a1`
- Status：`RECEIVED / STEP 5 IN PROGRESS / PI NOT AUTHORIZED`

## Intake conclusion

User於2026-09-05確認Income已正式交付。POC確認Core七步流程Step 1～4完成，現在承接Step 5；
`M4B-MVA-POC`為Open，只有Core Designer審核POC結果、採用完整profile並明確解除gate後，
Developer／Tester才可進場。這個新gate不回退已完成的LLM POC M4，也不改寫歷史P8、P9或P10B結果。

Income內兩個相對連結在`llm` checkout下無對應檔案，但所指內容已由本機`core` ref的上述exact
commits核對。POC文件以commit、path及digest記錄其權威來源，不複製或修改Core產品設計。

## Required design correction

舊winner surface只作provenance。MVA量測另建獨立surface，並明確取代下列舊假設：

| Old POC surface | M4B-MVA POC surface |
| --- | --- |
| 每operation建立fresh Conversation | 每product session恰一Conversation，正常turn reuse |
| model產生`action_kind/action_payload/next_perceptions` | model只產exact `text/end`；Reasoner決定speak/listen或rest |
| replacement必做pre-warm | cold/replacement分開做`none/once` A/B，依following-request gain決定 |
| attempt-count／48 MiB觸發recycle | 自然穩態trajectory；MemAvailable為capacity主訊號；recovery另行受控注入 |
| TTFT可代表整合回應 | TTFT、runtime TTC、caller TTC、audible latency分欄；缺Audio proof即縮限claim |

POC不自行改Reasoner政策、跨session記憶、tool/look能力或產品composition。32/128/1024與watchdog
只是`M4B-MVA-001`受控實驗值，不是Core production lock。

## Authorization boundary

本次交付與User指示足以開始workstation contract／runner準備。以下動作仍未獲授權：

- commit、push或正式發布execution snapshot；
- Pi存取、開機、6次cold reboot、hardware execution、artifact transfer/install或network切換；
- benchmark結果、candidate/profile建議發布；
- 跨repo寫入或Core product source修改。

POC會先完成可在workstation驗證的contract surface。Pi申請將附clean exact SHA、surface digest、
唯一命令、run IDs、預估時間、reboot次數、stop/cleanup條件與raw evidence位置。

## Workstation checkpoint

2026-09-05已建立MVA專用profile、prompt/template、compact semantic與`snowboard.llm/2` schemas、
public catalog、machine/manual result schemas、lifecycle/Reasoner/token/resource oracle及LiteRT session
backend。Targeted contract/backend tests為25/25 PASS；完整POC suite為245 PASS、1筆既有Gate 1
thread-warning。這只證明workstation設計與回歸，不建立runtime API、Pi、performance或quality evidence。
